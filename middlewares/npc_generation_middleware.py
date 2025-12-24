from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage


@wrap_tool_call
def handle_tool_errors(request, handler):
    """使用自定义消息处理出现错误的工具调用"""
    try:
        return handler(request)
    except Exception as e:
        # Return a custom error message to the model
        return ToolMessage(
            content=f"工具错误：请检查输入后重试。({str(e)})",
            tool_call_id=request.tool_call["id"]
        )