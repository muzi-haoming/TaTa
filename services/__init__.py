"""
外部服务封装模块

``base`` 提供通用的 HTTP / 异步任务端点能力，具体服务只描述自己的 API 形状。
"""
from .base import ApiError, HttpApiClient, Pagination, TaskEndpoint, TERMINAL_STATUSES
from .meshy_service import MeshyService, meshy_service

__all__ = [
    "HttpApiClient",
    "TaskEndpoint",
    "Pagination",
    "ApiError",
    "TERMINAL_STATUSES",
    "MeshyService",
    "meshy_service",
]
