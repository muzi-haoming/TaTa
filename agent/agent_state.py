from typing import Literal

from langchain.agents import AgentState


class AssistantAgentState(AgentState):
    mode: Literal["discuss", "generate"] = "discuss"
