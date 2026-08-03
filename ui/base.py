"""
页面基类

把每个 Streamlit 页面共有的骨架（页面配置 -> 注入样式 -> 初始化 session state
-> 渲染）收敛到 :class:`BasePage`，子类只实现 :meth:`BasePage.render`。
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Mapping

import streamlit as st

from .components import inject_css


class BasePage(ABC):
    """
    Streamlit 页面基类。

    子类通过类属性声明页面元信息，通过 :meth:`session_defaults` 声明需要的
    session state 字段（值为工厂函数，仅在缺失时调用）。
    """

    page_title: ClassVar[str] = "App"
    page_icon: ClassVar[str] = "🚀"
    layout: ClassVar[str] = "wide"
    custom_css: ClassVar[str] = ""

    # ==================== 生命周期 ====================

    def run(self) -> None:
        """页面入口：按固定顺序完成配置、样式、状态与渲染。"""
        st.set_page_config(
            page_title=self.page_title,
            page_icon=self.page_icon,
            layout=self.layout,
        )
        if self.custom_css:
            inject_css(self.custom_css)
        self.init_session_state()
        self.render()

    def session_defaults(self) -> Mapping[str, Callable[[], Any]]:
        """返回 ``{state 键: 默认值工厂}``；子类按需覆写。"""
        return {}

    def init_session_state(self) -> None:
        """为缺失的 session state 键填入默认值（已有值不会被覆盖）。"""
        for key, factory in self.session_defaults().items():
            if key not in st.session_state:
                st.session_state[key] = factory()

    def reset_session_state(self, *keys: str) -> None:
        """把指定键重置为默认值；不传参数时重置全部声明过的键。"""
        defaults = self.session_defaults()
        for key in keys or defaults.keys():
            if key in defaults:
                st.session_state[key] = defaults[key]()

    @abstractmethod
    def render(self) -> None:
        """渲染页面内容。"""

    # ==================== 便捷访问 ====================

    @property
    def state(self) -> Dict[str, Any]:
        """session state（等价于 ``st.session_state``，便于子类内简写）。"""
        return st.session_state
