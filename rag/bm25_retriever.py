import jieba
import pickle

from config import config


class BM25Retriever:
    def __init__(self):
        self.bm25_index_path = config["rag"]["bm25_index_path"]

    def retrieve(self, query: str) -> list[str]:
        # 对查询进行分词
        tokenized_query = list(jieba.cut(query))
        # 加载 BM25 索引和 chunks 列表
        with open(self.bm25_index_path, "rb") as f:  # 注意是 "rb"，二进制读取
            loaded = pickle.load(f)
            bm25 = loaded["bm25"]
            chunks = loaded["chunks"]
        # 使用 BM25 索引进行检索，返回 top 5 的结果
        results = bm25.get_top_n(tokenized_query, chunks, n=5)
        return results
