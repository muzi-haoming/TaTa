# """
# 文件操作工具

# 以沙箱根目录为单位封装读写、校验、清理与下载能力。
# """
# import base64
# import json
# import shutil
# from pathlib import Path
# from typing import Any, Dict, List, Union

# import aiofiles
# import aiohttp
# import yaml

# from .logger import logger

# #: 流式下载的默认分块大小（字节），避免大文件一次性读入内存
# DEFAULT_CHUNK_SIZE = 8192

# #: 需要归一化的图片扩展名
# _MIME_SUFFIX_ALIASES = {"jpg": "jpeg"}


# class FileUtil:
#     """
#     文件操作工具类。

#     特点：
#     1. 安全沙箱：所有操作限制在 ``root_dir`` 下，防止越权访问系统敏感文件；
#     2. 自动容错：写入时自动创建父目录；
#     3. 多格式支持：text / json / yaml / bytes / base64 图片；
#     4. 网络能力：异步流式下载。
#     """

#     def __init__(self, root_dir: Union[str, Path]):
#         """
#         :param root_dir: 所有文件操作的根目录（沙箱目录），不存在时自动创建。
#         """
#         self.root = Path(root_dir).resolve()
#         self.root.mkdir(parents=True, exist_ok=True)
#         logger.debug(f"FileUtil 沙箱根目录: {self.root}")

#     def __repr__(self) -> str:
#         return f"{type(self).__name__}(root={str(self.root)!r})"

#     # ==========================
#     # 内部方法 (Internal)
#     # ==========================
#     def _resolve(self, file_path: Union[str, Path]) -> Path:
#         """
#         解析相对路径并做越界检查（防止 ``../../etc/passwd`` 之类的路径穿越）。

#         :raises ValueError: 解析结果落在沙箱之外。
#         """
#         target = (self.root / file_path).resolve()
#         if target != self.root and not target.is_relative_to(self.root):
#             raise ValueError(f"Security Error: Access denied to {file_path} (Outside workspace)")
#         return target

#     def _prepare_target(self, file_path: Union[str, Path]) -> Path:
#         """解析写入路径，并确保父目录存在。"""
#         target = self._resolve(file_path)
#         target.parent.mkdir(parents=True, exist_ok=True)
#         return target

#     def _require_existing(self, file_path: Union[str, Path], what: str = "File") -> Path:
#         """解析读取路径，并确保目标存在。"""
#         target = self._resolve(file_path)
#         if not target.exists():
#             raise FileNotFoundError(f"{what} not found: {file_path}")
#         return target

#     @staticmethod
#     def _strip_base64_header(base64_string: str) -> str:
#         """去掉 ``data:image/png;base64,`` 这类前缀，只保留纯 base64 载荷。"""
#         return base64_string.split(",", 1)[1] if "," in base64_string else base64_string

#     # ==========================
#     # 写入操作 (Write)
#     # ==========================
#     def write_text(self, file_path: str, content: str, append: bool = False) -> str:
#         """写入纯文本文件；``append=True`` 时追加而非覆盖。"""
#         target = self._prepare_target(file_path)
#         with target.open("a" if append else "w", encoding="utf-8") as f:
#             f.write(content)
#         return str(target)

#     def write_json(self, file_path: str, data: Union[Dict, List]) -> str:
#         """写入 JSON 文件（``ensure_ascii=False`` 保证中文可读）。"""
#         target = self._prepare_target(file_path)
#         target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
#         return str(target)

#     def write_yaml(self, file_path: str, data: Any) -> str:
#         """写入 YAML 文件。"""
#         target = self._prepare_target(file_path)
#         with target.open("w", encoding="utf-8") as f:
#             yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
#         return str(target)

#     def write_bytes(self, file_path: str, data: bytes) -> str:
#         """写入二进制文件（如图片、模型）。"""
#         target = self._prepare_target(file_path)
#         target.write_bytes(data)
#         return str(target)

#     def write_image(self, file_path: str, base64_string: str) -> str:
#         """将 Base64 字符串解码并保存为图片文件。"""
#         payload = self._strip_base64_header(base64_string)
#         try:
#             image_data = base64.b64decode(payload)
#         except Exception as e:
#             raise ValueError(f"Invalid Base64 string: {e}") from e
#         return self.write_bytes(file_path, image_data)

#     # ==========================
#     # 读取操作 (Read)
#     # ==========================
#     def read_text(self, file_path: str) -> str:
#         """读取纯文本文件。"""
#         return self._require_existing(file_path).read_text(encoding="utf-8")

#     def read_json(self, file_path: str) -> Union[Dict, List]:
#         """读取 JSON 文件。"""
#         return json.loads(self.read_text(file_path))

#     def read_yaml(self, file_path: str) -> Any:
#         """读取 YAML 文件。"""
#         with self._require_existing(file_path).open("r", encoding="utf-8") as f:
#             return yaml.safe_load(f)

#     def read_bytes(self, file_path: str) -> bytes:
#         """读取二进制文件。"""
#         return self._require_existing(file_path).read_bytes()

#     def read_image(self, file_path: str, add_header: bool = False) -> str:
#         """
#         读取图片并转换为 Base64 字符串。

#         :param add_header: 为 True 时返回带 ``data:image/<ext>;base64,`` 前缀的 Data URI。
#         """
#         target = self._require_existing(file_path, what="Image file")
#         b64_string = base64.b64encode(target.read_bytes()).decode("utf-8")
#         if not add_header:
#             return b64_string
#         suffix = target.suffix.lower().lstrip(".")
#         suffix = _MIME_SUFFIX_ALIASES.get(suffix, suffix)
#         return f"data:image/{suffix};base64,{b64_string}"

#     # ==========================
#     # 校验与查询 (Check & List)
#     # ==========================
#     def exists(self, file_path: str) -> bool:
#         """检查文件或目录是否存在（路径不安全时视为不存在）。"""
#         try:
#             return self._resolve(file_path).exists()
#         except ValueError:
#             return False

#     def list_files(self, dir_path: str = ".", pattern: str = "*", recursive: bool = False) -> List[str]:
#         """列出目录下的文件，返回相对沙箱根目录的路径。"""
#         target = self._resolve(dir_path)
#         if not target.is_dir():
#             raise NotADirectoryError(f"Path is not a directory: {dir_path}")
#         glob_func = target.rglob if recursive else target.glob
#         return [str(p.relative_to(self.root)) for p in glob_func(pattern) if p.is_file()]

#     def get_abs_path(self, file_path: str) -> str:
#         """获取绝对路径（通常用于传给第三方库）。"""
#         return str(self._resolve(file_path))

#     # ==========================
#     # 清理操作 (Clean)
#     # ==========================
#     def delete(self, file_path: str) -> None:
#         """删除文件或整个目录；目标不存在时静默返回。"""
#         target = self._resolve(file_path)
#         if not target.exists():
#             return
#         if target.is_dir():
#             shutil.rmtree(target)
#         else:
#             target.unlink()

#     # ==========================
#     # 网络操作 (Network)
#     # ==========================
#     async def download_file(self, file_path: str, url: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
#         """[异步] 流式下载文件到沙箱内的指定路径。"""
#         target = self._prepare_target(file_path)
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url) as response:
#                 if response.status != 200:
#                     raise IOError(f"Download failed: HTTP {response.status} | URL: {url}")
#                 async with aiofiles.open(target, mode="wb") as f:
#                     async for chunk in response.content.iter_chunked(chunk_size):
#                         await f.write(chunk)
#         logger.debug(f"下载完成: {url} -> {target}")
#         return str(target)
