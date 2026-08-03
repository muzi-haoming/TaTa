"""向量库工厂"""
from functools import lru_cache

from langchain_chroma import Chroma

from config import settings
from utils import FileUtil

from .embedding_model import create_embedding_model


@lru_cache(maxsize=1)
def create_vector_store() -> Chroma:
    """创建（并进程内缓存）Chroma 向量库实例。"""
    return Chroma(
        collection_name=settings.vector_store.collection_name,
        embedding_function=create_embedding_model(),
        persist_directory=str(FileUtil(settings.vector_store.persist_directory).root),
    )
