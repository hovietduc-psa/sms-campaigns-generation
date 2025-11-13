"""
Campaign generation orchestrator.

This module coordinates the entire campaign generation process, from initial
request to final validated flow, including LLM integration, validation,
and auto-correction.

FIXED: Model reporting now uses self.llm_client.model instead of hardcoded settings.OPENAI_MODEL
"""

import time
import uuid
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow
from src.models.requests import CampaignGenerationRequest
from src.services.llm_engine.llm_client import get_llm_client
from src.services.llm_engine.prompt_builder import get_prompt_builder
from src.services.llm_engine.response_parser import get_response_parser
from src.services.validation.validator import get_validator, ValidationConfig
from src.services.validation.flowbuilder_schema import normalize_campaign_flow
from src.services.database.campaign_logger import get_database_logger

logger = get_logger(__name__)


class CampaignGenerationResult:
    """Result of campaign generation process."""

    def __init__(
        self,
        success: bool,
        flow_data: Optional[Dict[str, Any]] = None,
        campaign_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        errors: List[str] = None,
        warnings: List[str] = None,
        validation_summary: Optional[Any] = None,
    ):
        self.success = success
        self.flow_data = flow_data
        self.campaign_id = campaign_id or str(uuid.uuid4())
        self.metadata = metadata or {}
        self.errors = errors or []
        self.warnings = warnings or []
        self.validation_summary = validation_summary
        self.generated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "success": self.success,
            "campaign_id": self.campaign_id,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
        }

        if self.success and self.flow_data:
            result["initialStepID"] = self.flow_data.get("initialStepID")
            result["steps"] = self.flow_data.get("steps", [])
            result["validation"] = {
                "is_valid": self.validation_summary.is_valid if self.validation_summary else True,
                "total_issues": self.validation_summary.total_issues if self.validation_summary else 0,
                "corrections_applied": self.validation_summary.corrections_applied if self.validation_summary else 0,
            }
        else:
            result["errors"] = self.errors
            result["warnings"] = self.warnings

        return result


class CampaignOrchestrator:
    """
    Orchestrates the complete campaign generation process.

    Coordinates LLM generation, validation, auto-correction, and result
    formatting to provide a complete campaign generation service.
    """

    def __init__(self):
        """Initialize campaign orchestrator."""
        self.settings = get_settings()

        # Initialize components
        self.llm_client = get_llm_client()
        self.prompt_builder = get_prompt_builder()
        self.response_parser = get_response_parser()
        self.validator = get_validator()

        # Configure validation
        validation_config = ValidationConfig(
            enable_schema_validation=self.settings.ENABLE_FLOW_VALIDATION,
            enable_flow_validation=self.settings.ENABLE_FLOW_VALIDATION,
            enable_auto_correction=self.settings.ENABLE_AUTO_CORRECTION,
            auto_correction_risk_threshold="medium",
            strict_mode=False,
            max_validation_time_ms=30000,
        )
        self.validator.update_config(**validation_config.__dict__)

        # Get the correct model based on provider
        if self.settings.LLM_PROVIDER.lower() == "openrouter":
            llm_model = self.settings.OPENROUTER_MODEL
        else:
            llm_model = self.settings.OPENAI_MODEL

        # Initialize database logger
        self.db_logger = get_database_logger()

        logger.info(
            "Campaign orchestrator initialized",
            extra={
                "llm_model": llm_model,
                "validation_enabled": self.settings.ENABLE_FLOW_VALIDATION,
                "auto_correction_enabled": self.settings.ENABLE_AUTO_CORRECTION,
                "database_logging_enabled": self.db_logger.is_enabled(),
            }
        )

    async def generate_campaign(
        self,
        request: CampaignGenerationRequest,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> CampaignGenerationResult:
        """
        Generate a complete campaign flow.

        Args:
            request: Campaign generation request
            request_id: Optional request ID for tracking
            user_id: Optional user ID for tracking

        Returns:
            CampaignGenerationResult with complete flow and metadata
        """
        start_time = time.time()
        request_id = request_id or str(uuid.uuid4())

        logger.info(
            "Starting campaign generation",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "campaign_description": request.campaignDescription,
                "description_length": len(request.campaignDescription),
            }
        )

        try:
            # Step 1: Analyze campaign complexity
            complexity = self._analyze_complexity(request.campaignDescription)

            # Step 2: Generate prompt
            system_prompt, user_prompt = await self.prompt_builder.build_prompt(
                campaign_description=request.campaignDescription,
                complexity_level=complexity,
                include_examples=True,
                max_examples=2,
            )

            logger.info(
                "Prompt built successfully",
                extra={
                    "request_id": request_id,
                    "complexity": complexity,
                    "system_prompt_length": len(system_prompt),
                    "user_prompt_length": len(user_prompt),
                }
            )

            # Step 3: Generate LLM response
            raw_response = await self.llm_client.generate_json(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=self.settings.OPENAI_MAX_TOKENS,
                temperature=self.settings.OPENAI_TEMPERATURE,
            )

            generation_time = (time.time() - start_time) * 1000

            logger.info(
                "LLM response generated",
                extra={
                    "request_id": request_id,
                    "generation_time_ms": round(generation_time, 2),
                    "model_used": self.llm_client.model,
                }
            )

            # Step 4: Parse response
            # Handle both dict (from OpenRouter) and string (from OpenAI) responses
            if isinstance(raw_response, dict):
                # Apply FlowBuilder schema normalization first
                try:
                    flowbuilder_result = normalize_campaign_flow(raw_response)
                    normalized_response = flowbuilder_result["flow"]

                    logger.info(
                        "FlowBuilder schema normalization applied in orchestrator",
                        extra={
                            "fb_errors": flowbuilder_result["validation"]["error_count"],
                            "fb_warnings": flowbuilder_result["validation"]["warning_count"],
                            "fb_is_valid": flowbuilder_result["validation"]["is_valid"]
                        }
                    )
                except Exception as fb_error:
                    logger.warning(f"FlowBuilder schema normalization failed: {fb_error}")
                    normalized_response = raw_response

                # Try direct parsing first
                try:
                    campaign_flow = CampaignFlow(**normalized_response)
                    parse_metadata = {
                        "original_length": len(str(raw_response)),
                        "cleaning_steps": ["flowbuilder_normalization"],
                        "repair_attempts": 0,
                        "validation_errors": [],
                        "response_type": "parsed_json"
                    }
                except Exception as validation_error:
                    # If direct validation fails, try schema transformation
                    logger.warning(f"Direct validation failed, attempting schema transformation: {validation_error}")
                    try:
                        from src.services.llm_engine.schema_transformer import get_schema_transformer
                        transformer = get_schema_transformer()
                        campaign_flow = transformer.transform_to_campaign_flow(raw_response)
                        parse_metadata = {
                            "original_length": len(str(raw_response)),
                            "cleaning_steps": ["schema_transformation"],
                            "repair_attempts": 1,
                            "validation_errors": [str(validation_error)],
                            "response_type": "transformed_json"
                        }
                        logger.info("Schema transformation successful")
                    except Exception as transform_error:
                        logger.error(f"Schema transformation also failed: {transform_error}")
                        raise Exception(f"Campaign generation failed: Schema validation and transformation both failed. Validation error: {validation_error}. Transformation error: {transform_error}")
            else:
                # Parse string response (from OpenAI or other providers)
                campaign_flow, parse_metadata = self.response_parser.parse_response(
                    raw_response,
                    strict_mode=False,
                    attempt_repair=True,
                )

            parsing_time = (time.time() - start_time) * 1000

            logger.info(
                "LLM response parsed",
                extra={
                    "request_id": request_id,
                    "parsing_time_ms": round(parsing_time, 2),
                    "node_count": len(campaign_flow.steps),
                    "flow_complexity": parse_metadata.get("flow_complexity", "unknown"),
                }
            )

            # Step 5: Validate and auto-correct
            validation_start = time.time()

            # If we have a CampaignFlow object (from schema transformation), use validate_flow_object
            # Otherwise, convert to dict and use validate_flow
            if isinstance(campaign_flow, CampaignFlow):
                validation_summary = self.validator.validate_flow_object(
                    campaign_flow=campaign_flow,
                    apply_corrections=self.settings.ENABLE_AUTO_CORRECTION,
                )
            else:
                # campaign_flow is now a dict from optimized ResponseParser
                if isinstance(campaign_flow, dict):
                    flow_data = campaign_flow
                else:
                    flow_data = campaign_flow.dict() if hasattr(campaign_flow, 'dict') else campaign_flow.model_dump()
                validation_summary = self.validator.validate_flow(
                    flow_data=flow_data,
                    apply_corrections=self.settings.ENABLE_AUTO_CORRECTION,
                    raise_on_error=False,
                )

            validation_time = (time.time() - validation_start) * 1000
            total_time = (time.time() - start_time) * 1000

            # Step 6: Build result
            result = self._build_result(
                success=validation_summary.is_valid,
                flow_data=validation_summary.flow_data,
                campaign_id=f"campaign_{request_id[:8]}",
                metadata={
                    "request_id": request_id,
                    "user_id": user_id,
                    "campaign_description": request.campaignDescription,
                    "complexity": complexity,
                    "priority": request.priority,
                    "maxLength": request.maxLength,
                    "model_used": self.llm_client.model,
                    "generation_time_ms": round(generation_time, 2),
                    "parsing_time_ms": round(parsing_time - generation_time, 2),
                    "validation_time_ms": round(validation_time, 2),
                    "total_time_ms": round(total_time, 2),
                    "initial_node_count": len(campaign_flow.steps),
                    "final_node_count": len(validation_summary.flow_data.get("steps", [])),
                    "parse_metadata": parse_metadata,
                },
                warnings=self._extract_warnings(validation_summary),
                validation_summary=validation_summary,
            )

            if validation_summary.is_valid:
                logger.info(
                    "Campaign generation completed successfully",
                    extra={
                        "request_id": request_id,
                        "campaign_id": result.campaign_id,
                        "total_time_ms": total_time,
                        "node_count": len(result.flow_data.get("steps", [])),
                        "validation_issues": validation_summary.total_issues,
                        "corrections_applied": validation_summary.corrections_applied,
                    }
                )
            else:
                logger.warning(
                    "Campaign generation completed with validation errors",
                    extra={
                        "request_id": request_id,
                        "campaign_id": result.campaign_id,
                        "total_time_ms": total_time,
                        "error_count": validation_summary.error_count,
                        "warning_count": validation_summary.warning_count,
                    }
                )

            # Log campaign to database asynchronously (non-blocking)
            asyncio.create_task(
                self.db_logger.log_campaign_generation(
                    campaign_id=result.campaign_id,
                    request_id=request_id,
                    user_id=user_id,
                    campaign_description=request.campaignDescription,
                    generated_flow=result.flow_data if result.flow_data else {},
                    generation_time_ms=int(total_time),
                    tokens_used=result.metadata.get("parse_metadata", {}).get("parsing_metadata", {}).get("tokens_used", 0) if result.metadata else 0,
                    model_used=result.metadata.get("model_used", self.llm_client.model) if result.metadata else self.llm_client.model,
                    status="success" if validation_summary.is_valid else "partial",
                    error_message=None if validation_summary.is_valid else f"Validation issues: {validation_summary.error_count} errors, {validation_summary.warning_count} warnings",
                    node_count=len(result.flow_data.get("steps", [])) if result.flow_data else 0,
                    validation_issues=validation_summary.total_issues,
                    corrections_applied=validation_summary.corrections_applied,
                    quality_score=validation_summary.quality_score if hasattr(validation_summary, 'quality_score') else None,
                )
            )

            return result

        except Exception as e:
            total_time = (time.time() - start_time) * 1000

            logger.error(
                "Campaign generation failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "total_time_ms": total_time,
                },
                exc_info=True
            )

            # Log failed campaign to database asynchronously (non-blocking)
            error_result = CampaignGenerationResult(
                success=False,
                errors=[f"Campaign generation failed: {str(e)}"],
                metadata={
                    "request_id": request_id,
                    "user_id": user_id,
                    "campaign_description": request.campaignDescription,
                    "total_time_ms": total_time,
                    "error_type": type(e).__name__,
                }
            )

            # Generate campaign ID for failed attempt
            failed_campaign_id = f"failed_{request_id}_{int(time.time())}"

            asyncio.create_task(
                self.db_logger.log_campaign_generation(
                    campaign_id=failed_campaign_id,
                    request_id=request_id,
                    user_id=user_id,
                    campaign_description=request.campaignDescription,
                    generated_flow={},  # Empty flow for failed attempts
                    generation_time_ms=int(total_time),
                    tokens_used=0,
                    model_used=getattr(self.llm_client, 'model', 'unknown'),
                    status="error",
                    error_message=str(e),
                    node_count=0,
                    validation_issues=0,
                    corrections_applied=0,
                    quality_score=None,
                )
            )

            return error_result

    def _analyze_complexity(self, description: str) -> str:
        """Analyze campaign description to determine expected complexity."""
        description_lower = description.lower()

        # Count complexity indicators
        complexity_indicators = {
            "simple": 0,
            "medium": 0,
            "complex": 0,
        }

        # Simple indicators
        if any(word in description_lower for word in ["simple", "basic", "quick"]):
            complexity_indicators["simple"] += 1
        if len(description.split()) < 10:
            complexity_indicators["simple"] += 1

        # Medium indicators
        if any(word in description_lower for word in ["nurture", "follow", "sequence", "series"]):
            complexity_indicators["medium"] += 1
        if any(word in description_lower for word in ["segment", "branch", "condition"]):
            complexity_indicators["medium"] += 1
        if len(description.split()) >= 10 and len(description.split()) < 20:
            complexity_indicators["medium"] += 1

        # Complex indicators
        if any(word in description_lower for word in ["abandoned", "cart", "purchase", "experiment", "test"]):
            complexity_indicators["complex"] += 1
        if any(word in description_lower for word in ["multiple", "several", "various", "different"]):
            complexity_indicators["complex"] += 1
        if len(description.split()) >= 20:
            complexity_indicators["complex"] += 1

        # Determine complexity based on indicators
        if complexity_indicators["complex"] > 0:
            return "complex"
        elif complexity_indicators["medium"] > complexity_indicators["simple"]:
            return "medium"
        else:
            return "simple"

    def _extract_warnings(self, validation_summary: Any) -> List[str]:
        """Extract warnings from validation summary."""
        warnings = []

        if hasattr(validation_summary, 'issues'):
            for issue in validation_summary.issues:
                if hasattr(issue, 'severity') and issue.severity == "warning":
                    warnings.append(issue.message)

        return warnings

    def _build_result(
        self,
        success: bool,
        flow_data: Dict[str, Any],
        campaign_id: str,
        metadata: Dict[str, Any],
        warnings: List[str],
        validation_summary: Any,
    ) -> CampaignGenerationResult:
        """Build campaign generation result."""
        return CampaignGenerationResult(
            success=success,
            flow_data=flow_data if success else None,
            campaign_id=campaign_id,
            metadata=metadata,
            warnings=warnings,
            validation_summary=validation_summary,
        )

    async def generate_campaign_batch(
        self,
        requests: List[CampaignGenerationRequest],
        user_id: Optional[str] = None,
    ) -> List[CampaignGenerationResult]:
        """
        Generate multiple campaigns in batch.

        Args:
            requests: List of campaign generation requests
            user_id: Optional user ID for tracking

        Returns:
            List of campaign generation results
        """
        logger.info(
            "Starting batch campaign generation",
            extra={
                "user_id": user_id,
                "batch_size": len(requests),
            }
        )

        results = []
        for i, request in enumerate(requests):
            try:
                result = await self.generate_campaign(
                    request=request,
                    request_id=f"batch_{user_id}_{i}",
                    user_id=user_id,
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to generate campaign {i} in batch",
                    extra={
                        "batch_index": i,
                        "error": str(e),
                        "user_id": user_id,
                    },
                    exc_info=True
                )
                results.append(CampaignGenerationResult(
                    success=False,
                    errors=[f"Batch generation failed: {str(e)}"],
                    metadata={
                        "batch_index": i,
                        "user_id": user_id,
                    }
                ))

        success_count = sum(1 for result in results if result.success)
        logger.info(
            "Batch campaign generation completed",
            extra={
                "user_id": user_id,
                "batch_size": len(requests),
                "success_count": success_count,
                "failure_count": len(requests) - success_count,
            }
        )

        return results

    def get_generation_statistics(self) -> Dict[str, Any]:
        """Get generation statistics and performance metrics."""
        # Get the correct model and settings based on provider
        if self.settings.LLM_PROVIDER.lower() == "openrouter":
            llm_model = self.settings.OPENROUTER_MODEL
            max_tokens = self.settings.OPENROUTER_MAX_TOKENS
            temperature = self.settings.OPENROUTER_TEMPERATURE
        else:
            llm_model = self.settings.OPENAI_MODEL
            max_tokens = self.settings.OPENAI_MAX_TOKENS
            temperature = self.settings.OPENAI_TEMPERATURE

        return {
            "orchestrator_status": "active",
            "llm_model": llm_model,
            "validation_enabled": self.settings.ENABLE_FLOW_VALIDATION,
            "auto_correction_enabled": self.settings.ENABLE_AUTO_CORRECTION,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of all components."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
        }

        try:
            # Check LLM client
            try:
                # Simple test call
                await self.llm_client.estimate_tokens("test")
                health_status["components"]["llm_client"] = "healthy"
            except Exception as e:
                health_status["components"]["llm_client"] = f"unhealthy: {e}"
                health_status["status"] = "degraded"

            # Check prompt builder
            try:
                system_prompt, user_prompt = self.prompt_builder.build_prompt(
                    campaign_description="test campaign",
                    complexity_level="simple",
                )
                health_status["components"]["prompt_builder"] = "healthy"
            except Exception as e:
                health_status["components"]["prompt_builder"] = f"unhealthy: {e}"
                health_status["status"] = "degraded"

            # Check response parser
            try:
                test_json = '{"initialStepID": "welcome-step", "steps": [{"id": "welcome-step", "type": "message", "content": "Welcome!", "label": "Welcome Message", "active": true, "events": [{"id": "welcome-reply", "type": "reply", "intent": "yes", "nextStepID": null, "description": "Customer replied to welcome", "active": true, "parameters": {}}]}]}'
                parsed_flow, metadata = self.response_parser.parse_response(test_json)
                health_status["components"]["response_parser"] = "healthy"
            except Exception as e:
                health_status["components"]["response_parser"] = f"unhealthy: {e}"
                health_status["status"] = "degraded"

            # Check validator
            try:
                test_flow = {"initialStepID": "welcome-step", "steps": [{"id": "welcome-step", "type": "message", "content": "Welcome!", "label": "Welcome Message", "active": True, "events": [{"id": "welcome-reply", "type": "reply", "intent": "yes", "nextStepID": None, "description": "Customer replied to welcome", "active": True, "parameters": {}}]}]}
                summary = self.validator.quick_validate(test_flow)
                health_status["components"]["validator"] = "healthy"
            except Exception as e:
                health_status["components"]["validator"] = f"unhealthy: {e}"
                health_status["status"] = "degraded"

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status


# Global orchestrator instance
_orchestrator: Optional[CampaignOrchestrator] = None


def get_campaign_orchestrator() -> CampaignOrchestrator:
    """Get global campaign orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CampaignOrchestrator()
    return _orchestrator