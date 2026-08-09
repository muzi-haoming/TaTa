from langchain.chat_models import init_chat_model

from config import config
from utils import get_logger

logger = get_logger(__name__)


class MediumLLM:
    def __init__(self, **overrides):
        params = {**config["medium_llm"], **overrides}
        self.model = init_chat_model(**params)

    def get_model(self):
        return self.model
