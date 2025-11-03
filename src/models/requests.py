"""
Request and response models for the API.
Updated with whitespace validation fix.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class CampaignGenerationRequest(BaseModel):
    """Request model for campaign generation."""

    campaignDescription: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language description of the campaign to generate"
    )

    @field_validator('campaignDescription')
    @classmethod
    def validate_campaign_description(cls, v):
        """Validate that campaign description contains actual content, not just whitespace."""
        if not v or not v.strip():
            raise ValueError('Campaign description cannot be empty or whitespace only')
        stripped = v.strip()
        if len(stripped) < 3:
            raise ValueError('Campaign description must be at least 3 characters long after removing whitespace')
        return stripped

    # Optional parameters for future enhancement
    language: Optional[str] = Field(
        default="en",
        description="Language code for campaign generation"
    )

    tone: Optional[str] = Field(
        default="professional",
        description="Tone for campaign messages"
    )

    maxLength: Optional[int] = Field(
        default=None,
        ge=1,
        le=10000,
        description="Maximum desired flow length"
    )

    priority: Optional[str] = Field(
        default="normal",
        description="Campaign priority level"
    )


class CampaignGenerationResponse(BaseModel):
    """Response model for campaign generation."""

    initialStepID: str = Field(
        ...,
        description="ID of the initial step in the flow"
    )

    steps: list[Dict[str, Any]] = Field(
        ...,
        description="List of flow steps/nodes"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the generation"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(
        ...,
        description="Error code"
    )

    message: str = Field(
        ...,
        description="Error message"
    )

    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )

    status: str = Field(
        default="error",
        description="Response status"
    )


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    version: Optional[str] = Field(None, description="Application version")
    service: Optional[str] = Field(None, description="Service name")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""

    error: str = Field(
        default="VALIDATION_ERROR",
        description="Error code"
    )

    message: str = Field(
        ...,
        description="Error message"
    )

    field: Optional[str] = Field(
        default=None,
        description="Field that caused validation error"
    )

    status: str = Field(
        default="error",
        description="Response status"
    )


class RequestValidationErrorResponse(BaseModel):
    """Request validation error response model."""

    error: str = Field(
        default="REQUEST_VALIDATION_ERROR",
        description="Error code"
    )

    message: str = Field(
        default="Invalid request data",
        description="Error message"
    )

    details: list[Dict[str, Any]] = Field(
        ...,
        description="List of validation errors"
    )

    status: str = Field(
        default="error",
        description="Response status"
    )