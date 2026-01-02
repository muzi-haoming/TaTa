import asyncio
import base64
import unittest

from PIL import Image
from google import genai
from google.genai import types
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from config import settings
from utils import FileUtil
from workflows.generate_npc_workflow import GenerateNpcWorkflow


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self._prompt = "一个照顾花田的利特族人,不允许任何人触碰"
        self._thread_id = "959"
        self._settings = settings
        self._workflow = GenerateNpcWorkflow(thread_id=self._thread_id)

    async def generate_npc_work_flow(self):
        async for event in self._workflow.astream_events(self._prompt):
            kind = event.get("event")

        state = self._workflow.app.get_state(config={"configurable": {"thread_id": self._thread_id}})
        while state.next != ():
            # print(state)
            interrupt_info = state.interrupts[0]
            question = interrupt_info.value["question"]
            details = str(interrupt_info.value["details"])

            number = input(f"\n中断: \n{details}\n"
                           f"{question}\n(1通过/2拒绝): ")
            if number == "1":
                is_ok = True
                feedback = None
            else:
                is_ok = False
                feedback = input(f"\n请输入修改意见: ")

            async for event in self._workflow.astream_events_continue({"is_ok": is_ok, "feedback": feedback}):
                kind = event.get("event")

            state = self._workflow.app.get_state(config={"configurable": {"thread_id": self._thread_id}})


    def test_generate_npc_work_flow(self):
        asyncio.run(self.generate_npc_work_flow())


    # def test_optimize_image(self):
    #     # model = init_chat_model(settings.models.image_model)
    #     # async def optimization():
    #     #     response = asyncio.run(model.ainvoke([HumanMessage(content=[
    #     #         {
    #     #             "type": "text",
    #     #             "text": "换个发型,换个飞机头",
    #     #         }, {
    #     #             "type": "image_url",
    #     #             "image_url": {"url": FileUtil("data/npc_generation").read_image("米洛/米洛.png", True)}
    #     #         }
    #     #     ])]))
    #     #     return response
    #     #
    #     # npc_image_base64 = optimization.content[0].get("image_url").get("url")
    #
    #     image = Image.open("C:\\Users\\muzi_\\Data\\PycharmData\\TaTa\\data\\npc_generation\\米洛\\米洛.png")
    #     if max(image.size) > 1024:
    #         image.thumbnail((1024, 1024))
    #     client = genai.Client(
    #         vertexai=True,
    #         project=self._settings.google_cloud.project,
    #         location=self._settings.google_cloud.location
    #     )
    #     response = client.models.generate_content(
    #         model="gemini-2.5-flash-image",
    #         contents=["换个发型,换个飞机头", image],
    #     )
    #     image_bytes = response.candidates[0].content.parts[0].inline_data.data
    #     npc_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    #     print(type(npc_image_base64))
    #     FileUtil("data/npc_generation").write_image("qweqweqweqwe.png", npc_image_base64)





if __name__ == '__main__':
    unittest.main()
