from langchain.tools import tool

from core import create_retriever


@tool
def search_relevent_lore(query_content: str) -> str:
    """
    功能：搜索故事背景中与参数相关的背景资料

    参数：query_content -> 角色关键词或描述

    返回：相关背景资料片段
    """
    retriever = create_retriever()
    docs = retriever.invoke(query_content)
    results = f"{"\n\n".join(doc.page_content for doc in docs)}"
    return results
