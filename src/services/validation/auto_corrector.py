"""
Auto-correction engine for campaign flows.

This module provides intelligent auto-correction capabilities for common validation issues
in campaign flows, with configurable correction strategies and safety mechanisms.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from copy import deepcopy

from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow, NodeType
from src.services.validation.schema_validator import ValidationIssue, ValidationResult
from src.utils.constants import NODE_TYPES, EVENT_TYPES, DISCOUNT_TYPES, TIME_PERIODS

logger = get_logger(__name__)


class CorrectionStrategy:
    """Defines how to handle a specific type of validation issue."""

    def __init__(
        self,
        issue_code: str,
        auto_correct: bool = True,
        requires_user_confirmation: bool = False,
        risk_level: str = "low",  # "low", "medium", "high"
        description: str = "",
    ):
        self.issue_code = issue_code
        self.auto_correct = auto_correct
        self.requires_user_confirmation = requires_user_confirmation
        self.risk_level = risk_level
        self.description = description


class CorrectionResult:
    """Result of an auto-correction operation."""

    def __init__(
        self,
        success: bool,
        corrected_data: Optional[Dict[str, Any]] = None,
        applied_corrections: List[str] = None,
        blocked_corrections: List[str] = None,
        warnings: List[str] = None,
    ):
        self.success = success
        self.corrected_data = corrected_data
        self.applied_corrections = applied_corrections or []
        self.blocked_corrections = blocked_corrections or []
        self.warnings = warnings or []


class AutoCorrector:
    """
    Intelligent auto-correction engine for campaign flows.
    """

    def __init__(self, enable_auto_correction: bool = True):
        """
        Initialize auto-correction engine.

        Args:
            enable_auto_correction: Whether to enable auto-correction
        """
        self.enable_auto_correction = enable_auto_correction
        self.correction_strategies = self._build_correction_strategies()
        self.correction_history: List[Dict[str, Any]] = []

        logger.info(
            "Auto-corrector initialized",
            extra={
                "enable_auto_correction": enable_auto_correction,
                "strategies_count": len(self.correction_strategies),
            }
        )

    def _build_correction_strategies(self) -> Dict[str, CorrectionStrategy]:
        """Build correction strategies for different issue types."""
        return {
            # Structure issues
            "MISSING_INITIAL_STEP_ID": CorrectionStrategy(
                issue_code="MISSING_INITIAL_STEP_ID",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Set initialStepID to first node"
            ),
            "MISSING_STEPS": CorrectionStrategy(
                issue_code="MISSING_STEPS",
                auto_correct=False,
                requires_user_confirmation=True,
                risk_level="high",
                description="Cannot auto-correct missing steps array"
            ),
            "EMPTY_STEPS": CorrectionStrategy(
                issue_code="EMPTY_STEPS",
                auto_correct=False,
                requires_user_confirmation=True,
                risk_level="high",
                description="Cannot auto-correct empty steps array"
            ),
            "INVALID_INITIAL_STEP_ID": CorrectionStrategy(
                issue_code="INVALID_INITIAL_STEP_ID",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Set initialStepID to existing node"
            ),

            # Node issues
            "MISSING_NODE_TYPE": CorrectionStrategy(
                issue_code="MISSING_NODE_TYPE",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Set node type to 'message'"
            ),
            "DUPLICATE_NODE_ID": CorrectionStrategy(
                issue_code="DUPLICATE_NODE_ID",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Generate unique node ID"
            ),
            "INVALID_NODE_ID_FORMAT": CorrectionStrategy(
                issue_code="INVALID_NODE_ID_FORMAT",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Sanitize node ID format"
            ),

            # Message node issues
            "MISSING_MESSAGE_CONTENT": CorrectionStrategy(
                issue_code="MISSING_MESSAGE_CONTENT",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Add default message content"
            ),
            "MESSAGE_TOO_LONG": CorrectionStrategy(
                issue_code="MESSAGE_TOO_LONG",
                auto_correct=False,
                requires_user_confirmation=True,
                risk_level="medium",
                description="Message too long - requires manual review"
            ),

            # Segment node issues
            "MISSING_SEGMENT_CONDITIONS": CorrectionStrategy(
                issue_code="MISSING_SEGMENT_CONDITIONS",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Add default segment conditions"
            ),
            "INSUFFICIENT_SEGMENT_EVENTS": CorrectionStrategy(
                issue_code="INSUFFICIENT_SEGMENT_EVENTS",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Add default include/exclude events"
            ),

            # Delay node issues
            "MISSING_DELAY_TIME": CorrectionStrategy(
                issue_code="MISSING_DELAY_TIME",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Set default delay time"
            ),
            "MISSING_DELAY_PERIOD": CorrectionStrategy(
                issue_code="MISSING_DELAY_PERIOD",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Set default delay period"
            ),
            "INVALID_DELAY_TIME": CorrectionStrategy(
                issue_code="INVALID_DELAY_TIME",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Fix invalid delay time"
            ),

            # Event issues
            "MISSING_EVENT_TYPE": CorrectionStrategy(
                issue_code="MISSING_EVENT_TYPE",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Set default event type"
            ),
            "MISSING_NEXT_STEP_ID": CorrectionStrategy(
                issue_code="MISSING_NEXT_STEP_ID",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Set nextStepID to end node"
            ),
            "MISSING_REPLY_INTENT": CorrectionStrategy(
                issue_code="MISSING_REPLY_INTENT",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Set default reply intent"
            ),

            # Reference issues
            "BROKEN_EVENT_REFERENCE": CorrectionStrategy(
                issue_code="BROKEN_EVENT_REFERENCE",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Fix broken event references"
            ),
            "DUPLICATE_NEXT_STEP_ID": CorrectionStrategy(
                issue_code="DUPLICATE_NEXT_STEP_ID",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Create unique end nodes for duplicate nextStepID references"
            ),
            "ORPHANED_NODE": CorrectionStrategy(
                issue_code="ORPHANED_NODE",
                auto_correct=False,
                requires_user_confirmation=True,
                risk_level="medium",
                description="Remove or connect orphaned nodes"
            ),

            # Flow issues
            "NO_TERMINATION": CorrectionStrategy(
                issue_code="NO_TERMINATION",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Add end node to flow"
            ),
            "MISSING_END_NODE": CorrectionStrategy(
                issue_code="MISSING_END_NODE",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Add end node to flow"
            ),
            "CIRCULAR_REFERENCE": CorrectionStrategy(
                issue_code="CIRCULAR_REFERENCE",
                auto_correct=False,
                requires_user_confirmation=True,
                risk_level="high",
                description="Cannot auto-correct circular references"
            ),

            # Business rule issues
            "EMPTY_MESSAGE_CONTENT": CorrectionStrategy(
                issue_code="EMPTY_MESSAGE_CONTENT",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="medium",
                description="Add default message content"
            ),
            "NODE_WITHOUT_EVENTS": CorrectionStrategy(
                issue_code="NODE_WITHOUT_EVENTS",
                auto_correct=True,
                requires_user_confirmation=False,
                risk_level="low",
                description="Add default event to node"
            ),
        }

    def correct_flow(
        self,
        validation_result: ValidationResult,
        flow_data: Dict[str, Any],
        risk_threshold: str = "medium"
    ) -> CorrectionResult:
        """
        Apply auto-corrections to a flow based on validation issues.

        Args:
            validation_result: Result of validation with issues
            flow_data: Original flow data
            risk_threshold: Maximum risk level to auto-correct

        Returns:
            CorrectionResult with corrected data and applied corrections
        """
        if not self.enable_auto_correction:
            return CorrectionResult(
                success=False,
                corrected_data=None,
                blocked_corrections=["Auto-correction is disabled"]
            )

        applied_corrections = []
        blocked_corrections = []
        warnings = []

        # Work with a copy of the data
        corrected_data = deepcopy(flow_data)

        # Group issues by risk level and apply corrections
        issues_by_priority = self._prioritize_issues(validation_result.issues)

        for issue in issues_by_priority:
            strategy = self.correction_strategies.get(issue.code)

            if not strategy:
                blocked_corrections.append(f"No correction strategy for {issue.code}")
                continue

            # Check if we should auto-correct this issue
            if not strategy.auto_correct:
                blocked_corrections.append(f"Auto-correction disabled for {issue.code}")
                continue

            # Check risk level
            risk_levels = {"low": 1, "medium": 2, "high": 3}
            if risk_levels.get(strategy.risk_level, 3) > risk_levels.get(risk_threshold, 2):
                blocked_corrections.append(
                    f"Risk level {strategy.risk_level} exceeds threshold {risk_threshold} for {issue.code}"
                )
                continue

            # Apply correction
            try:
                correction_result = self._apply_correction(issue, strategy, corrected_data)
                if correction_result["success"]:
                    applied_corrections.append(correction_result["message"])
                    corrected_data = correction_result["corrected_data"]
                    if correction_result.get("warnings"):
                        warnings.extend(correction_result["warnings"])
                else:
                    blocked_corrections.append(f"Failed to correct {issue.code}: {correction_result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Failed to apply correction for {issue.code}: {e}", exc_info=True)
                blocked_corrections.append(f"Exception correcting {issue.code}: {e}")

        # Record correction attempt
        self.correction_history.append({
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "issues_count": len(validation_result.issues),
            "applied_corrections": len(applied_corrections),
            "blocked_corrections": len(blocked_corrections),
            "risk_threshold": risk_threshold,
        })

        logger.info(
            "Auto-correction completed",
            extra={
                "total_issues": len(validation_result.issues),
                "applied_corrections": len(applied_corrections),
                "blocked_corrections": len(blocked_corrections),
                "success": len(applied_corrections) > 0,
            }
        )

        return CorrectionResult(
            success=len(applied_corrections) > 0,
            corrected_data=corrected_data if applied_corrections else None,
            applied_corrections=applied_corrections,
            blocked_corrections=blocked_corrections,
            warnings=warnings,
        )

    def _prioritize_issues(self, issues: List[ValidationIssue]) -> List[ValidationIssue]:
        """Prioritize issues for correction based on severity and impact."""
        # Sort by severity (error > warning > info) and then by code
        severity_order = {"error": 0, "warning": 1, "info": 2}

        return sorted(
            issues,
            key=lambda issue: (
                severity_order.get(issue.severity, 3),
                issue.code
            )
        )

    def _apply_correction(
        self,
        issue: ValidationIssue,
        strategy: CorrectionStrategy,
        flow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a specific correction to the flow data.

        Args:
            issue: The validation issue to correct
            strategy: Correction strategy for the issue
            flow_data: Flow data to correct

        Returns:
            Dictionary with correction result
        """
        try:
            # Dispatch to specific correction method
            correction_method = getattr(self, f"_correct_{issue.code.lower()}", None)

            if correction_method:
                result = correction_method(issue, flow_data)
                return result
            else:
                # Generic correction
                return self._apply_generic_correction(issue, strategy, flow_data)

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "corrected_data": flow_data
            }

    def _apply_generic_correction(
        self,
        issue: ValidationIssue,
        strategy: CorrectionStrategy,
        flow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply generic correction based on suggested fix."""
        # This is a fallback for issues without specific correction methods
        # In practice, you'd implement more sophisticated generic corrections

        if "Add" in issue.suggested_fix:
            # Try to add missing fields
            return {"success": False, "error": "Generic addition not implemented"}

        return {
            "success": False,
            "error": f"No specific correction method for {issue.code}"
        }

    # Specific correction methods
    def _correct_missing_initial_step_id(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing initialStepID."""
        steps = flow_data.get("steps", [])
        if steps and "id" in steps[0]:
            flow_data["initialStepID"] = steps[0]["id"]
            return {
                "success": True,
                "message": f"Set initialStepID to '{steps[0]['id']}'",
                "corrected_data": flow_data
            }

        return {
            "success": False,
            "error": "No steps available to set as initial",
            "corrected_data": flow_data
        }

    def _correct_invalid_initial_step_id(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct invalid initialStepID."""
        steps = flow_data.get("steps", [])
        if steps:
            # Set to first available node
            flow_data["initialStepID"] = steps[0]["id"]
            return {
                "success": True,
                "message": f"Set initialStepID to '{steps[0]['id']}'",
                "corrected_data": flow_data
            }

        return {
            "success": False,
            "error": "No steps available",
            "corrected_data": flow_data
        }

    def _correct_missing_node_type(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing node type."""
        node_path = issue.field_path
        if node_path and node_path.startswith("steps["):
            # Extract node index
            try:
                import re
                match = re.search(r'stats\[(\d+)\]', node_path)
                if match:
                    index = int(match.group(1))
                    steps = flow_data.get("steps", [])
                    if index < len(steps):
                        steps[index]["type"] = "message"
                        return {
                            "success": True,
                            "message": f"Set node {index} type to 'message'",
                            "corrected_data": flow_data
                        }
            except (ValueError, IndexError):
                pass

        return {
            "success": False,
            "error": "Could not locate node for type correction",
            "corrected_data": flow_data
        }

    def _correct_duplicate_node_id(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct duplicate node ID."""
        if issue.node_id:
            # Generate unique ID
            base_id = issue.node_id
            counter = 1
            new_id = f"{base_id}_{counter}"

            # Check if new ID is unique
            existing_ids = [step.get("id") for step in flow_data.get("steps", []) if "id" in step]
            while new_id in existing_ids:
                counter += 1
                new_id = f"{base_id}_{counter}"

            # Update the node ID
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id:
                    step["id"] = new_id
                    # Update references to this node
                    self._update_node_references(flow_data, issue.node_id, new_id)
                    break

            return {
                "success": True,
                "message": f"Changed duplicate node ID from '{issue.node_id}' to '{new_id}'",
                "corrected_data": flow_data
            }

        return {
            "success": False,
            "error": "No node ID provided for duplicate correction",
            "corrected_data": flow_data
        }

    def _correct_invalid_node_id_format(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct invalid node ID format."""
        if issue.node_id:
            # Sanitize ID - replace invalid characters with hyphens
            import re
            sanitized_id = re.sub(r'[^a-zA-Z0-9_-]', '-', issue.node_id)
            sanitized_id = re.sub(r'-+', '-', sanitized_id).strip('-')

            if sanitized_id != issue.node_id:
                # Update the node ID
                for step in flow_data.get("steps", []):
                    if step.get("id") == issue.node_id:
                        old_id = step["id"]
                        step["id"] = sanitized_id
                        # Update references
                        self._update_node_references(flow_data, old_id, sanitized_id)
                        break

                return {
                    "success": True,
                    "message": f"Sanitized node ID from '{issue.node_id}' to '{sanitized_id}'",
                    "corrected_data": flow_data
                }

        return {
            "success": False,
            "error": "No node ID provided for format correction",
            "corrected_data": flow_data
        }

    def _correct_missing_message_content(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing message content."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") == "message":
                    step["content"] = "Thank you for your interest! We'll be in touch soon."
                    step["text"] = step["content"]
                    return {
                        "success": True,
                        "message": f"Added default content to message node '{issue.node_id}'",
                        "corrected_data": flow_data,
                        "warnings": ["Please customize the message content for your campaign"]
                    }

        return {
            "success": False,
            "error": "Could not locate message node for content correction",
            "corrected_data": flow_data
        }

    def _correct_missing_segment_conditions(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing segment conditions."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") == "segment":
                    step["conditions"] = [
                        {
                            "id": 1,
                            "type": "property",
                            "operator": "has",
                            "propertyName": "customer_type",
                            "propertyValue": "vip",
                            "propertyOperator": "with a value of",
                            "timeSettings": {
                                "timePeriod": "all time",
                                "timePeriodType": "relative"
                            }
                        }
                    ]
                    return {
                        "success": True,
                        "message": f"Added default conditions to segment node '{issue.node_id}'",
                        "corrected_data": flow_data,
                        "warnings": ["Please customize the segment conditions for your campaign"]
                    }

        return {
            "success": False,
            "error": "Could not locate segment node for conditions correction",
            "corrected_data": flow_data
        }

    def _correct_insufficient_segment_events(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct insufficient segment events."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") == "segment":
                    # Add default include/exclude events if missing
                    events = step.get("events", [])
                    has_include = any(e.get("action") == "include" for e in events if e.get("type") == "split")
                    has_exclude = any(e.get("action") == "exclude" for e in events if e.get("type") == "split")

                    if not has_include:
                        events.append({
                            "id": str(uuid.uuid4()),
                            "type": "split",
                            "label": "include",
                            "action": "include",
                            "nextStepID": "end-node",  # Will be fixed by reference correction
                            "active": True,
                            "parameters": {}
                        })

                    if not has_exclude:
                        events.append({
                            "id": str(uuid.uuid4()),
                            "type": "split",
                            "label": "exclude",
                            "action": "exclude",
                            "nextStepID": "end-node",  # Will be fixed by reference correction
                            "active": True,
                            "parameters": {}
                        })

                    step["events"] = events
                    return {
                        "success": True,
                        "message": f"Added default events to segment node '{issue.node_id}'",
                        "corrected_data": flow_data
                    }

        return {
            "success": False,
            "error": "Could not locate segment node for events correction",
            "corrected_data": flow_data
        }

    def _correct_missing_delay_time(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing delay time."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") == "delay":
                    step["time"] = "1"
                    step["period"] = "Hours"
                    step["delay"] = {"value": "1", "unit": "Hours"}
                    return {
                        "success": True,
                        "message": f"Set default delay time (1 hour) for node '{issue.node_id}'",
                        "corrected_data": flow_data
                    }

        return {
            "success": False,
            "error": "Could not locate delay node for time correction",
            "corrected_data": flow_data
        }

    def _correct_missing_delay_period(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing delay period."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") == "delay":
                    step["period"] = "Hours"
                    return {
                        "success": True,
                        "message": f"Set default delay period (Hours) for node '{issue.node_id}'",
                        "corrected_data": flow_data
                    }

        return {
            "success": False,
            "error": "Could not locate delay node for period correction",
            "corrected_data": flow_data
        }

    def _correct_invalid_delay_time(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct invalid delay time."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") == "delay":
                    try:
                        time_value = float(step.get("time", "0"))
                        if time_value <= 0:
                            step["time"] = "1"
                            step["period"] = "Hours"
                            step["delay"] = {"value": "1", "unit": "Hours"}
                            return {
                                "success": True,
                                "message": f"Fixed invalid delay time for node '{issue.node_id}'",
                                "corrected_data": flow_data
                            }
                    except (ValueError, TypeError):
                        step["time"] = "1"
                        step["period"] = "Hours"
                        step["delay"] = {"value": "1", "unit": "Hours"}
                        return {
                            "success": True,
                            "message": f"Fixed invalid delay time for node '{issue.node_id}'",
                            "corrected_data": flow_data
                        }

        return {
            "success": False,
            "error": "Could not locate delay node for time correction",
            "corrected_data": flow_data
        }

    def _correct_missing_event_type(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing event type."""
        if issue.event_id and issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id:
                    for event in step.get("events", []):
                        if event.get("id") == issue.event_id:
                            event["type"] = "default"
                            return {
                                "success": True,
                                "message": f"Set default event type for event '{issue.event_id}'",
                                "corrected_data": flow_data
                            }

        return {
            "success": False,
            "error": "Could not locate event for type correction",
            "corrected_data": flow_data
        }

    def _correct_missing_next_step_id(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing nextStepID."""
        # Find or create an end node
        end_node_id = None
        for step in flow_data.get("steps", []):
            if step.get("type") == "end":
                end_node_id = step.get("id")
                break

        if not end_node_id:
            # Create an end node
            end_node_id = "end-node"
            end_node = {
                "id": end_node_id,
                "type": "end",
                "label": "End",
                "active": True,
                "parameters": {},
                "events": []
            }
            flow_data.setdefault("steps", []).append(end_node)

        # Update the event with missing nextStepID
        if issue.event_id and issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id:
                    for event in step.get("events", []):
                        if event.get("id") == issue.event_id:
                            event["nextStepID"] = end_node_id
                            return {
                                "success": True,
                                "message": f"Set nextStepID to '{end_node_id}' for event '{issue.event_id}'",
                                "corrected_data": flow_data
                            }

        return {
            "success": False,
            "error": "Could not locate event for nextStepID correction",
            "corrected_data": flow_data
        }

    def _correct_missing_reply_intent(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct missing reply intent."""
        if issue.event_id and issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id:
                    for event in step.get("events", []):
                        if event.get("id") == issue.event_id and event.get("type") == "reply":
                            event["intent"] = "yes"
                            event["description"] = "Customer responded positively"
                            return {
                                "success": True,
                                "message": f"Set default reply intent for event '{issue.event_id}'",
                                "corrected_data": flow_data
                            }

        return {
            "success": False,
            "error": "Could not locate reply event for intent correction",
            "corrected_data": flow_data
        }

    def _correct_broken_event_reference(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct broken event reference."""
        # Find or create an end node as fallback
        end_node_id = None
        for step in flow_data.get("steps", []):
            if step.get("type") == "end":
                end_node_id = step.get("id")
                break

        if not end_node_id:
            end_node_id = "end-node"
            end_node = {
                "id": end_node_id,
                "type": "end",
                "label": "End",
                "active": True,
                "parameters": {},
                "events": []
            }
            flow_data.setdefault("steps", []).append(end_node)

        # Update the broken reference
        if issue.event_id and issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id:
                    for event in step.get("events", []):
                        if event.get("id") == issue.event_id:
                            old_next = event.get("nextStepID")
                            event["nextStepID"] = end_node_id
                            return {
                                "success": True,
                                "message": f"Fixed broken reference from '{old_next}' to '{end_node_id}'",
                                "corrected_data": flow_data
                            }

        return {
            "success": False,
            "error": "Could not locate event for reference correction",
            "corrected_data": flow_data
        }

    def _correct_no_termination(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add termination to flow."""
        # Check if end node already exists
        for step in flow_data.get("steps", []):
            if step.get("type") == "end":
                return {
                    "success": False,
                    "error": "End node already exists",
                    "corrected_data": flow_data
                }

        # Create end node
        end_node = {
            "id": "end-node",
            "type": "end",
            "label": "End",
            "active": True,
            "parameters": {},
            "events": []
        }

        flow_data.setdefault("steps", []).append(end_node)

        return {
            "success": True,
            "message": "Added end node to flow",
            "corrected_data": flow_data
        }

    def _correct_missing_end_node(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add END node when missing_end_node error is detected."""
        logger.info("Auto-correcting missing END node issue")
        return self._correct_no_termination(issue, flow_data)

    def _correct_empty_message_content(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct empty message content."""
        return self._correct_missing_message_content(issue, flow_data)

    def _correct_node_without_events(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add default event to node without events."""
        if issue.node_id:
            for step in flow_data.get("steps", []):
                if step.get("id") == issue.node_id and step.get("type") != "end":
                    # Find or create end node
                    end_node_id = None
                    for s in flow_data.get("steps", []):
                        if s.get("type") == "end":
                            end_node_id = s.get("id")
                            break

                    if not end_node_id:
                        end_node_id = "end-node"
                        end_node = {
                            "id": end_node_id,
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                        flow_data.setdefault("steps", []).append(end_node)

                    # Add default event
                    default_event = {
                        "id": str(uuid.uuid4()),
                        "type": "default",
                        "nextStepID": end_node_id,
                        "active": True,
                        "parameters": {}
                    }

                    step.setdefault("events", []).append(default_event)

                    return {
                        "success": True,
                        "message": f"Added default event to node '{issue.node_id}'",
                        "corrected_data": flow_data
                    }

        return {
            "success": False,
            "error": "Could not locate node for event addition",
            "corrected_data": flow_data
        }

    def _update_node_references(self, flow_data: Dict[str, Any], old_id: str, new_id: str) -> None:
        """Update all references to a node ID."""
        # Update initialStepID
        if flow_data.get("initialStepID") == old_id:
            flow_data["initialStepID"] = new_id

        # Update event references
        for step in flow_data.get("steps", []):
            for event in step.get("events", []):
                if event.get("nextStepID") == old_id:
                    event["nextStepID"] = new_id

    def _correct_duplicate_next_step_id(self, issue: ValidationIssue, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Correct duplicate nextStepID values by creating unique end nodes for each reference.

        This auto-correction creates unique end nodes (e.g., end-node-001, end-node-002)
        for each event that points to the same nextStepID, ensuring FlowBuilder compliance.
        """
        if not issue.value:
            return {
                "success": False,
                "message": "No nextStepID value provided for correction",
                "corrected_data": flow_data
            }

        duplicate_nextstepid = issue.value
        steps = flow_data.get("steps", [])
        events_to_correct = []

        # Find all events that reference the duplicate nextStepID
        for step in steps:
            for event in step.get("events", []):
                if event.get("nextStepID") == duplicate_nextstepid:
                    events_to_correct.append({
                        "step_id": step.get("id"),
                        "event": event,
                        "step": step
                    })

        if len(events_to_correct) <= 1:
            # No correction needed
            return {
                "success": True,
                "message": "No duplicate nextStepID found, no correction needed",
                "corrected_data": flow_data
            }

        # Create unique end nodes for each event (except the first one)
        original_end_node = None
        for i, event_info in enumerate(events_to_correct):
            step = event_info["step"]
            event = event_info["event"]

            if i == 0:
                # Keep the first event pointing to the original node
                # Find the original end node
                for s in steps:
                    if s.get("id") == duplicate_nextstepid:
                        original_end_node = s
                        break
                continue

            # Create a unique end node for this event
            unique_end_id = f"{duplicate_nextstepid}-{i:03d}"
            unique_end_node = {
                "id": unique_end_id,
                "type": "end",
                "name": f"End Node {i}",
                "events": []
            }

            # Add the new end node to the flow
            steps.append(unique_end_node)

            # Update the event to point to the unique end node
            event["nextStepID"] = unique_end_id

            logger.info(f"Created unique end node '{unique_end_id}' for event '{event.get('id')}' in step '{step.get('id')}'")

        return {
            "success": True,
            "message": f"Created {len(events_to_correct) - 1} unique end nodes for duplicate nextStepID '{duplicate_nextstepid}'",
            "corrected_data": flow_data
        }

    def get_correction_history(self) -> List[Dict[str, Any]]:
        """Get history of correction attempts."""
        return self.correction_history.copy()

    def clear_correction_history(self) -> None:
        """Clear correction history."""
        self.correction_history.clear()

    def enable_corrections(self, enable: bool = True) -> None:
        """Enable or disable auto-correction."""
        self.enable_auto_correction = enable
        logger.info(f"Auto-correction {'enabled' if enable else 'disabled'}")


# Global auto-corrector instance
_auto_corrector: Optional[AutoCorrector] = None


def get_auto_corrector() -> AutoCorrector:
    """Get global auto-corrector instance."""
    global _auto_corrector
    if _auto_corrector is None:
        _auto_corrector = AutoCorrector()
    return _auto_corrector