"""
Response parser for LLM campaign generation.

This module provides intelligent parsing and cleaning of LLM responses to extract valid JSON.
"""

import json
import re
from typing import Any, Dict, Optional, Tuple

from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow
from src.utils.constants import LOG_CONTEXT_MODEL_USED, LOG_CONTEXT_TOKENS_USED

logger = get_logger(__name__)


class ResponseParseError(Exception):
    """Exception raised when response parsing fails."""
    pass


class ResponseParser:
    """
    Intelligent response parser for extracting valid JSON from LLM responses.
    """

    def __init__(self):
        """Initialize response parser."""
        self.json_start_patterns = [
            r'\s*[\{\[]',  # Start of JSON object or array
            r'```json\s*[\{\[]',  # Markdown JSON code block
            r'```\s*[\{\[]',  # Generic code block
        ]

        self.json_end_patterns = [
            r'[\}\]]\s*$',  # End of JSON object or array
            r'[\}\]]\s*```',  # End of code block
        ]

        # Common LLM output artifacts to clean
        self.cleanup_patterns = [
            (r'^```json\s*', ''),  # Remove JSON code block start
            (r'^```\s*', ''),  # Remove generic code block start
            (r'\s*```$', ''),  # Remove code block end
            (r'^\s*//.*$', ''),  # Remove single-line comments
            (r'/\*.*?\*/', ''),  # Remove multi-line comments
            (r'^[^{]*\{', '{'),  # Remove text before first {
            (r'\}[^}]*$', '}'),  # Remove text after last }
        ]

    def parse_response(
        self,
        response_text: str,
        strict_mode: bool = False,
        attempt_repair: bool = True,
    ) -> Tuple[CampaignFlow, Dict[str, Any]]:
        """
        Parse LLM response and extract valid campaign flow.

        Args:
            response_text: Raw LLM response text
            strict_mode: If True, fail on any parsing issues
            attempt_repair: If True, attempt to repair common JSON issues

        Returns:
            Tuple of (CampaignFlow object, metadata)

        Raises:
            ResponseParseError: If parsing fails
        """
        metadata = {
            "original_length": len(response_text),
            "cleaning_steps": [],
            "repair_attempts": 0,
            "validation_errors": [],
        }

        try:
            # Step 1: Extract JSON from response
            json_text = self._extract_json(response_text, metadata)
            metadata["json_length"] = len(json_text)

            # Step 2: Clean JSON text
            if attempt_repair:
                json_text = self._clean_json(json_text, metadata)

            # Step 3: Parse JSON
            try:
                json_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                if attempt_repair:
                    json_text = self._repair_json(json_text, e, metadata)
                    json_data = json.loads(json_text)
                else:
                    raise ResponseParseError(f"Invalid JSON: {e}") from e

            # Step 4: Validate and create CampaignFlow
            try:
                campaign_flow = CampaignFlow(**json_data)
            except Exception as e:
                if strict_mode:
                    raise ResponseParseError(f"Invalid campaign flow structure: {e}") from e

                # Attempt to repair campaign flow structure
                if attempt_repair:
                    json_data = self._repair_campaign_flow(json_data, e, metadata)
                    campaign_flow = CampaignFlow(**json_data)
                else:
                    raise ResponseParseError(f"Invalid campaign flow structure: {e}") from e

            metadata["parsing_status"] = "success"
            metadata["node_count"] = len(campaign_flow.steps)
            metadata["flow_complexity"] = self._assess_complexity(campaign_flow)

            logger.info(
                "LLM response parsed successfully",
                extra={
                    "original_length": metadata["original_length"],
                    "final_length": len(json_text),
                    "node_count": metadata["node_count"],
                    "flow_complexity": metadata["flow_complexity"],
                    "cleaning_steps": len(metadata["cleaning_steps"]),
                    "repair_attempts": metadata["repair_attempts"],
                }
            )

            return campaign_flow, metadata

        except Exception as e:
            metadata["parsing_status"] = "failed"
            metadata["error"] = str(e)

            logger.error(
                "Failed to parse LLM response",
                extra={
                    "error": str(e),
                    "original_length": metadata["original_length"],
                    "cleaning_steps": len(metadata["cleaning_steps"]),
                    "repair_attempts": metadata["repair_attempts"],
                }
            )

            raise ResponseParseError(f"Failed to parse response: {e}") from e

    def _extract_json(self, text: str, metadata: Dict[str, Any]) -> str:
        """Extract JSON portion from response text."""
        original_text = text

        # Try to find JSON boundaries
        json_start = None
        json_end = None

        # Look for JSON start
        for pattern in self.json_start_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                json_start = match.start()
                break

        if json_start is None:
            # Fallback: find first { or [
            brace_pos = text.find('{')
            bracket_pos = text.find('[')
            if brace_pos != -1 and (bracket_pos == -1 or brace_pos < bracket_pos):
                json_start = brace_pos
            elif bracket_pos != -1:
                json_start = bracket_pos

        if json_start is None:
            raise ResponseParseError("Could not find JSON start in response")

        # Look for JSON end
        text_from_start = text[json_start:]

        for pattern in self.json_end_patterns:
            match = re.search(pattern, text_from_start, re.IGNORECASE | re.MULTILINE)
            if match:
                json_end = json_start + match.end()
                break

        if json_end is None:
            # Fallback: find last } or ]
            brace_pos = text_from_start.rfind('}')
            bracket_pos = text_from_start.rfind(']')
            if brace_pos != -1 and (bracket_pos == -1 or brace_pos > bracket_pos):
                json_end = json_start + brace_pos + 1
            elif bracket_pos != -1:
                json_end = json_start + bracket_pos + 1

        if json_end is None:
            raise ResponseParseError("Could not find JSON end in response")

        json_text = text[json_start:json_end]
        metadata["cleaning_steps"].append("extracted_json_from_response")

        return json_text

    def _clean_json(self, text: str, metadata: Dict[str, Any]) -> str:
        """Clean JSON text to fix common issues."""
        cleaned_text = text

        # Apply cleanup patterns
        for pattern, replacement in self.cleanup_patterns:
            if re.search(pattern, cleaned_text, re.MULTILINE | re.DOTALL):
                cleaned_text = re.sub(pattern, replacement, cleaned_text, flags=re.MULTILINE | re.DOTALL)
                metadata["cleaning_steps"].append(f"applied_pattern_{pattern[:20]}")

        # Fix common quote issues
        cleaned_text = self._fix_quotes(cleaned_text, metadata)

        # Fix trailing commas
        cleaned_text = self._fix_trailing_commas(cleaned_text, metadata)

        # Fix escaped characters
        cleaned_text = self._fix_escaped_characters(cleaned_text, metadata)

        return cleaned_text

    def _fix_quotes(self, text: str, metadata: Dict[str, Any]) -> str:
        """Fix common quote issues in JSON."""
        # Replace smart quotes with regular quotes
        text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")

        # Fix unescaped quotes in strings (basic attempt)
        # This is a simplified fix - may not catch all cases
        lines = text.split('\n')
        fixed_lines = []

        for line in lines:
            # Skip comment lines and empty lines
            if line.strip().startswith('//') or not line.strip():
                fixed_lines.append(line)
                continue

            # Count quotes to detect unescaped quotes
            quote_count = line.count('"')
            if quote_count % 2 == 1:
                # Odd number of quotes, likely missing escape
                # Add escape before quotes that should be escaped
                # This is a heuristic approach
                parts = line.split(':')
                if len(parts) >= 2:
                    # This looks like a key-value pair
                    value_part = ':'.join(parts[1:])
                    if value_part.strip().startswith('"') and not value_part.strip().endswith('"'):
                        # Incomplete string, try to fix
                        value_part = value_part[:-1] if value_part.endswith('"') else value_part
                        value_part = value_part.replace('"', '\\"')
                        value_part = '"' + value_part + '"'
                        line = ':'.join(parts[:1] + [value_part])

            fixed_lines.append(line)

        fixed_text = '\n'.join(fixed_lines)

        if fixed_text != text:
            metadata["cleaning_steps"].append("fixed_quotes")

        return fixed_text

    def _fix_trailing_commas(self, text: str, metadata: Dict[str, Any]) -> str:
        """Fix trailing commas in JSON objects/arrays."""
        # Remove trailing commas before closing braces/brackets
        fixed_text = re.sub(r',(\s*[}\]])', r'\1', text, flags=re.MULTILINE)

        if fixed_text != text:
            metadata["cleaning_steps"].append("fixed_trailing_commas")

        return fixed_text

    def _fix_escaped_characters(self, text: str, metadata: Dict[str, Any]) -> str:
        """Fix escaped characters in JSON strings."""
        # Fix common escape sequence issues
        fixed_text = text

        # Fix double escapes
        fixed_text = fixed_text.replace('\\\\', '\\')

        # Fix newlines in strings
        fixed_text = re.sub(r'(?<!\\)\\n', '\\n', fixed_text)

        # Fix tabs in strings
        fixed_text = re.sub(r'(?<!\\)\\t', '\\t', fixed_text)

        if fixed_text != text:
            metadata["cleaning_steps"].append("fixed_escaped_characters")

        return fixed_text

    def _repair_json(self, text: str, original_error: json.JSONDecodeError, metadata: Dict[str, Any]) -> str:
        """Attempt to repair JSON based on parsing error."""
        metadata["repair_attempts"] += 1
        repaired_text = text

        error_msg = str(original_error).lower()

        try:
            # Get error position
            error_pos = original_error.pos if hasattr(original_error, 'pos') else -1
        except:
            error_pos = -1

        # Common repairs based on error messages
        if "expecting ',' delimiter" in error_msg:
            # Missing comma
            repaired_text = self._add_missing_commas(repaired_text, error_pos, metadata)

        elif "expecting ':' delimiter" in error_msg:
            # Missing colon
            repaired_text = self._add_missing_colons(repaired_text, error_pos, metadata)

        elif "expecting property name enclosed in double quotes" in error_msg:
            # Unquoted property name
            repaired_text = self._quote_property_names(repaired_text, metadata)

        elif "expecting value" in error_msg:
            # Missing value
            repaired_text = self._add_missing_values(repaired_text, error_pos, metadata)

        elif "expecting '}'" in error_msg or "expecting ']'" in error_msg:
            # Missing closing brace/bracket
            repaired_text = self._add_missing_braces(repaired_text, error_msg, metadata)

        elif "invalid escape sequence" in error_msg:
            # Invalid escape sequence
            repaired_text = self._fix_escape_sequences(repaired_text, metadata)

        # Additional generic repairs
        repaired_text = self._generic_repairs(repaired_text, metadata)

        metadata["cleaning_steps"].append(f"repair_attempt_{metadata['repair_attempts']}")

        return repaired_text

    def _add_missing_commas(self, text: str, error_pos: int, metadata: Dict[str, Any]) -> str:
        """Add missing commas based on context."""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated parsing
        lines = text.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            fixed_lines.append(line)

            # Check if next line starts with a property name and current line doesn't end with comma
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                current_line = line.strip()

                if (next_line.startswith('"') and ':' in next_line and
                    current_line and not current_line.rstrip().endswith(',') and
                    not current_line.rstrip().endswith('{') and
                    not current_line.rstrip().endswith('[') and
                    not current_line.rstrip().endswith('}') and
                    not current_line.rstrip().endswith(']')):
                    fixed_lines[-1] = line.rstrip() + ','

        return '\n'.join(fixed_lines)

    def _add_missing_colons(self, text: str, error_pos: int, metadata: Dict[str, Any]) -> str:
        """Add missing colons in key-value pairs."""
        # Look for quoted keys without colons
        fixed_text = re.sub(r'"([^"]+)"\s*[^",:}\]]', r'"\1": ', text)
        return fixed_text

    def _quote_property_names(self, text: str, metadata: Dict[str, Any]) -> str:
        """Quote unquoted property names."""
        # Simple pattern to find unquoted property names
        # This is a basic implementation and may not catch all cases
        fixed_text = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)
        return fixed_text

    def _add_missing_values(self, text: str, error_pos: int, metadata: Dict[str, Any]) -> str:
        """Add missing values for keys."""
        # Add empty string or null for missing values
        fixed_text = re.sub(r'("\w+"\s*:\s*)$', r'\1""', text, flags=re.MULTILINE)
        fixed_text = re.sub(r'("\w+"\s*:\s*)([}\]])', r'\1null\2', text)
        return fixed_text

    def _add_missing_braces(self, text: str, error_msg: str, metadata: Dict[str, Any]) -> str:
        """Add missing closing braces or brackets."""
        # Count braces and brackets
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')

        # Add missing closing braces/brackets
        missing_braces = open_braces - close_braces
        missing_brackets = open_brackets - close_brackets

        fixed_text = text
        if missing_braces > 0:
            fixed_text += '}' * missing_braces
        if missing_brackets > 0:
            fixed_text += ']' * missing_brackets

        return fixed_text

    def _fix_escape_sequences(self, text: str, metadata: Dict[str, Any]) -> str:
        """Fix invalid escape sequences."""
        # Remove or fix invalid escape sequences
        fixed_text = re.sub(r'\\[^"\\nrtbf/v]', '', text)
        return fixed_text

    def _generic_repairs(self, text: str, metadata: Dict[str, Any]) -> str:
        """Apply generic repairs to fix common JSON issues."""
        fixed_text = text

        # Ensure proper JSON structure
        if not fixed_text.strip().startswith('{'):
            fixed_text = '{' + fixed_text
        if not fixed_text.strip().endswith('}') and not fixed_text.strip().endswith(']'):
            fixed_text = fixed_text + '}'

        # Remove any non-JSON content at the beginning or end
        fixed_text = re.sub(r'^[^{[]*', '', fixed_text)
        fixed_text = re.sub(r'[^}\]]*$', '', fixed_text)

        return fixed_text

    def _repair_campaign_flow(self, json_data: Dict[str, Any], original_error: Exception, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Repair campaign flow structure."""
        metadata["repair_attempts"] += 1
        repaired_data = json_data.copy()

        error_msg = str(original_error).lower()

        # Ensure required fields exist
        if "initialStepID" not in repaired_data:
            if "steps" in repaired_data and repaired_data["steps"]:
                repaired_data["initialStepID"] = repaired_data["steps"][0]["id"]
            else:
                repaired_data["initialStepID"] = "start-node"

        if "steps" not in repaired_data:
            repaired_data["steps"] = []

        # Repair individual steps
        repaired_steps = []
        for i, step in enumerate(repaired_data.get("steps", [])):
            try:
                # Ensure step has required fields
                if "id" not in step:
                    step["id"] = f"step-{i}"
                if "type" not in step:
                    step["type"] = "message"  # Default to message
                if "active" not in step:
                    step["active"] = True
                if "parameters" not in step:
                    step["parameters"] = {}
                if "events" not in step:
                    step["events"] = []

                # Repair events
                repaired_events = []
                for j, event in enumerate(step.get("events", [])):
                    if "id" not in event:
                        event["id"] = f"event-{i}-{j}"
                    if "type" not in event:
                        event["type"] = "default"
                    if "nextStepID" not in event and event["type"] != "end":
                        # Try to find next step or create end node
                        if i < len(repaired_data.get("steps", [])) - 1:
                            event["nextStepID"] = repaired_data["steps"][i + 1]["id"]
                        else:
                            event["nextStepID"] = "end-node"
                    if "active" not in event:
                        event["active"] = True
                    if "parameters" not in event:
                        event["parameters"] = {}

                    repaired_events.append(event)

                step["events"] = repaired_events
                repaired_steps.append(step)

            except Exception as e:
                logger.warning(f"Failed to repair step {i}: {e}")
                # Skip this step or create a basic one
                continue

        repaired_data["steps"] = repaired_steps

        # Ensure we have an end node
        has_end = any(step.get("type") == "end" for step in repaired_data["steps"])
        if not has_end and repaired_data["steps"]:
            repaired_data["steps"].append({
                "id": "end-node",
                "type": "end",
                "label": "End",
                "active": True,
                "parameters": {},
                "events": []
            })

        metadata["cleaning_steps"].append("repaired_campaign_flow_structure")

        return repaired_data

    def _assess_complexity(self, campaign_flow: CampaignFlow) -> str:
        """Assess the complexity of a campaign flow."""
        node_count = len(campaign_flow.steps)
        event_count = sum(len(step.events) for step in campaign_flow.steps)
        branch_count = sum(1 for step in campaign_flow.steps if step.type == "segment")
        message_count = sum(1 for step in campaign_flow.steps if step.type == "message")

        # Simple scoring system
        complexity_score = node_count + (event_count * 0.5) + (branch_count * 2) + (message_count * 0.3)

        if complexity_score < 5:
            return "simple"
        elif complexity_score < 15:
            return "medium"
        else:
            return "complex"


# Global response parser instance
_response_parser: Optional[ResponseParser] = None


def get_response_parser() -> ResponseParser:
    """Get global response parser instance."""
    global _response_parser
    if _response_parser is None:
        _response_parser = ResponseParser()
    return _response_parser