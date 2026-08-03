from model import PreRetrievalLLM


class RetrievalManager:

    def __init__(self):
        self.pre_retrieval_llm = PreRetrievalLLM()


    def retrieve(self, query: str) -> list[str]:
        """
        整个检索流程:
        1. 使用 PreRetrievalLLM 对用户查询进行改写和拆分，生成多个查询版本。
        2. 对每个查询版本进行混合检索(BM25 + 向量)，获取相关文档。
        3. 将所有检索结果进行去重和排序，返回最终的文档列表。
        4. 使用重排模型对检索结果进行重排，提升结果的相关性和准确性。
        """