"""
配置模块

提供全局配置访问接口。

使用示例:
    from config import settings, meshy_config

    # 访问主配置
    print(settings.google_cloud.project)
    print(settings.models.chat_model)

    # 访问 Meshy 配置
    print(meshy_config.api.get_endpoint_url("text_to_3d"))
    print(meshy_config.image_to_3d.ai_model)
"""
from .config import (
    config,
    settings,
    meshy_config,
    get_config,
    ConfigLoader,
    Settings,
    MeshySettings,
)

__all__ = [
    "config",
    "settings",
    "meshy_config",
    "get_config",
    "ConfigLoader",
    "Settings",
    "MeshySettings",
]
