# OpenRouter Integration Guide

## Overview

The SMS Campaign Generation System now supports OpenRouter as an additional LLM provider alongside OpenAI. OpenRouter provides access to multiple AI models through a single API, including models from Anthropic, Google, OpenAI, and others.

## Supported Models

OpenRouter supports a wide variety of models. Here are some popular options:

### Claude Models
- `anthropic/claude-3.5-sonnet` - Latest Claude model (recommended)
- `anthropic/claude-3-opus` - High-performance Claude model
- `anthropic/claude-3-sonnet` - Balanced Claude model
- `anthropic/claude-3-haiku` - Fast, cost-effective Claude model

### GPT Models
- `openai/gpt-4-turbo` - Latest GPT-4 model
- `openai/gpt-4` - Standard GPT-4
- `openai/gpt-3.5-turbo` - Fast, cost-effective GPT model

### Google Models
- `google/gemini-pro` - Google's latest model
- `google/gemini-pro-vision` - Multimodal model

### Other Popular Models
- `meta-llama/llama-3-70b-instruct` - Meta's Llama 3
- `mistralai/mixtral-8x7b-instruct` - Mistral's MoE model

For a complete list, visit: https://openrouter.ai/models

## Configuration

### 1. Get OpenRouter API Key

1. Sign up at [OpenRouter.ai](https://openrouter.ai)
2. Navigate to the API Keys section
3. Create a new API key
4. Copy the key (starts with `sk-or-...`)

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Set LLM provider to OpenRouter
LLM_PROVIDER=openrouter

# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-your-api-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_MAX_TOKENS=4000
OPENROUTER_TEMPERATURE=0.7
OPENROUTER_TIMEOUT=60
```

### 3. Optional Configuration

You can also override these settings in your code:

```python
from src.services.llm_engine.llm_client import LLMClient, LLMProvider

# Use OpenRouter with specific model
client = LLMClient(
    provider=LLMProvider.OPENROUTER,
    model="anthropic/claude-3.5-sonnet",
    api_key="your-api-key"
)
```

## Usage Examples

### Basic Text Generation

```python
from src.services.llm_engine.llm_client import LLMClient, LLMProvider

client = LLMClient(provider=LLMProvider.OPENROUTER)

response = await client.generate_text(
    prompt="Generate a welcome SMS message for new subscribers.",
    system_prompt="You are a helpful SMS marketing assistant.",
    max_tokens=100,
    temperature=0.7
)

print(response)
await client.close()
```

### JSON Generation

```python
response = await client.generate_json(
    prompt="Create a 2-step SMS campaign flow.",
    system_prompt="Generate valid JSON for SMS campaigns.",
    max_tokens=200
)

print(response)  # Returns a Python dictionary
```

### Switching Providers

```python
# OpenRouter
openrouter_client = LLMClient(provider=LLMProvider.OPENROUTER)

# OpenAI (backward compatibility)
openai_client = LLMClient(provider=LLMProvider.OPENAI)

# Use settings-based provider
default_client = LLMClient()  # Uses LLM_PROVIDER from settings
```

## Migration from OpenAI

### Automatic Migration

If you're already using the LLM client, migration is simple:

1. Change `LLM_PROVIDER` environment variable from `openai` to `openrouter`
2. Add `OPENROUTER_API_KEY` to your environment
3. Optionally update `OPENROUTER_MODEL` to your preferred model

### Code Changes

Most existing code will work without changes. The interface is the same for both providers:

```python
# This works with both OpenAI and OpenRouter
response = await client.generate_text(
    prompt="Your prompt here",
    max_tokens=100
)
```

## Feature Comparison

| Feature | OpenAI | OpenRouter |
|---------|--------|------------|
| Multiple Models | ✅ (OpenAI only) | ✅ (30+ models) |
| Unified API | ✅ | ✅ |
| Rate Limiting | ✅ | ✅ |
| Error Handling | ✅ | ✅ |
| JSON Mode | ✅ | ✅ |
| Streaming | ✅ | ✅ |
| Cost Tracking | ❌ | ✅ |
| Model Fallback | ❌ | ✅ |

## Best Practices

### 1. Model Selection

Choose models based on your needs:

- **For quality**: `anthropic/claude-3.5-sonnet` or `openai/gpt-4-turbo`
- **For speed**: `anthropic/claude-3-haiku` or `openai/gpt-3.5-turbo`
- **For cost**: `google/gemini-pro` or `meta-llama/llama-3-70b-instruct`

### 2. Error Handling

```python
from src.services.llm_engine.llm_client import LLMClientError, RateLimitError

try:
    response = await client.generate_text(prompt)
except RateLimitError as e:
    # Handle rate limiting
    print(f"Rate limit exceeded: {e}")
except LLMClientError as e:
    # Handle other errors
    print(f"LLM error: {e}")
```

### 3. Token Management

Monitor token usage to control costs:

```python
# The client logs token usage automatically
# You can also estimate tokens beforehand
tokens = await client.estimate_tokens("Your text here")
print(f"Estimated tokens: {tokens}")
```

### 4. Timeout Configuration

Set appropriate timeouts for your use case:

```python
client = LLMClient(
    provider=LLMProvider.OPENROUTER,
    timeout=30  # 30 seconds
)
```

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Verify your OpenRouter API key is correct
   - Check that the key has sufficient credits

2. **Model Not Found**
   - Verify the model name is correct
   - Check if the model is available on OpenRouter

3. **Rate Limiting**
   - Implement exponential backoff
   - Consider upgrading your OpenRouter plan

4. **Timeout Errors**
   - Increase the timeout setting
   - Check your network connection

### Testing

Use the provided test script to verify your configuration:

```bash
# Set your API key
export OPENROUTER_API_KEY=sk-or-your-key-here

# Run tests
python test_openrouter_integration.py
```

## Cost Management

OpenRouter provides detailed cost tracking:

1. Monitor usage in your OpenRouter dashboard
2. Set spending limits in your account settings
3. Use cost-effective models for bulk operations
4. Implement caching to reduce API calls

## Rate Limits

OpenRouter has different rate limits depending on your plan:

- **Free tier**: 20 requests/minute
- **Standard tier**: 100 requests/minute
- **Pro tier**: 500 requests/minute

Implement retry logic for rate limit handling:

```python
# The client automatically handles rate limits with exponential backoff
# You can configure the retry behavior
client.max_retries = 5
client.base_delay = 2.0  # Base delay in seconds
```

## Support

- **OpenRouter Documentation**: https://openrouter.ai/docs
- **Model List**: https://openrouter.ai/models
- **API Reference**: https://openrouter.ai/docs/api-reference
- **Status Page**: https://status.openrouter.ai

## Example Configuration Files

### Development Environment (.env)

```bash
# Development settings
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Use OpenRouter in development
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-dev-key-here
OPENROUTER_MODEL=anthropic/claude-3-haiku  # Cost-effective for testing
```

### Production Environment (.env)

```bash
# Production settings
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# Use OpenRouter in production
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-prod-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet  # High quality
OPENROUTER_TIMEOUT=120  # Longer timeout for production
```

## Migration Checklist

- [ ] Sign up for OpenRouter account
- [ ] Generate API key
- [ ] Update environment variables
- [ ] Test with provided test script
- [ ] Update model selection if needed
- [ ] Monitor initial usage and costs
- [ ] Set up alerts for rate limits
- [ ] Document any model-specific considerations

## Conclusion

OpenRouter integration provides flexibility in model choice and potential cost savings while maintaining the same interface as the existing OpenAI integration. The system is designed to be provider-agnostic, allowing you to switch between providers based on your specific needs.