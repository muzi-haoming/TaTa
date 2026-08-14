from .state import State


def router(state: State):
    if state["route_mode"] == "character_generation":
        return "character_generation_node"
    else:
        return "chat_node"
