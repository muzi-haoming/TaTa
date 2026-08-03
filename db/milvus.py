from pymilvus import MilvusClient

from config import config


class Milvus:
    def __init__(self, url: str = None):
        self.url = url or config["milvus"]["base_url"]
        self.client = MilvusClient(uri=self.url)

    def insert(self, collection_name: str, data: list[dict]):
        """插入数据到指定 collection"""
        if not self.client.has_collection(collection_name):
            self.client.create_collection(
                collection_name=collection_name, dimension=config["embedding_model"]["dimension"], auto_id=True
            )

        if any(not d.get("vector") or not isinstance(d.get("vector"), list) for d in data):
            raise ValueError("每条数据必须包含 'vector' 字段，且其值必须是列表")

        return self.client.insert(collection_name=collection_name, data=data)

    def search(self, collection_name: str, data: list[list[float]], limit: int = 5, output_fields: list[str] = None):
        """在指定 collection 中进行相似度检索"""
        if not self.client.has_collection(collection_name):
            raise ValueError(f"Collection '{collection_name}' 不存在")

        if not data or not isinstance(data, list):
            raise ValueError("data 必须是非空列表")

        return self.client.search(collection_name=collection_name, data=data, limit=limit, output_fields=output_fields)

    def drop_collection(self, collection_name: str):
        """删除指定 collection"""
        if self.client.has_collection(collection_name):
            self.client.drop_collection(collection_name)
