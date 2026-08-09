import logging
import unittest

from dotenv import load_dotenv

load_dotenv()

from agent import AssistantAgent
from utils import get_logger, setup_logger

setup_logger(logging.DEBUG)
logger = get_logger(__name__)


class TestAssistantAgent(unittest.IsolatedAsyncioTestCase):

    async def test_01(self):
        assistant_agent = AssistantAgent().get_agent()
        stream = await assistant_agent.astream_events(
            input={
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个助手，回答我的问题。当你需要更多信息来回答问题的时候，可以借助有用的工具来帮助你获取有用的信息。",
                    },
                    {"role": "user", "content": "告诉我雾溪村的相关信息"},
                ]
            },
            version="v3",
        )
        async for message in stream.messages:
            async for delta in message.text:
                print(delta, end="", flush=True)
            logger.debug(f"========== [{message.node}] {await message.text}")


if __name__ == "__main__":
    unittest.main()
