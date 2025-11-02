"""
Unit tests for LLM engine components.

Tests cover LLM client, prompt builder, and response parser
to ensure proper integration with OpenAI API and response handling.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.services.llm_engine.llm_client import LLMClient, get_llm_client
from src.services.llm_engine.prompt_builder import PromptBuilder, get_prompt_builder
from src.services.llm_engine.response_parser import ResponseParser, get_response_parser


class TestLLMClient:
    """Test LLM client functionality."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        return mock_client

    @pytest.fixture
    def llm_client(self, mock_openai_client):
        """Create LLM client with mocked OpenAI client."""
        with patch('openai.AsyncOpenAI', return_value=mock_openai_client):
            return LLMClient(api_key="test-key", model="gpt-4-test")

    @pytest.mark.asyncio
    async def test_generate_json_success(self, llm_client, mock_openai_client):
        """Test successful JSON generation."""
        # Mock successful OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"initialStepID": "test", "steps": []}'))
        ]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await llm_client.generate_json(
            prompt="Generate a campaign flow",
            system_prompt="You are a campaign generator",
            max_tokens=1000,
            temperature=0.7
        )

        assert result == '{"initialStepID": "test", "steps": []}'
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_json_with_invalid_response(self, llm_client, mock_openai_client):
        """Test handling of invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"invalid": json content}'))
        ]
        mock_openai_client.chat.completions.create.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await llm_client.generate_json("Generate campaign")
        assert "Failed to generate valid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_json_with_api_error(self, llm_client, mock_openai_client):
        """Test handling of OpenAI API errors."""
        # Mock API error
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            await llm_client.generate_json("Generate campaign")
        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_json_with_empty_response(self, llm_client, mock_openai_client):
        """Test handling of empty response."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.choices = []
        mock_openai_client.chat.completions.create.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            await llm_client.generate_json("Generate campaign")
        assert "No response from LLM" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_estimate_tokens(self, llm_client, mock_openai_client):
        """Test token estimation."""
        # Mock tokenizer
        with patch('tiktoken.encoding_for_model') as mock_encoding:
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = list(range(50))  # 50 tokens
            mock_encoding.return_value = mock_encoder

            result = await llm_client.estimate_tokens("Test message")

            assert result == 50
            mock_encoder.encode.assert_called_once_with("Test message")

    @pytest.mark.asyncio
    async def test_health_check(self, llm_client):
        """Test health check functionality."""
        with patch.object(llm_client, 'estimate_tokens', return_value=10) as mock_estimate:
            result = await llm_client.health_check()

            assert result["status"] == "healthy"
            assert "timestamp" in result
            mock_estimate.assert_called_once_with("health check")

    def test_llm_client_initialization(self):
        """Test LLM client initialization."""
        client = LLMClient(
            api_key="test-key",
            model="gpt-4",
            max_tokens=2000,
            temperature=0.5,
            timeout=60
        )

        assert client.api_key == "test-key"
        assert client.model == "gpt-4"
        assert client.max_tokens == 2000
        assert client.temperature == 0.5
        assert client.timeout == 60

    def test_llm_client_global_instance(self):
        """Test global LLM client instance."""
        # Reset global instance
        import src.services.llm_engine.llm_client
        src.services.llm_engine.llm_client._llm_client = None

        client1 = get_llm_client()
        client2 = get_llm_client()

        assert client1 is client2  # Should be the same instance

    @pytest.mark.asyncio
    async def test_generate_json_with_retry(self, llm_client, mock_openai_client):
        """Test JSON generation with retry logic."""
        # Mock first call fails, second succeeds
        mock_error_response = MagicMock()
        mock_error_response.choices = [
            MagicMock(message=MagicMock(content='{"invalid": json}'))
        ]

        mock_success_response = MagicMock()
        mock_success_response.choices = [
            MagicMock(message=MagicMock(content='{"initialStepID": "test", "steps": []}'))
        ]

        mock_openai_client.chat.completions.create.side_effect = [
            mock_error_response,
            mock_success_response
        ]

        # This should succeed on retry
        result = await llm_client.generate_json("Generate campaign")

        assert result == '{"initialStepID": "test", "steps": []}'
        assert mock_openai_client.chat.completions.create.call_count == 2


class TestPromptBuilder:
    """Test prompt builder functionality."""

    @pytest.fixture
    def prompt_builder(self):
        """Create prompt builder instance."""
        return PromptBuilder()

    def test_build_prompt_simple(self, prompt_builder):
        """Test building a simple prompt."""
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description="Send a welcome message to new users",
            complexity_level="simple",
            include_examples=False,
            max_examples=0
        )

        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        assert "welcome message" in user_prompt.lower()
        assert len(system_prompt) > 0
        assert len(user_prompt) > 0

    def test_build_prompt_with_examples(self, prompt_builder):
        """Test building prompt with examples."""
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description="Create a welcome series",
            complexity_level="medium",
            include_examples=True,
            max_examples=2
        )

        assert "examples" in user_prompt.lower() or "example" in user_prompt.lower()
        assert "initialStepID" in user_prompt
        assert "steps" in user_prompt

    def test_build_prompt_complex(self, prompt_builder):
        """Test building complex prompt."""
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description="Create a complex multi-path campaign with personalization",
            complexity_level="complex",
            include_examples=True,
            max_examples=3
        )

        assert len(system_prompt) > 1000  # Should be longer for complex
        assert "personalization" in user_prompt.lower()
        assert "condition" in user_prompt.lower() or "branch" in user_prompt.lower()

    def test_build_prompt_with_invalid_complexity(self, prompt_builder):
        """Test building prompt with invalid complexity level."""
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description="Test campaign",
            complexity_level="invalid",
            include_examples=False,
            max_examples=0
        )

        # Should default to medium complexity
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)

    def test_build_prompt_with_max_examples_limit(self, prompt_builder):
        """Test building prompt with too many examples requested."""
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description="Test campaign",
            complexity_level="simple",
            include_examples=True,
            max_examples=10  # More than allowed
        )

        # Should limit to maximum allowed examples
        example_count = user_prompt.count("example")
        assert example_count <= 5  # Assuming max 5 examples

    def test_build_prompt_empty_description(self, prompt_builder):
        """Test building prompt with empty description."""
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description="",
            complexity_level="simple",
            include_examples=False,
            max_examples=0
        )

        assert len(user_prompt) > 0  # Should still generate a prompt
        assert "campaign" in user_prompt.lower()

    def test_build_prompt_very_long_description(self, prompt_builder):
        """Test building prompt with very long description."""
        long_description = "Create a campaign " + "with many features " * 100
        system_prompt, user_prompt = prompt_builder.build_prompt(
            campaign_description=long_description,
            complexity_level="simple",
            include_examples=False,
            max_examples=0
        )

        # Should truncate or handle long description
        assert len(user_prompt) < 10000  # Reasonable limit
        assert "campaign" in user_prompt.lower()

    def test_prompt_builder_global_instance(self):
        """Test global prompt builder instance."""
        import src.services.llm_engine.prompt_builder
        src.services.llm_engine.prompt_builder._prompt_builder = None

        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()

        assert builder1 is builder2

    def test_system_prompt_contains_instructions(self, prompt_builder):
        """Test that system prompt contains proper instructions."""
        system_prompt, _ = prompt_builder.build_prompt(
            campaign_description="Test campaign",
            complexity_level="simple",
            include_examples=False,
            max_examples=0
        )

        assert "JSON" in system_prompt
        assert "flow" in system_prompt.lower()
        assert "steps" in system_prompt.lower()

    def test_user_prompt_structure(self, prompt_builder):
        """Test that user prompt has proper structure."""
        _, user_prompt = prompt_builder.build_prompt(
            campaign_description="Send promotional messages",
            complexity_level="medium",
            include_examples=True,
            max_examples=1
        )

        # Should contain campaign description
        assert "promotional messages" in user_prompt.lower()

        # Should contain expected output format
        assert "initialStepID" in user_prompt
        assert "steps" in user_prompt

    def test_complexity_affects_prompt_length(self, prompt_builder):
        """Test that complexity level affects prompt length."""
        simple_system, simple_user = prompt_builder.build_prompt(
            campaign_description="Test campaign",
            complexity_level="simple",
            include_examples=False,
            max_examples=0
        )

        complex_system, complex_user = prompt_builder.build_prompt(
            campaign_description="Test campaign",
            complexity_level="complex",
            include_examples=False,
            max_examples=0
        )

        # Complex prompt should be longer
        assert len(complex_system) > len(simple_system)


class TestResponseParser:
    """Test response parser functionality."""

    @pytest.fixture
    def response_parser(self):
        """Create response parser instance."""
        return ResponseParser()

    def test_parse_valid_json_response(self, response_parser):
        """Test parsing valid JSON response."""
        json_response = '{"initialStepID": "test", "steps": [{"id": "step1", "type": "SendMessage"}]}'
        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        assert campaign_flow.initialStepID == "test"
        assert len(campaign_flow.steps) == 1
        assert campaign_flow.steps[0].id == "step1"
        assert campaign_flow.steps[0].type == "SendMessage"

    def test_parse_response_with_json_in_code_blocks(self, response_parser):
        """Test parsing JSON response wrapped in code blocks."""
        json_response = '''```json
        {
            "initialStepID": "test",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {
                        "messageContent": {"body": "Hello"},
                        "recipient": {"type": "all"}
                    }
                }
            ]
        }
        ```'''

        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        assert campaign_flow.initialStepID == "test"
        assert len(campaign_flow.steps) == 1
        assert campaign_flow.steps[0].config["messageContent"]["body"] == "Hello"

    def test_parse_response_with_markdown_formatting(self, response_parser):
        """Test parsing JSON response with markdown formatting."""
        json_response = '''Here's the campaign flow you requested:

```json
{
    "initialStepID": "welcome",
    "steps": [
        {
            "id": "welcome",
            "type": "SendMessage",
            "config": {
                "messageContent": {"body": "Welcome!"},
                "recipient": {"type": "all"}
            }
        }
    ]
}
```

This flow will send a welcome message to all users.'''

        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        assert campaign_flow.initialStepID == "welcome"
        assert len(campaign_flow.steps) == 1

    def test_parse_response_with_missing_fields(self, response_parser):
        """Test parsing response with missing required fields."""
        json_response = '{"steps": [{"id": "step1", "type": "SendMessage"}]}'  # Missing initialStepID

        with pytest.raises(ValueError) as exc_info:
            response_parser.parse_response(
                json_response,
                strict_mode=True,
                attempt_repair=False
            )
        assert "validation error" in str(exc_info.value).lower()

    def test_parse_response_with_invalid_step_type(self, response_parser):
        """Test parsing response with invalid step type."""
        json_response = '''{
            "initialStepID": "test",
            "steps": [
                {
                    "id": "step1",
                    "type": "InvalidStepType",
                    "config": {}
                }
            ]
        }'''

        with pytest.raises(ValueError) as exc_info:
            response_parser.parse_response(
                json_response,
                strict_mode=True,
                attempt_repair=False
            )
        assert "validation error" in str(exc_info.value).lower()

    def test_parse_response_with_repair_enabled(self, response_parser):
        """Test parsing response with auto-repair enabled."""
        # Response with minor issues that can be repaired
        json_response = '''{
            "initialStepID": "test",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {
                        "messageContent": {"body": "Hello"},
                        "recipient": {"type": "all"}
                    }
                    // Missing closing brace
                }
            ]
        }'''

        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=True
        )

        # Should attempt repair and either succeed or fail gracefully
        assert metadata["repair_attempted"] is True
        if campaign_flow:
            assert isinstance(campaign_flow.initialStepID, str)

    def test_parse_response_completely_invalid_json(self, response_parser):
        """Test parsing completely invalid JSON."""
        json_response = 'This is not JSON at all'

        with pytest.raises(ValueError) as exc_info:
            response_parser.parse_response(
                json_response,
                strict_mode=False,
                attempt_repair=False
            )
        assert "Failed to extract valid JSON" in str(exc_info.value)

    def test_parse_response_empty_string(self, response_parser):
        """Test parsing empty response."""
        json_response = ""

        with pytest.raises(ValueError) as exc_info:
            response_parser.parse_response(
                json_response,
                strict_mode=False,
                attempt_repair=False
            )
        assert "No response content" in str(exc_info.value)

    def test_parse_response_with_extra_fields(self, response_parser):
        """Test parsing response with extra unknown fields."""
        json_response = '''{
            "initialStepID": "test",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {
                        "messageContent": {"body": "Hello"},
                        "recipient": {"type": "all"}
                    },
                    "unknownField": "should be ignored"
                }
            ],
            "unknownMetadata": "should be ignored"
        }'''

        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        # Should parse successfully, ignoring unknown fields
        assert campaign_flow.initialStepID == "test"
        assert len(campaign_flow.steps) == 1
        assert not hasattr(campaign_flow.steps[0].config, "unknownField")

    def test_parse_response_metadata(self, response_parser):
        """Test that parsing returns proper metadata."""
        json_response = '{"initialStepID": "test", "steps": []}'
        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        assert isinstance(metadata, dict)
        assert "flow_complexity" in metadata
        assert "node_count" in metadata
        assert "estimated_tokens" in metadata
        assert metadata["node_count"] == 0

    def test_response_parser_global_instance(self):
        """Test global response parser instance."""
        import src.services.llm_engine.response_parser
        src.services.llm_engine.response_parser._response_parser = None

        parser1 = get_response_parser()
        parser2 = get_response_parser()

        assert parser1 is parser2

    def test_parse_large_response(self, response_parser):
        """Test parsing large JSON response."""
        # Generate a large campaign flow
        steps = []
        for i in range(100):  # 100 steps
            steps.append({
                "id": f"step_{i}",
                "type": "SendMessage",
                "config": {
                    "messageContent": {"body": f"Message {i}"},
                    "recipient": {"type": "all"}
                },
                "nextStepId": f"step_{i+1}" if i < 99 else None
            })

        json_response = json.dumps({
            "initialStepID": "step_0",
            "steps": steps
        })

        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        assert len(campaign_flow.steps) == 100
        assert metadata["node_count"] == 100
        assert metadata["flow_complexity"] == "high"

    def test_parse_response_with_special_characters(self, response_parser):
        """Test parsing response with special characters."""
        json_response = '''{
            "initialStepID": "test",
            "steps": [
                {
                    "id": "step1",
                    "type": "SendMessage",
                    "config": {
                        "messageContent": {
                            "body": "Hello 🌟! Special chars: àáâãäåæçèéêë",
                            "subject": "Test ñòóôõö"
                        },
                        "recipient": {"type": "all"}
                    }
                }
            ]
        }'''

        campaign_flow, metadata = response_parser.parse_response(
            json_response,
            strict_mode=False,
            attempt_repair=False
        )

        assert "🌟" in campaign_flow.steps[0].config["messageContent"]["body"]
        assert "ñòó" in campaign_flow.steps[0].config["messageContent"]["subject"]