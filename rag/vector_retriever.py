from model import LiteLLM, Embedding
from schemas import RewrittenQueries, SplitedQueries
from db import Milvus
from config import config

from langchain_core.messages import HumanMessage, SystemMessage


class VectorRetriever:
    def __init__(self):
        self.lite_llm = LiteLLM()
        self.embedding = Embedding()
        self.milvus = Milvus()

    async def _rewrite_query(self, query: str) -> dict:
        REWRITE_SYSTEM_PROMPT = (
            "你是一个AI语言模型助手. "
            "你的任务是针对给定的用户问题生成3个不同的版本, 以便从向量数据库中检索相关文档. "
            "通过为用户问题提供多种视角, 你的目标是帮助用户克服基于距离的相似性搜索的一些局限性. "
            f"原始问题: {query}"
            '输出结构: {"queries": ["改写问题1", "改写问题2", "改写问题3"]}'
        )
        system_message = SystemMessage(content=REWRITE_SYSTEM_PROMPT)
        human_message = HumanMessage(content=query)
        response = await self.lite_llm.ainvoke(input=[system_message, human_message], pydantic_model=RewrittenQueries)

        return response

    async def _split_query(self, query: str) -> dict:
        SPLIT_SYSTEM_PROMPT = (
            "你是一个AI语言模型助手。"
            "你的任务是将用户提出的复杂问题拆解为若干个更简单、更独立的子问题，以便分别从向量数据库中检索相关文档。"
            "每个子问题应该只聚焦一个具体的信息点，避免包含多个并列的诉求。"
            "如果原始问题本身已经足够简单、不需要拆分，直接返回原始问题本身即可，不要强行拆分。"
            f"原始问题：{query}"
            '输出结构: {"queries": ["子问题1", "子问题2", "子问题3"]}'
        )
        system_message = SystemMessage(content=SPLIT_SYSTEM_PROMPT)
        human_message = HumanMessage(content=query)
        response = await self.lite_llm.ainvoke(input=[system_message, human_message], pydantic_model=SplitedQueries)

        return response

    async def _rewrite_and_split(self, query: str) -> list[str]:
        rewritten = (await self._rewrite_query(query)).get("queries", [query])
        split = (await self._split_query(query)).get("queries", [query])
        return list(set([query] + rewritten + split))

    async def retrieve(self, query: str) -> list[str]:
        queries = await self._rewrite_and_split(query)
        vectors = await self.embedding.embed(queries)
        return self.milvus.search(
            collection_name=config["rag"]["collection_name"]["background_info"],
            data=vectors,
            limit=5,
            output_fields=["content"],
        )
