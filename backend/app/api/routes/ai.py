from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import verify_admin_token
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse
from app.services.ai_generate import generate_myth_json

router = APIRouter()


@router.post("/generate", response_model=AIGenerateResponse, dependencies=[Depends(verify_admin_token)])
async def ai_generate(body: AIGenerateRequest) -> AIGenerateResponse:
    try:
        data = await generate_myth_json(body.country, body.theme)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI generation failed: {e!s}",
        ) from e

    return AIGenerateResponse(
        title_en=data["title_en"],
        title_zh=data["title_zh"],
        content_en=data["content_en"],
        content_zh=data["content_zh"],
        suggested_emoji=data["suggested_emoji"],
        suggested_tags=list(data["suggested_tags"]),
    )
