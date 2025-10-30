"""
Campaign Generation API endpoints.
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...security.authentication import verify_api_key
from ...models.campaign_generation import (
    GenerationRequest,
    GenerationResponse,
    CampaignType,
)
from ...services.campaign_generation.orchestrator import create_campaign_orchestrator
from ...services.campaign_validation import create_validator
from ...observability.metrics import get_metrics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
metrics = get_metrics_service()


# Dependency for campaign orchestrator
def get_campaign_orchestrator():
    """Get campaign orchestrator instance."""
    from ...core.config import get_settings
    settings = get_settings()

    # Try OpenRouter first, then OpenAI, then GROQ
    openrouter_api_key = settings.openrouter_api_key
    openrouter_base_url = settings.openrouter_base_url
    openai_api_key = settings.openai_api_key
    groq_api_key = settings.groq_api_key

    api_key = None
    base_url = None
    use_groq = False
    use_openrouter = False
    model_primary = "gpt-4o"
    model_fallback = "gpt-4o-mini"

    # Try OpenRouter first
    if openrouter_api_key and not openrouter_api_key.startswith("sk-your-") and not openrouter_api_key.startswith("sk-placeholder-"):
        api_key = openrouter_api_key
        base_url = openrouter_base_url
        use_openrouter = True
        model_primary = settings.openrouter_model_primary
        model_fallback = settings.openrouter_model_fallback
        print(f"Using OpenRouter with models: {model_primary} / {model_fallback}")

    # Fallback to OpenAI
    elif openai_api_key and not openai_api_key.startswith("sk-your-") and not openai_api_key.startswith("sk-placeholder-"):
        api_key = openai_api_key
        use_openrouter = False
        print(f"Using OpenAI with models: {model_primary} / {model_fallback}")

    # Fallback to GROQ
    elif groq_api_key:
        api_key = groq_api_key
        use_groq = True
        print("Using GROQ as fallback")

    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No valid AI provider configured (OpenRouter, OpenAI, or GROQ)"
        )

    # Optional Qdrant for templates
    qdrant_url = settings.qdrant_url
    qdrant_api_key = settings.qdrant_api_key

    # Cohere API key for embeddings
    cohere_api_key = settings.cohere_api_key

    # Template feature temporarily disabled due to Qdrant integration issues
    enable_templates = False

    return create_campaign_orchestrator(
        openai_api_key=api_key,
        base_url=base_url,
        model_primary=model_primary,
        model_fallback=model_fallback,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        cohere_api_key=cohere_api_key,
        enable_templates=enable_templates,
        use_groq=use_groq,
        use_openrouter=use_openrouter
    )


@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate campaign from natural language",
    description="Generate a complete SMS campaign from a natural language description"
)
async def generate_campaign(
    request: GenerationRequest,
    orchestrator=Depends(get_campaign_orchestrator),
    _: bool = Depends(verify_api_key),
):
    """
    Generate a complete campaign from natural language description.

    This endpoint:
    1. Extracts intent from the description using GPT-4o-mini
    2. Searches for similar templates (if enabled)
    3. Plans campaign structure using GPT-4o
    4. Generates content for all steps using GPT-4o-mini
    5. Validates the campaign comprehensively
    6. Returns campaign JSON ready for execution engine

    **Cost:** ~$0.12 per campaign (planning + content generation)

    **Processing Time:** 4-6 seconds typical

    **Features:**
    - Template-based generation for proven patterns
    - Multi-step retry with fallback
    - Comprehensive validation (schema + flow + best practices)
    - Quality scoring (A-F grade)
    - Optimization suggestions

    **Example Request:**
    ```json
    {
        "merchant_id": "merchant_123",
        "description": "Create a flash sale campaign offering 20% off everything. Send initial message, then follow up after 6 hours if no click.",
        "campaign_type": "promotional",
        "use_template": true
    }
    ```

    **Example Response:**
    ```json
    {
        "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
        "campaign_json": {
            "initialStepID": "step_001",
            "steps": [...]
        },
        "generation_metadata": {
            "total_cost_usd": 0.12,
            "duration_seconds": 4.5,
            "model_planning": "gpt-4o",
            "model_content": "gpt-4o-mini"
        },
        "validation": {
            "is_valid": true,
            "issues": [],
            "warnings": []
        },
        "status": "ready"
    }
    ```
    """
    start_time = time.time()

    try:
        logger.info(f"Generating campaign for merchant {request.merchant_id}")
        logger.info(f"Description: {request.description[:100]}...")

        # Prepare merchant context
        merchant_context = {
            "merchant_id": request.merchant_id,
            "name": request.merchant_id,  # Could be loaded from DB
            "industry": "retail",
            "brand_voice": "friendly and professional",
            "url": "https://example.com"
        }

        # Generate campaign
        response = await orchestrator.generate_campaign(
            request=request,
            merchant_context=merchant_context,
            max_retries=2
        )

        # Record metrics
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Campaign generated: id={response.campaign_id}, "
            f"status={response.status}, "
            f"cost=${response.generation_metadata.total_cost_usd:.4f}, "
            f"time={elapsed_ms}ms"
        )

        return response

    except Exception as e:
        logger.error(f"Error generating campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate campaign: {str(e)}"
        )


@router.post(
    "/validate",
    summary="Validate campaign JSON",
    description="Validate a campaign JSON structure comprehensively"
)
async def validate_campaign(
    campaign_json: dict,
    strict: bool = Query(default=False, description="Strict mode (warnings as errors)"),
    include_optimizations: bool = Query(default=True, description="Include optimization suggestions"),
    _: bool = Depends(verify_api_key),
):
    """
    Validate a campaign JSON structure.

    This endpoint performs comprehensive validation:
    - **Schema validation**: Required fields, types, references
    - **Flow validation**: Reachability, dead ends, infinite loops
    - **Best practices**: SMS optimization, personalization, CTAs
    - **Optimization suggestions**: Cost, performance, engagement improvements

    **Validation Layers:**
    1. Pydantic model validation (structure & types)
    2. Step ID uniqueness and references
    3. Graph-based flow analysis
    4. SMS best practices checking
    5. Grading (A-F) based on quality

    **Example Request:**
    ```json
    {
        "initialStepID": "step_001",
        "steps": [
            {
                "id": "step_001",
                "type": "message",
                "text": "{{merchant.name}}: Flash Sale! 20% off with code FLASH20. Shop: {{merchant.url}}",
                "events": [
                    {"id": "e1", "type": "click", "nextStepID": "step_end"}
                ]
            },
            {
                "id": "step_end",
                "type": "end",
                "reason": "Campaign completed"
            }
        ]
    }
    ```
    """
    start_time = time.time()

    try:
        validator = create_validator()

        result = validator.validate(
            campaign_json=campaign_json,
            include_optimizations=include_optimizations,
            strict=strict
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Campaign validated: valid={result.is_valid}, "
            f"errors={len(result.errors)}, "
            f"warnings={len(result.warnings)}, "
            f"grade={result.best_practices_grade}, "
            f"time={elapsed_ms}ms"
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"Error validating campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate campaign: {str(e)}"
        )


@router.post(
    "/templates/seed",
    summary="Seed official campaign templates",
    description="Seed the template library with official pre-built campaigns"
)
async def seed_templates(
    orchestrator=Depends(get_campaign_orchestrator),
    _: bool = Depends(verify_api_key),
):
    """
    Seed official campaign templates into the template library.

    This adds proven, high-performing campaign templates that can be used
    as starting points for generation.

    **Templates seeded:**
    - Simple promotional campaign
    - Abandoned cart recovery
    - Welcome series
    - Re-engagement campaign

    **Note:** Requires Qdrant to be configured with QDRANT_URL environment variable.
    """
    try:
        if not orchestrator.template_manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template manager not enabled. Configure QDRANT_URL to use templates."
            )

        await orchestrator.template_manager.seed_official_templates()

        logger.info("Official templates seeded successfully")

        return {
            "success": True,
            "message": "Official templates seeded successfully",
            "templates_added": 1  # Update as more templates are added
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error seeding templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed templates: {str(e)}"
        )


@router.post(
    "/templates/search",
    summary="Search similar campaign templates",
    description="Search for similar campaign templates using semantic search"
)
async def search_templates(
    query: str = Query(..., description="Search query (campaign description or intent)"),
    campaign_type: Optional[str] = Query(default=None, description="Filter by campaign type"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    min_similarity: float = Query(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score"),
    orchestrator=Depends(get_campaign_orchestrator),
    _: bool = Depends(verify_api_key),
):
    """
    Search for similar campaign templates.

    Uses semantic search to find relevant templates based on:
    - Campaign description/intent
    - Campaign type (promotional, abandoned_cart, etc.)
    - Historical performance

    **Example Query:**
    "Create a flash sale campaign with discount code"

    **Returns:**
    - Template ID and name
    - Similarity score (0-1)
    - Campaign JSON structure
    - Average conversion rate (if available)
    - Times used (popularity indicator)
    """
    try:
        if not orchestrator.template_manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template manager not enabled. Configure QDRANT_URL to use templates."
            )

        results = await orchestrator.template_manager.search_similar(
            query=query,
            campaign_type=campaign_type,
            top_k=top_k,
            min_similarity=min_similarity
        )

        logger.info(f"Template search: query='{query[:50]}...', results={len(results)}")

        return {
            "query": query,
            "campaign_type": campaign_type,
            "results": results,
            "count": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search templates: {str(e)}"
        )


@router.get(
    "/types",
    summary="Get available campaign types",
    description="Get list of supported campaign types"
)
async def get_campaign_types(_: bool = Depends(verify_api_key)):
    """
    Get list of available campaign types.

    Returns all supported campaign types with descriptions.
    """
    return {
        "campaign_types": [
            {
                "value": ct.value,
                "name": ct.value.replace("_", " ").title(),
                "description": _get_campaign_type_description(ct)
            }
            for ct in CampaignType
        ]
    }


def _get_campaign_type_description(campaign_type: CampaignType) -> str:
    """Get description for campaign type."""
    descriptions = {
        CampaignType.PROMOTIONAL: "Time-limited sales and promotions with discount codes",
        CampaignType.ABANDONED_CART: "Re-engage customers who left items in cart",
        CampaignType.WIN_BACK: "Win back inactive or churned customers with special offers",
        CampaignType.WELCOME: "Onboard new subscribers with multi-step introduction",
        CampaignType.POST_PURCHASE: "Follow up after purchase with reviews and upsells",
        CampaignType.BIRTHDAY: "Celebrate customer birthdays with special offers",
        CampaignType.SEASONAL: "Holiday and seasonal campaigns",
        CampaignType.REORDER_REMINDER: "Remind customers to reorder consumable products",
        CampaignType.PRODUCT_LAUNCH: "Announce new products with teasers and launch offers",
        CampaignType.CUSTOM: "Custom campaign type for unique business needs",
    }
    return descriptions.get(campaign_type, "Campaign type")