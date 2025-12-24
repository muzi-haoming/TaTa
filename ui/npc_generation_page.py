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


# 模式配置
MODE_CONFIG = {
    ChatMode.LLM.value: {
        "display": "💬 大模型对话",
        "description": "自由对话，讨论角色设计想法（支持上下文记忆）",
        "placeholder": "输入你的消息，与AI讨论角色设计...",
    },
    ChatMode.WORKFLOW_NPC.value: {
        "display": "🔄 NPC生成工作流",
        "description": "自动生成完整NPC角色（档案+图片+3D模型）",
        "placeholder": "描述你想要生成的NPC角色，例如：一个神秘的精灵法师...",
    },
}

# 工作流节点配置：节点名称 -> (完成时显示名称, 下一步骤名称)
WORKFLOW_NODES = {
    "search_worldview": ("检索世界观资料", "检索模型风格资料"),
    "search_model_style": ("检索模型风格资料", "检索相关背景资料"),
    "search_relevent_lore": ("检索相关背景资料", "生成NPC角色档案"),
    "generate_npc_json_generator": ("生成NPC角色档案", "评估角色档案质量"),
    "generate_npc_json_evaluator": ("评估角色档案", "保存角色档案"),
    "save_npc_json": ("保存角色档案", "生成图片描述词"),
    "generate_npc_image_prompt": ("生成图片描述词", "生成NPC角色图片"),
    "generate_npc_image_generator": ("生成NPC角色图片", "评估角色图片"),
    "generate_npc_image_evaluator": ("评估角色图片", "保存角色图片"),
    "save_npc_image": ("保存角色图片", "生成3D模型"),
    "generate_npc_model": ("生成3D模型", None),
}

# 系统提示词（用于大模型对话模式）
SYSTEM_PROMPT = """你是一个资深的游戏角色设计师，精通各种游戏世界观和角色设计。
你可以帮助用户：
1. 讨论游戏角色设计的想法和概念
2. 回答关于角色设计的问题
3. 提供角色设计的建议和灵感

请用专业但友好的语气与用户交流。"""


# ==================== 自定义CSS样式 ====================

CUSTOM_CSS = """
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
</style>
"""


def inject_custom_css():
    """注入自定义CSS样式"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==================== Session State 初始化 ====================

def init_session_state():
    """初始化 Session State"""
    defaults = {
        "messages": [],
        "chat_mode": ChatMode.LLM.value,
        "thread_id": str(uuid.uuid4())[:8],
        "llm_history": [SystemMessage(content=SYSTEM_PROMPT)],
        "workflow": None,
        "is_generating": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_workflow():
    """获取工作流实例（延迟初始化）"""
    if st.session_state.workflow is None:
        st.session_state.workflow = GenerateNpcWorkflow()
    return st.session_state.workflow


def clear_conversation():
    """清空对话"""
    st.session_state.messages = []
    st.session_state.llm_history = [SystemMessage(content=SYSTEM_PROMPT)]
    st.session_state.thread_id = str(uuid.uuid4())[:8]


# ==================== 大模型对话模式 ====================

def stream_llm_response(prompt: str) -> Generator[str, None, None]:
    """流式生成大模型回复"""
    model = init_chat_model(model=settings.models.chat_model)
    st.session_state.llm_history.append(HumanMessage(content=prompt))

    full_response = ""
    try:
        for chunk in model.stream(st.session_state.llm_history):
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield chunk.content
                time.sleep(settings.ui.stream_delay)
        st.session_state.llm_history.append(AIMessage(content=full_response))
    except Exception as e:
        logger.error(f"LLM 调用错误: {e}")
        error_msg = f"抱歉，生成回复时出现错误: {str(e)}"
        st.session_state.llm_history.append(AIMessage(content=error_msg))
        yield error_msg


# ==================== 格式化函数 ====================

def format_npc_json_result(npc_json: dict) -> str:
    """格式化 NPC JSON 结果"""
    if not npc_json:
        return ""

    fields = [
        ("姓名", "name"), ("种族", "race"), ("性格", "personality")
    ]

    lines = ["#### 📋 角色档案\n", "| 属性 | 内容 |", "|------|------|"]
    lines.extend(f"| **{label}** | {npc_json.get(key, '未知')} |" for label, key in fields)
    lines.append("")
    lines.append(f"**背景故事**: {npc_json.get('background', '未知')}")
    lines.append("")
    lines.append(f"**开场白**: _{npc_json.get('opening_line', '未知')}_")
    lines.append("")
    lines.append(f"**外观描述**: {npc_json.get('appearance', '未知')}")

    return "\n".join(lines)


def format_final_result(state: dict) -> str:
    """格式化最终结果（文件路径）"""
    files = [
        ("📄 角色档案", "npc_json_path"),
        ("🖼️ 角色图片", "npc_image_path"),
        ("🎮 3D模型", "npc_model_path"),
    ]

    lines = ["#### 📁 生成的文件\n"]
    lines.extend(
        f"- {icon}: `{state.get(key)}`"
        for icon, key in files if state.get(key)
    )

    return "\n".join(lines)


# ==================== UI 渲染组件 ====================

def render_loading_status(step_name: str):
    """渲染加载状态组件"""
    st.markdown(f"""
    <div class="loading-indicator">
        <div class="loading-spinner"></div>
        <span>正在{step_name}...</span>
    </div>
    """, unsafe_allow_html=True)


def render_model_progress(progress: int, status_text: str):
    """渲染3D模型生成进度"""
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
    """渲染已完成的步骤"""
    if completed_steps:
        steps_html = " ".join(f'<span class="progress-step">✅ {step}</span>' for step in completed_steps)
        st.markdown(f'<div class="progress-steps">{steps_html}</div>', unsafe_allow_html=True)


def render_message(role: str, content: str, image_base64: str = None):
    """渲染消息"""
    with st.chat_message(role):
        st.markdown(content)
        if image_base64:
            try:
                st.image(base64.b64decode(image_base64), caption="生成的角色图片", width=400)
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


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("🎮 NPC角色生成器")
        st.divider()

        st.caption(f"会话ID: `{st.session_state.thread_id}`")

        current_mode = MODE_CONFIG.get(st.session_state.chat_mode, {})
        st.info(f"当前模式: {current_mode.get('display', '未知')}")

        if st.button("🗑️ 清空对话", use_container_width=True):
            clear_conversation()
            st.rerun()

        st.divider()

        with st.expander("📖 使用说明", expanded=False):
            st.markdown("""
**💬 大模型对话模式**
- 与AI自由对话
- 讨论角色设计想法
- 支持上下文记忆

**🔄 NPC生成工作流模式**
- 输入角色描述
- 自动检索背景资料
- 生成角色档案、图片和3D模型
- 全程显示进度
            """)


def render_mode_selector():
    """渲染模式选择器"""
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        mode_options = list(MODE_CONFIG.keys())
        current_index = mode_options.index(st.session_state.chat_mode) if st.session_state.chat_mode in mode_options else 0

        selected_mode = st.selectbox(
            "🎯 选择模式",
            options=mode_options,
            format_func=lambda x: f"{MODE_CONFIG[x]['display']} - {MODE_CONFIG[x]['description']}",
            index=current_index,
            disabled=st.session_state.is_generating,
            key="mode_selector"
        )

        if selected_mode != st.session_state.chat_mode:
            st.session_state.chat_mode = selected_mode
            st.rerun()


# ==================== 工作流执行 ====================

async def run_workflow_async(workflow, prompt: str, progress_queue: queue.Queue, placeholders: dict):
    """
    异步执行工作流并更新UI

    Args:
        workflow: 工作流实例
        prompt: 用户输入
        progress_queue: 进度队列（用于3D模型进度回调）
        placeholders: UI占位符字典
    """
    all_states = {}
    completed_steps = []
    json_displayed = False
    image_displayed = False

    async for state_update in workflow.astream(prompt):
        node_name = list(state_update.keys())[0] if state_update else ""
        node_data = state_update.get(node_name, {})

        # 合并状态
        if isinstance(node_data, dict):
            all_states.update(node_data)

        # 处理已知节点
        if node_name in WORKFLOW_NODES:
            completed_name, next_step = WORKFLOW_NODES[node_name]
            completed_steps.append(completed_name)

            # 更新进度显示
            with placeholders["progress"].container():
                render_progress_steps(completed_steps)

            # 更新状态显示
            if next_step:
                with placeholders["status"].container():
                    render_loading_status(next_step)

            # 保存JSON后展示角色档案
            if node_name == "save_npc_json" and not json_displayed:
                npc_json = all_states.get("npc_json", {})
                if npc_json:
                    placeholders["json_result"].markdown("### ✨ NPC角色生成中...\n")
                    placeholders["json_result"].markdown(format_npc_json_result(npc_json))
                    json_displayed = True

            # 保存图片后展示图片
            if node_name == "save_npc_image" and not image_displayed:
                npc_image_base64 = all_states.get("npc_image_base64")
                if npc_image_base64:
                    try:
                        placeholders["image"].image(
                            base64.b64decode(npc_image_base64),
                            caption="🖼️ 生成的角色图片",
                            width=400
                        )
                        image_displayed = True
                    except Exception as e:
                        logger.error(f"图片显示错误: {e}")

        logger.info(f"工作流节点完成: {node_name}")

    return all_states, json_displayed


def handle_workflow_mode(prompt: str):
    """处理工作流模式的用户输入"""
    with st.chat_message("assistant"):
        # 创建UI占位符
        placeholders = {
            "status": st.empty(),
            "progress": st.empty(),
            "json_result": st.empty(),
            "image": st.empty(),
            "model_progress": st.empty(),
            "final_result": st.empty(),
        }

        try:
            workflow = get_workflow()

            # 创建线程安全的进度队列
            progress_queue = queue.Queue()

            # 设置3D模型进度回调
            def model_progress_callback(progress: int, status_text: str):
                progress_queue.put((progress, status_text))

            GenerateNpcWorkflow.model_progress_callback = model_progress_callback

            # 初始状态
            with placeholders["status"].container():
                render_loading_status("检索世界观资料")

            # 运行异步工作流
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_with_progress():
                # 创建工作流任务
                workflow_task = asyncio.create_task(
                    run_workflow_async(workflow, prompt, progress_queue, placeholders)
                )

                last_progress = -1

                # 轮询更新3D模型进度
                while not workflow_task.done():
                    # 从队列获取进度更新（修复：之前没有读取队列）
                    try:
                        while not progress_queue.empty():
                            progress, status_text = progress_queue.get_nowait()
                            if progress != last_progress and progress >= 0:
                                last_progress = progress
                                with placeholders["model_progress"].container():
                                    render_model_progress(progress, status_text)
                    except queue.Empty:
                        pass

                    await asyncio.sleep(0.3)

                # 处理队列中剩余的进度更新
                try:
                    while not progress_queue.empty():
                        progress, status_text = progress_queue.get_nowait()
                        if progress >= 0:
                            with placeholders["model_progress"].container():
                                render_model_progress(progress, status_text)
                except queue.Empty:
                    pass

                return await workflow_task

            try:
                final_state, json_displayed = loop.run_until_complete(run_with_progress())
            finally:
                loop.close()

            # 清除状态显示
            placeholders["status"].empty()
            placeholders["model_progress"].empty()

            # 更新标题为完成状态
            if json_displayed:
                placeholders["json_result"].markdown(
                    "### ✨ NPC角色生成完成！\n" + format_npc_json_result(final_state.get("npc_json", {}))
                )

            # 显示最终文件路径
            placeholders["final_result"].markdown(format_final_result(final_state))

            # 保存完整消息到历史
            full_content = "### ✨ NPC角色生成完成！\n\n"
            full_content += format_npc_json_result(final_state.get("npc_json", {}))
            full_content += "\n\n"
            full_content += format_final_result(final_state)

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_content,
                "image_base64": final_state.get("npc_image_base64")
            })

        except Exception as e:
            logger.error(f"工作流执行错误: {e}")
            import traceback
            traceback.print_exc()

            error_msg = f"❌ 生成过程中出现错误:\n```\n{str(e)}\n```\n\n请检查日志获取详细信息。"
            placeholders["status"].empty()
            placeholders["progress"].empty()
            placeholders["model_progress"].empty()
            placeholders["json_result"].markdown(error_msg)

            st.session_state.messages.append({"role": "assistant", "content": error_msg})

        finally:
            GenerateNpcWorkflow.model_progress_callback = None


def handle_llm_mode(prompt: str):
    """处理大模型对话模式的用户输入"""
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        with response_placeholder.container():
            render_loading_status("思考")

        for chunk in stream_llm_response(prompt):
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})


# ==================== 主函数 ====================

def main():
    """主函数"""
    # 页面配置
    st.set_page_config(page_title="NPC角色生成器", page_icon="🎮", layout="wide")

    # 注入CSS和初始化状态
    inject_custom_css()
    init_session_state()

    # 渲染UI组件
    render_sidebar()
    st.title("🎮 NPC角色生成器")
    render_mode_selector()
    st.divider()
    render_welcome_message()

    # 显示历史消息
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"], msg.get("image_base64"))

    # 聊天输入框
    current_mode_config = MODE_CONFIG.get(st.session_state.chat_mode, {})
    prompt = st.chat_input(
        placeholder=current_mode_config.get("placeholder", ""),
        disabled=st.session_state.is_generating
    )

    # 处理用户输入
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_message("user", prompt)
        st.session_state.is_generating = True

        if st.session_state.chat_mode == ChatMode.LLM.value:
            handle_llm_mode(prompt)
        else:
            handle_workflow_mode(prompt)

        st.session_state.is_generating = False
        st.rerun()


if __name__ == "__main__":
    main()
