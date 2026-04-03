from openai import AsyncOpenAI

from app.core.config import get_settings


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    r = await client.embeddings.create(
        model=settings.embedding_model,
        input=text[:8000],
        dimensions=settings.embedding_dimensions,
    )
    return list(r.data[0].embedding)


def build_embedding_document(title_en: str, title_zh: str, content_en: str, content_zh: str) -> str:
    return f"{title_en}\n{title_zh}\n{content_en}\n{content_zh}"
