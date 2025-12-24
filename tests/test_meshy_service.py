"""
Meshy Service 测试模块

包含:
1. 单元测试 (Mock)
2. 交互式管理系统 (真实 API 调用)
"""

import base64
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch
import unittest

from services import MeshyService


class TaskManager:
    """任务管理器：用于存储和管理测试中的任务信息"""
    _tasks_file = "data/test_tasks.json"

    def __init__(self):
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> List[Dict]:
        """从文件加载任务列表"""
        if not os.path.exists(self._tasks_file):
            return []
        try:
            with open(self._tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Warning: 加载任务文件失败: {e}")
            return []

    def _save_tasks(self):
        """保存任务列表到文件"""
        try:
            os.makedirs(os.path.dirname(self._tasks_file), exist_ok=True)
            with open(self._tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Warning: 保存任务文件失败: {e}")

    def add_task(self, task_id: str, task_type: str, **kwargs):
        """添加新任务"""
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        if not any(t["task_id"] == task_id for t in self.tasks):
            self.tasks.append(task)
            self._save_tasks()

    def update_task(self, task_id: str, **kwargs):
        """更新任务信息"""
        task = self.get_task(task_id)
        if task:
            task.update(kwargs)
            self._save_tasks()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        return next((t for t in self.tasks if t.get("task_id") == task_id or t.get("id") == task_id), None)

    def delete_task(self, task_id: str) -> bool:
        """从管理器中删除任务记录"""
        initial_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.get("task_id") != task_id and t.get("id") != task_id]
        if len(self.tasks) < initial_len:
            self._save_tasks()
            return True
        return False

    def list_tasks(self, task_type: Optional[str] = None) -> List[Dict]:
        """列出所有任务，可选按类型过滤"""
        tasks = sorted(self.tasks, key=lambda t: t.get("created_at", ""), reverse=True)
        if task_type:
            return [t for t in tasks if t.get("task_type") == task_type]
        return tasks

    def display_tasks(self, task_type: Optional[str] = None):
        """显示任务列表"""
        tasks = self.list_tasks(task_type)
        if not tasks:
            print("\n[INFO] 当前没有本地任务记录")
            return

        print("\n" + "=" * 80 + "\nLOCAL TASK LIST\n" + "=" * 80)
        for idx, task in enumerate(tasks, 1):
            task_id = task.get("id", task.get("task_id", "N/A"))
            task_type_name = task.get("task_type", "unknown")
            status = task.get("status", "UNKNOWN")
            created_at = task.get("created_at", "N/A")
            progress = task.get("progress", 0)

            try:
                dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                created_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                created_str = str(created_at)

            print(f"\n[{idx}] {task_type_name.upper()} | {task_id}")
            print(f"    Status: {status} | Progress: {progress}% | Created: {created_str}")

            if status == "SUCCEEDED":
                model_url = task.get("model_urls", {}).get("glb") or \
                            task.get("result", {}).get("rigged_character_glb_url") or \
                            task.get("result", {}).get("animation_glb_url")
                if model_url:
                    print(f"    Model (GLB): {model_url}")
        print("\n" + "=" * 80)

    def refresh_task_status(self, service: MeshyService, task_id: str) -> Optional[Dict]:
        """刷新任务状态（从 API 获取最新状态）"""
        task = self.get_task(task_id)
        if not task:
            return None

        task_type = task.get("task_type")
        endpoint_map = {
            "text-to-3d": service.text_to_3d, "image-to-3d": service.image_to_3d,
            "multi-image-to-3d": service.multi_image_to_3d, "remesh": service.remesh,
            "rigging": service.rigging, "animations": service.animations, "retexture": service.retexture,
        }
        endpoint = endpoint_map.get(task_type)
        if not endpoint:
            return None

        try:
            result = endpoint.get(task_id)
            if result:
                self.update_task(task_id, **result)
            return result
        except Exception as e:
            print(f"Warning: 刷新任务 {task_id} 状态失败: {e}")
            return None


class TestMeshyService(unittest.TestCase):
    """Meshy Service 单元测试"""

    def setUp(self):
        """测试前的准备工作"""
        print(f"\n--- Starting Test: {self._testMethodName} ---")
        self.service = MeshyService()
        self.local_image_single = "data/images/test/test_image.png"
        self.dummy_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    def _file_to_data_uri(self, file_path):
        """读取本地文件并转换为 Data URI (Base64)"""
        if not os.path.exists(file_path):
            return self.dummy_base64
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

    @patch('services.meshy_service.requests.post')
    def test_text_to_3d_preview(self, mock_post):
        """[Mock] 测试 Text-to-3D 预览任务创建"""
        mock_post.return_value.json.return_value = {"result": "mock_text_preview_123"}
        task_id = self.service.create_text_to_3d_preview_task(prompt="A cat")
        self.assertEqual(task_id, "mock_text_preview_123")
        self.assertEqual(mock_post.call_args.kwargs['json']["mode"], "preview")
        print("[PASS] Text-to-3D 预览任务创建测试通过")

    @patch('services.meshy_service.requests.get')
    def test_get_task_result(self, mock_get):
        """[Mock] 测试获取任务结果"""
        mock_get.return_value.json.return_value = {"id": "task_123", "status": "SUCCEEDED"}
        result = self.service.text_to_3d.get("task_123")
        self.assertEqual(result["status"], "SUCCEEDED")
        print("[PASS] 获取任务结果测试通过")

    @patch('services.meshy_service.requests.delete')
    def test_delete_task(self, mock_delete):
        """[Mock] 测试删除任务"""
        result = self.service.image_to_3d.delete("image_task_123")
        self.assertTrue(result)
        mock_delete.assert_called_once()
        print("[PASS] 删除任务测试通过")

    @patch('services.meshy_service.requests.post')
    def test_image_to_3d_with_texture_prompt(self, mock_post):
        """[Mock] 测试带纹理提示的单图转3D任务"""
        mock_post.return_value.json.return_value = {"result": "mock_texture_task_789"}
        image_uri = self._file_to_data_uri(self.local_image_single)
        task_id = self.service.create_image_to_3d_task(image_uri, texture_prompt="wood")
        self.assertEqual(task_id, "mock_texture_task_789")
        self.assertEqual(mock_post.call_args.kwargs['json']["texture_prompt"], "wood")
        print("[PASS] 带纹理提示的单图转3D任务测试通过")

    @patch('services.meshy_service.requests.get')
    def test_stream_listening(self, mock_get):
        """[Mock] 测试流式监听"""
        sse_data = [
            b'data: {"progress": 50, "status": "IN_PROGRESS"}\n',
            b'data: {"progress": 100, "status": "SUCCEEDED"}\n'
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_lines.return_value = iter(sse_data)
        mock_response.__enter__.return_value = mock_response
        mock_get.return_value = mock_response

        stream_generator = self.service.remesh.listen("test_task_123")
        updates = list(stream_generator)
        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[-1]['status'], "SUCCEEDED")
        print("[PASS] 流式监听测试通过")

    def test_management_system(self):
        MeshyManagementSystem().run()


class MeshyManagementSystem:
    """Meshy 任务管理系统 - 真实 API 调用测试"""

    def __init__(self):
        self.service = MeshyService()
        self.task_manager = TaskManager()
        self.local_image_single = "data/images/test/test_image.png"
        self.local_images_multi = ["data/images/test/test_front.png", "data/images/test/test_back.png"]
        self.dummy_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        self.blender_path = "blender"  # 假定 blender 在系统路径中

    def _file_to_data_uri(self, file_path):
        if not os.path.exists(file_path):
            print(f"Warning: 文件不存在: {file_path}")
            return self.dummy_base64
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

    def run(self):
        print("\n" + "=" * 80 + "\nMESHY TASK MANAGEMENT SYSTEM\n" + "=" * 80)
        while True:
            print("\nMAIN MENU: [1] Create [2] View Local [3] Process [4] Refresh [5] Delete [6] List API [q] Quit")
            choice = input("Select option: ").strip()
            if choice == 'q': break
            elif choice == '1': self._create_task_menu()
            elif choice == '2': self.task_manager.display_tasks()
            elif choice == '3': self._process_task_menu()
            elif choice == '4': self._refresh_all_tasks()
            elif choice == '5': self._delete_task_menu()
            elif choice == '6': self._list_api_tasks_menu()
            else: print("[ERROR] Invalid option")

    def _create_task_menu(self):
        print("\nCREATE: [1] Text-to-3D [2] Image-to-3D [3] Multi-Image [4] Remesh [5] Rigging [6] Animation [7] Retexture [b] Back")
        mode = input("Select task type: ").strip()
        if mode == 'b': return

        task_id, task_type = None, None
        try:
            if mode == '1':
                prompt = input("Enter prompt: ").strip()
                if prompt: task_id, task_type = self.service.create_text_to_3d_preview_task(prompt), "text-to-3d"
            elif mode == '2':
                data_uri = self._file_to_data_uri(self.local_image_single)
                task_id, task_type = self.service.create_image_to_3d_task(data_uri), "image-to-3d"
            # ... 其他创建逻辑可以按需添加 ...
            else:
                print("[ERROR] Invalid option")

            if task_id:
                print(f"\n[SUCCESS] Task created! ID: {task_id}")
                self.task_manager.add_task(task_id, task_type)
                if input("Process now? (y/n): ").lower() == 'y':
                    self._process_task(task_id, task_type)
        except Exception as e:
            print(f"\n[ERROR] Failed to create task: {e}")

    def _process_task_menu(self):
        self.task_manager.display_tasks()
        tasks = self.task_manager.list_tasks()
        if not tasks: return
        try:
            idx = int(input("\nEnter task number to process: ").strip()) - 1
            if 0 <= idx < len(tasks):
                task = tasks[idx]
                self._process_task(task.get("id") or task.get("task_id"), task["task_type"])
        except (ValueError, IndexError):
            print("[ERROR] Invalid selection")

    def _process_task(self, task_id: str, task_type: str):
        print(f"\n[INFO] Streaming task progress: {task_id}")
        endpoint_map = {
            "text-to-3d": self.service.text_to_3d, "image-to-3d": self.service.image_to_3d,
            "multi-image-to-3d": self.service.multi_image_to_3d, "remesh": self.service.remesh,
            "rigging": self.service.rigging, "animations": self.service.animations, "retexture": self.service.retexture,
        }
        endpoint = endpoint_map.get(task_type)
        if not endpoint:
            print(f"[ERROR] Unknown task type: {task_type}")
            return

        try:
            final_result = {}
            for update in endpoint.listen(task_id):
                final_result.update(update)
                self.task_manager.update_task(task_id, **final_result)
                progress = final_result.get('progress', 0)
                status = final_result.get('status', 'UNKNOWN')
                bar = '#' * int(30 * progress / 100) + '-' * (30 - int(30 * progress / 100))
                print(f"\rProgress: [{bar}] {progress}% | Status: {status}", end="", flush=True)
                if status in ["SUCCEEDED", "FAILED", "CANCELED"]:
                    print(f"\n[STATUS] Task {status}!")
                    break
        except Exception as e:
            print(f"\n[ERROR] Stream failed: {e}")

    def _refresh_all_tasks(self):
        tasks = self.task_manager.list_tasks()
        print(f"\n[INFO] Refreshing {len(tasks)} tasks...")
        for task in tasks:
            task_id = task.get("id") or task.get("task_id")
            self.task_manager.refresh_task_status(self.service, task_id)
        print("[INFO] Refresh complete.")

    def _delete_task_menu(self):
        self.task_manager.display_tasks()
        tasks = self.task_manager.list_tasks()
        if not tasks: return
        try:
            idx = int(input("\nEnter task number to delete: ").strip()) - 1
            if 0 <= idx < len(tasks):
                task = tasks[idx]
                task_id = task.get("id") or task.get("task_id")
                if input(f"Delete task {task_id}? (y/n): ").lower() != 'y': return

                endpoint_map = {"text-to-3d": self.service.text_to_3d, "image-to-3d": self.service.image_to_3d,
                                "multi-image-to-3d": self.service.multi_image_to_3d, "remesh": self.service.remesh,
                                "rigging": self.service.rigging, "animations": self.service.animations,
                                "retexture": self.service.retexture}
                endpoint = endpoint_map.get(task["task_type"])
                if endpoint:
                    try:
                        endpoint.delete(task_id)
                        print(f"[SUCCESS] Task {task_id} deleted from API.")
                    except Exception as e:
                        print(f"[ERROR] API deletion failed: {e}")
                self.task_manager.delete_task(task_id)
                print(f"[INFO] Task {task_id} removed from local storage.")
        except (ValueError, IndexError):
            print("[ERROR] Invalid selection")

    def _list_api_tasks_menu(self):
        print("\nLIST API: [1] Text-to-3D [2] Image-to-3D [3] Remesh [b] Back")
        choice = input("Select task type: ").strip()
        endpoint_map = {'1': self.service.text_to_3d, '2': self.service.image_to_3d, '3': self.service.remesh}
        endpoint = endpoint_map.get(choice)
        if not endpoint: return

        try:
            tasks = endpoint.list()
            print(f"\n[INFO] Found {len(tasks)} tasks on API:")
            for t in tasks:
                print(f"  - {t['id']} | Status: {t['status']} ({t['progress']}%)")
        except Exception as e:
            print(f"[ERROR] Failed to list tasks: {e}")


if __name__ == '__main__':
    if '--manage' in __import__('sys').argv:
        MeshyManagementSystem().run()
    else:
        unittest.main(argv=['first-arg-is-ignored'], exit=False)
