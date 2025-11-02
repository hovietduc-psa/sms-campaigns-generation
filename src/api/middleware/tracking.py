"""
Request tracking middleware.

This module provides middleware for tracking API requests, including
correlation IDs, request logging, and performance monitoring.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger

logger = get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking API requests with correlation IDs and performance metrics.
    """

    def __init__(self, app):
        """Initialize tracking middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracking."""
        start_time = time.time()

        # Generate or extract correlation ID
        correlation_id = self._get_or_generate_correlation_id(request)

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Log request start
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": str(request.url.query),
                "client_host": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "content_type": request.headers.get("content-type", "unknown"),
            }
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed with exception",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise

        # Calculate metrics
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-Duration-Ms"] = str(round(duration_ms, 2))

        # Log request completion
        logger.info(
            "Request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "response_size": len(response.body) if hasattr(response, 'body') else 0,
            }
        )

        # Log slow requests
        if duration_ms > 5000:  # 5 seconds
            logger.warning(
                "Slow request detected",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "duration_ms": round(duration_ms, 2),
                    "status_code": response.status_code,
                }
            )

        # Log error responses
        if response.status_code >= 400:
            logger.warning(
                "Request returned error status",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )

        return response

    def _get_or_generate_correlation_id(self, request: Request) -> str:
        """Get correlation ID from request or generate new one."""
        # Check for existing correlation ID in headers
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            # Check for correlation ID in query parameters
            correlation_id = request.query_params.get("correlation_id")

        if not correlation_id:
            # Generate new correlation ID
            correlation_id = str(uuid.uuid4())

        return correlation_id


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    """

    def __init__(self, app):
        """Initialize security headers middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security headers."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Remove potentially sensitive headers
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.

    Note: In production, you would want to use a more sophisticated
    rate limiting solution with Redis or similar.
    """

    def __init__(self, app, max_requests: int = 100, time_window: int = 60):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI app
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}  # Simple in-memory store for demo

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old entries
        self._cleanup_old_requests(current_time)

        # Check rate limit
        if client_ip in self.requests:
            request_count = len(self.requests[client_ip])
            if request_count >= self.max_requests:
                return Response(
                    content='{"error": "Rate limit exceeded"}',
                    status_code=429,
                    headers={"Retry-After": str(self.time_window)}
                )

        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)

        # Process request
        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Try to get IP from various headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, current_time: float) -> None:
        """Clean up old request records."""
        cutoff_time = current_time - self.time_window

        for ip in list(self.requests.keys()):
            # Remove old requests for this IP
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if req_time > cutoff_time
            ]

            # Remove empty entries
            if not self.requests[ip]:
                del self.requests[ip]