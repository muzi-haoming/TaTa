from pydantic import BaseModel, Field


class NPCGenerationResponseStructure(BaseModel):
    name: str = Field(description="姓名")
    race: str = Field(description="种族")
    personality: str = Field(description="性格特征")
    background: str = Field(description="背景故事(80-100字)")
    opening_line: str = Field(description="见面第一句台词")
    appearance: str = Field(description="外观描述(80-100字)")


class EvaluatorResponseStructure(BaseModel):
    is_ok: bool = Field(description="是否通过")
    feedback: str = Field(description="符合标准的话为None/不符合标准的话需要具体的feedback")


class SavingResponseStructure(BaseModel):
    is_ok: bool = Field(description="是否保存")
    feedback: str = Field(description="保存成功的话返回保存的路径/保存失败的话返回None")


class ImageResponseStructure(BaseModel):
    image_base64: str = Field(description="图片base64")


class ImageGeneratePromptResponseStructure(BaseModel):
    prompt: str = Field(description="提示词")


class PlanResponseStructure(BaseModel):
    plan_list: list[str] = Field(description="方案的步骤列表")