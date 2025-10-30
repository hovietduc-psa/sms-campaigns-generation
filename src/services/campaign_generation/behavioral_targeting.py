"""
Advanced Behavioral Targeting System for sophisticated audience segmentation.
Parses complex behavioral criteria and implements targeting logic.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TimeUnit(Enum):
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"

@dataclass
class BehaviorRule:
    """Represents a single behavioral rule."""
    field: str  # cart_activity, checkout_initiated, order_placed
    operator: str  # within_days, within_hours, exactly, not_within
    time_value: Optional[int] = None
    boolean_value: Optional[bool] = None

@dataclass
class ScheduleInfo:
    """Campaign scheduling information."""
    start_time: Optional[str] = None
    timezone: Optional[str] = None
    date_expression: Optional[str] = None  # "tomorrow", "next monday", etc.

@dataclass
class CustomTemplate:
    """Custom message template provided by merchant."""
    variables: List[str]
    conditional_logic: Dict[str, Any]
    message_structure: Dict[str, Any]

@dataclass
class BusinessRequirements:
    """Complete business requirements extracted from input."""
    behavior_rules: List[BehaviorRule]
    schedule: ScheduleInfo
    custom_template: CustomTemplate
    campaign_purpose: str
    urgency_level: str

class BehavioralTargeting:
    """Advanced behavioral targeting and requirements extraction system."""

    def __init__(self):
        self.behavior_patterns = {
            # Cart activity patterns
            r'added to cart (?:in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="cart_activity", operator="within", time_value=int(match.group(1))),

            r'(?:has )?NOT (?:added to cart|carted) (?:in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="cart_activity", operator="not_within", time_value=int(match.group(1))),

            # Checkout patterns
            r'(?:has )?(?:initiated|started) (?:a )?checkout (?:in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="checkout_initiated", operator="within", time_value=int(match.group(1))),

            r'(?:has )?NOT (?:initiated|started) (?:a )?checkout (?:in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="checkout_initiated", operator="not_within", time_value=int(match.group(1))),

            # Order patterns
            r'(?:has )?placed (?:an )?order (?:in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="order_placed", operator="within", time_value=int(match.group(1))),

            r'(?:has )?placed (?:\d+ )?orders? (?:in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="order_placed", operator="exactly", time_value=int(match.group(1)) if match.group(1).isdigit() else None),

            r'(?:has )?placed (?:an )?order (\d+) (?:times?|in )?(\d+)\s*(hours?|hrs?|days?|weeks?|months?)':
                lambda match: BehaviorRule(field="order_placed", operator="exactly", time_value=int(match.group(2)) if match.group(2).isdigit() else None),
        }

        self.schedule_patterns = {
            # Schedule patterns
            r'(?:Schedule|Date|Time):\s*(.+?)\s*(PST|EST|CST|MST|GMT)':
                lambda match: ScheduleInfo(start_time=match.group(1).strip(), timezone=self._extract_timezone(match.group(2))),

            r'(?:Schedule|Date):\s*(tomorrow|next \w+|today)\s*at\s*(\d{1,2}(?::\d{2})?(?:am|pm))':
                lambda match: ScheduleInfo(date_expression=match.group(1), start_time=match.group(2)),

            r'(?:Schedule|Date):\s*(\d{1,2}\s*am/pm)\s*(PST|EST|CST|MST|GMT)':
                lambda match: ScheduleInfo(start_time=match.group(1).strip(), timezone=self._extract_timezone(match.group(2))),
        }

        self.template_patterns = {
            # Custom template patterns
            r'(?:Message Content|Copy|Template):\s*"(.*?)"\s*Reply\s*(\w+)\s*':
                lambda match: self._parse_custom_template(match.group(1), match.group(2)),

            r'(?:initial step|first step)\s*should\s*be\s*a\s*(\w+)\s*offer\s*with\s*this\s*copy:\s*"(.*?)"':
                lambda match: CustomTemplate(
                    variables=[],
                    conditional_logic={},
                    message_structure={
                        "campaign_purpose": match.group(1),
                        "copy": match.group(2)
                    }
                ),
        }

    def _extract_timezone(self, tz_str: str) -> str:
        """Extract timezone from string."""
        tz_mapping = {
            "PST": "America/Los_Angeles",
            "EST": "America/New_York",
            "CST": "America/Chicago",
            "MST": "America/Denver",
            "GMT": "UTC"
        }
        return tz_mapping.get(tz_str.upper(), tz_str)

    def _parse_custom_template(self, template_text: str, trigger_word: str) -> CustomTemplate:
        """Parse custom template with conditional logic."""
        try:
            # Extract variables from template
            variables = re.findall(r'\{\{([^}]+)\}\}', template_text)

            # Extract conditional logic patterns like {{#if discount}}
            conditionals = re.findall(r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}', template_text)

            return CustomTemplate(
                variables=list(set(variables)),
                conditional_logic={cond[0]: cond[1] for cond in conditionals},
                message_structure={
                    "trigger": trigger_word,
                    "copy": template_text,
                    "conditionals": dict(conditionals)
                }
            )
        except Exception as e:
            logger.warning(f"Failed to parse custom template: {e}")
            return CustomTemplate(variables=[], conditional_logic={}, message_structure={})

    def extract_business_requirements(self, description: str) -> BusinessRequirements:
        """Extract comprehensive business requirements from campaign description."""
        requirements = BusinessRequirements(
            behavior_rules=[],
            schedule=ScheduleInfo(),
            custom_template=CustomTemplate(
                variables=[],
                conditional_logic={},
                message_structure={}
            ),
            campaign_purpose="",
            urgency_level="medium"
        )

        description_lower = description.lower()

        # Extract behavioral rules
        for pattern, rule_func in self.behavior_patterns.items():
            matches = re.finditer(pattern, description_lower)
            for match in matches:
                rule = rule_func(match)
                if rule:
                    requirements.behavior_rules.append(rule)
                    logger.info(f"Extracted behavioral rule: {rule}")

        # Extract scheduling information
        for pattern, schedule_func in self.schedule_patterns.items():
            match = re.search(pattern, description)
            if match:
                schedule_info = schedule_func(match)
                requirements.schedule = schedule_info
                logger.info(f"Extracted schedule: {schedule_info}")

        # Extract custom templates
        for pattern, template_func in self.template_patterns.items():
            match = re.search(pattern, description, re.IGNORECASE | re.DOTALL)
            if match:
                template_info = template_func(match)
                requirements.custom_template = template_info
                logger.info(f"Extracted custom template: {template_info}")

        # Determine campaign purpose and urgency
        if "abandoned" in description_lower or "cart" in description_lower:
            requirements.campaign_purpose = "cart_recovery"
            requirements.urgency_level = "high"
        elif "welcome" in description_lower:
            requirements.campaign_purpose = "onboarding"
            requirements.urgency_level = "low"
        elif "win back" in description_lower or "reactivation" in description_lower:
            requirements.campaign_purpose = "reactivation"
            requirements.urgency_level = "medium-high"

        return requirements

    def create_targeting_variables(self, requirements: BusinessRequirements) -> Dict[str, str]:
        """Create targeting variables based on extracted requirements."""
        variables = {}

        # Behavioral targeting variables
        if requirements.behavior_rules:
            variables["{{targeting.criteria}}"] = self._format_behavioral_criteria(requirements.behavior_rules)
            variables["{{targeting.recency}}"] = self._calculate_recency(requirements.behavior_rules)

        # Schedule variables
        if requirements.schedule.start_time:
            variables["{{schedule.time}}"] = requirements.schedule.start_time
        if requirements.schedule.timezone:
            variables["{{schedule.timezone}}"] = requirements.schedule.timezone
        if requirements.schedule.date_expression:
            variables["{{schedule.date_expr}}"] = requirements.schedule.date_expression

        # Custom template variables
        if requirements.custom_template.variables:
            for var in requirements.custom_template.variables:
                key = "{{{" + var + "}}"
                value = "[[" + var + "_PLACEHOLDER]]"
                variables[key] = value  # Mark for custom processing

        # Purpose variables
        variables["{{campaign.purpose}}"] = requirements.campaign_purpose
        variables["{{urgency.level}}"] = requirements.urgency_level

        return variables

    def _format_behavioral_criteria(self, rules: List[BehaviorRule]) -> str:
        """Format behavioral criteria into readable string."""
        criteria_parts = []
        for rule in rules:
            if rule.field == "cart_activity":
                if rule.operator == "within":
                    criteria_parts.append(f"Added to cart within {rule.time_value} days")
                elif rule.operator == "not_within":
                    criteria_parts.append(f"NOT added to cart within {rule.time_value} days")
            elif rule.field == "checkout_initiated":
                if rule.operator == "within":
                    criteria_parts.append(f"Initiated checkout within {rule.time_value} days")
                elif rule.operator == "not_within":
                    criteria_parts.append(f"NOT initiated checkout within {rule.time_value} days")
            elif rule.field == "order_placed":
                if rule.operator == "exactly":
                    criteria_parts.append(f"Placed exactly {rule.time_value} orders")
                elif rule.operator == "within":
                    criteria_parts.append(f"Placed order within {rule.time_value} days")

        return "; ".join(criteria_parts) if criteria_parts else "All customers"

    def _calculate_recency(self, rules: List[BehaviorRule]) -> str:
        """Calculate customer recency based on behavioral rules."""
        recency_scores = []
        for rule in rules:
            if rule.time_value:
                recency_scores.append(rule.time_value)

        if recency_scores:
            avg_recency = sum(recency_scores) / len(recency_scores)
            if avg_recency <= 3:
                return "very_recent"
            elif avg_recency <= 7:
                return "recent"
            elif avg_recency <= 30:
                return "moderate"
            else:
                return "cold"

        return "unknown"

    def generate_campaign_structure(self, requirements: BusinessRequirements) -> Dict[str, Any]:
        """Generate campaign structure based on business requirements."""
        structure = {
            "campaign_type": "behavioral_targeted",
            "targeting_logic": requirements.behavior_rules,
            "scheduling": {
                "start_time": requirements.schedule.start_time,
                "timezone": requirements.schedule.timezone,
                "date_expression": requirements.schedule.date_expression
            },
            "custom_elements": {
                "purpose": requirements.campaign_purpose,
                "urgency": requirements.urgency_level,
                "template_vars": requirements.custom_template.variables,
                "conditional_logic": requirements.custom_template.conditional_logic
            }
        }

        # Add specific step structure for cart abandonment
        if requirements.campaign_purpose == "cart_recovery":
            structure["steps"] = [
                {
                    "id": "step_001",
                    "type": "purchase_offer",
                    "trigger": "behavioral_match",
                    "template": requirements.custom_template.message_structure.get("copy", ""),
                    "required_variables": ["{{cart.list}}", "{{discount.label}}", "{{checkout.link}}"]
                }
            ]
        elif requirements.custom_template.message_structure:
            # Use custom template structure
            structure["steps"] = [
                {
                    "id": "step_001",
                    "type": requirements.custom_template.message_structure.get("trigger", "message"),
                    "template": requirements.custom_template.message_structure.get("copy", ""),
                    "variables": requirements.custom_template.variables
                }
            ]

        return structure