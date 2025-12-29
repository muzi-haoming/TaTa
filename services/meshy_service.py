"""
Meshy AI 3D生成服务封装
文档: https://docs.meshy.ai/zh

支持的功能:
- Text-to-3D: 文本生成3D模型 (预览 + 精细化)
- Image-to-3D: 单图/多图生成3D模型
- Remesh: 重建网格
- Rigging & Animation: 自动绑定骨骼并添加动画
- Retexture: 重新生成纹理
"""
import json
import os
from typing import Any, Dict, Generator, List, Optional

import requests

from config import meshy_config


class MeshyService:
    """
    Meshy AI 服务封装类（单例模式）。

    通过为每个API端点提供专门的处理器来简化交互。
    示例:
        meshy_service.image_to_3d.get("some-task-id")
        meshy_service.text_to_3d.create_preview_task("a cat")
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # API密钥从环境变量获取，如未设置则使用测试API密钥
            self.api_key = "msy_dummy_api_key_for_test_mode_12345678"
            # self.api_key = os.environ.get("MESHY_API_KEY", "msy_dummy_api_key_for_test_mode_12345678")
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            self._initialized = True
            self._config = meshy_config

            # 为每个API端点设置处理器
            self.text_to_3d = self._MeshyApiEndpoint(self, self._config.api.get_endpoint_url("text_to_3d"))
            self.image_to_3d = self._MeshyApiEndpoint(self, self._config.api.get_endpoint_url("image_to_3d"))
            self.multi_image_to_3d = self._MeshyApiEndpoint(self,
                                                            self._config.api.get_endpoint_url("multi_image_to_3d"))
            self.remesh = self._MeshyApiEndpoint(self, self._config.api.get_endpoint_url("remesh"))
            self.rigging = self._MeshyApiEndpoint(self, self._config.api.get_endpoint_url("rigging"))
            self.animations = self._MeshyApiEndpoint(self, self._config.api.get_endpoint_url("animations"))
            self.retexture = self._MeshyApiEndpoint(self, self._config.api.get_endpoint_url("retexture"))

    # ==================== 内部端点处理器 ====================

    class _MeshyApiEndpoint:
        """处理特定Meshy API端点的通用操作。"""

        def __init__(self, service_instance: 'MeshyService', base_url: str):
            self._service = service_instance
            self.base_url = base_url

        def create(self, payload: Dict[str, Any]) -> str:
            """提交创建任务。"""
            return self._service._submit_task(self.base_url, payload)

        def get(self, task_id: str) -> Dict[str, Any]:
            """获取任务结果。"""
            url = f"{self.base_url}/{task_id}"
            return self._service._get_task_result(url)

        def delete(self, task_id: str) -> bool:
            """删除任务。"""
            url = f"{self.base_url}/{task_id}"
            return self._service._delete_task(url)

        def list(self, page_num: int = None, page_size: int = None, sort_by: str = None) -> List[Dict[str, Any]]:
            """列出任务。"""
            task_list_config = self._service._config.task_list
            page_num = page_num or 1
            page_size = page_size or task_list_config.default_page_size
            sort_by = sort_by or task_list_config.default_sort_by
            return self._service._list_tasks(self.base_url, page_num, page_size, sort_by)

        def listen(self, task_id: str) -> Generator[Dict[str, Any], None, None]:
            """通过SSE流式监听任务进度。"""
            stream_url = f"{self.base_url}/{task_id}/stream"
            return self._service._listen_to_stream(stream_url)

    # ==================== 通用私有方法 ====================

    def _submit_task(self, url: str, payload: dict) -> str:
        """统一提交任务逻辑。"""
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()["result"]
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response"
            print(f"Meshy API Creation Failed: {e}\nDetails: {error_details}")
            raise

    def _get_task_result(self, url: str) -> Dict[str, Any]:
        """统一获取任务结果逻辑。"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response"
            print(f"Failed to get task result: {e}\nDetails: {error_details}")
            raise

    def _delete_task(self, url: str) -> bool:
        """统一删除任务逻辑。"""
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response"
            print(f"Failed to delete task: {e}\nDetails: {error_details}")
            raise

    def _list_tasks(self, url: str, page_num: int, page_size: int, sort_by: str) -> List[Dict[str, Any]]:
        """统一列表任务逻辑。"""
        max_page_size = self._config.task_list.max_page_size
        params = {"page_num": page_num, "page_size": min(page_size, max_page_size), "sort_by": sort_by}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response else "No response"
            print(f"Failed to list tasks: {e}\nDetails: {error_details}")
            raise

    def _listen_to_stream(self, stream_url: str) -> Generator[Dict[str, Any], None, None]:
        """统一的 SSE 流式监听逻辑。"""
        print(f"Listening to stream: {stream_url}")
        try:
            with requests.get(stream_url, headers=self.headers, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith(b"data:"):
                        continue
                    try:
                        data = json.loads(line.decode('utf-8')[5:])
                        yield data
                        if data.get("status") in ["SUCCEEDED", "FAILED", "CANCELED"]:
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield {"status": "CONNECTION_ERROR", "progress": 0, "error": str(e)}

    def _prepare_payload(self, **kwargs: Any) -> Dict[str, Any]:
        """根据提供的非None参数创建payload。"""
        return {k: v for k, v in kwargs.items() if v is not None}

    # ==================== Text-to-3D API ====================

    def create_text_to_3d_preview_task(self, prompt: str, **kwargs: Any) -> str:
        """创建 Text-to-3D 预览任务。"""
        preview_config = self._config.text_to_3d.preview
        max_prompt_length = preview_config.max_prompt_length

        payload = self._prepare_payload(
            mode="preview",
            prompt=prompt[:max_prompt_length],
            art_style=kwargs.get("art_style", preview_config.art_style),
            ai_model=kwargs.get("ai_model", preview_config.ai_model),
            topology=kwargs.get("topology", preview_config.topology),
            target_polycount=kwargs.get("target_polycount", preview_config.target_polycount),
            should_remesh=kwargs.get("should_remesh", preview_config.should_remesh),
            symmetry_mode=kwargs.get("symmetry_mode", preview_config.symmetry_mode),
            pose_mode=kwargs.get("pose_mode", preview_config.pose_mode),
            seed=kwargs.get("seed", None),
            moderation=preview_config.moderation
        )
        print(f"Submitting Text-to-3D Preview Task (Model: {payload['ai_model']})...")
        return self.text_to_3d.create(payload)

    def create_text_to_3d_refine_task(self, preview_task_id: str, **kwargs: Any) -> str:
        """创建 Text-to-3D 精细化任务。"""
        refine_config = self._config.text_to_3d.refine
        max_texture_prompt_length = refine_config.max_texture_prompt_length

        texture_prompt = kwargs.get("texture_prompt", "")
        if texture_prompt:
            texture_prompt = texture_prompt[:max_texture_prompt_length]

        payload = self._prepare_payload(
            mode="refine",
            preview_task_id=preview_task_id,
            enable_pbr=kwargs.get("enable_pbr", refine_config.enable_pbr),
            texture_prompt=texture_prompt,
            texture_image_url=kwargs.get("texture_image_url"),
            ai_model=kwargs.get("ai_model"),
            moderation=refine_config.moderation
        )
        print(f"Submitting Text-to-3D Refine Task (Preview: {preview_task_id})...")
        return self.text_to_3d.create(payload)

    # ==================== Image-to-3D API ====================

    def create_image_to_3d_task(self, image_url: str, **kwargs: Any) -> str:
        """创建单图转3D任务。"""
        img_config = self._config.image_to_3d
        max_texture_prompt_length = img_config.max_texture_prompt_length

        texture_prompt = kwargs.get("texture_prompt", "")
        if texture_prompt:
            texture_prompt = texture_prompt[:max_texture_prompt_length]

        payload = self._prepare_payload(
            image_url=image_url,
            ai_model=kwargs.get("ai_model", img_config.ai_model),
            enable_pbr=kwargs.get("enable_pbr", img_config.enable_pbr),
            texture_prompt=texture_prompt,
            texture_image_url=kwargs.get("texture_image_url"),
            topology=kwargs.get("topology", img_config.topology),
            target_polycount=kwargs.get("target_polycount", img_config.target_polycount),
            symmetry_mode=kwargs.get("symmetry_mode", img_config.symmetry_mode),
            should_remesh=kwargs.get("should_remesh", img_config.should_remesh),
            save_pre_remeshed_model=kwargs.get("save_pre_remeshed_model", img_config.save_pre_remeshed_model),
            should_texture=kwargs.get("should_texture", img_config.should_texture),
            pose_mode=kwargs.get("pose_mode", img_config.pose_mode),
            moderation=img_config.moderation
        )
        print(f"Submitting Single-Image Task (Model: {payload['ai_model']})...")
        return self.image_to_3d.create(payload)

    # ==================== Multi-Image-to-3D API ====================

    def create_multi_image_to_3d_task(self, image_urls: List[str], **kwargs: Any) -> str:
        """创建多图转3D任务（1-4张图片）。"""
        multi_config = self._config.multi_image_to_3d

        if not multi_config.min_images <= len(image_urls) <= multi_config.max_images:
            raise ValueError(f"image_urls 必须包含 {multi_config.min_images}-{multi_config.max_images} 张图片")

        ai_model = kwargs.get("ai_model", multi_config.ai_model)
        if ai_model == "latest":
            print("[Warning] 'latest' (Meshy-6) model does not support Multi-View. Auto-switching to 'meshy-5'.")
            ai_model = "meshy-5"

        texture_prompt = kwargs.get("texture_prompt", "")
        if texture_prompt:
            texture_prompt = texture_prompt[:multi_config.max_texture_prompt_length]

        payload = self._prepare_payload(
            image_urls=image_urls,
            ai_model=ai_model,
            enable_pbr=kwargs.get("enable_pbr", multi_config.enable_pbr),
            texture_prompt=texture_prompt,
            topology=kwargs.get("topology", multi_config.topology),
            target_polycount=kwargs.get("target_polycount", multi_config.target_polycount),
            symmetry_mode=kwargs.get("symmetry_mode", multi_config.symmetry_mode),
            should_remesh=kwargs.get("should_remesh", multi_config.should_remesh),
            save_pre_remeshed_model=kwargs.get("save_pre_remeshed_model", multi_config.save_pre_remeshed_model),
            should_texture=kwargs.get("should_texture", multi_config.should_texture),
            pose_mode=kwargs.get("pose_mode", multi_config.pose_mode),
            moderation=multi_config.moderation
        )
        print(f"Submitting Multi-Image Task (Model: {payload['ai_model']})...")
        return self.multi_image_to_3d.create(payload)

    # ==================== Remesh API ====================

    def create_remesh_task(self, input_task_id: str = None, model_url: str = None, **kwargs: Any) -> str:
        """创建重建网格任务。"""
        if not input_task_id and not model_url:
            raise ValueError("必须提供 input_task_id 或 model_url 中的一个")

        remesh_config = self._config.remesh
        payload = self._prepare_payload(
            input_task_id=input_task_id,
            model_url=model_url,
            target_formats=kwargs.get("target_formats", remesh_config.target_formats),
            topology=kwargs.get("topology", remesh_config.topology),
            target_polycount=kwargs.get("target_polycount", remesh_config.target_polycount),
            resize_height=kwargs.get("resize_height", remesh_config.resize_height),
            origin_at=kwargs.get("origin_at", remesh_config.origin_at),
            convert_format_only=kwargs.get("convert_format_only", remesh_config.convert_format_only)
        )
        print(f"Submitting Remesh Task (Formats: {payload['target_formats']})...")
        return self.remesh.create(payload)

    # ==================== Rigging API ====================

    def create_rigging_task(self, model_url: str = None, input_task_id: str = None, **kwargs: Any) -> str:
        """创建自动绑定骨骼任务。"""
        if not model_url and not input_task_id:
            raise ValueError("必须提供 model_url 或 input_task_id 中的一个")

        rigging_config = self._config.rigging
        payload = self._prepare_payload(
            model_url=model_url,
            input_task_id=input_task_id,
            height_meters=kwargs.get("height_meters", rigging_config.height_meters),
            texture_image_url=kwargs.get("texture_image_url")
        )
        print(f"Submitting Rigging Task (Height: {payload['height_meters']}m)...")
        return self.rigging.create(payload)

    # ==================== Animation API ====================

    def create_animation_task(self, rig_task_id: str, action_id: int, **kwargs: Any) -> str:
        """创建动画任务。"""
        payload = self._prepare_payload(
            rig_task_id=rig_task_id,
            action_id=action_id,
            post_process=kwargs.get("post_process")
        )
        print(f"Submitting Animation Task (Action ID: {action_id})...")
        return self.animations.create(payload)

    # ==================== Retexture API ====================

    def create_retexture_task(self, **kwargs: Any) -> str:
        """创建重新纹理任务。"""
        if not kwargs.get("input_task_id") and not kwargs.get("model_url"):
            raise ValueError("必须提供 input_task_id 或 model_url")
        if not kwargs.get("text_style_prompt") and not kwargs.get("image_style_url"):
            raise ValueError("必须提供 text_style_prompt 或 image_style_url")

        retexture_config = self._config.retexture
        payload = self._prepare_payload(
            input_task_id=kwargs.get("input_task_id"),
            model_url=kwargs.get("model_url"),
            text_style_prompt=kwargs.get("text_style_prompt"),
            image_style_url=kwargs.get("image_style_url"),
            ai_model=kwargs.get("ai_model", retexture_config.ai_model),
            enable_original_uv=kwargs.get("enable_original_uv", retexture_config.enable_original_uv),
            enable_pbr=kwargs.get("enable_pbr", retexture_config.enable_pbr)
        )
        print(f"Submitting Retexture Task (Model: {payload['ai_model']})...")
        return self.retexture.create(payload)

    # ==================== Blender 自动化 ====================

    def _download_file(self, url: str, folder: str, filename: str) -> Optional[str]:
        """(私有) 下载文件到指定文件夹。"""
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        chunk_size = self._config.download.chunk_size
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        f.write(chunk)
            print(f"Downloaded '{filename}' to '{folder}'")
            return filepath
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return None


# 实例化单例
meshy_service = MeshyService()
