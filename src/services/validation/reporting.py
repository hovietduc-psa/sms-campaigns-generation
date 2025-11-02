"""
Validation reporting and analytics module.

This module provides comprehensive reporting capabilities for validation results,
including issue categorization, trend analysis, and detailed reporting.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, Counter

from src.core.logging import get_logger
from src.services.validation.validator import ValidationSummary

logger = get_logger(__name__)


class ValidationReport:
    """Comprehensive validation report."""

    def __init__(
        self,
        flow_id: Optional[str] = None,
        summary: Optional[ValidationSummary] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.flow_id = flow_id or "unknown"
        self.summary = summary
        self.timestamp = timestamp or datetime.now(timezone.utc)

        # Analysis results
        self.issue_categories = self._categorize_issues() if summary else {}
        self.recommendations = self._generate_recommendations() if summary else []
        self.metrics = self._calculate_metrics() if summary else {}
        self.quality_score = self._calculate_quality_score() if summary else 0

    def _categorize_issues(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize validation issues by type and severity."""
        categories = {
            "structural": [],  # Schema and structure issues
            "reference": [],   # Reference integrity issues
            "logical": [],      # Flow logic issues
            "business": [],     # Business rule issues
            "optimization": [], # Optimization suggestions
        }

        for issue in self.summary.issues:
            issue_data = issue.to_dict()
            code = issue_data.get("code", "")

            # Categorize based on issue code
            if any(keyword in code.lower() for keyword in ["missing", "invalid", "empty"]):
                if "reference" in code.lower() or "initial" in code.lower():
                    categories["reference"].append(issue_data)
                else:
                    categories["structural"].append(issue_data)
            elif any(keyword in code.lower() for keyword in ["circular", "termination", "unreachable"]):
                categories["logical"].append(issue_data)
            elif any(keyword in code.lower() for keyword in ["content", "discount", "timing", "personalization"]):
                categories["business"].append(issue_data)
            elif any(keyword in code.lower() for keyword in ["too", "optimization", "simplification"]):
                categories["optimization"].append(issue_data)
            else:
                categories["logical"].append(issue_data)

        return categories

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on issues."""
        recommendations = []

        # High-priority recommendations (errors)
        if self.summary.error_count > 0:
            recommendations.append({
                "priority": "high",
                "category": "fix_errors",
                "title": "Fix Critical Errors",
                "description": f"Address {self.summary.error_count} critical errors before deploying the campaign",
                "actions": [
                    "Review error details in the validation report",
                    "Apply auto-corrections if available",
                    "Manually fix remaining issues",
                    "Re-validate the campaign flow"
                ]
            })

        # Medium-priority recommendations (warnings)
        if self.summary.warning_count > 0:
            recommendations.append({
                "priority": "medium",
                "category": "address_warnings",
                "title": "Review Warnings",
                "description": f"Review {self.summary.warning_count} warnings to improve campaign effectiveness",
                "actions": [
                    "Check for unreachable nodes or circular references",
                    "Verify message content and personalization",
                    "Review timing and delay settings"
                ]
            })

        # Optimization recommendations
        optimization_issues = len(self.issue_categories.get("optimization", []))
        if optimization_issues > 0:
            recommendations.append({
                "priority": "low",
                "category": "optimize_flow",
                "title": "Optimize Campaign Flow",
                "description": f"Consider {optimization_issues} optimization opportunities",
                "actions": [
                    "Simplify complex node structures",
                    "Combine consecutive delays",
                    "Improve message personalization",
                    "Add missing call-to-actions"
                ]
            })

        # Business rule recommendations
        business_issues = self.issue_categories.get("business", [])
        if business_issues:
            no_personalization = any("personalization" in issue.get("code", "").lower() for issue in business_issues)
            no_cta = any("call to action" in issue.get("message", "").lower() for issue in business_issues)

            if no_personalization or no_cta:
                recommendations.append({
                    "priority": "medium",
                    "category": "improve_engagement",
                    "title": "Improve Customer Engagement",
                    "description": "Enhance messages for better customer engagement",
                    "actions": []
                })

                if no_personalization:
                    recommendations[-1]["actions"].append("Add personalization variables like {{first_name}}")
                if no_cta:
                    recommendations[-1]["actions"].append("Add clear call-to-actions in messages")

        return recommendations

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate validation metrics."""
        total_issues = self.summary.total_issues

        return {
            "flow_complexity": self.summary._assess_complexity(),
            "node_count": len(self.summary.flow_data.get("steps", [])),
            "event_count": sum(
                len(step.get("events", []))
                for step in self.summary.flow_data.get("steps", [])
            ),
            "branch_count": sum(
                1 for step in self.summary.flow_data.get("steps", [])
                if step.get("type") == "segment"
            ),
            "message_count": sum(
                1 for step in self.summary.flow_data.get("steps", [])
                if step.get("type") == "message"
            ),
            "issue_density": total_issues / max(len(self.summary.flow_data.get("steps", [])), 1),
            "correction_rate": self.summary.corrections_applied / max(total_issues, 1),
            "validation_time_ms": self.summary.validation_time_ms,
        }

    def _calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        if not self.summary:
            return 0.0

        # Base score starts at 100
        score = 100.0

        # Deduct points for errors (most severe)
        score -= self.summary.error_count * 20

        # Deduct points for warnings
        score -= self.summary.warning_count * 5

        # Deduct points for info issues
        score -= self.summary.info_count * 1

        # Bonus points for corrections applied
        score += self.summary.corrections_applied * 2

        # Ensure score is within bounds
        return max(0.0, min(100.0, score))

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "flow_id": self.flow_id,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "is_valid": self.summary.is_valid,
                "total_issues": self.summary.total_issues,
                "error_count": self.summary.error_count,
                "warning_count": self.summary.warning_count,
                "info_count": self.summary.info_count,
                "corrections_applied": self.summary.corrections_applied,
                "validation_time_ms": self.summary.validation_time_ms,
                "flow_complexity": self.summary._assess_complexity(),
            },
            "issue_categories": {
                category: [
                    {
                        "code": issue.get("code"),
                        "message": issue.get("message"),
                        "severity": issue.get("severity"),
                        "node_id": issue.get("node_id"),
                        "suggested_fix": issue.get("suggested_fix")
                    }
                    for issue in issues
                ]
                for category, issues in self.issue_categories.items()
            },
            "recommendations": self.recommendations,
            "metrics": self.metrics,
            "quality_score": self.quality_score,
        }

    def to_json(self) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ValidationReporter:
    """
    Generates and manages validation reports.
    """

    def __init__(self):
        """Initialize validation reporter."""
        self.reports: List[ValidationReport] = []
        logger.info("Validation reporter initialized")

    def create_report(
        self,
        summary: ValidationSummary,
        flow_id: Optional[str] = None,
    ) -> ValidationReport:
        """
        Create a validation report.

        Args:
            summary: Validation summary
            flow_id: Optional flow identifier

        Returns:
            ValidationReport instance
        """
        report = ValidationReport(flow_id, summary)
        self.reports.append(report)

        logger.info(
            "Validation report created",
            extra={
                "flow_id": report.flow_id,
                "is_valid": report.summary.is_valid,
                "total_issues": report.summary.total_issues,
                "quality_score": report.quality_score,
            }
        )

        return report

    def get_reports(self, flow_id: Optional[str] = None) -> List[ValidationReport]:
        """
        Get validation reports.

        Args:
            flow_id: Optional flow ID to filter by

        Returns:
            List of validation reports
        """
        if flow_id:
            return [report for report in self.reports if report.flow_id == flow_id]
        return self.reports.copy()

    def get_latest_report(self, flow_id: Optional[str] = None) -> Optional[ValidationReport]:
        """
        Get the latest validation report.

        Args:
            flow_id: Optional flow ID to filter by

        Returns:
            Latest validation report or None
        """
        reports = self.get_reports(flow_id)
        return reports[-1] if reports else None

    def generate_trend_analysis(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate trend analysis from validation history.

        Args:
            flow_id: Optional flow ID to filter by

        Returns:
            Trend analysis dictionary
        """
        reports = self.get_reports(flow_id)

        if len(reports) < 2:
            return {
                "message": "Insufficient data for trend analysis (need at least 2 reports)",
                "reports_count": len(reports)
            }

        # Calculate trends
        quality_scores = [report.quality_score for report in reports]
        error_counts = [report.summary.error_count for report in reports]
        warning_counts = [report.summary.warning_count for report in reports]
        correction_rates = [
            report.summary.corrections_applied / max(report.summary.total_issues, 1)
            for report in reports
        ]

        return {
            "reports_analyzed": len(reports),
            "date_range": {
                "start": reports[0].timestamp.isoformat(),
                "end": reports[-1].timestamp.isoformat(),
            },
            "quality_score_trend": {
                "current": quality_scores[-1],
                "previous": quality_scores[-2] if len(quality_scores) > 1 else None,
                "change": quality_scores[-1] - quality_scores[-2] if len(quality_scores) > 1 else 0,
                "average": sum(quality_scores) / len(quality_scores),
                "min": min(quality_scores),
                "max": max(quality_scores),
            },
            "error_count_trend": {
                "current": error_counts[-1],
                "previous": error_counts[-2] if len(error_counts) > 1 else None,
                "change": error_counts[-1] - error_counts[-2] if len(error_counts) > 1 else 0,
                "average": sum(error_counts) / len(error_counts),
                "total": sum(error_counts),
            },
            "warning_count_trend": {
                "current": warning_counts[-1],
                "previous": warning_counts[-2] if len(warning_counts) > 1 else None,
                "change": warning_counts[-1] - warning_counts[-2] if len(warning_counts) > 1 else 0,
                "average": sum(warning_counts) / len(warning_counts),
                "total": sum(warning_counts),
            },
            "correction_rate_trend": {
                "current": correction_rates[-1],
                "previous": correction_rates[-2] if len(correction_rates) > 1 else None,
                "average": sum(correction_rates) / len(correction_rates),
            },
        }

    def generate_issue_frequency_analysis(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate frequency analysis of validation issues.

        Args:
            flow_id: Optional flow ID to filter by

        Returns:
            Issue frequency analysis
        """
        reports = self.get_reports(flow_id)

        # Collect all issues
        all_issues = []
        for report in reports:
            all_issues.extend(report.summary.issues)

        # Count issues by code
        issue_counter = Counter(issue.code for issue in all_issues)
        issue_counter_by_severity = defaultdict(Counter)

        for issue in all_issues:
            issue_counter_by_severity[issue.severity][issue.code] += 1

        # Most common issues
        most_common = issue_counter.most_common(10)

        return {
            "total_issues": len(all_issues),
            "unique_issue_types": len(issue_counter),
            "most_common_issues": [
                {
                    "code": code,
                    "count": count,
                    "percentage": (count / len(all_issues)) * 100
                }
                for code, count in most_common
            ],
            "issues_by_severity": {
                severity: {
                    "total": sum(counter.values()),
                    "types": [
                        {
                            "code": code,
                            "count": count,
                            "percentage": (count / sum(counter.values())) * 100
                        }
                        for code, count in counter.most_common()
                    ]
                }
                for severity, counter in issue_counter_by_severity.items()
            }
        }

    def generate_quality_metrics_summary(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate quality metrics summary.

        Args:
            flow_id: Optional flow ID to filter by

        Returns:
            Quality metrics summary
        """
        reports = self.get_reports(flow_id)

        if not reports:
            return {"message": "No reports available for analysis"}

        quality_scores = [report.quality_score for report in reports]

        return {
            "total_reports": len(reports),
            "quality_score_statistics": {
                "current": quality_scores[-1],
                "average": sum(quality_scores) / len(quality_scores),
                "min": min(quality_scores),
                "max": max(quality_scores),
                "median": sorted(quality_scores)[len(quality_scores) // 2],
                "standard_deviation": self._calculate_std_dev(quality_scores),
            },
            "quality_distribution": {
                "excellent": len([s for s in quality_scores if s >= 90]),
                "good": len([s for s in quality_scores if 80 <= s < 90]),
                "fair": len([s for s in quality_scores if 70 <= s < 80]),
                "poor": len([s for s in quality_scores if s < 70]),
            },
            "validation_performance": {
                "average_validation_time_ms": sum(
                    report.summary.validation_time_ms for report in reports
                ) / len(reports),
                "total_corrections_applied": sum(
                    report.summary.corrections_applied for report in reports
                ),
                "auto_correction_success_rate": sum(
                    1 for report in reports if report.summary.corrections_applied > 0
                ) / len(reports) * 100,
            }
        }

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def export_reports(self, flow_id: Optional[str] = None, format_type: str = "json") -> str:
        """
        Export reports in specified format.

        Args:
            flow_id: Optional flow ID to filter by
            format_type: Export format ("json" or "csv")

        Returns:
            Exported data as string
        """
        reports = self.get_reports(flow_id)

        if format_type.lower() == "json":
            return json.dumps([report.to_dict() for report in reports], indent=2)

        elif format_type.lower() == "csv":
            # Simple CSV export
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                "timestamp", "flow_id", "is_valid", "total_issues",
                "error_count", "warning_count", "info_count",
                "corrections_applied", "quality_score", "validation_time_ms"
            ])

            # Data rows
            for report in reports:
                writer.writerow([
                    report.timestamp.isoformat(),
                    report.flow_id,
                    report.summary.is_valid,
                    report.summary.total_issues,
                    report.summary.error_count,
                    report.summary.warning_count,
                    report.summary.info_count,
                    report.summary.corrections_applied,
                    report.quality_score,
                    report.summary.validation_time_ms
                ])

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def clear_reports(self, flow_id: Optional[str] = None) -> int:
        """
        Clear validation reports.

        Args:
            flow_id: Optional flow ID to filter by

        Returns:
            Number of reports cleared
        """
        if flow_id:
            original_count = len(self.reports)
            self.reports = [report for report in self.reports if report.flow_id != flow_id]
            cleared_count = original_count - len(self.reports)
        else:
            cleared_count = len(self.reports)
            self.reports.clear()

        logger.info(f"Cleared {cleared_count} validation reports")
        return cleared_count


# Global validation reporter instance
_validation_reporter: Optional[ValidationReporter] = None


def get_validation_reporter() -> ValidationReporter:
    """Get global validation reporter instance."""
    global _validation_reporter
    if _validation_reporter is None:
        _validation_reporter = ValidationReporter()
    return _validation_reporter