import logging
import aiohttp

from config import config

logger = logging.getLogger(__name__)


class RerankModel:
    def __init__(
        self,
        base_url: str = None,
        rerank_url: str = None,
        health_url: str = None,
    ):
        self.base_url = base_url or config["rerank_model"]["base_url"]
        self.health_url = health_url or config["rerank_model"]["health_url"]
        self.rerank_url = rerank_url or config["rerank_model"]["rerank_url"]

    async def rerank(self, query: str, texts: list) -> list[str]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url + self.rerank_url,
                json={"query": query, "texts": texts, "return_text": True},
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def health(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url + self.health_url) as response:
                response.raise_for_status()
                logger.debug("Rerank model is healthy")
