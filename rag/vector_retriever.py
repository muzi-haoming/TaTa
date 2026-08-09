import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from config import config
from db import Milvus
from model import Embedding, LiteLLM
from schemas import RewrittenQueries, SplitedQueries
from utils import get_logger

logger = get_logger(__name__)


class VectorRetriever:
    def __init__(self, vector_top_k: int = None):
        self.llm = LiteLLM(temperature=0.5)
        self.embedding = Embedding()
        self.milvus = Milvus()
        self.vector_top_k = vector_top_k or config["rag"]["vector_top_k"]

    async def _rewrite_query(self, query: str) -> RewrittenQueries:
        rewrite_system_prompt = (
            "你是一个AI语言模型助手.\n"
            "你的任务是针对给定的用户问题生成3个不同的版本, 以便从向量数据库中检索相关文档.\n"
            "通过为用户问题提供多种视角, 你的目标是帮助用户克服基于距离的相似性搜索的一些局限性.\n"
            '返回json格式的字典: {"queries": ["改写问题1", "改写问题2", "改写问题3"]}\n'
        )
        system_message = SystemMessage(content=rewrite_system_prompt)
        human_message = HumanMessage(content=f"原始问题: {query}")
        rewritten_queries: RewrittenQueries = (
            await self.llm.get_model().with_structured_output(RewrittenQueries).ainvoke([system_message, human_message])
        )
        return rewritten_queries

    async def _split_query(self, query: str) -> SplitedQueries:
        split_system_prompt = (
            "你是一个AI语言模型助手。\n"
            "你的任务是将用户提出的复杂问题拆解为若干个更简单、更独立的子问题，以便分别从向量数据库中检索相关文档。\n"
            "每个子问题应该只聚焦一个具体的信息点，避免包含多个并列的诉求。\n"
            "如果原始问题本身已经足够简单、不需要拆分，直接返回原始问题本身即可，不要强行拆分。\n"
            '返回json格式的字典: {"queries": ["子问题1", "子问题2", "子问题3"]}\n'
        )
        system_message = SystemMessage(content=split_system_prompt)
        human_message = HumanMessage(content=f"原始问题: {query}")
        splited_queries: SplitedQueries = (
            await self.llm.get_model().with_structured_output(SplitedQueries).ainvoke([system_message, human_message])
        )
        return splited_queries

    async def _rewrite_and_split(self, query: str) -> list[str]:
        rewritten_queries, splited_queries = await asyncio.gather(
            self._rewrite_query(query),
            self._split_query(query),
        )
        return list(set([query] + rewritten_queries.queries + splited_queries.queries))

    async def retrieve(self, query: str) -> list[str]:
        logger.debug(f"========== 开始 vector 检索, 检索内容: \n{query} ")
        queries = await self._rewrite_and_split(query)
        logger.debug(f"========== 重写和拆分后的检索内容, {len(queries)} 条: \n{"\n==========\n".join(queries)}")
        vectors = await self.embedding.embed(queries)
        milvus_search_results = await self.milvus.search(
            collection_name=config["rag"]["collection_name"]["background_info"],
            data=vectors,
            output_fields=["content"],
        )
        results = [
            item["entity"]["content"] for milvus_search_result in milvus_search_results for item in milvus_search_result
        ]
        logger.debug(f"========== vector 检索去重前的结果, {len(results)} 条")
        results = list(set(results))
        logger.debug(f"========== vector 检索去重后的结果, {len(results)} 条")
        # logger.debug(f"========== vector 检索去重后的结果, {len(results)} 条: \n{"\n==========\n".join(results)}")
        return results
