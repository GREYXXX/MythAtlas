from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models.story import Story
from app.services.story_geo import story_to_light_dict

router = APIRouter()


@router.get("/countries")
async def country_stats(session: AsyncSession = Depends(get_async_session)) -> dict:
    stmt = select(Story).order_by(Story.country, Story.id)
    stories = (await session.scalars(stmt)).all()
    by_country: dict[str, list] = defaultdict(list)
    for s in stories:
        by_country[s.country].append(story_to_light_dict(s))
    countries = []
    for country, items in sorted(by_country.items(), key=lambda x: (-len(x[1]), x[0])):
        countries.append(
            {
                "country": country,
                "count": len(items),
                "stories": items,
            }
        )
    total = len(stories)
    return {
        "total_stories": total,
        "country_count": len(countries),
        "countries": countries,
    }


@router.get("/summary")
async def summary(session: AsyncSession = Depends(get_async_session)) -> dict:
    total = await session.scalar(select(func.count()).select_from(Story))
    cc = await session.scalar(select(func.count(func.distinct(Story.country))))
    return {
        "total_stories": int(total or 0),
        "countries": int(cc or 0),
    }
