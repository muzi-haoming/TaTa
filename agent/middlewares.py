from langchain.agents.middleware import ModelRequest, dynamic_prompt

from utils import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = {
    "discuss": "你是一个助手，回答我的问题。当你需要更多信息来回答问题的时候，可以借助有用的工具来帮助你获取有用的信息。"
}


@dynamic_prompt
def build_system_prompt(request: ModelRequest) -> str:
    mode = request.state.get("mode", "discuss")
    logger.debug(f"========== dynamic_prompt 中间件 mode: {mode}")
    return SYSTEM_PROMPT[mode]
