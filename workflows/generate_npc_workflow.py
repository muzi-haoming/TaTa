"""
NPC 生成工作流

流程：检索参考资料 -> 生成角色档案 -> 自动评估 + 人工审核 -> 落盘
      -> 生成图片提示词 -> 人工审核 -> 生成图片 -> 自动评估 + 人工审核 -> 落盘
      -> 生成 3D 模型

通用节点（参考资料 / 生成 / 评估 / 人工审核 / 落盘 / 路由）由 :class:`workflows.base.LlmWorkflow`
提供，本模块只声明各节点的差异（提示词、字段、结构化输出）以及图的连线。
"""
import asyncio
import base64
from typing import Any, Dict, Optional, Tuple, Type

from google import genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from config import settings
from core import (
    EvaluatorResponseStructure,
    ImageGeneratePromptResponseStructure,
    NPCGenerationResponseStructure,
    asearch_lore,
    prompts,
)
from services import TERMINAL_STATUSES, meshy_service
from utils import logger

from .base import (
    ACCEPTED,
    REJECTED,
    EvaluatorSpec,
    GeneratorSpec,
    LlmWorkflow,
    ReferenceSpec,
    ReviewSpec,
    SaveSpec,
    Section,
)
from .state import NpcState, initial_state

#: 3D 模型生成进度事件名（前端通过 ``astream_events`` 消费）
MODEL_PROGRESS_EVENT = "generate_npc_model_progress"

#: 生成图片时使用的图片格式（MIME 子类型与文件扩展名同源）
_IMAGE_MIME_SUBTYPE = "jpeg"
_IMAGE_SUFFIX = f".{_IMAGE_MIME_SUBTYPE}"

#: 参与提示词的公共资料段
_WORLDVIEW = Section("worldview", "worldview")
_MODEL_STYLE = Section("model_style", "model_style")
_RELEVENT_LORE = Section("npc_relevent_lore", "npc_relevent_lore")
_NPC_JSON = Section("npc_json", "npc_json")
# 注意：标签沿用历史拼写 "promot"，改动即等于改动提示词，保持原样以免影响生成效果
_PROMPT = Section("promot", "prompt")

_LORE_SECTIONS: Tuple[Section, ...] = (_WORLDVIEW, _MODEL_STYLE, _RELEVENT_LORE)


# ====================
# 节点声明（纯数据，与实例无关）
# ====================

REFERENCE_SPECS: Tuple[ReferenceSpec, ...] = (
    ReferenceSpec("查询世界观资料", "worldview", settings.paths.worldview_file),
    ReferenceSpec("查询模型风格资料", "model_style", settings.paths.model_style_file),
)

NPC_JSON_GENERATOR_SPEC = GeneratorSpec(
    log_label="生成NPC角色档案",
    result_label="NPC json档案",
    schema=NPCGenerationResponseStructure,
    target_key="npc_json",
    generate_prompt=prompts.NPC_JSON_GENERATE,
    refine_prompt=prompts.NPC_JSON_REFINE,
    sections=(_PROMPT, *_LORE_SECTIONS),
    refine_sections=(_NPC_JSON, Section("feedback", "npc_json_feedback")),
    extract=lambda response: response.model_dump(),
)

NPC_JSON_EVALUATOR_SPEC = EvaluatorSpec(
    log_label="NPC档案评估",
    schema=EvaluatorResponseStructure,
    system_prompt=prompts.NPC_JSON_EVALUATE,
    sections=(_PROMPT, *_LORE_SECTIONS, _NPC_JSON),
    flag_key="npc_json_is_ok",
    feedback_key="npc_json_feedback",
)

NPC_IMAGE_PROMPT_GENERATOR_SPEC = GeneratorSpec(
    log_label="生成用于生成NPC图片的prompt",
    result_label="生成NPC图片的prompt",
    schema=ImageGeneratePromptResponseStructure,
    target_key="npc_image_prompt",
    generate_prompt=prompts.NPC_IMAGE_PROMPT_GENERATE,
    refine_prompt=prompts.NPC_IMAGE_PROMPT_REFINE,
    sections=(*_LORE_SECTIONS, _NPC_JSON),
    refine_sections=(
        Section("npc_image_prompt", "npc_image_prompt"),
        Section("feedback", "npc_image_prompt_feedback"),
    ),
    extract=lambda response: response.prompt,
)

NPC_IMAGE_EVALUATOR_SPEC = EvaluatorSpec(
    log_label="NPC图片评估",
    schema=EvaluatorResponseStructure,
    system_prompt=prompts.NPC_IMAGE_EVALUATE,
    sections=_LORE_SECTIONS,
    flag_key="npc_image_is_ok",
    feedback_key="npc_image_feedback",
    image_key="npc_image_base64",
)

#: 人工审核节点：节点名 -> 声明
REVIEW_SPECS: Dict[str, ReviewSpec] = {
    "generate_npc_json_human_evaluation": ReviewSpec(
        log_label="NPC档案人工评估",
        question="是否满意目前生成的NPC角色信息?",
        detail_key="npc_json",
        flag_key="npc_json_is_ok",
        feedback_key="npc_json_feedback",
    ),
    "generate_npc_image_prompt_human_evaluation": ReviewSpec(
        log_label="NPC图片prompt人工评估",
        question="是否满意目前生成的NPC生成图片的提示词?",
        detail_key="npc_image_prompt",
        flag_key="npc_image_prompt_is_ok",
        feedback_key="npc_image_prompt_feedback",
    ),
    "generate_npc_image_human_evaluation": ReviewSpec(
        log_label="NPC图片人工评估",
        question="是否满意目前生成的NPC图片信息?",
        detail_key="npc_image_base64",
        flag_key="npc_image_is_ok",
        feedback_key="npc_image_feedback",
    ),
}


class GenerateNpcWorkflow(LlmWorkflow):
    """NPC 角色生成工作流（档案 + 图片 + 3D 模型）。"""

    state_schema: Type = NpcState
    input_key = "prompt"
    workspace_dir = settings.paths.npc_generation_data
    graph_image_name = "workflows.png"

    # Vertex AI 侧的可重试异常
    retry_on = (
        ResourceExhausted,   # 429 频率限制
        ServiceUnavailable,  # 503 服务器过载
        ConnectionError,     # 网络掉线
        TimeoutError,        # 请求超时
    )

    def __init__(self, thread_id: Optional[str] = None, **kwargs: Any):
        self._optimize_image_model = init_chat_model(
            model=settings.models.image_model,
            streaming=False,
            model_kwargs={
                "response_modalities": [2],
                "image_generation_config": {
                    "aspect_ratio": "16:9",
                    "output_mime_type": "image/jpeg",
                },
            },
        )
        self._mesh_service = meshy_service
        super().__init__(thread_id=thread_id, **kwargs)

    # ====================
    # 节点声明（依赖实例的部分）
    # ====================
    def _save_specs(self) -> Dict[str, SaveSpec]:
        """落盘节点声明；``writer`` 绑定到本实例的文件沙箱。"""
        return {
            "save_npc_json": SaveSpec(
                log_label="保存NPC角色档案",
                flag_key="npc_json_is_ok",
                value_key="npc_json",
                target_key="npc_json_path",
                suffix=".json",
                writer=self._fs.write_json,
            ),
            "save_npc_image": SaveSpec(
                log_label="保存NPC图片",
                flag_key="npc_image_is_ok",
                value_key="npc_image_base64",
                target_key="npc_image_path",
                suffix=_IMAGE_SUFFIX,
                writer=self._fs.write_image,
            ),
        }

    # ====================
    # 专有节点
    # ====================
    async def _node_search_relevent_lore(self, state: NpcState) -> Dict[str, Any]:
        """查询相关背景资料（向量检索）"""
        self._log_step("查询相关背景资料")

        npc_relevent_lore = state["npc_relevent_lore"]
        if not npc_relevent_lore:
            npc_relevent_lore = await asearch_lore(state["prompt"])

        logger.info(f"\n相关背景资料: \n{self._preview(npc_relevent_lore)}")
        return {"npc_relevent_lore": npc_relevent_lore}

    async def _node_generate_npc_image_generator(self, state: NpcState) -> Dict[str, Any]:
        """生成NPC图片：首次走 Imagen 文生图，已有图片则走多模态图生图优化"""
        self._log_step("生成NPC图片")

        if not state["npc_image_base64"]:
            npc_image_base64 = await self._generate_image(state["npc_image_prompt"])
        else:
            npc_image_base64 = await self._refine_image(
                state["npc_image_base64"], state["npc_image_feedback"]
            )

        logger.info(f"生成NPC图片完成: {self._preview(npc_image_base64, 50)}")
        return {"npc_image_base64": npc_image_base64}

    async def _generate_image(self, image_prompt: str) -> str:
        """调用 Imagen 文生图，返回 base64。"""
        models_config = self._settings.models
        google_cloud = self._settings.google_cloud

        def _call_imagen():
            client = genai.Client(
                vertexai=True,
                project=google_cloud.project,
                location=google_cloud.location,
            )
            return client.models.generate_images(
                model=models_config.imagen_model,
                prompt=image_prompt,
                config={
                    "aspect_ratio": "1:1",
                    "output_mime_type": f"image/{_IMAGE_MIME_SUBTYPE}",
                    "number_of_images": models_config.imagen_number_of_images,
                },
            )

        response = await asyncio.to_thread(_call_imagen)
        return base64.b64encode(response.generated_images[0].image.image_bytes).decode("utf-8")

    async def _refine_image(self, image_base64: str, feedback: str) -> str:
        """带反馈的图生图优化，返回 base64。"""
        model = self._optimize_image_model.bind(system_prompt=prompts.NPC_IMAGE_REFINE)
        response = await model.ainvoke([HumanMessage(content=[
            {"type": "text", "text": f"[feedback]: {feedback}"},
            self._image_block(image_base64, _IMAGE_MIME_SUBTYPE),
        ])])

        image_url = response.content[0].get("image_url").get("url")
        return image_url.split(",", 1)[1] if "," in image_url else image_url

    async def _node_generate_npc_model(self, state: NpcState) -> Dict[str, Any]:
        """生成NPC 3D模型：提交 Meshy 任务，监听进度，成功后下载 glb"""
        self._log_step("生成NPC模型")

        image_data_uri = f"data:image/{_IMAGE_MIME_SUBTYPE};base64,{state['npc_image_base64']}"
        task_id = self._mesh_service.create_image_to_3d_task(image_data_uri)
        logger.info(f"3D模型生成任务ID: {task_id}")

        glb_url = await self._watch_model_task(task_id)
        if not glb_url:
            logger.warning("3D模型未生成成功，跳过下载")
            return {"npc_model_path": None}

        npc_name = state["npc_json"].get("name")
        saved_path = await self._fs.download_file(f"{npc_name}/{npc_name}.glb", glb_url)
        logger.info(f"\n保存路径: \n{saved_path}")
        return {"npc_model_path": saved_path}

    async def _watch_model_task(self, task_id: str) -> Optional[str]:
        """监听 3D 模型任务进度并派发进度事件，返回成功时的 glb 下载地址。"""
        progress = 0
        for update in self._mesh_service.image_to_3d.listen(task_id):
            status = update.get("status", "UNKNOWN")
            if status in TERMINAL_STATUSES:
                logger.info(f"3D模型生成状态 [STATUS] Task {status}")
                return update.get("model_urls", {}).get("glb") if status == "SUCCEEDED" else None

            current_progress = update.get("progress", 0)
            if current_progress != progress:
                progress = current_progress
                logger.info(f"3D模型生成进度 [STATUS] Task {progress}%")
                # 通过自定义事件把进度透传给前端
                await adispatch_custom_event(
                    MODEL_PROGRESS_EVENT,
                    {"message": "正在生成模型", "percent": progress},
                )
        return None

    # ====================
    # 构建流程图
    # ====================
    def _build_graph(self) -> StateGraph:
        graph = StateGraph(self.state_schema)
        retry_policy = self.build_retry_policy()
        saves = self._save_specs()
        worldview_spec, model_style_spec = REFERENCE_SPECS

        # (节点名, 动作, 是否需要重试)
        nodes = (
            ("initialize", self.make_initialize_node(lambda: initial_state(self.state_schema)), False),
            ("search_worldview", self.make_reference_node(worldview_spec), False),
            ("search_model_style", self.make_reference_node(model_style_spec), False),
            ("search_relevent_lore", self._node_search_relevent_lore, False),
            ("generate_npc_json_generator", self.make_generator_node(NPC_JSON_GENERATOR_SPEC), True),
            ("generate_npc_json_evaluator", self.make_evaluator_node(NPC_JSON_EVALUATOR_SPEC), True),
            ("generate_npc_json_human_evaluation",
             self.make_review_node(REVIEW_SPECS["generate_npc_json_human_evaluation"]), False),
            ("save_npc_json", self.make_save_node(saves["save_npc_json"]), False),
            ("generate_npc_image_prompt", self.make_generator_node(NPC_IMAGE_PROMPT_GENERATOR_SPEC), True),
            ("generate_npc_image_prompt_human_evaluation",
             self.make_review_node(REVIEW_SPECS["generate_npc_image_prompt_human_evaluation"]), False),
            ("generate_npc_image_generator", self._node_generate_npc_image_generator, True),
            ("generate_npc_image_evaluator", self.make_evaluator_node(NPC_IMAGE_EVALUATOR_SPEC), True),
            ("generate_npc_image_human_evaluation",
             self.make_review_node(REVIEW_SPECS["generate_npc_image_human_evaluation"]), False),
            ("save_npc_image", self.make_save_node(saves["save_npc_image"]), False),
            ("generate_npc_model", self._node_generate_npc_model, False),
        )
        for name, action, retriable in nodes:
            graph.add_node(name, action, **({"retry_policy": retry_policy} if retriable else {}))

        # 线性连接
        linear_edges = (
            (START, "initialize"),
            ("initialize", "search_worldview"),
            ("search_worldview", "search_model_style"),
            ("search_model_style", "search_relevent_lore"),
            ("search_relevent_lore", "generate_npc_json_generator"),
            ("generate_npc_json_generator", "generate_npc_json_evaluator"),
            ("save_npc_json", "generate_npc_image_prompt"),
            ("generate_npc_image_prompt", "generate_npc_image_prompt_human_evaluation"),
            ("generate_npc_image_generator", "generate_npc_image_evaluator"),
            ("save_npc_image", "generate_npc_model"),
            ("generate_npc_model", END),
        )
        for source, target in linear_edges:
            graph.add_edge(source, target)

        # 条件连接：(来源节点, 判定字段, 通过去向, 驳回去向)
        conditional_edges = (
            ("generate_npc_json_evaluator", "npc_json_is_ok",
             "generate_npc_json_human_evaluation", "generate_npc_json_generator"),
            ("generate_npc_json_human_evaluation", "npc_json_is_ok",
             "save_npc_json", "generate_npc_json_generator"),
            ("generate_npc_image_prompt_human_evaluation", "npc_image_prompt_is_ok",
             "generate_npc_image_generator", "generate_npc_image_prompt"),
            ("generate_npc_image_evaluator", "npc_image_is_ok",
             "generate_npc_image_human_evaluation", "generate_npc_image_generator"),
            ("generate_npc_image_human_evaluation", "npc_image_is_ok",
             "save_npc_image", "generate_npc_image_generator"),
        )
        for source, flag_key, accepted, rejected in conditional_edges:
            graph.add_conditional_edges(
                source=source,
                path=self.make_router(flag_key),
                path_map={ACCEPTED: accepted, REJECTED: rejected},
            )

        return graph
