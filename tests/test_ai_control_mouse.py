import asyncio
import unittest

from langchain.agents import create_agent
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.messages import HumanMessage
from langchain_experimental.tools import PythonREPLTool

from config import settings
from utils import FileUtil


class MyTestCase(unittest.TestCase):
    def test_ai_control(self):
        fs = FileUtil("data")
        # pip install langchain-experimental
        # 准备写入工具
        file_management_toolkit = FileManagementToolkit(root_dir="data/ai_auto_control")
        # REPL工具
        repl = PythonREPLTool()
        # agent的工具
        agent_tools = []
        agent_tools.extend(file_management_toolkit.get_tools())
        agent_tools.append(repl)
        print(f"\nagent的工具: {agent_tools}")
        # 创建agent
        system_prompt = "你是一个专业的python程序员."
        agent = create_agent(
            model=settings.models.chat_model,
            tools=agent_tools,
            system_prompt=system_prompt
        )
        # 让agent写一个python文件并运行
        prompt = "根据目前的屏幕截图,用pyautogui库写一个程序,从左下角的搜索框搜索'weixin'然后打开,自己决定所有的流程,你在root_dir可以随便操作,写完程序后自己检查代码,没问题的话利用[PythonREPLTool]运行程序"
        response = asyncio.run(agent.ainvoke({
            "messages": [HumanMessage(content=[
                {
                    "type": "text",
                    "text": prompt,
                }, {
                    "type": "image_url",
                    "image_url": {"url": fs.read_image("source/img.png")},
                }
            ])]
        }))

        print(response)

    # def test_control_mouse(self):
    #     # pip install pyautogui
    #
    #     # 给自己 3 秒钟准备时间，切换到你想操作的界面
    #     print("请在 3 秒内切换到目标窗口...")
    #     time.sleep(3)
    #
    #     # 1. 获取屏幕分辨率
    #     width, height = pyautogui.size()
    #     print(f"屏幕分辨率: {width} x {height}")
    #
    #     # 2. 移动鼠标 (moveTo)
    #     # 移动到屏幕中心，耗时 1 秒（不加 duration 会瞬间移动，太快了不像人）
    #     pyautogui.moveTo(width / 2, height / 2, duration=1)
    #
    #     # 3. 点击 (click)
    #     pyautogui.click()
    #
    #     # 4. 模拟拖拽（画一个正方形）
    #     distance = 200
    #     duration = 0.5
    #     pyautogui.dragRel(distance, 0, duration=duration)  # 向右拖
    #     pyautogui.dragRel(0, distance, duration=duration)  # 向下拖
    #     pyautogui.dragRel(-distance, 0, duration=duration)  # 向左拖
    #     pyautogui.dragRel(0, -distance, duration=duration)  # 向上拖
    #
    #     # 5. 打字输入
    #     pyautogui.write('Hello World', interval=0.5)


if __name__ == '__main__':
    unittest.main()
