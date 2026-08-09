import asyncio

from config import config
from model import RerankModel
from utils import get_logger

from .bm25_retriever import BM25Retriever
from .vector_retriever import VectorRetriever

logger = get_logger(__name__)


class RetrievalManager:

    def __init__(self, rerank_top_k: int = None):
        self.bm25_retriever = BM25Retriever()
        self.vector_retriever = VectorRetriever()
        self.rerank_model = RerankModel()
        self.rerank_top_k = rerank_top_k or config["rag"]["rerank_top_k"]

    async def retrieve(self, query: str) -> list[str]:
        """
        整个检索流程:
        1. 混合检索 (BM25 检索向量检索)
        2. 去重和排序，返回最终的文档列表
        3. 使用重排模型对检索结果进行重排，提升结果的相关性和准确性
        """
        bm25_results, vector_results = await asyncio.gather(
            self.bm25_retriever.retrieve(query=query),
            self.vector_retriever.retrieve(query=query),
        )
        results = list(bm25_results) + list(vector_results)
        logger.debug(f"========== 混合检索去重前结果, {len(results)} 条")
        results = list(set(results))
        reranked_results = await self.rerank_model.rerank(query=query, texts=results)
        reranked_results = [item["text"] for item in reranked_results[: self.rerank_top_k]]
        logger.debug(
            f"========== 混合检索去重后取top结果, {len(reranked_results)} 条: \n{"\n==========\n".join(reranked_results)}"
        )
        return reranked_results
