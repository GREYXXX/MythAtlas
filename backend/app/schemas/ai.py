from pydantic import BaseModel, Field


class AIGenerateRequest(BaseModel):
    country: str = Field(..., min_length=1, max_length=128)
    theme: str = Field(..., min_length=1, max_length=256)


class AIGenerateResponse(BaseModel):
    title_en: str
    title_zh: str
    content_en: str
    content_zh: str
    suggested_emoji: str
    suggested_tags: list[str]
