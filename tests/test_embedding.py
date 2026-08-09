import unittest
from dotenv import load_dotenv
load_dotenv()
from model import Embedding
from utils import setup_logger, get_logger

setup_logger()
logger = get_logger(__name__)

class TestEmbedding(unittest.IsolatedAsyncioTestCase):

    async def test_embedding(self):
        embedding = Embedding()

        vec_list = await embedding.embed(["这是一段测试文本", "这是另外一段测试文本"])
        logger.info(f"向量数量: {len(vec_list)}")
        logger.info(f"向量维度: {len(vec_list[0]) if vec_list else 0}")
        for v in vec_list:
            logger.info(f"向量前 5 位: {v[:5]}")

if __name__ == "__main__":
    unittest.main()