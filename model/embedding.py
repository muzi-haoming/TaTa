import logging

import aiohttp

from config import config
from exception import EmbeddingError

logger = logging.getLogger(__name__)


class Embedding:
    _session = None

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.base_url = config["embedding_model"]["base_url"]
        self.embed_url = config["embedding_model"]["embed_url"]
        self.health_url = config["embedding_model"]["health_url"]
        self.dimension = config["embedding_model"]["dimension"]

    async def _get_session(self):
        if not Embedding._session:
            Embedding._session = aiohttp.ClientSession(self.base_url, timeout=aiohttp.ClientTimeout(total=30))
            if not await self._health():
                raise EmbeddingError("Embedding服务异常")
        return Embedding._session

    async def _health(self) -> bool:
        session = await self._get_session()
        async with session.get(self.health_url) as resp:
            return resp.status == 200

    async def embed(self, texts: list[str]) -> list[list[float]]:
        session = await self._get_session()
        async with session.post(self.embed_url, json={"inputs": texts}) as resp:
            if resp.ok:
                return await resp.json()
            else:
                text = await resp.text()
                logger.error(f"请求 embedding 服务失败，状态码：{resp.status}，错误信息：{text}")
                raise EmbeddingError("请求 embedding 服务失败")

    async def close(self):
        if Embedding._session:
            await Embedding._session.close()
            Embedding._session = None
