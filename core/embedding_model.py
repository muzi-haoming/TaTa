from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import settings

_embeddings = None


def create_embedding_model():
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(model=settings.models.embedding_model)
    return _embeddings
