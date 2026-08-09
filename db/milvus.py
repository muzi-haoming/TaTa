import asyncio
import logging

from pymilvus import MilvusClient

from config import config

logger = logging.getLogger(__name__)


class Milvus:
    _client = None

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.base_url = config["milvus"]["base_url"]
        self.limit = config["milvus"]["limit"]
        self.dimension = config["embedding_model"]["dimension"]

    async def _get_client(self) -> MilvusClient:
        if Milvus._client is None:
            # MilvusClient 构造时会阻塞等待连接就绪，放线程池里避免卡住事件循环
            Milvus._client = await asyncio.to_thread(MilvusClient, uri=self.base_url)
        return Milvus._client

    async def has_collection(self, collection_name: str) -> bool:
        client = await self._get_client()
        return await asyncio.to_thread(client.has_collection, collection_name)

    async def insert(self, collection_name: str, data: list[dict]):
        client = await self._get_client()

        if not await self.has_collection(collection_name):
            await asyncio.to_thread(
                client.create_collection, collection_name=collection_name, dimension=self.dimension, auto_id=True
            )

        if any(not isinstance(d.get("vector"), list) for d in data):
            raise ValueError("每条数据必须包含 'vector' 字段，且其值必须是列表")

        return await asyncio.to_thread(client.insert, collection_name=collection_name, data=data)

    async def search(
        self,
        collection_name: str,
        data: list[list[float]],
        output_fields: list[str] | None = None,
    ) -> list[list[dict]]:
        if not data:
            raise ValueError("data 不能为空")

        client = await self._get_client()
        return await asyncio.to_thread(
            client.search,
            collection_name=collection_name,
            data=data,
            limit=self.limit,
            output_fields=output_fields,
        )

    async def drop_collection(self, collection_name: str) -> None:
        if await self.has_collection(collection_name):
            client = await self._get_client()
            await asyncio.to_thread(client.drop_collection, collection_name)

    async def close(self) -> None:
        if Milvus._client:
            await asyncio.to_thread(Milvus._client.close)
            Milvus._client = None
