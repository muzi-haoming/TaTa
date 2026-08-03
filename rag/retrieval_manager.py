from model import PreRetrievalLLM
from .bm25_retriever import BM25Retriever
from .vector_retriever import VectorRetriever


class RetrievalManager:

    def __init__(self):
        self.pre_retrieval_llm = PreRetrievalLLM()
        self.bm25_retriever = BM25Retriever()
        self.vector_retriever = VectorRetriever()


    def retrieve(self, query: str) -> list[str]:
        """
        整个检索流程:
        1. 混合检索 (BM25 检索向量检索)
        2. 去重和排序，返回最终的文档列表
        3. 使用重排模型对检索结果进行重排，提升结果的相关性和准确性
        """
        results = []
        results.extend(self.bm25_retriever.retrieve(query=query))
        results.extend(self.vector_retriever.retrieve(query=query))
        