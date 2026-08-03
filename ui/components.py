"""
可复用 UI 组件

每个函数只负责「把某种状态渲染成 HTML/控件」，不读写 session state，
便于在不同页面间复用与单独调整样式。
"""
import base64
from typing import Optional, Sequence

import streamlit as st

from utils import logger


def inject_css(css: str) -> None:
    """注入自定义 CSS。"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_loading_status(step_name: str) -> None:
    """渲染「正在 xxx...」的加载指示条。"""
    st.markdown(
        f"""
        <div class="loading-indicator">
            <div class="loading-spinner"></div>
            <span>正在{step_name}...</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress_steps(completed_steps: Sequence[str]) -> None:
    """渲染已完成步骤的标签串。"""
    if not completed_steps:
        return
    steps_html = " ".join(f'<span class="progress-step">✅ {step}</span>' for step in completed_steps)
    st.markdown(f'<div class="progress-steps">{steps_html}</div>', unsafe_allow_html=True)


def render_model_progress(progress: int, status_text: str) -> None:
    """渲染 3D 模型生成进度条。"""
    st.markdown(
        f"""
        <div class="model-progress-container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>🎮 {status_text}</span>
                <span style="font-weight: bold; color: #667eea;">{progress}%</span>
            </div>
            <div class="model-progress-bar">
                <div class="model-progress-fill" style="width: {progress}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_base64_image(placeholder, image_base64: str, caption: str, width: int = 400) -> bool:
    """
    在给定占位符中渲染 base64 图片。

    :return: 是否渲染成功（解码失败时记录日志并返回 False）。
    """
    try:
        placeholder.image(base64.b64decode(image_base64), caption=caption, width=width)
        return True
    except Exception as e:
        logger.error(f"图片显示错误: {e}")
        return False


def render_message(role: str, content: str, image_base64: Optional[str] = None) -> None:
    """渲染一条聊天消息（可带图片）。"""
    with st.chat_message(role):
        st.markdown(content)
        if image_base64:
            render_base64_image(st, image_base64, caption="生成的角色图片")
