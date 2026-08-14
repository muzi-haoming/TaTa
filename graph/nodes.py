import asyncio

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer

from agent import ChatAgent
from model import MediumLLM

from .state import State
from .tools import info_search

_chat_agent = None


def get_chat_agent():
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent(
            model=MediumLLM().get_model(),
            tools=[info_search],
            state_schema=State,
            system_prompt="你是一个助手，回答我的问题。当你需要更多信息来回答问题的时候，借助有用的工具来帮助你获取有用的信息。如果没有足够的信息，可以说明缺少哪些资料，而不是自己随便给出答案。",
        ).get_agent()
    return _chat_agent


# async def chat_node(state: State):
#     final_texts = []
#     writer = get_stream_writer()
#     stream = await _get_chat_agent().astream_events(
#         input={"messages": state["messages"]},
#         version="v3",
#     )

#     async def consume_messages():
#         async for model_msg in stream.messages:
#             # if model_msg.node not in MAIN_MODEL_NODES:
#             #     continue
#             async for text in model_msg.text:
#                 final_texts.append(text)
#                 writer(
#                     {
#                         "graph_node": "chat_node",
#                         "model_msg_node": model_msg.node,
#                         "text": text,
#                     }
#                 )

#     async def consume_tool_calls():
#         async for call in stream.tool_calls:
#             writer(
#                 {
#                     "graph_node": "chat_node",
#                     "model_msg_node": "tool_call",
#                     "tool_name": call.tool_name,
#                     "call_input": call.input,
#                     "call_output": call.output if not call.error else str(call.error),
#                 }
#             )
#             async for delta in call.output_deltas:
#                 writer(
#                     {
#                         "graph_node": "chat_node",
#                         "model_msg_node": "tool_call_delta",
#                         "delta": delta,
#                     }
#                 )

#     await asyncio.gather(consume_tool_calls(), consume_messages())

#     final_text = "".join(final_texts)

#     return {"messages": [AIMessage(content=final_text)]}
