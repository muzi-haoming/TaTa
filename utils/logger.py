import logging

import colorlog

NOISY_LOGGERS = {
    "watchfiles": logging.WARNING,  # chainlit -w 的文件监听，最吵
    "httpx": logging.WARNING,  # 每次 HTTP 请求都打一行
    "httpcore": logging.WARNING,
    "jieba": logging.WARNING,  # 加载词典那几行
    "urllib3": logging.WARNING,
    "asyncio": logging.WARNING,
    "openai": logging.WARNING,
    "pymilvus": logging.WARNING,
    "aiohttp": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
}


def setup_logger(level: int = logging.INFO) -> None:
    """
    设置日志格式和级别。
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    logging.basicConfig(level=level, handlers=[handler], force=True)

    for name, lv in NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(lv)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
