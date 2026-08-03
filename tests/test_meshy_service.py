"""
Meshy Service 单元测试（全部 Mock，不产生真实 API 调用）

交互式的真实调用工具见 ``python -m scripts.meshy_task_manager``。

打桩目标是 ``services.base.requests``——所有 HTTP 都经由
:class:`services.base.HttpApiClient` 发出。
"""
import unittest
from unittest.mock import MagicMock, patch

from services import MeshyService

_DUMMY_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


class TestMeshyService(unittest.TestCase):
    """任务创建与端点操作"""

    def setUp(self):
        self.service = MeshyService()

    def test_service_is_singleton(self):
        self.assertIs(MeshyService(), self.service)

    # ==================== 端点访问 ====================

    def test_endpoint_lookup_accepts_both_spellings(self):
        self.assertIs(self.service.endpoint("image-to-3d"), self.service.image_to_3d)
        self.assertIs(self.service.endpoint("image_to_3d"), self.service.image_to_3d)

    def test_endpoint_lookup_rejects_unknown_name(self):
        with self.assertRaises(KeyError):
            self.service.endpoint("no-such-endpoint")

    def test_endpoint_urls_come_from_config(self):
        self.assertTrue(self.service.text_to_3d.base_url.endswith("/v2/text-to-3d"))
        self.assertTrue(self.service.image_to_3d.base_url.endswith("/v1/image-to-3d"))

    # ==================== Text-to-3D ====================

    @patch("services.base.requests.post")
    def test_text_to_3d_preview(self, mock_post):
        mock_post.return_value.json.return_value = {"result": "mock_text_preview_123"}

        task_id = self.service.create_text_to_3d_preview_task(prompt="A cat")

        self.assertEqual(task_id, "mock_text_preview_123")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["mode"], "preview")
        self.assertEqual(payload["prompt"], "A cat")
        # 默认值来自 meshy_config.text_to_3d.preview
        self.assertEqual(payload["art_style"], "realistic")
        self.assertEqual(payload["topology"], "quad")
        # 未提供的可选字段不应出现在 payload 中
        self.assertNotIn("seed", payload)

    @patch("services.base.requests.post")
    def test_text_to_3d_preview_honours_overrides(self, mock_post):
        mock_post.return_value.json.return_value = {"result": "t"}

        self.service.create_text_to_3d_preview_task("A cat", art_style="sculpture", seed=7)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["art_style"], "sculpture")
        self.assertEqual(payload["seed"], 7)

    @patch("services.base.requests.post")
    def test_text_to_3d_preview_truncates_prompt(self, mock_post):
        mock_post.return_value.json.return_value = {"result": "t"}
        limit = self.service._config.text_to_3d.preview.max_prompt_length

        self.service.create_text_to_3d_preview_task("x" * (limit + 50))

        self.assertEqual(len(mock_post.call_args.kwargs["json"]["prompt"]), limit)

    @patch("services.base.requests.post")
    def test_text_to_3d_refine(self, mock_post):
        mock_post.return_value.json.return_value = {"result": "mock_refine"}

        self.service.create_text_to_3d_refine_task("preview_1")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["mode"], "refine")
        self.assertEqual(payload["preview_task_id"], "preview_1")

    # ==================== Image-to-3D ====================

    @patch("services.base.requests.post")
    def test_image_to_3d_with_texture_prompt(self, mock_post):
        mock_post.return_value.json.return_value = {"result": "mock_texture_task_789"}

        task_id = self.service.create_image_to_3d_task(_DUMMY_DATA_URI, texture_prompt="wood")

        self.assertEqual(task_id, "mock_texture_task_789")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["texture_prompt"], "wood")
        self.assertEqual(payload["image_url"], _DUMMY_DATA_URI)
        self.assertFalse(payload["moderation"])

    @patch("services.base.requests.post")
    def test_multi_image_downgrades_latest_model(self, mock_post):
        mock_post.return_value.json.return_value = {"result": "mock_multi"}

        self.service.create_multi_image_to_3d_task([_DUMMY_DATA_URI], ai_model="latest")

        self.assertEqual(mock_post.call_args.kwargs["json"]["ai_model"], "meshy-5")

    def test_multi_image_rejects_too_many_images(self):
        max_images = self.service._config.multi_image_to_3d.max_images
        with self.assertRaises(ValueError):
            self.service.create_multi_image_to_3d_task([_DUMMY_DATA_URI] * (max_images + 1))

    def test_multi_image_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            self.service.create_multi_image_to_3d_task([])

    # ==================== 其它任务的参数校验 ====================

    def test_remesh_requires_a_source(self):
        with self.assertRaises(ValueError):
            self.service.create_remesh_task()

    def test_rigging_requires_a_source(self):
        with self.assertRaises(ValueError):
            self.service.create_rigging_task()

    def test_retexture_requires_source_and_style(self):
        with self.assertRaises(ValueError):
            self.service.create_retexture_task(text_style_prompt="wood")
        with self.assertRaises(ValueError):
            self.service.create_retexture_task(model_url="http://x/y.glb")

    @patch("services.base.requests.post")
    def test_remesh_keeps_falsy_config_values(self, mock_post):
        """resize_height=0 / convert_format_only=False 属于有效取值，不能被过滤掉。"""
        mock_post.return_value.json.return_value = {"result": "mock_remesh"}

        self.service.create_remesh_task(input_task_id="task_1")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["resize_height"], 0)
        self.assertIs(payload["convert_format_only"], False)
        self.assertNotIn("model_url", payload)

    # ==================== 端点通用操作 ====================

    @patch("services.base.requests.get")
    def test_get_task_result(self, mock_get):
        mock_get.return_value.json.return_value = {"id": "task_123", "status": "SUCCEEDED"}

        result = self.service.text_to_3d.get("task_123")

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertTrue(mock_get.call_args.args[0].endswith("/task_123"))

    @patch("services.base.requests.delete")
    def test_delete_task(self, mock_delete):
        self.assertTrue(self.service.image_to_3d.delete("image_task_123"))
        mock_delete.assert_called_once()

    @patch("services.base.requests.get")
    def test_list_clamps_page_size(self, mock_get):
        mock_get.return_value.json.return_value = []
        max_page_size = self.service._config.task_list.max_page_size

        self.service.text_to_3d.list(page_size=max_page_size + 100)

        self.assertEqual(mock_get.call_args.kwargs["params"]["page_size"], max_page_size)

    @patch("services.base.requests.get")
    def test_stream_listening(self, mock_get):
        sse_data = [
            b'data: {"progress": 50, "status": "IN_PROGRESS"}\n',
            b'data: {"progress": 100, "status": "SUCCEEDED"}\n',
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_lines.return_value = iter(sse_data)
        mock_response.__enter__.return_value = mock_response
        mock_get.return_value = mock_response

        updates = list(self.service.remesh.listen("test_task_123"))

        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[-1]["status"], "SUCCEEDED")

    @patch("services.base.requests.get")
    def test_stream_stops_at_terminal_status(self, mock_get):
        sse_data = [
            b'data: {"progress": 100, "status": "SUCCEEDED"}\n',
            b'data: {"progress": 0, "status": "SHOULD_NOT_BE_READ"}\n',
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_lines.return_value = iter(sse_data)
        mock_response.__enter__.return_value = mock_response
        mock_get.return_value = mock_response

        updates = list(self.service.remesh.listen("t"))

        self.assertEqual(len(updates), 1)

    @patch("services.base.requests.get")
    def test_stream_yields_connection_error_event(self, mock_get):
        mock_get.side_effect = OSError("boom")

        updates = list(self.service.image_to_3d.listen("t"))

        self.assertEqual(updates[0]["status"], "CONNECTION_ERROR")


if __name__ == "__main__":
    unittest.main()
