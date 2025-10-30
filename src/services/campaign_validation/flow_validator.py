"""
Graph-based Flow Validator - Detects flow issues in campaign structures.
"""
import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict, deque

from .schema_validator import ValidationIssue

logger = logging.getLogger(__name__)


class FlowValidator:
    """
    Validates campaign flow using graph analysis.

    Detects:
    - Dead ends (steps with no exit)
    - Unreachable steps (steps that can never be reached)
    - Infinite loops (flows with no end step)
    - Orphaned steps (steps not connected to main flow)
    - Missing end steps
    """

    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.step_types: Dict[str, str] = {}

    def validate(self, campaign_json: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate campaign flow.

        Args:
            campaign_json: Campaign JSON dictionary

        Returns:
            List of validation issues
        """
        self.issues = []
        self.graph = defaultdict(set)
        self.step_types = {}

        if "steps" not in campaign_json or not isinstance(campaign_json["steps"], list):
            return self.issues

        # Build graph
        self._build_graph(campaign_json)

        # Run validations
        self._validate_has_end_steps(campaign_json)
        self._validate_reachability(campaign_json)
        self._validate_dead_ends(campaign_json)
        self._validate_infinite_loops(campaign_json)
        self._validate_event_coverage(campaign_json)

        return self.issues

    def _build_graph(self, campaign_json: Dict[str, Any]) -> None:
        """Build directed graph from campaign flow."""
        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            if not step_id:
                continue

            self.step_types[step_id] = step_type

            # Add edges from events
            if "events" in step and isinstance(step["events"], list):
                for event in step["events"]:
                    if not isinstance(event, dict):
                        continue

                    next_id = event.get("nextStepID")
                    if next_id:
                        self.graph[step_id].add(next_id)

            # Add edge from direct nextStepID (delay, etc.)
            if "nextStepID" in step and step["nextStepID"]:
                self.graph[step_id].add(step["nextStepID"])

            # Add edges from condition branches
            if step_type == "condition":
                if "trueStepID" in step and step["trueStepID"]:
                    self.graph[step_id].add(step["trueStepID"])
                if "falseStepID" in step and step["falseStepID"]:
                    self.graph[step_id].add(step["falseStepID"])

            # Add edges from experiment variants
            if step_type == "experiment" and "variants" in step:
                variants = step["variants"]
                if isinstance(variants, list):
                    for variant in variants:
                        if isinstance(variant, dict) and "nextStepID" in variant:
                            next_id = variant["nextStepID"]
                            if next_id:
                                self.graph[step_id].add(next_id)

    def _validate_has_end_steps(self, campaign_json: Dict[str, Any]) -> None:
        """Validate that campaign has at least one end step."""
        end_steps = [
            step.get("id")
            for step in campaign_json["steps"]
            if isinstance(step, dict) and step.get("type") == "end"
        ]

        if not end_steps:
            self.issues.append(ValidationIssue(
                level="error",
                category="flow",
                message="Campaign has no end step - may run indefinitely",
                suggestion="Add an 'end' step to properly terminate the campaign"
            ))

    def _validate_reachability(self, campaign_json: Dict[str, Any]) -> None:
        """Validate that all steps are reachable from initial step."""
        if "initialStepID" not in campaign_json:
            return

        initial_id = campaign_json["initialStepID"]
        all_step_ids = {step.get("id") for step in campaign_json["steps"] if isinstance(step, dict) and "id" in step}

        # BFS from initial step
        reachable = self._get_reachable_steps(initial_id)

        # Find unreachable steps
        unreachable = all_step_ids - reachable

        for step_id in unreachable:
            step_type = self.step_types.get(step_id, "unknown")
            self.issues.append(ValidationIssue(
                level="warning",
                category="flow",
                message=f"Step '{step_id}' ({step_type}) is unreachable from initial step",
                step_id=step_id,
                suggestion="Remove unreachable step or add a path to reach it"
            ))

    def _get_reachable_steps(self, start_id: str) -> Set[str]:
        """Get all steps reachable from a starting step using BFS."""
        reachable = {start_id}
        queue = deque([start_id])

        while queue:
            current = queue.popleft()

            for next_id in self.graph.get(current, set()):
                if next_id not in reachable:
                    reachable.add(next_id)
                    queue.append(next_id)

        return reachable

    def _validate_dead_ends(self, campaign_json: Dict[str, Any]) -> None:
        """Validate that non-end steps have exit paths."""
        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            if not step_id or not step_type:
                continue

            # End steps are supposed to be dead ends
            if step_type == "end":
                continue

            # Check if step has any outgoing edges
            outgoing = self.graph.get(step_id, set())

            if not outgoing:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="flow",
                    message=f"Step '{step_id}' ({step_type}) is a dead end with no exit path",
                    step_id=step_id,
                    suggestion="Add events or nextStepID to continue the flow"
                ))

    def _validate_infinite_loops(self, campaign_json: Dict[str, Any]) -> None:
        """Detect potential infinite loops (paths with no end step)."""
        if "initialStepID" not in campaign_json:
            return

        initial_id = campaign_json["initialStepID"]

        # Check if any end step is reachable from initial
        end_steps = [
            step.get("id")
            for step in campaign_json["steps"]
            if isinstance(step, dict) and step.get("type") == "end"
        ]

        if not end_steps:
            # Already reported in _validate_has_end_steps
            return

        reachable_from_initial = self._get_reachable_steps(initial_id)

        # Check if at least one end step is reachable
        reachable_end_steps = [end_id for end_id in end_steps if end_id in reachable_from_initial]

        if not reachable_end_steps:
            self.issues.append(ValidationIssue(
                level="error",
                category="flow",
                message="No end step is reachable from initial step - potential infinite loop",
                suggestion="Ensure at least one execution path leads to an end step"
            ))

        # Detect circular dependencies (simple cycle detection)
        cycles = self._detect_cycles()
        for cycle in cycles:
            # Only report if cycle doesn't include a way out
            has_exit = False
            for step_id in cycle:
                outgoing = self.graph.get(step_id, set())
                for next_id in outgoing:
                    if next_id not in cycle:
                        has_exit = True
                        break
                if has_exit:
                    break

            if not has_exit:
                self.issues.append(ValidationIssue(
                    level="warning",
                    category="flow",
                    message=f"Detected closed loop: {' → '.join(cycle)}",
                    suggestion="Ensure loop has exit condition or leads to end step"
                ))

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the flow graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in self.graph.keys():
            if node not in visited:
                dfs(node)

        return cycles

    def _validate_event_coverage(self, campaign_json: Dict[str, Any]) -> None:
        """Validate that message steps have proper event coverage."""
        for step in campaign_json["steps"]:
            if not isinstance(step, dict):
                continue

            step_id = step.get("id")
            step_type = step.get("type")

            if step_type != "message":
                continue

            events = step.get("events", [])
            if not isinstance(events, list):
                continue

            event_types = {event.get("type") for event in events if isinstance(event, dict)}

            # Check for common event patterns
            has_reply_handler = "reply" in event_types or "positive" in event_types or "negative" in event_types
            has_noreply_handler = "noreply" in event_types
            has_click_handler = "click" in event_types

            # Warnings for missing handlers
            if not has_reply_handler and not has_click_handler:
                self.issues.append(ValidationIssue(
                    level="warning",
                    category="flow",
                    message=f"Message step has no reply or click handler",
                    step_id=step_id,
                    suggestion="Add 'reply' or 'click' event handler for user engagement"
                ))

            if not has_noreply_handler and len(events) < 2:
                self.issues.append(ValidationIssue(
                    level="info",
                    category="flow",
                    message=f"Message step has no 'noreply' fallback",
                    step_id=step_id,
                    suggestion="Consider adding 'noreply' event for users who don't respond"
                ))

    def get_flow_summary(self) -> Dict[str, Any]:
        """Get a summary of the campaign flow."""
        total_steps = len(self.step_types)
        end_steps = sum(1 for t in self.step_types.values() if t == "end")
        message_steps = sum(1 for t in self.step_types.values() if t == "message")

        # Calculate max depth
        max_depth = 0
        if self.graph:
            # Simple depth calculation from initial to end
            max_depth = self._calculate_max_depth()

        return {
            "total_steps": total_steps,
            "end_steps": end_steps,
            "message_steps": message_steps,
            "max_depth": max_depth,
            "has_cycles": len(self._detect_cycles()) > 0
        }

    def _calculate_max_depth(self) -> int:
        """Calculate maximum depth from any start to any end."""
        max_depth = 0

        def dfs_depth(node: str, depth: int, visited: Set[str]) -> int:
            if node in visited:
                return depth
            visited.add(node)

            max_child_depth = depth

            for neighbor in self.graph.get(node, set()):
                child_depth = dfs_depth(neighbor, depth + 1, visited.copy())
                max_child_depth = max(max_child_depth, child_depth)

            return max_child_depth

        for start_node in self.graph.keys():
            depth = dfs_depth(start_node, 0, set())
            max_depth = max(max_depth, depth)

        return max_depth

    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(issue.level == "error" for issue in self.issues)

    def get_errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue.level == "error"]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue.level == "warning"]