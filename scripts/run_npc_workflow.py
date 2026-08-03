"""
在终端里端到端跑一遍 NPC 生成工作流（交互式，会真实调用大模型与 Meshy）

运行::

    python -m scripts.run_npc_workflow
    python -m scripts.run_npc_workflow "一个照顾花田的利特族人,不允许任何人触碰"

流程遇到人工审核节点时会中断并在终端提问，输入 1 通过、2 驳回并给出修改意见。
"""
import asyncio
import sys
from typing import Optional, Tuple

from utils import logger
from workflows import GenerateNpcWorkflow

DEFAULT_PROMPT = "一个照顾花田的利特族人,不允许任何人触碰"
DEFAULT_THREAD_ID = "959"

#: 中断详情过长（如图片 base64）时的展示上限
_DETAIL_PREVIEW = 500


def _ask_review(question: str, details: str) -> Tuple[bool, Optional[str]]:
    """在终端询问人工审核结果。"""
    preview = details if len(details) <= _DETAIL_PREVIEW else f"{details[:_DETAIL_PREVIEW]}...(已截断)"
    choice = input(f"\n中断: \n{preview}\n{question}\n(1通过/2拒绝): ").strip()
    if choice == "1":
        return True, None
    return False, input("\n请输入修改意见: ")


async def run(prompt: str, thread_id: str = DEFAULT_THREAD_ID) -> None:
    """跑完整个工作流，遇到中断就在终端交互续跑。"""
    workflow = GenerateNpcWorkflow(thread_id=thread_id)

    async for _ in workflow.astream_events(prompt):
        pass

    state = workflow.get_state()
    while state.next != ():
        interrupt_info = state.interrupts[0]
        is_ok, feedback = _ask_review(
            interrupt_info.value["question"], str(interrupt_info.value["details"])
        )

        async for _ in workflow.astream_events_continue({"is_ok": is_ok, "feedback": feedback}):
            pass

        state = workflow.get_state()

    logger.info(f"工作流结束，最终状态键: {sorted(state.values)}")


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    asyncio.run(run(prompt))


if __name__ == "__main__":
    main()
