"""
API documentation configuration and enhancements.

This module provides comprehensive API documentation including:
- Custom OpenAPI schema configuration
- Example responses and requests
- Security scheme documentation
- API metadata and descriptions
"""

from typing import Dict, Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from src.core.config import get_settings


security_scheme = {
    "type": "http",
    "scheme": "bearer",
    "bearerFormat": "JWT",
    "description": "Enter your Bearer token for authentication"
}


def custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.

    Args:
        app: FastAPI application instance

    Returns:
        Custom OpenAPI schema dictionary
    """
    settings = get_settings()

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.yourdomain.com",
                "description": "Production server"
            }
        ]
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": security_scheme
    }

    # Add global security requirements (optional)
    if not settings.DEBUG:
        openapi_schema["security"] = [{"BearerAuth": []}]

    # Add enhanced descriptions
    openapi_schema["info"]["contact"] = {
        "name": "API Support",
        "email": "support@yourdomain.com",
        "url": "https://yourdomain.com/support"
    }

    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }

    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "campaigns",
            "description": "Campaign generation and management operations"
        },
        {
            "name": "health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "validation",
            "description": "Flow validation and correction operations"
        }
    ]

    # Add example objects
    openapi_schema["components"]["examples"] = {
        "CampaignGenerationRequest": {
            "summary": "Example campaign generation request",
            "value": {
                "campaignDescription": "Create a welcome series for new subscribers that sends 3 messages over 7 days, with a special offer on day 3"
            }
        },
        "CampaignGenerationResponse": {
            "summary": "Example campaign generation response",
            "value": {
                "initialStepID": "welcome_step_1",
                "steps": [
                    {
                        "id": "welcome_step_1",
                        "type": "SendMessage",
                        "config": {
                            "messageContent": {
                                "body": "Welcome to our service! We're excited to have you on board."
                            },
                            "recipient": {
                                "type": "segment",
                                "segmentId": "new_subscribers"
                            }
                        }
                    }
                ],
                "metadata": {
                    "totalSteps": 3,
                    "estimatedDuration": "7 days",
                    "complexity": "medium"
                }
            }
        },
        "ErrorResponse": {
            "summary": "Example error response",
            "value": {
                "error": "VALIDATION_ERROR",
                "message": "Campaign description is too short",
                "correlation_id": "abc123-def456-ghi789",
                "status": "error",
                "type": "validation_error"
            }
        }
    }

    # Add response schemas
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error": {
                "type": "string",
                "description": "Error code"
            },
            "message": {
                "type": "string",
                "description": "Error description"
            },
            "correlation_id": {
                "type": "string",
                "description": "Request correlation ID for tracking"
            },
            "status": {
                "type": "string",
                "enum": ["error"],
                "description": "Response status"
            },
            "type": {
                "type": "string",
                "description": "Error type category"
            }
        },
        "required": ["error", "message", "correlation_id", "status", "type"]
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_api_documentation(app: FastAPI) -> None:
    """
    Setup enhanced API documentation for the application.

    Args:
        app: FastAPI application instance
    """
    settings = get_settings()

    # Configure custom OpenAPI schema
    app.openapi = lambda: custom_openapi_schema(app)

    # Add API metadata
    app.title = settings.APP_NAME
    app.version = settings.APP_VERSION
    app.description = """
## SMS Campaign Generation System

A sophisticated API service that transforms natural language campaign descriptions into JSON flows using Large Language Model (LLM) technology.

### Features

- **Natural Language Processing**: Convert campaign descriptions into structured JSON flows
- **Complete FlowBuilder Schema Support**: Full compatibility with all 16+ node types
- **Intelligent Validation**: Multi-layer validation with auto-correction capabilities
- **Performance Monitoring**: Comprehensive logging and metrics collection
- **Security**: Rate limiting, authentication, and security headers
- **Scalable Architecture**: Async design optimized for high throughput

### Getting Started

1. **Authentication**: Include your Bearer token in the Authorization header
2. **Rate Limiting**: Be mindful of rate limits (100 requests per minute by default)
3. **Correlation IDs**: Use `X-Correlation-ID` header for request tracking
4. **Response Format**: All responses include correlation IDs for debugging

### Error Handling

The API provides detailed error responses with:
- Error codes for programmatic handling
- Human-readable error messages
- Correlation IDs for support requests
- Structured error types for categorization

### Validation

All generated flows undergo comprehensive validation:
- Schema validation against FlowBuilder specifications
- Flow logic validation (circular references, missing connections)
- Best practices validation
- Automatic error correction when possible

### Rate Limits

- **Default**: 100 requests per minute
- **Burst**: Up to 150 requests in a single burst
- **Batch**: Maximum 10 campaigns per batch request
- **Headers**: Check `X-RateLimit-*` headers for current limits

### Monitoring

- **Health Checks**: `/health` endpoint for service status
- **Statistics**: `/api/v1/stats` for generation metrics
- **Correlation**: All requests include correlation IDs for tracing
- **Performance**: Response times included in headers

For detailed API documentation, visit the interactive docs at `/docs` (development only).
    """

    # Configure documentation URLs
    if settings.DEBUG:
        app.docs_url = "/docs"
        app.redoc_url = "/redoc"
        app.openapi_url = "/openapi.json"
    else:
        # Disable docs in production for security
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None


def get_api_examples() -> Dict[str, Any]:
    """
    Get comprehensive API usage examples.

    Returns:
        Dictionary containing example requests and responses
    """
    return {
        "campaign_generation": {
            "basic_request": {
                "method": "POST",
                "url": "/api/v1/generateFlow",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer your_token_here",
                    "X-Correlation-ID": "your-correlation-id"
                },
                "body": {
                    "campaignDescription": "Create a welcome series for new subscribers that sends 3 messages over 7 days"
                }
            },
            "complex_request": {
                "method": "POST",
                "url": "/api/v1/generateFlow",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer your_token_here",
                    "X-Correlation-ID": "your-correlation-id"
                },
                "body": {
                    "campaignDescription": "Create an abandoned cart recovery campaign with 3 messages. Send first message after 2 hours, second after 24 hours, and final after 72 hours. Include a 10% discount in the second message and free shipping in the final message. Use urgency tactics and personalize with customer name."
                }
            },
            "batch_request": {
                "method": "POST",
                "url": "/api/v1/generateFlow/batch",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer your_token_here",
                    "X-Correlation-ID": "batch-correlation-id"
                },
                "body": [
                    {
                        "campaignDescription": "Welcome series for new users"
                    },
                    {
                        "campaignDescription": "Weekly promotional campaign"
                    },
                    {
                        "campaignDescription": "Birthday celebration campaign"
                    }
                ]
            }
        },
        "health_checks": {
            "basic_health": {
                "method": "GET",
                "url": "/health",
                "description": "Basic service health check"
            },
            "campaign_health": {
                "method": "GET",
                "url": "/api/v1/health",
                "description": "Campaign service detailed health check"
            }
        },
        "statistics": {
            "get_stats": {
                "method": "GET",
                "url": "/api/v1/stats",
                "headers": {
                    "Authorization": "Bearer your_token_here"
                },
                "description": "Get campaign generation statistics"
            }
        },
        "reports": {
            "get_report": {
                "method": "GET",
                "url": "/api/v1/campaigns/{campaign_id}/report",
                "headers": {
                    "Authorization": "Bearer your_token_here"
                },
                "description": "Get validation report for specific campaign"
            }
        }
    }


def get_error_codes() -> Dict[str, str]:
    """
    Get comprehensive list of error codes and their meanings.

    Returns:
        Dictionary mapping error codes to descriptions
    """
    return {
        # General Errors
        "INTERNAL_SERVER_ERROR": "Unexpected internal server error",
        "BAD_REQUEST": "Invalid request format or parameters",
        "UNAUTHORIZED": "Authentication required or invalid credentials",
        "FORBIDDEN": "Access forbidden for current user",
        "NOT_FOUND": "Requested resource not found",
        "METHOD_NOT_ALLOWED": "HTTP method not allowed for this endpoint",
        "REQUEST_TIMEOUT": "Request processing timed out",
        "TOO_MANY_REQUESTS": "Rate limit exceeded",

        # Validation Errors
        "REQUEST_VALIDATION_ERROR": "Invalid request data format",
        "SCHEMA_VALIDATION_ERROR": "Data doesn't match expected schema",
        "FLOW_VALIDATION_ERROR": "Generated flow has validation issues",
        "CAMPAIGN_VALIDATION_ERROR": "Campaign description validation failed",

        # Campaign Generation Errors
        "CAMPAIGN_GENERATION_FAILED": "Campaign generation process failed",
        "LLM_SERVICE_ERROR": "Language model service unavailable or error",
        "PROMPT_GENERATION_ERROR": "Failed to generate LLM prompt",
        "RESPONSE_PARSING_ERROR": "Failed to parse LLM response",
        "FLOW_GENERATION_ERROR": "Failed to generate campaign flow",

        # Rate Limiting Errors
        "RATE_LIMIT_EXCEEDED": "Too many requests in time window",
        "BATCH_SIZE_EXCEEDED": "Batch request size exceeds limit",
        "TOKEN_LIMIT_EXCEEDED": "LLM token limit exceeded",

        # Authentication Errors
        "AUTHENTICATION_ERROR": "Authentication failed",
        "TOKEN_EXPIRED": "Authentication token has expired",
        "TOKEN_INVALID": "Authentication token is invalid",

        # Configuration Errors
        "SERVICE_UNAVAILABLE": "Service temporarily unavailable",
        "CONFIGURATION_ERROR": "Service configuration error",
        "DEPENDENCY_ERROR": "Required service dependency unavailable",

        # Business Logic Errors
        "CAMPAIGN_DESCRIPTION_TOO_SHORT": "Campaign description is too short",
        "CAMPAIGN_DESCRIPTION_TOO_LONG": "Campaign description is too long",
        "INVALID_CAMPAIGN_TYPE": "Requested campaign type is not supported",
        "INSUFFICIENT_PERMISSIONS": "User lacks required permissions",
    }