import unittest
import logging
import jieba
import pickle

from model import Embedding
from db import Milvus
from utils import split_docs
from rank_bm25 import BM25Okapi
from pathlib import Path
from config import config

from langchain_community.document_loaders import DirectoryLoader, TextLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKGROUND_INFO_FOLDER = "data/background_info/"
BM25_INDEX_PATH = config["rag"]["bm25_index_path"]
COLLECTION_NAME = config["rag"]["collection_name"]["background_info"]
VECTOR_DIM = 512


class TestBackgroundInfoInit(unittest.TestCase):
    def setUp(self):
        loader = DirectoryLoader(
            BACKGROUND_INFO_FOLDER, glob="**/*.md",
            loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}
        )
        docs = loader.load()
        self.chunks = split_docs(docs)

    def test_index(self):
        self.assertGreater(len(self.chunks), 0)
        # 对每个 chunk 分词
        tokenized_chunks = [list(jieba.cut(doc.page_content)) for doc in self.chunks]
        logger.info(f"共分词出 {len(tokenized_chunks)} 个 chunk")
        # 用分词结果建 BM25 索引
        bm25 = BM25Okapi(tokenized_chunks)
        # 把索引 + chunks 列表持久化到本地文件
        Path(BM25_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(BM25_INDEX_PATH, "wb") as f:   # 注意是 "wb"，二进制写入
            pickle.dump({"bm25": bm25, "chunks": self.chunks}, f)

    def test_embedding_save(self):
        embedding = Embedding()
        milvus = Milvus()

        vectors = embedding.embed([doc.page_content for doc in self.chunks])

        data = [{"vector": vector, "content": doc.page_content} for vector, doc in zip(vectors, self.chunks)]
        milvus.insert(collection_name=COLLECTION_NAME, data=data)

    # def test_search_background_info(self):
    #     embedding = Embedding()
    #     milvus = Milvus()

    #     query_texts = ["雾溪村每个人有什么共同点？"]
    #     query_vectors = embedding.embed(query_texts)

    #     for i in range(len(query_vectors)):
    #         logger.info(f"查询向量: {query_vectors[i][:5]}...")
    #     results = milvus.search(collection_name=COLLECTION_NAME, data=query_vectors, limit=3, output_fields=["content"])

    #     for item in results:
    #         logger.info(f"第{results.index(item)+1}条查询结果:")
    #         for res in item:
    #             logger.info(res["content"][:50] + "..." + f" 相似度: {res["distance"]}")


if __name__ == "__main__":
    unittest.main()
