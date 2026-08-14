from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import get_chat_agent
from .router import router
from .state import State


def build_graph():
    graph = StateGraph(State)
    graph.add_node(
        "router_node", router
    )
    graph.add_node(
        "chat_node", get_chat_agent()
    )
    # graph.add_node("cg_discuss_node", )
    # graph.add_node("cg_image_node", )
    # graph.add_node("cg_3d_node", )
    graph.add_conditional_edges(
        START,
        router,
        {
            "chat_node": "chat_node",
            # "character_generation_node": "character_generation_node",
        },
    )
    graph.add_edge("chat_node", END)

    return graph.compile(checkpointer=InMemorySaver())
