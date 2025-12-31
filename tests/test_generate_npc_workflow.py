import asyncio
import unittest

from workflows.generate_npc_workflow import GenerateNpcWorkflow


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self._prompt = "一个照顾花田的利特族人,不允许任何人触碰"
        self._thread_id = "959"
        self._workflow = GenerateNpcWorkflow(self._thread_id)

    async def generate_npc_work_flow(self):
        async for event in self._workflow.astream_events(self._prompt):
            kind = event.get("event")

        state = self._workflow.app.get_state(config={"configurable": {"thread_id": self._thread_id}})
        while state.next != ():
            print(state)
            interrupt_info = state.interrupts[0]
            question = interrupt_info.value["question"]
            details = interrupt_info.value["details"]

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


if __name__ == '__main__':
    unittest.main()
