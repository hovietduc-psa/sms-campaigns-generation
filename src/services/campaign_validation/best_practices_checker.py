"""
Best Practices Checker - Validates SMS campaign best practices.
"""
import logging
import re
from typing import Dict, Any, List, Set

from .schema_validator import ValidationIssue

logger = logging.getLogger(__name__)


class BestPracticesChecker:
    """
    Checks campaign against SMS marketing best practices.

    Validates:
    - Message length (SMS character limits)
    - Personalization usage
    - Call-to-action presence
    - Link inclusion
    - Brand identification
    - Timing and frequency
    - Compliance (opt-out, etc.)
    """

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, campaign_json: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate campaign against best practices.

        Args:
            campaign_json: Campaign JSON dictionary

        Returns:
            List of validation issues
        """
        self.issues = []

        if "steps" not in campaign_json or not isinstance(campaign_json["steps"], list):
            return self.issues

        self._check_message_best_practices(campaign_json)
        self._check_personalization(campaign_json)
        self._check_call_to_action(campaign_json)
        self._check_campaign_pacing(campaign_json)
        self._check_compliance(campaign_json)
        self._check_overall_campaign_structure(campaign_json)

        return self.issues

    def _check_message_best_practices(self, campaign_json: Dict[str, Any]) -> None:
        """Check message-specific best practices."""
        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            if step_type != "message":
                continue

            text = step.get("text", "")
            if not text or not isinstance(text, str):
                # AI-generated messages with prompts are OK
                if "prompt" in step and step["prompt"]:
                    continue
                else:
                    self.issues.append(ValidationIssue(
                        level="warning",
                        category="best_practice",
                        message="Message step has no text content",
                        step_id=step_id,
                        suggestion="Add message text or AI generation prompt"
                    ))
                    continue

            # Check message length
            self._check_message_length(step_id, text)

            # Check for personalization variables
            self._check_personalization_variables(step_id, text)

            # Check for links/URLs
            self._check_url_presence(step_id, text)

            # Check for brand name
            self._check_brand_identification(step_id, text)

            # Check for spam triggers
            self._check_spam_triggers(step_id, text)

    def _check_message_length(self, step_id: str, text: str) -> None:
        """Check message length against SMS limits."""
        length = len(text)

        # SMS segment sizes (GSM-7 encoding)
        # 1 segment: 160 chars
        # 2 segments: 306 chars (153 * 2)
        # 3 segments: 459 chars (153 * 3)
        # 4 segments: 612 chars (153 * 4)

        if length <= 160:
            # Perfect - single SMS
            pass
        elif length <= 306:
            # 2 SMS segments
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message=f"Message uses 2 SMS segments ({length} chars)",
                step_id=step_id,
                field="text",
                suggestion="Consider shortening to 160 chars for single SMS"
            ))
        elif length <= 320:
            # Borderline - might be 2 or 3 segments depending on encoding
            self.issues.append(ValidationIssue(
                level="warning",
                category="best_practice",
                message=f"Message length ({length} chars) may use 3 SMS segments",
                step_id=step_id,
                field="text",
                suggestion="Shorten to under 306 chars for 2 segments or under 160 for 1"
            ))
        else:
            # Definitely multiple segments
            segments = (length // 153) + 1 if length > 160 else 1
            self.issues.append(ValidationIssue(
                level="warning",
                category="best_practice",
                message=f"Message is long ({length} chars, ~{segments} SMS segments)",
                step_id=step_id,
                field="text",
                suggestion="Shorten message to reduce SMS costs and improve readability"
            ))

    def _check_personalization_variables(self, step_id: str, text: str) -> None:
        """Check for personalization variable usage."""
        # Look for {{variable}} patterns
        personalization_pattern = r'\{\{[^}]+\}\}'
        matches = re.findall(personalization_pattern, text)

        if not matches:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message="Message has no personalization variables",
                step_id=step_id,
                field="text",
                suggestion="Add variables like {{customer.first_name}} for personalization"
            ))
        else:
            # Check for common personalization variables
            common_vars = {
                "{{customer.first_name}}",
                "{{customer.name}}",
                "{{merchant.name}}"
            }

            has_common = any(var in text for var in common_vars)

            if not has_common:
                self.issues.append(ValidationIssue(
                    level="info",
                    category="best_practice",
                    message="Message uses personalization but missing common variables",
                    step_id=step_id,
                    field="text",
                    suggestion="Consider adding {{customer.first_name}} or {{merchant.name}}"
                ))

    def _check_url_presence(self, step_id: str, text: str) -> None:
        """Check for URL/link presence."""
        # Look for URLs or {{merchant.url}} variable
        has_url = (
            "http://" in text or
            "https://" in text or
            "{{merchant.url}}" in text or
            "{{url}}" in text
        )

        if not has_url:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message="Message has no link/URL",
                step_id=step_id,
                field="text",
                suggestion="Add {{merchant.url}} or specific link for user action"
            ))

    def _check_brand_identification(self, step_id: str, text: str) -> None:
        """Check for brand/merchant identification."""
        has_brand = "{{merchant.name}}" in text or "{{brand}}" in text

        if not has_brand:
            self.issues.append(ValidationIssue(
                level="warning",
                category="best_practice",
                message="Message doesn't identify brand/merchant",
                step_id=step_id,
                field="text",
                suggestion="Add {{merchant.name}} at start for brand recognition"
            ))

    def _check_spam_triggers(self, step_id: str, text: str) -> None:
        """Check for common spam trigger words."""
        spam_triggers = [
            "FREE!!!",
            "CLICK HERE NOW",
            "LIMITED TIME ONLY!!!",
            "ACT NOW!!!",
            "$$$",
            "WINNER",
            "CONGRATULATIONS!!!",
        ]

        text_upper = text.upper()

        for trigger in spam_triggers:
            if trigger in text_upper:
                self.issues.append(ValidationIssue(
                    level="warning",
                    category="best_practice",
                    message=f"Message contains potential spam trigger: '{trigger}'",
                    step_id=step_id,
                    field="text",
                    suggestion="Rephrase to avoid spam filters"
                ))

        # Check for excessive punctuation
        if "!!!" in text or "???" in text:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message="Message uses excessive punctuation",
                step_id=step_id,
                field="text",
                suggestion="Use single ! or ? for more professional tone"
            ))

        # Check for ALL CAPS
        words = text.split()
        all_caps_words = [w for w in words if len(w) > 3 and w.isupper() and w.isalpha()]
        if len(all_caps_words) > 2:
            self.issues.append(ValidationIssue(
                level="warning",
                category="best_practice",
                message=f"Message has multiple ALL CAPS words ({len(all_caps_words)})",
                step_id=step_id,
                field="text",
                suggestion="Use normal casing to avoid appearing spammy"
            ))

    def _check_call_to_action(self, campaign_json: Dict[str, Any]) -> None:
        """Check for clear calls-to-action."""
        cta_patterns = [
            r'\bshop\b',
            r'\bbuy\b',
            r'\bclick\b',
            r'\breply\b',
            r'\btext\b',
            r'\bvisit\b',
            r'\bview\b',
            r'\bcheck out\b',
            r'\blearn more\b',
            r'\bget\b',
            r'\bsave\b',
            r'\bjoin\b',
            r'\bsubscribe\b',
        ]

        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            if step_type != "message":
                continue

            text = step.get("text", "").lower()
            if not text:
                continue

            has_cta = any(re.search(pattern, text, re.IGNORECASE) for pattern in cta_patterns)

            if not has_cta:
                self.issues.append(ValidationIssue(
                    level="info",
                    category="best_practice",
                    message="Message has no clear call-to-action",
                    step_id=step_id,
                    field="text",
                    suggestion="Add action words like 'Shop', 'Click', 'Reply', etc."
                ))

    def _check_personalization(self, campaign_json: Dict[str, Any]) -> None:
        """Check overall personalization strategy."""
        message_steps = [
            step for step in campaign_json["steps"]
            if isinstance(step, dict) and step.get("type") == "message"
        ]

        if not message_steps:
            return

        personalized_messages = sum(
            1 for step in message_steps
            if "{{" in step.get("text", "")
        )

        personalization_ratio = personalized_messages / len(message_steps) if message_steps else 0

        if personalization_ratio < 0.5:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message=f"Only {personalization_ratio:.0%} of messages use personalization",
                suggestion="Increase personalization for better engagement"
            ))

    def _check_campaign_pacing(self, campaign_json: Dict[str, Any]) -> None:
        """Check campaign pacing and timing."""
        delay_steps = [
            step for step in campaign_json["steps"]
            if isinstance(step, dict) and step.get("type") == "delay"
        ]

        message_steps = [
            step for step in campaign_json["steps"]
            if isinstance(step, dict) and step.get("type") == "message"
        ]

        # Check if there are delays between messages
        if len(message_steps) > 1 and len(delay_steps) == 0:
            self.issues.append(ValidationIssue(
                level="warning",
                category="best_practice",
                message="Multiple messages without delays may overwhelm recipients",
                suggestion="Add delay steps between messages for better pacing"
            ))

        # Check delay durations
        for step in delay_steps:
            step_id = step.get("id")
            duration = step.get("duration", {})

            if not isinstance(duration, dict):
                continue

            # Calculate total seconds
            total_seconds = 0
            total_seconds += duration.get("seconds", 0)
            total_seconds += duration.get("minutes", 0) * 60
            total_seconds += duration.get("hours", 0) * 3600
            total_seconds += duration.get("days", 0) * 86400

            # Best practice: delays between 4-48 hours
            if total_seconds < 3600:  # Less than 1 hour
                self.issues.append(ValidationIssue(
                    level="info",
                    category="best_practice",
                    message=f"Delay is very short ({total_seconds}s)",
                    step_id=step_id,
                    suggestion="Consider 4-24 hour delays for better engagement"
                ))
            elif total_seconds > 7 * 86400:  # More than 7 days
                self.issues.append(ValidationIssue(
                    level="info",
                    category="best_practice",
                    message=f"Delay is very long ({total_seconds / 86400:.1f} days)",
                    step_id=step_id,
                    suggestion="Long delays may cause users to forget context"
                ))

    def _check_compliance(self, campaign_json: Dict[str, Any]) -> None:
        """Check compliance with SMS regulations."""
        # Check for opt-out language
        has_opt_out = False

        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            text = step.get("text", "").lower()

            if any(word in text for word in ["reply stop", "text stop", "stop to unsubscribe", "opt out"]):
                has_opt_out = True
                break

        if not has_opt_out:
            self.issues.append(ValidationIssue(
                level="warning",
                category="best_practice",
                message="Campaign has no opt-out instructions",
                suggestion="Include 'Reply STOP to unsubscribe' in at least one message"
            ))

    def _check_overall_campaign_structure(self, campaign_json: Dict[str, Any]) -> None:
        """Check overall campaign structure best practices."""
        steps = campaign_json.get("steps", [])
        message_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "message"]

        # Check campaign length
        if len(message_steps) > 5:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message=f"Campaign has {len(message_steps)} messages - may be too long",
                suggestion="Consider breaking into multiple campaigns or reducing messages"
            ))

        if len(message_steps) == 1:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message="Campaign has only one message",
                suggestion="Consider adding follow-up for better engagement"
            ))

        # Check for A/B testing
        has_experiment = any(
            s.get("type") == "experiment"
            for s in steps
            if isinstance(s, dict)
        )

        if len(message_steps) > 1 and not has_experiment:
            self.issues.append(ValidationIssue(
                level="info",
                category="best_practice",
                message="Campaign could benefit from A/B testing",
                suggestion="Consider adding experiment step to test message variations"
            ))

    def get_score(self) -> float:
        """
        Calculate best practices score (0-100).

        Returns:
            Score from 0 to 100
        """
        if not self.issues:
            return 100.0

        # Deduct points for issues
        score = 100.0

        for issue in self.issues:
            if issue.level == "error":
                score -= 10
            elif issue.level == "warning":
                score -= 5
            elif issue.level == "info":
                score -= 2

        return max(0.0, score)

    def get_grade(self) -> str:
        """Get letter grade for campaign."""
        score = self.get_score()

        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(issue.level == "warning" for issue in self.issues)

    def get_warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue.level == "warning"]