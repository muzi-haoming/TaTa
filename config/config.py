import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
config_path = CONFIG_DIR / "config.yaml"

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


# """
# 配置加载模块

# 负责「配置从哪来」：定位配置目录、加载 YAML、注入环境变量、初始化日志。
# 配置的数据结构定义在 :mod:`config.models` 中。

# 加载器为单例，保证全局配置一致性。
# """
# import os
# from pathlib import Path
# from typing import Optional

# from utils import SingletonMeta, setup_logger

# from .models import MeshySettings, Settings


# class ConfigLoader(metaclass=SingletonMeta):
#     """配置加载器（单例）。"""

#     def __init__(self, config_dir: Optional[Path] = None):
#         """
#         :param config_dir: 配置文件目录，默认为本模块所在目录。
#         """
#         self._config_dir = config_dir or Path(__file__).parent
#         self._settings: Optional[Settings] = None
#         self._meshy_settings: Optional[MeshySettings] = None
#         self._load_configs()

#     # ==================== 加载流程 ====================

#     def _load_configs(self) -> None:
#         """加载所有配置，并完成依赖配置的副作用初始化。"""
#         self._settings = Settings.load(self._config_dir)
#         self._meshy_settings = MeshySettings.load(self._config_dir)

#         self._setup_environment()
#         # 日志的 sink 依赖配置，配置就绪后立即重建
#         setup_logger(self._settings.logging)

#     def _setup_environment(self) -> None:
#         """设置 Google Cloud SDK 依赖的环境变量（不覆盖已有值）。"""
#         google_cloud = self._settings.google_cloud
#         os.environ.setdefault("GOOGLE_CLOUD_PROJECT", google_cloud.project)
#         os.environ.setdefault("GOOGLE_CLOUD_LOCATION", google_cloud.location)

#     def reload(self) -> None:
#         """重新加载配置（配置文件变更后调用）。"""
#         self._load_configs()

#     # ==================== 访问入口 ====================

#     @property
#     def config_dir(self) -> Path:
#         """配置文件目录"""
#         return self._config_dir

#     @property
#     def settings(self) -> Settings:
#         """主配置"""
#         return self._settings

#     @property
#     def meshy(self) -> MeshySettings:
#         """Meshy 配置"""
#         return self._meshy_settings


# # ==================== 全局配置实例 ====================

# def get_config() -> ConfigLoader:
#     """获取配置加载器实例（单例）。"""
#     return ConfigLoader()


# config = get_config()
# settings = config.settings
# meshy_config = config.meshy
