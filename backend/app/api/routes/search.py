from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.search import SearchResult
from app.services.search_service import semantic_search

router = APIRouter()


@router.get("/search", response_model=list[SearchResult])
async def search_stories(
    q: str = Query(..., min_length=1, max_length=512),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
) -> list[SearchResult]:
    rows = await semantic_search(session, q, limit=limit)
    return [SearchResult.model_validate(r) for r in rows]
