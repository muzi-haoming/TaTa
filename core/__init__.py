"""
核心能力模块

- 模型 / 向量库 / 检索器的工厂（进程内单实例）
- 大模型结构化输出定义
- 提示词常量
"""
from . import prompts
from .embedding_model import create_embedding_model
from .response_structure import (
    EvaluatorResponseStructure,
    ImageGeneratePromptResponseStructure,
    ImageResponseStructure,
    NPCGenerationResponseStructure,
    ReviewResponseStructure,
    SavingResponseStructure,
)
from .retriever import asearch_lore, create_retriever, search_lore
from .vector_store import create_vector_store

__all__ = [
    "prompts",
    "create_embedding_model",
    "create_vector_store",
    "create_retriever",
    "search_lore",
    "asearch_lore",
    "ReviewResponseStructure",
    "NPCGenerationResponseStructure",
    "EvaluatorResponseStructure",
    "SavingResponseStructure",
    "ImageResponseStructure",
    "ImageGeneratePromptResponseStructure",
]
