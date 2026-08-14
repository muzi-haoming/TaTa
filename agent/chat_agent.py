from langchain.agents import create_agent

from model import MediumLLM
from utils import get_logger

logger = get_logger(__name__)


class ChatAgent:
    def __init__(self, **overrides):
        params = {
            "model": MediumLLM().get_model(),
            **overrides,
        }
        self.agent = create_agent(**params)
        logger.debug("========== Agent 创建成功!")

    def get_agent(self):
        return self.agent
