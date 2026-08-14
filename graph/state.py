from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict):
    input: str
    route_mode: Literal["chat", "character_generation"] = "chat"
    messages: Annotated[list[BaseMessage], add_messages] = []
