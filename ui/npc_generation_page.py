"""
NPC 角色生成页面

提供两种模式：
1. 大模型对话模式 - 传统的聊天对话，带有上下文记忆
2. 工作流模式 - 使用 NPC 生成工作流，自动生成角色档案、图片和3D模型
"""
import asyncio
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Mapping, Optional, Tuple

import streamlit as st
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import settings
from core import prompts
from utils import logger
from workflows import GenerateNpcWorkflow

from .base import BasePage
from .components import (
    render_base64_image,
    render_loading_status,
    render_message,
    render_progress_steps,
)
from .formatters import format_completed_result, format_final_result, format_npc_json_result
from .styles import NPC_PAGE_CSS


# ==================== 模式定义 ====================

class ChatMode(Enum):
    """聊天模式"""
    LLM = "llm"
    WORKFLOW_NPC = "workflow_npc"


@dataclass(frozen=True)
class ModeMeta:
    """模式的展示信息"""
    display_name: str
    description: str
    input_placeholder: str


MODES: Dict[str, ModeMeta] = {
    ChatMode.LLM.value: ModeMeta(
        display_name="💬 大模型对话",
        description="自由对话，讨论角色设计想法（支持上下文记忆）",
        input_placeholder="输入你的消息，与AI讨论角色设计...",
    ),
    ChatMode.WORKFLOW_NPC.value: ModeMeta(
        display_name="🔄 NPC生成工作流",
        description="自动生成完整NPC角色（档案+图片+3D模型）",
        input_placeholder="描述你想要生成的NPC角色，例如：一个神秘的精灵法师...",
    ),
}


# ==================== 工作流步骤 ====================

@dataclass(frozen=True)
class WorkflowStep:
    """
    工作流节点在 UI 上的呈现。

    :param node: 工作流节点名。
    :param completed_label: 节点完成后加入「已完成步骤」的文案。
    :param pending_label: 节点完成后展示的下一步加载文案；None 表示流程结束。
    """
    node: str
    completed_label: str
    pending_label: Optional[str]


#: 按执行顺序声明；两份文案合并在一张表里，避免维护平行字典时不同步
WORKFLOW_STEPS: Tuple[WorkflowStep, ...] = (
    WorkflowStep("search_worldview", "检索世界观资料", "检索模型风格资料"),
    WorkflowStep("search_model_style", "检索模型风格资料", "检索相关背景资料"),
    WorkflowStep("search_relevent_lore", "检索相关背景资料", "生成NPC角色档案"),
    WorkflowStep("generate_npc_json_generator", "生成NPC角色档案", "评估角色档案质量"),
    WorkflowStep("generate_npc_json_evaluator", "评估角色档案", "保存角色档案"),
    WorkflowStep("save_npc_json", "保存角色档案", "生成图片描述词"),
    WorkflowStep("generate_npc_image_prompt", "生成图片描述词", "生成NPC角色图片"),
    WorkflowStep("generate_npc_image_generator", "生成NPC角色图片", "评估角色图片"),
    WorkflowStep("generate_npc_image_evaluator", "评估角色图片", "保存角色图片"),
    WorkflowStep("save_npc_image", "保存角色图片", "生成3D模型"),
    WorkflowStep("generate_npc_model", "生成3D模型", None),
)

WORKFLOW_STEPS_BY_NODE: Dict[str, WorkflowStep] = {step.node: step for step in WORKFLOW_STEPS}

#: 流程启动时展示的第一条加载文案
FIRST_STEP_LABEL = WORKFLOW_STEPS[0].completed_label

WELCOME_MESSAGE = """
👋 **欢迎使用 NPC 角色生成器！**

我可以帮助你：
- 💬 **对话模式**: 自由讨论游戏角色设计的想法（支持上下文记忆）
- 🔄 **工作流模式**: 自动生成完整的NPC角色（包括档案、图片和3D模型）

在上方选择模式，然后在下方输入框输入你的需求开始吧！
"""

USAGE_MESSAGE = """
**💬 大模型对话模式**
- 与AI自由对话
- 讨论角色设计想法
- 支持上下文记忆
- 可以进行多轮对话

**🔄 NPC生成工作流模式**
- 输入角色描述
- 自动检索背景资料
- 生成角色档案
- 生成角色图片
- 生成3D模型
- 全程显示进度
"""


# ==================== 页面 ====================

class NpcGenerationPage(BasePage):
    """NPC 角色生成页面。"""

    page_title = "NPC角色生成器"
    page_icon = "🎮"
    layout = "wide"
    custom_css = NPC_PAGE_CSS

    #: 会话被清空时需要重置的 state 键
    _CONVERSATION_KEYS = (
        "messages",
        "llm_history",
        "thread_id",
        "model_progress",
        "model_progress_text",
    )

    def session_defaults(self) -> Mapping[str, Callable[[], Any]]:
        return {
            # 消息历史
            "messages": list,
            # 当前模式
            "chat_mode": lambda: ChatMode.LLM.value,
            # 对话线程ID（用于记忆功能）
            "thread_id": lambda: str(uuid.uuid4())[:8],
            # LLM 对话历史（LangChain Message 格式）
            "llm_history": lambda: [SystemMessage(content=prompts.CHAT_SYSTEM)],
            # 工作流实例（延迟初始化）
            "workflow": lambda: None,
            # 是否正在生成
            "is_generating": lambda: False,
            # 3D模型生成进度与状态文本
            "model_progress": int,
            "model_progress_text": str,
        }

    # ==================== 依赖 ====================

    @staticmethod
    def _llm_model():
        """获取 LLM 模型实例。"""
        return init_chat_model(model=settings.models.chat_model)

    def _workflow(self) -> GenerateNpcWorkflow:
        """获取工作流实例（延迟初始化并缓存在 session 中）。"""
        if self.state.workflow is None:
            self.state.workflow = GenerateNpcWorkflow()
        return self.state.workflow

    @property
    def _mode(self) -> str:
        return self.state.chat_mode

    # ==================== 渲染 ====================

    def render(self) -> None:
        self._render_sidebar()

        st.title("🎮 NPC角色生成器")
        self._render_mode_selector()
        st.divider()

        self._render_welcome()
        self._render_history()

        prompt = st.chat_input(
            placeholder=MODES[self._mode].input_placeholder,
            disabled=self.state.is_generating,
        )
        if prompt:
            self._handle_prompt(prompt)

    def _render_sidebar(self) -> None:
        with st.sidebar:
            st.header("🎮 NPC角色生成器")
            st.divider()

            st.caption(f"会话ID: `{self.state.thread_id}`")
            st.info(f"当前模式: {MODES[self._mode].display_name}")

            if st.button("🗑️ 清空对话", use_container_width=True):
                self.reset_session_state(*self._CONVERSATION_KEYS)
                st.rerun()

            st.divider()
            with st.expander("📖 使用说明", expanded=False):
                st.markdown(USAGE_MESSAGE)

    def _render_mode_selector(self) -> None:
        """模式选择区域（放在标题下方居中）"""
        _, center, _ = st.columns([2, 3, 2])
        with center:
            options = list(MODES.keys())
            selected = st.selectbox(
                "🎯 选择模式",
                options=options,
                format_func=lambda key: f"{MODES[key].display_name} - {MODES[key].description}",
                index=options.index(self._mode) if self._mode in options else 0,
                disabled=self.state.is_generating,
                key="mode_selector",
            )
            if selected != self.state.chat_mode:
                self.state.chat_mode = selected
                st.rerun()

    def _render_welcome(self) -> None:
        if not self.state.messages:
            with st.chat_message("assistant"):
                st.markdown(WELCOME_MESSAGE)

    def _render_history(self) -> None:
        for message in self.state.messages:
            render_message(message["role"], message["content"], message.get("image_base64"))

    # ==================== 输入处理 ====================

    def _handle_prompt(self, prompt: str) -> None:
        """处理一次用户输入：落历史 -> 按模式生成 -> 重跑页面。"""
        self._append_message("user", prompt)
        render_message("user", prompt)

        self.state.is_generating = True
        try:
            if self._mode == ChatMode.LLM.value:
                self._run_llm_mode(prompt)
            else:
                self._run_workflow_mode(prompt)
        finally:
            self.state.is_generating = False

        st.rerun()

    def _append_message(self, role: str, content: str, image_base64: Optional[str] = None) -> None:
        """把一条消息追加到展示用的历史中。"""
        message: Dict[str, Any] = {"role": role, "content": content}
        if image_base64:
            message["image_base64"] = image_base64
        self.state.messages.append(message)

    # ==================== 大模型对话模式 ====================

    def _stream_llm_response(self, prompt: str) -> Generator[str, None, None]:
        """流式生成大模型回复，并维护 LangChain 消息历史。"""
        model = self._llm_model()
        history = self.state.llm_history
        history.append(HumanMessage(content=prompt))

        chunks: List[str] = []
        try:
            for chunk in model.stream(history):
                content = getattr(chunk, "content", None)
                if not content:
                    continue
                chunks.append(content)
                yield content
                time.sleep(settings.ui.stream_delay)
            history.append(AIMessage(content="".join(chunks)))
        except Exception as e:
            logger.error(f"LLM 调用错误: {e}")
            error_msg = f"抱歉，生成回复时出现错误: {str(e)}"
            history.append(AIMessage(content=error_msg))
            yield error_msg

    def _run_llm_mode(self, prompt: str) -> None:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            with placeholder.container():
                render_loading_status("思考")

            parts: List[str] = []
            for chunk in self._stream_llm_response(prompt):
                parts.append(chunk)
                placeholder.markdown("".join(parts) + "▌")

            full_response = "".join(parts)
            placeholder.markdown(full_response)

        self._append_message("assistant", full_response)

    # ==================== 工作流模式 ====================

    def _run_workflow_mode(self, prompt: str) -> None:
        with st.chat_message("assistant"):
            slots = _WorkflowSlots.create()
            try:
                final_state = _WorkflowRunner(self._workflow(), slots).run(prompt)
            except Exception as e:
                logger.exception(f"工作流执行错误: {e}")
                slots.clear_transient()
                slots.progress.empty()
                error_msg = (
                    f"❌ 生成过程中出现错误:\n```\n{str(e)}\n```\n\n请检查日志获取详细信息。"
                )
                slots.json_result.markdown(error_msg)
                self._append_message("assistant", error_msg)
                return

            slots.clear_transient()
            if final_state.get("npc_json"):
                slots.json_result.markdown(
                    "### ✨ NPC角色生成完成！\n" + format_npc_json_result(final_state["npc_json"])
                )
            slots.final_result.markdown(format_final_result(final_state))

            self._append_message(
                "assistant",
                format_completed_result(final_state),
                image_base64=final_state.get("npc_image_base64"),
            )


@dataclass
class _WorkflowSlots:
    """工作流模式用到的一组 Streamlit 占位符。"""
    status: Any
    progress: Any
    json_result: Any
    image: Any
    #: 预留给 3D 模型进度条。工作流通过 MODEL_PROGRESS_EVENT 自定义事件派发进度，
    #: 但本页当前用 astream（节点级）而非 astream_events（事件级）驱动，
    #: 因此暂无进度数据写入；改用事件流后可在此渲染 render_model_progress。
    model_progress: Any
    final_result: Any

    @classmethod
    def create(cls) -> "_WorkflowSlots":
        return cls(
            status=st.empty(),
            progress=st.empty(),
            json_result=st.empty(),
            image=st.empty(),
            model_progress=st.empty(),
            final_result=st.empty(),
        )

    def clear_transient(self) -> None:
        """清除只在运行期间有意义的占位符。"""
        self.status.empty()
        self.model_progress.empty()


class _WorkflowRunner:
    """
    驱动工作流并把节点事件翻译成页面更新。

    与页面解耦：只依赖工作流对象和一组占位符，便于单独调整展示策略。
    """

    def __init__(self, workflow: GenerateNpcWorkflow, slots: _WorkflowSlots):
        self._workflow = workflow
        self._slots = slots
        self._state: Dict[str, Any] = {}
        self._completed: List[str] = []
        self._json_shown = False
        self._image_shown = False

    def run(self, prompt: str) -> Dict[str, Any]:
        """同步执行工作流，返回累积的最终状态。"""
        with self._slots.status.container():
            render_loading_status(FIRST_STEP_LABEL)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._consume(prompt))
        finally:
            loop.close()

    async def _consume(self, prompt: str) -> Dict[str, Any]:
        async for update in self._workflow.astream(prompt):
            if not update:
                continue
            node_name = next(iter(update))
            node_data = update[node_name]
            if isinstance(node_data, dict):
                self._state.update(node_data)

            self._on_node_completed(node_name)
            logger.info(f"工作流节点完成: {node_name}")
        return self._state

    def _on_node_completed(self, node_name: str) -> None:
        """节点完成后刷新步骤条、加载文案，并按需提前展示中间产物。"""
        step = WORKFLOW_STEPS_BY_NODE.get(node_name)
        if step is None:
            return

        self._completed.append(step.completed_label)
        with self._slots.progress.container():
            render_progress_steps(self._completed)

        if step.pending_label:
            with self._slots.status.container():
                render_loading_status(step.pending_label)

        self._show_intermediate_result(node_name)

    def _show_intermediate_result(self, node_name: str) -> None:
        """档案 / 图片一旦落盘就先行展示，不必等整个流程跑完。"""
        if node_name == "save_npc_json" and not self._json_shown:
            npc_json = self._state.get("npc_json")
            if npc_json:
                self._slots.json_result.markdown("### ✨ NPC角色生成中...\n")
                self._slots.json_result.markdown(format_npc_json_result(npc_json))
                self._json_shown = True

        if node_name == "save_npc_image" and not self._image_shown:
            npc_image_base64 = self._state.get("npc_image_base64")
            if npc_image_base64:
                self._image_shown = render_base64_image(
                    self._slots.image, npc_image_base64, caption="🖼️ 生成的角色图片"
                )

