from langchain.tools import tool
from pydantic import BaseModel, Field

from rag import RetrievalManager
from utils import get_logger

logger = get_logger(__name__)


class SearchInfoInput(BaseModel):
    query: str = Field(
        description="检索用的查询语句。直接使用用户的原始问题即可，不需要自行改写、拆分或提取关键词——检索系统内部会自动完成这些处理。"
    )


@tool(args_schema=SearchInfoInput)
async def info_search(query: str) -> list[str]:
    """说明: 检索本项目已沉淀的全部资料。

    资料库涵盖这个游戏项目中所有已经确立、记录在案的内容：
    -世界观与设定、地点与势力、角色档案、剧情与事件、
    -历史上做过的设计决策，以及先前对话中确认下来的结论。
    -内容会随项目推进持续增长。

    调用原则：
    - 任何涉及"这个项目里已经有什么"的问题，都先检索再回答
    - 在创作新内容之前先检索，确认不与既有设定冲突
    - 不确定某个信息是否已存在时，检索的成本远低于凭空编造

    不要调用：
    - 纯闲聊、问候，或询问你自身能力的问题
    - 不依赖项目资料的通用常识问题
    - 本轮对话中已经检索过、且结果足够回答的情况

    重要：一个问题只调用一次。系统内部会自动做查询改写、拆分和多路检索，
    你不需要把问题拆成多个子问题分别调用。
    若检索结果不足以回答，请如实说明缺少哪些资料，而不是反复检索。
    """
    logger.debug(f"========== 使用 info_search 工具, 输入: {query}")
    retriever = RetrievalManager()
    result = await retriever.retrieve(query)
    return result


@tool()
async def character_generation(query: str) -> list[str]:
    """说明：本工具为开启游戏角色(档案+图片+3D模型)流程的入口。

    调用原则：
    - 当用户要求生成角色时

    不要调用：
    - 与生成游戏角色无关的问题
    """
    logger.debug(f"========== 使用 character_generation 工具, 输入: {query}")
    retriever = RetrievalManager()
    result = await retriever.retrieve(query)
    return result
