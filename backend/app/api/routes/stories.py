from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_admin_token
from app.db.session import get_async_session
from app.models.story import Story
from app.schemas.story import StoryCreate, StoryFull, StoryLight, StoryNearParams
from app.services.embeddings import build_embedding_document, embed_text
from app.services.story_geo import story_to_full_dict, story_to_light_dict

router = APIRouter()


@router.get("/near", response_model=list[StoryLight])
async def list_stories_near(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(500.0, ge=0.1, le=20000.0),
    session: AsyncSession = Depends(get_async_session),
) -> list[StoryLight]:
    _ = StoryNearParams(lat=lat, lng=lng, radius_km=radius_km)
    radius_m = radius_km * 1000.0
    origin = cast(
        func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326),
        Geography,
    )
    stmt = (
        select(Story)
        .where(func.ST_DWithin(Story.location, origin, radius_m))
        .order_by(Story.id)
    )
    rows = (await session.scalars(stmt)).all()
    return [StoryLight.model_validate(story_to_light_dict(s)) for s in rows]


@router.get("", response_model=list[StoryLight])
async def list_stories(
    tag: Optional[str] = Query(None, description="Filter by tag (substring match on tags)"),
    session: AsyncSession = Depends(get_async_session),
) -> list[StoryLight]:
    stmt = select(Story).order_by(Story.country, Story.id)
    if tag and tag.strip():
        t = tag.strip()
        stmt = stmt.where(func.array_to_string(Story.tags, " ").ilike(f"%{t}%"))
    rows = (await session.scalars(stmt)).all()
    return [StoryLight.model_validate(story_to_light_dict(s)) for s in rows]


@router.get("/{story_id}", response_model=StoryFull)
async def get_story(
    story_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> StoryFull:
    story = await session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return StoryFull.model_validate(story_to_full_dict(story))


@router.post("", response_model=StoryFull, dependencies=[Depends(verify_admin_token)])
async def create_story(
    body: StoryCreate,
    session: AsyncSession = Depends(get_async_session),
) -> StoryFull:
    loc = WKTElement(f"POINT({body.lng} {body.lat})", srid=4326)
    story = Story(
        title_en=body.title_en,
        title_zh=body.title_zh,
        content_en=body.content_en,
        content_zh=body.content_zh,
        country=body.country,
        tags=body.tags,
        emoji=body.emoji,
        location=loc,
        embedding=None,
    )
    session.add(story)
    await session.flush()

    try:
        doc = build_embedding_document(
            story.title_en,
            story.title_zh,
            story.content_en,
            story.content_zh,
        )
        story.embedding = await embed_text(doc)
    except Exception:
        story.embedding = None

    await session.commit()
    await session.refresh(story)
    return StoryFull.model_validate(story_to_full_dict(story))
