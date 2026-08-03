"""
配置数据模型

全部配置以 pydantic 模型描述，提供类型安全与默认值兜底。
:class:`YamlSettings` 抽象出「一个配置文件 <-> 一个根模型」的加载能力，
子类只需声明 ``source_filename``。
"""
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Self

import yaml
from pydantic import BaseModel, Field

from utils import DEFAULT_CONSOLE_FORMAT


# ==================== 加载能力基类 ====================

class YamlSettings(BaseModel):
    """
    可从 YAML 文件加载的配置根模型基类。

    子类通过 ``source_filename`` 声明自己对应的配置文件名；文件缺失或为空时
    退化为模型自身的默认值，保证程序在缺省配置下依然可运行。
    """

    #: 该配置对应的 YAML 文件名（相对于配置目录）
    source_filename: ClassVar[str] = ""

    @classmethod
    def load(cls, config_dir: Path) -> Self:
        """从 ``config_dir / source_filename`` 加载配置。"""
        if not cls.source_filename:
            raise NotImplementedError(f"{cls.__name__} 必须声明 source_filename")

        config_path = config_dir / cls.source_filename
        data: Dict[str, Any] = {}
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        return cls(**data)


# ==================== 主配置模型 ====================

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
    format: str = DEFAULT_CONSOLE_FORMAT


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
    worldview_file: str = "worldview.txt"
    model_style_file: str = "model_style.txt"


class UIConfig(BaseModel):
    """UI 配置"""
    default_thread_id: str = "959"
    stream_delay: float = 0.01


class Settings(YamlSettings):
    """主配置（settings.yaml）"""
    source_filename: ClassVar[str] = "settings.yaml"

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


class MeshySettings(YamlSettings):
    """Meshy 配置（meshy_config.yaml）"""
    source_filename: ClassVar[str] = "meshy_config.yaml"

    api: MeshyApiConfig = Field(default_factory=MeshyApiConfig)
    text_to_3d: TextTo3DConfig = Field(default_factory=TextTo3DConfig)
    image_to_3d: ImageTo3DConfig = Field(default_factory=ImageTo3DConfig)
    multi_image_to_3d: MultiImageTo3DConfig = Field(default_factory=MultiImageTo3DConfig)
    remesh: RemeshConfig = Field(default_factory=RemeshConfig)
    rigging: RiggingConfig = Field(default_factory=RiggingConfig)
    retexture: RetextureConfig = Field(default_factory=RetextureConfig)
    task_list: TaskListConfig = Field(default_factory=TaskListConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
