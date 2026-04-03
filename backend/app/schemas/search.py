from pydantic import BaseModel


class SearchResult(BaseModel):
    id: int
    title_en: str
    title_zh: str
    country: str
    emoji: str
    score: float
    method: str
