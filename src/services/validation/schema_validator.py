"""
Comprehensive schema validator for campaign flows.

This module provides detailed validation of FlowBuilder schema compliance for all node types.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

from pydantic import ValidationError

from src.core.logging import get_logger
from src.models.flow_schema import (
    CampaignFlow,
    NodeType,
    DiscountType,
    TimePeriod,
    MessageType,
    ProductSelectionType,
    CartSourceType,
    ConditionType,
    EventAction,
    PropertyOperator,
)

logger = get_logger(__name__)


class ValidationIssue:
    """Represents a validation issue with severity and details."""

    def __init__(
        self,
        code: str,
        message: str,
        severity: str = "error",  # "error", "warning", "info"
        node_id: Optional[str] = None,
        event_id: Optional[str] = None,
        field_path: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.node_id = node_id
        self.event_id = event_id
        self.field_path = field_path
        self.suggested_fix = suggested_fix

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "node_id": self.node_id,
            "event_id": self.event_id,
            "field_path": self.field_path,
            "suggested_fix": self.suggested_fix,
        }


class ValidationResult:
    """Result of validation with issues and corrected data."""

    def __init__(self, is_valid: bool, issues: List[ValidationIssue], corrected_data: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.issues = issues
        self.corrected_data = corrected_data
        self.error_count = sum(1 for issue in issues if issue.severity == "error")
        self.warning_count = sum(1 for issue in issues if issue.severity == "warning")
        self.info_count = sum(1 for issue in issues if issue.severity == "info")

    def get_issues_by_severity(self, severity: str) -> List[ValidationIssue]:
        """Get issues filtered by severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return self.error_count > 0

    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return self.warning_count > 0


class SchemaValidator:
    """
    Comprehensive schema validator for FlowBuilder campaign flows.
    """

    def __init__(self):
        """Initialize schema validator."""
        # Validation rules and constraints
        self.max_message_length = 1600
        self.max_discount_percentage = 100
        self.max_delay_days = 365
        self.max_rate_limit_requests = 1000
        self.max_campaign_nodes = 100

        # Regex patterns
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
        self.id_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')

        # Required fields by node type
        self.required_fields = self._build_required_fields_map()

        logger.info("Schema validator initialized", extra={
            "max_message_length": self.max_message_length,
            "max_campaign_nodes": self.max_campaign_nodes,
        })

    def validate(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate campaign flow data against complete FlowBuilder schema.

        Args:
            flow_data: Dictionary representation of campaign flow

        Returns:
            ValidationResult with issues and any corrections
        """
        issues = []
        corrected_data = flow_data.copy()

        try:
            # Step 1: Basic structure validation
            structure_issues = self._validate_structure(flow_data, corrected_data)
            issues.extend(structure_issues)

            # Step 2: Node-specific validation
            if "steps" in flow_data:
                node_issues = self._validate_nodes(flow_data["steps"], corrected_data)
                issues.extend(node_issues)

            # Step 3: Cross-node validation
            cross_node_issues = self._validate_cross_node_references(flow_data, corrected_data)
            issues.extend(cross_node_issues)

            # Step 4: Business logic validation
            business_issues = self._validate_business_logic(flow_data, corrected_data)
            issues.extend(business_issues)

            # Determine validity
            is_valid = not any(issue.severity == "error" for issue in issues)

            # Determine if we have corrections
            has_corrections = corrected_data != flow_data
            final_corrected_data = corrected_data if has_corrections else None

            logger.info(
                "Schema validation completed",
                extra={
                    "is_valid": is_valid,
                    "total_issues": len(issues),
                    "error_count": sum(1 for issue in issues if issue.severity == "error"),
                    "warning_count": sum(1 for issue in issues if issue.severity == "warning"),
                    "node_count": len(flow_data.get("steps", [])),
                    "has_corrections": has_corrections,
                }
            )

            return ValidationResult(is_valid, issues, final_corrected_data)

        except Exception as e:
            logger.error(f"Schema validation failed with exception: {e}", exc_info=True)
            issues.append(ValidationIssue(
                code="VALIDATION_EXCEPTION",
                message=f"Validation failed with unexpected error: {e}",
                severity="error",
                suggested_fix="Check flow data format and try again"
            ))
            return ValidationResult(False, issues)

    def _build_required_fields_map(self) -> Dict[str, Set[str]]:
        """Build map of required fields by node type."""
        return {
            "message": {"type", "content", "text"},
            "segment": {"type", "conditions"},
            "delay": {"type", "time", "period"},
            "product_choice": {"type", "messageText"},
            "purchase_offer": {"type", "messageText", "cartSource"},
            "purchase": {"type", "cartSource"},
            "end": {"type", "label"},
        }

    def _validate_structure(self, flow_data: Dict[str, Any], corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate basic flow structure."""
        issues = []

        # Check required top-level fields
        if "initialStepID" not in flow_data:
            issues.append(ValidationIssue(
                code="MISSING_INITIAL_STEP_ID",
                message="Missing required field: initialStepID",
                severity="error",
                field_path="initialStepID",
                suggested_fix="Add initialStepID pointing to the first node"
            ))

        if "steps" not in flow_data:
            issues.append(ValidationIssue(
                code="MISSING_STEPS",
                message="Missing required field: steps",
                severity="error",
                field_path="steps",
                suggested_fix="Add steps array with at least one node"
            ))
            return issues

        # Validate steps structure
        steps = flow_data["steps"]
        if not isinstance(steps, list):
            issues.append(ValidationIssue(
                code="INVALID_STEPS_TYPE",
                message="steps must be an array",
                severity="error",
                field_path="steps",
                suggested_fix="Change steps to an array of node objects"
            ))
            return issues

        if len(steps) == 0:
            issues.append(ValidationIssue(
                code="EMPTY_STEPS",
                message="steps array cannot be empty",
                severity="error",
                field_path="steps",
                suggested_fix="Add at least one node to the steps array"
            ))

        if len(steps) > self.max_campaign_nodes:
            issues.append(ValidationIssue(
                code="TOO_MANY_NODES",
                message=f"Campaign has {len(steps)} nodes, maximum allowed is {self.max_campaign_nodes}",
                severity="warning",
                field_path="steps",
                suggested_fix="Consider breaking the campaign into smaller flows"
            ))

        # Validate initialStepID reference
        if "initialStepID" in flow_data and steps:
            step_ids = [step.get("id") for step in steps if "id" in step]
            if flow_data["initialStepID"] not in step_ids:
                issues.append(ValidationIssue(
                    code="INVALID_INITIAL_STEP_ID",
                    message=f"initialStepID '{flow_data['initialStepID']}' does not reference any existing node",
                    severity="error",
                    field_path="initialStepID",
                    suggested_fix="Set initialStepID to one of the existing node IDs"
                ))

        return issues

    def _validate_nodes(self, steps: List[Dict[str, Any]], corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate individual nodes."""
        issues = []
        node_ids = set()
        corrected_steps = []

        for i, node in enumerate(steps):
            node_issues = []
            corrected_node = node.copy()

            # Validate basic node structure
            node_issues.extend(self._validate_basic_node_structure(node, corrected_node, i))

            # Get node type
            node_type = node.get("type")
            if not node_type:
                node_issues.append(ValidationIssue(
                    code="MISSING_NODE_TYPE",
                    message="Node is missing required field: type",
                    severity="error",
                    node_id=node.get("id", f"node-{i}"),
                    field_path="steps[{i}].type",
                    suggested_fix="Add type field with valid node type"
                ))
                issues.extend(node_issues)
                continue

            # Validate node ID uniqueness
            node_id = node.get("id")
            if node_id:
                if node_id in node_ids:
                    node_issues.append(ValidationIssue(
                        code="DUPLICATE_NODE_ID",
                        message=f"Duplicate node ID: {node_id}",
                        severity="error",
                        node_id=node_id,
                        field_path=f"steps[{i}].id",
                        suggested_fix=f"Change node ID to a unique value"
                    ))
                else:
                    node_ids.add(node_id)

                # Validate ID format
                if not self.id_pattern.match(node_id):
                    node_issues.append(ValidationIssue(
                        code="INVALID_NODE_ID_FORMAT",
                        message=f"Node ID '{node_id}' contains invalid characters",
                        severity="warning",
                        node_id=node_id,
                        field_path=f"steps[{i}].id",
                        suggested_fix="Use only letters, numbers, hyphens, and underscores"
                    ))

            # Node-specific validation
            if node_type == "message":
                node_issues.extend(self._validate_message_node(node, corrected_node, i))
            elif node_type == "segment":
                node_issues.extend(self._validate_segment_node(node, corrected_node, i))
            elif node_type == "delay":
                node_issues.extend(self._validate_delay_node(node, corrected_node, i))
            elif node_type == "product_choice":
                node_issues.extend(self._validate_product_choice_node(node, corrected_node, i))
            elif node_type == "purchase_offer":
                node_issues.extend(self._validate_purchase_offer_node(node, corrected_node, i))
            elif node_type == "purchase":
                node_issues.extend(self._validate_purchase_node(node, corrected_node, i))
            elif node_type == "end":
                # Basic validation for end node
                node_issues.extend(self._validate_generic_node(node, corrected_node, i))
            else:
                # Unknown node type - add error
                issues.append(ValidationIssue(
                    code="UNKNOWN_NODE_TYPE",
                    message=f"Unknown node type: {node_type}. Valid types are: message, segment, delay, product_choice, purchase_offer, purchase, end",
                    severity="error",
                    node_id=node.get("id", f"node-{i}"),
                    field_path=f"steps[{i}].type",
                    suggested_fix="Use one of the valid node types"
                ))

            # Validate events
            if "events" in node:
                event_issues = self._validate_events(node["events"], node, corrected_node, i)
                node_issues.extend(event_issues)

            issues.extend(node_issues)
            corrected_steps.append(corrected_node)

        # Update corrected data
        # Always apply corrections for missing fields (even with errors)
        # The auto-correction system should fill in missing required fields
        corrected_data["steps"] = corrected_steps

        return issues

    def _validate_basic_node_structure(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate basic node structure."""
        issues = []

        # Validate required fields
        required_fields = {"type", "id"}
        for field in required_fields:
            if field not in node:
                issues.append(ValidationIssue(
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Missing required field: {field}",
                    severity="error",
                    node_id=node.get("id", f"node-{index}"),
                    field_path=f"steps[{index}].{field}",
                    suggested_fix=f"Add {field} field to the node"
                ))

        # Add default fields if missing
        if "active" not in node:
            corrected_node["active"] = True

        if "parameters" not in node:
            corrected_node["parameters"] = {}

        if "events" not in node:
            corrected_node["events"] = []

        return issues

    def _validate_message_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate message node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Check content
        content = node.get("content")
        if not content:
            issues.append(ValidationIssue(
                code="MISSING_MESSAGE_CONTENT",
                message="Message node missing required content",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].content",
                suggested_fix="Add content field with message text"
            ))
        else:
            # Validate content length
            if len(content) > self.max_message_length:
                issues.append(ValidationIssue(
                    code="MESSAGE_TOO_LONG",
                    message=f"Message content is {len(content)} characters, maximum recommended is {self.max_message_length}",
                    severity="warning",
                    node_id=node_id,
                    field_path=f"steps[{index}].content",
                    suggested_fix="Shorten message content or split into multiple messages"
                ))

            # Check for template variables
            template_vars = re.findall(r'\{\{([^}]+)\}\}', content)
            if template_vars:
                # Validate template variables
                valid_vars = {
                    "brand_name", "store_url", "first_name", "customer_timezone",
                    "agent_name", "opt_in_terms", "Product List", "Cart List"
                }
                for var in template_vars:
                    if var.strip() not in valid_vars:
                        issues.append(ValidationIssue(
                            code="INVALID_TEMPLATE_VARIABLE",
                            message=f"Unknown template variable: {{{{{var}}}}}",
                            severity="warning",
                            node_id=node_id,
                            field_path=f"steps[{index}].content",
                            suggested_fix=f"Use valid template variables: {', '.join(valid_vars)}"
                        ))

        # Validate discount settings
        discount_type = node.get("discountType", "none")
        if discount_type != "none":
            if discount_type not in [dt.value for dt in DiscountType]:
                issues.append(ValidationIssue(
                    code="INVALID_DISCOUNT_TYPE",
                    message=f"Invalid discount type: {discount_type}",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].discountType",
                    suggested_fix=f"Use valid discount type: {', '.join([dt.value for dt in DiscountType])}"
                ))

            if discount_type == DiscountType.PERCENTAGE.value:
                discount_value = node.get("discountValue")
                if not discount_value:
                    issues.append(ValidationIssue(
                        code="MISSING_DISCOUNT_VALUE",
                        message="Percentage discount missing discountValue",
                        severity="error",
                        node_id=node_id,
                        field_path=f"steps[{index}].discountValue",
                        suggested_fix="Add discountValue with percentage number (e.g., '20')"
                    ))
                else:
                    try:
                        percentage = float(discount_value)
                        if percentage <= 0 or percentage > self.max_discount_percentage:
                            issues.append(ValidationIssue(
                                code="INVALID_DISCOUNT_PERCENTAGE",
                                message=f"Discount percentage {percentage} must be between 1 and {self.max_discount_percentage}",
                                severity="error",
                                node_id=node_id,
                                field_path=f"steps[{index}].discountValue",
                                suggested_fix=f"Set discountValue to a valid percentage between 1 and {self.max_discount_percentage}"
                            ))
                    except ValueError:
                        issues.append(ValidationIssue(
                            code="INVALID_DISCOUNT_VALUE_FORMAT",
                            message=f"discountValue '{discount_value}' must be a valid number",
                            severity="error",
                            node_id=node_id,
                            field_path=f"steps[{index}].discountValue",
                            suggested_fix="Set discountValue to a valid number (e.g., '20')"
                        ))

            elif discount_type == DiscountType.CODE.value:
                discount_code = node.get("discountCode")
                if not discount_code:
                    issues.append(ValidationIssue(
                        code="MISSING_DISCOUNT_CODE",
                        message="Code discount missing discountCode",
                        severity="error",
                        node_id=node_id,
                        field_path=f"steps[{index}].discountCode",
                        suggested_fix="Add discountCode with the discount code"
                    ))

        # Validate image URL if present
        if node.get("addImage", False):
            image_url = node.get("imageUrl")
            if not image_url:
                issues.append(ValidationIssue(
                    code="MISSING_IMAGE_URL",
                    message="addImage is true but imageUrl is missing",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].imageUrl",
                    suggested_fix="Add imageUrl field with valid image URL"
                ))
            else:
                if not self.url_pattern.match(image_url):
                    issues.append(ValidationIssue(
                        code="INVALID_IMAGE_URL",
                        message=f"Invalid image URL format: {image_url}",
                        severity="warning",
                        node_id=node_id,
                        field_path=f"steps[{index}].imageUrl",
                        suggested_fix="Use a valid URL starting with http:// or https://"
                    ))

        return issues

    def _validate_segment_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate segment node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Check conditions
        conditions = node.get("conditions", [])
        segment_definition = node.get("segmentDefinition")

        if not conditions and not segment_definition:
            issues.append(ValidationIssue(
                code="MISSING_SEGMENT_CONDITIONS",
                message="Segment node must have either conditions or segmentDefinition",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].conditions",
                suggested_fix="Add conditions array or segmentDefinition object"
            ))

        # Validate conditions if present
        if conditions:
            if not isinstance(conditions, list):
                issues.append(ValidationIssue(
                    code="INVALID_CONDITIONS_TYPE",
                    message="conditions must be an array",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].conditions",
                    suggested_fix="Change conditions to an array of condition objects"
                ))
            else:
                for j, condition in enumerate(conditions):
                    condition_issues = self._validate_condition(condition, node_id, index, j)
                    issues.extend(condition_issues)

        # Validate events - segment nodes should typically have split events
        events = node.get("events", [])
        if len(events) < 2:
            issues.append(ValidationIssue(
                code="INSUFFICIENT_SEGMENT_EVENTS",
                message="Segment nodes typically need at least 2 events (include/exclude branches)",
                severity="warning",
                node_id=node_id,
                field_path=f"steps[{index}].events",
                suggested_fix="Add split events for include and exclude branches"
            ))

        return issues

    def _validate_condition(self, condition: Dict[str, Any], node_id: str, node_index: int, condition_index: int) -> List[ValidationIssue]:
        """Validate individual condition."""
        issues = []
        field_path = f"steps[{node_index}].conditions[{condition_index}]"

        # Required fields
        required_fields = {"id", "type", "operator"}
        for field in required_fields:
            if field not in condition:
                issues.append(ValidationIssue(
                    code="MISSING_CONDITION_FIELD",
                    message=f"Condition missing required field: {field}",
                    severity="error",
                    node_id=node_id,
                    field_path=f"{field_path}.{field}",
                    suggested_fix=f"Add {field} field to the condition"
                ))

        # Validate condition type
        condition_type = condition.get("type")
        if condition_type and condition_type not in [ct.value for ct in ConditionType]:
            issues.append(ValidationIssue(
                code="INVALID_CONDITION_TYPE",
                message=f"Invalid condition type: {condition_type}",
                severity="error",
                node_id=node_id,
                field_path=f"{field_path}.type",
                suggested_fix=f"Use valid condition type: {', '.join([ct.value for ct in ConditionType])}"
            ))

        # Validate type-specific fields
        if condition_type == ConditionType.EVENT.value:
            if "action" not in condition:
                issues.append(ValidationIssue(
                    code="MISSING_EVENT_ACTION",
                    message="Event condition missing action field",
                    severity="error",
                    node_id=node_id,
                    field_path=f"{field_path}.action",
                    suggested_fix="Add action field with valid event action"
                ))
            else:
                action = condition["action"]
                if action not in [ea.value for ea in EventAction]:
                    issues.append(ValidationIssue(
                        code="INVALID_EVENT_ACTION",
                        message=f"Invalid event action: {action}",
                        severity="error",
                        node_id=node_id,
                        field_path=f"{field_path}.action",
                        suggested_fix=f"Use valid event action: {', '.join([ea.value for ea in EventAction])}"
                    ))

        elif condition_type == ConditionType.PROPERTY.value:
            if "propertyName" not in condition:
                issues.append(ValidationIssue(
                    code="MISSING_PROPERTY_NAME",
                    message="Property condition missing propertyName",
                    severity="error",
                    node_id=node_id,
                    field_path=f"{field_path}.propertyName",
                    suggested_fix="Add propertyName field with the property name"
                ))

            if "propertyValue" not in condition:
                issues.append(ValidationIssue(
                    code="MISSING_PROPERTY_VALUE",
                    message="Property condition missing propertyValue",
                    severity="error",
                    node_id=node_id,
                    field_path=f"{field_path}.propertyValue",
                    suggested_fix="Add propertyValue field with the property value"
                ))

            if "propertyOperator" not in condition:
                issues.append(ValidationIssue(
                    code="MISSING_PROPERTY_OPERATOR",
                    message="Property condition missing propertyOperator",
                    severity="error",
                    node_id=node_id,
                    field_path=f"{field_path}.propertyOperator",
                    suggested_fix=f"Add propertyOperator field with valid operator"
                ))

        return issues

    def _validate_delay_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate delay node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Validate time
        time_value = node.get("time")
        if not time_value:
            issues.append(ValidationIssue(
                code="MISSING_DELAY_TIME",
                message="Delay node missing required time field",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].time",
                suggested_fix="Add time field with delay value as string"
            ))
        else:
            try:
                time_num = float(time_value)
                if time_num <= 0:
                    issues.append(ValidationIssue(
                        code="INVALID_DELAY_TIME",
                        message=f"Delay time must be positive, got: {time_value}",
                        severity="error",
                        node_id=node_id,
                        field_path=f"steps[{index}].time",
                        suggested_fix="Set time to a positive number"
                    ))

                # Check maximum delay
                period = node.get("period", "Minutes")
                if period == "Days" and time_num > self.max_delay_days:
                    issues.append(ValidationIssue(
                        code="DELAY_TOO_LONG",
                        message=f"Delay of {time_value} days exceeds maximum of {self.max_delay_days} days",
                        severity="warning",
                        node_id=node_id,
                        field_path=f"steps[{index}].time",
                        suggested_fix=f"Reduce delay to {self.max_delay_days} days or less"
                    ))

            except ValueError:
                issues.append(ValidationIssue(
                    code="INVALID_DELAY_TIME_FORMAT",
                    message=f"Delay time must be a valid number, got: {time_value}",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].time",
                    suggested_fix="Set time to a valid number as string"
                ))

        # Validate period
        period = node.get("period")
        if not period:
            issues.append(ValidationIssue(
                code="MISSING_DELAY_PERIOD",
                message="Delay node missing required period field",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].period",
                suggested_fix="Add period field with valid time unit"
            ))
        elif period not in [tp.value for tp in TimePeriod]:
            issues.append(ValidationIssue(
                code="INVALID_DELAY_PERIOD",
                message=f"Invalid delay period: {period}",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].period",
                suggested_fix=f"Use valid period: {', '.join([tp.value for tp in TimePeriod])}"
            ))

        # Validate structured delay format
        delay_dict = node.get("delay", {})
        if delay_dict:
            if delay_dict.get("value") != time_value:
                issues.append(ValidationIssue(
                    code="MISMATCHED_DELAY_VALUE",
                    message="delay.value must match time field",
                    severity="warning",
                    node_id=node_id,
                    field_path=f"steps[{index}].delay.value",
                    suggested_fix="Set delay.value to match time field"
                ))

            if delay_dict.get("unit") != period:
                issues.append(ValidationIssue(
                    code="MISMATCHED_DELAY_UNIT",
                    message="delay.unit must match period field",
                    severity="warning",
                    node_id=node_id,
                    field_path=f"steps[{index}].delay.unit",
                    suggested_fix="Set delay.unit to match period field"
                ))

        return issues

    def _validate_product_choice_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate product choice node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Validate messageText
        message_text = node.get("messageText")
        if not message_text:
            issues.append(ValidationIssue(
                code="MISSING_MESSAGE_TEXT",
                message="Product choice node missing required messageText",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].messageText",
                suggested_fix="Add messageText field with product selection message"
            ))

        # Validate productSelection
        product_selection = node.get("productSelection")
        if product_selection and product_selection not in [pst.value for pst in ProductSelectionType]:
            issues.append(ValidationIssue(
                code="INVALID_PRODUCT_SELECTION",
                message=f"Invalid productSelection: {product_selection}",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].productSelection",
                suggested_fix=f"Use valid productSelection: {', '.join([pst.value for pst in ProductSelectionType])}"
            ))

        # Validate products array for manual selection
        if product_selection == ProductSelectionType.MANUALLY.value:
            products = node.get("products", [])
            if not products:
                issues.append(ValidationIssue(
                    code="MISSING_MANUAL_PRODUCTS",
                    message="Manual product selection requires products array",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].products",
                    suggested_fix="Add products array with product objects"
                ))
            else:
                if not isinstance(products, list):
                    issues.append(ValidationIssue(
                        code="INVALID_PRODUCTS_TYPE",
                        message="products must be an array",
                        severity="error",
                        node_id=node_id,
                        field_path=f"steps[{index}].products",
                        suggested_fix="Change products to an array of product objects"
                    ))
                else:
                    for j, product in enumerate(products):
                        if not product.get("id"):
                            issues.append(ValidationIssue(
                                code="MISSING_PRODUCT_ID",
                                message=f"Product {j} missing required id field",
                                severity="error",
                                node_id=node_id,
                                field_path=f"steps[{index}].products[{j}].id",
                                suggested_fix="Add id field to the product"
                            ))

        return issues

    def _validate_purchase_offer_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate purchase offer node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Validate messageText
        message_text = node.get("messageText")
        if not message_text:
            issues.append(ValidationIssue(
                code="MISSING_MESSAGE_TEXT",
                message="Purchase offer node missing required messageText",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].messageText",
                suggested_fix="Add messageText field with purchase offer message"
            ))

        # Validate cartSource
        cart_source = node.get("cartSource")
        if cart_source and cart_source not in [cst.value for cst in CartSourceType]:
            issues.append(ValidationIssue(
                code="INVALID_CART_SOURCE",
                message=f"Invalid cartSource: {cart_source}",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].cartSource",
                suggested_fix=f"Use valid cartSource: {', '.join([cst.value for cst in CartSourceType])}"
            ))

        # Validate products for manual cart source
        if cart_source == CartSourceType.MANUAL.value:
            products = node.get("products", [])
            if not products:
                issues.append(ValidationIssue(
                    code="MISSING_MANUAL_PRODUCTS",
                    message="Manual cart source requires products array",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].products",
                    suggested_fix="Add products array with product variant objects"
                ))

        # Validate discount settings if enabled
        if node.get("discount", False):
            discount_type = node.get("discountType")
            if discount_type == DiscountType.PERCENTAGE.value and not node.get("discountPercentage"):
                issues.append(ValidationIssue(
                    code="MISSING_DISCOUNT_PERCENTAGE",
                    message="Discount enabled but discountPercentage missing",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].discountPercentage",
                    suggested_fix="Add discountPercentage field or set discount to false"
                ))

        return issues

    def _validate_purchase_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate purchase node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Validate cartSource
        cart_source = node.get("cartSource")
        if not cart_source:
            issues.append(ValidationIssue(
                code="MISSING_CART_SOURCE",
                message="Purchase node missing required cartSource",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].cartSource",
                suggested_fix="Add cartSource field with valid source type"
            ))
        elif cart_source not in [cst.value for cst in CartSourceType]:
            issues.append(ValidationIssue(
                code="INVALID_CART_SOURCE",
                message=f"Invalid cartSource: {cart_source}",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].cartSource",
                suggested_fix=f"Use valid cartSource: {', '.join([cst.value for cst in CartSourceType])}"
            ))

        # Validate products for manual cart source
        if cart_source == CartSourceType.MANUAL.value:
            products = node.get("products", [])
            if not products:
                issues.append(ValidationIssue(
                    code="MISSING_MANUAL_PRODUCTS",
                    message="Manual cart source requires products array",
                    severity="warning",
                    node_id=node_id,
                    field_path=f"steps[{index}].products",
                    suggested_fix="Add products array with product variant objects"
                ))

        return issues

    def _validate_rate_limit_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate rate limit node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Validate occurrences
        occurrences = node.get("occurrences")
        if not occurrences:
            issues.append(ValidationIssue(
                code="MISSING_RATE_LIMIT_OCCURRENCES",
                message="Rate limit node missing required occurrences",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].occurrences",
                suggested_fix="Add occurrences field with number as string"
            ))
        else:
            try:
                occ_num = int(occurrences)
                if occ_num <= 0 or occ_num > self.max_rate_limit_requests:
                    issues.append(ValidationIssue(
                        code="INVALID_RATE_LIMIT_OCCURRENCES",
                        message=f"Rate limit occurrences {occ_num} must be between 1 and {self.max_rate_limit_requests}",
                        severity="error",
                        node_id=node_id,
                        field_path=f"steps[{index}].occurrences",
                        suggested_fix=f"Set occurrences to a value between 1 and {self.max_rate_limit_requests}"
                    ))
            except ValueError:
                issues.append(ValidationIssue(
                    code="INVALID_RATE_LIMIT_OCCURRENCES_FORMAT",
                    message=f"Rate limit occurrences must be a valid integer, got: {occurrences}",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].occurrences",
                    suggested_fix="Set occurrences to a valid integer as string"
                ))

        return issues

    def _validate_limit_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate limit node."""
        # Limit node has same structure as rate_limit
        return self._validate_rate_limit_node(node, corrected_node, index)

    def _validate_reply_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate reply node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Check required fields
        if "enabled" not in node:
            issues.append(ValidationIssue(
                code="MISSING_REPLY_ENABLED",
                message="Reply node missing required enabled field",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].enabled",
                suggested_fix="Add enabled field with boolean value (true/false)"
            ))
            corrected_node["enabled"] = True

        if "intent" not in node:
            issues.append(ValidationIssue(
                code="MISSING_REPLY_INTENT",
                message="Reply node missing required intent",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].intent",
                suggested_fix="Add intent field with the intent to match (e.g., 'yes', 'no')"
            ))

        if "description" not in node:
            issues.append(ValidationIssue(
                code="MISSING_REPLY_DESCRIPTION",
                message="Reply node missing required description",
                severity="warning",
                node_id=node_id,
                field_path=f"steps[{index}].description",
                suggested_fix="Add description field for better intent matching"
            ))
            corrected_node["description"] = f"Handle {node.get('intent', 'reply')} intent"

        if "label" not in node:
            corrected_node["label"] = node.get("intent", "reply")

        return issues

    def _validate_no_reply_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate no_reply node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Check required fields
        if "enabled" not in node:
            issues.append(ValidationIssue(
                code="MISSING_NO_REPLY_ENABLED",
                message="NoReply node missing required enabled field",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].enabled",
                suggested_fix="Add enabled field with boolean value (true/false)"
            ))
            corrected_node["enabled"] = True

        if "value" not in node:
            issues.append(ValidationIssue(
                code="MISSING_NO_REPLY_VALUE",
                message="NoReply node missing required value",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].value",
                suggested_fix="Add value field with numeric wait time"
            ))
            corrected_node["value"] = 2

        if "unit" not in node:
            issues.append(ValidationIssue(
                code="MISSING_NO_REPLY_UNIT",
                message="NoReply node missing required unit",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].unit",
                suggested_fix="Add unit field with time unit ('seconds', 'minutes', 'hours', 'days')"
            ))
            corrected_node["unit"] = "hours"

        # Validate after structure
        if "after" not in node:
            value = node.get("value", 2)
            unit = node.get("unit", "hours")
            corrected_node["after"] = {"value": value, "unit": unit}

        # Validate content display
        if "content" not in node:
            value = node.get("value", 2)
            unit = node.get("unit", "hours")
            corrected_node["content"] = f"Display content: {value} {unit}"

        # Validate legacy fields
        if "seconds" not in node:
            value = int(node.get("value", 2))
            unit = node.get("unit", "hours").lower()
            if unit == "hours":
                seconds = value * 3600
            elif unit == "minutes":
                seconds = value * 60
            else:
                seconds = value
            corrected_node["seconds"] = seconds

        if "period" not in node:
            unit = node.get("unit", "hours")
            corrected_node["period"] = unit.capitalize()

        return issues

    def _validate_split_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate split node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Check required fields
        if "enabled" not in node:
            issues.append(ValidationIssue(
                code="MISSING_SPLIT_ENABLED",
                message="Split node missing required enabled field",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].enabled",
                suggested_fix="Add enabled field with boolean value (true/false)"
            ))
            corrected_node["enabled"] = True

        if "action" not in node:
            issues.append(ValidationIssue(
                code="MISSING_SPLIT_ACTION",
                message="Split node missing required action",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].action",
                suggested_fix="Add action field with value ('include' or 'exclude')"
            ))
            corrected_node["action"] = "include"

        # Validate action value
        action = node.get("action")
        if action and action not in ["include", "exclude"]:
            issues.append(ValidationIssue(
                code="INVALID_SPLIT_ACTION",
                message=f"Split action must be 'include' or 'exclude', got: {action}",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].action",
                suggested_fix="Set action to 'include' or 'exclude'"
            ))

        # Validate label
        if "label" not in node:
            action = node.get("action", "include")
            corrected_node["label"] = action

        # Validate content display
        if "content" not in node:
            action = node.get("action", "include")
            corrected_node["content"] = f"Display content: {action}"

        return issues

    def _validate_property_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate property node."""
        issues = []
        node_id = node.get("id", f"node-{index}")

        # Check properties array
        if "properties" not in node:
            issues.append(ValidationIssue(
                code="MISSING_PROPERTY_ARRAY",
                message="Property node missing required properties array",
                severity="error",
                node_id=node_id,
                field_path=f"steps[{index}].properties",
                suggested_fix="Add properties array with property objects"
            ))
            corrected_node["properties"] = []
        else:
            properties = node["properties"]
            if not isinstance(properties, list):
                issues.append(ValidationIssue(
                    code="INVALID_PROPERTY_ARRAY",
                    message="Properties field must be an array",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].properties",
                    suggested_fix="Set properties to an array of property objects"
                ))
                corrected_node["properties"] = []
            else:
                # Validate each property
                for i, prop in enumerate(properties):
                    if not isinstance(prop, dict):
                        issues.append(ValidationIssue(
                            code="INVALID_PROPERTY_OBJECT",
                            message=f"Property {i} must be an object",
                            severity="error",
                            node_id=node_id,
                            field_path=f"steps[{index}].properties[{i}]",
                            suggested_fix="Set each property to an object with 'id', 'name', and 'value' fields"
                        ))
                        continue

                    # Check required fields for each property
                    if "id" not in prop:
                        issues.append(ValidationIssue(
                            code="MISSING_PROPERTY_ID",
                            message=f"Property {i} missing required id field",
                            severity="error",
                            node_id=node_id,
                            field_path=f"steps[{index}].properties[{i}].id",
                            suggested_fix="Add id field with numeric identifier"
                        ))

                    if "name" not in prop:
                        issues.append(ValidationIssue(
                            code="MISSING_PROPERTY_NAME",
                            message=f"Property {i} missing required name field",
                            severity="error",
                            node_id=node_id,
                            field_path=f"steps[{index}].properties[{i}].name",
                            suggested_fix="Add name field with property name"
                        ))

                    if "value" not in prop:
                        issues.append(ValidationIssue(
                            code="MISSING_PROPERTY_VALUE",
                            message=f"Property {i} missing required value field",
                            severity="error",
                            node_id=node_id,
                            field_path=f"steps[{index}].properties[{i}].value",
                            suggested_fix="Add value field with property value"
                        ))

        # Set default label if missing
        if "label" not in node:
            corrected_node["label"] = "Customer Property Step"

        # Set default content if missing
        if "content" not in node:
            corrected_node["content"] = "Display content: Customer Property Step"

        return issues

    def _validate_split_group_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate split group node."""
        # Split group node has same structure as split node but used for experiment branches
        return self._validate_split_node(node, corrected_node, index)

    def _validate_split_range_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate split range node."""
        # Split range node has same structure as split node but used for schedule branches
        return self._validate_split_node(node, corrected_node, index)

    def _validate_generic_node(self, node: Dict[str, Any], corrected_node: Dict[str, Any], index: int) -> List[ValidationIssue]:
        """Validate generic node types (experiment, schedule, end)."""
        issues = []
        node_id = node.get("id", f"node-{index}")
        node_type = node.get("type")

        # Basic validation for remaining node types
        if node_type == "experiment":
            if not node.get("experimentName"):
                issues.append(ValidationIssue(
                    code="MISSING_EXPERIMENT_NAME",
                    message="Experiment node missing required experimentName",
                    severity="error",
                    node_id=node_id,
                    field_path=f"steps[{index}].experimentName",
                    suggested_fix="Add experimentName field with experiment name"
                ))
                corrected_node["experimentName"] = "Default Experiment"

              # No additional validation needed for schedule and end nodes

        return issues

    def _validate_events(self, events: List[Dict[str, Any]], node: Dict[str, Any], corrected_node: Dict[str, Any], node_index: int) -> List[ValidationIssue]:
        """Validate node events."""
        issues = []
        node_id = node.get("id", f"node-{node_index}")
        corrected_events = []

        for i, event in enumerate(events):
            event_issues = []
            corrected_event = event.copy()
            event_id = event.get("id", f"event-{node_index}-{i}")

            # Validate event type
            event_type = event.get("type")
            if not event_type:
                event_issues.append(ValidationIssue(
                    code="MISSING_EVENT_TYPE",
                    message="Event missing required type",
                    severity="error",
                    node_id=node_id,
                    event_id=event_id,
                    field_path=f"steps[{node_index}].events[{i}].type",
                    suggested_fix="Add type field with valid event type"
                ))

            # Validate nextStepID
            next_step_id = event.get("nextStepID")
            if not next_step_id:
                event_issues.append(ValidationIssue(
                    code="MISSING_NEXT_STEP_ID",
                    message="Event missing required nextStepID",
                    severity="error",
                    node_id=node_id,
                    event_id=event_id,
                    field_path=f"steps[{node_index}].events[{i}].nextStepID",
                    suggested_fix="Add nextStepID field pointing to the next node"
                ))

            # Type-specific validation
            if event_type == "reply":
                if not event.get("intent"):
                    event_issues.append(ValidationIssue(
                        code="MISSING_REPLY_INTENT",
                        message="Reply event missing required intent",
                        severity="error",
                        node_id=node_id,
                        event_id=event_id,
                        field_path=f"steps[{node_index}].events[{i}].intent",
                        suggested_fix="Add intent field with the intent to match"
                    ))

            elif event_type == "noreply":
                if not event.get("after"):
                    event_issues.append(ValidationIssue(
                        code="MISSING_NOREPLY_AFTER",
                        message="NoReply event missing required after object",
                        severity="error",
                        node_id=node_id,
                        event_id=event_id,
                        field_path=f"steps[{node_index}].events[{i}].after",
                        suggested_fix="Add after object with value and unit"
                    ))

            elif event_type == "split":
                if not event.get("label"):
                    event_issues.append(ValidationIssue(
                        code="MISSING_SPLIT_LABEL",
                        message="Split event missing required label",
                        severity="error",
                        node_id=node_id,
                        event_id=event_id,
                        field_path=f"steps[{node_index}].events[{i}].label",
                        suggested_fix="Add label field with split condition label"
                    ))

                if not event.get("action"):
                    event_issues.append(ValidationIssue(
                        code="MISSING_SPLIT_ACTION",
                        message="Split event missing required action",
                        severity="error",
                        node_id=node_id,
                        event_id=event_id,
                        field_path=f"steps[{node_index}].events[{i}].action",
                        suggested_fix="Add action field with split action"
                    ))

            # Add default fields if missing
            if "active" not in event:
                corrected_event["active"] = True

            if "parameters" not in event:
                corrected_event["parameters"] = {}

            issues.extend(event_issues)
            corrected_events.append(corrected_event)

        # Update corrected data if no errors
        if not any(issue.severity == "error" for issue in issues):
            corrected_node["events"] = corrected_events

        return issues

    def _validate_cross_node_references(self, flow_data: Dict[str, Any], corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate references between nodes."""
        issues = []
        steps = flow_data.get("steps", [])

        if not steps:
            return issues

        # Collect all node IDs
        node_ids = {step.get("id") for step in steps if "id" in step}

        # Validate all event references
        for i, node in enumerate(steps):
            node_id = node.get("id", f"node-{i}")
            events = node.get("events", [])

            for j, event in enumerate(events):
                event_id = event.get("id", f"event-{i}-{j}")
                next_step_id = event.get("nextStepID")

                if next_step_id and next_step_id not in node_ids:
                    issues.append(ValidationIssue(
                        code="INVALID_NEXT_STEP_REFERENCE",
                        message=f"Event references non-existent node: {next_step_id}",
                        severity="error",
                        node_id=node_id,
                        event_id=event_id,
                        field_path=f"steps[{i}].events[{j}].nextStepID",
                        suggested_fix=f"Set nextStepID to an existing node ID or add missing node"
                    ))

        return issues

    def _validate_business_logic(self, flow_data: Dict[str, Any], corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate business logic and best practices."""
        issues = []
        steps = flow_data.get("steps", [])

        # Check for end nodes
        end_nodes = [step for step in steps if step.get("type") == "end"]
        if not end_nodes:
            issues.append(ValidationIssue(
                code="MISSING_END_NODE",
                message="Campaign flow should have at least one END node",
                severity="warning",
                field_path="steps",
                suggested_fix="Add an END node to terminate the flow"
            ))

        # Check for unreachable nodes (basic check)
        if steps and "initialStepID" in flow_data:
            initial_id = flow_data["initialStepID"]
            reachable_ids = set()

            # Simple reachability check
            def collect_reachable(node_id: str, visited: Set[str] = None):
                if visited is None:
                    visited = set()
                if node_id in visited or node_id in reachable_ids:
                    return
                visited.add(node_id)
                reachable_ids.add(node_id)

                # Find the node
                for step in steps:
                    if step.get("id") == node_id:
                        # Collect next steps from events
                        for event in step.get("events", []):
                            next_id = event.get("nextStepID")
                            if next_id:
                                collect_reachable(next_id, visited)
                        break

            collect_reachable(initial_id)

            for step in steps:
                step_id = step.get("id")
                if step_id and step_id not in reachable_ids:
                    issues.append(ValidationIssue(
                        code="UNREACHABLE_NODE",
                        message=f"Node '{step_id}' is not reachable from the initial step",
                        severity="warning",
                        node_id=step_id,
                        field_path="steps",
                        suggested_fix="Ensure all nodes are reachable through event connections"
                    ))

        return issues


# Global schema validator instance
_schema_validator: Optional[SchemaValidator] = None


def get_schema_validator() -> SchemaValidator:
    """Get global schema validator instance."""
    global _schema_validator
    if _schema_validator is None:
        _schema_validator = SchemaValidator()
    return _schema_validator