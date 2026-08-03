"""检索器工厂与背景资料检索"""
from functools import lru_cache
from typing import Iterable

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from config import settings

from .vector_store import create_vector_store

#: 多个文档片段之间的拼接分隔符
LORE_SEPARATOR = "\n\n"


@lru_cache(maxsize=1)
def create_retriever() -> VectorStoreRetriever:
    """创建（并进程内缓存）向量检索器。"""
    retriever_config = settings.retriever
    return create_vector_store().as_retriever(
        search_type=retriever_config.search_type,
        search_kwargs=retriever_config.search_kwargs.model_dump(),
    )


def _join_documents(docs: Iterable[Document]) -> str:
    """把检索到的文档片段拼成一段可直接喂给大模型的文本。"""
    return LORE_SEPARATOR.join(doc.page_content for doc in docs)


def search_lore(query: str) -> str:
    """检索与 ``query`` 相关的背景资料片段。"""
    return _join_documents(create_retriever().invoke(query))


async def asearch_lore(query: str) -> str:
    """[异步] 检索与 ``query`` 相关的背景资料片段。"""
    return _join_documents(await create_retriever().ainvoke(query))
