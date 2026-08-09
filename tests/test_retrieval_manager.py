import logging
import unittest

from dotenv import load_dotenv

load_dotenv()

from utils import get_logger, setup_logger

setup_logger(logging.DEBUG)
logger = get_logger(__name__)

from rag import RetrievalManager


class TestRetrievalManager(unittest.IsolatedAsyncioTestCase):

    async def test_01(self):
        query = "生成NPC角色, 形象要搞怪, 虽然看着很无厘头, 但是其实是一个实力非常强的雾隐村的村长"
        retrieval_manager = RetrievalManager()
        results = await retrieval_manager.retrieve(query=query)
        logger.debug(f"========== 最终结果: \n{"\n==========\n".join(results)}")


if __name__ == "__main__":
    unittest.main()
