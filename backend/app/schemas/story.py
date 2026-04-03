from pydantic import BaseModel, Field, field_validator


class StoryLight(BaseModel):
    id: int
    title_en: str
    title_zh: str
    lat: float
    lng: float
    country: str
    emoji: str
    tags: list[str]

    model_config = {"from_attributes": True}


class StoryFull(BaseModel):
    id: int
    title_en: str
    title_zh: str
    content_en: str
    content_zh: str
    lat: float
    lng: float
    country: str
    emoji: str
    tags: list[str]

    model_config = {"from_attributes": True}


class StoryCreate(BaseModel):
    title_en: str = Field(..., min_length=1, max_length=512)
    title_zh: str = Field(..., min_length=1, max_length=512)
    content_en: str = Field(..., min_length=1)
    content_zh: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1, max_length=128)
    tags: list[str] = Field(default_factory=list)
    emoji: str = Field(default="📖", max_length=16)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        return [t.strip() for t in v if t and t.strip()]


class StoryNearParams(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(default=500.0, ge=0.1, le=20000.0)
