import logging

from config import config
from exception import EmbeddingException

import requests

logger = logging.getLogger(__name__)


class Embedding:
    def __init__(
        self,
        base_url: str = None,
        embed_url: str = None,
        health_url: str = None,
        dimension: int = None,
    ):
        self.base_url = base_url or config["embedding_model"]["base_url"]
        self.embed_url = embed_url or config["embedding_model"]["embed_url"]
        self.health_url = health_url or config["embedding_model"]["health_url"]
        self.dimension = dimension or config["embedding_model"]["dimension"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本转化为向量"""
        resp = requests.post(
            self.base_url + self.embed_url,
            json={"inputs": texts},
        )

        if resp.ok:
            return resp.json()
        else:
            logger.error(f"请求 embedding 服务失败，状态码：{resp.status_code}，错误信息：{resp.text}")
            raise EmbeddingException("请求 embedding 服务失败")
