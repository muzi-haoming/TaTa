"""Agent 中间件"""
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage

from utils import logger


@wrap_tool_call
def handle_tool_errors(request, handler):
    """把工具调用异常转成模型可读的 ToolMessage，避免整个 Agent 中断。"""
    try:
        return handler(request)
    except Exception as e:
        logger.warning(f"工具 {request.tool_call.get('name')} 调用失败: {e}")
        return ToolMessage(
            content=f"工具错误：请检查输入后重试。({str(e)})",
            tool_call_id=request.tool_call["id"],
        )
