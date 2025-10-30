"""
Campaign generation models for API requests and responses.

This module defines models for the AI campaign generation service,
including generation requests, responses, and validation results.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CampaignType(str, Enum):
    """Campaign type categories."""
    PROMOTIONAL = "promotional"
    ABANDONED_CART = "abandoned_cart"
    WIN_BACK = "win_back"
    WELCOME = "welcome"
    POST_PURCHASE = "post_purchase"
    BIRTHDAY = "birthday"
    SEASONAL = "seasonal"
    REORDER_REMINDER = "reorder_reminder"
    PRODUCT_LAUNCH = "product_launch"
    CUSTOM = "custom"


class GenerationStatus(str, Enum):
    """Campaign generation status."""
    DRAFT = "draft"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


# ============================================================================
# Request Models
# ============================================================================

class SchedulingConfig(BaseModel):
    """Scheduling configuration for campaigns."""
    datetime: Optional[str] = Field(None, description="Scheduled datetime in ISO format")
    timezone: Optional[str] = Field(None, description="Timezone (e.g., 'PST', 'EST')")
    description: Optional[str] = Field(None, description="Human-readable scheduling description")

    @validator('datetime')
    def validate_datetime(cls, v):
        """Validate datetime format."""
        if v and not v.startswith('20'):
            raise ValueError("Datetime must be in valid format")
        return v


class OfferConfig(BaseModel):
    """Offer/discount configuration."""
    type: Optional[str] = Field(None, description="Offer type: 'percentage_discount', 'fixed_amount', 'code'")
    value: Optional[float] = Field(None, description="Discount value (percentage or amount)")
    scope: Optional[str] = Field(None, description="Offer scope: 'sitewide', 'category', 'product'")
    code: Optional[str] = Field(None, description="Discount code")
    expiry: Optional[str] = Field(None, description="Expiry date")


class GenerationRequest(BaseModel):
    """Request model for generating a campaign from natural language."""
    merchant_id: str = Field(..., description="Merchant identifier")
    description: str = Field(
        ...,
        description="Natural language description of the campaign",
        min_length=10,
        max_length=2000
    )
    campaign_type: Optional[CampaignType] = Field(
        None,
        description="Type of campaign (optional, will be inferred if not provided)"
    )

    # Structured inputs for precise requirements
    scheduling: Optional[SchedulingConfig] = Field(
        None,
        description="Campaign scheduling configuration"
    )
    specific_cta: Optional[str] = Field(
        None,
        description="Exact call-to-action text to include in messages"
    )
    store_link: Optional[str] = Field(
        None,
        description="Specific store link to include"
    )
    offer: Optional[OfferConfig] = Field(
        None,
        description="Offer/discount configuration"
    )

    # Existing fields
    target_audience: Optional[Dict[str, Any]] = Field(
        None,
        description="Target audience criteria (optional)"
    )
    goals: Optional[List[str]] = Field(
        None,
        description="Campaign goals (e.g., 'increase_revenue', 're_engage')"
    )
    constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="Generation constraints (e.g., max_steps, budget_per_customer)"
    )
    merchant_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Merchant-specific context (brand voice, product catalog, etc.)"
    )
    use_template: Optional[bool] = Field(
        default=False,
        description="Whether to use template library for inspiration (temporarily disabled)"
    )

    @validator('description')
    def validate_description(cls, v):
        """Ensure description is meaningful."""
        if len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v.strip()

    class Config:
        use_enum_values = True


class CampaignUpdateRequest(BaseModel):
    """Request model for updating a generated campaign."""
    name: Optional[str] = Field(None, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    campaign_json: Optional[Dict[str, Any]] = Field(None, description="Updated campaign JSON")
    status: Optional[GenerationStatus] = Field(None, description="Campaign status")

    class Config:
        use_enum_values = True


class TemplateSearchRequest(BaseModel):
    """Request model for searching campaign templates."""
    query: str = Field(..., description="Search query")
    campaign_type: Optional[CampaignType] = Field(None, description="Filter by campaign type")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")

    class Config:
        use_enum_values = True


# ============================================================================
# Response Models
# ============================================================================

class ValidationResult(BaseModel):
    """Campaign validation results."""
    is_valid: bool = Field(..., description="Whether campaign passed validation")
    issues: List[str] = Field(default_factory=list, description="Critical issues that must be fixed")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    suggestions: List[str] = Field(default_factory=list, description="Optimization suggestions")

    @property
    def has_issues(self) -> bool:
        """Check if there are any critical issues."""
        return len(self.issues) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class GenerationMetadata(BaseModel):
    """Metadata about the generation process."""
    model_planning: str = Field(..., description="LLM model used for planning")
    model_content: str = Field(..., description="LLM model used for content generation")
    total_tokens: int = Field(..., description="Total tokens consumed")
    planning_tokens: int = Field(default=0, description="Tokens used for planning")
    generation_tokens: int = Field(default=0, description="Tokens used for content generation")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    planning_cost_usd: float = Field(default=0.0, description="Cost for planning")
    generation_cost_usd: float = Field(default=0.0, description="Cost for content generation")
    duration_seconds: float = Field(..., description="Total generation time in seconds")
    template_used: Optional[str] = Field(None, description="Template ID if template was used")
    template_similarity: Optional[float] = Field(None, description="Similarity score to template")
    attempts: int = Field(default=1, description="Number of generation attempts")


class GenerationResponse(BaseModel):
    """Response model for campaign generation."""
    campaign_id: str = Field(..., description="Unique campaign identifier (UUID)")
    campaign_json: Dict[str, Any] = Field(..., description="Complete campaign JSON structure")
    generation_metadata: GenerationMetadata = Field(..., description="Generation metadata")
    validation: ValidationResult = Field(..., description="Validation results")
    status: str = Field(default="draft", description="Campaign status")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CampaignListItem(BaseModel):
    """List item model for campaign listing."""
    campaign_id: str
    merchant_id: str
    name: str
    campaign_type: Optional[str]
    status: str
    ai_generated: bool
    validation_passed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CampaignListResponse(BaseModel):
    """Response model for listing campaigns."""
    campaigns: List[CampaignListItem]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    has_more: bool


class TemplateResponse(BaseModel):
    """Response model for campaign template."""
    template_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    use_case: Optional[str]
    template_json: Dict[str, Any]
    variables: Optional[Dict[str, Any]]
    avg_conversion_rate: Optional[float]
    times_used: int
    is_official: bool
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TemplateSearchResult(BaseModel):
    """Search result for template."""
    template: TemplateResponse
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class TemplateSearchResponse(BaseModel):
    """Response model for template search."""
    results: List[TemplateSearchResult]
    total: int


# ============================================================================
# Intent Extraction (Internal Model)
# ============================================================================

class CampaignIntent(BaseModel):
    """Extracted campaign intent from natural language description."""
    campaign_type: CampaignType = Field(..., description="Detected campaign type")
    goals: List[str] = Field(..., description="Detected campaign goals")
    target_audience: Dict[str, Any] = Field(default_factory=dict, description="Detected audience criteria")
    key_products: Optional[List[str]] = Field(default=None, description="Mentioned products")
    discount_info: Optional[Dict[str, Any]] = Field(None, description="Discount/offer information")
    timing: Optional[Dict[str, Any]] = Field(None, description="Timing information")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in intent extraction")

    @validator('key_products', pre=True, always=True)
    def set_key_products(cls, v):
        """Convert None to empty list for key_products."""
        return v if v is not None else []

    class Config:
        use_enum_values = True


# ============================================================================
# Error Responses
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused error")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")