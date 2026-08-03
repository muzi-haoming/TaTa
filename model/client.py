from openai import OpenAI


class Client:
    def __init__(self, client: OpenAI):
        self.client = client

    def create(self, model: str, input: str = None) -> dict:
        return self.client.responses.create(model=model, input=input)
