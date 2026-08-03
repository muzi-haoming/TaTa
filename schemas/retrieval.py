from pydantic import BaseModel, Field

class RewrittenQueries(BaseModel):
    queries: list[str] = Field(description="改写后的多个查询版本")

class SplitedQueries(BaseModel):
    queries: list[str] = Field(description="拆分后的多个查询版本")