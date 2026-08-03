from .config import config

__all__ = [
    "config",
]

# """
# 配置模块

# 使用示例::

#     from config import settings, meshy_config

#     # 访问主配置
#     print(settings.google_cloud.project)
#     print(settings.models.chat_model)

#     # 访问 Meshy 配置
#     print(meshy_config.api.get_endpoint_url("text_to_3d"))
#     print(meshy_config.image_to_3d.ai_model)

# 导入本模块会顺带完成两件事：注入 Google Cloud 环境变量、按配置初始化日志。
# """
# from .config import ConfigLoader, config, get_config, meshy_config, settings
# from .models import MeshySettings, Settings, YamlSettings

# __all__ = [
#     "config",
#     "settings",
#     "meshy_config",
#     "get_config",
#     "ConfigLoader",
#     "YamlSettings",
#     "Settings",
#     "MeshySettings",
# ]
