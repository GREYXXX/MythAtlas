from fastapi import APIRouter

from app.api.routes import ai, health, search, stats, stories

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stories.router, prefix="/stories", tags=["stories"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
