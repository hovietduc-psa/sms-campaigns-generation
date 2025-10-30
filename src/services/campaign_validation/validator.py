"""
Campaign Validator - Main validation service combining all validators.
"""
import logging
from typing import Dict, Any, List
import time

from .schema_validator import SchemaValidator, ValidationIssue
from .flow_validator import FlowValidator
from .best_practices_checker import BestPracticesChecker
from .optimization_engine import OptimizationEngine, OptimizationSuggestion

logger = logging.getLogger(__name__)


class CampaignValidationResult:
    """Complete validation result."""

    def __init__(
        self,
        is_valid: bool,
        schema_issues: List[ValidationIssue],
        flow_issues: List[ValidationIssue],
        best_practice_issues: List[ValidationIssue],
        optimizations: List[OptimizationSuggestion],
        best_practices_score: float,
        best_practices_grade: str,
        flow_summary: Dict[str, Any],
        validation_duration: float
    ):
        self.is_valid = is_valid
        self.schema_issues = schema_issues
        self.flow_issues = flow_issues
        self.best_practice_issues = best_practice_issues
        self.optimizations = optimizations
        self.best_practices_score = best_practices_score
        self.best_practices_grade = best_practices_grade
        self.flow_summary = flow_summary
        self.validation_duration = validation_duration

    @property
    def all_issues(self) -> List[ValidationIssue]:
        """Get all validation issues combined."""
        return self.schema_issues + self.flow_issues + self.best_practice_issues

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.all_issues if issue.level == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.all_issues if issue.level == "warning"]

    @property
    def info(self) -> List[ValidationIssue]:
        """Get only info-level issues."""
        return [issue for issue in self.all_issues if issue.level == "info"]

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return len(self.warnings) > 0

    def get_summary(self) -> str:
        """Get validation summary."""
        if not self.is_valid:
            return f"❌ Validation failed: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        elif self.has_warnings():
            return f"⚠️  Validation passed with {len(self.warnings)} warning(s)"
        else:
            return f"✅ Validation passed (Grade: {self.best_practices_grade}, Score: {self.best_practices_score:.0f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "summary": self.get_summary(),
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "info": [issue.to_dict() for issue in self.info],
            "best_practices": {
                "score": self.best_practices_score,
                "grade": self.best_practices_grade
            },
            "flow_summary": self.flow_summary,
            "optimizations": {
                "total": len(self.optimizations),
                "high_priority": len([o for o in self.optimizations if o.priority == "high"]),
                "suggestions": [opt.to_dict() for opt in self.optimizations[:5]]  # Top 5
            },
            "validation_duration_ms": round(self.validation_duration * 1000, 2)
        }


class CampaignValidator:
    """
    Comprehensive campaign validator.

    Combines:
    - Schema validation (structure, types, required fields)
    - Flow validation (reachability, dead ends, loops)
    - Best practices checking (SMS best practices)
    - Optimization suggestions (cost, performance, engagement)
    """

    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.flow_validator = FlowValidator()
        self.best_practices_checker = BestPracticesChecker()
        self.optimization_engine = OptimizationEngine()

    def validate(
        self,
        campaign_json: Dict[str, Any],
        include_optimizations: bool = True,
        strict: bool = False
    ) -> CampaignValidationResult:
        """
        Validate campaign comprehensively.

        Args:
            campaign_json: Campaign JSON dictionary
            include_optimizations: Whether to include optimization suggestions
            strict: If True, warnings are treated as errors

        Returns:
            CampaignValidationResult with all validation results
        """
        start_time = time.time()

        logger.info("Starting comprehensive campaign validation")

        # Run all validators
        schema_issues = self.schema_validator.validate(campaign_json)
        flow_issues = self.flow_validator.validate(campaign_json)
        best_practice_issues = self.best_practices_checker.validate(campaign_json)

        # Get best practices score and grade
        best_practices_score = self.best_practices_checker.get_score()
        best_practices_grade = self.best_practices_checker.get_grade()

        # Get flow summary
        flow_summary = self.flow_validator.get_flow_summary()

        # Get optimizations if requested
        optimizations = []
        if include_optimizations:
            optimizations = self.optimization_engine.analyze(campaign_json)

        # Determine if campaign is valid
        has_schema_errors = self.schema_validator.has_errors()
        has_flow_errors = self.flow_validator.has_errors()

        if strict:
            # In strict mode, warnings are also considered errors
            has_schema_errors = has_schema_errors or len(self.schema_validator.get_warnings()) > 0
            has_flow_errors = has_flow_errors or len(self.flow_validator.get_warnings()) > 0
            has_best_practice_errors = len(self.best_practices_checker.get_warnings()) > 0
            is_valid = not (has_schema_errors or has_flow_errors or has_best_practice_errors)
        else:
            # Only hard errors fail validation
            is_valid = not (has_schema_errors or has_flow_errors)

        duration = time.time() - start_time

        result = CampaignValidationResult(
            is_valid=is_valid,
            schema_issues=schema_issues,
            flow_issues=flow_issues,
            best_practice_issues=best_practice_issues,
            optimizations=optimizations,
            best_practices_score=best_practices_score,
            best_practices_grade=best_practices_grade,
            flow_summary=flow_summary,
            validation_duration=duration
        )

        logger.info(f"Validation completed in {duration:.3f}s: {result.get_summary()}")

        return result

    def validate_and_log(
        self,
        campaign_json: Dict[str, Any],
        include_optimizations: bool = True
    ) -> CampaignValidationResult:
        """
        Validate campaign and log detailed results.

        Args:
            campaign_json: Campaign JSON dictionary
            include_optimizations: Whether to include optimization suggestions

        Returns:
            CampaignValidationResult
        """
        result = self.validate(campaign_json, include_optimizations)

        # Log errors
        if result.errors:
            logger.error(f"Validation errors ({len(result.errors)}):")
            for error in result.errors:
                logger.error(f"  {error}")

        # Log warnings
        if result.warnings:
            logger.warning(f"Validation warnings ({len(result.warnings)}):")
            for warning in result.warnings[:5]:  # First 5 warnings
                logger.warning(f"  {warning}")
            if len(result.warnings) > 5:
                logger.warning(f"  ... and {len(result.warnings) - 5} more warnings")

        # Log best practices score
        logger.info(f"Best Practices: {result.best_practices_grade} ({result.best_practices_score:.0f}/100)")

        # Log top optimizations
        if result.optimizations:
            logger.info(f"Optimization suggestions ({len(result.optimizations)} total):")
            for opt in result.optimizations[:3]:  # Top 3
                logger.info(f"  [{opt.priority.upper()}] {opt.title}")

        return result

    def quick_validate(self, campaign_json: Dict[str, Any]) -> bool:
        """
        Quick validation - only checks critical errors.

        Args:
            campaign_json: Campaign JSON dictionary

        Returns:
            True if campaign passes critical validation
        """
        schema_issues = self.schema_validator.validate(campaign_json)
        flow_issues = self.flow_validator.validate(campaign_json)

        return not (
            self.schema_validator.has_errors() or
            self.flow_validator.has_errors()
        )


# Factory function
def create_validator() -> CampaignValidator:
    """
    Factory function to create CampaignValidator instance.

    Returns:
        CampaignValidator instance
    """
    return CampaignValidator()