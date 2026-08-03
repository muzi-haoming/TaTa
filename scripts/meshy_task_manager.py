"""
Meshy 任务管理系统（交互式，会真实调用 API）

运行::

    python -m scripts.meshy_task_manager

原先它混在 ``tests/test_meshy_service.py`` 里，会让自动化测试卡在 ``input()``；
现在独立成脚本，测试目录只保留可无人值守运行的用例。
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from services import MeshyService, TERMINAL_STATUSES
from utils import FileUtil, logger

#: 本地任务记录的存放目录与文件名
_STORE_DIR = "data"
_STORE_FILE = "test_tasks.json"

#: 测试用图片
_TEST_IMAGE = "images/test/test_image.png"

#: 占位图（1x1 PNG），本地测试图缺失时使用
_DUMMY_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

_SEPARATOR = "=" * 80


class TaskManager:
    """本地任务记录的存储与管理（借助 FileUtil 完成读写与沙箱约束）。"""

    def __init__(self, store_dir: str = _STORE_DIR, store_file: str = _STORE_FILE):
        self._fs = FileUtil(store_dir)
        self._store_file = store_file
        self.tasks: List[Dict[str, Any]] = self._load_tasks()

    # ==================== 持久化 ====================

    def _load_tasks(self) -> List[Dict[str, Any]]:
        if not self._fs.exists(self._store_file):
            return []
        try:
            return self._fs.read_json(self._store_file)
        except (OSError, ValueError) as e:
            logger.warning(f"加载任务文件失败: {e}")
            return []

    def _save_tasks(self) -> None:
        try:
            self._fs.write_json(self._store_file, self.tasks)
        except OSError as e:
            logger.warning(f"保存任务文件失败: {e}")

    # ==================== 记录操作 ====================

    @staticmethod
    def _task_id_of(task: Dict[str, Any]) -> Optional[str]:
        """兼容 ``task_id``（本地写入）与 ``id``（API 返回）两种键。"""
        return task.get("task_id") or task.get("id")

    def add_task(self, task_id: str, task_type: str, **extra: Any) -> None:
        if self.get_task(task_id):
            return
        self.tasks.append({
            "task_id": task_id,
            "task_type": task_type,
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            **extra,
        })
        self._save_tasks()

    def update_task(self, task_id: str, **fields: Any) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        task.update(fields)
        self._save_tasks()
        return True

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return next((t for t in self.tasks if self._task_id_of(t) == task_id), None)

    def delete_task(self, task_id: str) -> bool:
        remaining = [t for t in self.tasks if self._task_id_of(t) != task_id]
        if len(remaining) == len(self.tasks):
            return False
        self.tasks = remaining
        self._save_tasks()
        return True

    def list_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = sorted(self.tasks, key=lambda t: t.get("created_at", ""), reverse=True)
        return [t for t in tasks if t.get("task_type") == task_type] if task_type else tasks

    # ==================== 展示 ====================

    @staticmethod
    def _format_created_at(value: Any) -> str:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _model_url_of(task: Dict[str, Any]) -> Optional[str]:
        result = task.get("result") or {}
        return (
            task.get("model_urls", {}).get("glb")
            or result.get("rigged_character_glb_url")
            or result.get("animation_glb_url")
        )

    def display_tasks(self, task_type: Optional[str] = None) -> None:
        tasks = self.list_tasks(task_type)
        if not tasks:
            print("\n[INFO] 当前没有本地任务记录")
            return

        print(f"\n{_SEPARATOR}\nLOCAL TASK LIST\n{_SEPARATOR}")
        for idx, task in enumerate(tasks, 1):
            status = task.get("status", "UNKNOWN")
            print(f"\n[{idx}] {task.get('task_type', 'unknown').upper()} | {self._task_id_of(task) or 'N/A'}")
            print(f"    Status: {status} | Progress: {task.get('progress', 0)}% "
                  f"| Created: {self._format_created_at(task.get('created_at', 'N/A'))}")
            if status == "SUCCEEDED":
                model_url = self._model_url_of(task)
                if model_url:
                    print(f"    Model (GLB): {model_url}")
        print(f"\n{_SEPARATOR}")

    def refresh_task_status(self, service: MeshyService, task_id: str) -> Optional[Dict[str, Any]]:
        """从 API 拉取最新状态并写回本地记录。"""
        task = self.get_task(task_id)
        if not task:
            return None
        try:
            result = service.endpoint(task["task_type"]).get(task_id)
        except Exception as e:  # 端点未知或网络失败都只提示，不中断批量刷新
            logger.warning(f"刷新任务 {task_id} 状态失败: {e}")
            return None
        if result:
            self.update_task(task_id, **result)
        return result


class MeshyManagementSystem:
    """交互式的 Meshy 任务管理菜单。"""

    #: 创建任务的菜单项：菜单选项 -> 任务类型
    _CREATE_OPTIONS = {
        "1": "text-to-3d",
        "2": "image-to-3d",
    }

    def __init__(self):
        self.service = MeshyService()
        self.task_manager = TaskManager()
        self._data_fs = FileUtil(_STORE_DIR)

    # ==================== 辅助 ====================

    def _image_data_uri(self, file_path: str = _TEST_IMAGE) -> str:
        if not self._data_fs.exists(file_path):
            print(f"Warning: 文件不存在: {file_path}，使用占位图")
            return _DUMMY_DATA_URI
        return self._data_fs.read_image(file_path, add_header=True)

    # ==================== 主循环 ====================

    def run(self) -> None:
        print(f"\n{_SEPARATOR}\nMESHY TASK MANAGEMENT SYSTEM\n{_SEPARATOR}")
        actions = {
            "1": self._create_task_menu,
            "2": self.task_manager.display_tasks,
            "3": self._process_task_menu,
            "4": self._refresh_all_tasks,
            "5": self._delete_task_menu,
            "6": self._list_api_tasks_menu,
        }
        while True:
            print("\nMAIN MENU: [1] Create [2] View Local [3] Process "
                  "[4] Refresh [5] Delete [6] List API [q] Quit")
            choice = input("Select option: ").strip()
            if choice == "q":
                return
            action = actions.get(choice)
            if action is None:
                print("[ERROR] Invalid option")
                continue
            action()

    # ==================== 菜单项 ====================

    def _create_task_menu(self) -> None:
        print("\nCREATE: [1] Text-to-3D [2] Image-to-3D [b] Back")
        mode = input("Select task type: ").strip()
        if mode == "b":
            return
        task_type = self._CREATE_OPTIONS.get(mode)
        if not task_type:
            print("[ERROR] Invalid option")
            return

        try:
            if task_type == "text-to-3d":
                prompt = input("Enter prompt: ").strip()
                if not prompt:
                    return
                task_id = self.service.create_text_to_3d_preview_task(prompt)
            else:
                task_id = self.service.create_image_to_3d_task(self._image_data_uri())
        except Exception as e:
            print(f"\n[ERROR] Failed to create task: {e}")
            return

        print(f"\n[SUCCESS] Task created! ID: {task_id}")
        self.task_manager.add_task(task_id, task_type)
        if input("Process now? (y/n): ").lower() == "y":
            self._process_task(task_id, task_type)

    def _pick_task(self, action_name: str) -> Optional[Dict[str, Any]]:
        """展示任务列表并让用户选一个。"""
        self.task_manager.display_tasks()
        tasks = self.task_manager.list_tasks()
        if not tasks:
            return None
        try:
            idx = int(input(f"\nEnter task number to {action_name}: ").strip()) - 1
        except ValueError:
            print("[ERROR] Invalid selection")
            return None
        if not 0 <= idx < len(tasks):
            print("[ERROR] Invalid selection")
            return None
        return tasks[idx]

    def _process_task_menu(self) -> None:
        task = self._pick_task("process")
        if task:
            self._process_task(TaskManager._task_id_of(task), task["task_type"])

    def _process_task(self, task_id: str, task_type: str) -> None:
        print(f"\n[INFO] Streaming task progress: {task_id}")
        try:
            endpoint = self.service.endpoint(task_type)
        except KeyError as e:
            print(f"[ERROR] {e}")
            return

        try:
            final_result: Dict[str, Any] = {}
            for update in endpoint.listen(task_id):
                final_result.update(update)
                self.task_manager.update_task(task_id, **final_result)
                progress = final_result.get("progress", 0)
                status = final_result.get("status", "UNKNOWN")
                filled = int(30 * progress / 100)
                bar = "#" * filled + "-" * (30 - filled)
                print(f"\rProgress: [{bar}] {progress}% | Status: {status}", end="", flush=True)
                if status in TERMINAL_STATUSES:
                    print(f"\n[STATUS] Task {status}!")
                    break
        except Exception as e:
            print(f"\n[ERROR] Stream failed: {e}")

    def _refresh_all_tasks(self) -> None:
        tasks = self.task_manager.list_tasks()
        print(f"\n[INFO] Refreshing {len(tasks)} tasks...")
        for task in tasks:
            self.task_manager.refresh_task_status(self.service, TaskManager._task_id_of(task))
        print("[INFO] Refresh complete.")

    def _delete_task_menu(self) -> None:
        task = self._pick_task("delete")
        if not task:
            return
        task_id = TaskManager._task_id_of(task)
        if input(f"Delete task {task_id}? (y/n): ").lower() != "y":
            return

        try:
            self.service.endpoint(task["task_type"]).delete(task_id)
            print(f"[SUCCESS] Task {task_id} deleted from API.")
        except Exception as e:
            print(f"[ERROR] API deletion failed: {e}")
        self.task_manager.delete_task(task_id)
        print(f"[INFO] Task {task_id} removed from local storage.")

    def _list_api_tasks_menu(self) -> None:
        print("\nLIST API: [1] Text-to-3D [2] Image-to-3D [3] Remesh [b] Back")
        choice = input("Select task type: ").strip()
        task_types = {"1": "text-to-3d", "2": "image-to-3d", "3": "remesh"}
        task_type = task_types.get(choice)
        if not task_type:
            return

        try:
            tasks = self.service.endpoint(task_type).list()
            print(f"\n[INFO] Found {len(tasks)} tasks on API:")
            for task in tasks:
                print(f"  - {task['id']} | Status: {task['status']} ({task['progress']}%)")
        except Exception as e:
            print(f"[ERROR] Failed to list tasks: {e}")


def main() -> None:
    MeshyManagementSystem().run()


if __name__ == "__main__":
    main()
