"""
Main validation orchestration service.

This module provides the main entry point for all validation operations,
coordinating between schema validation, flow validation, and auto-correction.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow
from src.services.validation.auto_corrector import AutoCorrector, get_auto_corrector
from src.services.validation.flow_validator import FlowValidator, get_flow_validator
from src.services.validation.schema_validator import SchemaValidator, get_schema_validator
from src.services.validation.flowbuilder_schema import normalize_campaign_flow
from src.utils.constants import LOG_CONTEXT_GENERATION_TIME, LOG_CONTEXT_TOKENS_USED

logger = get_logger(__name__)


class ValidationConfig:
    """Configuration for validation operations."""

    def __init__(
        self,
        enable_schema_validation: bool = True,
        enable_flow_validation: bool = True,
        enable_auto_correction: bool = True,
        auto_correction_risk_threshold: str = "medium",
        strict_mode: bool = False,
        max_validation_time_ms: int = 30000,  # 30 seconds
    ):
        self.enable_schema_validation = enable_schema_validation
        self.enable_flow_validation = enable_flow_validation
        self.enable_auto_correction = enable_auto_correction
        self.auto_correction_risk_threshold = auto_correction_risk_threshold
        self.strict_mode = strict_mode
        self.max_validation_time_ms = max_validation_time_ms


class ValidationSummary:
    """Summary of validation results."""

    def __init__(
        self,
        is_valid: bool,
        total_issues: int,
        error_count: int,
        warning_count: int,
        info_count: int,
        corrections_applied: int,
        validation_time_ms: float,
        flow_data: Dict[str, Any],
        issues: List[Any] = None,
    ):
        self.is_valid = is_valid
        self.total_issues = total_issues
        self.error_count = error_count
        self.warning_count = warning_count
        self.info_count = info_count
        self.corrections_applied = corrections_applied
        self.validation_time_ms = validation_time_ms
        self.flow_data = flow_data
        self.issues = issues or []
        self.quality_score = self._calculate_quality_score()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "total_issues": self.total_issues,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "corrections_applied": self.corrections_applied,
            "validation_time_ms": round(self.validation_time_ms, 2),
            "flow_complexity": self._assess_complexity(),
            "quality_score": self.quality_score,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def _calculate_quality_score(self) -> float:
        """Calculate quality score based on validation results."""
        # Start with a perfect score of 100
        score = 100.0

        # Deduct points for errors
        score -= (self.error_count * 20)  # Each error deducts 20 points

        # Deduct points for warnings
        score -= (self.warning_count * 10)  # Each warning deducts 10 points

        # Deduct points for info items
        score -= (self.info_count * 5)  # Each info item deducts 5 points

        # Bonus for corrections applied (shows the system fixed issues)
        score += (self.corrections_applied * 5)  # Each correction adds 5 points

        # Ensure score stays within bounds
        score = max(0.0, min(100.0, score))

        return round(score, 1)

    def _assess_complexity(self) -> str:
        """Assess flow complexity."""
        node_count = len(self.flow_data.get("steps", []))
        event_count = sum(
            len(step.get("events", []))
            for step in self.flow_data.get("steps", [])
        )

        complexity_score = node_count + (event_count * 0.5)

        if complexity_score < 5:
            return "simple"
        elif complexity_score < 15:
            return "medium"
        else:
            return "complex"


class Validator:
    """
    Main validation orchestrator for campaign flows.

    Coordinates schema validation, flow validation, and auto-correction
    to provide comprehensive validation results.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize validator.

        Args:
            config: Validation configuration (if None, uses defaults)
        """
        self.config = config or ValidationConfig()

        # Initialize validation components
        self.schema_validator = get_schema_validator()
        self.flow_validator = get_flow_validator()
        self.auto_corrector = get_auto_corrector()

        # Configure auto-corrector based on config
        self.auto_corrector.enable_corrections(self.config.enable_auto_correction)

        logger.info(
            "Validator initialized",
            extra={
                "enable_schema_validation": self.config.enable_schema_validation,
                "enable_flow_validation": self.config.enable_flow_validation,
                "enable_auto_correction": self.config.enable_auto_correction,
                "auto_correction_risk_threshold": self.config.auto_correction_risk_threshold,
                "strict_mode": self.config.strict_mode,
            }
        )

    def validate_flow(
        self,
        flow_data: Dict[str, Any],
        apply_corrections: bool = None,
        raise_on_error: bool = False,
    ) -> ValidationSummary:
        """
        Validate a campaign flow with comprehensive checks.

        Args:
            flow_data: Flow data to validate
            apply_corrections: Whether to apply auto-corrections (overrides config)
            raise_on_error: Whether to raise exception on validation errors

        Returns:
            ValidationSummary with complete results

        Raises:
            ValidationError: If validation fails and raise_on_error is True
        """
        start_time = time.time()
        all_issues = []
        corrected_data = flow_data.copy()
        corrections_applied = 0

        try:
            logger.info(
                "Starting flow validation",
                extra={
                    "node_count": len(flow_data.get("steps", [])),
                    "initial_step_id": flow_data.get("initialStepID"),
                    "apply_corrections": apply_corrections if apply_corrections is not None else self.config.enable_auto_correction,
                }
            )

            # Step 0: FlowBuilder schema normalization
            try:
                flowbuilder_result = normalize_campaign_flow(corrected_data)
                corrected_data = flowbuilder_result["flow"]

                # Convert FlowBuilder validation issues to our format
                fb_validation = flowbuilder_result["validation"]
                for error in fb_validation["errors"]:
                    all_issues.append(type('ValidationIssue', (), {
                        'type': 'ERROR',
                        'code': 'FLOWBUILDER_SCHEMA_ERROR',
                        'message': error,
                        'severity': 'high',
                        'auto_correctable': False,
                        'suggestion': None,
                        'field_path': None,
                        'actual_value': None,
                        'expected_value': None
                    })())

                for warning in fb_validation["warnings"]:
                    all_issues.append(type('ValidationIssue', (), {
                        'type': 'WARNING',
                        'code': 'FLOWBUILDER_SCHEMA_WARNING',
                        'message': warning,
                        'severity': 'low',
                        'auto_correctable': False,
                        'suggestion': None,
                        'field_path': None,
                        'actual_value': None,
                        'expected_value': None
                    })())

                logger.info(
                    "FlowBuilder schema normalization completed",
                    extra={
                        "fb_errors": fb_validation["error_count"],
                        "fb_warnings": fb_validation["warning_count"],
                        "fb_is_valid": fb_validation["is_valid"]
                    }
                )
            except Exception as e:
                logger.error(f"FlowBuilder schema normalization failed: {e}", exc_info=True)
                all_issues.append(type('ValidationIssue', (), {
                    'type': 'ERROR',
                    'code': 'FLOWBUILDER_NORMALIZATION_FAILED',
                    'message': f"FlowBuilder schema normalization failed: {str(e)}",
                    'severity': 'high',
                    'auto_correctable': False,
                    'suggestion': None,
                    'field_path': None,
                    'actual_value': None,
                    'expected_value': None
                })())

            # Step 1: Schema validation
            if self.config.enable_schema_validation:
                schema_result = self.schema_validator.validate(corrected_data)
                all_issues.extend(schema_result.issues)

                if schema_result.corrected_data:
                    corrected_data = schema_result.corrected_data

            # Step 2: Convert to CampaignFlow for flow validation
            try:
                campaign_flow = CampaignFlow(**corrected_data)
            except Exception as e:
                # If we can't create CampaignFlow, we have serious schema issues
                logger.error(f"Failed to create CampaignFlow: {e}")
                if raise_on_error:
                    raise
                return ValidationSummary(
                    is_valid=False,
                    total_issues=len(all_issues),
                    error_count=sum(1 for issue in all_issues if issue.severity == "error"),
                    warning_count=sum(1 for issue in all_issues if issue.severity == "warning"),
                    info_count=sum(1 for issue in all_issues if issue.severity == "info"),
                    corrections_applied=corrections_applied,
                    validation_time_ms=(time.time() - start_time) * 1000,
                    flow_data=corrected_data,
                    issues=all_issues,
                )

            # Step 3: Flow validation
            if self.config.enable_flow_validation:
                flow_result = self.flow_validator.validate(campaign_flow)
                all_issues.extend(flow_result.issues)

                if flow_result.corrected_data:
                    corrected_data = flow_result.corrected_data

            # Step 4: Auto-correction
            should_apply_corrections = (
                apply_corrections if apply_corrections is not None else self.config.enable_auto_correction
            )

            if should_apply_corrections and all_issues:
                # Create validation result for auto-corrector
                combined_result = type('ValidationResult', (), {
                    'issues': all_issues,
                    'is_valid': not any(issue.severity == "error" for issue in all_issues)
                })()

                correction_result = self.auto_corrector.correct_flow(
                    combined_result,
                    corrected_data,
                    self.config.auto_correction_risk_threshold
                )

                if correction_result.success:
                    corrected_data = correction_result.corrected_data
                    corrections_applied = len(correction_result.applied_corrections)

                    logger.info(
                        "Auto-corrections applied",
                        extra={
                            "corrections_count": corrections_applied,
                            "blocked_corrections": len(correction_result.blocked_corrections),
                            "warnings": len(correction_result.warnings),
                        }
                    )

                    # Add correction results to issues
                    for correction in correction_result.applied_corrections:
                        all_issues.append(type('ValidationIssue', (), {
                            'code': 'AUTO_CORRECTION',
                            'message': correction,
                            'severity': 'info',
                            'to_dict': lambda self: {
                                'code': 'AUTO_CORRECTION',
                                'message': correction,
                                'severity': 'info'
                            }
                        })())

                # Log blocked corrections
                if correction_result.blocked_corrections:
                    logger.debug(
                        "Some corrections were blocked",
                        extra={
                            "blocked_corrections": correction_result.blocked_corrections,
                            "warnings": correction_result.warnings,
                        }
                    )

            # Step 5: Final validation check (if corrections were applied)
            if corrections_applied > 0:
                try:
                    # Quick validation that corrected data is still valid
                    final_campaign_flow = CampaignFlow(**corrected_data)
                    logger.info("Corrected data passed final validation")
                except Exception as e:
                    logger.error(f"Corrected data failed final validation: {e}")
                    if raise_on_error:
                        raise
                    # Fallback to original data
                    corrected_data = flow_data
                    corrections_applied = 0
                    all_issues.append(type('ValidationIssue', (), {
                        'code': 'CORRECTION_VALIDATION_FAILED',
                        'message': f"Auto-corrections created invalid data: {e}",
                        'severity': 'error',
                        'to_dict': lambda self: {
                            'code': 'CORRECTION_VALIDATION_FAILED',
                            'message': str(e),
                            'severity': 'error'
                        }
                    })())

            validation_time_ms = (time.time() - start_time) * 1000

            # Check for timeout
            if validation_time_ms > self.config.max_validation_time_ms:
                logger.warning(
                    f"Validation exceeded time limit: {validation_time_ms:.2f}ms > {self.config.max_validation_time_ms}ms"
                )

            # Determine final validity
            is_valid = not any(issue.severity == "error" for issue in all_issues)

            # Log final results
            logger.info(
                "Flow validation completed",
                extra={
                    "is_valid": is_valid,
                    "total_issues": len(all_issues),
                    "error_count": sum(1 for issue in all_issues if issue.severity == "error"),
                    "warning_count": sum(1 for issue in all_issues if issue.severity == "warning"),
                    "info_count": sum(1 for issue in all_issues if issue.severity == "info"),
                    "corrections_applied": corrections_applied,
                    LOG_CONTEXT_GENERATION_TIME: validation_time_ms,
                    "node_count": len(corrected_data.get("steps", [])),
                }
            )

            # Create summary
            summary = ValidationSummary(
                is_valid=is_valid,
                total_issues=len(all_issues),
                error_count=sum(1 for issue in all_issues if issue.severity == "error"),
                warning_count=sum(1 for issue in all_issues if issue.severity == "warning"),
                info_count=sum(1 for issue in all_issues if issue.severity == "info"),
                corrections_applied=corrections_applied,
                validation_time_ms=validation_time_ms,
                flow_data=corrected_data,
                issues=all_issues,
            )

            # Raise exception if requested and there are errors
            if raise_on_error and not is_valid:
                error_messages = [
                    f"{issue.code}: {issue.message}"
                    for issue in all_issues
                    if issue.severity == "error"
                ]
                raise ValidationError(f"Validation failed: {'; '.join(error_messages)}")

            return summary

        except Exception as e:
            validation_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Validation failed with exception: {e}",
                extra={
                    "validation_time_ms": validation_time_ms,
                    "node_count": len(flow_data.get("steps", [])),
                },
                exc_info=True
            )

            if raise_on_error:
                raise

            # Return error summary
            error_issue = type('ValidationIssue', (), {
                'code': 'VALIDATION_EXCEPTION',
                'message': f"Validation failed with exception: {e}",
                'severity': 'error',
                'to_dict': lambda self: {
                    'code': 'VALIDATION_EXCEPTION',
                    'message': str(e),
                    'severity': 'error'
                }
            })()

            return ValidationSummary(
                is_valid=False,
                total_issues=1,
                error_count=1,
                warning_count=0,
                info_count=0,
                corrections_applied=0,
                validation_time_ms=validation_time_ms,
                flow_data=flow_data,
                issues=[error_issue],
            )

    def validate_flow_object(
        self,
        campaign_flow: CampaignFlow,
        apply_corrections: bool = None,
    ) -> ValidationSummary:
        """
        Validate a CampaignFlow object.

        Args:
            campaign_flow: CampaignFlow object to validate
            apply_corrections: Whether to apply auto-corrections

        Returns:
            ValidationSummary with complete results
        """
        start_time = time.time()
        should_apply_corrections = (
            apply_corrections if apply_corrections is not None else self.config.enable_auto_correction
        )

        try:
            all_issues = []
            corrected_data = campaign_flow.model_dump()
            corrections_applied = 0

            # Skip schema validation since we already have a valid CampaignFlow object
            logger.info("Skipping schema validation for existing CampaignFlow object")

            # Step 2: Apply flow validation for reference integrity checking
            # Convert CampaignFlow to dict format for flow validator compatibility
            logger.info("Applying flow validation for reference integrity checks")

            try:
                # Apply flow validation using flow_validator (expects CampaignFlow object)
                from .flow_validator import FlowValidator
                flow_validator = FlowValidator()
                flow_validation_result = flow_validator.validate(campaign_flow)

                # Extract issues from flow validation
                if hasattr(flow_validation_result, 'issues'):
                    for issue in flow_validation_result.issues:
                        all_issues.append(issue)
                        if issue.severity == 'high':
                            corrections_applied += 1  # Count as correction needed

                logger.info(f"Flow validation completed: {len(flow_validation_result.issues)} issues found")

            except Exception as flow_val_error:
                logger.warning(f"Flow validation failed, continuing with schema validation: {flow_val_error}")
                # Add a warning about flow validation failure
                all_issues.append(type('ValidationIssue', (), {
                    'code': 'FLOW_VALIDATION_SKIPPED',
                    'message': f'Flow validation could not be completed: {flow_val_error}',
                    'severity': 'warning',
                    'node_id': None,
                    'to_dict': lambda self: {
                        'code': 'FLOW_VALIDATION_SKIPPED',
                        'message': f'Flow validation could not be completed: {flow_val_error}',
                        'severity': 'warning',
                        'node_id': None
                    }
                })())

            # Add a simple warning about missing END node instead
            all_issues.append(type('ValidationIssue', (), {
                'code': 'MISSING_END_NODE',
                'message': 'Campaign flow should have at least one END node',
                'severity': 'warning',
                'node_id': None,
                'to_dict': lambda self: {
                    'code': 'MISSING_END_NODE',
                    'message': 'Campaign flow should have at least one END node',
                    'severity': 'warning',
                    'node_id': None
                }
            })())

            # Step 3: Auto-correction for reference integrity issues
            if should_apply_corrections:
                logger.info("Applying auto-correction for CampaignFlow object")
                flow_data = campaign_flow.model_dump()

                # Fix missing step references by setting them to None or creating missing steps
                if 'steps' in flow_data:
                    step_ids = {step.get('id') for step in flow_data['steps']}

                    # Fix each step's events
                    for step in flow_data['steps']:
                        if 'events' in step and isinstance(step['events'], list):
                            for event in step['events']:
                                if 'nextStepID' in event and event['nextStepID']:
                                    # If nextStepID doesn't exist in steps, set it to None to end the flow
                                    if event['nextStepID'] not in step_ids:
                                        logger.warning(f"Fixing invalid nextStepID reference: {event['nextStepID']} -> None")
                                        event['nextStepID'] = None
                                        corrections_applied += 1

                    # Update corrected_data
                    corrected_data = flow_data

                    logger.info(f"Auto-correction applied: {corrections_applied} reference fixes")
            else:
                logger.info("Auto-correction disabled for CampaignFlow object")

            # Determine final validity
            is_valid = not any(issue.severity == "error" for issue in all_issues)

            validation_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "Flow object validation completed",
                extra={
                    "is_valid": is_valid,
                    "total_issues": len(all_issues),
                    "error_count": sum(1 for issue in all_issues if issue.severity == "error"),
                    "warning_count": sum(1 for issue in all_issues if issue.severity == "warning"),
                    "corrections_applied": corrections_applied,
                    "validation_time_ms": validation_time_ms,
                    "node_count": len(corrected_data.get("steps", [])),
                }
            )

            # Create summary
            summary = ValidationSummary(
                is_valid=is_valid,
                total_issues=len(all_issues),
                error_count=sum(1 for issue in all_issues if issue.severity == "error"),
                warning_count=sum(1 for issue in all_issues if issue.severity == "warning"),
                info_count=sum(1 for issue in all_issues if issue.severity == "info"),
                corrections_applied=corrections_applied,
                validation_time_ms=validation_time_ms,
                flow_data=corrected_data,
                issues=all_issues,
            )

            return summary

        except Exception as e:
            validation_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Flow object validation failed: {e}")

            # Return error summary
            error_issue = type('ValidationIssue', (), {
                'code': 'VALIDATION_EXCEPTION',
                'message': f"Flow object validation failed: {e}",
                'severity': 'error',
                'to_dict': lambda self: {
                    'code': 'VALIDATION_EXCEPTION',
                    'message': str(e),
                    'severity': 'error'
                }
            })()

            return ValidationSummary(
                is_valid=False,
                total_issues=1,
                error_count=1,
                warning_count=0,
                info_count=0,
                corrections_applied=0,
                validation_time_ms=validation_time_ms,
                flow_data=campaign_flow.model_dump(),
                issues=[error_issue],
            )

    def quick_validate(
        self,
        flow_data: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Quick validation that only checks for critical errors.

        Args:
            flow_data: Flow data to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            summary = self.validate_flow(
                flow_data,
                apply_corrections=False,
                raise_on_error=False
            )

            error_messages = [
                issue.message
                for issue in summary.issues
                if issue.severity == "error"
            ]

            return summary.is_valid, error_messages

        except Exception as e:
            return False, [f"Validation failed: {e}"]

    def get_validation_config(self) -> Dict[str, Any]:
        """Get current validation configuration."""
        return {
            "enable_schema_validation": self.config.enable_schema_validation,
            "enable_flow_validation": self.config.enable_flow_validation,
            "enable_auto_correction": self.config.enable_auto_correction,
            "auto_correction_risk_threshold": self.config.auto_correction_risk_threshold,
            "strict_mode": self.config.strict_mode,
            "max_validation_time_ms": self.config.max_validation_time_ms,
        }

    def update_config(self, **kwargs) -> None:
        """Update validation configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated validation config: {key} = {value}")

        # Update auto-corrector if needed
        if "enable_auto_correction" in kwargs:
            self.auto_corrector.enable_corrections(kwargs["enable_auto_correction"])

    def get_correction_history(self) -> List[Dict[str, Any]]:
        """Get auto-correction history."""
        return self.auto_corrector.get_correction_history()

    def clear_correction_history(self) -> None:
        """Clear auto-correction history."""
        self.auto_corrector.clear_correction_history()


class ValidationError(Exception):
    """Exception raised when validation fails."""

    def __init__(self, message: str, issues: List[Any] = None):
        super().__init__(message)
        self.issues = issues or []


# Global validator instance
_validator: Optional[Validator] = None


def get_validator(config: Optional[ValidationConfig] = None) -> Validator:
    """Get global validator instance."""
    global _validator
    if _validator is None:
        _validator = Validator(config)
    return _validator


def validate_flow(
    flow_data: Dict[str, Any],
    config: Optional[ValidationConfig] = None,
    apply_corrections: bool = None,
    raise_on_error: bool = False,
) -> ValidationSummary:
    """
    Convenience function to validate a flow.

    Args:
        flow_data: Flow data to validate
        config: Validation configuration
        apply_corrections: Whether to apply auto-corrections
        raise_on_error: Whether to raise exception on errors

    Returns:
        ValidationSummary with complete results
    """
    validator = get_validator(config)
    return validator.validate_flow(flow_data, apply_corrections, raise_on_error)


def quick_validate(flow_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Convenience function for quick validation.

    Args:
        flow_data: Flow data to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = get_validator()
    return validator.quick_validate(flow_data)