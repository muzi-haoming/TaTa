import os
from openai import OpenAI
from langchain_huggingface import HuggingFaceEndpoint

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

HuggingFaceEndpoint

completion = client.chat.completions.create(
    model="Qwen/Qwen3-8B:nscale",
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ],
)

print(completion.choices[0].message)