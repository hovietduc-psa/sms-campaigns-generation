"""
Main FastAPI application for SMS Campaign Generation System.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import get_settings
from src.core.logging import setup_logging
from src.core.database import init_db, close_db
from src.services.database.campaign_logger import get_database_logger
from src.api.endpoints.campaigns import router as campaigns_router
from src.api.endpoints.health import router as health_router
from src.api.endpoints.database import router as database_router  # Fixed import
from src.api.middleware.error_handlers import setup_exception_handlers
from src.api.middleware.tracking import (
    RequestTrackingMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware
)
from src.api.documentation import setup_api_documentation


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    setup_logging(
        level=settings.LOG_LEVEL,
        format_type=settings.LOG_FORMAT,
        log_file=settings.LOG_FILE
    )

    # Initialize database (fault-tolerant)
    try:
        await init_db()
        print("SUCCESS: Database initialized successfully")
    except Exception as e:
        print(f"WARNING: Database initialization failed: {e}")
        print("INFO: System will continue without database logging")
        # Disable database logging if initialization fails
        db_logger = get_database_logger()
        db_logger.disable()

    # Initialize database logger health check
    db_logger = get_database_logger()
    if await db_logger.is_healthy():
        print("SUCCESS: Database logger healthy")
    else:
        print("WARNING: Database logger unhealthy, using memory fallback")
        db_logger.disable()

    yield

    # Shutdown
    try:
        # Cleanup database logger
        await db_logger.cleanup()
        await close_db()
        print("SUCCESS: Database connections closed")
    except Exception as e:
        print(f"WARNING: Database cleanup failed: {e}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Automated SMS Campaign Flow Generation using LLM technology",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Add middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )

    # Add tracking middleware (first for maximum coverage)
    app.add_middleware(RequestTrackingMiddleware)

    # Add rate limiting middleware
    if settings.ENABLE_RATE_LIMITING:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
            time_window=settings.RATE_LIMIT_TIME_WINDOW
        )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add CORS middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )

    # Add trusted host middleware
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Setup API documentation
    setup_api_documentation(app)

    # Mount static files
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    else:
        # Fallback for development
        app.mount("/static", StaticFiles(directory="static"), name="static")

    # Include routers
    app.include_router(
        campaigns_router,
        prefix=settings.API_V1_STR,
        tags=["campaigns"]
    )

    app.include_router(
        health_router,
        prefix=settings.API_V1_STR,
        tags=["health"]
    )

    app.include_router(
        database_router,
        prefix=f"{settings.API_V1_STR}/database",
        tags=["database"]
    )

    # Root health check endpoint
    @app.get("/health", include_in_schema=False)
    async def root_health_check():
        """Root health check endpoint for load balancers."""
        return {"status": "healthy", "version": settings.APP_VERSION}

    return app


# Create application instance
app = create_application()


def run_server() -> None:
    """Run the FastAPI server."""
    settings = get_settings()

    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.MAX_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    run_server()