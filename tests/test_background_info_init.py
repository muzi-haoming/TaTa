import logging
import pickle
import unittest
from pathlib import Path

import jieba
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from rank_bm25 import BM25Okapi

from config import config
from db import Milvus
from model import Embedding
from utils import get_logger, setup_logger, split_docs

setup_logger(logging.DEBUG)
logger = get_logger(__name__)

BACKGROUND_INFO_FOLDER = "data/background_info/"  # 文件夹路径
BM25_INDEX_PATH = config["rag"]["bm25_index_path"]  # BM25 索引文件路径
COLLECTION_NAME = config["rag"]["collection_name"]["background_info"]  # Milvus collection 名


class TestBackgroundInfoInit(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        loader = DirectoryLoader(
            BACKGROUND_INFO_FOLDER, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}
        )
        docs = loader.load()
        cls.chunks = split_docs(docs)

    def test_index(self):
        self.assertGreater(len(self.chunks), 0)
        # 对每个 chunk 分词
        tokenized_chunks = [list(jieba.cut(doc.page_content)) for doc in self.chunks]
        logger.debug(f"共分词出 {len(tokenized_chunks)} 个 chunk")
        # 用分词结果建 BM25 索引
        bm25 = BM25Okapi(tokenized_chunks)
        # 把索引 + chunks 列表持久化到本地文件
        Path(BM25_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(BM25_INDEX_PATH, "wb") as f:  # 注意是 "wb"，二进制写入
            pickle.dump({"bm25": bm25, "chunks": self.chunks}, f)

    async def test_embedding_save(self):
        embedding = Embedding()
        # 获取 MilvusClient 实例
        milvus = Milvus()
        # 删除 collection，避免冲突
        await milvus.drop_collection(collection_name=COLLECTION_NAME)
        # 获取 chunks 的 embedding 向量
        vectors = await embedding.embed([doc.page_content for doc in self.chunks])
        # 将向量和 chunks 保存到 Milvus
        data = [
            {"vector": vector, "content": doc.page_content} for vector, doc in zip(vectors, self.chunks, strict=True)
        ]
        # 将数据插入 Milvus
        resp = await milvus.insert(collection_name=COLLECTION_NAME, data=data)
        logger.debug(f"插入数据成功，影响行数：{resp.get("insert_count")}")

        await embedding.close()
        await milvus.close()


if __name__ == "__main__":
    # python -m tests.test_background_info_init
    unittest.main()
