from config import config

from langchain_core.messages import AIMessage
from langchain.chat_models import init_chat_model


class LiteLLM:
    def __init__(
        self, base_url: str = None, model_name: str = None, model_provider: str = None, temperature: float = None
    ):
        self.base_url = base_url or config["lite_llm"]["base_url"]
        self.model_name = model_name or config["lite_llm"]["model_name"]
        self.model_provider = model_provider or config["lite_llm"]["model_provider"]
        self.temperature = temperature or config["lite_llm"]["temperature"]

        if "huggingface" == self.model_provider:
            self.model = init_chat_model(
                model=self.model_name,
                model_provider=self.model_provider,
                temperature=self.temperature,
                backend="endpoint",
            )
        elif "openai" == self.model_provider:
            self.model = init_chat_model(
                base_url=self.base_url,
                model=self.model_name,
                model_provider=self.model_provider,
                temperature=self.temperature,
            )

    async def ainvoke(self, input: list, pydantic_model: type = None) -> AIMessage:
        if pydantic_model:
            return await self.model.with_structured_output(
                schema=pydantic_model.model_json_schema(), method="json_schema"
            ).ainvoke(input)
        return await self.model.ainvoke(input)
