"""NPC 生成 Agent 可调用的工具"""
from langchain.tools import tool

from core import search_lore


@tool
def search_relevent_lore(query_content: str) -> str:
    """
    功能：搜索故事背景中与参数相关的背景资料

    参数：query_content -> 角色关键词或描述

    返回：相关背景资料片段
    """
    return search_lore(query_content)
