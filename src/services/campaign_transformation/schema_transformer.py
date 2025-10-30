"""
Schema Transformer - Transforms campaign models to FlowBuilder schema format.

This service handles the transformation between the internal campaign models
and the FlowBuilder JSON schema format, ensuring full compliance.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from ...models.campaign import Campaign, CampaignStep, CampaignEvent, StepType

logger = logging.getLogger(__name__)


class SchemaTransformer:
    """
    Transforms campaign models to FlowBuilder schema format.

    This service handles:
    - Converting internal campaign models to FlowBuilder JSON
    - Applying field mappings and structure transformations
    - Ensuring backward compatibility during migration
    - Validating FlowBuilder schema compliance
    """

    def __init__(self):
        """Initialize Schema Transformer."""
        self.field_mappings = self._initialize_field_mappings()
        self.transform_rules = self._initialize_transform_rules()

    def _initialize_field_mappings(self) -> Dict[str, Dict[str, str]]:
        """Initialize field mappings for different step types."""
        return {
            'message': {
                'text': 'content',  # Map legacy text to content field
                'legacy_text': 'text',  # Keep text for backward compatibility
            },
            'segment': {
                'segmentDefinition': 'conditions',  # Map legacy segmentDefinition to conditions array
            },
            'delay': {
                'duration': 'time',  # Map legacy duration to time/period format
            },
            'rate_limit': {
                'maxMessages': 'occurrences',  # Map legacy maxMessages to occurrences
                'timeWindow': 'timespan',  # Map legacy timeWindow to timespan
            },
            'purchase_offer': {
                'fullText': 'messageText',  # Map legacy fullText to messageText
            }
        }

    def _initialize_transform_rules(self) -> Dict[str, callable]:
        """Initialize transformation rules for complex conversions."""
        return {
            'message': self._transform_message_step,
            'segment': self._transform_segment_step,
            'delay': self._transform_delay_step,
            'rate_limit': self._transform_rate_limit_step,
            'purchase_offer': self._transform_purchase_offer_step,
            'experiment': self._transform_experiment_step,
            'schedule': self._transform_schedule_step,
            'events': self._transform_events,
        }

    def transform_to_flowbuilder_format(
        self,
        campaign: Campaign,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Transform Campaign model to FlowBuilder JSON format.

        Args:
            campaign: Campaign model to transform
            strict_mode: If True, apply strict FlowBuilder compliance

        Returns:
            FlowBuilder compliant JSON dict
        """
        try:
            logger.info("Transforming campaign to FlowBuilder format")

            # Transform each step
            transformed_steps = []
            for step in campaign.steps:
                transformed_step = self.transform_step(step, strict_mode)
                transformed_steps.append(transformed_step)

            # Build FlowBuilder campaign
            flowbuilder_campaign = {
                "initialStepID": campaign.initialStepID,
                "steps": transformed_steps
            }

            # Validate FlowBuilder compliance if strict mode
            if strict_mode:
                self._validate_flowbuilder_compliance(flowbuilder_campaign)

            logger.info(f"Successfully transformed {len(transformed_steps)} steps to FlowBuilder format")
            return flowbuilder_campaign

        except Exception as e:
            logger.error(f"Failed to transform campaign to FlowBuilder format: {e}")
            raise

    def transform_step(self, step: CampaignStep, strict_mode: bool = False) -> Dict[str, Any]:
        """
        Transform individual step to FlowBuilder format.

        Args:
            step: Campaign step to transform
            strict_mode: If True, apply strict compliance

        Returns:
            Transformed step dict
        """
        step_dict = step.model_dump(by_alias=True, exclude_none=True)

        # Get step type
        step_type = step.type.value if hasattr(step.type, 'value') else step.type

        # Apply type-specific transformations
        if step_type in self.transform_rules:
            step_dict = self.transform_rules[step_type](step_dict, strict_mode)

        # Apply field mappings
        if step_type in self.field_mappings:
            step_dict = self._apply_field_mappings(step_dict, step_type)

        # Apply common transformations
        step_dict = self._apply_common_transformations(step_dict, step_type)

        return step_dict

    def _transform_message_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform message step to FlowBuilder format."""
        # Map text to content for FlowBuilder compliance
        if 'text' in step_dict and 'content' not in step_dict:
            step_dict['content'] = step_dict['text']

        # Ensure discount fields are properly formatted
        if step_dict.get('discountType') == 'none':
            step_dict['discountValue'] = ""
            step_dict['discountCode'] = ""
            step_dict['discountEmail'] = ""
            step_dict['discountExpiry'] = ""

        return step_dict

    def _transform_segment_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform segment step to FlowBuilder format."""
        # Convert legacy segmentDefinition to conditions array
        if 'segmentDefinition' in step_dict and not step_dict.get('conditions'):
            conditions = self._convert_segment_definition_to_conditions(step_dict['segmentDefinition'])
            step_dict['conditions'] = conditions

            # Remove legacy segmentDefinition in strict mode
            if strict_mode:
                step_dict.pop('segmentDefinition', None)

        return step_dict

    def _transform_delay_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform delay step to FlowBuilder format."""
        # Convert legacy duration to time/period/delay format
        if 'duration' in step_dict:
            delay_info = self._convert_duration_to_flowbuilder(step_dict['duration'])
            step_dict.update(delay_info)

            # Remove legacy duration in strict mode
            if strict_mode:
                step_dict.pop('duration', None)
                step_dict.pop('nextStepID', None)  # FlowBuilder uses events for flow

        return step_dict

    def _transform_rate_limit_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform rate_limit step to FlowBuilder format."""
        # Convert legacy maxMessages/timeWindow to occurrences/timespan/period
        if 'maxMessages' in step_dict:
            rate_limit_info = self._convert_rate_limit_to_flowbuilder(step_dict)
            step_dict.update(rate_limit_info)

            # Remove legacy fields in strict mode
            if strict_mode:
                step_dict.pop('maxMessages', None)
                step_dict.pop('timeWindow', None)
                step_dict.pop('nextStepID', None)
                step_dict.pop('exceededStepID', None)

        return step_dict

    def _transform_purchase_offer_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform purchase_offer step to FlowBuilder format."""
        # Map legacy fullText to messageText
        if 'fullText' in step_dict and not step_dict.get('messageText'):
            step_dict['messageText'] = step_dict['fullText']

        # Ensure discount fields are properly structured
        if step_dict.get('discount', False):
            if not step_dict.get('discountType') or step_dict['discountType'] == 'none':
                step_dict['discountType'] = 'percentage'
                step_dict['discountPercentage'] = '10'

        return step_dict

    def _transform_experiment_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform experiment step to FlowBuilder format."""
        # Generate content from experimentName and version if not provided
        if not step_dict.get('content') and step_dict.get('experimentName'):
            version = step_dict.get('version', '1')
            step_dict['content'] = f"{step_dict['experimentName']}(v{version})"

        return step_dict

    def _transform_schedule_step(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform schedule step to FlowBuilder format."""
        # Generate content from label if not provided
        if not step_dict.get('content') and step_dict.get('label'):
            step_dict['content'] = step_dict['label']

        return step_dict

    def _transform_events(self, step_dict: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform events to FlowBuilder format."""
        if 'events' not in step_dict:
            return step_dict

        transformed_events = []
        for event in step_dict['events']:
            transformed_event = self._transform_event(event, strict_mode)
            transformed_events.append(transformed_event)

        step_dict['events'] = transformed_events
        return step_dict

    def _transform_event(self, event: Dict[str, Any], strict_mode: bool) -> Dict[str, Any]:
        """Transform individual event to FlowBuilder format."""
        # Ensure event type is string (not enum)
        if hasattr(event.get('type'), 'value'):
            event['type'] = event['type'].value

        # Map legacy event types to FlowBuilder types
        event_type_mapping = {
            'click': 'default',  # FlowBuilder uses default for direct connections
            'timeout': 'noreply',
            'condition_met': 'default',
            'condition_not_met': 'default',
        }

        if event['type'] in event_type_mapping:
            event['type'] = event_type_mapping[event['type']]

        # Ensure after object is properly formatted for noreply events
        if event['type'] == 'noreply' and event.get('after'):
            if isinstance(event['after'], dict):
                # Ensure after object has value and unit
                if 'value' not in event['after']:
                    event['after']['value'] = 6  # Default value
                if 'unit' not in event['after']:
                    event['after']['unit'] = 'hours'  # Default unit

        return event

    def _apply_field_mappings(self, step_dict: Dict[str, Any], step_type: str) -> Dict[str, Any]:
        """Apply field mappings for the given step type."""
        if step_type not in self.field_mappings:
            return step_dict

        mappings = self.field_mappings[step_type]
        for legacy_field, new_field in mappings.items():
            if legacy_field in step_dict and new_field not in step_dict:
                step_dict[new_field] = step_dict[legacy_field]

        return step_dict

    def _apply_common_transformations(self, step_dict: Dict[str, Any], step_type: str) -> Dict[str, Any]:
        """Apply common transformations to all step types."""
        # Ensure all steps have required base fields
        if 'active' not in step_dict:
            step_dict['active'] = True

        if 'parameters' not in step_dict:
            step_dict['parameters'] = {}

        # Ensure content field exists for display purposes
        if 'content' not in step_dict and 'label' in step_dict:
            step_dict['content'] = step_dict['label']

        return step_dict

    def _convert_segment_definition_to_conditions(self, segment_def: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert legacy segmentDefinition to FlowBuilder conditions array."""
        conditions = []

        try:
            if 'segments' in segment_def:
                for i, segment in enumerate(segment_def['segments']):
                    condition = {
                        "id": i + 1,
                        "type": segment.get('customerAction', {}).get('type', 'event'),
                        "operator": segment.get('customerAction', {}).get('filterOperator', 'has'),
                        "timePeriod": "within the last 30 Days",
                        "timePeriodType": "relative",
                        "filterTab": "productId",
                        "showFilterOptions": False,
                        "showTimePeriodOptions": False,
                    }

                    # Add action-specific fields
                    customer_action = segment.get('customerAction', {})
                    if customer_action.get('type') == 'event':
                        condition['action'] = customer_action.get('event', 'placed_order')
                        condition['filter'] = "all orders"
                    elif customer_action.get('type') == 'customer_property':
                        condition['propertyName'] = customer_action.get('propertyName', '')
                        condition['propertyValue'] = customer_action.get('propertyValue', '')
                        condition['propertyOperator'] = customer_action.get('filterOperator', 'equals')
                        condition['showPropertyValueInput'] = True
                        condition['showPropertyOperatorOptions'] = True

                    # Add time period if specified
                    if 'period' in segment:
                        period = segment['period']
                        if period.get('type') == 'within_last' and 'value' in period:
                            condition['customTimeValue'] = str(period['value'].get('value', 30))
                            condition['customTimeUnit'] = period['value'].get('unit', 'Days').title()

                    conditions.append(condition)

        except Exception as e:
            logger.warning(f"Failed to convert segmentDefinition to conditions: {e}")
            # Return basic condition as fallback
            conditions = [{
                "id": 1,
                "type": "event",
                "operator": "has",
                "action": "placed_order",
                "filter": "all orders",
                "timePeriod": "within the last 30 Days",
                "timePeriodType": "relative"
            }]

        return conditions

    def _convert_duration_to_flowbuilder(self, duration: Dict[str, int]) -> Dict[str, Any]:
        """Convert legacy duration to FlowBuilder time/period/delay format."""
        result = {}

        # Find the time unit and value
        for unit, value in duration.items():
            if unit in ['seconds', 'minutes', 'hours', 'days']:
                period = unit.title()  # "Seconds", "Minutes", "Hours", "Days"
                result.update({
                    "time": str(value),
                    "period": period,
                    "delay": {"value": str(value), "unit": period}
                })
                break

        return result

    def _convert_rate_limit_to_flowbuilder(self, step_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy rate limit to FlowBuilder occurrences/timespan/period format."""
        max_messages = step_dict.get('maxMessages', 12)
        time_window = step_dict.get('timeWindow', {'hours': 1})

        result = {}

        # Find the time unit and value
        for unit, value in time_window.items():
            if unit in ['minutes', 'hours', 'days']:
                period = unit.title()  # "Minutes", "Hours", "Days"
                result.update({
                    "occurrences": str(max_messages),
                    "timespan": str(value),
                    "period": period,
                    "rateLimit": {"limit": str(max_messages), "period": period},
                    "content": f"{max_messages} times every {value} {unit}"
                })
                break

        return result

    def _validate_flowbuilder_compliance(self, campaign_dict: Dict[str, Any]) -> None:
        """
        Validate FlowBuilder schema compliance.

        Args:
            campaign_dict: Campaign dict to validate

        Raises:
            ValueError: If campaign doesn't meet FlowBuilder compliance
        """
        # Check required fields
        if 'initialStepID' not in campaign_dict:
            raise ValueError("Campaign missing required 'initialStepID' field")

        if 'steps' not in campaign_dict or not campaign_dict['steps']:
            raise ValueError("Campaign missing required 'steps' field or steps array is empty")

        # Validate each step
        step_ids = set()
        for step in campaign_dict['steps']:
            if 'id' not in step:
                raise ValueError("Step missing required 'id' field")

            if 'type' not in step:
                raise ValueError(f"Step '{step.get('id', 'unknown')}' missing required 'type' field")

            # Check for duplicate IDs
            if step['id'] in step_ids:
                raise ValueError(f"Duplicate step ID found: {step['id']}")
            step_ids.add(step['id'])

            # Validate step-specific requirements
            self._validate_step_compliance(step)

        # Validate initialStepID exists
        if campaign_dict['initialStepID'] not in step_ids:
            raise ValueError(f"initialStepID '{campaign_dict['initialStepID']}' not found in steps")

    def _validate_step_compliance(self, step: Dict[str, Any]) -> None:
        """Validate individual step compliance with FlowBuilder schema."""
        step_type = step.get('type', '')

        # Validate required fields per step type
        if step_type == 'message':
            if not step.get('content') and not step.get('text') and not step.get('prompt'):
                raise ValueError(f"Message step '{step.get('id')}' must have content, text, or prompt")

        elif step_type == 'delay':
            if not step.get('time') or not step.get('period'):
                raise ValueError(f"Delay step '{step.get('id')}' must have time and period fields")

        elif step_type == 'segment':
            if not step.get('conditions') and not step.get('segmentDefinition'):
                raise ValueError(f"Segment step '{step.get('id')}' must have conditions or segmentDefinition")

        elif step_type == 'rate_limit':
            if not step.get('occurrences') or not step.get('period'):
                raise ValueError(f"Rate limit step '{step.get('id')}' must have occurrences and period fields")

        elif step_type == 'experiment':
            if not step.get('experimentName'):
                raise ValueError(f"Experiment step '{step.get('id')}' must have experimentName field")

        # Validate events if present
        if 'events' in step:
            for event in step['events']:
                if not event.get('type'):
                    raise ValueError(f"Event in step '{step.get('id')}' missing required 'type' field")

                if event.get('type') == 'reply' and not event.get('intent'):
                    raise ValueError(f"Reply event in step '{step.get('id')}' must have intent field")

    def create_flowbuilder_example(self, campaign_type: str = "promotional") -> Dict[str, Any]:
        """
        Create a FlowBuilder compliant example campaign.

        Args:
            campaign_type: Type of campaign to create example for

        Returns:
            FlowBuilder compliant example campaign
        """
        examples = {
            "promotional": self._create_promotional_example(),
            "welcome": self._create_welcome_example(),
            "abandoned_cart": self._create_abandoned_cart_example(),
        }

        return examples.get(campaign_type, examples["promotional"])

    def _create_promotional_example(self) -> Dict[str, Any]:
        """Create a promotional campaign example."""
        return {
            "initialStepID": "welcome-message",
            "steps": [
                {
                    "id": "welcome-message",
                    "type": "message",
                    "content": "Hi {{first_name}}! Flash sale: 20% off everything this weekend! Use code FLASH20",
                    "text": "Hi {{first_name}}! Flash sale: 20% off everything this weekend! Use code FLASH20",
                    "discountType": "percentage",
                    "discountValue": "20",
                    "discountCode": "FLASH20",
                    "discountExpiry": "2024-12-31T23:59:59",
                    "addImage": False,
                    "sendContactCard": False,
                    "handled": False,
                    "aiGenerated": False,
                    "active": True,
                    "parameters": {},
                    "events": [
                        {
                            "id": "welcome-reply",
                            "type": "reply",
                            "intent": "yes",
                            "description": "Customer wants to shop",
                            "nextStepID": "segment-vip",
                            "active": True,
                            "parameters": {}
                        },
                        {
                            "id": "welcome-noreply",
                            "type": "noreply",
                            "after": {
                                "value": 6,
                                "unit": "hours"
                            },
                            "nextStepID": "followup-message",
                            "active": True,
                            "parameters": {}
                        }
                    ]
                },
                {
                    "id": "segment-vip",
                    "type": "segment",
                    "label": "VIP Customer Check",
                    "conditions": [
                        {
                            "id": 1,
                            "type": "event",
                            "operator": "has",
                            "action": "placed_order",
                            "filter": "all orders",
                            "timePeriod": "within the last 30 Days",
                            "timePeriodType": "relative"
                        }
                    ],
                    "active": True,
                    "parameters": {},
                    "events": [
                        {
                            "id": "vip-yes",
                            "type": "split",
                            "label": "include",
                            "action": "include",
                            "nextStepID": "vip-offer",
                            "active": True,
                            "parameters": {}
                        },
                        {
                            "id": "vip-no",
                            "type": "split",
                            "label": "exclude",
                            "action": "exclude",
                            "nextStepID": "regular-products",
                            "active": True,
                            "parameters": {}
                        }
                    ]
                },
                {
                    "id": "end-node",
                    "type": "end",
                    "label": "End",
                    "active": True,
                    "parameters": {},
                    "events": []
                }
            ]
        }

    def _create_welcome_example(self) -> Dict[str, Any]:
        """Create a welcome campaign example."""
        return {
            "initialStepID": "welcome-message",
            "steps": [
                {
                    "id": "welcome-message",
                    "type": "message",
                    "content": "Welcome {{first_name}}! Thanks for joining us. Here's 10% off your first order!",
                    "discountType": "percentage",
                    "discountValue": "10",
                    "discountCode": "WELCOME10",
                    "sendContactCard": True,
                    "handled": False,
                    "aiGenerated": False,
                    "active": True,
                    "parameters": {},
                    "events": [
                        {
                            "id": "welcome-reply",
                            "type": "reply",
                            "intent": "shop",
                            "description": "Customer wants to shop",
                            "nextStepID": "end-node",
                            "active": True,
                            "parameters": {}
                        }
                    ]
                },
                {
                    "id": "end-node",
                    "type": "end",
                    "label": "End",
                    "active": True,
                    "parameters": {},
                    "events": []
                }
            ]
        }

    def _create_abandoned_cart_example(self) -> Dict[str, Any]:
        """Create an abandoned cart campaign example."""
        return {
            "initialStepID": "cart-reminder",
            "steps": [
                {
                    "id": "cart-reminder",
                    "type": "message",
                    "content": "Hi {{first_name}}, you left items in your cart! Complete your order before they sell out.",
                    "handled": False,
                    "aiGenerated": False,
                    "active": True,
                    "parameters": {},
                    "events": [
                        {
                            "id": "cart-reply",
                            "type": "reply",
                            "intent": "complete",
                            "description": "Customer wants to complete purchase",
                            "nextStepID": "end-node",
                            "active": True,
                            "parameters": {}
                        },
                        {
                            "id": "cart-noreply",
                            "type": "noreply",
                            "after": {
                                "value": 24,
                                "unit": "hours"
                            },
                            "nextStepID": "final-reminder",
                            "active": True,
                            "parameters": {}
                        }
                    ]
                },
                {
                    "id": "final-reminder",
                    "type": "message",
                    "content": "Last chance! Your cart items are reserved for 24 more hours. Complete your order now!",
                    "handled": False,
                    "aiGenerated": False,
                    "active": True,
                    "parameters": {},
                    "events": [
                        {
                            "id": "final-reply",
                            "type": "reply",
                            "intent": "buy",
                            "description": "Customer wants to buy",
                            "nextStepID": "end-node",
                            "active": True,
                            "parameters": {}
                        }
                    ]
                },
                {
                    "id": "end-node",
                    "type": "end",
                    "label": "End",
                    "active": True,
                    "parameters": {},
                    "events": []
                }
            ]
        }


# Factory function
def create_schema_transformer() -> SchemaTransformer:
    """
    Factory function to create SchemaTransformer instance.

    Returns:
        Configured SchemaTransformer instance
    """
    return SchemaTransformer()