"""
Unit tests for validation system components.

Tests cover schema validator, flow validator, auto-corrector, and
validation orchestration to ensure comprehensive flow validation.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.models.flow_schema import CampaignFlow, SendMessageStep, DelayStep
from src.services.validation.schema_validator import SchemaValidator
from src.services.validation.flow_validator import FlowValidator
from src.services.validation.auto_corrector import AutoCorrector
from src.services.validation.validator import FlowValidator as ValidationOrchestrator, ValidationConfig
from src.services.validation.reporting import ValidationReporter


class TestSchemaValidator:
    """Test schema validator functionality."""

    @pytest.fixture
    def schema_validator(self):
        """Create schema validator instance."""
        return SchemaValidator()

    def test_validate_valid_campaign_flow(self, schema_validator, sample_campaign_flow):
        """Test validating a valid campaign flow."""
        result = schema_validator.validate(sample_campaign_flow)

        assert result.is_valid is True
        assert result.total_issues == 0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_invalid_campaign_flow_missing_required_fields(self, schema_validator):
        """Test validating campaign flow with missing required fields."""
        invalid_flow = {
            "steps": [  # Missing initialStepID
                {
                    "type": "SendMessage",  # Missing id
                    "config": {}
                }
            ]
        }

        result = schema_validator.validate(invalid_flow)

        assert result.is_valid is False
        assert result.total_issues > 0
        assert len(result.errors) > 0

        # Check for specific error messages
        error_messages = [error.message for error in result.errors]
        assert any("initialStepID" in msg for msg in error_messages)
        assert any("id" in msg for msg in error_messages)

    def test_validate_invalid_step_type(self, schema_validator):
        """Test validating campaign flow with invalid step type."""
        invalid_flow = {
            "initialStepID": "invalid_step",
            "steps": [
                {
                    "id": "invalid_step",
                    "type": "InvalidStepType",
                    "config": {}
                }
            ]
        }

        result = schema_validator.validate(invalid_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("InvalidStepType" in msg or "invalid" in msg.lower() for msg in error_messages)

    def test_validate_send_message_step_missing_message_content(self, schema_validator):
        """Test validating SendMessage step without message content."""
        invalid_flow = {
            "initialStepID": "send_step",
            "steps": [
                {
                    "id": "send_step",
                    "type": "SendMessage",
                    "config": {
                        "recipient": {"type": "all"}
                        # Missing messageContent
                    }
                }
            ]
        }

        result = schema_validator.validate(invalid_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("messageContent" in msg or "message" in msg.lower() for msg in error_messages)

    def test_validate_delay_step_with_invalid_config(self, schema_validator):
        """Test validating Delay step with invalid configuration."""
        invalid_flow = {
            "initialStepID": "delay_step",
            "steps": [
                {
                    "id": "delay_step",
                    "type": "Delay",
                    "config": {
                        "delayMinutes": -10  # Negative delay
                    }
                }
            ]
        }

        result = schema_validator.validate(invalid_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("delay" in msg.lower() and "negative" in msg.lower() for msg in error_messages)

    def test_validate_condition_step_missing_branches(self, schema_validator):
        """Test validating Condition step without proper branches."""
        invalid_flow = {
            "initialStepID": "condition_step",
            "steps": [
                {
                    "id": "condition_step",
                    "type": "Condition",
                    "config": {
                        "conditions": [
                            {
                                "field": "user.tag",
                                "operator": "equals",
                                "value": "premium"
                            }
                        ]
                        # Missing trueStepId and falseStepId
                    }
                }
            ]
        }

        result = schema_validator.validate(invalid_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("trueStepId" in msg or "falseStepId" in msg for msg in error_messages)

    def test_validate_webhook_step_invalid_url(self, schema_validator):
        """Test validating Webhook step with invalid URL."""
        invalid_flow = {
            "initialStepID": "webhook_step",
            "steps": [
                {
                    "id": "webhook_step",
                    "type": "Webhook",
                    "config": {
                        "url": "not-a-valid-url",
                        "method": "POST"
                    }
                }
            ]
        }

        result = schema_validator.validate(invalid_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("url" in msg.lower() and "invalid" in msg.lower() for msg in error_messages)

    def test_validate_circular_reference_in_schema(self, schema_validator):
        """Test schema validation with potential circular reference."""
        circular_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}},
                    "nextStepId": "step2"
                },
                {
                    "id": "step2",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello again"}, "recipient": {"type": "all"}},
                    "nextStepId": "step1"  # Back to step1
                }
            ]
        }

        # Schema validator should catch this as a warning or error
        result = schema_validator.validate(circular_flow)

        # Circular reference should be flagged (may be warning or error depending on implementation)
        has_circular_issue = any(
            "circular" in issue.message.lower() or "cycle" in issue.message.lower()
            for issue in result.issues
        )
        assert has_circular_issue

    def test_validate_empty_steps_array(self, schema_validator):
        """Test validating campaign flow with empty steps array."""
        empty_flow = {
            "initialStepID": "nonexistent",
            "steps": []
        }

        result = schema_validator.validate(empty_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("initialStepID" in msg for msg in error_messages)

    def test_validate_duplicate_step_ids(self, schema_validator):
        """Test validating campaign flow with duplicate step IDs."""
        duplicate_flow = {
            "initialStepID": "duplicate_step",
            "steps": [
                {
                    "id": "duplicate_step",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}}
                },
                {
                    "id": "duplicate_step",  # Same ID
                    "type": "Delay",
                    "config": {"delayMinutes": 60}
                }
            ]
        }

        result = schema_validator.validate(duplicate_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("duplicate" in msg.lower() for msg in error_messages)

    def test_validate_metadata_preservation(self, schema_validator, sample_campaign_flow):
        """Test that metadata is preserved during validation."""
        result = schema_validator.validate(sample_campaign_flow)

        assert result.is_valid is True
        # Metadata should be preserved if valid
        if result.flow_data:
            assert "metadata" in result.flow_data

    def test_validate_with_model_instance(self, schema_validator, sample_campaign_flow):
        """Test validating with a CampaignFlow model instance."""
        campaign_model = CampaignFlow(**sample_campaign_flow)
        result = schema_validator.validate(campaign_model)

        assert result.is_valid is True
        assert result.total_issues == 0


class TestFlowValidator:
    """Test flow validator functionality."""

    @pytest.fixture
    def flow_validator(self):
        """Create flow validator instance."""
        return FlowValidator()

    def test_validate_linear_flow(self, flow_validator):
        """Test validating a simple linear flow."""
        linear_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}},
                    "nextStepId": "step2"
                },
                {
                    "id": "step2",
                    "type": "Delay",
                    "config": {"delayMinutes": 60},
                    "nextStepId": "step3"
                },
                {
                    "id": "step3",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Final message"}, "recipient": {"type": "all"}}
                }
            ]
        }

        result = flow_validator.validate_flow(linear_flow)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_flow_with_circular_reference(self, flow_validator):
        """Test detecting circular references."""
        circular_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}},
                    "nextStepId": "step2"
                },
                {
                    "id": "step2",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello again"}, "recipient": {"type": "all"}},
                    "nextStepId": "step3"
                },
                {
                    "id": "step3",
                    "type": "Delay",
                    "config": {"delayMinutes": 60},
                    "nextStepId": "step1"  # Circular reference back to step1
                }
            ]
        }

        result = flow_validator.validate_flow(circular_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("circular" in msg.lower() or "cycle" in msg.lower() for msg in error_messages)

    def test_validate_flow_with_broken_reference(self, flow_validator):
        """Test detecting broken step references."""
        broken_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}},
                    "nextStepId": "nonexistent_step"  # References non-existent step
                }
            ]
        }

        result = flow_validator.validate_flow(broken_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("nonexistent_step" in msg or "reference" in msg.lower() for msg in error_messages)

    def test_validate_flow_with_orphaned_steps(self, flow_validator):
        """Test detecting orphaned steps (unreachable)."""
        orphaned_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}}
                    # No nextStepId - flow ends here
                },
                {
                    "id": "orphaned_step",  # This step is unreachable
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Orphaned"}, "recipient": {"type": "all"}}
                }
            ]
        }

        result = flow_validator.validate_flow(orphaned_flow)

        # Orphaned steps should be flagged as warnings or errors
        has_orphan_warning = any(
            "orphan" in issue.message.lower() or "unreachable" in issue.message.lower()
            for issue in result.issues
        )
        assert has_orphan_warning

    def test_validate_complex_branching_flow(self, flow_validator):
        """Test validating complex branching flow."""
        complex_flow = {
            "initialStepID": "condition_step",
            "steps": [
                {
                    "id": "condition_step",
                    "type": "Condition",
                    "config": {
                        "conditions": [{"field": "user.segment", "operator": "equals", "value": "premium"}],
                        "trueStepId": "premium_flow",
                        "falseStepId": "regular_flow"
                    }
                },
                {
                    "id": "premium_flow",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Premium message"}, "recipient": {"type": "all"}}
                },
                {
                    "id": "regular_flow",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Regular message"}, "recipient": {"type": "all"}}
                }
            ]
        }

        result = flow_validator.validate_flow(complex_flow)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_condition_with_missing_branch(self, flow_validator):
        """Test condition step with missing branch."""
        incomplete_flow = {
            "initialStepID": "condition_step",
            "steps": [
                {
                    "id": "condition_step",
                    "type": "Condition",
                    "config": {
                        "conditions": [{"field": "user.tag", "operator": "equals", "value": "test"}],
                        "trueStepId": "true_branch"
                        # Missing falseStepId
                    }
                },
                {
                    "id": "true_branch",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "True branch"}, "recipient": {"type": "all"}}
                }
            ]
        }

        result = flow_validator.validate_flow(incomplete_flow)

        assert result.is_valid is False
        error_messages = [error.message for error in result.errors]
        assert any("falseStepId" in msg or "missing branch" in msg.lower() for msg in error_messages)

    def test_validate_ab_test_branches(self, flow_validator):
        """Test A/B test step validation."""
        ab_test_flow = {
            "initialStepID": "ab_test",
            "steps": [
                {
                    "id": "ab_test",
                    "type": "ATest",
                    "config": {
                        "testName": "subject_test",
                        "variants": [
                            {"name": "variant_a", "weight": 50},
                            {"name": "variant_b", "weight": 50}
                        ],
                        "variantAId": "variant_a_step",
                        "variantBId": "variant_b_step"
                    }
                },
                {
                    "id": "variant_a_step",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Variant A"}, "recipient": {"type": "all"}}
                },
                {
                    "id": "variant_b_step",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Variant B"}, "recipient": {"type": "all"}}
                }
            ]
        }

        result = flow_validator.validate_flow(ab_test_flow)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_flow_complexity_metrics(self, flow_validator):
        """Test flow complexity calculation."""
        simple_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}}
                }
            ]
        }

        complex_flow = {
            "initialStepID": "start",
            "steps": [
                {"id": "start", "type": "Condition", "config": {
                    "conditions": [{"field": "test", "operator": "equals", "value": "test"}],
                    "trueStepId": "branch1", "falseStepId": "branch2"
                }},
                {"id": "branch1", "type": "ATest", "config": {
                    "variantAId": "variant1", "variantBId": "variant2"
                }},
                {"id": "variant1", "type": "SendMessage", "config": {"messageContent": {"body": "V1"}, "recipient": {"type": "all"}}},
                {"id": "variant2", "type": "SendMessage", "config": {"messageContent": {"body": "V2"}, "recipient": {"type": "all"}}},
                {"id": "branch2", "type": "Webhook", "config": {"url": "https://example.com", "method": "POST"}}
            ]
        }

        simple_result = flow_validator.validate_flow(simple_flow)
        complex_result = flow_validator.validate_flow(complex_flow)

        # Complex flow should have higher complexity score
        assert complex_result.complexity_score > simple_result.complexity_score

    def test_validate_best_practices(self, flow_validator):
        """Test best practices validation."""
        problematic_flow = {
            "initialStepID": "immediate_webhook",
            "steps": [
                {
                    "id": "immediate_webhook",
                    "type": "Webhook",
                    "config": {
                        "url": "https://example.com/webhook",
                        "method": "POST",
                        "timeout": 300,  # Very long timeout
                        "retries": 10     # Too many retries
                    }
                }
            ]
        }

        result = flow_validator.validate_flow(problematic_flow)

        # Should generate warnings for best practice violations
        has_timeout_warning = any(
            "timeout" in issue.message.lower() for issue in result.warnings
        )
        has_retry_warning = any(
            "retry" in issue.message.lower() for issue in result.warnings
        )

        assert has_timeout_warning or has_retry_warning


class TestAutoCorrector:
    """Test auto-corrector functionality."""

    @pytest.fixture
    def auto_corrector(self):
        """Create auto-corrector instance."""
        return AutoCorrector()

    def test_correct_missing_initial_step_id(self, auto_corrector):
        """Test auto-correction of missing initialStepID."""
        invalid_flow = {
            "steps": [
                {
                    "id": "only_step",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}}
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(invalid_flow)

        assert "initialStepID" in corrected_flow
        assert corrected_flow["initialStepID"] == "only_step"
        assert len(corrections) > 0
        assert any("initialStepID" in correction.description for correction in corrections)

    def test_correct_empty_step_id(self, auto_corrector):
        """Test auto-correction of empty step ID."""
        invalid_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "",  # Empty ID
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}}
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(invalid_flow)

        assert corrected_flow["steps"][0]["id"] != ""
        assert corrected_flow["steps"][0]["id"].startswith("step_")
        assert len(corrections) > 0

    def test_correct_invalid_step_type(self, auto_corrector):
        """Test auto-correction of invalid step type."""
        invalid_flow = {
            "initialStepID": "invalid_step",
            "steps": [
                {
                    "id": "invalid_step",
                    "type": "InvalidStepType",
                    "config": {}
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(invalid_flow)

        # Should change to a valid default step type
        assert corrected_flow["steps"][0]["type"] in ["SendMessage", "Delay"]
        assert len(corrections) > 0

    def test_correct_missing_message_content(self, auto_corrector):
        """Test auto-correction of missing message content."""
        invalid_flow = {
            "initialStepID": "send_step",
            "steps": [
                {
                    "id": "send_step",
                    "type": "SendMessage",
                    "config": {
                        "recipient": {"type": "all"}
                        # Missing messageContent
                    }
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(invalid_flow)

        assert "messageContent" in corrected_flow["steps"][0]["config"]
        assert "body" in corrected_flow["steps"][0]["config"]["messageContent"]
        assert len(corrections) > 0

    def test_correct_negative_delay(self, auto_corrector):
        """Test auto-correction of negative delay values."""
        invalid_flow = {
            "initialStepID": "delay_step",
            "steps": [
                {
                    "id": "delay_step",
                    "type": "Delay",
                    "config": {
                        "delayMinutes": -10  # Negative
                    }
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(invalid_flow)

        assert corrected_flow["steps"][0]["config"]["delayMinutes"] > 0
        assert len(corrections) > 0

    def test_correct_broken_next_step_reference(self, auto_corrector):
        """Test auto-correction of broken next step references."""
        invalid_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {"messageContent": {"body": "Hello"}, "recipient": {"type": "all"}},
                    "nextStepId": "nonexistent"  # Broken reference
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(invalid_flow)

        # Should remove or fix the broken reference
        assert "nextStepId" not in corrected_flow["steps"][0] or corrected_flow["steps"][0]["nextStepId"] is None
        assert len(corrections) > 0

    def test_no_corrections_for_valid_flow(self, auto_corrector, sample_campaign_flow):
        """Test that valid flows don't get corrections."""
        corrected_flow, corrections = auto_corrector.correct_flow(sample_campaign_flow)

        assert len(corrections) == 0
        # Flow should remain unchanged
        assert corrected_flow["initialStepID"] == sample_campaign_flow["initialStepID"]

    def test_multiple_corrections_in_single_flow(self, auto_corrector):
        """Test applying multiple corrections to a single flow."""
        very_invalid_flow = {
            "steps": [  # Missing initialStepID
                {
                    "id": "",  # Empty ID
                    "type": "InvalidStepType",  # Invalid type
                    "config": {}  # Missing required config for any valid type
                },
                {
                    "id": "valid_step",
                    "type": "Delay",
                    "config": {"delayMinutes": -5}  # Negative delay
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(very_invalid_flow)

        assert len(corrections) >= 3  # Should have multiple corrections
        assert "initialStepID" in corrected_flow
        assert corrected_flow["steps"][0]["id"] != ""
        assert corrected_flow["steps"][1]["config"]["delayMinutes"] > 0

    def test_correction_risk_assessment(self, auto_corrector):
        """Test risk assessment for corrections."""
        risky_flow = {
            "initialStepID": "complex_step",
            "steps": [
                {
                    "id": "complex_step",
                    "type": "Condition",
                    "config": {
                        "conditions": [{"field": "complex.field", "operator": "equals", "value": "test"}],
                        "trueStepId": "missing_branch",  # Missing branch
                        "falseStepId": "also_missing"
                    }
                }
            ]
        }

        corrected_flow, corrections = auto_corrector.correct_flow(risky_flow)

        # Complex corrections should have risk assessment
        for correction in corrections:
            assert hasattr(correction, 'risk_level')
            assert correction.risk_level in ['low', 'medium', 'high']


class TestValidationOrchestrator:
    """Test validation orchestration."""

    @pytest.fixture
    def validation_orchestrator(self):
        """Create validation orchestrator instance."""
        config = ValidationConfig(
            enable_schema_validation=True,
            enable_flow_validation=True,
            enable_auto_correction=True,
            strict_mode=False
        )
        return ValidationOrchestrator(config)

    def test_full_validation_pipeline_valid_flow(self, validation_orchestrator, sample_campaign_flow):
        """Test full validation pipeline with valid flow."""
        result = validation_orchestrator.validate_flow(
            flow_data=sample_campaign_flow,
            apply_corrections=True,
            raise_on_error=False
        )

        assert result.is_valid is True
        assert result.total_issues == 0
        assert result.flow_data is not None

    def test_full_validation_pipeline_invalid_flow(self, validation_orchestrator):
        """Test full validation pipeline with invalid flow."""
        invalid_flow = {
            "steps": [
                {
                    "id": "invalid_step",
                    "type": "InvalidType",
                    "config": {}
                }
            ]
        }

        result = validation_orchestrator.validate_flow(
            flow_data=invalid_flow,
            apply_corrections=True,
            raise_on_error=False
        )

        # Should attempt corrections
        assert result.corrections_applied > 0
        # Result may still be invalid if corrections couldn't fix everything

    def test_validation_with_strict_mode(self, validation_orchestrator):
        """Test validation in strict mode."""
        slightly_invalid_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {
                        "recipient": {"type": "all"}
                        # Missing messageContent
                    }
                }
            ]
        }

        validation_orchestrator.config.strict_mode = True

        result = validation_orchestrator.validate_flow(
            flow_data=slightly_invalid_flow,
            apply_corrections=False,
            raise_on_error=False
        )

        assert result.is_valid is False

    def test_validation_with_disabled_components(self, validation_orchestrator):
        """Test validation with specific components disabled."""
        invalid_flow = {
            "initialStepID": "step1",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {
                        "messageContent": {"body": "Hello"},
                        "recipient": {"type": "all"}
                    },
                    "nextStepId": "nonexistent"  # Flow validation issue
                }
            ]
        }

        # Disable flow validation
        validation_orchestrator.config.enable_flow_validation = False

        result = validation_orchestrator.validate_flow(
            flow_data=invalid_flow,
            apply_corrections=False,
            raise_on_error=False
        )

        # Should pass schema validation but miss flow issues
        assert result.is_valid is True or len([e for e in result.errors if "nonexistent" in str(e.message)]) == 0

    def test_validation_performance_timing(self, validation_orchestrator, sample_campaign_flow):
        """Test validation performance timing."""
        import time

        start_time = time.time()
        result = validation_orchestrator.validate_flow(
            flow_data=sample_campaign_flow,
            apply_corrections=True,
            raise_on_error=False
        )
        end_time = time.time()

        validation_time = (end_time - start_time) * 1000

        assert validation_time < 5000  # Should complete within 5 seconds
        assert hasattr(result, 'validation_time_ms')

    def test_quick_validation_method(self, validation_orchestrator, sample_campaign_flow):
        """Test quick validation method."""
        result = validation_orchestrator.quick_validate(sample_campaign_flow)

        assert result.is_valid is True
        assert result.total_issues == 0

    def test_validation_error_aggregation(self, validation_orchestrator):
        """Test validation error aggregation from multiple sources."""
        very_invalid_flow = {
            "steps": [
                {
                    "id": "invalid",
                    "type": "InvalidType",
                    "config": {}
                }
            ]
        }

        result = validation_orchestrator.validate_flow(
            flow_data=very_invalid_flow,
            apply_corrections=False,
            raise_on_error=False
        )

        # Should collect errors from both schema and flow validation
        assert len(result.errors) > 0
        assert result.total_issues == len(result.errors) + len(result.warnings)

    def test_validation_config_update(self, validation_orchestrator):
        """Test updating validation configuration."""
        new_config = {
            "strict_mode": True,
            "enable_auto_correction": False,
            "auto_correction_risk_threshold": "low"
        }

        validation_orchestrator.update_config(**new_config)

        assert validation_orchestrator.config.strict_mode is True
        assert validation_orchestrator.config.enable_auto_correction is False
        assert validation_orchestrator.config.auto_correction_risk_threshold == "low"


class TestValidationReporter:
    """Test validation reporting functionality."""

    @pytest.fixture
    def validation_reporter(self):
        """Create validation reporter instance."""
        return ValidationReporter()

    def test_create_validation_report(self, validation_reporter):
        """Test creating validation report."""
        # Mock validation summary
        mock_summary = MagicMock()
        mock_summary.is_valid = False
        mock_summary.total_issues = 3
        mock_summary.error_count = 2
        mock_summary.warning_count = 1
        mock_summary.corrections_applied = 1
        mock_summary.flow_data = {"initialStepID": "test", "steps": []}
        mock_summary.errors = [
            MagicMock(message="Error 1", field="step1", severity="error"),
            MagicMock(message="Error 2", field="step2", severity="error")
        ]
        mock_summary.warnings = [
            MagicMock(message="Warning 1", field="step3", severity="warning")
        ]

        report = validation_reporter.create_report(mock_summary, "test_campaign_123")

        assert report.campaign_id == "test_campaign_123"
        assert report.is_valid is False
        assert report.total_issues == 3
        assert report.quality_score < 100

    def test_get_latest_report(self, validation_reporter):
        """Test retrieving latest report for campaign."""
        # Create a report first
        mock_summary = MagicMock()
        mock_summary.is_valid = True
        mock_summary.total_issues = 0
        mock_summary.flow_data = {"initialStepID": "test", "steps": []}

        validation_reporter.create_report(mock_summary, "test_campaign")
        latest_report = validation_reporter.get_latest_report("test_campaign")

        assert latest_report is not None
        assert latest_report.campaign_id == "test_campaign"
        assert latest_report.is_valid is True

    def test_get_reports_summary(self, validation_reporter):
        """Test getting reports summary."""
        # Create multiple reports
        for i in range(5):
            mock_summary = MagicMock()
            mock_summary.is_valid = i % 2 == 0  # Alternate valid/invalid
            mock_summary.total_issues = i
            mock_summary.flow_data = {"initialStepID": f"test_{i}", "steps": []}

            validation_reporter.create_report(mock_summary, f"campaign_{i}")

        summary = validation_reporter.get_reports_summary()

        assert summary["total_reports"] == 5
        assert summary["valid_campaigns"] == 3  # 0, 2, 4
        assert summary["invalid_campaigns"] == 2  # 1, 3
        assert "average_quality_score" in summary

    def test_delete_old_reports(self, validation_reporter):
        """Test deleting old reports."""
        # Create reports with different timestamps
        from datetime import datetime, timezone, timedelta

        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        recent_time = datetime.now(timezone.utc) - timedelta(days=1)

        mock_summary = MagicMock()
        mock_summary.is_valid = True
        mock_summary.total_issues = 0
        mock_summary.flow_data = {"initialStepID": "test", "steps": []}

        # Create old report
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = old_time
            validation_reporter.create_report(mock_summary, "old_campaign")

        # Create recent report
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = recent_time
            validation_reporter.create_report(mock_summary, "recent_campaign")

        # Delete reports older than 5 days
        deleted_count = validation_reporter.delete_old_reports(days=5)

        assert deleted_count == 1
        assert validation_reporter.get_latest_report("recent_campaign") is not None
        assert validation_reporter.get_latest_report("old_campaign") is None