"""
工作流基础设施

分两层抽象，具体业务工作流继承 :class:`LlmWorkflow` 后只需描述「图的形状」：

- :class:`BaseWorkflow`：LangGraph 图的生命周期（构建、编译、导出）与统一的
  运行入口（invoke / stream / stream_events + 人工中断续跑）。
- :class:`LlmWorkflow`：在此之上提供大模型结构化调用，以及「生成 / 评估 /
  人工审核 / 路由 / 保存 / 读取参考资料」这些反复出现的节点的通用实现。

节点的差异通过 ``*Spec`` 声明式描述（见下方 dataclass），避免为每个字段复制
一整套近似的 async 函数。
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
)

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import Command, RetryPolicy, interrupt
from pydantic import BaseModel

from config import settings
from utils import FileUtil, logger

#: 节点日志的分隔横幅
_BANNER = "\n===========================\n"

#: 日志中长文本的预览长度
_PREVIEW_LENGTH = 100

#: 条件边的两种去向
ACCEPTED = "Accepted"
REJECTED = "Rejected"

#: 节点函数签名：接收 state，返回要合并回 state 的增量（None 表示不更新）
NodeAction = Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]


# ==================== 节点声明 ====================

@dataclass(frozen=True)
class Section:
    """
    提示词中的一段 ``[label]: value``。

    ``label`` 是给模型看的字段名，``key`` 是取值用的 state 键——两者故意分开，
    因为提示词里的字段名不一定等于 state 里的字段名。
    """
    label: str
    key: str


@dataclass(frozen=True)
class ReferenceSpec:
    """从沙箱文件读取参考资料的节点。"""
    log_label: str
    state_key: str
    filename: str


@dataclass(frozen=True)
class GeneratorSpec:
    """
    「首次生成 / 带反馈优化」二态生成节点。

    当 ``target_key`` 已有值时视为二次优化：换用 ``refine_prompt``，
    并在 ``sections`` 之后追加 ``refine_sections``。
    """
    log_label: str
    result_label: str
    schema: Type[BaseModel]
    target_key: str
    generate_prompt: str
    refine_prompt: str
    sections: Tuple[Section, ...]
    refine_sections: Tuple[Section, ...] = ()
    #: 从结构化响应中取出要写回 state 的值
    extract: Callable[[BaseModel], Any] = lambda response: response


@dataclass(frozen=True)
class EvaluatorSpec:
    """大模型自动评估节点；``image_key`` 非空时以多模态消息发送。"""
    log_label: str
    schema: Type[BaseModel]
    system_prompt: str
    sections: Tuple[Section, ...]
    flag_key: str
    feedback_key: str
    image_key: Optional[str] = None


@dataclass(frozen=True)
class ReviewSpec:
    """人工审核节点（LangGraph interrupt）。"""
    log_label: str
    question: str
    detail_key: str
    flag_key: str
    feedback_key: str


@dataclass(frozen=True)
class SaveSpec:
    """
    落盘节点：``flag_key`` 未通过时跳过；文件名由 ``name_key`` 指向的档案的
    ``name`` 字段 + ``suffix`` 组成，形如 ``<name>/<name>.json``。
    """
    log_label: str
    flag_key: str
    value_key: str
    target_key: str
    suffix: str
    writer: Callable[..., str]
    name_key: str = "npc_json"
    name_field: str = "name"


# ==================== 图生命周期 ====================

class BaseWorkflow(ABC):
    """
    LangGraph 工作流基类。

    子类需要：
    1. 声明 ``state_schema``（以及可选的 ``input_key`` / ``workspace_dir`` / ``graph_image_name``）；
    2. 实现 :meth:`_build_graph` 返回未编译的 ``StateGraph``。

    其余（编译、checkpointer、thread 配置、六个运行入口、图片导出）均由基类提供。
    """

    #: 状态的 TypedDict 类型
    state_schema: ClassVar[Type] = None
    #: ``ainvoke(prompt)`` 时 prompt 写入的 state 键
    input_key: ClassVar[str] = "prompt"
    #: ``astream_events`` 对外透出的事件类型
    streamed_event_kinds: ClassVar[Tuple[str, ...]] = ("on_chat_model_stream", "on_custom_event")
    #: 文件沙箱根目录（相对项目根），None 表示不需要沙箱
    workspace_dir: ClassVar[Optional[str]] = None
    #: 编译后导出的流程图文件名，None 表示不导出
    graph_image_name: ClassVar[Optional[str]] = None

    #: 重试策略参数
    retry_max_attempts: ClassVar[int] = 3
    retry_initial_interval: ClassVar[float] = 1.0
    retry_backoff_factor: ClassVar[float] = 2.0
    #: 触发重试的异常；子类可按所用服务商扩展
    retry_on: ClassVar[Tuple[Type[BaseException], ...]] = (ConnectionError, TimeoutError)

    def __init__(
        self,
        thread_id: Optional[str] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        workspace_dir: Optional[str] = None,
    ):
        """
        :param thread_id: 会话线程 ID，默认取 ``settings.ui.default_thread_id``。
        :param checkpointer: 状态存储，默认内存实现（进程重启即丢失）。
        :param workspace_dir: 文件沙箱根目录，默认取类属性 ``workspace_dir``。
        """
        if self.state_schema is None:
            raise NotImplementedError(f"{type(self).__name__} 必须声明 state_schema")

        self._settings = settings
        self._thread_id = thread_id or settings.ui.default_thread_id
        self._checkpointer = checkpointer or MemorySaver()

        root = workspace_dir or self.workspace_dir
        self._fs = FileUtil(root) if root else None

        self.app = self._build_graph().compile(checkpointer=self._checkpointer)

        if self.graph_image_name:
            self.export_graph_image(self.graph_image_name)

    # ==================== 构建 ====================

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """构建（但不编译）状态图。"""

    @classmethod
    def build_retry_policy(cls) -> RetryPolicy:
        """按类属性生成失败重试策略。"""
        return RetryPolicy(
            max_attempts=cls.retry_max_attempts,      # 包括第一次尝试在内的总次数
            initial_interval=cls.retry_initial_interval,  # 第一次重试前的等待时间（秒）
            backoff_factor=cls.retry_backoff_factor,  # 每次重试等待时间的倍数
            retry_on=cls.retry_on,
        )

    def export_graph_image(self, filename: str) -> Optional[str]:
        """
        导出流程图 PNG 到沙箱目录。

        依赖外部渲染服务，属于开发期辅助产物，失败只告警不影响工作流运行。
        """
        if self._fs is None:
            logger.warning("未配置 workspace_dir，跳过流程图导出")
            return None
        try:
            image = self.app.get_graph(xray=True).draw_mermaid_png()
        except Exception as e:
            logger.warning(f"流程图导出失败（不影响运行）: {e}")
            return None
        return self._fs.write_bytes(filename, image)

    # ==================== 运行配置 ====================

    @property
    def thread_id(self) -> str:
        """当前会话线程 ID"""
        return self._thread_id

    @property
    def run_config(self) -> Dict[str, Any]:
        """LangGraph 运行配置（携带 thread_id 以启用 checkpoint）"""
        return {"configurable": {"thread_id": self._thread_id}}

    def get_state(self):
        """获取当前 checkpoint 状态（含待处理的 interrupts）。"""
        return self.app.get_state(config=self.run_config)

    def _entry_payload(self, prompt: str) -> Dict[str, Any]:
        """把用户输入包装为图的初始输入。"""
        return {self.input_key: prompt}

    # ==================== 运行入口 ====================

    async def ainvoke(self, prompt: str) -> Dict[str, Any]:
        """异步运行至结束或中断。"""
        return await self.app.ainvoke(input=self._entry_payload(prompt), config=self.run_config)

    async def ainvoke_continue(self, resume: Any) -> Dict[str, Any]:
        """携带人工审核结果继续运行。"""
        return await self.app.ainvoke(Command(resume=resume), config=self.run_config)

    async def astream(self, prompt: str) -> AsyncIterator[Any]:
        """异步流式运行，逐节点产出状态增量。"""
        async for chunk in self._astream(self._entry_payload(prompt)):
            yield chunk

    async def astream_continue(self, resume: Any) -> AsyncIterator[Any]:
        """携带人工审核结果继续流式运行。"""
        async for chunk in self._astream(Command(resume=resume)):
            yield chunk

    async def astream_events(self, prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """异步流式运行，产出 token / 自定义事件。"""
        async for event in self._astream_events(self._entry_payload(prompt)):
            yield event

    async def astream_events_continue(self, resume: Any) -> AsyncIterator[Dict[str, Any]]:
        """携带人工审核结果继续流式运行，产出 token / 自定义事件。"""
        async for event in self._astream_events(Command(resume=resume)):
            yield event

    async def _astream(self, payload: Any) -> AsyncIterator[Any]:
        """流式运行的唯一实现。"""
        async for chunk in self.app.astream(payload, config=self.run_config):
            yield chunk

    async def _astream_events(self, payload: Any) -> AsyncIterator[Dict[str, Any]]:
        """事件流的唯一实现，按 ``streamed_event_kinds`` 过滤。"""
        async for event in self.app.astream_events(payload, config=self.run_config):
            if event.get("event") in self.streamed_event_kinds:
                yield event


# ==================== 通用 LLM 节点 ====================

class LlmWorkflow(BaseWorkflow, ABC):
    """
    面向「大模型生成 -> 自动评估 -> 人工审核 -> 落盘」这类工作流的基类。

    提供的通用节点工厂都返回 async 闭包，可直接交给 ``StateGraph.add_node``。
    """

    def __init__(self, *args: Any, **kwargs: Any):
        self._model = init_chat_model(model=settings.models.chat_model)
        super().__init__(*args, **kwargs)

    # ==================== 日志 ====================

    @staticmethod
    def _log_step(label: str) -> None:
        """打印节点开始的分隔横幅。"""
        logger.info(f"{_BANNER}{label}")

    @staticmethod
    def _preview(value: Any, length: int = _PREVIEW_LENGTH) -> str:
        """截断长文本，避免日志被世界观／base64 撑爆。"""
        return str(value)[:length]

    # ==================== 大模型调用 ====================

    def _structured_model(self, schema: Type[BaseModel], system_prompt: str):
        """绑定结构化输出与系统提示词的模型。"""
        return self._model.with_structured_output(schema).bind(system_prompt=system_prompt)

    @staticmethod
    def _render_sections(sections: Sequence[Section], state: Dict[str, Any], suffix: str = "") -> list:
        """把 sections 渲染成 ``[label]: value`` 文本列表。"""
        return [f"[{section.label}]: {state[section.key]}{suffix}" for section in sections]

    @staticmethod
    def _image_block(image_base64: str, mime_subtype: str = "jpeg") -> Dict[str, Any]:
        """构造多模态消息中的图片块。"""
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/{mime_subtype};base64,{image_base64}"},
        }

    async def _ainvoke_structured(
        self,
        schema: Type[BaseModel],
        system_prompt: str,
        sections: Sequence[Section],
        state: Dict[str, Any],
        image_key: Optional[str] = None,
    ) -> BaseModel:
        """
        以结构化输出调用大模型。

        :param image_key: 非空时改用多模态消息，把 ``state[image_key]`` 作为图片附上。
        """
        model = self._structured_model(schema, system_prompt)
        if image_key is None:
            return await model.ainvoke("\n\n".join(self._render_sections(sections, state)))

        content: list = [
            {"type": "text", "text": text}
            for text in self._render_sections(sections, state, suffix="\n\n")
        ]
        content.append(self._image_block(state[image_key]))
        return await model.ainvoke([HumanMessage(content=content)])

    # ==================== 通用节点工厂 ====================

    def make_initialize_node(self, defaults_factory: Callable[[], Dict[str, Any]]) -> NodeAction:
        """初始化节点：用零值补齐未提供的字段。"""

        async def node(state: Dict[str, Any]) -> Dict[str, Any]:
            self._log_step("初始化节点")
            merged = {**defaults_factory(), **state}
            logger.info(f"\n初始state: \n{merged}")
            return merged

        return node

    def make_reference_node(self, spec: ReferenceSpec) -> NodeAction:
        """参考资料节点：state 中已有值则复用，否则从沙箱文件读取。"""

        async def node(state: Dict[str, Any]) -> Dict[str, Any]:
            self._log_step(spec.log_label)
            value = state[spec.state_key]
            if not value:
                value = await asyncio.to_thread(self._fs.read_text, spec.filename)
            logger.info(f"\n{spec.log_label}: \n{self._preview(value)}")
            return {spec.state_key: value}

        return node

    def make_generator_node(self, spec: GeneratorSpec) -> NodeAction:
        """生成节点：首次生成，或带反馈优化已有结果。"""

        async def node(state: Dict[str, Any]) -> Dict[str, Any]:
            self._log_step(spec.log_label)
            is_refining = bool(state[spec.target_key])
            system_prompt = spec.refine_prompt if is_refining else spec.generate_prompt
            sections = spec.sections + (spec.refine_sections if is_refining else ())

            response = await self._ainvoke_structured(spec.schema, system_prompt, sections, state)
            value = spec.extract(response)

            logger.info(f"\n{spec.result_label}: \n{value}")
            return {spec.target_key: value}

        return node

    def make_evaluator_node(self, spec: EvaluatorSpec) -> NodeAction:
        """自动评估节点：产出 is_ok 与 feedback。"""

        async def node(state: Dict[str, Any]) -> Dict[str, Any]:
            self._log_step(spec.log_label)
            response = await self._ainvoke_structured(
                spec.schema, spec.system_prompt, spec.sections, state, image_key=spec.image_key
            )
            logger.info(f"\n{spec.log_label}: \n{response}")
            return {spec.flag_key: response.is_ok, spec.feedback_key: response.feedback}

        return node

    def make_review_node(self, spec: ReviewSpec) -> NodeAction:
        """人工审核节点：中断等待前端回填 ``{"is_ok": bool, "feedback": str}``。"""

        async def node(state: Dict[str, Any]) -> Dict[str, Any]:
            self._log_step(spec.log_label)
            response = interrupt({
                "question": spec.question,
                "details": state[spec.detail_key],
            })
            logger.info(f"\n用户对 {spec.detail_key} 的确认信息: \n{response}")
            return {spec.flag_key: response["is_ok"], spec.feedback_key: response["feedback"]}

        return node

    def make_save_node(self, spec: SaveSpec) -> NodeAction:
        """落盘节点：未通过审核则不写文件。"""

        async def node(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            self._log_step(spec.log_label)
            if not state[spec.flag_key]:
                return None

            name = state[spec.name_key].get(spec.name_field)
            file_path = f"{name}/{name}{spec.suffix}"
            saved_path = await asyncio.to_thread(spec.writer, file_path, state[spec.value_key])

            logger.info(f"\n保存路径: \n{saved_path}")
            return {spec.target_key: saved_path}

        return node

    @staticmethod
    def make_router(flag_key: str) -> Callable[[Dict[str, Any]], str]:
        """条件边路由：按布尔标记返回 ``Accepted`` / ``Rejected``。"""

        def route(state: Dict[str, Any]) -> str:
            return ACCEPTED if state[flag_key] else REJECTED

        # LangGraph 以函数名标注条件边，给出可读的名字便于看图排查
        route.__name__ = f"route_{flag_key}"
        return route
