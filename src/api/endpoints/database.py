"""
Database API endpoints for retrieving campaign data and metrics.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, Field

from src.services.database.campaign_logger import get_database_logger

from src.core.logging import get_logger
logger = get_logger(__name__)
router = APIRouter()


class CampaignLogResponse(BaseModel):
    """Response model for campaign log data."""
    id: str
    campaign_id: str
    request_id: str
    user_id: Optional[str]
    campaign_description: str
    generated_flow: Dict[str, Any]
    generation_time_ms: Optional[int]
    tokens_used: Optional[int]
    model_used: Optional[str]
    status: str
    error_message: Optional[str]
    node_count: Optional[int]
    validation_issues: int
    corrections_applied: int
    quality_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM model, converting UUID to string."""
        return cls.model_validate({
            'id': str(obj.id),
            'campaign_id': obj.campaign_id,
            'request_id': obj.request_id,
            'user_id': obj.user_id,
            'campaign_description': obj.campaign_description,
            'generated_flow': obj.generated_flow,
            'generation_time_ms': obj.generation_time_ms,
            'tokens_used': obj.tokens_used,
            'model_used': obj.model_used,
            'status': obj.status,
            'error_message': obj.error_message,
            'node_count': obj.node_count,
            'validation_issues': obj.validation_issues,
            'corrections_applied': obj.corrections_applied,
            'quality_score': obj.quality_score,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
        })


class CampaignMetricsResponse(BaseModel):
    """Response model for campaign metrics data."""
    id: str
    date: date
    total_requests: int
    successful_generations: int
    failed_generations: int
    partial_generations: int
    average_generation_time_ms: Optional[float]
    average_tokens_used: Optional[float]
    average_quality_score: Optional[float]
    model_usage: Optional[Dict[str, Any]]
    total_nodes_generated: int
    total_validation_issues: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserFeedbackRequest(BaseModel):
    """Request model for submitting user feedback."""
    campaign_log_id: str = Field(..., description="ID of the campaign log to provide feedback for")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Text feedback")
    issues: Optional[Dict[str, Any]] = Field(None, description="Specific issues reported")
    would_use_again: Optional[bool] = Field(None, description="Whether user would use this campaign again")


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics."""
    total_campaigns: int
    successful_campaigns: int
    failed_campaigns: int
    average_generation_time: Optional[float]
    average_quality_score: Optional[float]
    most_used_model: Optional[str]
    campaigns_today: int
    database_healthy: bool


@router.get(
    "/campaigns",
    response_model=List[CampaignLogResponse],
    status_code=200,
    summary="Get Campaign Logs",
    description="Retrieve campaign generation logs with optional filtering",
)
async def get_campaign_logs(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of campaigns to return"),
    offset: int = Query(0, ge=0, description="Number of campaigns to skip"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status (success, error, partial)"),
    model_used: Optional[str] = Query(None, description="Filter by LLM model used"),
    date_from: Optional[date] = Query(None, description="Filter campaigns from this date"),
    date_to: Optional[date] = Query(None, description="Filter campaigns until this date"),
    db_logger = Depends(get_database_logger),
) -> List[CampaignLogResponse]:
    """
    Retrieve campaign generation logs from the database.

    Supports filtering by user, status, model, and date ranges.
    Returns paginated results.
    """
    try:
        if not db_logger.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Database logging is currently disabled"
            )

        campaign_logs = await db_logger.get_campaign_logs(
            limit=limit,
            offset=offset,
            user_id=user_id,
            status=status,
            model_used=model_used,
            date_from=date_from,
            date_to=date_to,
        )

        return [CampaignLogResponse.from_orm(log) for log in campaign_logs]

    except Exception as e:
        logger.error(f"Failed to retrieve campaign logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve campaign logs"
        )


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignLogResponse,
    status_code=200,
    summary="Get Campaign by ID",
    description="Retrieve a specific campaign by its ID",
)
async def get_campaign_by_id(
    campaign_id: str,
    db_logger = Depends(get_database_logger),
) -> CampaignLogResponse:
    """Retrieve a specific campaign by its ID."""
    try:
        if not db_logger.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Database logging is currently disabled"
            )

        # Get campaign logs and filter by campaign_id
        campaign_logs = await db_logger.get_campaign_logs(limit=1000, offset=0)

        for log in campaign_logs:
            if log.campaign_id == campaign_id:
                return CampaignLogResponse(
                    id=str(log.id),
                    campaign_id=log.campaign_id,
                    request_id=log.request_id,
                    user_id=log.user_id,
                    campaign_description=log.campaign_description,
                    generated_flow=log.generated_flow,
                    generation_time_ms=log.generation_time_ms,
                    tokens_used=log.tokens_used,
                    model_used=log.model_used,
                    status=log.status,
                    error_message=log.error_message,
                    node_count=log.node_count,
                    validation_issues=log.validation_issues,
                    corrections_applied=log.corrections_applied,
                    quality_score=log.quality_score,
                    created_at=log.created_at,
                    updated_at=log.updated_at,
                )

        raise HTTPException(
            status_code=404,
            detail=f"Campaign with ID {campaign_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve campaign {campaign_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve campaign"
        )


@router.get(
    "/metrics",
    response_model=List[CampaignMetricsResponse],
    status_code=200,
    summary="Get Campaign Metrics",
    description="Retrieve daily campaign generation metrics",
)
async def get_campaign_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve metrics for"),
    db_logger = Depends(get_database_logger),
) -> List[CampaignMetricsResponse]:
    """Retrieve daily campaign generation metrics."""
    try:
        if not db_logger.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Database logging is currently disabled"
            )

        metrics = await db_logger.get_daily_metrics(days=days)
        return [CampaignMetricsResponse.model_validate(metric) for metric in metrics]

    except Exception as e:
        logger.error(f"Failed to retrieve campaign metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve campaign metrics"
        )


@router.get(
    "/stats",
    response_model=DatabaseStatsResponse,
    status_code=200,
    summary="Get Database Statistics",
    description="Get overall database statistics and health status",
)
async def get_database_stats(
    db_logger = Depends(get_database_logger),
) -> DatabaseStatsResponse:
    """Get overall database statistics and health status."""
    try:
        if not db_logger.is_enabled():
            return DatabaseStatsResponse(
                total_campaigns=0,
                successful_campaigns=0,
                failed_campaigns=0,
                average_generation_time=None,
                average_quality_score=None,
                most_used_model=None,
                campaigns_today=0,
                database_healthy=False,
            )

        # Get recent campaigns for stats
        recent_campaigns = await db_logger.get_campaign_logs(limit=1000, offset=0)

        # Calculate statistics
        total_campaigns = len(recent_campaigns)
        successful_campaigns = len([c for c in recent_campaigns if c.status == "success"])
        failed_campaigns = len([c for c in recent_campaigns if c.status == "error"])

        # Calculate averages
        generation_times = [c.generation_time_ms for c in recent_campaigns if c.generation_time_ms]
        quality_scores = [c.quality_score for c in recent_campaigns if c.quality_score]

        avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else None
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None

        # Find most used model
        models = [c.model_used for c in recent_campaigns if c.model_used]
        most_used_model = max(set(models), key=models.count) if models else None

        # Get today's campaigns
        today = date.today()
        campaigns_today = len([
            c for c in recent_campaigns
            if c.created_at.date() == today
        ])

        return DatabaseStatsResponse(
            total_campaigns=total_campaigns,
            successful_campaigns=successful_campaigns,
            failed_campaigns=failed_campaigns,
            average_generation_time=avg_generation_time,
            average_quality_score=avg_quality_score,
            most_used_model=most_used_model,
            campaigns_today=campaigns_today,
            database_healthy=await db_logger.is_healthy(),
        )

    except Exception as e:
        logger.error(f"Failed to retrieve database stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve database statistics"
        )


@router.post(
    "/feedback",
    status_code=201,
    summary="Submit User Feedback",
    description="Submit feedback for a generated campaign",
)
async def submit_user_feedback(
    feedback: UserFeedbackRequest,
    db_logger = Depends(get_database_logger),
) -> Dict[str, Any]:
    """Submit user feedback for a generated campaign."""
    try:
        if not db_logger.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Database logging is currently disabled"
            )

        # Convert campaign_log_id string to UUID
        from uuid import UUID
        try:
            campaign_log_uuid = UUID(feedback.campaign_log_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid campaign_log_id format"
            )

        success = await db_logger.log_user_feedback(
            campaign_log_id=campaign_log_uuid,
            user_id=None,  # Could be extracted from auth token in future
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            issues=feedback.issues,
            would_use_again=feedback.would_use_again,
        )

        if success:
            return {
                "message": "Feedback submitted successfully",
                "campaign_log_id": feedback.campaign_log_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to save feedback"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit user feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback"
        )


@router.get(
    "/health",
    status_code=200,
    summary="Database Health Check",
    description="Check the health and status of the database logging system",
)
async def database_health_check(
    db_logger = Depends(get_database_logger),
) -> Dict[str, Any]:
    """Check the health and status of the database logging system."""
    try:
        is_healthy = await db_logger.is_healthy()
        is_enabled = db_logger.is_enabled()

        return {
            "database_healthy": is_healthy,
            "logging_enabled": is_enabled,
            "status": "healthy" if is_healthy and is_enabled else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "memory_fallback_size": len(db_logger._memory_fallback) if hasattr(db_logger, '_memory_fallback') else 0,
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "database_healthy": False,
            "logging_enabled": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }