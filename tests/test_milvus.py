import logging
import unittest

from db import Milvus
from model import Embedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "test_collection"
VECTOR_DIM = 512


class TestMilvus(unittest.IsolatedAsyncioTestCase):

    async def test_Milvus(self):
        embedding = Embedding()
        milvus = Milvus()

        texts = [f"这是第{i}条测试数据" for i in range(5)]
        vectors = await embedding.embed(texts)

        data = [{"vector": vector, "text": text} for i, (vector, text) in enumerate(zip(vectors, texts))]
        for i in range(len(data)):
            logger.info(f"插入数据: {data[i]['text']}... -> {data[i]['vector'][:5]}...")
        await milvus.insert(collection_name=COLLECTION_NAME, data=data)

        data = await embedding.embed(["第0条测试数据是错误的", "塞尔达的主要任务是什么"])
        for i in range(len(data)):
            logger.info(f"查询向量: {data[i][:5]}...")
        results = await milvus.search(collection_name=COLLECTION_NAME, data=data, output_fields=["text"])

        for item in results:
            logger.info(f"第{results.index(item)+1}条查询结果:")
            for res in item:
                logger.info(res)

        await milvus.drop_collection(collection_name=COLLECTION_NAME)

        await Embedding().close()
        await Milvus().close()


if __name__ == "__main__":
    unittest.main()
