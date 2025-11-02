"""
Health check and monitoring endpoints.

This module provides comprehensive health monitoring including:
- Service health checks
- Component status monitoring
- Performance metrics
- System information
"""

import time
import psutil
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.logging import get_logger
from src.services.campaign_generation.orchestrator import get_campaign_orchestrator, CampaignOrchestrator
from src.services.llm_engine.llm_client import get_llm_client
from src.services.validation.validator import get_validator
from src.services.validation.reporting import get_validation_reporter

logger = get_logger(__name__)
router = APIRouter()


class HealthCheckResponse:
    """Health check response model."""

    def __init__(
        self,
        status: str,
        timestamp: datetime,
        service_name: str = "sms-campaign-generation",
        version: str = "1.0.0",
        environment: str = "production",
        components: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        checks: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.timestamp = timestamp
        self.service_name = service_name
        self.version = version
        self.environment = environment
        self.components = components or {}
        self.metrics = metrics or {}
        self.checks = checks or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "service": {
                "name": self.service_name,
                "version": self.version,
                "environment": self.environment
            },
            "components": self.components,
            "metrics": self.metrics,
            "checks": self.checks
        }


@router.get(
    "/health",
    summary="Basic Health Check",
    description="Basic health check endpoint for load balancers and monitoring",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"}
    }
)
async def basic_health_check() -> Dict[str, Any]:
    """Basic health check for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "sms-campaign-generation",
        "version": "1.0.0"
    }


@router.get(
    "/health/detailed",
    summary="Detailed Health Check",
    description="Comprehensive health check with component status and metrics",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy or degraded"}
    }
)
async def detailed_health_check(
    orchestrator: CampaignOrchestrator = Depends(get_campaign_orchestrator)
) -> Dict[str, Any]:
    """
    Detailed health check with component status and metrics.

    Returns comprehensive health information including:
    - Overall service status
    - Component health checks
    - System metrics
    - Performance indicators
    """
    settings = get_settings()
    start_time = time.time()

    try:
        # Initialize health response
        health_response = HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            service_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT
        )

        # Check campaign orchestrator
        try:
            orchestrator_health = await orchestrator.health_check()
            health_response.components["campaign_orchestrator"] = {
                "status": orchestrator_health.get("status", "unknown"),
                "details": orchestrator_health.get("components", {}),
                "timestamp": orchestrator_health.get("timestamp")
            }

            if orchestrator_health.get("status") != "healthy":
                health_response.status = "degraded"
        except Exception as e:
            health_response.components["campaign_orchestrator"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_response.status = "unhealthy"

        # Check LLM client
        try:
            llm_client = get_llm_client()
            await llm_client.estimate_tokens("health check test")
            health_response.components["llm_client"] = {
                "status": "healthy",
                "model": settings.OPENAI_MODEL,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            health_response.components["llm_client"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_response.status = "unhealthy"

        # Check validator
        try:
            validator = get_validator()
            test_flow = {"initialStepID": "welcome-step", "steps": [{"id": "welcome-step", "type": "message", "content": "Welcome!", "label": "Welcome Message", "active": True, "events": [{"id": "welcome-reply", "type": "reply", "intent": "yes", "nextStepID": None, "description": "Customer replied to welcome", "active": True, "parameters": {}}]}]}
            summary = validator.quick_validate(test_flow)
            health_response.components["validator"] = {
                "status": "healthy",
                "validation_enabled": settings.ENABLE_FLOW_VALIDATION,
                "auto_correction_enabled": settings.ENABLE_AUTO_CORRECTION,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            health_response.components["validator"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_response.status = "unhealthy"

        # Add system metrics
        health_response.metrics = get_system_metrics()

        # Add performance checks
        health_response.checks = get_performance_checks(start_time)

        # Determine overall status based on components
        component_statuses = [
            comp.get("status", "unknown")
            for comp in health_response.components.values()
        ]

        if "unhealthy" in component_statuses:
            health_response.status = "unhealthy"
        elif "degraded" in component_statuses:
            health_response.status = "degraded"

        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        health_response.metrics["response_time_ms"] = round(response_time, 2)

        # Set appropriate HTTP status code
        status_code = status.HTTP_200_OK
        if health_response.status == "unhealthy":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_response.status == "degraded":
            status_code = status.HTTP_200_OK  # Still serve traffic but indicate issues

        return JSONResponse(
            status_code=status_code,
            content=health_response.to_dict()
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION
            }
        )


@router.get(
    "/health/ready",
    summary="Readiness Check",
    description="Check if service is ready to handle requests",
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"}
    }
)
async def readiness_check(
    orchestrator: CampaignOrchestrator = Depends(get_campaign_orchestrator)
) -> Dict[str, Any]:
    """
    Readiness check for Kubernetes/containers.

    Checks if all critical dependencies are available and the service
    can handle requests successfully.
    """
    try:
        # Check critical components
        orchestrator_health = await orchestrator.health_check()

        if orchestrator_health.get("status") != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service dependencies not ready"
            )

        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "orchestrator": "healthy",
                "dependencies": "available"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@router.get(
    "/health/live",
    summary="Liveness Check",
    description="Check if service is alive and responding",
    responses={
        200: {"description": "Service is alive"},
        503: {"description": "Service is not alive"}
    }
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for Kubernetes/containers.

    Simple check to verify the service process is running and responsive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": time.time() - psutil.boot_time()
    }


@router.get(
    "/metrics",
    summary="Service Metrics",
    description="Get detailed service metrics and performance indicators"
)
async def get_metrics(
    orchestrator: CampaignOrchestrator = Depends(get_campaign_orchestrator)
) -> Dict[str, Any]:
    """Get comprehensive service metrics."""
    try:
        # Get orchestrator statistics
        orchestrator_stats = orchestrator.get_generation_statistics()

        # Get validation reporting statistics
        validation_reporter = get_validation_reporter()
        reports = validation_reporter.get_reports()

        # Get system metrics
        system_metrics = get_system_metrics()

        # Calculate validation statistics
        validation_stats = {
            "total_reports": len(reports),
            "average_quality_score": 0,
            "recent_reports": 0,
        }

        if reports:
            quality_scores = [report.quality_score for report in reports]
            validation_stats["average_quality_score"] = sum(quality_scores) / len(quality_scores)

            # Count recent reports (last 24 hours)
            now = datetime.now(timezone.utc)
            recent_cutoff = now.replace(hour=now.hour - 24)
            validation_stats["recent_reports"] = sum(
                1 for report in reports
                if report.created_at > recent_cutoff
            )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_metrics": orchestrator_stats,
            "validation_metrics": validation_stats,
            "system_metrics": system_metrics,
            "performance_metrics": get_performance_metrics()
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


def get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        memory = psutil.virtual_memory()

        # Disk metrics
        disk = psutil.disk_usage('/')

        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()

        return {
            "cpu": {
                "percent_used": cpu_percent,
                "count": cpu_count,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            },
            "memory": {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "percent_used": memory.percent,
                "process_rss_bytes": process_memory.rss,
                "process_vms_bytes": process_memory.vms
            },
            "disk": {
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "percent_used": (disk.used / disk.total) * 100
            }
        }
    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        return {"error": "Failed to collect system metrics"}


def get_performance_checks(start_time: float) -> Dict[str, Any]:
    """Get performance check results."""
    response_time = (time.time() - start_time) * 1000

    checks = {
        "response_time": {
            "value_ms": round(response_time, 2),
            "status": "healthy" if response_time < 1000 else "degraded"
        }
    }

    # Add memory check
    try:
        memory = psutil.virtual_memory()
        checks["memory_usage"] = {
            "value_percent": memory.percent,
            "status": "healthy" if memory.percent < 80 else "degraded"
        }
    except Exception:
        pass

    # Add CPU check
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        checks["cpu_usage"] = {
            "value_percent": cpu_percent,
            "status": "healthy" if cpu_percent < 80 else "degraded"
        }
    except Exception:
        pass

    return checks


def get_performance_metrics() -> Dict[str, Any]:
    """Get detailed performance metrics."""
    try:
        process = psutil.Process()

        return {
            "process": {
                "pid": process.pid,
                "create_time": process.create_time(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "connections": len(process.connections()),
            },
            "runtime_metrics": {
                "uptime_seconds:": time.time() - psutil.boot_time(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    except Exception as e:
        logger.warning(f"Failed to get performance metrics: {e}")
        return {"error": "Failed to collect performance metrics"}