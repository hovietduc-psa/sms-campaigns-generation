"""
Authentication and authorization.
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> bool:
    """
    Verify API key for authentication.

    Args:
        credentials: Bearer token credentials

    Returns:
        True if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    # Skip authentication if no API keys are configured (for development)
    if not os.getenv("API_KEY") and not os.getenv("CAMPAIGN_API_KEY"):
        return True

    # Get API key from header
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Check against allowed API keys
    allowed_keys = [
        os.getenv("API_KEY"),
        os.getenv("CAMPAIGN_API_KEY"),
        "dev-key" if settings.debug else None,
    ]
    allowed_keys = [k for k in allowed_keys if k]  # Remove None values

    if token not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True