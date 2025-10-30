"""
JSON Schema Validator - Validates campaign structure against FlowBuilder schema requirements.
"""
import logging
from typing import Dict, Any, List, Optional, Set
from pydantic import ValidationError

from ...models.campaign import Campaign, StepType, EventType

logger = logging.getLogger(__name__)


class ValidationIssue:
    """Represents a validation issue."""

    def __init__(
        self,
        level: str,  # "error", "warning", "info"
        category: str,  # "schema", "flow", "best_practice", "optimization"
        message: str,
        step_id: Optional[str] = None,
        field: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        self.level = level
        self.category = category
        self.message = message
        self.step_id = step_id
        self.field = field
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "step_id": self.step_id,
            "field": self.field,
            "suggestion": self.suggestion
        }

    def __repr__(self) -> str:
        location = f" ({self.step_id})" if self.step_id else ""
        return f"[{self.level.upper()}] {self.message}{location}"


class SchemaValidator:
    """
    Validates campaign structure against FlowBuilder schema requirements.

    This ensures:
    - All required FlowBuilder fields are present
    - Field types match FlowBuilder specification
    - Step IDs are unique and valid
    - Event types and references are valid (reply, noreply, default, split)
    - FlowBuilder-specific structures are correct (delay, rateLimit, conditions)
    - Pydantic models validate successfully
    - Backward compatibility with legacy formats
    """

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, campaign_json: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate campaign JSON structure.

        Args:
            campaign_json: Campaign JSON dictionary

        Returns:
            List of validation issues
        """
        self.issues = []

        # Validate using Pydantic model
        try:
            campaign = Campaign(**campaign_json)
            logger.info("Pydantic validation passed")
        except ValidationError as e:
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"Pydantic validation failed: {error['msg']}",
                    field=field_path,
                    suggestion="Fix the field type or value according to the schema"
                ))
            return self.issues
        except Exception as e:
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message=f"Failed to parse campaign: {str(e)}",
                suggestion="Ensure the campaign JSON is valid"
            ))
            return self.issues

        # Additional structural validations
        self._validate_basic_structure(campaign_json)
        self._validate_step_ids(campaign_json)
        self._validate_step_references(campaign_json)
        self._validate_event_types(campaign_json)
        self._validate_required_fields_by_type(campaign_json)
        self._validate_field_constraints(campaign_json)

        # FlowBuilder specific validations
        self._validate_flowbuilder_compliance(campaign_json)

        return self.issues

    def _validate_basic_structure(self, campaign_json: Dict[str, Any]) -> None:
        """Validate basic campaign structure."""
        # Check required top-level fields
        if "initialStepID" not in campaign_json:
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Missing required field 'initialStepID'",
                suggestion="Add 'initialStepID' pointing to the first step"
            ))

        if "steps" not in campaign_json:
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Missing required field 'steps'",
                suggestion="Add 'steps' array with at least one step"
            ))
            return

        # Check steps is a list
        if not isinstance(campaign_json["steps"], list):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Field 'steps' must be an array",
                suggestion="Ensure 'steps' is a JSON array"
            ))
            return

        # Check at least one step exists
        if len(campaign_json["steps"]) == 0:
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Campaign must have at least one step",
                suggestion="Add at least one step to the campaign"
            ))

    def _validate_step_ids(self, campaign_json: Dict[str, Any]) -> None:
        """Validate step IDs are unique and well-formed."""
        if "steps" not in campaign_json:
            return

        step_ids: Set[str] = set()

        for i, step in enumerate(campaign_json["steps"]):
            if not isinstance(step, dict):
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"Step at index {i} is not an object",
                    suggestion="Each step must be a JSON object"
                ))
                continue

            # Check step has ID
            if "id" not in step:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"Step at index {i} missing required field 'id'",
                    suggestion="Add unique 'id' field to the step"
                ))
                continue

            step_id = step["id"]

            # Check ID is a string
            if not isinstance(step_id, str):
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"Step ID at index {i} must be a string",
                    step_id=str(step_id),
                    suggestion="Use string type for step IDs"
                ))
                continue

            # Check ID is not empty
            if not step_id.strip():
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"Step ID at index {i} is empty",
                    suggestion="Provide a non-empty step ID"
                ))
                continue

            # Check for duplicate IDs
            if step_id in step_ids:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"Duplicate step ID: {step_id}",
                    step_id=step_id,
                    suggestion="Ensure all step IDs are unique"
                ))
            else:
                step_ids.add(step_id)

    def _validate_step_references(self, campaign_json: Dict[str, Any]) -> None:
        """Validate that all step references point to existing steps."""
        if "steps" not in campaign_json:
            return

        # Collect all step IDs
        step_ids = {step.get("id") for step in campaign_json["steps"] if isinstance(step, dict) and "id" in step}

        # Check initialStepID exists
        if "initialStepID" in campaign_json:
            initial_id = campaign_json["initialStepID"]
            if initial_id not in step_ids:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message=f"initialStepID '{initial_id}' does not reference an existing step",
                    field="initialStepID",
                    suggestion=f"Ensure initialStepID references one of: {', '.join(sorted(step_ids))}"
                ))

        # Check all nextStepID references in events
        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")

            # Check events
            if "events" in step and isinstance(step["events"], list):
                for event in step["events"]:
                    if not isinstance(event, dict):
                        continue

                    if "nextStepID" in event and event["nextStepID"]:
                        next_id = event["nextStepID"]
                        if next_id not in step_ids:
                            self.issues.append(ValidationIssue(
                                level="error",
                                category="schema",
                                message=f"Event nextStepID '{next_id}' does not reference an existing step",
                                step_id=step_id,
                                field="nextStepID",
                                suggestion=f"Use one of the existing step IDs"
                            ))

            # Check direct nextStepID (for delay, etc.)
            if "nextStepID" in step and step["nextStepID"]:
                next_id = step["nextStepID"]
                if next_id not in step_ids:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message=f"Step nextStepID '{next_id}' does not reference an existing step",
                        step_id=step_id,
                        field="nextStepID",
                        suggestion=f"Use one of the existing step IDs"
                    ))

            # Check condition step references
            if step.get("type") == "condition":
                if "trueStepID" in step and step["trueStepID"]:
                    true_id = step["trueStepID"]
                    if true_id not in step_ids:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="schema",
                            message=f"Condition trueStepID '{true_id}' does not reference an existing step",
                            step_id=step_id,
                            field="trueStepID",
                            suggestion=f"Use one of the existing step IDs"
                        ))

                if "falseStepID" in step and step["falseStepID"]:
                    false_id = step["falseStepID"]
                    if false_id not in step_ids:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="schema",
                            message=f"Condition falseStepID '{false_id}' does not reference an existing step",
                            step_id=step_id,
                            field="falseStepID",
                            suggestion=f"Use one of the existing step IDs"
                        ))

    def _validate_event_types(self, campaign_json: Dict[str, Any]) -> None:
        """Validate event types are valid."""
        if "steps" not in campaign_json:
            return

        valid_event_types = {e.value for e in EventType}

        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")

            if "events" not in step or not isinstance(step["events"], list):
                continue

            for i, event in enumerate(step["events"]):
                if not isinstance(event, dict):
                    continue

                if "type" not in event:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message=f"Event at index {i} missing required field 'type'",
                        step_id=step_id,
                        suggestion="Add 'type' field to the event"
                    ))
                    continue

                event_type = event["type"]
                if event_type not in valid_event_types:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message=f"Invalid event type '{event_type}'",
                        step_id=step_id,
                        suggestion=f"Use one of: {', '.join(sorted(valid_event_types))}"
                    ))

    def _validate_required_fields_by_type(self, campaign_json: Dict[str, Any]) -> None:
        """Validate that steps have required fields based on their type."""
        if "steps" not in campaign_json:
            return

        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            if not step_type:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message="Step missing required field 'type'",
                    step_id=step_id,
                    suggestion="Add 'type' field to specify step type"
                ))
                continue

            # Message steps
            if step_type == "message":
                # Must have text OR prompt (for AI-generated)
                has_text = "text" in step and step["text"]
                has_prompt = "prompt" in step and step["prompt"]

                if not has_text and not has_prompt:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Message step must have 'text' or 'prompt' field",
                        step_id=step_id,
                        suggestion="Add 'text' for static message or 'prompt' for AI-generated"
                    ))

            # Segment steps
            elif step_type == "segment":
                if "segmentDefinition" not in step or not step["segmentDefinition"]:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Segment step must have 'segmentDefinition' field",
                        step_id=step_id,
                        suggestion="Add 'segmentDefinition' with segment criteria"
                    ))

            # Delay steps
            elif step_type == "delay":
                if "duration" not in step or not step["duration"]:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Delay step must have 'duration' field",
                        step_id=step_id,
                        suggestion="Add 'duration' object (e.g., {\"hours\": 6})"
                    ))

            # Condition steps
            elif step_type == "condition":
                if "condition" not in step or not step["condition"]:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Condition step must have 'condition' field",
                        step_id=step_id,
                        suggestion="Add 'condition' object with evaluation criteria"
                    ))

                if "trueStepID" not in step or not step["trueStepID"]:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Condition step must have 'trueStepID' field",
                        step_id=step_id,
                        suggestion="Add 'trueStepID' for when condition is true"
                    ))

                if "falseStepID" not in step or not step["falseStepID"]:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Condition step must have 'falseStepID' field",
                        step_id=step_id,
                        suggestion="Add 'falseStepID' for when condition is false"
                    ))

            # Experiment steps
            elif step_type == "experiment":
                if "variants" not in step or not isinstance(step["variants"], list):
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Experiment step must have 'variants' array",
                        step_id=step_id,
                        suggestion="Add 'variants' array with experiment branches"
                    ))

            # End steps
            elif step_type == "end":
                if "reason" not in step or not step["reason"]:
                    self.issues.append(ValidationIssue(
                        level="warning",
                        category="schema",
                        message="End step should have 'reason' field for tracking",
                        step_id=step_id,
                        suggestion="Add 'reason' to explain why campaign ended"
                    ))

    def _validate_field_constraints(self, campaign_json: Dict[str, Any]) -> None:
        """Validate field-specific constraints."""
        if "steps" not in campaign_json:
            return

        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            # Validate message text length
            if step_type == "message" and "text" in step:
                text = step["text"]
                if isinstance(text, str):
                    if len(text) > 1600:  # 10 SMS segments
                        self.issues.append(ValidationIssue(
                            level="warning",
                            category="schema",
                            message=f"Message text is very long ({len(text)} chars)",
                            step_id=step_id,
                            field="text",
                            suggestion="Consider shortening message to reduce SMS costs"
                        ))

            # Validate delay duration
            if step_type == "delay" and "duration" in step:
                duration = step["duration"]
                if isinstance(duration, dict):
                    total_seconds = 0
                    if "seconds" in duration:
                        total_seconds += duration["seconds"]
                    if "minutes" in duration:
                        total_seconds += duration["minutes"] * 60
                    if "hours" in duration:
                        total_seconds += duration["hours"] * 3600
                    if "days" in duration:
                        total_seconds += duration["days"] * 86400

                    if total_seconds > 30 * 86400:  # 30 days
                        self.issues.append(ValidationIssue(
                            level="warning",
                            category="schema",
                            message=f"Delay duration is very long ({total_seconds / 86400:.1f} days)",
                            step_id=step_id,
                            field="duration",
                            suggestion="Consider if such a long delay is intended"
                        ))

            # Validate experiment percentages
            if step_type == "experiment" and "splitPercentages" in step:
                percentages = step["splitPercentages"]
                if isinstance(percentages, list):
                    total = sum(percentages)
                    if abs(total - 100) > 0.01:  # Allow for floating point errors
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="schema",
                            message=f"Experiment split percentages must sum to 100 (currently {total})",
                            step_id=step_id,
                            field="splitPercentages",
                            suggestion="Adjust percentages to sum to 100"
                        ))

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.level == "error" for issue in self.issues)

    def get_errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue.level == "error"]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue.level == "warning"]

    def get_summary(self) -> str:
        """Get a summary of validation results."""
        errors = len(self.get_errors())
        warnings = len(self.get_warnings())

        if errors == 0 and warnings == 0:
            return "✅ Campaign schema validation passed"
        elif errors == 0:
            return f"⚠️  Campaign has {warnings} warning(s)"
        else:
            return f"❌ Campaign has {errors} error(s) and {warnings} warning(s)"

    def _validate_flowbuilder_compliance(self, campaign_json: Dict[str, Any]) -> None:
        """Validate FlowBuilder-specific schema requirements."""
        steps = campaign_json.get("steps", [])

        for step in steps:
            step_id = step.get("id", "unknown")
            step_type = step.get("type", "")

            # Validate message steps
            if step_type == "message":
                self._validate_message_step_flowbuilder(step, step_id)

            # Validate delay steps
            elif step_type == "delay":
                self._validate_delay_step_flowbuilder(step, step_id)

            # Validate segment steps
            elif step_type == "segment":
                self._validate_segment_step_flowbuilder(step, step_id)

            # Validate rate_limit steps
            elif step_type == "rate_limit":
                self._validate_rate_limit_step_flowbuilder(step, step_id)

            # Validate experiment steps
            elif step_type == "experiment":
                self._validate_experiment_step_flowbuilder(step, step_id)

            # Validate end steps
            elif step_type == "end":
                self._validate_end_step_flowbuilder(step, step_id)

            # Validate events for FlowBuilder compliance
            if "events" in step:
                self._validate_events_flowbuilder(step["events"], step_id)

    def _validate_message_step_flowbuilder(self, step: Dict[str, Any], step_id: str) -> None:
        """Validate message step FlowBuilder compliance."""
        # Check for content field (primary display field)
        if not step.get("content") and not step.get("text"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Message step must have 'content' field",
                step_id=step_id,
                field="content",
                suggestion="Add 'content' field with the message text"
            ))

        # Validate discount fields if discountType is not 'none'
        discount_type = step.get("discountType", "none")
        if discount_type != "none":
            if not step.get("discountValue"):
                self.issues.append(ValidationIssue(
                    level="warning",
                    category="schema",
                    message="Discount value missing for discount type",
                    step_id=step_id,
                    field="discountValue",
                    suggestion="Add discountValue field with the discount amount"
                ))

    def _validate_delay_step_flowbuilder(self, step: Dict[str, Any], step_id: str) -> None:
        """Validate delay step FlowBuilder compliance."""
        # Check for required FlowBuilder fields
        if not step.get("time"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Delay step must have 'time' field",
                step_id=step_id,
                field="time",
                suggestion="Add 'time' field as string (e.g., '5')"
            ))

        if not step.get("period"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Delay step must have 'period' field",
                step_id=step_id,
                field="period",
                suggestion="Add 'period' field (e.g., 'Minutes', 'Hours')"
            ))

        # Check for delay object structure
        delay_obj = step.get("delay")
        if not delay_obj:
            self.issues.append(ValidationIssue(
                level="warning",
                category="schema",
                message="Delay step should have 'delay' object",
                step_id=step_id,
                field="delay",
                suggestion="Add 'delay' object with 'value' and 'unit' fields"
            ))
        elif not isinstance(delay_obj, dict) or not delay_obj.get("value") or not delay_obj.get("unit"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Delay object must have 'value' and 'unit' fields",
                step_id=step_id,
                field="delay",
                suggestion="Ensure 'delay' object has proper structure: {'value': '5', 'unit': 'Minutes'}"
            ))

    def _validate_segment_step_flowbuilder(self, step: Dict[str, Any], step_id: str) -> None:
        """Validate segment step FlowBuilder compliance."""
        # Check for conditions array (FlowBuilder preferred)
        if not step.get("conditions") and not step.get("segmentDefinition"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Segment step must have 'conditions' array or 'segmentDefinition'",
                step_id=step_id,
                field="conditions",
                suggestion="Add 'conditions' array with segment criteria"
            ))

        # Prefer conditions over segmentDefinition
        if step.get("segmentDefinition") and not step.get("conditions"):
            self.issues.append(ValidationIssue(
                level="warning",
                category="schema",
                message="Consider using 'conditions' array instead of 'segmentDefinition'",
                step_id=step_id,
                field="conditions",
                suggestion="Convert to FlowBuilder 'conditions' array format for better compatibility"
            ))

    def _validate_rate_limit_step_flowbuilder(self, step: Dict[str, Any], step_id: str) -> None:
        """Validate rate_limit step FlowBuilder compliance."""
        # Check for required FlowBuilder fields
        if not step.get("occurrences"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Rate limit step must have 'occurrences' field",
                step_id=step_id,
                field="occurrences",
                suggestion="Add 'occurrences' field as string (e.g., '12')"
            ))

        if not step.get("period"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Rate limit step must have 'period' field",
                step_id=step_id,
                field="period",
                suggestion="Add 'period' field (e.g., 'Minutes', 'Hours')"
            ))

        # Check for rateLimit object structure
        rate_limit_obj = step.get("rateLimit")
        if not rate_limit_obj:
            self.issues.append(ValidationIssue(
                level="warning",
                category="schema",
                message="Rate limit step should have 'rateLimit' object",
                step_id=step_id,
                field="rateLimit",
                suggestion="Add 'rateLimit' object with 'limit' and 'period' fields"
            ))
        elif not isinstance(rate_limit_obj, dict) or not rate_limit_obj.get("limit") or not rate_limit_obj.get("period"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Rate limit object must have 'limit' and 'period' fields",
                step_id=step_id,
                field="rateLimit",
                suggestion="Ensure 'rateLimit' object has proper structure: {'limit': '12', 'period': 'Minutes'}"
            ))

    def _validate_experiment_step_flowbuilder(self, step: Dict[str, Any], step_id: str) -> None:
        """Validate experiment step FlowBuilder compliance."""
        # Check for required FlowBuilder fields
        if not step.get("experimentName"):
            self.issues.append(ValidationIssue(
                level="error",
                category="schema",
                message="Experiment step must have 'experimentName' field",
                step_id=step_id,
                field="experimentName",
                suggestion="Add 'experimentName' field with a descriptive name"
            ))

        if not step.get("version"):
            self.issues.append(ValidationIssue(
                level="warning",
                category="schema",
                message="Experiment step should have 'version' field",
                step_id=step_id,
                field="version",
                suggestion="Add 'version' field (e.g., '1')"
            ))

        if not step.get("content"):
            self.issues.append(ValidationIssue(
                level="warning",
                category="schema",
                message="Experiment step should have 'content' field for display",
                step_id=step_id,
                field="content",
                suggestion="Add 'content' field with display text"
            ))

    def _validate_end_step_flowbuilder(self, step: Dict[str, Any], step_id: str) -> None:
        """Validate end step FlowBuilder compliance."""
        # Check for label field
        if not step.get("label"):
            self.issues.append(ValidationIssue(
                level="warning",
                category="schema",
                message="End step should have 'label' field",
                step_id=step_id,
                field="label",
                suggestion="Add 'label' field (e.g., 'End')"
            ))

    def _validate_events_flowbuilder(self, events: List[Dict[str, Any]], step_id: str) -> None:
        """Validate events for FlowBuilder compliance."""
        valid_event_types = ["reply", "noreply", "default", "split", "click", "purchase"]

        for event in events:
            event_id = event.get("id", "unknown")
            event_type = event.get("type", "")

            # Check event type validity
            if event_type not in valid_event_types:
                self.issues.append(ValidationIssue(
                    level="warning",
                    category="schema",
                    message=f"Event type '{event_type}' may not be FlowBuilder compliant",
                    step_id=step_id,
                    field=f"events.{event_id}.type",
                    suggestion="Use FlowBuilder event types: reply, noreply, default, split"
                ))

            # Validate reply events
            if event_type == "reply" and not event.get("intent"):
                self.issues.append(ValidationIssue(
                    level="error",
                    category="schema",
                    message="Reply event must have 'intent' field",
                    step_id=step_id,
                    field=f"events.{event_id}.intent",
                    suggestion="Add 'intent' field with the expected reply intent"
                ))

            # Validate noreply events
            if event_type == "noreply":
                after_obj = event.get("after")
                if not after_obj or not isinstance(after_obj, dict):
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Noreply event must have 'after' object",
                        step_id=step_id,
                        field=f"events.{event_id}.after",
                        suggestion="Add 'after' object with 'value' and 'unit' fields"
                    ))
                elif not after_obj.get("value") or not after_obj.get("unit"):
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="After object must have 'value' and 'unit' fields",
                        step_id=step_id,
                        field=f"events.{event_id}.after",
                        suggestion="Ensure 'after' object has proper structure: {'value': 6, 'unit': 'hours'}"
                    ))

            # Validate split events
            if event_type == "split":
                if not event.get("label"):
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Split event must have 'label' field",
                        step_id=step_id,
                        field=f"events.{event_id}.label",
                        suggestion="Add 'label' field describing the split condition"
                    ))

                if not event.get("action"):
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="schema",
                        message="Split event must have 'action' field",
                        step_id=step_id,
                        field=f"events.{event_id}.action",
                        suggestion="Add 'action' field (e.g., 'include', 'exclude')"
                    ))