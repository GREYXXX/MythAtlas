"""Import stories from a JSON file (Claude / external generator).

Supports:
  - { "stories": [ {...}, ... ], "meta": {...} }
  - [ {...}, ... ]

Each item may use summary_en/summary_zh (mapped to content) or content_en/content_zh.
Optional: type, wiki_en, wiki_zh (appended as a short references footer).

Usage (from repo root, with venv + DATABASE_URL set):
  cd backend && python -m scripts.import_json_stories ../stories/east_asia_stories.json

Options:
  --dry-run     Parse and validate only, no DB writes
  --no-skip     Insert even when title_en already exists
  --no-embed    Do not compute OpenAI embeddings after insert
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.story import Story
from app.services.embeddings import build_embedding_document, embed_text

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_stories_payload(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "stories" in raw:
        s = raw["stories"]
        if not isinstance(s, list):
            raise ValueError('"stories" must be a JSON array')
        return s
    raise ValueError("JSON must be an array of stories or an object with a 'stories' array")


def _norm_tags(tags: object, extra: list[str] | None = None) -> list[str]:
    out: list[str] = []
    if isinstance(tags, list):
        for t in tags:
            if isinstance(t, str) and t.strip():
                s = t.strip()[:128]
                if s not in out:
                    out.append(s)
    if extra:
        for t in extra:
            if t and t not in out:
                out.append(t[:128])
    return out[:64]


def _footnote_en(wiki_en: str | None, wiki_zh: str | None) -> str:
    parts: list[str] = []
    if wiki_en:
        parts.append(f"References: {wiki_en}")
    if wiki_zh:
        parts.append(wiki_zh)
    if not parts:
        return ""
    return "\n\n" + " · ".join(parts)


def _footnote_zh(wiki_en: str | None, wiki_zh: str | None) -> str:
    parts: list[str] = []
    if wiki_zh:
        parts.append(f"参考：{wiki_zh}")
    if wiki_en:
        parts.append(wiki_en)
    if not parts:
        return ""
    return "\n\n" + " · ".join(parts)


def row_to_story_fields(row: dict) -> dict:
    title_en = str(row["title_en"]).strip()[:512]
    title_zh = str(row["title_zh"]).strip()[:512]
    if not title_en or not title_zh:
        raise ValueError("title_en and title_zh are required")

    body_en = row.get("content_en") or row.get("summary_en")
    body_zh = row.get("content_zh") or row.get("summary_zh")
    if not body_en or not body_zh:
        raise ValueError(f"Missing content for {title_en!r}: need content_en/summary_en and content_zh/summary_zh")
    content_en = str(body_en).strip()
    content_zh = str(body_zh).strip()
    if not content_en or not content_zh:
        raise ValueError(f"Empty content for {title_en!r}")

    wiki_en = row.get("wiki_en")
    wiki_zh = row.get("wiki_zh")
    if isinstance(wiki_en, str) and wiki_en.strip():
        content_en = content_en + _footnote_en(wiki_en.strip(), wiki_zh.strip() if isinstance(wiki_zh, str) else None)
    elif isinstance(wiki_zh, str) and wiki_zh.strip():
        content_en = content_en + _footnote_en(None, wiki_zh.strip())

    if isinstance(wiki_zh, str) and wiki_zh.strip():
        content_zh = content_zh + _footnote_zh(
            wiki_en.strip() if isinstance(wiki_en, str) else None,
            wiki_zh.strip(),
        )
    elif isinstance(wiki_en, str) and wiki_en.strip():
        content_zh = content_zh + _footnote_zh(wiki_en.strip(), None)

    country = str(row["country"]).strip()[:128]
    if not country:
        raise ValueError(f"country required for {title_en!r}")

    lat = float(row["lat"])
    lng = float(row["lng"])
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError(f"Invalid lat/lng for {title_en!r}")

    emoji = str(row.get("emoji") or "📖").strip()[:16] or "📖"
    typ = row.get("type")
    extra_tags: list[str] = []
    if isinstance(typ, str) and typ.strip():
        extra_tags.append(typ.strip().lower().replace(" ", "-")[:128])

    tags = _norm_tags(row.get("tags"), extra_tags)

    return {
        "title_en": title_en,
        "title_zh": title_zh,
        "content_en": content_en,
        "content_zh": content_zh,
        "country": country,
        "tags": tags,
        "emoji": emoji,
        "lat": lat,
        "lng": lng,
    }


async def _title_exists(session: AsyncSession, title_en: str) -> bool:
    n = await session.scalar(select(func.count()).select_from(Story).where(Story.title_en == title_en))
    return bool(n and int(n) > 0)


async def import_stories(
    path: Path,
    *,
    dry_run: bool,
    skip_existing: bool,
    do_embed: bool,
) -> tuple[int, int, int, int]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    rows = _load_stories_payload(data)

    parsed: list[dict] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Item {i} is not an object")
        parsed.append(row_to_story_fields(row))

    if dry_run:
        print(f"Dry run: {len(parsed)} stories valid (no DB writes).")
        return len(parsed), 0, 0, 0

    inserted = 0
    skipped = 0
    inserted_titles: list[str] = []
    async with async_session_factory() as session:
        for fields in parsed:
            if skip_existing and await _title_exists(session, fields["title_en"]):
                skipped += 1
                continue
            loc = WKTElement(f"POINT({fields['lng']} {fields['lat']})", srid=4326)
            session.add(
                Story(
                    title_en=fields["title_en"],
                    title_zh=fields["title_zh"],
                    content_en=fields["content_en"],
                    content_zh=fields["content_zh"],
                    country=fields["country"],
                    tags=fields["tags"],
                    emoji=fields["emoji"],
                    location=loc,
                    embedding=None,
                )
            )
            inserted_titles.append(fields["title_en"])
            inserted += 1
        await session.commit()

    embedded = 0
    if do_embed and inserted_titles and get_settings().openai_api_key:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Story).where(
                    Story.title_en.in_(inserted_titles),
                    Story.embedding.is_(None),
                )
            )
            stories = result.scalars().all()
            for s in stories:
                doc = build_embedding_document(s.title_en, s.title_zh, s.content_en, s.content_zh)
                try:
                    s.embedding = await embed_text(doc)
                    embedded += 1
                except Exception:
                    continue
            await session.commit()
    elif do_embed and inserted_titles and not get_settings().openai_api_key:
        print("OPENAI_API_KEY not set; skipping embeddings.")

    return len(parsed), inserted, skipped, embedded


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MythAtlas stories from JSON.")
    parser.add_argument(
        "json_path",
        nargs="?",
        default=str(REPO_ROOT / "stories" / "east_asia_stories.json"),
        help="Path to JSON file (default: <repo>/stories/east_asia_stories.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate only")
    parser.add_argument("--no-skip", action="store_true", help="Insert duplicates (same title_en)")
    parser.add_argument("--no-embed", action="store_true", help="Skip embedding pass")
    args = parser.parse_args()

    path = Path(args.json_path).expanduser().resolve()
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    total, inserted, skipped, embedded = asyncio.run(
        import_stories(
            path,
            dry_run=args.dry_run,
            skip_existing=not args.no_skip,
            do_embed=not args.no_embed,
        )
    )
    if not args.dry_run:
        msg = f"Parsed: {total} | Inserted: {inserted} | Skipped (existing title_en): {skipped}"
        if embedded:
            msg += f" | Embeddings updated: {embedded}"
        print(msg)


if __name__ == "__main__":
    main()
