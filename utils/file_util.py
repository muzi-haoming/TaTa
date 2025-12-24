import base64
import json

import aiofiles
import aiohttp
import yaml
import shutil
from pathlib import Path
from typing import Union, List, Any, Dict


class FileUtil:
    """
    文件操作工具类
    特点：
    1. 安全沙箱：限制所有操作在 root_dir 下，防止 Agent 访问系统敏感文件。
    2. 自动容错：写入时自动创建父目录。
    3. 多格式支持：原生支持 text, json, yaml, bytes。
    """

    def __init__(self, root_dir: str):
        """
        初始化文件工具。
        :param root_dir: 所有文件操作的根目录（沙箱目录）。
        """
        self.root = Path(root_dir).resolve()
        # 初始化时确保根目录存在
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)
        print(f"--- [FileUtil] Root initialized at: {self.root} ---")

    def _resolve(self, sub_path: str) -> Path:
        """
        [内部方法] 解析路径并进行安全检查 (防止 ../../etc/passwd 攻击)
        """
        # 将输入路径结合根目录
        target = (self.root / sub_path).resolve()

        # 安全检查：确保解析后的路径依然在 root 目录下
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"Security Error: Access denied to {sub_path} (Outside workspace)")

        return target

    def _ensure_parent(self, path: Path):
        """确保父目录存在"""
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    # ==========================
    # 写入操作 (Write)
    # ==========================
    def write_text(self, file_path: str, content: str, append: bool = False) -> str:
        """写入纯文本文件"""
        target = self._resolve(self.root / file_path)
        self._ensure_parent(target)

        mode = "a" if append else "w"
        target.write_text(content, encoding="utf-8") if not append else None

        # pathlib 的 write_text 不支持 append 模式，如果需要 append 用 open
        if append:
            with target.open(mode="a", encoding="utf-8") as f:
                f.write(content)
        else:
            target.write_text(content, encoding="utf-8")

        return str(target)

    def write_json(self, file_path: str, data: Union[Dict, List]) -> str:
        """写入 JSON 文件"""
        target = self._resolve(file_path)
        self._ensure_parent(target)

        # ensure_ascii=False 保证中文正常显示
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(target)

    def write_yaml(self, file_path: str, data: Any) -> str:
        """写入 YAML 文件 (需安装 PyYAML)"""
        target = self._resolve(file_path)
        self._ensure_parent(target)

        with target.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        return str(target)

    def write_bytes(self, file_path: str, data: bytes) -> str:
        """写入二进制文件 (如图片、模型)"""
        target = self._resolve(file_path)
        self._ensure_parent(target)
        target.write_bytes(data)
        return str(target)

    def write_image(self, file_path: str, base64_string: str) -> str:
        """将 Base64 字符串解码并保存为图片文件"""
        target = self._resolve(file_path)
        self._ensure_parent(target)

        if "," in base64_string:
            base64_string = base64_string.split(",", 1)[1]

        try:
            image_data = base64.b64decode(base64_string)
        except Exception as e:
            raise ValueError(f"Invalid Base64 string: {str(e)}")

        target.write_bytes(image_data)

        return str(target)

    # ==========================
    # 读取操作 (Read)
    # ==========================
    def read_text(self, file_path: str) -> str:
        target = self._resolve(file_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return target.read_text(encoding="utf-8")

    def read_json(self, file_path: str) -> Union[Dict, List]:
        content = self.read_text(file_path)
        return json.loads(content)

    def read_yaml(self, file_path: str) -> Any:
        target = self._resolve(file_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with target.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def read_image(self, file_path: str, add_header: bool = False) -> str:
        """读取图片文件并转换为 Base64 字符串"""
        target = self._resolve(file_path)
        if not target.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        image_data = target.read_bytes()

        b64_bytes = base64.b64encode(image_data)

        b64_string = b64_bytes.decode('utf-8')

        if add_header:
            suffix = target.suffix.lower().replace('.', '')
            if suffix == 'jpg': suffix = 'jpeg'

            return f"data:image/{suffix};base64,{b64_string}"

        return b64_string

    # ==========================
    # 校验与查询 (Check & List)
    # ==========================
    def exists(self, file_path: str) -> bool:
        """检查文件或目录是否存在"""
        try:
            return self._resolve(file_path).exists()
        except ValueError:
            return False  # 路径不安全视为不存在

    def list_files(self, dir_path: str = ".", pattern: str = "*", recursive: bool = False) -> List[str]:
        """列出目录下的文件"""
        target = self._resolve(dir_path)
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {dir_path}")

        # 决定使用 glob 还是 rglob (递归)
        glob_func = target.rglob if recursive else target.glob

        # 返回相对路径，方便阅读
        files = [
            str(p.relative_to(self.root))
            for p in glob_func(pattern)
            if p.is_file()
        ]
        return files

    def get_abs_path(self, file_path: str) -> str:
        """获取绝对路径 (通常用于传给第三方库)"""
        return str(self._resolve(file_path))

    # ==========================
    # 清理操作 (Clean)
    # ==========================
    def delete(self, file_path: str):
        """删除文件或文件夹"""
        target = self._resolve(file_path)
        if not target.exists():
            return

        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)

    # ==========================
    # 网络操作 (Network)
    # ==========================
    async def download_file(self, file_path: str, url: str) -> str:
        """[异步] 下载文件到指定路径"""
        target = self._resolve(file_path)
        self._ensure_parent(target)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Download failed: HTTP {response.status} | URL: {url}")

                # 使用 aiofiles 异步写入硬盘
                async with aiofiles.open(target, mode="wb") as f:
                    # 每次读取 8KB，避免大文件撑爆内存
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)

        return str(target)