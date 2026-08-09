"""
首页（Chainlit 版）

启动::

    chainlit run app.py -w

说明：
    - Chainlit 是事件驱动的，不像 Streamlit 每次交互重跑整个脚本，
      因此不需要 st.rerun()、st.session_state 这类模式。
    - 每个浏览器会话由 cl.user_session 隔离，历史消息存在其中。
    - 侧边栏的历史会话列表由 Chainlit 内置 Thread 机制提供
      （需配置 data layer 才会持久化），无需手写 conversations 字典。
"""

import asyncio
import os

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

from agent import AssistantAgent
from db import Milvus
from model import Embedding
from utils import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = (
    "你是一个助手，回答我的问题。当你需要更多信息来回答问题的时候，可以借助有用的工具来帮助你获取有用的信息。"
)

# 允许渲染到前端的 LangGraph 节点名。
# create_agent 里主模型节点叫 "model"；工具节点（含 RAG 内部的 LLM 调用）叫 "tools"。
# 首次运行看 debug 日志确认实际名字，不符再调整。
MAIN_MODEL_NODES = {"model", "agent"}
# 工具显示名
TOOL_DISPLAY_NAMES = {
    "info_search": "🔍 搜索信息",
}


# ==============================================================================
# 持久化层：会话历史存 PostgreSQL，侧边栏的历史列表依赖它
# ==============================================================================
@cl.data_layer
def get_data_layer():
    """Chainlit 启动时调用一次，返回持久化实现"""
    return SQLAlchemyDataLayer(conninfo=os.environ["DATABASE_URL"])


# ==============================================================================
# 认证：data layer 要求用户身份，thread 挂在 user 下才能归属会话
# ==============================================================================
@cl.password_auth_callback
def auth_callback(username: str, password: str) -> cl.User | None:
    """返回 cl.User 表示登录成功，返回 None 表示拒绝。

    开发阶段用环境变量里的固定账号，生产环境应换成查数据库或接 OAuth。
    """
    expected_user = os.getenv("APP_USER", "admin")
    expected_pwd = os.getenv("APP_PASSWORD", "admin")

    if (username, password) == (expected_user, expected_pwd):
        logger.info(f"========== 用户登录成功: {username}")
        return cl.User(identifier=username, metadata={"role": "admin"})

    logger.warning(f"========== 用户登录失败: {username}")
    return None


# ==============================================================================
# Agent 单例：进程级只创建一次，避免每个会话重复初始化模型客户端
# ==============================================================================
_agent = None


def get_assistant_agent():
    global _agent
    if _agent is None:
        _agent = AssistantAgent().get_agent()
        logger.info("========== Agent 初始化完成")
    return _agent


# ==============================================================================
# 落地页引导：渲染成可点击卡片，属于前端配置，不会写入 data layer
# （欢迎语正文在 chainlit.md，通过右上角「说明」按钮查看）
# ==============================================================================
@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(
            label="查设定",
            message="雾溪村目前有哪些已知设定？",
        ),
        cl.Starter(
            label="做个 NPC",
            message="我想做一个雾溪村的村长，形象搞怪但实力很强",
        ),
        cl.Starter(
            label="看世界观",
            message="现在的世界观里有哪些村落和势力？",
        ),
        cl.Starter(
            label="补充设定",
            message="我想给雾溪村补充一些背景设定，帮我梳理一下现在缺什么",
        ),
    ]


# ==============================================================================
# 会话生命周期
# ==============================================================================
@cl.on_chat_start
async def on_chat_start() -> None:
    """新会话开始时触发，等价于旧版侧边栏的『新对话』按钮"""
    # system message 只放一条，放在历史最前面
    cl.user_session.set("messages", [{"role": "system", "content": SYSTEM_PROMPT}])
    logger.debug(f"========== 新会话开始: {cl.context.session.id}")

    # 欢迎语走 chainlit.md 的 welcome screen，不发 cl.Message，
    # 这样既能每次打开界面都看到，又不会被 data layer 持久化成一条 step


@cl.on_chat_resume
async def on_chat_resume(thread) -> None:
    """从历史会话恢复时触发（需配置 data layer 才生效）"""
    logger.debug(f"========== thread: {thread}")
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for step in thread.get("steps", []):
        if step["type"] == "user_message":
            messages.append({"role": "user", "content": step["output"]})
        elif step["type"] == "assistant_message":
            messages.append({"role": "assistant", "content": step["output"]})

    cl.user_session.set("messages", messages)
    logger.debug(f"========== 会话恢复，历史消息 {len(messages)} 条")


# ==============================================================================
# 消息处理：流式输出
# ==============================================================================
@cl.on_message
async def on_message(message: cl.Message) -> None:
    """用户每发一条消息触发一次"""
    messages: list[dict] = cl.user_session.get("messages") or [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": message.content})

    # 先送一条空消息占位，之后用 stream_token 往里灌内容
    reply = cl.Message(content="")
    await reply.send()

    try:
        stream = await get_assistant_agent().astream_events(
            {"messages": messages},
            version="v3",
        )

        async def consume_messages():
            async for model_msg in stream.messages:
                if model_msg.node not in MAIN_MODEL_NODES:
                    continue
                async for text in model_msg.text:
                    await reply.stream_token(text)

        async def consume_tool_calls():
            async for call in stream.tool_calls:
                display_name = TOOL_DISPLAY_NAMES.get(call.tool_name, f"🔧 {call.tool_name}")
                async with cl.Step(
                    name=display_name,
                    type="tool",
                    parent_id=reply.id,
                    thread_id=reply.thread_id,
                ) as step:
                    step.input = call.input
                    async for delta in call.output_deltas:
                        await step.stream_token(delta)
                    if call.error:
                        step.is_error = True
                        step.output = str(call.error)
                    else:
                        step.output = call.output

        await asyncio.gather(consume_tool_calls(), consume_messages())
        await reply.update()

    except Exception as e:
        logger.exception("========== 生成回复失败")
        reply.content = f"抱歉，生成回复时出错了：{e}"
        await reply.update()
        return

    messages.append({"role": "assistant", "content": reply.content})
    cl.user_session.set("messages", messages)


# ==============================================================================
# 应用关闭时清理资源
# ==============================================================================
@cl.on_app_shutdown
async def shutdown():
    embedding = Embedding()
    milvus = Milvus()
    await embedding.close()
    await milvus.close()
