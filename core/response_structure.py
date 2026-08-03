"""
大模型结构化输出定义

这些模型会通过 ``with_structured_output`` 交给大模型，字段 ``description``
即是给模型看的说明，修改时等同于修改提示词，请谨慎。
"""
from pydantic import BaseModel, Field


class ReviewResponseStructure(BaseModel):
    """
    「通过 / 不通过 + 反馈」型结果的公共基类。

    工作流里的自动评估、人工审核、保存结果都遵循这一形状，
    统一后可以被 :class:`workflows.base.EvaluatorSpec` 之类的通用节点直接消费。
    """
    is_ok: bool = Field(description="是否通过")
    feedback: str = Field(description="反馈信息")


class NPCGenerationResponseStructure(BaseModel):
    """NPC 角色档案"""
    name: str = Field(description="姓名")
    race: str = Field(description="种族")
    personality: str = Field(description="性格特征")
    background: str = Field(description="背景故事(80-100字)")
    opening_line: str = Field(description="见面第一句台词")
    appearance: str = Field(description="外观描述(80-100字)")


class EvaluatorResponseStructure(ReviewResponseStructure):
    """评估结果"""
    is_ok: bool = Field(description="是否通过")
    feedback: str = Field(description="符合标准的话为None/不符合标准的话需要具体的feedback")


class SavingResponseStructure(ReviewResponseStructure):
    """保存结果"""
    is_ok: bool = Field(description="是否保存")
    feedback: str = Field(description="保存成功的话返回保存的路径/保存失败的话返回None")


class ImageResponseStructure(BaseModel):
    """图片结果"""
    image_base64: str = Field(description="图片base64")


class ImageGeneratePromptResponseStructure(BaseModel):
    """图片生成提示词"""
    prompt: str = Field(description="提示词")
