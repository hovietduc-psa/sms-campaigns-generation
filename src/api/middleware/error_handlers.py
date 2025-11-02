"""
Error handlers for FastAPI application.

This module provides comprehensive error handling for all types of errors
that can occur in the campaign generation service.
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging import get_logger
from src.utils.constants import ERROR_RESPONSES
from src.services.campaign_generation.orchestrator import CampaignOrchestrator
from src.services.validation.validator import ValidationError

logger = get_logger(__name__)


class CampaignGenerationError(Exception):
    """Custom exception for campaign generation errors."""

    def __init__(self, message: str, error_code: str = "GENERATION_ERROR", correlation_id: str = None):
        self.message = message
        self.error_code = error_code
        self.correlation_id = correlation_id
        super().__init__(self.message)


class FlowValidationError(Exception):
    """Custom exception for flow validation errors."""

    def __init__(self, message: str, field: str = None, correlation_id: str = None):
        self.message = message
        self.field = field
        self.correlation_id = correlation_id
        super().__init__(self.message)


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""

    def __init__(self, message: str, error_type: str = "LLM_ERROR", correlation_id: str = None):
        self.message = message
        self.error_type = error_type
        self.correlation_id = correlation_id
        super().__init__(self.message)


async def campaign_generation_exception_handler(
    request: Request, exc: CampaignGenerationError
) -> JSONResponse:
    """Handle campaign generation errors."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.error(
        f"Campaign generation error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "correlation_id": correlation_id,
            "status": "error",
            "type": "campaign_generation_error"
        }
    )


async def flow_validation_exception_handler(
    request: Request, exc: FlowValidationError
) -> JSONResponse:
    """Handle flow validation errors."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.error(
        f"Flow validation error: {exc.message}",
        extra={
            "field": exc.field,
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "FLOW_VALIDATION_ERROR",
            "message": exc.message,
            "field": exc.field,
            "correlation_id": correlation_id,
            "status": "error",
            "type": "flow_validation_error"
        }
    )


async def llm_service_exception_handler(
    request: Request, exc: LLMServiceError
) -> JSONResponse:
    """Handle LLM service errors."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.error(
        f"LLM service error: {exc.error_type} - {exc.message}",
        extra={
            "error_type": exc.error_type,
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    # Determine appropriate status code based on error type
    if exc.error_type in ["RATE_LIMIT_ERROR", "TOKEN_LIMIT_ERROR"]:
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif exc.error_type == "AUTHENTICATION_ERROR":
        status_code = status.HTTP_401_UNAUTHORIZED
    elif exc.error_type == "INVALID_REQUEST":
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.error_type,
            "message": exc.message,
            "correlation_id": correlation_id,
            "status": "error",
            "type": "llm_service_error"
        }
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": ERROR_RESPONSES.get(exc.status_code, "HTTP_ERROR"),
            "message": exc.detail,
            "correlation_id": correlation_id,
            "status": "error",
            "type": "http_error"
        }
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.warning(
        f"Request validation error: {exc.errors()}",
        extra={
            "validation_errors": exc.errors(),
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    # Format validation errors for better readability
    formatted_errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        formatted_errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "REQUEST_VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": formatted_errors,
            "correlation_id": correlation_id,
            "status": "error",
            "type": "validation_error"
        }
    )


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.warning(
        f"Pydantic validation error: {exc}",
        extra={
            "validation_errors": exc.errors(),
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    # Extract validation errors
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "SCHEMA_VALIDATION_ERROR",
            "message": "Invalid data format",
            "details": formatted_errors,
            "correlation_id": correlation_id,
            "status": "error",
            "type": "schema_validation_error"
        }
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle general exceptions."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
            "traceback": traceback.format_exc(),
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "correlation_id": correlation_id,
            "status": "error",
            "type": "internal_error"
        }
    )


async def timeout_exception_handler(request: Request, exc: TimeoutError) -> JSONResponse:
    """Handle timeout exceptions."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    logger.error(
        f"Request timeout: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_id": getattr(request.state, 'user_id', 'anonymous'),
        }
    )

    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content={
            "error": "REQUEST_TIMEOUT",
            "message": "Request processing timed out",
            "correlation_id": correlation_id,
            "status": "error",
            "type": "timeout_error"
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup all exception handlers for the application."""
    # Custom exceptions
    app.add_exception_handler(
        CampaignGenerationError,
        campaign_generation_exception_handler
    )
    app.add_exception_handler(
        FlowValidationError,
        flow_validation_exception_handler
    )
    app.add_exception_handler(
        LLMServiceError,
        llm_service_exception_handler
    )

    # Pydantic validation errors
    app.add_exception_handler(
        ValidationError,
        pydantic_validation_exception_handler
    )

    # Framework exceptions
    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler
    )
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler
    )

    # Timeout exceptions
    app.add_exception_handler(
        TimeoutError,
        timeout_exception_handler
    )

    # Catch-all for unexpected exceptions
    app.add_exception_handler(
        Exception,
        general_exception_handler
    )

    logger.info("Exception handlers configured")