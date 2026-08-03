import unittest

from dotenv import load_dotenv
load_dotenv()
from model import PreRetrievalLLM
from utils import setup_logger, get_logger

setup_logger()
logger = get_logger(__name__)


class TestPreRetrievalLLM(unittest.IsolatedAsyncioTestCase):

    # async def test_01(self):
    #     pre_retrieval_llm = PreRetrievalLLM()
    #     result = await pre_retrieval_llm.ainvoke("中国的首都是什么?")
    #     logger.info(result)
    #     logger.info(result.content)
    #     return result

    # async def test_02(self):
    #     pre_retrieval_llm = PreRetrievalLLM(temperature=0.3)
    #     result = await pre_retrieval_llm.rewrite_query("生成NPC角色, 形象要搞怪, 虽然看着很无厘头, 但是其实是一个实力非常强的雾隐村的村长")
    #     logger.info(result)
    #     return result

    # async def test_03(self):
    #     pre_retrieval_llm = PreRetrievalLLM(temperature=0.3)
    #     result = await pre_retrieval_llm.split_query("生成NPC角色, 形象要搞怪, 虽然看着很无厘头, 但是其实是一个实力非常强的雾隐村的村长")
    #     logger.info(result)
    #     return result

    async def test_04(self):
        pre_retrieval_llm = PreRetrievalLLM(temperature=0.5)
        result = await pre_retrieval_llm.rewrite_and_split(
            "生成NPC角色, 形象要搞怪, 虽然看着很无厘头, 但是其实是一个实力非常强的雾隐村的村长"
        )
        logger.info(result)
        return result


if __name__ == "__main__":
    unittest.main()
