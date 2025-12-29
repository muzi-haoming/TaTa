"""
NPC 角色生成页面

提供两种模式：
1. 大模型对话模式 - 传统的聊天对话，带有上下文记忆
2. 工作流模式 - 使用 NPC 生成工作流，自动生成角色档案、图片和3D模型
"""
import asyncio
import base64
import queue
import time
import uuid
from enum import Enum
from typing import Generator

import streamlit as st
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config import settings
from utils import logger
from workflows.generate_npc_workflow import GenerateNpcWorkflow


# ==================== 常量定义 ====================

class ChatMode(Enum):
    """聊天模式枚举"""
    LLM = "llm"
    WORKFLOW_NPC = "workflow_npc"


# 模式显示名称
MODE_DISPLAY_NAMES = {
    ChatMode.LLM.value: "💬 大模型对话",
    ChatMode.WORKFLOW_NPC.value: "🔄 NPC生成工作流",
}

# 模式说明
MODE_DESCRIPTIONS = {
    ChatMode.LLM.value: "自由对话，讨论角色设计想法（支持上下文记忆）",
    ChatMode.WORKFLOW_NPC.value: "自动生成完整NPC角色（档案+图片+3D模型）",
}

# 工作流节点完成后，下一个要执行的步骤名称
# 当收到某节点的完成通知时，显示下一个步骤的状态
WORKFLOW_NEXT_STEP = {
    "search_worldview": "检索模型风格资料",
    "search_model_style": "检索相关背景资料",
    "search_relevent_lore": "生成NPC角色档案",
    "generate_npc_json_generator": "评估角色档案质量",
    "generate_npc_json_evaluator": "保存角色档案",  # 或者重新生成
    "save_npc_json": "生成图片描述词",
    "generate_npc_image_prompt": "生成NPC角色图片",
    "generate_npc_image_generator": "评估角色图片",
    "generate_npc_image_evaluator": "保存角色图片",  # 或者重新生成
    "save_npc_image": "生成3D模型",
    "generate_npc_model": None,  # 最后一步，完成
}

# 节点完成时的友好名称（用于进度显示）
WORKFLOW_NODE_COMPLETED_NAMES = {
    "search_worldview": "检索世界观资料",
    "search_model_style": "检索模型风格资料",
    "search_relevent_lore": "检索相关背景资料",
    "generate_npc_json_generator": "生成NPC角色档案",
    "generate_npc_json_evaluator": "评估角色档案",
    "save_npc_json": "保存角色档案",
    "generate_npc_image_prompt": "生成图片描述词",
    "generate_npc_image_generator": "生成NPC角色图片",
    "generate_npc_image_evaluator": "评估角色图片",
    "save_npc_image": "保存角色图片",
    "generate_npc_model": "生成3D模型",
}

# 系统提示词（用于大模型对话模式）
SYSTEM_PROMPT = """你是一个资深的游戏角色设计师，精通各种游戏世界观和角色设计。
你可以帮助用户：
1. 讨论游戏角色设计的想法和概念
2. 回答关于角色设计的问题
3. 提供角色设计的建议和灵感

请用专业但友好的语气与用户交流。"""


# ==================== 自定义CSS样式 ====================

def inject_custom_css():
    """注入自定义CSS样式"""
    st.markdown("""
    <style>
    /* 加载动画 */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .loading-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.25rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 25px;
        color: white;
        font-size: 0.95rem;
        animation: pulse 1.5s ease-in-out infinite;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .loading-spinner {
        width: 18px;
        height: 18px;
        border: 2px solid #ffffff40;
        border-top: 2px solid #ffffff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* 进度步骤样式 */
    .progress-steps {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.5rem 0;
    }

    .progress-step {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.25rem 0.75rem;
        background: #e8f5e9;
        border-radius: 15px;
        font-size: 0.85rem;
        color: #2e7d32;
    }

    /* 3D模型进度条 */
    .model-progress-container {
        margin: 0.5rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }

    .model-progress-bar {
        width: 100%;
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 0.5rem;
    }

    .model-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    /* 消息区域底部留白 */
    .main .block-container {
        padding-bottom: 100px;
    }

    /* 结果卡片 */
    .result-section {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    </style>
    """, unsafe_allow_html=True)


# ==================== Session State 初始化 ====================

def init_session_state():
    """初始化 Session State"""
    # 消息历史
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 当前模式
    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = ChatMode.LLM.value

    # 对话线程ID（用于记忆功能）
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())[:8]

    # LLM 对话历史（LangChain Message 格式）
    if "llm_history" not in st.session_state:
        st.session_state.llm_history = [SystemMessage(content=SYSTEM_PROMPT)]

    # 工作流实例（延迟初始化）
    if "workflow" not in st.session_state:
        st.session_state.workflow = None

    # 是否正在生成
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False

    # 3D模型生成进度
    if "model_progress" not in st.session_state:
        st.session_state.model_progress = 0

    # 3D模型生成状态文本
    if "model_progress_text" not in st.session_state:
        st.session_state.model_progress_text = ""


def get_llm_model():
    """获取 LLM 模型实例"""
    return init_chat_model(model=settings.models.chat_model)


def get_workflow():
    """获取工作流实例（延迟初始化）"""
    if st.session_state.workflow is None:
        st.session_state.workflow = GenerateNpcWorkflow()
    return st.session_state.workflow


# ==================== 大模型对话模式 ====================

def stream_llm_response(prompt: str) -> Generator[str, None, None]:
    """
    流式生成大模型回复

    Args:
        prompt: 用户输入

    Yields:
        回复的文本块
    """
    model = get_llm_model()

    # 添加用户消息到历史
    st.session_state.llm_history.append(HumanMessage(content=prompt))

    # 流式调用模型
    full_response = ""
    try:
        for chunk in model.stream(st.session_state.llm_history):
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield chunk.content
                time.sleep(settings.ui.stream_delay)

        # 添加 AI 回复到历史
        st.session_state.llm_history.append(AIMessage(content=full_response))

    except Exception as e:
        logger.error(f"LLM 调用错误: {e}")
        error_msg = f"抱歉，生成回复时出现错误: {str(e)}"
        st.session_state.llm_history.append(AIMessage(content=error_msg))
        yield error_msg


# ==================== 工作流模式 ====================

def format_npc_json_result(npc_json: dict) -> str:
    """
    格式化 NPC JSON 结果

    Args:
        npc_json: NPC 角色档案数据

    Returns:
        格式化的结果字符串
    """
    if not npc_json:
        return ""

    result_parts = ["#### 📋 角色档案\n"]
    result_parts.append(f"| 属性 | 内容 |")
    result_parts.append(f"|------|------|")
    result_parts.append(f"| **姓名** | {npc_json.get('name', '未知')} |")
    result_parts.append(f"| **种族** | {npc_json.get('race', '未知')} |")
    result_parts.append(f"| **性格** | {npc_json.get('personality', '未知')} |")
    result_parts.append("")
    result_parts.append(f"**背景故事**: {npc_json.get('background', '未知')}")
    result_parts.append("")
    result_parts.append(f"**开场白**: _{npc_json.get('opening_line', '未知')}_")
    result_parts.append("")
    result_parts.append(f"**外观描述**: {npc_json.get('appearance', '未知')}")

    return "\n".join(result_parts)


def format_final_result(state: dict) -> str:
    """
    格式化最终结果（仅文件路径）

    Args:
        state: 工作流最终状态

    Returns:
        格式化的结果字符串
    """
    npc_json_path = state["npc_json_path"]
    npc_image_path = state["npc_image_path"]
    npc_model_path = state["npc_model_path"]

    result_parts = ["#### 📁 生成的文件\n"]
    if npc_json_path:
        result_parts.append(f"- 📄 角色档案: `{npc_json_path}`")
    if npc_image_path:
        result_parts.append(f"- 🖼️ 角色图片: `{npc_image_path}`")
    if npc_model_path:
        result_parts.append(f"- 🎮 3D模型: `{npc_model_path}`")

    return "\n".join(result_parts)


# ==================== UI 组件 ====================

def render_loading_status(step_name: str):
    """
    渲染加载状态组件

    Args:
        step_name: 当前步骤名称
    """
    st.markdown(f"""
    <div class="loading-indicator">
        <div class="loading-spinner"></div>
        <span>正在{step_name}...</span>
    </div>
    """, unsafe_allow_html=True)


def render_model_progress(progress: int, status_text: str):
    """
    渲染3D模型生成进度

    Args:
        progress: 进度百分比 (0-100)
        status_text: 状态文本
    """
    st.markdown(f"""
    <div class="model-progress-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>🎮 {status_text}</span>
            <span style="font-weight: bold; color: #667eea;">{progress}%</span>
        </div>
        <div class="model-progress-bar">
            <div class="model-progress-fill" style="width: {progress}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_progress_steps(completed_steps: list):
    """
    渲染已完成的步骤

    Args:
        completed_steps: 已完成步骤列表
    """
    if completed_steps:
        steps_html = " ".join([f'<span class="progress-step">✅ {step}</span>' for step in completed_steps])
        st.markdown(f'<div class="progress-steps">{steps_html}</div>', unsafe_allow_html=True)


def render_message(role: str, content: str, image_base64: str = None):
    """
    渲染消息

    Args:
        role: 消息角色（user/assistant）
        content: 消息内容
        image_base64: 可选的图片 base64 编码
    """
    with st.chat_message(role):
        st.markdown(content)
        if image_base64:
            try:
                image_bytes = base64.b64decode(image_base64)
                st.image(image_bytes, caption="生成的角色图片", width=400)
            except Exception as e:
                logger.error(f"图片显示错误: {e}")


def render_welcome_message():
    """渲染欢迎消息"""
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("""
👋 **欢迎使用 NPC 角色生成器！**

我可以帮助你：
- 💬 **对话模式**: 自由讨论游戏角色设计的想法（支持上下文记忆）
- 🔄 **工作流模式**: 自动生成完整的NPC角色（包括档案、图片和3D模型）

在上方选择模式，然后在下方输入框输入你的需求开始吧！
            """)


def clear_conversation():
    """清空对话"""
    st.session_state.messages = []
    st.session_state.llm_history = [SystemMessage(content=SYSTEM_PROMPT)]
    st.session_state.thread_id = str(uuid.uuid4())[:8]
    st.session_state.model_progress = 0
    st.session_state.model_progress_text = ""


# ==================== 主函数 ====================

def main():
    """主函数"""
    # 页面配置
    st.set_page_config(
        page_title="NPC角色生成器",
        page_icon="🎮",
        layout="wide"
    )

    # 注入自定义CSS
    inject_custom_css()

    # 初始化状态
    init_session_state()

    # 侧边栏
    with st.sidebar:
        st.header("🎮 NPC角色生成器")
        st.divider()

        # 会话信息
        st.caption(f"会话ID: `{st.session_state.thread_id}`")

        # 模式信息
        current_mode_name = MODE_DISPLAY_NAMES.get(st.session_state.chat_mode, "未知")
        st.info(f"当前模式: {current_mode_name}")

        # 清空对话按钮
        if st.button("🗑️ 清空对话", use_container_width=True):
            clear_conversation()
            st.rerun()

        st.divider()

        # 使用说明
        with st.expander("📖 使用说明", expanded=False):
            st.markdown("""
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
            """)

    # 主聊天区域
    st.title("🎮 NPC角色生成器")

    # 模式选择区域 - 放在标题下方
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        mode_options = list(MODE_DISPLAY_NAMES.keys())
        current_index = mode_options.index(st.session_state.chat_mode) if st.session_state.chat_mode in mode_options else 0

        selected_mode = st.selectbox(
            "🎯 选择模式",
            options=mode_options,
            format_func=lambda x: f"{MODE_DISPLAY_NAMES[x]} - {MODE_DESCRIPTIONS[x]}",
            index=current_index,
            disabled=st.session_state.is_generating,
            key="mode_selector"
        )

        if selected_mode != st.session_state.chat_mode:
            st.session_state.chat_mode = selected_mode
            st.rerun()

    st.divider()

    # 渲染欢迎消息
    render_welcome_message()

    # 显示历史消息
    for msg in st.session_state.messages:
        render_message(
            msg["role"],
            msg["content"],
            msg.get("image_base64")
        )

    # 聊天输入框
    if st.session_state.chat_mode == ChatMode.LLM.value:
        placeholder = "输入你的消息，与AI讨论角色设计..."
    else:
        placeholder = "描述你想要生成的NPC角色，例如：一个神秘的精灵法师..."

    prompt = st.chat_input(
        placeholder=placeholder,
        disabled=st.session_state.is_generating
    )

    # 处理用户输入
    if prompt:
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_message("user", prompt)

        # 设置生成状态
        st.session_state.is_generating = True

        if st.session_state.chat_mode == ChatMode.LLM.value:
            # ========== 大模型对话模式 ==========
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""

                # 显示思考状态
                with response_placeholder.container():
                    render_loading_status("思考")

                # 流式生成回复
                for chunk in stream_llm_response(prompt):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)

            # 保存助手回复
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })

        else:
            # ========== 工作流模式 ==========
            with st.chat_message("assistant"):
                # 创建多个占位符用于不同内容的显示
                status_placeholder = st.empty()
                progress_placeholder = st.empty()
                json_result_placeholder = st.empty()
                image_placeholder = st.empty()
                model_progress_placeholder = st.empty()
                final_result_placeholder = st.empty()

                try:
                    # 获取工作流
                    workflow = get_workflow()
                    all_states = {}
                    completed_steps = []
                    json_displayed = False
                    image_displayed = False

                    # 创建线程安全的队列用于传递进度更新
                    progress_queue = queue.Queue()

                    # 设置3D模型进度回调 - 将进度放入队列（线程安全）
                    def model_progress_callback(progress: int, status_text: str):
                        progress_queue.put((progress, status_text))

                    # 设置回调到工作流类
                    GenerateNpcWorkflow.model_progress_callback = model_progress_callback

                    # 初始状态
                    with status_placeholder.container():
                        render_loading_status("检索世界观资料")

                    # 定义异步运行函数
                    async def run_workflow_with_progress():
                        nonlocal all_states, completed_steps, json_displayed, image_displayed

                        async for state_update in workflow.astream(prompt):
                            node_name = list(state_update.keys())[0] if state_update else ""
                            node_data = state_update.get(node_name, {})

                            # 合并状态
                            if isinstance(node_data, dict):
                                all_states.update(node_data)

                            if node_name in WORKFLOW_NODE_COMPLETED_NAMES:
                                step_name = WORKFLOW_NODE_COMPLETED_NAMES[node_name]
                                completed_steps.append(step_name)

                                # 更新进度显示
                                with progress_placeholder.container():
                                    render_progress_steps(completed_steps)

                                # 获取下一个步骤名称并更新状态显示
                                next_step = WORKFLOW_NEXT_STEP.get(node_name)
                                if next_step:
                                    with status_placeholder.container():
                                        render_loading_status(next_step)

                                # === 逐步展示结果 ===

                                # 保存JSON后立即展示角色档案
                                if node_name == "save_npc_json" and not json_displayed:
                                    npc_json = all_states.get("npc_json", {})
                                    if npc_json:
                                        json_result_placeholder.markdown("### ✨ NPC角色生成中...\n")
                                        json_result_placeholder.markdown(format_npc_json_result(npc_json))
                                        json_displayed = True

                                # 保存图片后立即展示图片
                                if node_name == "save_npc_image" and not image_displayed:
                                    npc_image_base64 = all_states.get("npc_image_base64")
                                    if npc_image_base64:
                                        try:
                                            image_bytes = base64.b64decode(npc_image_base64)
                                            image_placeholder.image(
                                                image_bytes,
                                                caption="🖼️ 生成的角色图片",
                                                width=400
                                            )
                                            image_displayed = True
                                        except Exception as e:
                                            logger.error(f"图片显示错误: {e}")

                                # 3D模型生成中显示进度
                                if node_name == "save_npc_image":
                                    # 开始3D模型生成，初始化进度
                                    st.session_state.model_progress = 0
                                    st.session_state.model_progress_text = "准备生成3D模型..."

                            logger.info(f"工作流节点完成: {node_name}")

                        return all_states

                    # 运行异步工作流，同时轮询更新3D模型进度
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # 创建工作流任务
                    async def run_with_model_progress_update():
                        nonlocal all_states

                        # 创建工作流协程
                        workflow_task = asyncio.create_task(run_workflow_with_progress())

                        # 轮询更新3D模型进度显示
                        last_progress = -1
                        while not workflow_task.done():
                            current_progress = st.session_state.model_progress
                            progress_text = st.session_state.model_progress_text

                            # 只在进度变化时更新UI
                            if current_progress != last_progress and current_progress >= 0:
                                last_progress = current_progress
                                if progress_text and "3D模型" in progress_text:
                                    with model_progress_placeholder.container():
                                        render_model_progress(current_progress, progress_text)

                            await asyncio.sleep(0.5)

                        # 获取最终结果
                        all_states = await workflow_task
                        return all_states

                    try:
                        final_state = loop.run_until_complete(run_with_model_progress_update())
                    finally:
                        loop.close()

                    # 清除状态和进度显示
                    status_placeholder.empty()
                    model_progress_placeholder.empty()

                    # 更新标题为完成状态
                    if json_displayed:
                        json_result_placeholder.markdown("### ✨ NPC角色生成完成！\n" + format_npc_json_result(final_state["npc_json"]))

                    # 显示最终文件路径
                    final_result_placeholder.markdown(format_final_result(final_state))

                    # 保存完整消息到历史
                    full_content = "### ✨ NPC角色生成完成！\n\n"
                    full_content += format_npc_json_result(final_state["npc_json"])
                    full_content += "\n\n"
                    full_content += format_final_result(final_state)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_content,
                        "image_base64": final_state["npc_image_base64"]
                    })

                except Exception as e:
                    logger.error(f"工作流执行错误: {e}")
                    import traceback
                    traceback.print_exc()

                    error_msg = f"❌ 生成过程中出现错误:\n```\n{str(e)}\n```\n\n请检查日志获取详细信息。"
                    status_placeholder.empty()
                    progress_placeholder.empty()
                    model_progress_placeholder.empty()
                    json_result_placeholder.markdown(error_msg)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

                finally:
                    # 清除进度回调
                    GenerateNpcWorkflow.model_progress_callback = None

        # 重置生成状态
        st.session_state.is_generating = False
        st.rerun()


if __name__ == "__main__":
    main()
