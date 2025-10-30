"""
Campaign Generation API main application.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import time

from .core.config import get_settings
from .observability.metrics import timer_metric
from .api.v1.campaigns import router as campaigns_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Campaign Generation API...")

    # Log configuration
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"OpenAI configured: {bool(settings.openai_api_key)}")
    logger.info(f"GROQ configured: {bool(settings.groq_api_key)}")
    logger.info(f"Qdrant configured: {bool(settings.qdrant_url)}")
    logger.info(f"Cohere configured: {bool(settings.cohere_api_key)}")

    yield

    logger.info("Shutting down Campaign Generation API...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="AI-powered SMS campaign generation API",
    lifespan=lifespan,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add request timing and metrics."""
    start_time = time.time()

    try:
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time
        duration_ms = duration * 1000

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        # Record metrics
        path = request.url.path
        method = request.method

        timer_metric(
            "request_duration",
            duration_ms,
            tags={"method": method, "path": path}
        )

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Request failed after {duration:.2f}s: {e}")
        raise


# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # Static files directory may not exist in production
    pass

# Include routers
app.include_router(campaigns_router, prefix=settings.api_prefix)


# Enhanced root endpoint
@app.get("/", response_class=HTMLResponse)
async def root_html():
    """Root endpoint with user-friendly web interface."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMS Campaign Generation API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            text-align: center;
        }
        .container {
            max-width: 800px;
            padding: 2rem;
        }
        .logo { font-size: 3rem; margin-bottom: 1rem; }
        .title { font-size: 2rem; margin-bottom: 1rem; font-weight: 300; }
        .description { font-size: 1.2rem; margin-bottom: 2rem; opacity: 0.9; }
        .buttons { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
        .btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 1rem 2rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            border: 2px solid rgba(255, 255, 255, 0.3);
            backdrop-filter: blur(10px);
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        .info { margin-top: 3rem; opacity: 0.8; }
        .version { background: rgba(255, 255, 255, 0.1); padding: 0.5rem 1rem; border-radius: 25px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🚀</div>
        <h1 class="title">SMS Campaign Generation API</h1>
        <p class="description">AI-powered campaign generation for modern SMS marketing</p>

        <div class="buttons">
            <a href="/static/index.html" class="btn">🎯 Try Interactive Demo</a>
            <a href="/static/quickstart.html" class="btn">📖 Quick Start Guide</a>
            <a href="/docs" class="btn">📚 API Documentation</a>
            <a href="/redoc" class="btn">📋 ReDoc</a>
        </div>

        <div class="info">
            <div class="version">Version 1.0.0</div>
            <p>✅ Production Ready • 🤖 AI-Powered • ⚡ Fast & Reliable</p>
        </div>
    </div>
</body>
</html>"""


# API info endpoint (JSON)
@app.get("/api")
async def api_info():
    """API information in JSON format."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": "AI-powered SMS campaign generation API",
        "endpoints": {
            "campaigns": f"{settings.api_prefix}/campaigns",
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "interactive": "/static/index.html"
        },
        "models": {
            "planning": settings.openai_model,
            "content": settings.openai_mini_model
        },
        "features": {
            "campaign_generation": "AI-powered campaign creation",
            "validation": "Comprehensive campaign validation",
            "template_search": "Semantic template search",
            "quality_scoring": "A-F grading system",
            "cost_tracking": "Real-time cost calculation"
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.api_version,
        "debug": settings.debug
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )