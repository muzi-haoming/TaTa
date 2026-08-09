import asyncio
import pickle

import jieba

from config import config
from utils import get_logger

logger = get_logger(__name__)


class BM25Retriever:
    def __init__(self):
        self.bm25_index_path = config["rag"]["bm25_index_path"]
        self.bm25_top_k = config["rag"]["bm25_top_k"]

    def _retrieve_sync(self, query: str) -> list[str]:
        logger.debug(f"========== 开始 bm25 检索, 检索内容: \n{query}")
        # 对查询进行分词
        tokenized_queries = list(jieba.cut(query))
        tokenized_queries = [
            tokenized_query
            for tokenized_query in tokenized_queries
            if tokenized_query.strip() and tokenized_query.strip() not in ["，", "。", ",", ".", "?", "!", "？", "！"]
        ]
        logger.debug(
            f"========== bm25 检索, 分词后的检索内容, {len(tokenized_queries)} 条: \n{"\n==========\n".join(tokenized_queries)}"
        )
        # 加载 BM25 索引和 chunks 列表
        with open(self.bm25_index_path, "rb") as f:
            loaded = pickle.load(f)
            bm25 = loaded["bm25"]
            chunks = loaded["chunks"]
        # 使用 BM25 索引进行检索，返回 top 5 的结果
        results = bm25.get_top_n(tokenized_queries, chunks, n=self.bm25_top_k)
        results = [doc.page_content for doc in results]
        logger.debug(f"========== bm25 去重前检索结果, {len(results)} 条")
        results = list(set(results))
        logger.debug(f"========== bm25 去重后检索结果, {len(results)} 条")
        # logger.debug(f"========== bm25 去重后检索结果, {len(results)} 条: \n{"\n==========\n".join(results)}")
        return results

    async def retrieve(self, query: str) -> list[str]:
        return await asyncio.to_thread(self._retrieve_sync, query)
