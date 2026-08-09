from langchain.agents import create_agent

from model import MediumLLM
from utils import get_logger

from .tools import info_search

logger = get_logger(__name__)


class AssistantAgent:
    def __init__(self):
        self.agent = create_agent(
            model=MediumLLM().get_model(),
            tools=[info_search],
        )
        logger.debug("========== Agent 创建成功!")

    def get_agent(self):
        return self.agent
