"""
配置管理模块

提供类型安全的配置管理，支持从YAML文件加载配置。
配置采用单例模式，确保全局配置一致性。
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
from pydantic import BaseModel, Field


# ==================== 基础配置模型 ====================

class GoogleCloudConfig(BaseModel):
    """Google Cloud 配置"""
    project: str = "tata-482008"
    location: str = "us-central1"


class ModelsConfig(BaseModel):
    """AI 模型配置"""
    chat_model: str = "google_vertexai:gemini-2.5-flash"
    image_model: str = "google_vertexai:gemini-2.5-flash-image"
    imagen_model: str = "imagen-4.0-generate-001"
    imagen_number_of_images: int = 1
    embedding_model: str = "text-embedding-004"


class VectorStoreConfig(BaseModel):
    """向量数据库配置"""
    collection_name: str = "npc_lore_collection"
    persist_directory: str = "data/chroma_db"


class RetrieverSearchKwargs(BaseModel):
    """检索器搜索参数"""
    k: int = 10
    score_threshold: float = 0.2


class RetrieverConfig(BaseModel):
    """检索器配置"""
    search_type: str = "similarity_score_threshold"
    search_kwargs: RetrieverSearchKwargs = Field(default_factory=RetrieverSearchKwargs)


class LogConsoleConfig(BaseModel):
    """控制台日志配置"""
    level: str = "INFO"
    colorize: bool = True
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"


class LogFileRuntimeConfig(BaseModel):
    """运行时日志文件配置"""
    filename_pattern: str = "runtime_{time:YYYY-MM-DD}.log"
    rotation: str = "00:00"
    retention: str = "10 days"
    level: str = "DEBUG"
    encoding: str = "utf-8"
    enqueue: bool = True


class LogFileErrorConfig(BaseModel):
    """错误日志文件配置"""
    filename_pattern: str = "error_{time:YYYY-MM-DD}.log"
    rotation: str = "10 MB"
    retention: str = "30 days"
    level: str = "ERROR"
    encoding: str = "utf-8"


class LogFileConfig(BaseModel):
    """日志文件配置"""
    directory: str = "data/log"
    runtime: LogFileRuntimeConfig = Field(default_factory=LogFileRuntimeConfig)
    error: LogFileErrorConfig = Field(default_factory=LogFileErrorConfig)


class LoggingConfig(BaseModel):
    """日志配置"""
    console: LogConsoleConfig = Field(default_factory=LogConsoleConfig)
    file: LogFileConfig = Field(default_factory=LogFileConfig)


class PathsConfig(BaseModel):
    """文件路径配置"""
    npc_generation_data: str = "data/npc_generation"
    ai_auto_control_data: str = "data/ai_auto_control"
    worldview_file: str = "worldview.txt"
    model_style_file: str = "model_style.txt"


class UIConfig(BaseModel):
    """UI 配置"""
    default_thread_id: str = "959"
    stream_delay: float = 0.01


class Settings(BaseModel):
    """主配置类"""
    google_cloud: GoogleCloudConfig = Field(default_factory=GoogleCloudConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    retriever: RetrieverConfig = Field(default_factory=RetrieverConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    ui: UIConfig = Field(default_factory=UIConfig)


# ==================== Meshy 配置模型 ====================

class MeshyApiConfig(BaseModel):
    """Meshy API 端点配置"""
    base_url: str = "https://api.meshy.ai/openapi"
    endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "text_to_3d": "/v2/text-to-3d",
        "image_to_3d": "/v1/image-to-3d",
        "multi_image_to_3d": "/v1/multi-image-to-3d",
        "remesh": "/v1/remesh",
        "rigging": "/v1/rigging",
        "animations": "/v1/animations",
        "retexture": "/v1/retexture",
    })

    def get_endpoint_url(self, endpoint_name: str) -> str:
        """获取完整的端点URL"""
        endpoint = self.endpoints.get(endpoint_name, "")
        return f"{self.base_url}{endpoint}"


class TextTo3DPreviewConfig(BaseModel):
    """Text-to-3D 预览配置"""
    art_style: str = "realistic"
    ai_model: str = "latest"
    topology: str = "quad"
    target_polycount: int = 50000
    should_remesh: bool = True
    symmetry_mode: str = "auto"
    pose_mode: str = "t-pose"
    moderation: bool = False
    max_prompt_length: int = 600


class TextTo3DRefineConfig(BaseModel):
    """Text-to-3D 精细化配置"""
    enable_pbr: bool = False
    max_texture_prompt_length: int = 600
    moderation: bool = False


class TextTo3DConfig(BaseModel):
    """Text-to-3D 配置"""
    preview: TextTo3DPreviewConfig = Field(default_factory=TextTo3DPreviewConfig)
    refine: TextTo3DRefineConfig = Field(default_factory=TextTo3DRefineConfig)


class ImageTo3DConfig(BaseModel):
    """Image-to-3D 配置"""
    ai_model: str = "latest"
    enable_pbr: bool = False
    topology: str = "quad"
    target_polycount: int = 50000
    symmetry_mode: str = "auto"
    should_remesh: bool = True
    save_pre_remeshed_model: bool = False
    should_texture: bool = True
    pose_mode: str = "t-pose"
    moderation: bool = False
    max_texture_prompt_length: int = 600


class MultiImageTo3DConfig(BaseModel):
    """Multi-Image-to-3D 配置"""
    ai_model: str = "meshy-5"
    enable_pbr: bool = False
    topology: str = "quad"
    target_polycount: int = 50000
    symmetry_mode: str = "auto"
    should_remesh: bool = True
    save_pre_remeshed_model: bool = False
    should_texture: bool = True
    pose_mode: str = "t-pose"
    moderation: bool = False
    max_texture_prompt_length: int = 600
    min_images: int = 1
    max_images: int = 4


class RemeshConfig(BaseModel):
    """Remesh 配置"""
    target_formats: List[str] = Field(default_factory=lambda: ["glb"])
    topology: str = "quad"
    target_polycount: int = 50000
    resize_height: int = 0
    origin_at: str = "bottom"
    convert_format_only: bool = False


class RiggingConfig(BaseModel):
    """Rigging 配置"""
    height_meters: float = 1.6


class RetextureConfig(BaseModel):
    """Retexture 配置"""
    ai_model: str = "latest"
    enable_original_uv: bool = True
    enable_pbr: bool = False


class TaskListConfig(BaseModel):
    """任务列表配置"""
    default_page_size: int = 10
    max_page_size: int = 50
    default_sort_by: str = "-created_at"


class DownloadConfig(BaseModel):
    """下载配置"""
    chunk_size: int = 8192


class MeshySettings(BaseModel):
    """Meshy 配置主类"""
    api: MeshyApiConfig = Field(default_factory=MeshyApiConfig)
    text_to_3d: TextTo3DConfig = Field(default_factory=TextTo3DConfig)
    image_to_3d: ImageTo3DConfig = Field(default_factory=ImageTo3DConfig)
    multi_image_to_3d: MultiImageTo3DConfig = Field(default_factory=MultiImageTo3DConfig)
    remesh: RemeshConfig = Field(default_factory=RemeshConfig)
    rigging: RiggingConfig = Field(default_factory=RiggingConfig)
    retexture: RetextureConfig = Field(default_factory=RetextureConfig)
    task_list: TaskListConfig = Field(default_factory=TaskListConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)


# ==================== 配置加载器 ====================

class ConfigLoader:
    """配置加载器（单例模式）"""

    _instance: Optional['ConfigLoader'] = None
    _settings: Optional[Settings] = None
    _meshy_settings: Optional[MeshySettings] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._settings is None:
            self._load_configs()

    def _get_config_dir(self) -> Path:
        """获取配置文件目录"""
        return Path(__file__).parent

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """加载 YAML 配置文件"""
        config_path = self._get_config_dir() / filename
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_configs(self):
        """加载所有配置"""
        # 加载主配置
        settings_data = self._load_yaml('settings.yaml')
        self._settings = Settings(**settings_data) if settings_data else Settings()

        # 加载 Meshy 配置
        meshy_data = self._load_yaml('meshy_config.yaml')
        self._meshy_settings = MeshySettings(**meshy_data) if meshy_data else MeshySettings()

        # 设置环境变量
        self._setup_environment()

    def _setup_environment(self):
        """设置必要的环境变量"""
        if self._settings:
            os.environ.setdefault("GOOGLE_CLOUD_PROJECT", self._settings.google_cloud.project)
            os.environ.setdefault("GOOGLE_CLOUD_LOCATION", self._settings.google_cloud.location)

    @property
    def settings(self) -> Settings:
        """获取主配置"""
        if self._settings is None:
            self._load_configs()
        return self._settings

    @property
    def meshy(self) -> MeshySettings:
        """获取 Meshy 配置"""
        if self._meshy_settings is None:
            self._load_configs()
        return self._meshy_settings

    def reload(self):
        """重新加载配置"""
        self._settings = None
        self._meshy_settings = None
        self._load_configs()


# ==================== 全局配置实例 ====================

def get_config() -> ConfigLoader:
    """获取配置加载器实例"""
    return ConfigLoader()


# 便捷访问
config = get_config()
settings = config.settings
meshy_config = config.meshy
