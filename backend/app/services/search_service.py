from sqlalchemy import Select, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.story import Story
from app.services.embeddings import embed_text


async def semantic_search(session: AsyncSession, q: str, limit: int = 20) -> list[dict]:
    settings = get_settings()
    q_clean = q.strip()
    if not q_clean:
        return []

    n_vec = await session.scalar(
        select(func.count()).select_from(Story).where(Story.embedding.is_not(None))
    )
    use_vector = bool(settings.openai_api_key and n_vec and int(n_vec) > 0)

    if use_vector:
        try:
            vec = await embed_text(q_clean)
        except Exception:
            vec = None
        if vec is not None:
            dist_col = Story.embedding.cosine_distance(vec)
            score_expr = (literal(1) - dist_col).label("score")
            stmt: Select = (
                select(Story, score_expr)
                .where(Story.embedding.is_not(None))
                .order_by(dist_col)
                .limit(limit)
            )
            rows = (await session.execute(stmt)).all()
            if rows:
                out: list[dict] = []
                for story, score in rows:
                    out.append(
                        {
                            "id": story.id,
                            "title_en": story.title_en,
                            "title_zh": story.title_zh,
                            "country": story.country,
                            "emoji": story.emoji,
                            "score": float(max(0.0, min(1.0, score or 0.0))),
                            "method": "vector",
                        }
                    )
                return out

    # Full-text (English-friendly) when vector path unavailable
    ts = func.plainto_tsquery("simple", q_clean)
    vec_concat = func.to_tsvector(
        "simple",
        func.concat_ws(
            " ",
            Story.title_en,
            Story.title_zh,
            Story.content_en,
            Story.content_zh,
        ),
    )
    rank = func.ts_rank(vec_concat, ts)
    stmt_fts: Select = (
        select(Story, rank.label("score"))
        .where(vec_concat.op("@@")(ts))
        .order_by(rank.desc())
        .limit(limit)
    )
    rows_fts = (await session.execute(stmt_fts)).all()
    if rows_fts:
        return [
            {
                "id": s.id,
                "title_en": s.title_en,
                "title_zh": s.title_zh,
                "country": s.country,
                "emoji": s.emoji,
                "score": float(max(0.0, min(1.0, (sc or 0.0) * 2))),
                "method": "fts",
            }
            for s, sc in rows_fts
        ]

    like = f"%{q_clean}%"
    stmt_like = (
        select(Story)
        .where(
            or_(
                Story.title_en.ilike(like),
                Story.title_zh.ilike(like),
                Story.content_en.ilike(like),
                Story.content_zh.ilike(like),
            )
        )
        .limit(limit)
    )
    stories = (await session.scalars(stmt_like)).all()
    return [
        {
            "id": s.id,
            "title_en": s.title_en,
            "title_zh": s.title_zh,
            "country": s.country,
            "emoji": s.emoji,
            "score": 0.6,
            "method": "ilike",
        }
        for s in stories
    ]
