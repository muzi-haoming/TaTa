import asyncio
import base64
from typing import TypedDict

from google import genai
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Command, interrupt

from config import settings
from core import create_retriever, NPCGenerationResponseStructure, EvaluatorResponseStructure, ImageGeneratePromptResponseStructure
from services import meshy_service
from utils import FileUtil, logger


class State(TypedDict):
    prompt: str
    worldview: str
    model_style: str
    npc_relevent_lore: str
    npc_json: dict
    npc_json_is_ok: bool
    npc_json_feedback: str
    npc_json_path: str
    npc_image_prompt: str
    npc_image_prompt_is_ok: bool
    npc_image_prompt_feedback: str
    npc_image_base64: str
    npc_image_is_ok: bool
    npc_image_feedback: str
    npc_image_path: str
    npc_model_path: str


class GenerateNpcWorkflow:
    def __init__(self, thread_id: str = "959"):
        # 环境变量通过config模块自动设置
        self._thread_id = thread_id
        self._settings = settings
        self._fs = FileUtil(self._settings.paths.npc_generation_data)
        self._retriever = create_retriever()
        self._model = init_chat_model(model=self._settings.models.chat_model)
        self._optimize_image_model = init_chat_model(model=self._settings.models.image_model)
        self._3d_model = meshy_service

        self.app = self._build_graph()

    # ====================
    # Nodes
    # ====================
    async def _node_initialize(self, state: State):
        """初始化节点"""
        logger.info("\n===========================\n初始化节点")

        default_state = {
            "prompt": "",
            "worldview": "",
            "model_style": "",
            "npc_relevent_lore": "",
            "npc_json": {},
            "npc_json_is_ok": False,
            "npc_json_feedback": "",
            "npc_json_path": "",
            "npc_image_prompt": "",
            "npc_image_prompt_is_ok": False,
            "npc_image_prompt_feedback": "",
            "npc_image_base64": "",
            "npc_image_is_ok": False,
            "npc_image_feedback": "",
            "npc_image_path": "",
            "npc_model_path": ""
        }

        state = {**default_state, **state}
        logger.info(f"\n初始state: \n{state}")

        return state

    async def _node_search_worldview(self, state: State):
        """查询世界观资料"""
        logger.info("\n===========================\n查询世界观资料")

        worldview = state["worldview"]
        if not worldview:
            worldview = await asyncio.to_thread(self._fs.read_text, self._settings.paths.worldview_file)

        logger.info(f"\n世界观: \n{worldview[:100]}")

        return {"worldview": worldview}

    async def _node_search_model_style(self, state: State):
        """查询模型风格资料"""
        logger.info("\n===========================\n查询模型风格资料")

        model_style = state["model_style"]
        if not model_style:
            model_style = await asyncio.to_thread(self._fs.read_text, self._settings.paths.model_style_file)

        logger.info(f"\n模型风格: \n{model_style[:100]}")

        return {"model_style": model_style}

    async def _node_search_relevent_lore(self, state: State):
        """查询相关背景资料"""
        logger.info("\n===========================\n查询相关背景资料")

        prompt = state["prompt"]
        npc_relevent_lore = state["npc_relevent_lore"]
        if not npc_relevent_lore:
            docs = await self._retriever.ainvoke(prompt)
            npc_relevent_lore = f"{"\n\n".join(doc.page_content for doc in docs)}"

        logger.info(f"\n相关背景资料: \n{npc_relevent_lore[:100]}")

        return {"npc_relevent_lore": npc_relevent_lore}

    async def _node_generate_npc_json_generator(self, state: State):
        """生成NPC角色档案"""
        logger.info("\n===========================\n生成NPC角色档案")
        npc_json_is_ok = state["npc_json_is_ok"]
        if not npc_json_is_ok:
            system_prompt = ("你是一个资深的游戏设计师,精通游戏角色档案设计.\n\n"
                             "目标是结合世界观[worldview],模型风格[model_style]和npc背景资料[npc_relevent_lore],根据输入[prompt]生成一个角色档案.")
        else:
            system_prompt = ("你是一个资深的游戏设计师,精通游戏角色档案设计.\n\n"
                             "目标是结合世界观[worldview],模型风格[model_style]和npc背景资料[npc_relevent_lore],根据当前生成的npc档案[npc_json],输入[prompt]和反馈[feedback]完善npc档案.")

        generate_npc_json_model = (self._model
                                   .with_structured_output(NPCGenerationResponseStructure)
                                   .bind(system_prompt=system_prompt))

        if npc_json_is_ok is None or not npc_json_is_ok:
            response = await generate_npc_json_model.ainvoke(f"[promot]: {state["prompt"]}\n\n"
                                                      f"[worldview]: {state["worldview"]}\n\n"
                                                      f"[model_style]: {state["model_style"]}\n\n"
                                                      f"[npc_relevent_lore]: {state["npc_relevent_lore"]}")
        else:
            response = await generate_npc_json_model.ainvoke(f"[promot]: {state["prompt"]}\n\n"
                                                      f"[worldview]: {state["worldview"]}\n\n"
                                                      f"[model_style]: {state["model_style"]}\n\n"
                                                      f"[npc_relevent_lore]: {state["npc_relevent_lore"]}\n\n"
                                                      f"[npc_json]: {state["npc_json"]}\n\n"
                                                      f"[feedback]: {state["npc_json_feedback"]}")
        npc_json = response.model_dump()

        logger.info(f"\nNPC json档案: \n{npc_json}")

        return {"npc_json": npc_json}

    async def _node_generate_npc_json_evaluator(self, state: State):
        """NPC档案评估"""
        logger.info("\n===========================\nNPC档案评估")

        system_prompt = ("你是一个资深的游戏设计师,精通游戏角色档案设计.\n\n"
                         "目标是结合输入[prompt],世界观[worldview],模型风格[model_style]和npc背景资料[npc_relevent_lore],评判角色档案[npc_json]是否符合以下标准:\n"
                         "\t - 必须完美符合世界观[worldview]\n"
                         "\t - 必须完美符合模型风格[model_style]\n"
                         "\t - 必须完美符合npc背景资料[npc_relevent_lore]\n\n"
                         "如果不符合标准,请给出具体的修改意见.")
        generate_npc_json_model = (self._model
                                   .with_structured_output(EvaluatorResponseStructure)
                                   .bind(system_prompt=system_prompt))

        response = await generate_npc_json_model.ainvoke(f"[promot]: {state["prompt"]}\n\n"
                                                  f"[worldview]: {state["worldview"]}\n\n"
                                                  f"[model_style]: {state["model_style"]}\n\n"
                                                  f"[npc_relevent_lore]: {state["npc_relevent_lore"]}\n\n"
                                                  f"[npc_json]: {state["npc_json"]}")

        logger.info(f"\nNPC档案评估: \n{response}")

        return {"npc_json_is_ok": response.is_ok, "npc_json_feedback": response.feedback}

    async def _node_generate_npc_json_human_evaluation(self, state: State):
        """NPC档案人工评估"""
        response = interrupt({
            "question": "是否满意目前生成的NPC角色信息?",
            "details": state["npc_json"]
        })

        is_ok = response["is_ok"]
        feedback = response["feedback"]
        logger.info(f"\n用户对npc_json的确认信息: \n{response}")

        return {"npc_json_is_ok": is_ok, "npc_json_feedback": feedback}


    async def _node_save_npc_json(self, state: State):
        """保存NPC角色档案"""
        logger.info("\n===========================\n保存NPC角色档案")

        if not state["npc_json_is_ok"]:
            return None

        npc_json = state["npc_json"]
        npc_json_path = f"{npc_json.get("name")}/{npc_json.get("name")}.json"
        direct_path = await asyncio.to_thread(self._fs.write_json, npc_json_path, npc_json)

        logger.info(f"\n保存路径: \n{direct_path}")

        return {"npc_json_path": direct_path}

    async def _node_generate_npc_image_prompt(self, state: State):
        """生成用于生成NPC图片的prompt"""
        logger.info("\n===========================\n生成用于生成NPC图片的prompt")

        npc_image_prompt_is_ok = state["npc_image_prompt_is_ok"]
        npc_image_prompt_feedback = state["npc_image_prompt_feedback"]

        if not npc_image_prompt_is_ok:
            system_prompt = ("你是一个精通图片生成大模型的资深的游戏设计师,精通游戏角色图片设计.\n\n"
                             "目标是结合世界观[worldview],模型风格[model_style],npc背景资料[npc_relevent_lore]和npc档案[npc_json],生成一小段可以借助图片生成大模型来生成角色图片的**中文提示词**.")
        else:
            system_prompt = ("你是一个精通图片生成大模型的资深的游戏设计师,精通游戏角色图片设计.\n\n"
                             "目标是结合世界观[worldview],模型风格[model_style],npc背景资料[npc_relevent_lore]和npc档案[npc_json],基于已经生成的用于生成角色图片的提示词[npc_image_prompt]和反馈[feedback],优化提示词[npc_image_prompt].")

        generate_npc_image_prompt_model = (self._model
                                           .with_structured_output(ImageGeneratePromptResponseStructure)
                                           .bind(system_prompt=system_prompt))

        if not npc_image_prompt_is_ok:
            response = await generate_npc_image_prompt_model.ainvoke(f"[worldview]: {state["worldview"]}\n\n"
                                                                     f"[model_style]: {state["model_style"]}\n\n"
                                                                     f"[npc_relevent_lore]: {state["npc_relevent_lore"]}\n\n"
                                                                     f"[npc_json]: {state["npc_json"]}")
        else:
            response = await generate_npc_image_prompt_model.ainvoke(f"[worldview]: {state["worldview"]}\n\n"
                                                                     f"[model_style]: {state["model_style"]}\n\n"
                                                                     f"[npc_relevent_lore]: {state["npc_relevent_lore"]}\n\n"
                                                                     f"[npc_json]: {state["npc_json"]}\n\n"
                                                                     f"[npc_image_prompt]: {state["npc_image_prompt"]}\n\n"
                                                                     f"[feedback]: {state["npc_image_prompt_feedback"]}")
        npc_image_prompt = response.prompt

        logger.info(f"\n生成NPC图片的prompt: \n{npc_image_prompt}")

        return {"npc_image_prompt": npc_image_prompt}

    async def _node_generate_npc_image_prompt_human_evaluation(self, state: State):
        """NPC图片prompt人工评估"""
        response = interrupt({
            "question": "是否满意目前生成的NPC生成图片的提示词?",
            "details": state["npc_image_prompt"]
        })

        is_ok = response["is_ok"]
        feedback = response["feedback"]
        logger.info(f"\n用户对npc_json的确认信息: \n{response}")

        return {"npc_image_prompt_is_ok": is_ok, "npc_image_prompt_feedback": feedback}

    async def _node_generate_npc_image_generator(self, state: State):
        """生成NPC图片"""
        logger.info("\n===========================\n生成NPC图片")

        npc_image_is_ok = state["npc_image_is_ok"]
        if not npc_image_is_ok:
            def _generate_image():
                client = genai.Client(
                    vertexai=True,
                    project=self._settings.google_cloud.project,
                    location=self._settings.google_cloud.location
                )
                return client.models.generate_images(
                    model=self._settings.models.imagen_model,
                    prompt=state["npc_image_prompt"],
                    config={"number_of_images": self._settings.models.imagen_number_of_images}
                )
            
            response = await asyncio.to_thread(_generate_image)
            npc_image_bytes = response.generated_images[0].image.image_bytes
            npc_image_base64 = base64.b64encode(npc_image_bytes).decode('utf-8')
        else:
            system_prompt = ("你是一个资深的游戏设计师,精通游戏角色图片设计.\n\n"
                             "目标是根据当前生成的npc图片[npc_image_base64]和反馈[feedback]优化npc图片.")
            generate_npc_image_model = (
                self._optimize_image_model
                .bind(system_prompt=system_prompt))
            response = await generate_npc_image_model.ainvoke([HumanMessage(content=[
                {
                    "type": "text",
                    "text": "[feedback]: 给他带一个牛仔帽",
                }, {
                    "type": "image_url",
                    "image_url": {"url": state["npc_image_base64"]},
                }
            ])])
            npc_image_base64 = response.content[0].get("image_url").get("url")

        logger.info(f"\n===========================\n生成NPC图片完成")

        return {"npc_image_base64": npc_image_base64}

    async def _node_generate_npc_image_evaluator(self, state: State):
        """NPC图片评估"""
        logger.info("\n===========================\nNPC图片评估")

        system_prompt = ("你是一个精通图片生成大模型的资深的游戏设计师,精通游戏角色图片设计.\n\n"
                         "目标是结合世界观[worldview],模型风格[model_style]和npc背景资料[npc_relevent_lore],评判角色图片[npc_image_base64]是否符合以下标准:\n"
                         "\t - 必须完美符合世界观[worldview]\n"
                         "\t - 必须完美符合模型风格[model_style]\n"
                         "\t - 必须完美符合npc背景资料[npc_relevent_lore]\n"
                         "\t - 背景纯白色\n"
                         "\t - 必须是非常标准的T-Pose,胳膊必须展开,便于之后生成3D模型\n"
                         "\t - 必须是正面全身\n"
                         "\t - 50%塞尔达风格+50%宫崎骏风格\n\n"
                         "如果不符合标准,请给出具体的修改意见.")
        generate_npc_json_model = (self._model
                                   .with_structured_output(EvaluatorResponseStructure)
                                   .bind(system_prompt=system_prompt))

        response = await generate_npc_json_model.ainvoke([HumanMessage(content=[
            {
                "type": "text",
                "text": f"[worldview]: {state["worldview"]}\n\n",
            }, {
                "type": "text",
                "text": f"[model_style]: {state["model_style"]}\n\n",
            }, {
                "type": "text",
                "text": f"[npc_relevent_lore]: {state["npc_relevent_lore"]}\n\n",
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{state["npc_image_base64"]}"}
            }
        ])])

        logger.info(f"\nNPC图片评估: \n{response}")

        return {"npc_image_is_ok": response.is_ok, "npc_image_feedback": response.feedback}

    async def _node_generate_npc_image_human_evaluation(self, state: State):
        """NPC图片人工评估"""
        response = interrupt({
            "question": "是否满意目前生成的NPC图片信息?",
            "details": state["npc_image_base64"]
        })

        is_ok = response["is_ok"]
        feedback = response["feedback"]
        logger.info(f"\n用户对npc_image_base64的确认信息: \n{response}")

        return {"npc_image_is_ok": is_ok, "npc_image_feedback": feedback}

    async def _node_save_npc_image(self, state: State):
        """保存NPC图片"""
        logger.info("\n===========================\n保存NPC图片")

        if not state["npc_image_is_ok"]:
            return None

        npc_image_base64 = state["npc_image_base64"]
        npc_json = state["npc_json"]
        npc_image_path = f"{npc_json.get("name")}/{npc_json.get("name")}.jpeg"
        direct_path = await asyncio.to_thread(self._fs.write_image, npc_image_path, npc_image_base64)

        logger.info(f"\n保存路径: \n{direct_path}")

        return {"npc_image_path": direct_path}

    async def _node_generate_npc_model(self, state: State):
        """生成NPC模型"""
        logger.info("\n===========================\n生成NPC模型")
        npc_json = state["npc_json"]
        npc_image_base64 = f"data:image/jpeg;base64,{state['npc_image_base64']}"
        # 开始生成模型并获取任务ID
        task_id = self._3d_model.create_image_to_3d_task(npc_image_base64)
        logger.info(f"\n\n\n3D模型生成任务ID: {task_id}")
        # 根据任务ID获取生成进度
        progress = 0
        glb_url = ""
        for update in self._3d_model.image_to_3d.listen(task_id):
            current_progress = update.get('progress', 0)
            status = update.get('status', 'UNKNOWN')
            if status in ["SUCCEEDED", "FAILED", "CANCELED"]:
                logger.info(f"\n3D模型生成状态 [STATUS] Task {status}")
                if status == "SUCCEEDED":
                    glb_url = update.get("model_urls").get("glb")
                break
            if current_progress != progress:
                progress = current_progress
                logger.info(f"\n3D模型生成进度 [STATUS] Task {current_progress}%")
                # 使用自定义事件传递进度
                await adispatch_custom_event(
                    "generate_npc_model_progress",
                    {"message": "正在生成模型", "percent": progress}
                )

        direct_path = None
        if glb_url:
            npc_model_path = f"{npc_json.get('name')}/{npc_json.get('name')}.glb"
            direct_path = await self._fs.download_file(npc_model_path, glb_url)
        logger.info(f"\n保存路径: \n{direct_path}")

        return {"npc_model_path": direct_path}


    # ====================
    # Route
    # ====================
    def _route_generate_npc_json(self, state: State):
        """路由NPC档案生成"""
        npc_json_is_ok = state["npc_json_is_ok"]
        if not npc_json_is_ok:
            return "Rejected"
        return "Accepted"

    def _route_generate_npc_image_prompt(self, state: State):
        """路由NPC图片prompt生成"""
        npc_image_prompt_is_ok = state["npc_image_prompt_is_ok"]
        if not npc_image_prompt_is_ok:
            return "Rejected"
        return "Accepted"

    def _route_generate_npc_image(self, state: State):
        """路由NPC档案生成"""
        npc_image_is_ok = state["npc_image_is_ok"]
        if not npc_image_is_ok:
            return "Rejected"
        return "Accepted"

    # ====================
    # Build Graph
    # ====================
    def _build_graph(self):
        graph = StateGraph(State)

        # 添加节点
        graph.add_node("initialize", self._node_initialize)
        graph.add_node("search_worldview", self._node_search_worldview)
        graph.add_node("search_model_style", self._node_search_model_style)
        graph.add_node("search_relevent_lore", self._node_search_relevent_lore)
        graph.add_node("generate_npc_json_generator", self._node_generate_npc_json_generator)
        graph.add_node("generate_npc_json_evaluator", self._node_generate_npc_json_evaluator)
        graph.add_node("generate_npc_json_human_evaluation", self._node_generate_npc_json_human_evaluation)
        graph.add_node("save_npc_json", self._node_save_npc_json)
        graph.add_node("generate_npc_image_prompt", self._node_generate_npc_image_prompt)
        graph.add_node("generate_npc_image_prompt_human_evaluation", self._node_generate_npc_image_prompt_human_evaluation)
        graph.add_node("generate_npc_image_generator", self._node_generate_npc_image_generator)
        graph.add_node("generate_npc_image_evaluator", self._node_generate_npc_image_evaluator)
        graph.add_node("generate_npc_image_human_evaluation", self._node_generate_npc_image_human_evaluation)
        graph.add_node("save_npc_image", self._node_save_npc_image)
        graph.add_node("generate_npc_model", self._node_generate_npc_model)
        # 线性连接
        graph.add_edge(START, "initialize")
        graph.add_edge("initialize", "search_worldview")
        graph.add_edge("search_worldview", "search_model_style")
        graph.add_edge("search_model_style", "search_relevent_lore")
        graph.add_edge("search_relevent_lore", "generate_npc_json_generator")
        graph.add_edge("generate_npc_json_generator", "generate_npc_json_evaluator")
        graph.add_conditional_edges(
            source="generate_npc_json_evaluator",
            path=self._route_generate_npc_json,
            path_map={
                "Accepted": "generate_npc_json_human_evaluation",
                "Rejected": "generate_npc_json_generator",
            }
        )
        graph.add_conditional_edges(
            source="generate_npc_json_human_evaluation",
            path=self._route_generate_npc_json,
            path_map={
                "Accepted": "save_npc_json",
                "Rejected": "generate_npc_json_generator",
            }
        )
        graph.add_edge("save_npc_json", "generate_npc_image_prompt")
        graph.add_edge("generate_npc_image_prompt", "generate_npc_image_prompt_human_evaluation")
        graph.add_conditional_edges(
            source="generate_npc_image_prompt_human_evaluation",
            path=self._route_generate_npc_image_prompt,
            path_map={
                "Accepted": "generate_npc_image_generator",
                "Rejected": "generate_npc_image_prompt",
            }
        )
        graph.add_edge("generate_npc_image_generator", "generate_npc_image_evaluator")
        graph.add_conditional_edges(
            source="generate_npc_image_evaluator",
            path=self._route_generate_npc_image,
            path_map={
                "Accepted": "generate_npc_image_human_evaluation",
                "Rejected": "generate_npc_image_generator",
            }
        )
        graph.add_conditional_edges(
            source="generate_npc_image_human_evaluation",
            path=self._route_generate_npc_image,
            path_map={
                "Accepted": "save_npc_image",
                "Rejected": "generate_npc_image_generator",
            }
        )
        graph.add_edge("save_npc_image", "generate_npc_model")
        graph.add_edge("generate_npc_model", END)
        # 编译
        checkpointer = MemorySaver()
        app = graph.compile(checkpointer=checkpointer)
        # 画图
        # logger.info(f"\n{app.get_graph().draw_ascii()}")
        # app.get_graph().print_ascii()
        self._fs.write_bytes("workflows.png", app.get_graph(xray=True).draw_mermaid_png())

        return app

    # ====================
    # Run
    # ====================
    async def ainvoke(self, prompt: str):
        """异步运行"""
        return await self.app.ainvoke(input={"prompt": prompt}, config={"configurable": {"thread_id": self._thread_id}})

    async def ainvoke_continue(self, resume: dict):
        """继续异步运行"""
        return await self.app.ainvoke(Command(resume=resume), config={"configurable": {"thread_id": self._thread_id}})

    async def astream(self, prompt: str):
        """异步流式运行"""
        async for _ in self.app.astream(input={"prompt": prompt}, config={"configurable": {"thread_id": self._thread_id}}):
            yield _

    async def astream_continue(self, resume: dict):
        """继续异步运行"""
        async for _ in self.app.astream(Command(resume=resume), config={"configurable": {"thread_id": self._thread_id}}):
            yield _
