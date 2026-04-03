from typing import Optional

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def verify_admin_token(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")) -> None:
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin token required",
        )
