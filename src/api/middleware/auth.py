"""
API authentication middleware for user management.
"""

import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, date

from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and, or_

from src.core.database import get_db_session
from src.core.logging import get_logger
from src.models.database import User, UsageLog

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Manages API key generation and validation."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"sk-{secrets.token_urlsafe(32)}"


class UserAuthentication:
    """Handles user authentication and authorization."""

    def __init__(self):
        self._user_cache = {}  # Simple cache for user lookups
        self._cache_ttl = 300  # 5 minutes

    async def authenticate_user(
        self,
        api_key: str,
        db: AsyncSession
    ) -> User:
        """Authenticate user by API key."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check cache first
        cache_key = f"user:{api_key}"
        if cache_key in self._user_cache:
            cached_user, cached_time = self._user_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                if cached_user.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account is not active"
                    )
                return cached_user

        # Query database
        stmt = select(User).where(
            and_(
                User.api_key == api_key,
                User.status == "active"
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check monthly quota
        await self._check_monthly_quota(user, db)

        # Cache the user
        self._user_cache[cache_key] = (user, time.time())

        return user

    async def _check_monthly_quota(self, user: User, db: AsyncSession) -> None:
        """Check if user has exceeded their monthly quota."""
        today = date.today()

        # Reset usage if new billing cycle
        if today.day == 1 and user.billing_cycle_start != today:
            user.current_usage = 0
            user.billing_cycle_start = today
            await db.commit()

        # Check quota
        if user.current_usage >= user.monthly_quota:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "QUOTA_EXCEEDED",
                    "message": f"Monthly quota of {user.monthly_quota} requests exceeded",
                    "quota": user.monthly_quota,
                    "used": user.current_usage,
                    "reset_date": self._get_next_billing_date(user.billing_cycle_start).isoformat()
                }
            )

    def _get_next_billing_date(self, billing_start: date) -> date:
        """Get the next billing date."""
        if billing_start.month == 12:
            return date(billing_start.year + 1, 1, 1)
        else:
            return date(billing_start.year, billing_start.month + 1, 1)


class UsageTracker:
    """Tracks API usage for billing and analytics."""

    @staticmethod
    async def log_usage(
        user_id: str,
        request_type: str,
        endpoint: str,
        status_code: int,
        response_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        request_details: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> None:
        """Log API usage for tracking and billing."""
        if not db:
            return

        try:
            usage_log = UsageLog(
                user_id=user_id,
                request_type=request_type,
                endpoint=endpoint,
                status_code=status_code,
                response_time_ms=response_time_ms,
                tokens_used=tokens_used,
                cost=cost,
                request_details=request_details
            )
            db.add(usage_log)

            # Update user's current usage
            user = await db.get(User, user_id)
            if user:
                user.current_usage += 1
                user.last_request_at = datetime.utcnow()

            await db.commit()
            logger.debug(f"Usage logged for user {user_id}: {request_type}")

        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            await db.rollback()

    @staticmethod
    async def get_user_usage_stats(
        user_id: str,
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(UsageLog).where(
            and_(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= start_date
            )
        )
        result = await db.execute(stmt)
        logs = list(result.scalars().all())

        total_requests = len(logs)
        successful_requests = len([log for log in logs if 200 <= log.status_code < 400])
        failed_requests = total_requests - successful_requests

        total_tokens = sum([log.tokens_used or 0 for log in logs])
        total_cost = sum([log.cost or 0 for log in logs])

        avg_response_time = 0
        if logs:
            response_times = [log.response_time_ms for log in logs if log.response_time_ms]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        return {
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "total_tokens_used": total_tokens,
            "total_cost": total_cost,
            "average_response_time_ms": avg_response_time
        }


# Global instances
auth_manager = UserAuthentication()
usage_tracker = UsageTracker()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Dependency to get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await auth_manager.authenticate_user(credentials.credentials, db)


# Optional authentication (doesn't raise error if no API key)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """Dependency to get optional user (for public endpoints with enhanced features for authenticated users)."""
    if not credentials:
        return None

    try:
        return await auth_manager.authenticate_user(credentials.credentials, db)
    except HTTPException:
        return None