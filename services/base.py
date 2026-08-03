"""
HTTP API 服务基础设施

抽象出两层可复用能力，供具体的第三方服务封装（如 Meshy）继承 / 组合：

- :class:`HttpApiClient`：统一鉴权头、错误日志、异常语义与 SSE 解析；
- :class:`TaskEndpoint`：「提交任务 -> 查询 -> 监听进度 -> 删除 / 列表」这一
  异步任务型 REST 端点的通用操作集。
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Mapping, Optional

import requests

from utils import logger

#: 任务的终态，命中即可停止轮询 / 监听
TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED", "CANCELED"})

#: SSE 数据行前缀
_SSE_DATA_PREFIX = b"data:"


class ApiError(RuntimeError):
    """API 调用失败。"""


@dataclass(frozen=True)
class Pagination:
    """列表接口的分页默认值。"""
    default_page_size: int = 10
    max_page_size: int = 50
    default_sort_by: str = "-created_at"


class HttpApiClient:
    """
    带统一错误处理与日志的 HTTP 客户端。

    所有请求共享同一份请求头（鉴权信息），并在失败时输出可定位的日志后原样抛出，
    调用方无需重复编写 try/except 样板。
    """

    def __init__(self, headers: Mapping[str, str], timeout: Optional[float] = None):
        """
        :param headers: 每个请求都会携带的请求头（通常含 Authorization）。
        :param timeout: 单次请求超时（秒），None 表示不设置。
        """
        self._headers = dict(headers)
        self._timeout = timeout

    # ==================== 内部 ====================

    def _request_kwargs(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """组装 requests 的关键字参数。"""
        kwargs: Dict[str, Any] = {"headers": self._headers, **extra}
        if self._timeout is not None:
            kwargs.setdefault("timeout", self._timeout)
        return kwargs

    @staticmethod
    def _describe_error(error: requests.exceptions.RequestException) -> str:
        """从异常中提取服务端返回的错误详情。"""
        response = getattr(error, "response", None)
        # 注意：Response 对 4xx/5xx 的布尔值为 False，必须显式与 None 比较
        return response.text if response is not None else "No response"

    def _call(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """
        执行请求并校验状态码。

        通过 ``getattr(requests, method)`` 而非 ``requests.request`` 分发，
        以便测试对 ``requests.post`` / ``requests.get`` 的打桩生效。
        """
        caller = getattr(requests, method)
        try:
            response = caller(url, **self._request_kwargs(kwargs))
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP {method.upper()} {url} 失败: {e}\nDetails: {self._describe_error(e)}")
            raise

    # ==================== 对外 ====================

    def get_json(self, url: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        """GET 请求并返回解析后的 JSON。"""
        extra = {"params": dict(params)} if params else {}
        return self._call("get", url, **extra).json()

    def post_json(self, url: str, payload: Mapping[str, Any]) -> Any:
        """POST JSON 请求并返回解析后的 JSON。"""
        return self._call("post", url, json=dict(payload)).json()

    def delete(self, url: str) -> bool:
        """DELETE 请求，成功返回 True（失败会抛出异常）。"""
        self._call("delete", url)
        return True

    def stream_sse(self, url: str) -> Generator[Dict[str, Any], None, None]:
        """
        以 SSE 方式流式读取事件；命中终态或连接结束后停止。

        连接异常不会抛出，而是产出一条 ``CONNECTION_ERROR`` 事件，
        便于调用方在同一个循环里处理。
        """
        logger.info(f"开始监听流: {url}")
        try:
            with requests.get(url, **self._request_kwargs({"stream": True})) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith(_SSE_DATA_PREFIX):
                        continue
                    try:
                        data = json.loads(line.decode("utf-8")[len(_SSE_DATA_PREFIX):])
                    except json.JSONDecodeError:
                        continue
                    yield data
                    if data.get("status") in TERMINAL_STATUSES:
                        break
        except Exception as e:
            logger.error(f"监听流失败 {url}: {e}")
            yield {"status": "CONNECTION_ERROR", "progress": 0, "error": str(e)}


class TaskEndpoint:
    """
    异步任务型 REST 端点的通用操作集。

    约定的 URL 形状::

        POST   {base_url}                    创建任务，返回体含 result=<task_id>
        GET    {base_url}/{task_id}          查询任务
        DELETE {base_url}/{task_id}          删除任务
        GET    {base_url}?page_num=...       列出任务
        GET    {base_url}/{task_id}/stream   SSE 进度流
    """

    def __init__(self, client: HttpApiClient, base_url: str, pagination: Optional[Pagination] = None):
        self._client = client
        self.base_url = base_url
        self._pagination = pagination or Pagination()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self.base_url!r})"

    def _task_url(self, task_id: str, suffix: str = "") -> str:
        return f"{self.base_url}/{task_id}{suffix}"

    def create(self, payload: Mapping[str, Any]) -> str:
        """提交创建任务，返回任务 ID。"""
        body = self._client.post_json(self.base_url, payload)
        try:
            return body["result"]
        except (TypeError, KeyError) as e:
            raise ApiError(f"创建任务响应缺少 result 字段: {body!r}") from e

    def get(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果。"""
        return self._client.get_json(self._task_url(task_id))

    def delete(self, task_id: str) -> bool:
        """删除任务。"""
        return self._client.delete(self._task_url(task_id))

    def list(
        self,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
        sort_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """列出任务，未指定的参数使用分页默认值。"""
        pagination = self._pagination
        params = {
            "page_num": page_num or 1,
            "page_size": min(page_size or pagination.default_page_size, pagination.max_page_size),
            "sort_by": sort_by or pagination.default_sort_by,
        }
        return self._client.get_json(self.base_url, params=params)

    def listen(self, task_id: str) -> Generator[Dict[str, Any], None, None]:
        """通过 SSE 流式监听任务进度。"""
        return self._client.stream_sse(self._task_url(task_id, "/stream"))
