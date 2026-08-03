import logging
import colorlog


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
    logging.basicConfig(level=level, handlers=[handler])


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
