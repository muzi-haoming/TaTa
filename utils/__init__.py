"""
通用工具模块

不依赖任何业务模块，可被 config / core / services / workflows / ui 自由引用。
"""
# from .file_util import DEFAULT_CHUNK_SIZE, FileUtil
from .logger import setup_logger, get_logger
from .singleton import SingletonMeta
from .text_splitter import split_docs

__all__ = [
    # "FileUtil",
    # "DEFAULT_CHUNK_SIZE",
    "setup_logger",
    "get_logger",
    "SingletonMeta",
    "split_docs",
]
