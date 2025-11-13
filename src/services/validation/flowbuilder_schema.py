"""
FlowBuilder Schema Validator and Normalizer

This module provides validation and normalization functions to ensure
generated campaign flows match the exact FlowBuilder schema specification.
"""

import json
from typing import Dict, Any, List, Optional
from copy import deepcopy

class FlowBuilderSchemaValidator:
    """Validates and normalizes campaign flows to match FlowBuilder schema."""

    # Required root fields
    REQUIRED_ROOT_FIELDS = ["name", "description", "initialStepID", "steps"]

    # Valid node types - from format_json_flowbuilder.md
    VALID_NODE_TYPES = {
        "message", "delay", "segment", "product_choice", "purchase",
        "purchase_offer", "reply_cart_choice", "no_reply", "end", "start",
        "property", "rate_limit", "limit", "split", "reply", "experiment",
        "quiz", "schedule", "split_group", "split_range"
    }

    # Valid event types
    VALID_EVENT_TYPES = {"reply", "noreply", "split", "default"}

    # Valid time periods
    VALID_PERIODS = {"Seconds", "Minutes", "Hours", "Days"}
    VALID_UNITS = {"seconds", "minutes", "hours", "days"}

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_and_normalize(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize a flow to match FlowBuilder schema.

        Args:
            flow_data: Raw flow data from LLM

        Returns:
            Normalized flow data matching FlowBuilder schema
        """
        self.errors = []
        self.warnings = []

        # Deep copy to avoid modifying original
        normalized_flow = deepcopy(flow_data)

        # Validate and normalize root structure
        self._normalize_root_structure(normalized_flow)

        # Validate and normalize steps
        if "steps" in normalized_flow:
            normalized_steps = []
            for step in normalized_flow["steps"]:
                normalized_step = self._normalize_step(step)
                if normalized_step:
                    normalized_steps.append(normalized_step)
            normalized_flow["steps"] = normalized_steps

        # Validate step references
        self._validate_step_references(normalized_flow)

        return normalized_flow

    def _normalize_root_structure(self, flow: Dict[str, Any]) -> None:
        """Normalize root level structure."""
        # Add missing required fields with defaults
        if "name" not in flow:
            flow["name"] = f"Generated Campaign {flow.get('initialStepID', 'Unknown')}"
            self.warnings.append("Added missing 'name' field to root")

        if "description" not in flow:
            # Extract from metadata if available
            description = flow.get("metadata", {}).get("campaign_description", "Auto-generated campaign")
            flow["description"] = description
            self.warnings.append("Added missing 'description' field to root")

        # Validate initialStepID exists and points to a valid step
        if "initialStepID" not in flow:
            if flow.get("steps"):
                flow["initialStepID"] = flow["steps"][0]["id"]
                self.warnings.append("Set initialStepID to first step")
            else:
                self.errors.append("No initialStepID found and no steps available")

    def _normalize_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize a single step."""
        step_type = step.get("type", "")

        # Validate step type
        if step_type not in self.VALID_NODE_TYPES:
            self.errors.append(f"Invalid node type: {step_type}")
            return None

        # Ensure required base fields (from format_json_flowbuilder.md)
        if "id" not in step:
            self.errors.append(f"Step missing required 'id' field: {step}")
            return None

        if "type" not in step:
            self.errors.append(f"Step missing required 'type' field: {step}")
            return None

        if "label" not in step:
            step["label"] = step["id"].replace("-", " ").title()
            self.warnings.append(f"Added missing 'label' for step {step['id']}")

        if "content" not in step:
            step["content"] = f"Step {step['label']}"
            self.warnings.append(f"Added missing 'content' for step {step['id']}")

        # Set default values (from format_json_flowbuilder.md)
        step.setdefault("active", True)
        step.setdefault("parameters", {})

        # Normalize based on step type
        if step_type == "message":
            return self._normalize_message_step(step)
        elif step_type == "delay":
            return self._normalize_delay_step(step)
        elif step_type == "segment":
            return self._normalize_segment_step(step)
        elif step_type == "product_choice":
            return self._normalize_product_choice_step(step)
        elif step_type == "purchase":
            return self._normalize_purchase_step(step)
        elif step_type == "purchase_offer":
            return self._normalize_purchase_offer_step(step)
        elif step_type == "reply_cart_choice":
            return self._normalize_reply_cart_choice_step(step)
        elif step_type == "no_reply":
            return self._normalize_no_reply_step(step)
        elif step_type == "end":
            return self._normalize_end_step(step)
        elif step_type == "start":
            return self._normalize_start_step(step)
        elif step_type == "property":
            return self._normalize_property_step(step)
        elif step_type == "rate_limit":
            return self._normalize_rate_limit_step(step)
        elif step_type == "limit":
            return self._normalize_limit_step(step)
        elif step_type == "split":
            return self._normalize_split_step(step)
        elif step_type == "reply":
            return self._normalize_reply_step(step)
        elif step_type == "experiment":
            return self._normalize_experiment_step(step)
        elif step_type == "quiz":
            return self._normalize_quiz_step(step)
        elif step_type == "schedule":
            return self._normalize_schedule_step(step)
        elif step_type == "split_group":
            return self._normalize_split_group_step(step)
        elif step_type == "split_range":
            return self._normalize_split_range_step(step)
        else:
            return step

    def _normalize_message_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize message step."""
        # Move content to messageText if messageText doesn't exist
        if "messageText" not in step:
            step["messageText"] = step.get("content", step.get("text", ""))
            self.warnings.append(f"Set messageText from content for step {step['id']}")

        # Set default discount fields
        step.setdefault("discountType", "none")
        step.setdefault("discountValue", "")
        step.setdefault("discountCode", "")
        step.setdefault("discountEmail", "")
        step.setdefault("discountExpiry", "")
        step.setdefault("addImage", False)
        step.setdefault("imageUrl", "")
        step.setdefault("sendContactCard", False)

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_delay_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize delay step."""
        if "time" not in step:
            step["time"] = "1"
            self.warnings.append(f"Added default time for delay step {step['id']}")

        if "period" not in step:
            step["period"] = "Hours"
            self.warnings.append(f"Added default period for delay step {step['id']}")

        # Validate period
        if step["period"] not in self.VALID_PERIODS:
            old_period = step["period"]
            step["period"] = "Hours"
            self.warnings.append(f"Invalid period '{old_period}' changed to 'Hours' for step {step['id']}")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_segment_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize segment step."""
        if "conditions" not in step or not step["conditions"]:
            # Add default condition
            step["conditions"] = [{
                "id": 1,
                "type": "property",
                "action": "custom_property",
                "operator": "has",
                "filter": "all",
                "timePeriod": "within the last 30 days",
                "timePeriodType": "relative",
                "propertyName": "customer_type",
                "propertyValue": "active",
                "showFilterOptions": False
            }]
            self.warnings.append(f"Added default condition for segment step {step['id']}")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_product_choice_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize product choice step."""
        step.setdefault("messageType", "standard")
        step.setdefault("productSelection", "manually")
        step.setdefault("productImages", True)
        step.setdefault("discountType", "none")
        step.setdefault("discountValue", "")
        step.setdefault("discountCode", "")

        # Set messageText from content/text if not present
        if "messageText" not in step:
            step["messageText"] = step.get("content", step.get("text", "Choose your product:"))

        # Add default products if none exist
        if "products" not in step or not step["products"]:
            step["products"] = [
                {"id": "prod-1", "label": "Product 1", "showLabel": True, "uniqueId": 1},
                {"id": "prod-2", "label": "Product 2", "showLabel": True, "uniqueId": 2}
            ]
            self.warnings.append(f"Added default products for product_choice step {step['id']}")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_purchase_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize purchase step."""
        step.setdefault("cartSource", "latest")
        step.setdefault("discountType", "none")
        step.setdefault("discountValue", "")
        step.setdefault("discountCode", "")
        step.setdefault("customTotals", False)
        step.setdefault("shippingAmount", "")
        step.setdefault("sendReminderForNonPurchasers", False)
        step.setdefault("allowAutomaticPayment", False)

        # Normalize products array
        if "products" not in step:
            step["products"] = []

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_end_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize end step."""
        step.setdefault("events", [])
        return step

    def _normalize_purchase_offer_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize purchase offer step."""
        step.setdefault("messageType", "standard")
        step.setdefault("cartSource", "manual")
        step.setdefault("discount", False)
        step.setdefault("discountType", "none")
        step.setdefault("discountValue", "")
        step.setdefault("discountCode", "")
        step.setdefault("discountEmail", "")
        step.setdefault("discountExpiry", False)
        step.setdefault("customTotals", False)
        step.setdefault("shippingAmount", "")
        step.setdefault("includeProductImage", True)
        step.setdefault("skipForRecentOrders", False)

        # Set messageText from content/text if not present
        if "messageText" not in step:
            step["messageText"] = step.get("content", step.get("text", ""))

        # Normalize products array
        if "products" not in step:
            step["products"] = []

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_reply_cart_choice_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize reply cart choice step."""
        step.setdefault("messageType", "standard")
        step.setdefault("cartSelection", "latest")
        step.setdefault("customTotals", False)
        step.setdefault("customTotalsAmount", "Shipping")

        # Set messageText from content/text if not present
        if "messageText" not in step:
            step["messageText"] = step.get("content", step.get("prompt", "Choose from your cart:"))

        # Add default cart items if none exist
        if "cartItems" not in step:
            step["cartItems"] = []

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_no_reply_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize no reply step."""
        step.setdefault("enabled", True)

        if "value" not in step:
            step["value"] = 2
            self.warnings.append(f"Added default value for no_reply step {step['id']}")

        if "unit" not in step:
            step["unit"] = "hours"
            self.warnings.append(f"Added default unit for no_reply step {step['id']}")

        # Validate unit
        if step["unit"] not in self.VALID_UNITS:
            old_unit = step["unit"]
            step["unit"] = "hours"
            self.warnings.append(f"Invalid unit '{old_unit}' changed to 'hours' for step {step['id']}")

        # Set structured format if not present
        if "after" not in step:
            step["after"] = {"value": step["value"], "unit": step["unit"].title()}

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_start_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize start step."""
        # Start node typically doesn't need special fields
        return step

    def _normalize_property_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize property step."""
        # Add default properties if none exist
        if "properties" not in step or not step["properties"]:
            step["properties"] = [{
                "name": "custom_property",
                "value": "updated",
                "id": f"prop_{step['id']}_1"
            }]
            self.warnings.append(f"Added default property for property step {step['id']}")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_rate_limit_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize rate limit step."""
        if "occurrences" not in step:
            step["occurrences"] = "12"
            self.warnings.append(f"Added default occurrences for rate_limit step {step['id']}")

        if "timespan" not in step:
            step["timespan"] = "1"
            self.warnings.append(f"Added default timespan for rate_limit step {step['id']}")

        if "period" not in step:
            step["period"] = "Hours"
            self.warnings.append(f"Added default period for rate_limit step {step['id']}")

        # Validate period
        if step["period"] not in self.VALID_PERIODS:
            old_period = step["period"]
            step["period"] = "Hours"
            self.warnings.append(f"Invalid period '{old_period}' changed to 'Hours' for step {step['id']}")

        # Set structured format if not present
        if "rateLimit" not in step:
            step["rateLimit"] = {"limit": step["occurrences"], "period": step["period"]}

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_limit_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize limit step."""
        if "occurrences" not in step:
            step["occurrences"] = "5"
            self.warnings.append(f"Added default occurrences for limit step {step['id']}")

        if "timespan" not in step:
            step["timespan"] = "1"
            self.warnings.append(f"Added default timespan for limit step {step['id']}")

        if "period" not in step:
            step["period"] = "Hours"
            self.warnings.append(f"Added default period for limit step {step['id']}")

        # Validate period
        if step["period"] not in self.VALID_PERIODS:
            old_period = step["period"]
            step["period"] = "Hours"
            self.warnings.append(f"Invalid period '{old_period}' changed to 'Hours' for step {step['id']}")

        # Set structured format if not present
        if "limit" not in step:
            step["limit"] = {"value": step["occurrences"], "period": step["period"]}

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_split_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize split step."""
        step.setdefault("enabled", True)
        step.setdefault("action", "include")
        step.setdefault("description", "Split flow based on conditions")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_reply_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize reply step."""
        step.setdefault("enabled", True)
        step.setdefault("intent", "yes")
        step.setdefault("description", f"Wait for reply from customer")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_experiment_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize experiment step."""
        if "experimentName" not in step:
            step["experimentName"] = f"Experiment {step['id']}"
            self.warnings.append(f"Added default experimentName for experiment step {step['id']}")

        if "version" not in step:
            step["version"] = "1"
            self.warnings.append(f"Added default version for experiment step {step['id']}")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_quiz_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize quiz step."""
        # Add default questions if none exist
        if "questions" not in step or not step["questions"]:
            step["questions"] = [
                {
                    "id": "q1",
                    "question": "What type of products do you prefer?",
                    "type": "single",
                    "options": ["Electronics", "Clothing", "Food"],
                    "correctAnswer": "Electronics",
                    "points": 10
                }
            ]
            self.warnings.append(f"Added default questions for quiz step {step['id']}")

        # Add default quiz config if not present
        if "quizConfig" not in step:
            step["quizConfig"] = {
                "timeLimit": 300,
                "passingScore": 70,
                "shuffleQuestions": False,
                "showResults": True
            }

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_schedule_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize schedule step."""
        # Schedule node typically uses default fields
        self._normalize_events(step)

        return step

    def _normalize_split_group_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize split group step."""
        step.setdefault("enabled", True)
        step.setdefault("action", "control")
        step.setdefault("description", "Experiment variant group")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_split_range_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize split range step."""
        step.setdefault("enabled", True)
        step.setdefault("action", "schedule")
        step.setdefault("description", "Scheduled time range")

        # Normalize events
        self._normalize_events(step)

        return step

    def _normalize_events(self, step: Dict[str, Any]) -> None:
        """Normalize events for a step."""
        if "events" not in step:
            return

        normalized_events = []
        for event in step["events"]:
            normalized_event = self._normalize_event(event, step["id"])
            if normalized_event:
                normalized_events.append(normalized_event)

        step["events"] = normalized_events

    def _normalize_event(self, event: Dict[str, Any], step_id: str) -> Optional[Dict[str, Any]]:
        """Normalize a single event."""
        event_type = event.get("type", "")

        if event_type not in self.VALID_EVENT_TYPES:
            self.errors.append(f"Invalid event type '{event_type}' in step {step_id}")
            return None

        # Ensure required fields (from format_json_flowbuilder.md)
        if "nextStepID" not in event:
            self.warnings.append(f"Event missing nextStepID in step {step_id}")
            return None

        # Set defaults (from format_json_flowbuilder.md)
        event.setdefault("active", True)
        event.setdefault("parameters", {})

        # Normalize based on event type (enhanced validation)
        if event_type == "reply":
            # Reply events require intent and description
            if "intent" not in event:
                event.setdefault("intent", "yes")
                self.warnings.append(f"Added default intent for reply event in step {step_id}")
            if "description" not in event:
                event.setdefault("description", f"Customer replied with intent: {event['intent']}")

        elif event_type == "noreply":
            # NoReply events require after timing
            if "after" not in event:
                event["after"] = {"value": 24, "unit": "hours"}
                self.warnings.append(f"Added default after timing for noreply event in step {step_id}")
            else:
                # Validate after structure
                after = event["after"]
                if not isinstance(after, dict) or "value" not in after or "unit" not in after:
                    event["after"] = {"value": 24, "unit": "hours"}
                    self.warnings.append(f"Fixed invalid after structure for noreply event in step {step_id}")

        elif event_type == "split":
            # Split events require label and action
            if "label" not in event:
                event.setdefault("label", "Split Branch")
                self.warnings.append(f"Added default label for split event in step {step_id}")
            if "action" not in event:
                event.setdefault("action", "include")
                self.warnings.append(f"Added default action for split event in step {step_id}")

        elif event_type == "default":
            # Default events are simple transitions
            pass

        # Remove extra fields not in format_json_flowbuilder.md schema
        allowed_fields = {"id", "type", "nextStepID", "active", "parameters", "intent", "description", "after", "label", "action"}
        event = {k: v for k, v in event.items() if k in allowed_fields}

        return event

    def _validate_step_references(self, flow: Dict[str, Any]) -> None:
        """Validate step references and unique nextStepID rules (from format_json_flowbuilder.md)."""
        step_ids = {step["id"] for step in flow.get("steps", [])}
        next_step_references = {}  # Track all nextStepID references for uniqueness check

        for step in flow.get("steps", []):
            for event in step.get("events", []):
                next_step_id = event.get("nextStepID")
                if next_step_id:
                    # Check if target step exists
                    if next_step_id not in step_ids:
                        self.errors.append(f"Event in step '{step['id']}' references non-existent step: '{next_step_id}'")

                    # Check for duplicate nextStepID references (format_json_flowbuilder.md rule)
                    if next_step_id in next_step_references:
                        self.errors.append(f"VIOLATION: Multiple events pointing to same nextStepID '{next_step_id}' - Event in step '{step['id']}' and '{next_step_references[next_step_id]}'")
                    else:
                        next_step_references[next_step_id] = step['id']

    def get_validation_report(self) -> Dict[str, Any]:
        """Get validation report."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "is_valid": len(self.errors) == 0,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }


def normalize_campaign_flow(flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a campaign flow to match FlowBuilder schema.

    Args:
        flow_data: Raw flow data from LLM generation

    Returns:
        Dictionary with normalized flow and validation results
    """
    validator = FlowBuilderSchemaValidator()
    normalized_flow = validator.validate_and_normalize(flow_data)

    return {
        "flow": normalized_flow,
        "validation": validator.get_validation_report()
    }