import asyncio
import base64
import time
from io import BytesIO
from typing import TypedDict, Callable, Optional

import pyautogui
from google import genai
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from config import settings
from core import EvaluatorResponseStructure, ImageGeneratePromptResponseStructure
from core.response_structure import PlanResponseStructure
from utils import FileUtil, logger


class State(TypedDict):
    prompt: str
    # screen_capture_base64: str
    master_plan: list[str]
    master_plan_current_step: int
    sub_plan: list[str]
    sub_plan_is_ok: list[str]
    sub_plan_feedback: list[str]


class AiAutoControlWorkflow:
    def __init__(self):
        # 环境变量通过config模块自动设置
        self._settings = settings
        self._model = init_chat_model(model=self._settings.models.chat_model)
        self._sub_plan_model = init_chat_model(model=self._settings.models.chat_model)
        self._fs = FileUtil(self._settings.paths.ai_auto_control_data)
        # self._retriever = create_retriever()
        # self._optimize_image_model = init_chat_model(model=self._settings.models.image_model)
        # self._3d_model = meshy_service

        self.app = self._build_graph()

    # ====================
    # Tools
    # ====================
    async def _refresh_screen_capture_base64(self):
        """刷新最新的当前屏幕截图"""
        logger.info("\n获取最新的当前屏幕截图")
        # 获取当前的屏幕
        screenshot = pyautogui.screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format='JPEG', quality=50)
        screenshot_base_64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        self._fs.write_image(f"{time.time()}.jpeg", screenshot_base_64)

        return screenshot_base_64

    # ====================
    # Nodes
    # ====================
    async def _node_generate_master_plan(self, state: State):
        """生成总体计划"""
        logger.info("\n===========================\n生成总体计划")
        # 获取最新的当前的屏幕
        screen_capture_base64 = await self._refresh_screen_capture_base64()
        # system_prompt
        system_prompt = "你是[AI控屏]的总指挥,你擅长根据当前的屏幕截图[screen_capture_base64]和输入[promot]制定总的方案来满足用户的操作和需求"
        # model
        generate_master_plan_model = (self._model
                                     .with_structured_output(PlanResponseStructure)
                                     .bind(system_prompt=system_prompt))
        # invoke
        response = await generate_master_plan_model.ainvoke([
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"[promot]: {state.get("prompt")}"
                }, {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{screen_capture_base64}"}
                }
            ])
        ])
        # result
        master_plan = response.plan_list
        logger.info(f"\n总方案: \n{master_plan}")

        return {"master_plan": master_plan, "master_plan_current_step": 0}

    async def _node_generate_sub_plan_generator(self, state: State):
        """子方案生成器"""
        logger.info("\n===========================\n子方案生成器")
        # 获取最新的当前的屏幕
        screen_capture_base64 = await self._refresh_screen_capture_base64()
        # 获取当前步骤
        master_plan_current_step = state.get("master_plan_current_step")
        master_plan = state.get("master_plan")
        master_plan_current_step_target = master_plan[master_plan_current_step]
        logger.info(f"\n总方案的当前步骤: \n{master_plan_current_step_target}")

        # system_prompt
        system_prompt = ("你是一个操作电脑的精准机器人。你的输出必须是 Python 函数调用列表。\n"
                         "示例输入目标：'点击任务栏微信'\n"
                         "示例输出方案：['move_mouse_with_click(50, 1050)']\n"
                         "当前目标：[master_plan_current_step_target]\n"
                         "规则：严禁使用中文描述，必须且只能输出格式化指令。")
        # system_prompt = ("分析当前的屏幕截图[screen_capture_base64],生成具体的步骤来达到目标[master_plan_current_step_target]\n"
        #                  "每一个步骤的描述必须遵循如下格式:\n"
        #                  "\t- move_mouse(x,y)\n"
        #                  "\t- move_mouse_with_click(x,y)\n"
        #                  "\t- keyboard_input(text)\n"
        #                  "\t- keyboard_hold_and_move_mouse_with_click(ctrl,x,y)\n")
        # system_prompt = "你是[AI控屏]的专家,基于已经制定的总方案[master_plan]和用户的目标[promot],必须根据当前的屏幕截图[screen_capture_base64],生成非常具体的鼠标和键盘操作步骤来完成当前的子任务[master_plan_current_step_target]"
        # model
        generate_sub_plan_generator_model = (self._model
                                     .with_structured_output(PlanResponseStructure)
                                     .bind(system_prompt=system_prompt))
        # invoke
        response = await generate_sub_plan_generator_model.ainvoke([
            HumanMessage(content=[
                {
                #     "type": "text",
                #     "text": f"[promot]: {state.get("prompt")}"
                # }, {
                #     "type": "text",
                #     "text": f"[master_plan]: {master_plan}"
                # }, {
                    "type": "text",
                    "text": f"[master_plan_current_step_target]: {master_plan_current_step_target}"
                }, {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{screen_capture_base64}"}
                }
            ])
        ])
        # result
        sub_plan = response.plan_list
        logger.info(f"\n总方案当前步骤的具体方案: \n{sub_plan}")

        return {"sub_plan": sub_plan}

    async def _node_generate_sub_plan_evaluator(self, state: State):
        """子方案评估器"""
        logger.info("\n===========================\n子方案评估器")
        # 获取最新的当前的屏幕
        screen_capture_base64 = await self._refresh_screen_capture_base64()
        # 获取子方案
        sub_plan = state.get("sub_plan")
        # system_prompt
        system_prompt = ("评判子方案[sub_plan]的描述是否符合 Python 函数调用列表。\n"
                         "示例输入目标：'点击任务栏微信'\n"
                         "示例输出方案：['move_mouse_with_click(50, 1050)']\n"
                         "当前目标：[master_plan_current_step_target]\n"
                         "规则：严禁使用中文描述，必须且只能输出格式化指令。")
        # system_prompt = ("你是一个AI控屏专家.\n\n"
        #                  "评判子方案[sub_plan]的描述是否符合以下格式标准:\n"
        #                  "\t- move_mouse(x,y)\n"
        #                  "\t- move_mouse_with_click(x,y)\n"
        #                  "\t- keyboard_input(text)\n"
        #                  "\t- keyboard_hold_and_move_mouse_with_click(ctrl,x,y)\n")
        logger.info(f"\n子方案: \n{sub_plan}")
        # system_prompt = "你是[AI控屏]的专家,基于已经制定的总方案[master_plan]和用户的目标[promot],必须根据当前的屏幕截图[screen_capture_base64],生成非常具体的鼠标和键盘操作步骤来完成当前的子任务[master_plan_current_step_target]"
        # model
        generate_sub_plan_evaluator_model = (self._sub_plan_model
                                     .with_structured_output(EvaluatorResponseStructure)
                                     .bind(system_prompt=system_prompt))
        # invoke
        response = await generate_sub_plan_evaluator_model.ainvoke([
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": f"[sub_plan]: {sub_plan}"
                }, {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{screen_capture_base64}"}
                }
            ])
        ])
        # result
        master_plan_current_step = state.get("master_plan_current_step")
        if response.is_ok:
            master_plan_current_step += 1
        logger.info(f"\n评估结果: \n{response}")

        return {"sub_plan_is_ok": response.is_ok, "sub_plan_feedback": response.feedback, "master_plan_current_step": master_plan_current_step}

    # ====================
    # Route
    # ====================
    def _route_plan_is_ok(self, state: State):
        """路由NPC档案生成"""
        sub_plan_is_ok = state.get("sub_plan_is_ok")
        master_plan = state.get("master_plan")
        master_plan_current_step = state.get("master_plan_current_step")
        if not sub_plan_is_ok or master_plan_current_step < len(master_plan):
            return "Rejected"
        return "Accepted"

    # def _route_generate_npc_image(self, state: State):
    #     """路由NPC档案生成"""
    #     npc_image_is_ok = state.get("npc_image_is_ok")
    #     if not npc_image_is_ok:
    #         return "Rejected"
    #     return "Accepted"

    # ====================
    # Build Graph
    # ====================
    def _build_graph(self):
        graph = StateGraph(State)

        # 添加节点
        graph.add_node("generate_master_plan", self._node_generate_master_plan)
        graph.add_node("generate_sub_plan_generator", self._node_generate_sub_plan_generator)
        graph.add_node("generate_sub_plan_evaluator", self._node_generate_sub_plan_evaluator)
        # 线性连接
        graph.add_edge(START, "generate_master_plan")
        graph.add_edge("generate_master_plan", "generate_sub_plan_generator")
        graph.add_edge("generate_sub_plan_generator", "generate_sub_plan_evaluator")
        graph.add_conditional_edges(
            source="generate_sub_plan_evaluator",
            path=self._route_plan_is_ok,
            path_map={
                "Accepted": END,
                "Rejected": "generate_sub_plan_generator",
            }
        )
        # 编译
        app = graph.compile()
        # 打印
        logger.info(f"\n{app.get_graph().draw_ascii()}")

        return app

    # ====================
    # Run
    # ====================
    async def ainvoke(self, prompt: str):
        """异步运行接口"""
        return await self.app.ainvoke(input={"prompt": prompt})

    async def astream(self, prompt: str):
        """异步流式运行接口"""
        async for _ in self.app.astream(input={"prompt": prompt}):
            yield _
