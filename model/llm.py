import os

from openai import OpenAI

from config import config
from .client import Client


class LLM:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        base_url: str = config["llm"]["base_url"],
        model: str = config["llm"]["model"],
        api_key: str = os.environ.get("API_KEY"),
    ):
        if self._instance:
            return
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )

    def create(self, model: str = config["llm"]["model"], input: str = None) -> dict:
        return self.client.responses.create(model=model, input=input)

    def create_client(self) -> Client:
        return Client(self.client)

    @staticmethod
    def get_llm() -> OpenAI:
        return LLM()