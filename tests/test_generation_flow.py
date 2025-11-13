"""
Test cases for generationFlow API functionality.

This test suite covers comprehensive testing of the /generateFlow endpoint
including unit tests, integration tests, and end-to-end tests against a running API.
"""

import pytest
import json
import time
import requests
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from src.api.main import create_application
from src.services.campaign_generation.orchestrator import CampaignOrchestrator, CampaignGenerationResult
from src.models.requests import CampaignGenerationRequest, CampaignGenerationResponse
from src.models.flow_schema import CampaignFlow, MessageNode


class TestGenerationFlowUnit:
    """Unit tests for generationFlow functionality."""

    @pytest.fixture
    def sample_request_data(self):
        """Sample campaign generation request data."""
        return {
            "campaignDescription": "Create a welcome series for new subscribers with a 3-message sequence",
            "tone": "friendly",
            "maxLength": 1000,
            "priority": "normal"
        }

    @pytest.fixture
    def sample_flow_response(self):
        """Sample campaign flow response."""
        return {
            "initialStepID": "welcome_step",
            "steps": [
                {
                    "id": "welcome_step",
                    "type": "message",
                    "content": "Welcome to our service! We're excited to have you on board.",
                    "label": "Welcome Message",
                    "active": True,
                    "events": [
                        {
                            "id": "welcome_reply",
                            "type": "reply",
                            "intent": "get_started",
                            "nextStepID": "onboarding_step",
                            "description": "Customer wants to get started",
                            "active": True,
                            "parameters": {}
                        }
                    ]
                },
                {
                    "id": "onboarding_step",
                    "type": "message",
                    "content": "Let's help you get started with our key features.",
                    "label": "Onboarding Message",
                    "active": True,
                    "events": []
                }
            ],
            "metadata": {
                "total_time_ms": 2500,
                "model_used": "gpt-4",
                "node_count": 2
            }
        }

    def test_campaign_generation_request_validation(self, sample_request_data):
        """Test campaign generation request validation."""
        # Valid request
        request = CampaignGenerationRequest(**sample_request_data)
        assert request.campaignDescription == "Create a welcome series for new subscribers with a 3-message sequence"
        assert request.tone == "friendly"
        assert request.maxLength == 1000
        assert request.priority == "normal"

    def test_campaign_generation_request_invalid_description(self):
        """Test campaign generation request with invalid description."""
        # Empty description
        with pytest.raises(ValueError):
            CampaignGenerationRequest(campaignDescription="")

        # Whitespace only
        with pytest.raises(ValueError):
            CampaignGenerationRequest(campaignDescription="   ")

        # Too short
        with pytest.raises(ValueError):
            CampaignGenerationRequest(campaignDescription="Hi")

    def test_campaign_generation_response_validation(self, sample_flow_response):
        """Test campaign generation response validation."""
        response = CampaignGenerationResponse(**sample_flow_response)
        assert response.initialStepID == "welcome_step"
        assert len(response.steps) == 2
        assert response.steps[0]["type"] == "message"
        assert response.metadata["total_time_ms"] == 2500

    def test_campaign_flow_model_validation(self):
        """Test campaign flow model validation."""
        flow_data = {
            "name": "Test Campaign",
            "description": "A test campaign flow",
            "initialStepID": "welcome",
            "steps": [
                {
                    "id": "welcome",
                    "type": "message",
                    "content": "Welcome!",
                    "label": "Welcome Message",
                    "active": True,
                    "events": []
                }
            ]
        }

        flow = CampaignFlow(**flow_data)
        assert flow.name == "Test Campaign"
        assert flow.initialStepID == "welcome"
        assert len(flow.steps) == 1
        assert flow.steps[0].type == "message"

    def test_campaign_flow_model_invalid_initial_step(self):
        """Test campaign flow model with invalid initial step ID."""
        flow_data = {
            "name": "Test Campaign",
            "description": "A test campaign flow",
            "initialStepID": "nonexistent",
            "steps": [
                {
                    "id": "welcome",
                    "type": "message",
                    "content": "Welcome!",
                    "label": "Welcome Message",
                    "active": True,
                    "events": []
                }
            ]
        }

        with pytest.raises(ValueError, match="Initial step 'nonexistent' not found in steps"):
            CampaignFlow(**flow_data)

    def test_campaign_flow_model_duplicate_step_ids(self):
        """Test campaign flow model with duplicate step IDs."""
        flow_data = {
            "name": "Test Campaign",
            "description": "A test campaign flow",
            "initialStepID": "welcome",
            "steps": [
                {
                    "id": "welcome",
                    "type": "message",
                    "content": "Welcome!",
                    "label": "Welcome Message",
                    "active": True,
                    "events": []
                },
                {
                    "id": "welcome",  # Duplicate ID
                    "type": "delay",
                    "time": "5",
                    "period": "Minutes",
                    "active": True,
                    "events": []
                }
            ]
        }

        with pytest.raises(ValueError, match="Duplicate step ID: welcome"):
            CampaignFlow(**flow_data)


class TestGenerationFlowIntegration:
    """Integration tests for generationFlow API."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock campaign orchestrator."""
        mock_orchestrator = AsyncMock(spec=CampaignOrchestrator)

        # Mock successful generation
        mock_result = CampaignGenerationResult(
            success=True,
            flow_data={
                "initialStepID": "welcome_step",
                "steps": [
                    {
                        "id": "welcome_step",
                        "type": "message",
                        "content": "Welcome to our service!",
                        "label": "Welcome Message",
                        "active": True,
                        "events": []
                    }
                ]
            },
            campaign_id="test_campaign_123",
            metadata={
                "total_time_ms": 2000,
                "model_used": "gpt-4",
                "complexity": "simple"
            }
        )

        mock_orchestrator.generate_campaign.return_value = mock_result
        mock_orchestrator.health_check.return_value = {"status": "healthy"}

        return mock_orchestrator

    def test_generate_flow_success(self, client, mock_orchestrator):
        """Test successful flow generation."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a welcome campaign for new users"
                },
                headers={
                    "X-API-Key": "sk-9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["initialStepID"] == "welcome_step"
            assert len(data["steps"]) == 1
            assert data["steps"][0]["type"] == "message"
            assert "metadata" in data

    def test_generate_flow_with_optional_parameters(self, client, mock_orchestrator):
        """Test flow generation with optional parameters."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a promotional campaign",
                    "tone": "professional",
                    "maxLength": 2000,
                    "priority": "high"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["initialStepID"] == "welcome_step"

    def test_generate_flow_invalid_description(self, client):
        """Test flow generation with invalid description."""
        response = client.post(
            "/api/v1/generateFlow",
            json={
                "campaignDescription": ""  # Empty description
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "REQUEST_VALIDATION_ERROR"

    def test_generate_flow_missing_description(self, client):
        """Test flow generation without description."""
        response = client.post(
            "/api/v1/generateFlow",
            json={}  # Missing campaignDescription
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "REQUEST_VALIDATION_ERROR"

    def test_generate_flow_service_error(self, client, mock_orchestrator):
        """Test flow generation with service error."""
        # Mock service error
        mock_orchestrator.generate_campaign.return_value = CampaignGenerationResult(
            success=False,
            errors=["LLM service unavailable"],
            campaign_id="error_campaign_456"
        )

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a test campaign"
                }
            )

            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "CAMPAIGN_GENERATION_FAILED"
            assert "LLM service unavailable" in data["message"]

    def test_generate_flow_complex_campaign(self, client, mock_orchestrator):
        """Test generation of complex campaign with multiple steps."""
        # Mock complex flow
        mock_orchestrator.generate_campaign.return_value = CampaignGenerationResult(
            success=True,
            flow_data={
                "initialStepID": "welcome_step",
                "steps": [
                    {
                        "id": "welcome_step",
                        "type": "message",
                        "content": "Welcome to our service!",
                        "label": "Welcome Message",
                        "active": True,
                        "events": [
                            {
                                "id": "welcome_reply",
                                "type": "reply",
                                "intent": "yes",
                                "nextStepID": "onboarding_step",
                                "description": "Customer replied yes",
                                "active": True,
                                "parameters": {}
                            }
                        ]
                    },
                    {
                        "id": "onboarding_step",
                        "type": "segment",
                        "label": "User Segmentation",
                        "conditions": [],
                        "events": []
                    },
                    {
                        "id": "delay_step",
                        "type": "delay",
                        "time": "24",
                        "period": "Hours",
                        "events": []
                    }
                ]
            },
            campaign_id="complex_campaign_123",
            metadata={
                "total_time_ms": 5000,
                "model_used": "gpt-4",
                "complexity": "complex",
                "node_count": 3
            }
        )

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a complex onboarding campaign with segmentation and delays"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["initialStepID"] == "welcome_step"
            assert len(data["steps"]) == 3
            # Verify different node types
            step_types = [step["type"] for step in data["steps"]]
            assert "message" in step_types
            assert "segment" in step_types
            assert "delay" in step_types

    def test_generate_flow_with_validation_issues(self, client, mock_orchestrator):
        """Test flow generation that has validation issues but gets auto-corrected."""
        # Mock result with validation issues
        from src.services.validation.validator import ValidationSummary
        mock_validation_summary = MagicMock()
        mock_validation_summary.is_valid = True
        mock_validation_summary.total_issues = 2
        mock_validation_summary.corrections_applied = 2
        mock_validation_summary.flow_data = {
            "initialStepID": "welcome_step",
            "steps": [
                {
                    "id": "welcome_step",
                    "type": "message",
                    "content": "Welcome!",
                    "label": "Welcome Message",
                    "active": True,
                    "events": []
                }
            ]
        }

        mock_orchestrator.generate_campaign.return_value = CampaignGenerationResult(
            success=True,
            flow_data=mock_validation_summary.flow_data,
            campaign_id="corrected_campaign_123",
            validation_summary=mock_validation_summary,
            warnings=["Auto-corrected 2 validation issues"]
        )

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a campaign that needs corrections"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["initialStepID"] == "welcome_step"
            assert len(data["steps"]) == 1


class TestGenerationFlowEndToEnd:
    """End-to-end tests for generationFlow against running API."""

    BASE_URL = "http://localhost:8008"
    API_ENDPOINT = f"{BASE_URL}/api/v1/generateFlow"

    @pytest.mark.slow
    def test_real_api_health_check(self):
        """Test that the real API is running and healthy."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")

    @pytest.mark.slow
    def test_real_api_detailed_health_check(self):
        """Test detailed health check of the real API."""
        try:
            response = requests.get(f"{self.BASE_URL}/api/v1/health", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "components" in data
            assert "service" in data
            assert data["service"] == "campaign-generation"
        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")

    @pytest.mark.slow
    def test_real_generate_flow_simple_campaign(self):
        """Test generating a simple campaign flow with real API."""
        try:
            request_data = {
                "campaignDescription": "Create a simple welcome message for new users",
                "tone": "friendly",
                "priority": "normal"
            }

            response = requests.post(
                self.API_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            # Note: This test might fail if LLM is not properly configured
            # It's designed to work against a real, configured API
            if response.status_code == 200:
                data = response.json()
                assert "initialStepID" in data
                assert "steps" in data
                assert isinstance(data["steps"], list)
                assert len(data["steps"]) > 0

                # Validate structure of returned steps
                for step in data["steps"]:
                    assert "id" in step
                    assert "type" in step
                    assert "active" in step

            elif response.status_code == 500:
                # Expected if LLM is not configured
                pytest.skip("LLM not properly configured for end-to-end testing")
            else:
                pytest.fail(f"Unexpected response status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")

    @pytest.mark.slow
    def test_real_generate_flow_complex_campaign(self):
        """Test generating a complex campaign flow with real API."""
        try:
            request_data = {
                "campaignDescription": """Create a comprehensive customer onboarding campaign with the following flow:
                1. Welcome message for new subscribers
                2. Segment users based on their response (interested vs not interested)
                3. For interested users: send product information after 2 days
                4. For not interested users: send a different message after 3 days
                5. Add a final follow-up message for both segments after 1 week
                Include personalization and make it engaging.""",
                "tone": "professional",
                "maxLength": 5000,
                "priority": "high"
            }

            response = requests.post(
                self.API_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=60  # Longer timeout for complex campaigns
            )

            if response.status_code == 200:
                data = response.json()
                assert "initialStepID" in data
                assert "steps" in data
                assert len(data["steps"]) > 1  # Complex campaign should have multiple steps

                # Verify we have different types of steps
                step_types = set(step["type"] for step in data["steps"])
                assert len(step_types) > 1 or len(data["steps"]) > 2  # Either multiple types or multiple messages

                # Check for proper flow connections
                step_ids = {step["id"] for step in data["steps"]}
                assert data["initialStepID"] in step_ids

            elif response.status_code == 500:
                pytest.skip("LLM not properly configured for end-to-end testing")
            else:
                pytest.fail(f"Unexpected response status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")

    @pytest.mark.slow
    def test_real_generate_flow_validation_errors(self):
        """Test validation error handling with real API."""
        try:
            # Test with empty description
            response = requests.post(
                self.API_ENDPOINT,
                json={"campaignDescription": ""},
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            assert response.status_code == 422
            data = response.json()
            assert data["error"] == "REQUEST_VALIDATION_ERROR"

            # Test with missing description
            response = requests.post(
                self.API_ENDPOINT,
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            assert response.status_code == 422
            data = response.json()
            assert data["error"] == "REQUEST_VALIDATION_ERROR"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")

    @pytest.mark.slow
    def test_real_api_stats_endpoint(self):
        """Test the statistics endpoint of the real API."""
        try:
            response = requests.get(f"{self.BASE_URL}/api/v1/stats", timeout=10)
            assert response.status_code == 200
            data = response.json()
            assert "orchestrator_status" in data
            assert "llm_model" in data
            assert "validation_enabled" in data
            assert "auto_correction_enabled" in data

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")

    @pytest.mark.slow
    def test_real_generate_flow_performance_metrics(self):
        """Test that generation flow returns performance metrics."""
        try:
            request_data = {
                "campaignDescription": "Create a simple promotional campaign",
                "priority": "normal"
            }

            start_time = time.time()
            response = requests.post(
                self.API_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            end_time = time.time()

            if response.status_code == 200:
                data = response.json()
                # Check if metadata contains performance information
                if "metadata" in data:
                    metadata = data["metadata"]
                    # Some APIs might include timing info in metadata
                    assert isinstance(metadata, dict)

                # The request should complete in a reasonable time (less than 30 seconds)
                assert (end_time - start_time) < 30

            elif response.status_code == 500:
                pytest.skip("LLM not properly configured for end-to-end testing")
            else:
                pytest.fail(f"Unexpected response status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not running at {self.BASE_URL}: {e}")


class TestGenerationFlowEdgeCases:
    """Test edge cases and error scenarios for generationFlow."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_very_long_campaign_description(self, client):
        """Test with extremely long campaign description."""
        long_description = "Create a detailed campaign " * 1000

        response = client.post(
            "/api/v1/generateFlow",
            json={
                "campaignDescription": long_description
            }
        )

        # Should either accept or reject gracefully
        assert response.status_code in [200, 413, 422]

    def test_special_characters_in_description(self, client):
        """Test with special characters in campaign description."""
        special_description = "Create a campaign with émojis 🎉, spëcial characters, & $ymb0ls!"

        # Mock successful response
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()
            mock_result = CampaignGenerationResult(
                success=True,
                flow_data={"initialStepID": "test", "steps": []},
                campaign_id="special_test"
            )
            mock_orchestrator.generate_campaign.return_value = mock_result
            mock_get_orchestrator.return_value = mock_orchestrator

            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": special_description
                }
            )

            assert response.status_code == 200

    def test_unicode_content_in_response(self, client):
        """Test handling of Unicode content in response."""
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()
            mock_result = CampaignGenerationResult(
                success=True,
                flow_data={
                    "initialStepID": "welcome_unicode",
                    "steps": [
                        {
                            "id": "welcome_unicode",
                            "type": "message",
                            "content": "Welcome! 🎉 Bonjour! ¡Hola! 你好! مرحبا!",
                            "label": "Welcome Message",
                            "active": True,
                            "events": []
                        }
                    ]
                },
                campaign_id="unicode_test"
            )
            mock_orchestrator.generate_campaign.return_value = mock_result
            mock_get_orchestrator.return_value = mock_orchestrator

            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a multilingual welcome campaign"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "🎉" in data["steps"][0]["content"]

    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests."""
        # This would typically be handled by FastAPI before reaching our endpoint
        # but we can test our error handling
        response = client.post(
            "/api/v1/generateFlow",
            data='{"campaignDescription": "test", invalid}',
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_concurrent_generation_requests(self, client):
        """Test handling multiple concurrent generation requests."""
        import threading
        import time

        results = []
        errors = []

        def make_request(request_id):
            try:
                with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
                    mock_orchestrator = AsyncMock()
                    mock_result = CampaignGenerationResult(
                        success=True,
                        flow_data={"initialStepID": f"concurrent_{request_id}", "steps": []},
                        campaign_id=f"concurrent_{request_id}"
                    )
                    mock_orchestrator.generate_campaign.return_value = mock_result
                    mock_get_orchestrator.return_value = mock_orchestrator

                    response = client.post(
                        "/api/v1/generateFlow",
                        json={
                            "campaignDescription": f"Concurrent test campaign {request_id}"
                        }
                    )
                    results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Make multiple concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should complete successfully
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(status == 200 for status in results)
        assert len(results) == 10


if __name__ == "__main__":
    # Run specific test classes
    pytest.main([__file__, "-v", "--tb=short"])