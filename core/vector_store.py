from langchain_chroma import Chroma

from config import settings
from utils import FileUtil
from .embedding_model import create_embedding_model

_vector_store = None


def create_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            collection_name=settings.vector_store.collection_name,
            embedding_function=create_embedding_model(),
            persist_directory=FileUtil(settings.vector_store.persist_directory).root,
        )
    return _vector_store