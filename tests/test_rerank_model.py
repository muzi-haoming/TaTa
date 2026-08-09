import unittest
import logging

from model import RerankModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRerankModel(unittest.IsolatedAsyncioTestCase):

    async def test_01(self):
        rerank = RerankModel()
        await rerank.health()
        results = await rerank.rerank("我想去广州", texts=["我去了北京", "我去了上海", "我去了广州"])
        logger.info(results)


if __name__ == "__main__":
    unittest.main()
