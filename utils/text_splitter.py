import logging
import re

from functools import lru_cache
from config import config
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _get_splitter(
    chunk_size: int = None,
    chunk_overlap: int = None,
    separators: list[str] = None,
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or config["text_splitter"]["chunk_size"],
        chunk_overlap=chunk_overlap or config["text_splitter"]["chunk_overlap"],
        separators=separators or config["text_splitter"]["separators"],
        length_function=len,  # 按字符数计算，非 token 数
    )


def _text_cleaning(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[ \t]+", " ", text)  # 连续空格/制表符 -> 一个空格
    text = re.sub(r"\n{3,}", "\n\n", text)  # 多个空行 -> 2个空行
    return text


def _docs_cleaning(docs: list[Document]) -> list[Document]:
    for doc in docs:
        doc.page_content = _text_cleaning(doc.page_content)
    return docs


def split_docs(
    docs: list[Document],
    chunk_size: int = None,
    chunk_overlap: int = None,
    separators: list[str] = None,
) -> list[Document]:
    splitter = _get_splitter(
        chunk_size,
        chunk_overlap,
        separators,
    )

    docs = _docs_cleaning(docs)

    return splitter.split_documents(docs)
