"""
Schema transformer for converting LLM output to CampaignFlow format.

This module handles the conversion between the LLM's natural output format
and the structured CampaignFlow schema expected by the system.
"""

import json
from typing import Dict, Any, List, Optional
from uuid import uuid4

from src.core.logging import get_logger
from src.models.flow_schema import (
    CampaignFlow, MessageNode, DelayNode, SegmentNode, ExperimentNode,
    RateLimitNode, EndNode
)

logger = get_logger(__name__)


class SchemaTransformer:
    """
    Transforms LLM-generated campaign data to CampaignFlow format.
    """

    def __init__(self):
        """Initialize schema transformer."""
        self.step_type_mapping = {
            "message": "SendMessage",
            "delay": "Delay",
            "segment": "Condition",
            "end": "SendMessage",  # Convert end nodes to simple messages
            "product_choice": "SendMessage",
            "purchase_offer": "SendMessage",
            "experiment": "Condition",
            "condition": "Condition",
            "webhook": "Webhook",
            "add_to_crm": "AddToCRM",
            "remove_from_crm": "RemoveFromCRM",
            "update_contact": "UpdateContact",
            "add_tag": "AddTag",
            "remove_tag": "RemoveTag",
            "track_event": "TrackEvent",
            "distribute": "Distribute",
            "random": "Random",
            "wait_until": "WaitUntil",
            "a_test": "ATest"
        }

    def transform_to_campaign_flow(self, llm_output: Dict[str, Any]) -> CampaignFlow:
        """
        Transform LLM output to CampaignFlow model.

        Args:
            llm_output: Raw LLM-generated data

        Returns:
            CampaignFlow model instance
        """
        try:
            logger.info("Starting schema transformation from LLM output to CampaignFlow")

            # Extract basic structure
            initial_step_id = llm_output.get("initialStepID", "welcome-step")
            steps_data = llm_output.get("steps", [])
            metadata = llm_output.get("metadata", {})

            # Transform steps
            transformed_steps = []
            step_mapping = {}  # Maps old IDs to new IDs
            failed_steps = []

            for i, step_data in enumerate(steps_data):
                try:
                    transformed_step = self._transform_step(step_data)
                    if transformed_step:
                        transformed_steps.append(transformed_step)
                        new_id = transformed_step.get("id") if isinstance(transformed_step, dict) else transformed_step.id
                        old_id = step_data.get("id", f"step_{i}")
                        step_mapping[old_id] = new_id
                        # Step transformation successful
                    else:
                        failed_steps.append(i)
                        logger.warning(f"Failed to transform step {i}")
                except Exception as e:
                    failed_steps.append(i)
                    logger.error(f"Error transforming step {i}: {e}")

            if failed_steps:
                logger.warning(f"Failed to transform {len(failed_steps)} steps: {failed_steps}")

            # Update next step references
            self._update_step_references(transformed_steps, step_mapping)

            # Create CampaignFlow
            campaign_flow = CampaignFlow(
                initialStepID=self._map_step_id(initial_step_id, step_mapping),
                steps=transformed_steps,
                metadata=metadata,
                version="1.0",
                active=True
            )

            logger.info(f"Successfully transformed {len(transformed_steps)}/{len(steps_data)} steps to CampaignFlow format")
            return campaign_flow

        except Exception as e:
            logger.error(f"Schema transformation failed: {e}")
            logger.debug(f"LLM output that failed: {llm_output}")
            raise ValueError(f"Failed to transform LLM output to CampaignFlow: {e}")

    def _transform_step(self, step_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a single step from LLM format to CampaignFlow format."""
        if not step_data or not step_data.get("id"):
            return None

        step_type = step_data.get("type", "message")
        mapped_type = self.step_type_mapping.get(step_type, "SendMessage")

        # Generate new UUID for the step
        new_id = str(uuid4())

        if mapped_type == "SendMessage":
            return self._transform_message_step(step_data, new_id)
        elif mapped_type == "Delay":
            return self._transform_delay_step(step_data, new_id)
        elif mapped_type == "Condition":
            return self._transform_condition_step(step_data, new_id)
        elif mapped_type == "Webhook":
            return self._transform_webhook_step(step_data, new_id)
        elif mapped_type == "AddToCRM":
            return self._transform_add_to_crm_step(step_data, new_id)
        elif mapped_type == "RemoveFromCRM":
            return self._transform_remove_from_crm_step(step_data, new_id)
        elif mapped_type == "UpdateContact":
            return self._transform_update_contact_step(step_data, new_id)
        elif mapped_type == "AddTag":
            return self._transform_add_tag_step(step_data, new_id)
        elif mapped_type == "RemoveTag":
            return self._transform_remove_tag_step(step_data, new_id)
        elif mapped_type == "TrackEvent":
            return self._transform_track_event_step(step_data, new_id)
        elif mapped_type == "ATest":
            return self._transform_a_test_step(step_data, new_id)
        elif mapped_type == "Distribute":
            return self._transform_distribute_step(step_data, new_id)
        elif mapped_type == "Random":
            return self._transform_random_step(step_data, new_id)
        elif mapped_type == "WaitUntil":
            return self._transform_wait_until_step(step_data, new_id)
        else:
            # Default to message step for unknown types
            return self._transform_message_step(step_data, new_id)

    def _transform_message_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a message step to SendMessage format."""
        # Extract message content with multiple fallbacks
        content = (step_data.get("content", "") or
                  step_data.get("text", "") or
                  step_data.get("message", "") or
                  step_data.get("body", ""))

        # If still no content, create a default message
        if not content:
            content = "Hi {{first_name}}! This is a campaign message."

        # Create message content dictionary
        message_content = {
            "body": content,
            "subject": step_data.get("subject", "SMS Campaign Message"),
            "mediaUrl": step_data.get("mediaUrl"),
            "templateId": step_data.get("templateId"),
            "templateData": step_data.get("templateData", {})
        }

        # Create recipient dictionary - extract from various possible sources
        recipient = {
            "type": "all",  # Default to all recipients
            "segmentId": step_data.get("segmentId"),
            "contactId": step_data.get("contactId"),
            "phoneNumber": step_data.get("phoneNumber"),
            "email": step_data.get("email"),
            "customFilter": step_data.get("customFilter", {})
        }

        # Create sender object if needed
        sender_data = None
        if step_data.get("sender_type") and step_data.get("sender_type") != "default":
            sender_data = Sender(
                type=step_data.get("sender_type", "default"),
                userId=step_data.get("senderId"),
                phoneNumber=step_data.get("senderPhone"),
                email=step_data.get("senderEmail"),
                name=step_data.get("senderName")
            )

        # Create config using Pydantic model
        try:
            config = SendMessageConfig(
                messageContent=message_content,
                recipient=recipient,
                sender=sender_data
            )
            config_dict = config if isinstance(config, dict) else config.model_dump()
        except Exception as e:
            logger.warning(f"Failed to create SendMessageConfig, using minimal config: {e}")
            # Create minimal valid config
            config_dict = {
                "messageContent": {
                    "body": content,
                    "subject": "SMS Campaign Message"
                },
                "recipient": {
                    "type": "all"
                }
            }

        # Determine next step from multiple possible sources
        next_step_id = None
        # Try events first
        events = step_data.get("events", [])
        if events:
            for event in events:
                if event.get("nextStepID"):
                    next_step_id = event["nextStepID"]
                    break
        # Try direct nextStepId field
        if not next_step_id:
            next_step_id = step_data.get("nextStepId")
        # Try direct nextStep field
        if not next_step_id:
            next_step_id = step_data.get("nextStep")

        # Return clean step data matching CampaignFlow schema
        return {
            "id": new_id,
            "type": "SendMessage",
            "config": config_dict,
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_delay_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a delay step to Delay format."""
        # Extract delay information
        events = step_data.get("events", [])
        delay_minutes = 60  # Default

        # Look for delay information in events
        for event in events:
            if event.get("type") == "noreply":
                after = event.get("after", {})
                if isinstance(after, dict):
                    value = after.get("value", 60)
                    unit = after.get("unit", "minutes")

                    # Convert to minutes
                    if unit == "seconds":
                        delay_minutes = value / 60
                    elif unit == "minutes":
                        delay_minutes = value
                    elif unit == "hours":
                        delay_minutes = value * 60
                    elif unit == "days":
                        delay_minutes = value * 24 * 60
                break

        # Determine next step
        next_step_id = None
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        config = DelayConfig(
            delayMinutes=int(delay_minutes),
            delayType="minutes",
            businessHoursOnly=False
        )

        return {
            "id": new_id,
            "type": "Delay",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_condition_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a segment/condition step to Condition format."""
        try:
            conditions = step_data.get("conditions", [])
            operator = step_data.get("operator", "AND")

            # Create a simple condition based on the segment
            condition_configs = []
            for i, condition in enumerate(conditions):
                # Skip empty conditions
                if not condition or not isinstance(condition, dict):
                    continue

                # Add required id field for SegmentCondition
                condition_config = {
                    "id": i + 1,  # Required field: sequential IDs starting from 1
                    "type": condition.get("type", "property"),
                    "operator": condition.get("operator", "has")
                }

                # Add optional fields based on condition type
                if condition.get("type") == "event":
                    condition_config["action"] = condition.get("action", "performed")
                    condition_config["filter"] = condition.get("filter")
                else:
                    condition_config["propertyName"] = condition.get("propertyName", "customer_type")
                    condition_config["propertyValue"] = condition.get("propertyValue", "vip")
                    condition_config["propertyOperator"] = condition.get("propertyOperator", "with a value of")

                # Add time settings if available
                if condition.get("timeSettings"):
                    condition_config["timeSettings"] = condition["timeSettings"]

                # Add display settings if available
                display_fields = ["filterTab", "cartFilterTab", "optInFilterTab",
                                "showFilterOptions", "showLinkFilterOptions",
                                "showCartFilterOptions", "showOptInFilterOptions",
                                "showPropertyValueInput", "showPropertyOperatorOptions"]
                for field in display_fields:
                    if field in condition:
                        condition_config[field] = condition[field]

                # Only add non-None optional fields
                condition_config = {k: v for k, v in condition_config.items() if v is not None}
                condition_configs.append(condition_config)

            # If no valid conditions provided, create a default condition
            if not condition_configs:
                condition_configs = [{
                    "id": 1,
                    "type": "property",
                    "operator": "has",
                    "propertyName": "customer_type",
                    "propertyValue": "vip",
                    "propertyOperator": "with a value of",
                    "showPropertyValueInput": False,
                    "showPropertyOperatorOptions": False
                }]

            # Create condition config dictionary
            config = {
                "conditions": condition_configs,
                "operator": operator
            }

            # Determine next step from multiple sources
            next_step_id = None
            events = step_data.get("events", [])
            if events:
                for event in events:
                    if event.get("nextStepID"):
                        next_step_id = event["nextStepID"]
                        break
            if not next_step_id:
                next_step_id = step_data.get("nextStepId")
            if not next_step_id:
                next_step_id = step_data.get("nextStep")

            return {
                "id": new_id,
                "type": "Condition",
                "config": config,
                "nextStepId": next_step_id,
                "active": step_data.get("active", True)
            }

        except Exception as e:
            logger.warning(f"Failed to transform condition step, using fallback: {e}")
            # Create minimal valid condition as fallback
            fallback_config = {
                "conditions": [{
                    "id": 1,
                    "type": "property",
                    "operator": "has",
                    "propertyName": "customer_type",
                    "propertyValue": "vip",
                    "propertyOperator": "with a value of"
                }],
                "operator": "AND"
            }

            return {
                "id": new_id,
                "type": "Condition",
                "config": fallback_config,
                "nextStepId": step_data.get("nextStepId"),
                "active": step_data.get("active", True)
            }

    def _update_step_references(self, steps: List[Dict[str, Any]], step_mapping: Dict[str, str]):
        """Update step references after transformation."""
        for step in steps:
            if "nextStepId" in step and step["nextStepId"]:
                old_id = step["nextStepId"]
                new_id = step_mapping.get(old_id)
                if new_id:
                    step["nextStepId"] = new_id

    def _map_step_id(self, old_id: str, step_mapping: Dict[str, str]) -> str:
        """Map an old step ID to a new step ID."""
        return step_mapping.get(old_id, old_id)

    def _transform_webhook_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a webhook step to Webhook format."""
        # Extract webhook URL from step data
        webhook_url = step_data.get("webhook_url", "") or step_data.get("url", "https://example.com/webhook")

        config = WebhookConfig(
            url=webhook_url,
            method=step_data.get("method", "POST"),
            headers=step_data.get("headers", {})
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "Webhook",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_add_to_crm_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform an AddToCRM step."""
        config = CRMConfig(
            operation="add",
            crmSystem=step_data.get("crmId", "default"),
            contactData=step_data.get("contactData", {})
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "AddToCRM",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_remove_from_crm_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a RemoveFromCRM step."""
        config = CRMConfig(
            operation="remove",
            crmSystem=step_data.get("crmId", "default"),
            contactData={"contactId": step_data.get("contactId")}
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "RemoveFromCRM",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_update_contact_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform an UpdateContact step."""
        config = CRMConfig(
            operation="update",
            crmSystem=step_data.get("crmId", "default"),
            updateData=step_data.get("updateData", {}),
            contactData={"contactId": step_data.get("contactId")} if step_data.get("contactId") else None
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "UpdateContact",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_add_tag_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform an AddTag step."""
        # Handle both single tag and multiple tags
        tags = []
        if isinstance(step_data.get("tagName"), str):
            tags = [step_data.get("tagName")]
        elif isinstance(step_data.get("tags"), list):
            tags = step_data.get("tags")
        elif isinstance(step_data.get("tagName"), list):
            tags = step_data.get("tagName")

        config = TagConfig(
            operation="add",
            tags=tags or ["default"],
            contactId=step_data.get("contactId")
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "AddTag",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_remove_tag_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a RemoveTag step."""
        # Handle both single tag and multiple tags
        tags = []
        if isinstance(step_data.get("tagName"), str):
            tags = [step_data.get("tagName")]
        elif isinstance(step_data.get("tags"), list):
            tags = step_data.get("tags")
        elif isinstance(step_data.get("tagName"), list):
            tags = step_data.get("tagName")

        config = TagConfig(
            operation="remove",
            tags=tags or ["default"],
            contactId=step_data.get("contactId")
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "RemoveTag",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_track_event_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a TrackEvent step."""
        config = TrackEventConfig(
            eventName=step_data.get("eventName", "default_event"),
            properties=step_data.get("properties", {})
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "TrackEvent",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_a_test_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform an ATest step."""
        config = ATestConfig(
            testName=step_data.get("testName", "default_test"),
            variants=step_data.get("variants", [])
        )

        # Determine next step
        next_step_id = None
        events = step_data.get("events", [])
        for event in events:
            if event.get("nextStepID"):
                next_step_id = event["nextStepID"]
                break

        return {
            "id": new_id,
            "type": "ATest",
            "config": config if isinstance(config, dict) else config.model_dump(),
            "nextStepId": next_step_id,
            "active": step_data.get("active", True)
        }

    def _transform_distribute_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a Distribute step."""
        try:
            # Extract distribution type with fallback
            distribution_type = step_data.get("distributionType") or step_data.get("distribution", "random")
            # Extract targets with fallback
            targets = step_data.get("targets") or step_data.get("paths", [])

            config = DistributeConfig(
                distributionType=distribution_type,
                targets=targets
            )

            # Determine next step from multiple sources
            next_step_id = None
            events = step_data.get("events", [])
            if events:
                for event in events:
                    if event.get("nextStepID"):
                        next_step_id = event["nextStepID"]
                        break
            if not next_step_id:
                next_step_id = step_data.get("nextStepId")
            if not next_step_id:
                next_step_id = step_data.get("nextStep")

            return {
                "id": new_id,
                "type": "Distribute",
                "config": config if isinstance(config, dict) else config.model_dump(),
                "nextStepId": next_step_id,
                "active": step_data.get("active", True)
            }
        except Exception as e:
            logger.warning(f"Failed to transform distribute step, using fallback: {e}")
            # Create minimal valid config
            fallback_config = DistributeConfig(
                distributionType="random",
                targets=[]
            )

            return {
                "id": new_id,
                "type": "Distribute",
                "config": fallback_config if isinstance(fallback_config, dict) else fallback_config.model_dump(),
                "nextStepId": step_data.get("nextStepId"),
                "active": step_data.get("active", True)
            }

    def _transform_random_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a Random step."""
        try:
            # Extract probability with fallback
            probability = step_data.get("probability", 0.5)
            # Extract branch step IDs
            true_step_id = step_data.get("trueStepId")
            false_step_id = step_data.get("falseStepId")

            config = RandomConfig(
                probability=probability,
                trueStepId=true_step_id,
                falseStepId=false_step_id
            )

            # Determine next step from multiple sources
            next_step_id = None
            events = step_data.get("events", [])
            if events:
                for event in events:
                    if event.get("nextStepID"):
                        next_step_id = event["nextStepID"]
                        break
            if not next_step_id:
                next_step_id = step_data.get("nextStepId")
            if not next_step_id:
                next_step_id = step_data.get("nextStep")

            return {
                "id": new_id,
                "type": "Random",
                "config": config if isinstance(config, dict) else config.model_dump(),
                "nextStepId": next_step_id,
                "active": step_data.get("active", True)
            }
        except Exception as e:
            logger.warning(f"Failed to transform random step, using fallback: {e}")
            # Create minimal valid config
            fallback_config = RandomConfig(
                probability=0.5
            )

            return {
                "id": new_id,
                "type": "Random",
                "config": fallback_config if isinstance(fallback_config, dict) else fallback_config.model_dump(),
                "nextStepId": step_data.get("nextStepId"),
                "active": step_data.get("active", True)
            }

    def _transform_wait_until_step(self, step_data: Dict[str, Any], new_id: str) -> Dict[str, Any]:
        """Transform a WaitUntil step."""
        try:
            # Extract waitUntil datetime with fallback
            wait_until = step_data.get("waitUntil", "business_hours")
            # Extract timezone with fallback
            timezone = step_data.get("timezone", "UTC")

            config = WaitUntilConfig(
                waitUntil=wait_until,
                timezone=timezone
            )

            # Determine next step from multiple sources
            next_step_id = None
            events = step_data.get("events", [])
            if events:
                for event in events:
                    if event.get("nextStepID"):
                        next_step_id = event["nextStepID"]
                        break
            if not next_step_id:
                next_step_id = step_data.get("nextStepId")
            if not next_step_id:
                next_step_id = step_data.get("nextStep")

            return {
                "id": new_id,
                "type": "WaitUntil",
                "config": config if isinstance(config, dict) else config.model_dump(),
                "nextStepId": next_step_id,
                "active": step_data.get("active", True)
            }
        except Exception as e:
            logger.warning(f"Failed to transform wait_until step, using fallback: {e}")
            # Create minimal valid config
            fallback_config = WaitUntilConfig(
                waitUntil="business_hours",
                timezone="UTC"
            )

            return {
                "id": new_id,
                "type": "WaitUntil",
                "config": fallback_config if isinstance(fallback_config, dict) else fallback_config.model_dump(),
                "nextStepId": step_data.get("nextStepId"),
                "active": step_data.get("active", True)
            }


def get_schema_transformer() -> SchemaTransformer:
    """Get singleton instance of schema transformer."""
    return SchemaTransformer()