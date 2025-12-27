import asyncio
import unittest

from workflows import AiAutoControlWorkflow


class MyTestCase(unittest.TestCase):
    def test_something(self):
        workflow = AiAutoControlWorkflow()
        asyncio.run(workflow.ainvoke("打开微信,给'养殖场老板'发送一条消息: '你刚刚吃什么了?''"))


if __name__ == '__main__':
    unittest.main()
