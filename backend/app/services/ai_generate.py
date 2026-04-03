import json
import re

from openai import AsyncOpenAI

from app.core.config import get_settings


_SYSTEM = """You are a folklore scholar. Generate a concise myth or folktale (fiction in traditional style) 
inspired by the given country and theme. Respond with ONLY valid JSON matching this schema:
{
  "title_en": string,
  "title_zh": string,
  "content_en": string (2-4 short paragraphs),
  "content_zh": string (same ideas, natural Chinese),
  "suggested_emoji": string (single emoji),
  "suggested_tags": string[] (3-6 lowercase English tags)
}
No markdown, no code fences."""


async def generate_myth_json(country: str, theme: str) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    user = f'Country / region: "{country}"\nTheme: "{theme}"'
    r = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.85,
        max_tokens=1800,
    )
    raw = (r.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    required = {
        "title_en",
        "title_zh",
        "content_en",
        "content_zh",
        "suggested_emoji",
        "suggested_tags",
    }
    if not required.issubset(data.keys()):
        raise ValueError("AI response missing required fields")
    return data
