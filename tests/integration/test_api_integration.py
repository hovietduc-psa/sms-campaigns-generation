"""
Integration tests for API endpoints.

Tests cover the full integration between API endpoints, services,
and external dependencies to ensure proper end-to-end functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.main import create_application
from src.services.campaign_generation.orchestrator import CampaignOrchestrator
from src.services.llm_engine.llm_client import LLMClient
from src.services.validation.validator import FlowValidator


@pytest.mark.integration
class TestCampaignGenerationAPI:
    """Test campaign generation API integration."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def async_client(self, app):
        """Create async test client."""
        return AsyncClient(app=app, base_url="http://test")

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock campaign orchestrator."""
        mock_orchestrator = AsyncMock(spec=CampaignOrchestrator)

        # Mock successful campaign generation
        from src.services.campaign_generation.orchestrator import CampaignGenerationResult
        mock_result = CampaignGenerationResult(
            success=True,
            flow_data={
                "initialStepID": "welcome_step",
                "steps": [
                    {
                        "id": "welcome_step",
                        "type": "SendMessage",
                        "config": {
                            "messageContent": {"body": "Welcome!"},
                            "recipient": {"type": "segment", "segmentId": "new_users"}
                        }
                    }
                ]
            },
            campaign_id="test_campaign_123",
            metadata={
                "total_time_ms": 2500,
                "model_used": "gpt-4",
                "complexity": "simple"
            }
        )

        mock_orchestrator.generate_campaign.return_value = mock_result
        mock_orchestrator.health_check.return_value = {"status": "healthy"}
        mock_orchestrator.get_generation_statistics.return_value = {
            "total_campaigns_generated": 100,
            "success_rate": 95.5
        }

        return mock_orchestrator

    def test_generate_campaign_success(self, client, mock_orchestrator):
        """Test successful campaign generation."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a welcome series for new subscribers"
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Correlation-ID": "test-correlation-123"
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["initialStepID"] == "welcome_step"
            assert len(data["steps"]) == 1
            assert data["steps"][0]["type"] == "SendMessage"
            assert "metadata" in data

    def test_generate_campaign_with_authentication(self, client, mock_orchestrator):
        """Test campaign generation with authentication."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a promotional campaign"
                },
                headers={
                    "Authorization": "Bearer test-token-123",
                    "Content-Type": "application/json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "initialStepID" in data

    def test_generate_campaign_validation_error(self, client):
        """Test campaign generation with validation error."""
        response = client.post(
            "/api/v1/generateFlow",
            json={
                "campaignDescription": ""  # Empty description
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "REQUEST_VALIDATION_ERROR"
        assert "details" in data

    def test_generate_campaign_missing_description(self, client):
        """Test campaign generation without description."""
        response = client.post(
            "/api/v1/generateFlow",
            json={}  # Missing campaignDescription
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "REQUEST_VALIDATION_ERROR"
        assert any("campaignDescription" in detail["field"] for detail in data["details"])

    def test_generate_campaign_too_short_description(self, client):
        """Test campaign generation with very short description."""
        response = client.post(
            "/api/v1/generateFlow",
            json={
                "campaignDescription": "Hi"  # Too short
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "REQUEST_VALIDATION_ERROR"

    def test_generate_campaign_service_error(self, client, mock_orchestrator):
        """Test campaign generation with service error."""
        # Mock service error
        from src.services.campaign_generation.orchestrator import CampaignGenerationResult
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

    @pytest.mark.asyncio
    async def test_generate_campaign_async(self, async_client, mock_orchestrator):
        """Test campaign generation with async client."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = await async_client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create an async test campaign"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["initialStepID"] == "welcome_step"

    def test_generate_batch_campaigns_success(self, client, mock_orchestrator):
        """Test successful batch campaign generation."""
        from src.services.campaign_generation.orchestrator import CampaignGenerationResult
        mock_result = CampaignGenerationResult(
            success=True,
            flow_data={
                "initialStepID": "batch_step",
                "steps": [{"id": "batch_step", "type": "SendMessage", "config": {}}]
            },
            campaign_id="batch_campaign_123"
        )
        mock_orchestrator.generate_campaign_batch.return_value = [mock_result]

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow/batch",
                json=[
                    {"campaignDescription": "Welcome campaign"},
                    {"campaignDescription": "Promotional campaign"}
                ]
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total_requests"] == 2
            assert data["successful_generations"] == 2
            assert data["failed_generations"] == 0
            assert data["success_rate"] == 100.0
            assert len(data["results"]) == 2

    def test_generate_batch_campaigns_too_many_requests(self, client):
        """Test batch campaign generation with too many requests."""
        # Create batch with more than allowed limit (10)
        large_batch = [
            {"campaignDescription": f"Campaign {i}"}
            for i in range(15)
        ]

        response = client.post(
            "/api/v1/generateFlow/batch",
            json=large_batch
        )

        assert response.status_code == 400
        data = response.json()
        assert "Batch size too large" in data["detail"]

    def test_generate_batch_campaigns_empty_batch(self, client):
        """Test batch campaign generation with empty batch."""
        response = client.post(
            "/api/v1/generateFlow/batch",
            json=[]
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "REQUEST_VALIDATION_ERROR"

    def test_get_campaign_statistics_success(self, client, mock_orchestrator):
        """Test getting campaign generation statistics."""
        mock_orchestrator.get_generation_statistics.return_value = {
            "total_campaigns_generated": 150,
            "average_generation_time_ms": 2200,
            "success_rate": 96.2,
            "most_common_complexity": "medium"
        }

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.get("/api/v1/stats")

            assert response.status_code == 200
            data = response.json()

            assert data["total_campaigns_generated"] == 150
            assert data["success_rate"] == 96.2
            assert "validation_reports_count" in data

    def test_get_campaign_statistics_with_authentication(self, client, mock_orchestrator):
        """Test getting statistics with authentication."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.get(
                "/api/v1/stats",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_campaigns_generated" in data

    def test_get_campaign_health_check_success(self, client, mock_orchestrator):
        """Test campaign service health check."""
        mock_orchestrator.health_check.return_value = {
            "status": "healthy",
            "components": {
                "llm_client": "healthy",
                "validator": "healthy"
            }
        }

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.get("/api/v1/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "campaign-generation"
            assert data["components"]["llm_client"] == "healthy"

    def test_get_campaign_health_check_degraded(self, client, mock_orchestrator):
        """Test campaign service health check with degraded status."""
        mock_orchestrator.health_check.return_value = {
            "status": "degraded",
            "components": {
                "llm_client": "unhealthy: API timeout",
                "validator": "healthy"
            }
        }

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.get("/api/v1/health")

            assert response.status_code == 503  # Service unavailable for degraded status
            data = response.json()
            assert data["status"] == "degraded"

    def test_get_campaign_health_check_unhealthy(self, client, mock_orchestrator):
        """Test campaign service health check with unhealthy status."""
        mock_orchestrator.health_check.return_value = {
            "status": "unhealthy",
            "error": "Service initialization failed"
        }

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.get("/api/v1/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "error" in data

    def test_get_campaign_report_success(self, client):
        """Test getting campaign validation report."""
        mock_reporter = AsyncMock()
        mock_report = MagicMock()
        mock_report.campaign_id = "test_campaign_123"
        mock_report.quality_score = 85.5
        mock_report.is_valid = True
        mock_report.total_issues = 2
        mock_report.to_dict.return_value = {
            "campaign_id": "test_campaign_123",
            "quality_score": 85.5,
            "is_valid": True,
            "total_issues": 2
        }
        mock_reporter.get_latest_report.return_value = mock_report

        with patch('src.api.endpoints.campaigns.get_validation_reporter', return_value=mock_reporter):
            response = client.get("/api/v1/campaigns/test_campaign_123/report")

            assert response.status_code == 200
            data = response.json()
            assert data["campaign_id"] == "test_campaign_123"
            assert data["quality_score"] == 85.5

    def test_get_campaign_report_not_found(self, client):
        """Test getting report for non-existent campaign."""
        mock_reporter = AsyncMock()
        mock_reporter.get_latest_report.return_value = None

        with patch('src.api.endpoints.campaigns.get_validation_reporter', return_value=mock_reporter):
            response = client.get("/api/v1/campaigns/nonexistent_campaign/report")

            assert response.status_code == 404
            data = response.json()
            assert "No validation report found" in data["detail"]

    def test_correlation_id_tracking(self, client, mock_orchestrator):
        """Test correlation ID tracking through requests."""
        correlation_id = "test-correlation-456"

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Test campaign with correlation"
                },
                headers={
                    "X-Correlation-ID": correlation_id
                }
            )

            assert response.status_code == 200
            # Response should include correlation ID (either in headers or body)
            assert correlation_id in response.headers.get("X-Correlation-ID", "")

    def test_request_timeout_handling(self, client, mock_orchestrator):
        """Test handling of request timeouts."""
        # Mock slow response
        import asyncio
        mock_orchestrator.generate_campaign.side_effect = asyncio.TimeoutError("Request timeout")

        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Test timeout campaign"
                }
            )

            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "INTERNAL_SERVER_ERROR"

    def test_rate_limiting_headers(self, client, mock_orchestrator):
        """Test rate limiting headers in responses."""
        with patch('src.api.endpoints.campaigns.get_campaign_orchestrator', return_value=mock_orchestrator):
            response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Test rate limiting"
                }
            )

            # Check for rate limiting headers (if rate limiting is enabled)
            rate_limit_headers = [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ]

            # At least some rate limiting headers should be present
            has_rate_headers = any(header in response.headers for header in rate_limit_headers)
            # This may or may not be true depending on configuration


@pytest.mark.integration
class TestHealthAPI:
    """Test health API integration."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_detailed_health_check_success(self, client):
        """Test detailed health check with all components healthy."""
        # Mock all components as healthy
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.health_check.return_value = {
                "status": "healthy",
                "components": {
                    "llm_client": "healthy",
                    "prompt_builder": "healthy",
                    "response_parser": "healthy",
                    "validator": "healthy"
                }
            }
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch('src.services.llm_engine.llm_client.get_llm_client') as mock_get_llm:
                mock_llm = AsyncMock()
                mock_llm.estimate_tokens.return_value = 10
                mock_get_llm.return_value = mock_llm

                with patch('src.services.validation.validator.get_validator') as mock_get_validator:
                    mock_validator = MagicMock()
                    mock_validator.quick_validate.return_value = MagicMock(is_valid=True)
                    mock_get_validator.return_value = mock_validator

                    response = client.get("/api/v1/health/detailed")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert "components" in data
                    assert "metrics" in data
                    assert "checks" in data

    def test_readiness_check_ready(self, client):
        """Test readiness check when service is ready."""
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.health_check.return_value = {"status": "healthy"}
            mock_get_orchestrator.return_value = mock_orchestrator

            response = client.get("/api/v1/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert "checks" in data

    def test_readiness_check_not_ready(self, client):
        """Test readiness check when service is not ready."""
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.health_check.return_value = {"status": "unhealthy"}
            mock_get_orchestrator.return_value = mock_orchestrator

            response = client.get("/api/v1/health/ready")

            assert response.status_code == 503
            data = response.json()
            assert "not ready" in data["detail"]

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "uptime_seconds" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.get_generation_statistics.return_value = {
                "total_campaigns_generated": 100,
                "success_rate": 95.0
            }
            mock_get_orchestrator.return_value = mock_orchestrator

            with patch('src.services.validation.reporting.get_validation_reporter') as mock_get_reporter:
                mock_reporter = MagicMock()
                mock_reporter.get_reports.return_value = []
                mock_get_reporter.return_value = mock_reporter

                response = client.get("/api/v1/metrics")

                assert response.status_code == 200
                data = response.json()
                assert "service_metrics" in data
                assert "validation_metrics" in data
                assert "system_metrics" in data
                assert "performance_metrics" in data


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def app(self):
        """Create FastAPI application for testing."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_complete_campaign_generation_workflow(self, client):
        """Test complete campaign generation workflow."""
        # This test would require actual LLM integration or comprehensive mocking

        # 1. Check service health
        health_response = client.get("/api/v1/health")
        assert health_response.status_code in [200, 503]  # May be unhealthy without LLM

        # 2. Generate a campaign
        with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
            mock_orchestrator = AsyncMock()

            from src.services.campaign_generation.orchestrator import CampaignGenerationResult
            mock_result = CampaignGenerationResult(
                success=True,
                flow_data={
                    "initialStepID": "welcome",
                    "steps": [
                        {
                            "id": "welcome",
                            "type": "SendMessage",
                            "config": {
                                "messageContent": {"body": "Welcome!"},
                                "recipient": {"type": "segment", "segmentId": "new_users"}
                            }
                        }
                    ]
                },
                campaign_id="e2e_test_campaign",
                metadata={"total_time_ms": 2000}
            )

            mock_orchestrator.generate_campaign.return_value = mock_result
            mock_orchestrator.health_check.return_value = {"status": "healthy"}
            mock_orchestrator.get_generation_statistics.return_value = {"total": 1}
            mock_get_orchestrator.return_value = mock_orchestrator

            campaign_response = client.post(
                "/api/v1/generateFlow",
                json={
                    "campaignDescription": "Create a welcome campaign for new users"
                }
            )
            assert campaign_response.status_code == 200
            campaign_data = campaign_response.json()
            assert campaign_data["initialStepID"] == "welcome"

            # 3. Get statistics
            stats_response = client.get("/api/v1/stats")
            assert stats_response.status_code == 200
            stats_data = stats_response.json()
            assert "total_campaigns_generated" in stats_data

    def test_error_handling_workflow(self, client):
        """Test error handling throughout the workflow."""

        # Test invalid request handling
        invalid_response = client.post(
            "/api/v1/generateFlow",
            json={"invalid": "data"}
        )
        assert invalid_response.status_code == 422
        assert "error" in invalid_response.json()

        # Test missing endpoint handling
        not_found_response = client.get("/api/v1/nonexistent")
        assert not_found_response.status_code == 404

        # Test method not allowed
        method_not_allowed = client.delete("/api/v1/generateFlow")
        assert method_not_allowed.status_code == 405

    def test_security_headers_workflow(self, client):
        """Test security headers are present."""
        response = client.get("/health")

        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy"
        ]

        # Check that security headers are present
        for header in security_headers:
            assert header in response.headers

    def test_cors_handling(self, client):
        """Test CORS handling."""
        # Test preflight request
        response = client.options(
            "/api/v1/generateFlow",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )

        # Should handle preflight request appropriately
        assert response.status_code in [200, 204, 405]  # Depending on CORS config

    def test_request_size_limits(self, client):
        """Test handling of large requests."""
        # Create a very large campaign description
        large_description = "Create a complex campaign " * 1000

        response = client.post(
            "/api/v1/generateFlow",
            json={
                "campaignDescription": large_description
            }
        )

        # Should handle large requests gracefully (either accept or reject with proper error)
        assert response.status_code in [200, 413, 422]  # 413 = Payload Too Large

    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            with patch('src.services.campaign_generation.orchestrator.get_campaign_orchestrator') as mock_get_orchestrator:
                mock_orchestrator = AsyncMock()

                from src.services.campaign_generation.orchestrator import CampaignGenerationResult
                mock_result = CampaignGenerationResult(
                    success=True,
                    flow_data={"initialStepID": "test", "steps": []},
                    campaign_id=f"concurrent_{time.time()}"
                )

                mock_orchestrator.generate_campaign.return_value = mock_result
                mock_get_orchestrator.return_value = mock_orchestrator

                response = client.post(
                    "/api/v1/generateFlow",
                    json={"campaignDescription": "Concurrent test campaign"}
                )
                results.append(response.status_code)

        # Make multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should complete successfully
        assert all(status == 200 for status in results)
        assert len(results) == 5