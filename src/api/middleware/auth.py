"""
API authentication middleware for user management.
"""

import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, date

from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import and_
from sqlalchemy import or_

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Manages API key generation and validation."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"sk-{secrets.token_urlsafe(32)}"


# Simple user class for service-to-service authentication
class ServiceUser:
    """Simple user class for service-to-service authentication."""
    def __init__(self, user_id: str):
        self.id = user_id
        self.status = "active"
        self.monthly_quota = 999999
        self.current_usage = 0


# Environment API Key verification for service-to-service communication
async def verify_env_api_key(
    request: Request
) -> None:
    """Verify environment API key from request headers."""
    settings = get_settings()

    if not settings.ENV_API_KEY_ENABLED:
        return  # Skip verification if disabled

    # Get API key from header
    api_key = request.headers.get(settings.ENV_API_KEY_HEADER)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API key required in {settings.ENV_API_KEY_HEADER} header",
            headers={"WWW-Authenticate": f"{settings.ENV_API_KEY_HEADER}"},
        )

    if api_key != settings.ENV_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": f"{settings.ENV_API_KEY_HEADER}"},
        )

    logger.debug("Environment API key verified successfully")


async def verify_env_api_key_or_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[ServiceUser]:
    """Verify environment API key OR user authentication (whichever is provided)."""
    settings = get_settings()

    if settings.ENV_API_KEY_ENABLED:
        # Check for environment API key first
        api_key = request.headers.get(settings.ENV_API_KEY_HEADER)
        if api_key and api_key == settings.ENV_API_KEY:
            logger.debug("Environment API key verified - using default service user")
            return ServiceUser('sms-app')

    # Fall back to user authentication (simplified for now)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required either in Bearer token or X-API-Key header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # For now, create a user from the Bearer token
    # In production, this should validate against a database
    return ServiceUser(credentials.credentials[:20])  # Use first 20 chars as user ID