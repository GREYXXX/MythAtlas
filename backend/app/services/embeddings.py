import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings


async def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for text.

    Provider priority:
      1. OpenAI  — if OPENAI_API_KEY is set in .env
      2. Ollama  — local model (nomic-embed-text by default), no API key needed

    Both providers produce 768-dimensional vectors:
      - OpenAI text-embedding-3-small with dimensions=768
      - nomic-embed-text natively outputs 768 dims
    """
    settings = get_settings()
    if settings.openai_api_key:
        return await _embed_openai(text, settings)
    return await _embed_ollama(text, settings)


async def _embed_openai(text: str, settings) -> list[float]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    r = await client.embeddings.create(
        model=settings.embedding_model,
        input=text[:8000],
        dimensions=settings.embedding_dimensions,
    )
    return list(r.data[0].embedding)


async def _embed_ollama(text: str, settings) -> list[float]:
    url = f"{settings.ollama_base_url}/api/embeddings"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            json={"model": settings.local_embedding_model, "prompt": text[:8000]},
        )
        r.raise_for_status()
        return r.json()["embedding"]


def build_embedding_document(title_en: str, title_zh: str, content_en: str, content_zh: str) -> str:
    return f"{title_en}\n{title_zh}\n{content_en}\n{content_zh}"
