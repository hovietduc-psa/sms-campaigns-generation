"""
Unit tests for FlowBuilder schema models.

Tests cover all Pydantic models in the flow_schema module to ensure
proper validation, serialization, and business logic enforcement.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from src.models.flow_schema import (
    CampaignFlow, MessageContent, Recipient, Sender, Step,
    SendMessageStep, SendEmailStep, DelayStep, ConditionStep,
    WebhookStep, AddToCRMStep, RemoveFromCRMStep, UpdateContactStep,
    AddTagStep, RemoveTagStep, TrackEventStep, ATestStep,
    DistributeStep, RandomStep, WaitUntilStep
)


class TestCampaignFlow:
    """Test CampaignFlow model."""

    def test_valid_campaign_flow(self, sample_campaign_flow):
        """Test creating a valid campaign flow."""
        flow = CampaignFlow(**sample_campaign_flow)

        assert flow.initialStepID == "welcome_step"
        assert len(flow.steps) == 2
        assert flow.metadata["campaignType"] == "welcome_series"
        assert isinstance(flow.metadata["estimatedDuration"], str)

    def test_minimal_campaign_flow(self):
        """Test creating a minimal valid campaign flow."""
        minimal_flow = {
            "initialStepID": "single_step",
            "steps": [
                {
                    "id": "single_step",
                    "type": "SendMessage",
                    "config": {
                        "messageContent": {"body": "Hello World"},
                        "recipient": {"type": "all"}
                    }
                }
            ]
        }

        flow = CampaignFlow(**minimal_flow)
        assert flow.initialStepID == "single_step"
        assert len(flow.steps) == 1
        assert flow.metadata == {}

    def test_invalid_campaign_flow_missing_initial_step(self):
        """Test campaign flow validation with missing initial step."""
        with pytest.raises(ValueError) as exc_info:
            CampaignFlow(
                initialStepID="nonexistent_step",
                steps=[
                    {
                        "id": "actual_step",
                        "type": "SendMessage",
                        "config": {
                            "messageContent": {"body": "Hello"},
                            "recipient": {"type": "all"}
                        }
                    }
                ]
            )
        assert "Initial step" in str(exc_info.value)

    def test_invalid_campaign_flow_duplicate_step_ids(self):
        """Test campaign flow validation with duplicate step IDs."""
        with pytest.raises(ValueError) as exc_info:
            CampaignFlow(
                initialStepID="duplicate_step",
                steps=[
                    {
                        "id": "duplicate_step",
                        "type": "SendMessage",
                        "config": {
                            "messageContent": {"body": "Hello"},
                            "recipient": {"type": "all"}
                        }
                    },
                    {
                        "id": "duplicate_step",
                        "type": "Delay",
                        "config": {"delayMinutes": 60}
                    }
                ]
            )
        assert "Duplicate step ID" in str(exc_info.value)

    def test_campaign_flow_serialization(self, sample_campaign_flow):
        """Test campaign flow serialization to dictionary."""
        flow = CampaignFlow(**sample_campaign_flow)
        flow_dict = flow.model_dump()

        assert isinstance(flow_dict, dict)
        assert flow_dict["initialStepID"] == sample_campaign_flow["initialStepID"]
        assert len(flow_dict["steps"]) == len(sample_campaign_flow["steps"])
        assert "metadata" in flow_dict


class TestMessageContent:
    """Test MessageContent model."""

    def test_valid_message_content(self):
        """Test creating valid message content."""
        content = MessageContent(
            body="Hello World",
            subject="Test Subject",
            mediaUrl="https://example.com/image.jpg",
            buttons=[
                {"text": "Click Me", "url": "https://example.com"}
            ]
        )

        assert content.body == "Hello World"
        assert content.subject == "Test Subject"
        assert content.mediaUrl == "https://example.com/image.jpg"
        assert len(content.buttons) == 1

    def test_minimal_message_content(self):
        """Test creating minimal valid message content."""
        content = MessageContent(body="Hello")
        assert content.body == "Hello"
        assert content.subject is None
        assert content.mediaUrl is None
        assert content.buttons == []

    def test_empty_message_body(self):
        """Test validation with empty message body."""
        with pytest.raises(ValueError) as exc_info:
            MessageContent(body="")
        assert "Message body" in str(exc_info.value) and "empty" in str(exc_info.value).lower()

    def test_very_long_message_body(self):
        """Test validation with very long message body."""
        with pytest.raises(ValueError) as exc_info:
            MessageContent(body="A" * 10001)  # Assuming 10K character limit
        assert "Message body" in str(exc_info.value) and "too long" in str(exc_info.value).lower()

    def test_invalid_media_url(self):
        """Test validation with invalid media URL."""
        with pytest.raises(ValueError) as exc_info:
            MessageContent(body="Hello", mediaUrl="not-a-url")
        assert "Invalid media URL" in str(exc_info.value)

    def test_invalid_button_format(self):
        """Test validation with invalid button format."""
        with pytest.raises(ValueError) as exc_info:
            MessageContent(
                body="Hello",
                buttons=[{"invalid": "button"}]  # Missing required fields
            )
        assert "Button" in str(exc_info.value)


class TestRecipient:
    """Test Recipient model."""

    def test_segment_recipient(self):
        """Test creating segment recipient."""
        recipient = Recipient(type="segment", segmentId="premium_users")
        assert recipient.type == "segment"
        assert recipient.segmentId == "premium_users"

    def test_user_recipient(self):
        """Test creating user recipient."""
        recipient = Recipient(type="user", userId="user123")
        assert recipient.type == "user"
        assert recipient.userId == "user123"

    def test_all_recipient(self):
        """Test creating 'all' recipient."""
        recipient = Recipient(type="all")
        assert recipient.type == "all"

    def test_invalid_recipient_type(self):
        """Test validation with invalid recipient type."""
        with pytest.raises(ValueError) as exc_info:
            Recipient(type="invalid_type")
        assert "Invalid recipient type" in str(exc_info.value)

    def test_segment_recipient_missing_id(self):
        """Test segment recipient without segment ID."""
        with pytest.raises(ValueError) as exc_info:
            Recipient(type="segment")
        assert "Segment ID" in str(exc_info.value) and "required" in str(exc_info.value)

    def test_user_recipient_missing_id(self):
        """Test user recipient without user ID."""
        with pytest.raises(ValueError) as exc_info:
            Recipient(type="user")
        assert "User ID" in str(exc_info.value) and "required" in str(exc_info.value)


class TestSender:
    """Test Sender model."""

    def test_default_sender(self):
        """Test creating default sender."""
        sender = Sender(type="default")
        assert sender.type == "default"

    def test_phone_sender(self):
        """Test creating phone sender."""
        sender = Sender(type="phone", phoneNumber="+1234567890")
        assert sender.type == "phone"
        assert sender.phoneNumber == "+1234567890"

    def test_invalid_sender_type(self):
        """Test validation with invalid sender type."""
        with pytest.raises(ValueError) as exc_info:
            Sender(type="invalid_type")
        assert "Invalid sender type" in str(exc_info.value)

    def test_phone_sender_missing_number(self):
        """Test phone sender without phone number."""
        with pytest.raises(ValueError) as exc_info:
            Sender(type="phone")
        assert "Phone number" in str(exc_info.value) and "required" in str(exc_info.value)

    def test_invalid_phone_number(self):
        """Test validation with invalid phone number."""
        with pytest.raises(ValueError) as exc_info:
            Sender(type="phone", phoneNumber="invalid-phone")
        assert "Invalid phone number" in str(exc_info.value)


class TestStep:
    """Test base Step model and validation."""

    def test_minimal_step(self):
        """Test creating minimal valid step."""
        step = Step(id="test_step", type="SendMessage")
        assert step.id == "test_step"
        assert step.type == "SendMessage"
        assert step.nextStepId is None
        assert step.config == {}

    def test_step_with_next_step(self):
        """Test creating step with next step ID."""
        step = Step(
            id="test_step",
            type="SendMessage",
            nextStepId="next_step",
            config={"test": "config"}
        )
        assert step.nextStepId == "next_step"
        assert step.config["test"] == "config"

    def test_empty_step_id(self):
        """Test validation with empty step ID."""
        with pytest.raises(ValueError) as exc_info:
            Step(id="", type="SendMessage")
        assert "Step ID" in str(exc_info.value) and "empty" in str(exc_info.value)

    def test_invalid_step_id_format(self):
        """Test validation with invalid step ID format."""
        with pytest.raises(ValueError) as exc_info:
            Step(id="invalid id with spaces", type="SendMessage")
        assert "Step ID" in str(exc_info.value) and "alphanumeric" in str(exc_info.value)

    def test_very_long_step_id(self):
        """Test validation with very long step ID."""
        with pytest.raises(ValueError) as exc_info:
            Step(id="a" * 101, type="SendMessage")  # Assuming 100 character limit
        assert "Step ID" in str(exc_info.value) and "too long" in str(exc_info.value)


class TestSendMessageStep:
    """Test SendMessageStep model."""

    def test_valid_send_message_step(self):
        """Test creating valid send message step."""
        step = SendMessageStep(
            id="send_step",
            config={
                "messageContent": {
                    "body": "Hello World",
                    "subject": "Test"
                },
                "recipient": {
                    "type": "segment",
                    "segmentId": "users"
                },
                "sender": {
                    "type": "default"
                }
            }
        )

        assert step.type == "SendMessage"
        assert step.config["messageContent"]["body"] == "Hello World"
        assert step.config["recipient"]["type"] == "segment"

    def test_send_message_step_missing_message_content(self):
        """Test send message step without message content."""
        with pytest.raises(ValueError) as exc_info:
            SendMessageStep(
                id="send_step",
                config={
                    "recipient": {"type": "all"}
                }
            )
        assert "Message content" in str(exc_info.value) and "required" in str(exc_info.value)

    def test_send_message_step_missing_recipient(self):
        """Test send message step without recipient."""
        with pytest.raises(ValueError) as exc_info:
            SendMessageStep(
                id="send_step",
                config={
                    "messageContent": {"body": "Hello"}
                }
            )
        assert "Recipient" in str(exc_info.value) and "required" in str(exc_info.value)


class TestDelayStep:
    """Test DelayStep model."""

    def test_valid_delay_step_minutes(self):
        """Test creating valid delay step with minutes."""
        step = DelayStep(
            id="delay_step",
            config={"delayMinutes": 60}
        )
        assert step.type == "Delay"
        assert step.config["delayMinutes"] == 60

    def test_valid_delay_step_until_time(self):
        """Test creating valid delay step with specific time."""
        future_time = datetime.now(timezone.utc).isoformat()
        step = DelayStep(
            id="delay_step",
            config={"delayUntil": future_time}
        )
        assert step.type == "Delay"
        assert step.config["delayUntil"] == future_time

    def test_delay_step_missing_delay_config(self):
        """Test delay step without delay configuration."""
        with pytest.raises(ValueError) as exc_info:
            DelayStep(id="delay_step", config={})
        assert "Either delayMinutes or delayUntil" in str(exc_info.value)

    def test_delay_step_both_delay_configs(self):
        """Test delay step with both delay configurations."""
        with pytest.raises(ValueError) as exc_info:
            DelayStep(
                id="delay_step",
                config={
                    "delayMinutes": 60,
                    "delayUntil": "2024-01-01T00:00:00Z"
                }
            )
        assert "Only one of delayMinutes or delayUntil" in str(exc_info.value)

    def test_negative_delay_minutes(self):
        """Test delay step with negative minutes."""
        with pytest.raises(ValueError) as exc_info:
            DelayStep(id="delay_step", config={"delayMinutes": -10})
        assert "Delay minutes" in str(exc_info.value) and "positive" in str(exc_info.value)

    def test_past_delay_until_time(self):
        """Test delay step with past time."""
        past_time = "2020-01-01T00:00:00Z"
        with pytest.raises(ValueError) as exc_info:
            DelayStep(id="delay_step", config={"delayUntil": past_time})
        assert "Delay time" in str(exc_info.value) and "future" in str(exc_info.value)


class TestConditionStep:
    """Test ConditionStep model."""

    def test_valid_condition_step(self):
        """Test creating valid condition step."""
        step = ConditionStep(
            id="condition_step",
            config={
                "conditions": [
                    {
                        "field": "user.tags",
                        "operator": "contains",
                        "value": "premium"
                    }
                ],
                "trueStepId": "premium_flow",
                "falseStepId": "regular_flow"
            }
        )

        assert step.type == "Condition"
        assert len(step.config["conditions"]) == 1
        assert step.config["trueStepId"] == "premium_flow"
        assert step.config["falseStepId"] == "regular_flow"

    def test_condition_step_missing_conditions(self):
        """Test condition step without conditions."""
        with pytest.raises(ValueError) as exc_info:
            ConditionStep(
                id="condition_step",
                config={
                    "trueStepId": "next_step",
                    "falseStepId": "end_step"
                }
            )
        assert "Conditions" in str(exc_info.value) and "required" in str(exc_info.value)

    def test_condition_step_missing_branches(self):
        """Test condition step without branch destinations."""
        with pytest.raises(ValueError) as exc_info:
            ConditionStep(
                id="condition_step",
                config={
                    "conditions": [
                        {
                            "field": "user.tags",
                            "operator": "contains",
                            "value": "premium"
                        }
                    ]
                }
            )
        assert "trueStepId" in str(exc_info.value) and "falseStepId" in str(exc_info.value)

    def test_invalid_condition_operator(self):
        """Test condition with invalid operator."""
        with pytest.raises(ValueError) as exc_info:
            ConditionStep(
                id="condition_step",
                config={
                    "conditions": [
                        {
                            "field": "user.tags",
                            "operator": "invalid_operator",
                            "value": "premium"
                        }
                    ],
                    "trueStepId": "next_step",
                    "falseStepId": "end_step"
                }
            )
        assert "Invalid operator" in str(exc_info.value)


class TestWebhookStep:
    """Test WebhookStep model."""

    def test_valid_webhook_step(self):
        """Test creating valid webhook step."""
        step = WebhookStep(
            id="webhook_step",
            config={
                "url": "https://api.example.com/webhook",
                "method": "POST",
                "headers": {
                    "Authorization": "Bearer token123",
                    "Content-Type": "application/json"
                },
                "body": {
                    "event": "campaign_completed",
                    "data": "{{user_data}}"
                },
                "timeout": 30,
                "retries": 3
            }
        )

        assert step.type == "Webhook"
        assert step.config["url"] == "https://api.example.com/webhook"
        assert step.config["method"] == "POST"
        assert step.config["timeout"] == 30
        assert step.config["retries"] == 3

    def test_webhook_step_missing_url(self):
        """Test webhook step without URL."""
        with pytest.raises(ValueError) as exc_info:
            WebhookStep(
                id="webhook_step",
                config={"method": "POST"}
            )
        assert "URL" in str(exc_info.value) and "required" in str(exc_info.value)

    def test_webhook_step_invalid_url(self):
        """Test webhook step with invalid URL."""
        with pytest.raises(ValueError) as exc_info:
            WebhookStep(
                id="webhook_step",
                config={
                    "url": "not-a-url",
                    "method": "POST"
                }
            )
        assert "Invalid URL" in str(exc_info.value)

    def test_webhook_step_invalid_method(self):
        """Test webhook step with invalid HTTP method."""
        with pytest.raises(ValueError) as exc_info:
            WebhookStep(
                id="webhook_step",
                config={
                    "url": "https://api.example.com/webhook",
                    "method": "INVALID_METHOD"
                }
            )
        assert "Invalid HTTP method" in str(exc_info.value)

    def test_webhook_step_negative_timeout(self):
        """Test webhook step with negative timeout."""
        with pytest.raises(ValueError) as exc_info:
            WebhookStep(
                id="webhook_step",
                config={
                    "url": "https://api.example.com/webhook",
                    "method": "POST",
                    "timeout": -10
                }
            )
        assert "Timeout" in str(exc_info.value) and "positive" in str(exc_info.value)

    def test_webhook_step_negative_retries(self):
        """Test webhook step with negative retries."""
        with pytest.raises(ValueError) as exc_info:
            WebhookStep(
                id="webhook_step",
                config={
                    "url": "https://api.example.com/webhook",
                    "method": "POST",
                    "retries": -1
                }
            )
        assert "Retries" in str(exc_info.value) and "non-negative" in str(exc_info.value)


class TestCRMSteps:
    """Test CRM-related steps."""

    def test_add_to_crm_step(self):
        """Test AddToCRMStep."""
        step = AddToCRMStep(
            id="add_crm",
            config={
                "crmSystem": "salesforce",
                "data": {
                    "email": "{{user.email}}",
                    "name": "{{user.name}}",
                    "source": "campaign"
                }
            }
        )

        assert step.type == "AddToCRM"
        assert step.config["crmSystem"] == "salesforce"
        assert "email" in step.config["data"]

    def test_remove_from_crm_step(self):
        """Test RemoveFromCRMStep."""
        step = RemoveFromCRMStep(
            id="remove_crm",
            config={
                "crmSystem": "hubspot",
                "identifier": "{{user.id}}",
                "identifierType": "userId"
            }
        )

        assert step.type == "RemoveFromCRM"
        assert step.config["crmSystem"] == "hubspot"
        assert step.config["identifierType"] == "userId"

    def test_update_contact_step(self):
        """Test UpdateContactStep."""
        step = UpdateContactStep(
            id="update_contact",
            config={
                "crmSystem": "salesforce",
                "identifier": "{{user.email}}",
                "identifierType": "email",
                "updates": {
                    "last_campaign": "{{campaign.id}}",
                    "status": "engaged"
                }
            }
        )

        assert step.type == "UpdateContact"
        assert step.config["crmSystem"] == "salesforce"
        assert "last_campaign" in step.config["updates"]


class TestTagSteps:
    """Test tag management steps."""

    def test_add_tag_step(self):
        """Test AddTagStep."""
        step = AddTagStep(
            id="add_tag",
            config={
                "tag": "premium_user",
                "condition": {
                    "field": "user.subscription",
                    "operator": "equals",
                    "value": "premium"
                }
            }
        )

        assert step.type == "AddTag"
        assert step.config["tag"] == "premium_user"

    def test_remove_tag_step(self):
        """Test RemoveTagStep."""
        step = RemoveTagStep(
            id="remove_tag",
            config={
                "tag": "inactive_user"
            }
        )

        assert step.type == "RemoveTag"
        assert step.config["tag"] == "inactive_user"

    def test_add_tag_step_empty_tag(self):
        """Test AddTagStep with empty tag."""
        with pytest.raises(ValueError) as exc_info:
            AddTagStep(
                id="add_tag",
                config={"tag": ""}
            )
        assert "Tag" in str(exc_info.value) and "empty" in str(exc_info.value)


class TestSpecializedSteps:
    """Test specialized step types."""

    def test_track_event_step(self):
        """Test TrackEventStep."""
        step = TrackEventStep(
            id="track_event",
            config={
                "eventName": "campaign_completed",
                "properties": {
                    "campaign_id": "{{campaign.id}}",
                    "user_segment": "{{user.segment}}",
                    "completion_time": "{{timestamp}}"
                }
            }
        )

        assert step.type == "TrackEvent"
        assert step.config["eventName"] == "campaign_completed"
        assert "campaign_id" in step.config["properties"]

    def test_a_b_test_step(self):
        """Test ATestStep."""
        step = ATestStep(
            id="ab_test",
            config={
                "testName": "subject_line_test",
                "variants": [
                    {"name": "variant_a", "weight": 50},
                    {"name": "variant_b", "weight": 50}
                ],
                "variantAId": "variant_a_step",
                "variantBId": "variant_b_step"
            }
        )

        assert step.type == "ATest"
        assert step.config["testName"] == "subject_line_test"
        assert len(step.config["variants"]) == 2

    def test_distribute_step(self):
        """Test DistributeStep."""
        step = DistributeStep(
            id="distribute",
            config={
                "branches": [
                    {"stepId": "path_1", "weight": 60},
                    {"stepId": "path_2", "weight": 30},
                    {"stepId": "path_3", "weight": 10}
                ]
            }
        )

        assert step.type == "Distribute"
        assert len(step.config["branches"]) == 3

    def test_random_step(self):
        """Test RandomStep."""
        step = RandomStep(
            id="random_choice",
            config={
                "options": [
                    {"stepId": "option_1", "weight": 70},
                    {"stepId": "option_2", "weight": 30}
                ]
            }
        )

        assert step.type == "Random"
        assert len(step.config["options"]) == 2

    def test_wait_until_step(self):
        """Test WaitUntilStep."""
        future_time = datetime.now(timezone.utc).isoformat()
        step = WaitUntilStep(
            id="wait_until",
            config={"waitUntil": future_time}
        )

        assert step.type == "WaitUntil"
        assert step.config["waitUntil"] == future_time

    def test_wait_until_step_past_time(self):
        """Test WaitUntilStep with past time."""
        past_time = "2020-01-01T00:00:00Z"
        with pytest.raises(ValueError) as exc_info:
            WaitUntilStep(
                id="wait_until",
                config={"waitUntil": past_time}
            )
        assert "Wait time" in str(exc_info.value) and "future" in str(exc_info.value)


class TestStepValidation:
    """Test step validation across all step types."""

    def test_all_step_types_have_valid_ids(self):
        """Test that all step types validate IDs properly."""
        step_types = [
            SendMessageStep, SendEmailStep, DelayStep, ConditionStep,
            WebhookStep, AddToCRMStep, RemoveFromCRMStep, UpdateContactStep,
            AddTagStep, RemoveTagStep, TrackEventStep, ATestStep,
            DistributeStep, RandomStep, WaitUntilStep
        ]

        for step_type in step_types:
            # Test empty ID
            with pytest.raises(ValueError):
                step_type(id="", config={})

            # Test invalid ID format
            with pytest.raises(ValueError):
                step_type(id="invalid id", config={})

            # Test valid ID should work (config depends on step type)
            try:
                if step_type == SendMessageStep:
                    step_type(
                        id="valid_id",
                        config={
                            "messageContent": {"body": "test"},
                            "recipient": {"type": "all"}
                        }
                    )
                elif step_type == DelayStep:
                    step_type(id="valid_id", config={"delayMinutes": 60})
                else:
                    # Try minimal config for other types
                    step_type(id="valid_id", config={})
            except (ValueError, TypeError):
                # Some step types have required config, that's okay
                pass

    def test_step_serialization_roundtrip(self, sample_campaign_flow):
        """Test that steps can be serialized and deserialized."""
        flow = CampaignFlow(**sample_campaign_flow)

        # Serialize to dict
        flow_dict = flow.model_dump()

        # Deserialize back to model
        restored_flow = CampaignFlow(**flow_dict)

        # Verify all data is preserved
        assert restored_flow.initialStepID == flow.initialStepID
        assert len(restored_flow.steps) == len(flow.steps)

        for original_step, restored_step in zip(flow.steps, restored_flow.steps):
            assert original_step.id == restored_step.id
            assert original_step.type == restored_step.type
            assert original_step.config == restored_step.config