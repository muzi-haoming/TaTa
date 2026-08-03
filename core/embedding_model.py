"""Embedding 模型工厂"""
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import settings


@lru_cache(maxsize=1)
def create_embedding_model() -> Embeddings:
    """创建（并进程内缓存）Embedding 模型实例。"""
    return GoogleGenerativeAIEmbeddings(model=settings.models.embedding_model)
