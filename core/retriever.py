from config import settings
from .vector_store import create_vector_store

_retriever = None


def create_retriever():
    global _retriever
    if _retriever is None:
        _retriever = create_vector_store().as_retriever(
            search_type=settings.retriever.search_type,
            search_kwargs={
                "k": settings.retriever.search_kwargs.k,
                "score_threshold": settings.retriever.search_kwargs.score_threshold
            },
        )
    return _retriever