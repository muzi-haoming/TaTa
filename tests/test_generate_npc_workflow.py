import asyncio
import unittest

from workflows.generate_npc_workflow import GenerateNpcWorkflow


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self._prompt = "一个照顾花田的利特族人,不允许任何人触碰"
        self._workflow = GenerateNpcWorkflow()

    async def generate_npc_work_flow(self):
        interrupt_info = await self._workflow.ainvoke(self._prompt)
        number = input(f"\n中断信息: \n{interrupt_info["npc_json"]}\n"
                       f"是否通过?(1通过/2拒绝)")
        if number == "1":
            is_ok = True
            feedback = None
        else:
            is_ok = False
            feedback = input(f"\n请输入修改意见: ")

        interrupt_info = await self._workflow.ainvoke_continue({"is_ok": is_ok, "feedback": feedback})

        number = input(f"\n中断信息: \n{interrupt_info}\n"
                       f"是否通过?(1通过/2拒绝)")
        if number == "1":
            is_ok = True
            feedback = None
        else:
            is_ok = False
            feedback = input(f"\n请输入修改意见: ")

        interrupt_info = await self._workflow.ainvoke_continue({"is_ok": is_ok, "feedback": feedback})

        number = input(f"\n中断信息: \n{interrupt_info}\n"
                       f"是否通过?(1通过/2拒绝)")
        if number == "1":
            is_ok = True
            feedback = None
        else:
            is_ok = False
            feedback = input(f"\n请输入修改意见: ")

        interrupt_info = await self._workflow.ainvoke_continue({"is_ok": is_ok, "feedback": feedback})

        number = input(f"\n中断信息: \n{interrupt_info}\n"
                       f"是否通过?(1通过/2拒绝)")
        if number == "1":
            is_ok = True
            feedback = None
        else:
            is_ok = False
            feedback = input(f"\n请输入修改意见: ")

        interrupt_info = await self._workflow.ainvoke_continue({"is_ok": is_ok, "feedback": feedback})

        number = input(f"\n中断信息: \n{interrupt_info}\n"
                       f"是否通过?(1通过/2拒绝)")
        if number == "1":
            is_ok = True
            feedback = None
        else:
            is_ok = False
            feedback = input(f"\n请输入修改意见: ")

        interrupt_info = await self._workflow.ainvoke_continue({"is_ok": is_ok, "feedback": feedback})

    def test_generate_npc_work_flow(self):
        asyncio.run(self.generate_npc_work_flow())


    # def test_generate_npc_model(self):
    #     fs = FileUtil("data/npc_generation")
    #     model = meshy_service
    #
    #     npc_image_base64 = fs.read_image("艾拉拉/艾拉拉.png", True)
    #     task_id = model.create_image_to_3d_task(npc_image_base64)
    #     logger.info(f"\n\n\n3D模型生成任务ID: {task_id}")
    #     progress = 0
    #     glb_url = None
    #     for update in model.image_to_3d.listen(task_id):
    #         current_progress = update.get('progress', 0)
    #         status = update.get('status', 'UNKNOWN')
    #         logger.info(f"\n3D模型生成状态 [STATUS] Task {status}")
    #         if status in ["SUCCEEDED", "FAILED", "CANCELED"]:
    #             if status == "SUCCEEDED":
    #                 glb_url = update.get("model_urls").get("glb")
    #             break
    #         if current_progress != progress:
    #             progress = current_progress
    #             logger.info(f"\n3D模型生成进度 [STATUS] Task {current_progress}%")
    #
    #     direct_path = None
    #     npc_model_path = "艾拉拉/艾拉拉.glb"
    #     if glb_url:
    #         direct_path = asyncio.run(fs.download_file(npc_model_path, glb_url))
    #
    #     print(direct_path)


    # def test_generate_image(self):
    #     client = genai.Client(
    #         vertexai=True,
    #         project="tata-npc-architect-system",
    #         location="us-central1",
    #     )
    #
    #     response = client.models.generate_images(
    #         model='imagen-4.0-generate-001',
    #         prompt=("一个格鲁德人  塞尔达风格  全身  T-Pose  背景纯白色  头身比4"),
    #         config={
    #             "number_of_images": 1,
    #         }
    #     )
    #     for generated_image in response.generated_images:
    #         print(FileUtil("data/npc_generation").write_bytes("asd.png", generated_image.image.image_bytes))
    #
    # def test_optimize_image(self):
    #     # client = genai.Client(
    #     #     vertexai=True,
    #     #     project="tata-npc-architect-system",
    #     #     location="us-central1",
    #     # )
    #     #
    #     # input_image = Image.open("data/npc_generation/asd.png")
    #     # # input_image = Image.open(io.BytesIO(img_bytes))
    #     #
    #     # response = client.models.generate_content(
    #     #     model='gemini-2.5-flash-image',
    #     #     contents=["给他带一个牛仔帽", input_image],
    #     # )
    #     # for generated_image in response.generated_images:
    #     #     print(FileUtil("data/npc_generation").write_bytes("asd.png", generated_image.image.image_bytes))
    #
    #     input_image = FileUtil("data/npc_generation").read_image("asd.png", True)
    #
    #     system_prompt = ("你是一个资深的游戏设计师,精通游戏角色图片设计.\n\n"
    #                      "目标是根据输入[prompt]生成一个png格式的角色图片.")
    #
    #     generate_npc_image_model = (
    #         init_chat_model(model="google_vertexai:gemini-2.5-flash-image")
    #         .bind(system_prompt=system_prompt))
    #
    #     # response = generate_npc_image_model.invoke([HumanMessage(content=[
    #     #     {
    #     #         "type": "text",
    #     #         "text": "[prompt]: 给他带一个牛仔帽",
    #     #     }, {
    #     #         "type": "image_url",
    #     #         "image_url": {"url": input_image}
    #     #     }
    #     # ])])
    #
    #     response = generate_npc_image_model.invoke([HumanMessage(content=[
    #         {
    #             "type": "text",
    #             "text": "[prompt]: 给他带一个牛仔帽",
    #         }, {
    #             "type": "image_url",
    #             "image_url": {"url": input_image}
    #         }
    #     ])])
    #
    #     # image_base64 = response.content[0].get("image_url").get("url")
    #     # FileUtil("data/npc_generation").write_image("ascccccc.png", image_base64)
    #
    #     # print(image_base64)
    #     print(response)


if __name__ == '__main__':
    unittest.main()
