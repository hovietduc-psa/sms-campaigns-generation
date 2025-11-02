"""
Campaign generation endpoints.

This module provides the main API endpoints for campaign generation,
integrating LLM generation, validation, and orchestration services.
"""

import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.config import get_settings
from src.core.logging import get_logger, CampaignLogger
from src.models.requests import CampaignGenerationRequest, CampaignGenerationResponse
from src.services.campaign_generation.orchestrator import get_campaign_orchestrator, CampaignOrchestrator
from src.services.validation.reporting import get_validation_reporter

logger = get_logger(__name__)
campaign_logger = CampaignLogger()
security = HTTPBearer(auto_error=False)

router = APIRouter()


async def get_orchestrator() -> CampaignOrchestrator:
    """Dependency to get campaign orchestrator."""
    return get_campaign_orchestrator()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Extract current user from credentials."""
    if credentials and credentials.credentials:
        # In a real implementation, you would validate the token here
        # For now, we'll use the token as a simple user identifier
        return credentials.credentials
    return None


@router.post(
    "/generateFlow",
    response_model=CampaignGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate SMS Campaign Flow",
    description="Generate an SMS campaign flow from a natural language description",
    responses={
        200: {"description": "Campaign flow generated successfully"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def generate_campaign_flow(
    request: CampaignGenerationRequest,
    http_request: Request,
    orchestrator: CampaignOrchestrator = Depends(get_orchestrator),
    current_user: Optional[str] = Depends(get_current_user),
    settings: Any = Depends(get_settings),
) -> CampaignGenerationResponse:
    """
    Generate an SMS campaign flow from a natural language description.

    This endpoint orchestrates the complete campaign generation process:
    1. Analyzes the campaign description
    2. Generates prompts for the LLM
    3. Calls the LLM to generate flow JSON
    4. Parses and validates the response
    5. Applies auto-corrections if needed
    6. Returns the validated campaign flow

    Args:
        request: Campaign generation request with description
        http_request: HTTP request object for tracking
        orchestrator: Campaign orchestrator service
        current_user: Current user identifier
        settings: Application settings

    Returns:
        Generated campaign flow in JSON format

    Raises:
        HTTPException: If generation fails
    """
    start_time = time.time()
    request_id = str(int(start_time * 1000))  # Simple request ID

    try:
        # Log generation start
        campaign_logger.log_generation_start(
            campaign_description=request.campaignDescription,
            request_id=request_id,
            user_id=current_user,
        )

        # Generate campaign
        result = await orchestrator.generate_campaign(
            request=request,
            request_id=request_id,
            user_id=current_user,
        )

        # Build response
        if result.success:
            response_data = result.to_dict()

            # Log successful generation
            if result.validation_summary:
                campaign_logger.log_generation_success(
                    campaign_id=result.campaign_id,
                    generation_time_ms=result.metadata.get("total_time_ms", 0),
                    tokens_used=result.metadata.get("parse_metadata", {}).get("parsing_metadata", {}).get("tokens_used", 0),
                    model_used=result.metadata.get("model_used", "unknown"),
                    node_count=len(response_data.get("steps", [])),
                    request_id=request_id,
                    user_id=current_user,
                )
            else:
                campaign_logger.log_generation_success(
                    campaign_id=result.campaign_id,
                    generation_time_ms=result.metadata.get("total_time_ms", 0),
                    tokens_used=0,
                    model_used=result.metadata.get("model_used", "unknown"),
                    node_count=len(response_data.get("steps", [])),
                    request_id=request_id,
                    user_id=current_user,
                )

            # Create validation report if issues exist
            if result.validation_summary and result.validation_summary.total_issues > 0:
                validation_reporter = get_validation_reporter()
                validation_reporter.create_report(result.validation_summary, result.campaign_id)

            # Log request completion
            request_logger = get_logger("request")
            request_logger.info(
                "Campaign generation request completed",
                extra={
                    "method": "POST",
                    "path": "/generateFlow",
                    "status_code": 200,
                    "duration_ms": (time.time() - start_time) * 1000,
                    "request_id": request_id,
                    "user_id": current_user,
                }
            )

            # Extract response data
            return CampaignGenerationResponse(
                initialStepID=response_data.get("initialStepID"),
                steps=response_data.get("steps", []),
                metadata=response_data.get("metadata", {}),
            )

        else:
            # Generation failed
            campaign_logger.log_generation_error(
                error=result.errors[0] if result.errors else "Unknown error",
                generation_time_ms=result.metadata.get("total_time_ms", 0),
                request_id=request_id,
                user_id=current_user,
            )

            # Determine appropriate HTTP status
            if "validation" in str(result.errors).lower():
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            elif "rate" in str(result.errors).lower() or "limit" in str(result.errors).lower():
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": "CAMPAIGN_GENERATION_FAILED",
                    "message": result.errors[0] if result.errors else "Unknown error occurred",
                    "campaign_id": result.campaign_id,
                    "request_id": request_id,
                    "warnings": result.warnings,
                }
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Log unexpected error
        campaign_logger.log_generation_error(
            error=str(e),
            generation_time_ms=(time.time() - start_time) * 1000,
            request_id=request_id,
            user_id=current_user,
        )

        logger.error(
            f"Unexpected error in generate_campaign_flow: {e}",
            extra={
                "request_id": request_id,
                "user_id": current_user,
                "campaign_description": request.campaignDescription,
            },
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during campaign generation",
                "request_id": request_id,
            }
        )


@router.post(
    "/generateFlow/batch",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generate Multiple SMS Campaign Flows",
    description="Generate multiple campaign flows in batch from a list of descriptions",
)
async def generate_campaign_flows_batch(
    requests: list[CampaignGenerationRequest],
    http_request: Request,
    orchestrator: CampaignOrchestrator = Depends(get_orchestrator),
    current_user: Optional[str] = Depends(get_current_user),
    settings: Any = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Generate multiple campaign flows in batch.

    Args:
        requests: List of campaign generation requests
        http_request: HTTP request object for tracking
        orchestrator: Campaign orchestrator service
        current_user: Current user identifier
        settings: Application settings

    Returns:
        Dictionary with batch generation results
    """
    start_time = time.time()
    batch_id = str(int(start_time * 1000))

    try:
        # Validate batch size
        if len(requests) > 10:  # Reasonable batch limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch size too large. Maximum 10 requests per batch, got {len(requests)}"
            )

        logger.info(
            "Starting batch campaign generation",
            extra={
                "batch_id": batch_id,
                "batch_size": len(requests),
                "user_id": current_user,
            }
        )

        # Generate campaigns
        results = await orchestrator.generate_campaign_batch(
            requests=requests,
            user_id=current_user,
        )

        # Build response
        successful_results = [
            result.to_dict() for result in results if result.success
        ]
        failed_results = [
            {
                "campaign_id": result.campaign_id,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata,
            }
            for result in results if not result.success
        ]

        response_data = {
            "batch_id": batch_id,
            "total_requests": len(requests),
            "successful_generations": len(successful_results),
            "failed_generations": len(failed_results),
            "success_rate": len(successful_results) / len(requests) * 100,
            "results": successful_results,
            "errors": failed_results,
            "metadata": {
                "generation_time_ms": round((time.time() - start_time) * 1000, 2),
                "user_id": current_user,
            }
        }

        # Log batch completion
        logger.info(
            "Batch campaign generation completed",
            extra={
                "batch_id": batch_id,
                "total_requests": len(requests),
                "successful_generations": len(successful_results),
                "failed_generations": len(failed_results),
                "success_rate": response_data["success_rate"],
                "generation_time_ms": response_data["metadata"]["generation_time_ms"],
                "user_id": current_user,
            }
        )

        return response_data

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error in generate_campaign_flows_batch: {e}",
            extra={
                "batch_id": batch_id,
                "batch_size": len(requests),
                "user_id": current_user,
            },
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BATCH_GENERATION_FAILED",
                "message": "An unexpected error occurred during batch campaign generation",
                "batch_id": batch_id,
            }
        )


@router.get(
    "/health",
    summary="Campaign Service Health Check",
    description="Health check for the campaign generation service",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def campaign_health_check(
    orchestrator: CampaignOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Health check endpoint for campaign service."""
    try:
        health_status = await orchestrator.health_check()
        status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

        # Add service information
        health_status.update({
            "service": "campaign-generation",
            "version": "1.0.0",
            "environment": get_settings().ENVIRONMENT,
        })

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "campaign-generation",
            "error": str(e),
            "timestamp": time.time(),
        }


@router.get(
    "/stats",
    summary="Campaign Generation Statistics",
    description="Get statistics and performance metrics for campaign generation",
)
async def get_generation_statistics(
    orchestrator: CampaignOrchestrator = Depends(get_orchestrator),
    current_user: Optional[str] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get campaign generation statistics."""
    try:
        # Get orchestrator statistics
        stats = orchestrator.get_generation_statistics()

        # Get validation reporting statistics
        validation_reporter = get_validation_reporter()
        reports = validation_reporter.get_reports()

        # Add reporting statistics
        stats.update({
            "validation_reports_count": len(reports),
            "average_quality_score": 0,
            "total_validations": len(reports),
        })

        if reports:
            quality_scores = [report.quality_score for report in reports]
            stats["average_quality_score"] = sum(quality_scores) / len(quality_scores)

        return stats

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get(
    "/campaigns/{campaign_id}/report",
    summary="Get Campaign Validation Report",
    description="Get detailed validation report for a specific campaign",
)
async def get_campaign_report(
    campaign_id: str,
    current_user: Optional[str] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get validation report for a specific campaign."""
    try:
        validation_reporter = get_validation_reporter()
        report = validation_reporter.get_latest_report(campaign_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No validation report found for campaign: {campaign_id}"
            )

        return report.to_dict()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get campaign report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve campaign report"
        )