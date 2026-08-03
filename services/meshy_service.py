"""
Meshy AI 3D 生成服务封装
文档: https://docs.meshy.ai/zh

支持的功能:
- Text-to-3D: 文本生成3D模型 (预览 + 精细化)
- Image-to-3D: 单图/多图生成3D模型
- Remesh: 重建网格
- Rigging & Animation: 自动绑定骨骼并添加动画
- Retexture: 重新生成纹理

本模块只描述「Meshy 的 API 形状」——每个接口需要哪些字段、默认值取自哪段配置；
HTTP 传输、错误处理、SSE 解析等通用机制由 :mod:`services.base` 提供。
"""
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence

from config import meshy_config
from utils import SingletonMeta, logger

from .base import HttpApiClient, Pagination, TaskEndpoint

#: 未配置 ``MESHY_API_KEY`` 时使用的测试密钥（Meshy 的 test mode）
TEST_API_MODE_KEY = "msy_dummy_api_key_for_test_mode_12345678"

#: 环境变量名
API_KEY_ENV = "MESHY_API_KEY"

#: 多视图不支持的模型 -> 自动降级目标
_MULTI_VIEW_FALLBACK_MODEL = "meshy-5"
_MULTI_VIEW_UNSUPPORTED_MODEL = "latest"


class MeshyService(metaclass=SingletonMeta):
    """
    Meshy AI 服务封装类（单例）。

    通过为每个 API 端点提供 :class:`~services.base.TaskEndpoint` 来简化交互::

        meshy_service.image_to_3d.get("some-task-id")
        meshy_service.text_to_3d.create_preview_task("a cat")
        meshy_service.endpoint("image-to-3d").listen(task_id)
    """

    #: 全部端点名（同时是 ``meshy_config.api.endpoints`` 的键）
    ENDPOINT_NAMES = (
        "text_to_3d",
        "image_to_3d",
        "multi_image_to_3d",
        "remesh",
        "rigging",
        "animations",
        "retexture",
    )

    def __init__(self, api_key: Optional[str] = None):
        """
        :param api_key: Meshy API 密钥；默认读取环境变量 ``MESHY_API_KEY``，
                        未设置时回退到 Meshy 的测试密钥。
        """
        self._config = meshy_config
        self.api_key = api_key or os.environ.get(API_KEY_ENV, TEST_API_MODE_KEY)
        if self.api_key == TEST_API_MODE_KEY:
            logger.warning(f"未设置 {API_KEY_ENV}，Meshy 将以测试密钥运行")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._client = HttpApiClient(self.headers)
        self._pagination = Pagination(
            default_page_size=self._config.task_list.default_page_size,
            max_page_size=self._config.task_list.max_page_size,
            default_sort_by=self._config.task_list.default_sort_by,
        )

        # 各端点处理器
        self.text_to_3d = self._build_endpoint("text_to_3d")
        self.image_to_3d = self._build_endpoint("image_to_3d")
        self.multi_image_to_3d = self._build_endpoint("multi_image_to_3d")
        self.remesh = self._build_endpoint("remesh")
        self.rigging = self._build_endpoint("rigging")
        self.animations = self._build_endpoint("animations")
        self.retexture = self._build_endpoint("retexture")

    # ==================== 端点访问 ====================

    def _build_endpoint(self, name: str) -> TaskEndpoint:
        """按配置构建一个任务端点。"""
        return TaskEndpoint(
            client=self._client,
            base_url=self._config.api.get_endpoint_url(name),
            pagination=self._pagination,
        )

    def endpoint(self, name: str) -> TaskEndpoint:
        """
        按名称获取任务端点，兼容 ``image-to-3d`` 与 ``image_to_3d`` 两种写法。

        :raises KeyError: 名称未知。
        """
        key = name.replace("-", "_")
        if key not in self.ENDPOINT_NAMES:
            raise KeyError(f"未知的 Meshy 端点: {name}（可用: {', '.join(self.ENDPOINT_NAMES)}）")
        return getattr(self, key)

    # ==================== payload 构建 ====================

    @staticmethod
    def _truncate(text: Optional[str], limit: int) -> Optional[str]:
        """按上限截断文本；空值原样返回。"""
        return text[:limit] if text else text

    @staticmethod
    def _build_payload(
        config_section: Any,
        overrides: Mapping[str, Any],
        *,
        defaults: Sequence[str] = (),
        passthrough: Sequence[str] = (),
        **explicit: Any,
    ) -> Dict[str, Any]:
        """
        统一的 payload 组装逻辑，替代大段 ``kwargs.get("x", cfg.x)`` 样板。

        :param config_section: 提供默认值的配置片段，可为 None。
        :param overrides: 调用方传入的 ``**kwargs``。
        :param defaults: 默认值取自 ``config_section``、允许被 overrides 覆盖的字段。
        :param passthrough: 仅来自 overrides 的可选字段（缺省为 None，最终被剔除）。
        :param explicit: 由调用方直接确定的字段，优先级最高。
        :return: 已剔除 None 值的 payload。
        """
        payload: Dict[str, Any] = {}
        for field in defaults:
            payload[field] = overrides.get(field, getattr(config_section, field))
        for field in passthrough:
            payload[field] = overrides.get(field)
        payload.update(explicit)
        return {k: v for k, v in payload.items() if v is not None}

    # ==================== Text-to-3D API ====================

    def create_text_to_3d_preview_task(self, prompt: str, **kwargs: Any) -> str:
        """创建 Text-to-3D 预览任务。"""
        cfg = self._config.text_to_3d.preview
        payload = self._build_payload(
            cfg, kwargs,
            defaults=(
                "art_style", "ai_model", "topology", "target_polycount",
                "should_remesh", "symmetry_mode", "pose_mode",
            ),
            passthrough=("seed",),
            mode="preview",
            prompt=self._truncate(prompt, cfg.max_prompt_length),
            moderation=cfg.moderation,
        )
        logger.info(f"提交 Text-to-3D 预览任务 (model={payload['ai_model']})")
        return self.text_to_3d.create(payload)

    def create_text_to_3d_refine_task(self, preview_task_id: str, **kwargs: Any) -> str:
        """创建 Text-to-3D 精细化任务。"""
        cfg = self._config.text_to_3d.refine
        payload = self._build_payload(
            cfg, kwargs,
            defaults=("enable_pbr",),
            passthrough=("texture_image_url", "ai_model"),
            mode="refine",
            preview_task_id=preview_task_id,
            texture_prompt=self._truncate(kwargs.get("texture_prompt", ""), cfg.max_texture_prompt_length),
            moderation=cfg.moderation,
        )
        logger.info(f"提交 Text-to-3D 精细化任务 (preview={preview_task_id})")
        return self.text_to_3d.create(payload)

    # ==================== Image-to-3D API ====================

    def create_image_to_3d_task(self, image_url: str, **kwargs: Any) -> str:
        """创建单图转3D任务。"""
        cfg = self._config.image_to_3d
        payload = self._build_payload(
            cfg, kwargs,
            defaults=(
                "ai_model", "enable_pbr", "topology", "target_polycount",
                "symmetry_mode", "should_remesh", "save_pre_remeshed_model",
                "should_texture", "pose_mode",
            ),
            passthrough=("texture_image_url",),
            image_url=image_url,
            texture_prompt=self._truncate(kwargs.get("texture_prompt", ""), cfg.max_texture_prompt_length),
            moderation=cfg.moderation,
        )
        logger.info(f"提交 Image-to-3D 任务 (model={payload['ai_model']})")
        return self.image_to_3d.create(payload)

    # ==================== Multi-Image-to-3D API ====================

    def create_multi_image_to_3d_task(self, image_urls: List[str], **kwargs: Any) -> str:
        """创建多图转3D任务（1-4 张图片）。"""
        cfg = self._config.multi_image_to_3d
        if not cfg.min_images <= len(image_urls) <= cfg.max_images:
            raise ValueError(f"image_urls 必须包含 {cfg.min_images}-{cfg.max_images} 张图片")

        ai_model = kwargs.get("ai_model", cfg.ai_model)
        if ai_model == _MULTI_VIEW_UNSUPPORTED_MODEL:
            logger.warning(
                f"'{_MULTI_VIEW_UNSUPPORTED_MODEL}' (Meshy-6) 不支持多视图，"
                f"自动切换为 '{_MULTI_VIEW_FALLBACK_MODEL}'"
            )
            ai_model = _MULTI_VIEW_FALLBACK_MODEL

        payload = self._build_payload(
            cfg, kwargs,
            defaults=(
                "enable_pbr", "topology", "target_polycount", "symmetry_mode",
                "should_remesh", "save_pre_remeshed_model", "should_texture", "pose_mode",
            ),
            image_urls=image_urls,
            ai_model=ai_model,
            texture_prompt=self._truncate(kwargs.get("texture_prompt", ""), cfg.max_texture_prompt_length),
            moderation=cfg.moderation,
        )
        logger.info(f"提交 Multi-Image-to-3D 任务 (model={payload['ai_model']}, images={len(image_urls)})")
        return self.multi_image_to_3d.create(payload)

    # ==================== Remesh API ====================

    def create_remesh_task(
        self,
        input_task_id: Optional[str] = None,
        model_url: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """创建重建网格任务，``input_task_id`` 与 ``model_url`` 至少提供其一。"""
        if not input_task_id and not model_url:
            raise ValueError("必须提供 input_task_id 或 model_url 中的一个")

        payload = self._build_payload(
            self._config.remesh, kwargs,
            defaults=(
                "target_formats", "topology", "target_polycount",
                "resize_height", "origin_at", "convert_format_only",
            ),
            input_task_id=input_task_id,
            model_url=model_url,
        )
        logger.info(f"提交 Remesh 任务 (formats={payload['target_formats']})")
        return self.remesh.create(payload)

    # ==================== Rigging API ====================

    def create_rigging_task(
        self,
        model_url: Optional[str] = None,
        input_task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """创建自动绑定骨骼任务，``model_url`` 与 ``input_task_id`` 至少提供其一。"""
        if not model_url and not input_task_id:
            raise ValueError("必须提供 model_url 或 input_task_id 中的一个")

        payload = self._build_payload(
            self._config.rigging, kwargs,
            defaults=("height_meters",),
            passthrough=("texture_image_url",),
            model_url=model_url,
            input_task_id=input_task_id,
        )
        logger.info(f"提交 Rigging 任务 (height={payload['height_meters']}m)")
        return self.rigging.create(payload)

    # ==================== Animation API ====================

    def create_animation_task(self, rig_task_id: str, action_id: int, **kwargs: Any) -> str:
        """创建动画任务。"""
        payload = self._build_payload(
            None, kwargs,
            passthrough=("post_process",),
            rig_task_id=rig_task_id,
            action_id=action_id,
        )
        logger.info(f"提交 Animation 任务 (action_id={action_id})")
        return self.animations.create(payload)

    # ==================== Retexture API ====================

    def create_retexture_task(self, **kwargs: Any) -> str:
        """创建重新纹理任务。"""
        if not kwargs.get("input_task_id") and not kwargs.get("model_url"):
            raise ValueError("必须提供 input_task_id 或 model_url")
        if not kwargs.get("text_style_prompt") and not kwargs.get("image_style_url"):
            raise ValueError("必须提供 text_style_prompt 或 image_style_url")

        payload = self._build_payload(
            self._config.retexture, kwargs,
            defaults=("ai_model", "enable_original_uv", "enable_pbr"),
            passthrough=("input_task_id", "model_url", "text_style_prompt", "image_style_url"),
        )
        logger.info(f"提交 Retexture 任务 (model={payload['ai_model']})")
        return self.retexture.create(payload)


#: 全局单例
meshy_service = MeshyService()
