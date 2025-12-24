import sys
from pathlib import Path

import yaml
from loguru import logger


def _load_logging_config():
    """加载日志配置（直接读取yaml，避免循环导入）"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            return config.get("logging", {})
    return {}


def _setup_logger():
    """配置日志系统"""
    log_config = _load_logging_config()

    # 控制台配置
    console_config = log_config.get("console", {})
    console_level = console_config.get("level", "INFO")
    console_colorize = console_config.get("colorize", True)
    console_format = console_config.get(
        "format",
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 文件配置
    file_config = log_config.get("file", {})
    log_directory = file_config.get("directory", "data/log")

    # 运行时日志配置
    runtime_config = file_config.get("runtime", {})
    runtime_filename = runtime_config.get("filename_pattern", "runtime_{time:YYYY-MM-DD}.log")
    runtime_rotation = runtime_config.get("rotation", "00:00")
    runtime_retention = runtime_config.get("retention", "10 days")
    runtime_level = runtime_config.get("level", "DEBUG")
    runtime_encoding = runtime_config.get("encoding", "utf-8")
    runtime_enqueue = runtime_config.get("enqueue", True)

    # 错误日志配置
    error_config = file_config.get("error", {})
    error_filename = error_config.get("filename_pattern", "error_{time:YYYY-MM-DD}.log")
    error_rotation = error_config.get("rotation", "10 MB")
    error_retention = error_config.get("retention", "30 days")
    error_level = error_config.get("level", "ERROR")
    error_encoding = error_config.get("encoding", "utf-8")

    logger.remove()

    # 控制台输出 (开发用)
    logger.add(
        sys.stderr,
        colorize=console_colorize,
        format=console_format,
        level=console_level
    )

    # 文件输出 (存档用)
    logger.add(
        f"{log_directory}/{runtime_filename}",
        rotation=runtime_rotation,
        retention=runtime_retention,
        enqueue=runtime_enqueue,
        encoding=runtime_encoding,
        level=runtime_level
    )

    # 错误日志单独存一份 (方便排查报错)
    logger.add(
        f"{log_directory}/{error_filename}",
        rotation=error_rotation,
        retention=error_retention,
        level=error_level,
        encoding=error_encoding
    )


# 初始化日志配置
_setup_logger()
