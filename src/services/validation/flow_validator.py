"""
Advanced flow validator for campaign flow logic validation.

This module provides comprehensive validation of flow logic, reference integrity,
and business rules for campaign flows.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow, NodeType
from src.services.validation.schema_validator import ValidationIssue, ValidationResult

logger = get_logger(__name__)


class FlowPath:
    """Represents a path through the campaign flow."""

    def __init__(self, node_ids: List[str], events: List[Dict[str, Any]]):
        self.node_ids = node_ids
        self.events = events
        self.length = len(node_ids)

    def has_cycle(self) -> bool:
        """Check if path contains a cycle."""
        return len(self.node_ids) != len(set(self.node_ids))

    def get_cycle_nodes(self) -> List[str]:
        """Get nodes that form a cycle."""
        seen = set()
        cycle_nodes = []

        for node_id in self.node_ids:
            if node_id in seen:
                cycle_start = self.node_ids.index(node_id)
                cycle_nodes = self.node_ids[cycle_start:]
                break
            seen.add(node_id)

        return cycle_nodes


class FlowValidator:
    """
    Advanced flow validator for comprehensive flow logic validation.
    """

    def __init__(self):
        """Initialize flow validator."""
        self.max_flow_depth = 50
        self.max_branches_per_segment = 10
        self.max_delay_hours = 720  # 30 days

        # Business rules
        self.required_flow_end_types = {"end"}
        self.warning_flow_end_types = {"message", "delay"}
        self.segment_branch_types = {"include", "exclude"}

        logger.info("Flow validator initialized", extra={
            "max_flow_depth": self.max_flow_depth,
            "max_branches_per_segment": self.max_branches_per_segment,
            "max_delay_hours": self.max_delay_hours,
        })

    def validate(self, flow: CampaignFlow) -> ValidationResult:
        """
        Validate campaign flow logic and structure.

        Args:
            flow: CampaignFlow object to validate

        Returns:
            ValidationResult with issues and any corrections
        """
        issues = []
        corrected_data = flow.dict() if hasattr(flow, 'dict') else flow.model_dump()

        try:
            # Step 1: Reference integrity validation
            reference_issues = self._validate_reference_integrity(flow, corrected_data)
            issues.extend(reference_issues)

            # Step 2: Circular reference detection
            circular_issues = self._detect_circular_references(flow, corrected_data)
            issues.extend(circular_issues)

            # Step 3: Flow completeness validation
            completeness_issues = self._validate_flow_completeness(flow, corrected_data)
            issues.extend(completeness_issues)

            # Step 4: Branch logic validation
            branch_issues = self._validate_branch_logic(flow, corrected_data)
            issues.extend(branch_issues)

            # Step 5: Timing validation
            timing_issues = self._validate_timing_logic(flow, corrected_data)
            issues.extend(timing_issues)

            # Step 6: Business rules validation
            business_issues = self._validate_business_rules(flow, corrected_data)
            issues.extend(business_issues)

            # Step 7: Flow optimization suggestions
            optimization_issues = self._validate_flow_optimization(flow, corrected_data)
            issues.extend(optimization_issues)

            # Determine validity
            is_valid = not any(issue.severity == "error" for issue in issues)

            logger.info(
                "Flow validation completed",
                extra={
                    "is_valid": is_valid,
                    "total_issues": len(issues),
                    "error_count": sum(1 for issue in issues if issue.severity == "error"),
                    "warning_count": sum(1 for issue in issues if issue.severity == "warning"),
                    "node_count": len(flow.steps),
                    "initial_step_id": flow.initialStepID,
                }
            )

            return ValidationResult(is_valid, issues, corrected_data)

        except Exception as e:
            logger.error(f"Flow validation failed with exception: {e}", exc_info=True)
            issues.append(ValidationIssue(
                code="FLOW_VALIDATION_EXCEPTION",
                message=f"Flow validation failed with unexpected error: {e}",
                severity="error",
                suggested_fix="Check flow structure and try again"
            ))
            return ValidationResult(False, issues)

    def _validate_reference_integrity(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate all references between nodes and events."""
        issues = []

        # Create node lookup
        node_map = {step.id: step for step in flow.steps}
        node_ids = set(node_map.keys())

        # Validate initialStepID
        if flow.initialStepID not in node_ids:
            issues.append(ValidationIssue(
                code="INVALID_INITIAL_STEP_REFERENCE",
                message=f"initialStepID '{flow.initialStepID}' does not reference any existing node",
                severity="error",
                field_path="initialStepID",
                suggested_fix="Set initialStepID to one of the existing node IDs"
            ))

        # Validate all next step references in events (FlowBuilder format uses events with nextStepID)
        for step in flow.steps:
            for event in step.events:
                if hasattr(event, 'nextStepID') and event.nextStepID:
                    next_step_id = event.nextStepID
                    if next_step_id and next_step_id not in node_ids:
                        issues.append(ValidationIssue(
                            code="BROKEN_STEP_REFERENCE",
                            message=f"Step '{step.id}' event '{event.id}' references non-existent node: {next_step_id}",
                            severity="error",
                            node_id=step.id,
                            event_id=event.id,
                            field_path=f"steps.{step.id}.events.{event.id}.nextStepID",
                            suggested_fix=f"Set nextStepID to an existing node ID or add the missing node"
                        ))

        # Check for orphaned nodes (nodes not reachable from initial step)
        reachable_nodes = self._find_reachable_nodes(flow)
        orphaned_nodes = node_ids - reachable_nodes

        for orphaned_id in orphaned_nodes:
            issues.append(ValidationIssue(
                code="ORPHANED_NODE",
                message=f"Node '{orphaned_id}' is not reachable from the initial step",
                severity="warning",
                node_id=orphaned_id,
                field_path="steps",
                suggested_fix="Ensure all nodes are reachable through event connections or remove orphaned nodes"
            ))

        return issues

    def _find_reachable_nodes(self, flow: CampaignFlow) -> Set[str]:
        """Find all nodes reachable from the initial step."""
        reachable = set()
        to_visit = deque([flow.initialStepID])
        visited = set()

        node_map = {step.id: step for step in flow.steps}

        while to_visit:
            current_id = to_visit.popleft()
            if current_id in visited or current_id in reachable:
                continue

            visited.add(current_id)
            if current_id in node_map:
                reachable.add(current_id)
                current_node = node_map[current_id]

                # Add next step IDs from events (FlowBuilder format uses events with nextStepID)
                for event in current_node.events:
                    if hasattr(event, 'nextStepID') and event.nextStepID:
                        next_id = event.nextStepID
                        if next_id and next_id not in visited:
                            to_visit.append(next_id)

        return reachable

    def _detect_circular_references(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Detect circular references in the flow."""
        issues = []

        # Build adjacency list
        adjacency = defaultdict(list)
        node_map = {step.id: step for step in flow.steps}

        for step in flow.steps:
            # Build adjacency list from events (FlowBuilder format uses events with nextStepID)
            for event in step.events:
                if hasattr(event, 'nextStepID') and event.nextStepID:
                    next_id = event.nextStepID
                    if next_id and next_id in node_map:
                        adjacency[step.id].append(next_id)

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str, path: List[str]) -> Tuple[bool, List[str]]:
            """Detect cycle starting from node_id."""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency[node_id]:
                if neighbor not in visited:
                    has_cycle_result, cycle_path = has_cycle(neighbor, path.copy())
                    if has_cycle_result:
                        return True, cycle_path
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:] + [neighbor]

            rec_stack.remove(node_id)
            return False, []

        # Check all nodes for cycles
        for step in flow.steps:
            if step.id not in visited:
                has_cycle_result, cycle_path = has_cycle(step.id, [])
                if has_cycle_result:
                    issues.append(ValidationIssue(
                        code="CIRCULAR_REFERENCE",
                        message=f"Circular reference detected: {' -> '.join(cycle_path)}",
                        severity="error",
                        node_id=cycle_path[0] if cycle_path else None,
                        field_path="steps",
                        suggested_fix="Break the circular reference by changing one of the event connections"
                    ))

        return issues

    def _validate_flow_completeness(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate that flows are complete and properly terminated."""
        issues = []

        # Find all end nodes
        end_nodes = [step for step in flow.steps if step.type == "end"]
        reachable_nodes = self._find_reachable_nodes(flow)

        # Check if flow has proper termination
        if not end_nodes:
            issues.append(ValidationIssue(
                code="NO_TERMINATION",
                message="Flow has no END nodes - all paths must terminate",
                severity="error",
                field_path="steps",
                suggested_fix="Add END nodes to terminate all flow paths"
            ))
        else:
            # Check if all paths lead to termination
            nodes_without_exit = []
            for step in flow.steps:
                if step.type == "end":
                    continue

                has_termination = False
                for event in step.events:
                    if event.nextStepID in [end_node.id for end_node in end_nodes]:
                        has_termination = True
                        break
                    # Also check if any path from this node leads to termination
                    if self._path_leads_to_termination(step.id, flow):
                        has_termination = True
                        break

                if not has_termination and step.id in reachable_nodes:
                    nodes_without_exit.append(step.id)

            for node_id in nodes_without_exit:
                issues.append(ValidationIssue(
                    code="NO_TERMINATION_PATH",
                    message=f"Node '{node_id}' has no path to termination",
                    severity="error",
                    node_id=node_id,
                    field_path="steps",
                    suggested_fix="Add events that lead to END nodes or add END nodes"
                ))

        # Check for nodes without events (except END nodes)
        for step in flow.steps:
            if step.type != "end" and not step.events:
                issues.append(ValidationIssue(
                    code="NODE_WITHOUT_EVENTS",
                    message=f"Node '{step.id}' has no events - flow cannot continue",
                    severity="warning",
                    node_id=step.id,
                    field_path=f"steps.{step.id}.events",
                    suggested_fix="Add events to connect to other nodes or add an END node"
                ))

        return issues

    def _path_leads_to_termination(self, start_node_id: str, flow: CampaignFlow, visited: Optional[Set[str]] = None) -> bool:
        """Check if any path from start_node leads to an END node."""
        if visited is None:
            visited = set()

        if start_node_id in visited:
            return False

        visited.add(start_node_id)

        # Find the node
        start_node = None
        for step in flow.steps:
            if step.id == start_node_id:
                start_node = step
                break

        if not start_node:
            return False

        # If this is an END node, we've reached termination
        if start_node.type == "end":
            return True

        # Check all events
        for event in start_node.events:
            next_id = event.nextStepID
            if next_id and self._path_leads_to_termination(next_id, flow, visited.copy()):
                return True

        return False

    def _validate_branch_logic(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate branching logic for segments and other branching nodes."""
        issues = []

        for step in flow.steps:
            # Validate segment nodes
            if step.type == "segment":
                issues.extend(self._validate_segment_logic(step, flow))

            # Validate experiment nodes
            elif step.type == "experiment":
                issues.extend(self._validate_experiment_logic(step, flow))

            # Validate schedule nodes
            elif step.type == "schedule":
                issues.extend(self._validate_schedule_logic(step, flow))

        return issues

    def _validate_segment_logic(self, step: NodeType, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate segment node logic."""
        issues = []

        events = step.events
        split_events = [event for event in events if event.type == "split"]

        # Check for proper segment branching
        if len(split_events) < 2:
            issues.append(ValidationIssue(
                code="INSUFFICIENT_SEGMENT_BRANCHES",
                message=f"Segment node '{step.id}' should have at least 2 split events (include/exclude)",
                severity="warning",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fix="Add split events for include and exclude branches"
            ))

        if len(split_events) > self.max_branches_per_segment:
            issues.append(ValidationIssue(
                code="TOO_MANY_SEGMENT_BRANCHES",
                message=f"Segment node '{step.id}' has {len(split_events)} branches, consider simplifying",
                severity="warning",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fit=f"Reduce branches to {self.max_branches_per_segment} or fewer"
            ))

        # Check branch labels
        labels = [event.label for event in split_events if event.label]
        if len(labels) != len(set(labels)):
            issues.append(ValidationIssue(
                code="DUPLICATE_SEGMENT_LABELS",
                message=f"Segment node '{step.id}' has duplicate branch labels",
                severity="warning",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fix="Use unique labels for each branch"
            ))

        # Check for standard include/exclude pattern
        has_include = any(event.action == "include" for event in split_events)
        has_exclude = any(event.action == "exclude" for event in split_events)

        if not (has_include and has_exclude):
            issues.append(ValidationIssue(
                code="NONSTANDARD_SEGMENT_BRANCHES",
                message=f"Segment node '{step.id}' should typically have both include and exclude branches",
                severity="info",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fix="Consider adding standard include/exclude branches"
            ))

        return issues

    def _validate_experiment_logic(self, step: NodeType, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate experiment node logic."""
        issues = []

        events = step.events
        split_events = [event for event in events if event.type == "split"]

        # Experiments should typically have 2 branches (A/B test)
        if len(split_events) != 2:
            issues.append(ValidationIssue(
                code="INVALID_EXPERIMENT_BRANCHES",
                message=f"Experiment node '{step.id}' should have exactly 2 branches for A/B testing",
                severity="warning",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fix="Add exactly 2 split events (Group A and Group B)"
            ))

        # Check branch labels
        labels = [event.label for event in split_events if event.label]
        expected_labels = {"Group A", "Group B"}

        if not set(labels).issubset(expected_labels):
            issues.append(ValidationIssue(
                code="NONSTANDARD_EXPERIMENT_LABELS",
                message=f"Experiment node '{step.id}' should use standard labels (Group A, Group B)",
                severity="info",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fix="Use standard Group A and Group B labels"
            ))

        return issues

    def _validate_schedule_logic(self, step: NodeType, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate schedule node logic."""
        issues = []

        events = step.events
        split_events = [event for event in events if event.type == "split"]

        # Schedule nodes should have at least 2 branches
        if len(split_events) < 2:
            issues.append(ValidationIssue(
                code="INSUFFICIENT_SCHEDULE_BRANCHES",
                message=f"Schedule node '{step.id}' should have at least 2 branches (scheduled/default)",
                severity="warning",
                node_id=step.id,
                field_path=f"steps.{step.id}.events",
                suggested_fix="Add branches for scheduled time and default time"
            ))

        return issues

    def _validate_timing_logic(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate timing logic and delays."""
        issues = []

        # Check delay nodes
        for step in flow.steps:
            if step.type == "delay":
                issues.extend(self._validate_delay_timing(step))

            # Check noreply events
            for event in step.events:
                if event.type == "noreply" and event.after:
                    issues.extend(self._validate_noreply_timing(event, step))

        # Check total flow timing
        issues.extend(self._validate_total_flow_timing(flow))

        return issues

    def _validate_delay_timing(self, step: NodeType) -> List[ValidationIssue]:
        """Validate delay node timing."""
        issues = []

        try:
            time_value = float(step.time)
            period = step.period

            # Convert to hours for comparison
            if period == "Seconds":
                hours = time_value / 3600
            elif period == "Minutes":
                hours = time_value / 60
            elif period == "Hours":
                hours = time_value
            elif period == "Days":
                hours = time_value * 24
            else:
                return issues

            if hours > self.max_delay_hours:
                issues.append(ValidationIssue(
                    code="EXCESSIVE_DELAY",
                    message=f"Delay of {hours:.1f} hours may be too long for customer engagement",
                    severity="warning",
                    node_id=step.id,
                    field_path=f"steps.{step.id}.time",
                    suggested_fix="Consider reducing delay time or breaking into smaller delays"
                ))

        except (ValueError, TypeError):
            # This should be caught by schema validation
            pass

        return issues

    def _validate_noreply_timing(self, event: Any, step: NodeType) -> List[ValidationIssue]:
        """Validate noreply event timing."""
        issues = []

        try:
            after = event.after
            value = after.get("value", 0)
            unit = after.get("unit", "hours")

            # Convert to hours
            if unit == "seconds":
                hours = value / 3600
            elif unit == "minutes":
                hours = value / 60
            elif unit == "hours":
                hours = value
            elif unit == "days":
                hours = value * 24
            else:
                return issues

            # Check for very short noreply times
            if hours < 0.25:  # Less than 15 minutes
                issues.append(ValidationIssue(
                    code="VERY_SHORT_NOREPLY",
                    message=f"NoReply time of {hours:.1f} hours may be too short for customer response",
                    severity="info",
                    node_id=step.id,
                    event_id=event.id,
                    field_path=f"steps.{step.id}.events.{event.id}.after",
                    suggested_fit="Consider increasing NoReply time to at least 15 minutes"
                ))

            # Check for very long noreply times
            if hours > 168:  # More than 7 days
                issues.append(ValidationIssue(
                    code="VERY_LONG_NOREPLY",
                    message=f"NoReply time of {hours:.1f} hours may be too long",
                    severity="warning",
                    node_id=step.id,
                    event_id=event.id,
                    field_path=f"steps.{step.id}.events.{event.id}.after",
                    suggested_fit="Consider reducing NoReply time to 7 days or less"
                ))

        except (ValueError, TypeError, AttributeError):
            # This should be caught by schema validation
            pass

        return issues

    def _validate_total_flow_timing(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate total flow timing across all paths."""
        issues = []

        # Calculate timing for each path
        path_timings = self._calculate_path_timings(flow)

        for path, total_hours in path_timings.items():
            if total_hours > self.max_delay_hours:
                issues.append(ValidationIssue(
                    code="EXCESSIVE_FLOW_DURATION",
                    message=f"Flow path duration of {total_hours:.1f} hours may be too long",
                    severity="warning",
                    field_path="steps",
                    suggested_fix="Consider reducing delays or breaking the flow into multiple campaigns"
                ))

        return issues

    def _calculate_path_timings(self, flow: CampaignFlow) -> Dict[str, float]:
        """Calculate total timing for each path in the flow."""
        path_timings = {}
        node_map = {step.id: step for step in flow.steps}

        def calculate_path_timing(node_id: str, visited: Set[str] = None) -> Dict[str, float]:
            """Recursively calculate timing for paths from node."""
            if visited is None:
                visited = set()

            if node_id in visited:
                return {}  # Avoid cycles

            visited.add(node_id)
            timings = {}
            current_node = node_map.get(node_id)

            if not current_node:
                return timings

            # Calculate current node timing
            current_timing = 0

            if current_node.type == "delay":
                try:
                    time_value = float(current_node.time)
                    period = current_node.period

                    if period == "Seconds":
                        current_timing = time_value / 3600
                    elif period == "Minutes":
                        current_timing = time_value / 60
                    elif period == "Hours":
                        current_timing = time_value
                    elif period == "Days":
                        current_timing = time_value * 24
                except (ValueError, TypeError):
                    pass

            # Calculate timing for each path from events
            for event in current_node.events:
                next_id = event.nextStepID
                if next_id and next_id in node_map:
                    # Add noreply timing if applicable
                    event_timing = 0
                    if event.type == "noreply" and event.after:
                        try:
                            value = event.after.get("value", 0)
                            unit = event.after.get("unit", "hours")

                            if unit == "seconds":
                                event_timing = value / 3600
                            elif unit == "minutes":
                                event_timing = value / 60
                            elif unit == "hours":
                                event_timing = value
                            elif unit == "days":
                                event_timing = value * 24
                        except (ValueError, TypeError, AttributeError):
                            pass

                    # Recursively calculate timing for next node
                    next_timings = calculate_path_timing(next_id, visited.copy())
                    for next_path, next_timing in next_timings.items():
                        path_name = f"{node_id} -> {next_path}"
                        timings[path_name] = current_timing + event_timing + next_timing

            # If no outgoing events (end node), return current timing
            if not timings:
                timings[node_id] = current_timing

            return timings

        return calculate_path_timing(flow.initialStepID)

    def _validate_business_rules(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate business rules and best practices."""
        issues = []

        # Validate message content
        issues.extend(self._validate_message_content(flow))

        # Validate discount usage
        issues.extend(self._validate_discount_usage(flow))

        # Validate purchase flows
        issues.extend(self._validate_purchase_flows(flow))

        # Validate product recommendations
        issues.extend(self._validate_product_recommendations(flow))

        return issues

    def _validate_message_content(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate message content for best practices."""
        issues = []

        for step in flow.steps:
            if step.type == "message":
                content = getattr(step, "content", "")

                # Check for empty content
                if not content or not content.strip():
                    issues.append(ValidationIssue(
                        code="EMPTY_MESSAGE_CONTENT",
                        message=f"Message node '{step.id}' has empty content",
                        severity="error",
                        node_id=step.id,
                        field_path=f"steps.{step.id}.content",
                        suggested_fix="Add meaningful message content"
                    ))

                # Check for personalization
                if "{{first_name}}" not in content and "{{brand_name}}" not in content:
                    issues.append(ValidationIssue(
                        code="NO_PERSONALIZATION",
                        message=f"Message node '{step.id}' has no personalization variables",
                        severity="info",
                        node_id=step.id,
                        field_path=f"steps.{step.id}.content",
                        suggested_fix="Consider adding personalization variables like {{first_name}} or {{brand_name}}"
                    ))

                # Check for call to action
                cta_keywords = ["reply", "click", "buy", "shop", "order", "claim", "get", "learn"]
                has_cta = any(keyword in content.lower() for keyword in cta_keywords)

                if not has_cta and step.events:
                    reply_events = [e for e in step.events if e.type == "reply"]
                    if reply_events:
                        issues.append(ValidationIssue(
                            code="MISSING_CALL_TO_ACTION",
                            message=f"Message node '{step.id}' expects reply but has no clear call to action",
                            severity="info",
                            node_id=step.id,
                            field_path=f"steps.{step.id}.content",
                            suggested_fix="Add a clear call to action in the message content"
                        ))

        return issues

    def _validate_discount_usage(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate discount usage and configuration."""
        issues = []

        discount_nodes = []
        for step in flow.steps:
            if step.type == "message" and hasattr(step, "discountType") and step.discountType != "none":
                discount_nodes.append(step)

        # Check for multiple discounts in same flow
        if len(discount_nodes) > 3:
            issues.append(ValidationIssue(
                code="TOO_MANY_DISCOUNTS",
                message=f"Flow has {len(discount_nodes)} discount messages, consider consolidating",
                severity="warning",
                field_path="steps",
                suggested_fit="Reduce the number of discount offers to avoid devaluation"
            ))

        # Check discount expiry
        for step in discount_nodes:
            if hasattr(step, "discountExpiry") and not step.discountExpiry:
                issues.append(ValidationIssue(
                    code="MISSING_DISCOUNT_EXPIRY",
                    message=f"Message node '{step.id}' has discount but no expiry date",
                    severity="info",
                    node_id=step.id,
                    field_path=f"steps.{step.id}.discountExpiry",
                    suggested_fix="Add discountExpiry to create urgency"
                ))

        return issues

    def _validate_purchase_flows(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate purchase flow logic."""
        issues = []

        purchase_nodes = [step for step in flow.steps if step.type == "purchase"]
        purchase_offer_nodes = [step for step in flow.steps if step.type == "purchase_offer"]

        # Check for purchase nodes without preceding offers
        for purchase_node in purchase_nodes:
            has_preceding_offer = self._has_preceding_node_of_type(
                purchase_node.id, flow, ["purchase_offer", "product_choice"]
            )

            if not has_preceding_offer:
                issues.append(ValidationIssue(
                    code="PURCHASE_WITHOUT_OFFER",
                    message=f"Purchase node '{purchase_node.id}' has no preceding purchase offer",
                    severity="warning",
                    node_id=purchase_node.id,
                    field_path="steps",
                    suggested_fix="Add a purchase_offer or product_choice node before the purchase node"
                ))

        return issues

    def _validate_product_recommendations(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Validate product recommendation logic."""
        issues = []

        product_choice_nodes = [step for step in flow.steps if step.type == "product_choice"]

        for node in product_choice_nodes:
            # Check product selection mode
            if hasattr(node, "productSelection"):
                if node.productSelection == "manually":
                    products = getattr(node, "products", [])
                    if len(products) < 2:
                        issues.append(ValidationIssue(
                            code="INSUFFICIENT_MANUAL_PRODUCTS",
                            message=f"Product choice node '{node.id}' has {len(products)} products, consider adding more",
                            severity="info",
                            node_id=node.id,
                            field_path=f"steps.{node.id}.products",
                            suggested_fix="Add more product options or use automatic selection"
                        ))
                    elif len(products) > 10:
                        issues.append(ValidationIssue(
                            code="TOO_MANY_MANUAL_PRODUCTS",
                            message=f"Product choice node '{node.id}' has {len(products)} products, may overwhelm customers",
                            severity="warning",
                            node_id=node.id,
                            field_path=f"steps.{node.id}.products",
                            suggested_fix="Reduce product options to 10 or fewer"
                        ))

        return issues

    def _has_preceding_node_of_type(self, start_node_id: str, flow: CampaignFlow, target_types: List[str]) -> bool:
        """Check if there's a preceding node of target types."""
        # This is a simplified check - in practice, you'd need full path analysis
        node_map = {step.id: step for step in flow.steps}

        # Check if any previous node in the flow is of target type
        for step in flow.steps:
            if step.id == start_node_id:
                break
            if step.type in target_types:
                return True

        return False

    def _validate_flow_optimization(self, flow: CampaignFlow, corrected_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate flow optimization and suggest improvements."""
        issues = []

        # Check for optimization opportunities
        issues.extend(self._check_optimization_opportunities(flow))

        # Check for potential simplifications
        issues.extend(self._check_simplification_opportunities(flow))

        return issues

    def _check_optimization_opportunities(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Check for flow optimization opportunities."""
        issues = []

        # Count consecutive delays
        consecutive_delays = 0
        max_consecutive_delays = 0

        for step in flow.steps:
            if step.type == "delay":
                consecutive_delays += 1
                max_consecutive_delays = max(max_consecutive_delays, consecutive_delays)
            else:
                consecutive_delays = 0

        if max_consecutive_delays >= 3:
            issues.append(ValidationIssue(
                code="MULTIPLE_CONSECUTIVE_DELAYS",
                message=f"Flow has {max_consecutive_delays} consecutive delays, consider combining them",
                severity="info",
                field_path="steps",
                suggested_fix="Combine consecutive delays into a single longer delay"
            ))

        # Check for nodes without events (excluding END nodes)
        nodes_without_events = [
            step for step in flow.steps
            if step.type != "end" and not step.events
        ]

        if nodes_without_events:
            issues.append(ValidationIssue(
                code="NODES_WITHOUT_EVENTS",
                message=f"Flow has {len(nodes_without_events)} nodes without events",
                severity="warning",
                field_path="steps",
                suggested_fix="Add events to connect nodes or remove unused nodes"
            ))

        return issues

    def _check_simplification_opportunities(self, flow: CampaignFlow) -> List[ValidationIssue]:
        """Check for flow simplification opportunities."""
        issues = []

        # Check for single-message flows
        message_nodes = [step for step in flow.steps if step.type == "message"]
        if len(message_nodes) == 1 and len(flow.steps) <= 3:
            issues.append(ValidationIssue(
                code="SIMPLE_FLOW",
                message="Flow is very simple, consider adding more engagement steps",
                severity="info",
                field_path="steps",
                suggested_fix="Add personalization, segmentation, or follow-up messages"
            ))

        # Check for similar messages
        message_contents = []
        for step in flow.steps:
            if step.type == "message":
                content = getattr(step, "content", "")
                if content:
                    message_contents.append((step.id, content.lower()))

        # Check for duplicate or very similar messages
        for i, (id1, content1) in enumerate(message_contents):
            for j, (id2, content2) in enumerate(message_contents[i+1:], i+1):
                # Simple similarity check (could be more sophisticated)
                if content1 == content2:
                    issues.append(ValidationIssue(
                        code="DUPLICATE_MESSAGE",
                        message=f"Nodes '{id1}' and '{id2}' have identical message content",
                        severity="warning",
                        node_id=id1,
                        field_path="steps",
                        suggested_fix="Differentiate message content or remove duplicate node"
                    ))

        return issues


# Global flow validator instance
_flow_validator: Optional[FlowValidator] = None


def get_flow_validator() -> FlowValidator:
    """Get global flow validator instance."""
    global _flow_validator
    if _flow_validator is None:
        _flow_validator = FlowValidator()
    return _flow_validator