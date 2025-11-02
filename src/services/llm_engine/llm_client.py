"""
LLM client for campaign generation.

This module provides integration with multiple LLM providers including OpenAI and OpenRouter
for generating SMS campaign flows.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import httpx
import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from src.core.config import get_settings
from src.core.logging import get_logger
from src.utils.constants import LOG_CONTEXT_MODEL_USED, LOG_CONTEXT_TOKENS_USED


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"

logger = get_logger(__name__)
settings = get_settings()


class LLMClientError(Exception):
    """Custom exception for LLM client errors."""
    pass


class RateLimitError(LLMClientError):
    """Exception raised when rate limit is exceeded."""
    pass


class TokenLimitError(LLMClientError):
    """Exception raised when token limit is exceeded."""
    pass


class LLMClient:
    """
    LLM client for campaign generation with retry logic and error handling.
    Supports multiple LLM providers including OpenAI and OpenRouter.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[Union[str, LLMProvider]] = None
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key (if None, uses settings based on provider)
            model: Model to use (if None, uses settings)
            provider: LLM provider to use (if None, uses settings)
        """
        # Determine provider
        self.provider = LLMProvider(provider or settings.LLM_PROVIDER)

        # Set configuration based on provider
        if self.provider == LLMProvider.OPENAI:
            self.api_key = api_key or settings.OPENAI_API_KEY
            self.model = model or settings.OPENAI_MODEL
            self.max_tokens = settings.OPENAI_MAX_TOKENS
            self.temperature = settings.OPENAI_TEMPERATURE
            self.timeout = settings.OPENAI_TIMEOUT
            self.base_url = "https://api.openai.com/v1"
        elif self.provider == LLMProvider.OPENROUTER:
            self.api_key = api_key or settings.OPENROUTER_API_KEY
            self.model = model or settings.OPENROUTER_MODEL
            self.max_tokens = settings.OPENROUTER_MAX_TOKENS
            self.temperature = settings.OPENROUTER_TEMPERATURE
            self.timeout = settings.OPENROUTER_TIMEOUT
            self.base_url = "https://openrouter.ai/api/v1"
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Initialize clients
        if self.provider == LLMProvider.OPENAI:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
            )
            self.http_client = None
        else:  # OpenRouter
            self.client = None
            self.http_client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": settings.APP_URL if hasattr(settings, 'APP_URL') else "http://localhost:8000",
                    "X-Title": "SMS Campaign Generation System"
                }
            )

        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds

        logger.info(
            "LLM client initialized",
            extra={
                "provider": self.provider,
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "timeout": self.timeout,
            }
        )

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Union[ChatCompletion, Dict[str, Any]]:
        """
        Generate chat completion with retry logic.

        Args:
            messages: List of chat messages
            max_tokens: Maximum tokens to generate (overrides default)
            temperature: Sampling temperature (overrides default)
            stop_sequences: Stop sequences for generation
            **kwargs: Additional parameters for LLM API

        Returns:
            ChatCompletion object for OpenAI or Dict for OpenRouter

        Raises:
            LLMClientError: If generation fails after retries
            RateLimitError: If rate limit is exceeded
            TokenLimitError: If token limit is exceeded
        """
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            **kwargs,
        }

        if stop_sequences:
            params["stop"] = stop_sequences

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()

                logger.debug(
                    f"LLM request attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries + 1,
                        "message_count": len(messages),
                        "provider": self.provider,
                    }
                )

                if self.provider == LLMProvider.OPENAI:
                    response = await self.client.chat.completions.create(**params)

                    generation_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                    logger.info(
                        "LLM request completed successfully",
                        extra={
                            "attempt": attempt + 1,
                            "generation_time_ms": round(generation_time, 2),
                            LOG_CONTEXT_TOKENS_USED: response.usage.total_tokens if response.usage else 0,
                            LOG_CONTEXT_MODEL_USED: response.model,
                            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                            "provider": self.provider,
                        }
                    )

                    return response

                else:  # OpenRouter
                    # Add JSON response format for OpenRouter if needed
                    if "response_format" in kwargs:
                        params["response_format"] = kwargs["response_format"]

                    response = await self.http_client.post(
                        f"{self.base_url}/chat/completions",
                        json=params
                    )
                    response.raise_for_status()

                    response_data = response.json()

                    generation_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                    logger.info(
                        "LLM request completed successfully",
                        extra={
                            "attempt": attempt + 1,
                            "generation_time_ms": round(generation_time, 2),
                            LOG_CONTEXT_TOKENS_USED: response_data.get("usage", {}).get("total_tokens", 0),
                            LOG_CONTEXT_MODEL_USED: response_data.get("model", self.model),
                            "prompt_tokens": response_data.get("usage", {}).get("prompt_tokens", 0),
                            "completion_tokens": response_data.get("usage", {}).get("completion_tokens", 0),
                            "provider": self.provider,
                        }
                    )

                    return response_data

            except openai.RateLimitError as e:
                last_exception = RateLimitError(f"Rate limit exceeded: {e}")
                logger.warning(
                    f"Rate limit hit on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "provider": self.provider,
                    }
                )

                # Don't retry rate limit errors, just propagate
                raise last_exception

            except openai.AuthenticationError as e:
                last_exception = LLMClientError(f"Authentication failed: {e}")
                logger.error(
                    f"Authentication error on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "provider": self.provider,
                    }
                )
                # Don't retry authentication errors
                raise last_exception

            except openai.BadRequestError as e:
                if "maximum context length" in str(e).lower():
                    last_exception = TokenLimitError(f"Token limit exceeded: {e}")
                    logger.error(
                        f"Token limit exceeded on attempt {attempt + 1}",
                        extra={
                            "attempt": attempt + 1,
                            "error": str(e),
                            "provider": self.provider,
                        }
                    )
                    # Don't retry token limit errors
                    raise last_exception

                last_exception = LLMClientError(f"Bad request: {e}")
                logger.warning(
                    f"Bad request on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "provider": self.provider,
                    }
                )

            except openai.APIError as e:
                last_exception = LLMClientError(f"API error: {e}")
                logger.warning(
                    f"API error on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "provider": self.provider,
                    }
                )

            except httpx.HTTPStatusError as e:
                error_response = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {"error": {"message": str(e)}}
                error_message = error_response.get("error", {}).get("message", str(e))
                status_code = e.response.status_code

                if status_code == 429:
                    last_exception = RateLimitError(f"Rate limit exceeded: {error_message}")
                    logger.warning(
                        f"Rate limit hit on attempt {attempt + 1}",
                        extra={
                            "attempt": attempt + 1,
                            "error": error_message,
                            "provider": self.provider,
                            "status_code": status_code,
                        }
                    )
                    raise last_exception

                elif status_code == 401:
                    last_exception = LLMClientError(f"Authentication failed: {error_message}")
                    logger.error(
                        f"Authentication error on attempt {attempt + 1}",
                        extra={
                            "attempt": attempt + 1,
                            "error": error_message,
                            "provider": self.provider,
                            "status_code": status_code,
                        }
                    )
                    raise last_exception

                elif status_code == 400:
                    if "maximum context length" in error_message.lower():
                        last_exception = TokenLimitError(f"Token limit exceeded: {error_message}")
                        logger.error(
                            f"Token limit exceeded on attempt {attempt + 1}",
                            extra={
                                "attempt": attempt + 1,
                                "error": error_message,
                                "provider": self.provider,
                                "status_code": status_code,
                            }
                        )
                        raise last_exception

                    last_exception = LLMClientError(f"Bad request: {error_message}")
                    logger.warning(
                        f"Bad request on attempt {attempt + 1}",
                        extra={
                            "attempt": attempt + 1,
                            "error": error_message,
                            "provider": self.provider,
                            "status_code": status_code,
                        }
                    )

                else:
                    last_exception = LLMClientError(f"API error: {error_message}")
                    logger.warning(
                        f"API error on attempt {attempt + 1}",
                        extra={
                            "attempt": attempt + 1,
                            "error": error_message,
                            "provider": self.provider,
                            "status_code": status_code,
                        }
                    )

            except asyncio.TimeoutError as e:
                last_exception = LLMClientError(f"Request timeout: {e}")
                logger.warning(
                    f"Request timeout on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "timeout": self.timeout,
                        "provider": self.provider,
                    }
                )

            except Exception as e:
                last_exception = LLMClientError(f"Unexpected error: {e}")
                logger.warning(
                    f"Unexpected error on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "provider": self.provider,
                    }
                )

            # If this is not the last attempt, wait before retrying
            if attempt < self.max_retries:
                delay = min(
                    self.base_delay * (2 ** attempt) + (0.1 * attempt),  # Exponential backoff with jitter
                    self.max_delay
                )

                logger.info(
                    f"Retrying LLM request in {delay:.2f} seconds",
                    extra={
                        "attempt": attempt + 1,
                        "delay_seconds": delay,
                        "next_attempt": attempt + 2,
                    }
                )

                await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            "LLM request failed after all retries",
            extra={
                "total_attempts": self.max_retries + 1,
                "last_error": str(last_exception),
            }
        )

        raise last_exception

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text completion from a simple prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Stop sequences for generation
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.generate_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences,
            **kwargs,
        )

        if self.provider == LLMProvider.OPENAI:
            return response.choices[0].message.content or ""
        else:  # OpenRouter
            return response["choices"][0]["message"]["content"] or ""

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate JSON completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Generated JSON as dictionary

        Raises:
            LLMClientError: If JSON generation fails
        """
        # Add JSON format instruction to system prompt
        json_instruction = "You must respond with valid JSON only. Do not include any explanations or text outside the JSON structure."

        if system_prompt:
            full_system_prompt = f"{system_prompt}\n\n{json_instruction}"
        else:
            full_system_prompt = json_instruction

        response = await self.generate_completion(
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
            **kwargs,
        )

        if self.provider == LLMProvider.OPENAI:
            content = response.choices[0].message.content or "{}"
        else:  # OpenRouter
            content = response["choices"][0]["message"]["content"] or "{}"

        try:
            import json
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMClientError(f"Failed to parse JSON response: {e}. Response content: {content}")

    async def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        try:
            import tiktoken

            # Get encoding for the model
            try:
                encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fallback to cl100k_base for unknown models
                encoding = tiktoken.get_encoding("cl100k_base")

            return len(encoding.encode(text))
        except ImportError:
            logger.warning("tiktoken not available, using rough token estimation")
            # Rough estimation: 1 token ≈ 4 characters for English text
            return len(text) // 4

    async def truncate_prompt(
        self,
        prompt: str,
        max_prompt_tokens: Optional[int] = None,
    ) -> str:
        """
        Truncate prompt to fit within token limit.

        Args:
            prompt: Original prompt
            max_prompt_tokens: Maximum tokens for prompt (defaults to 80% of max_tokens)

        Returns:
            Truncated prompt
        """
        if max_prompt_tokens is None:
            max_prompt_tokens = int(self.max_tokens * 0.8)

        current_tokens = await self.estimate_tokens(prompt)

        if current_tokens <= max_prompt_tokens:
            return prompt

        # Calculate how much to truncate
        excess_ratio = current_tokens / max_prompt_tokens
        target_length = len(prompt) / excess_ratio

        # Truncate from the middle, keeping start and end
        keep_start = target_length // 2
        keep_end = target_length - keep_start

        truncated = (
            prompt[:int(keep_start)] +
            "\n...[CONTENT TRUNCATED TO FIT TOKEN LIMIT]...\n" +
            prompt[-int(keep_end):]
        )

        logger.info(
            "Prompt truncated to fit token limit",
            extra={
                "original_tokens": current_tokens,
                "max_tokens": max_prompt_tokens,
                "truncated_tokens": await self.estimate_tokens(truncated),
                "original_length": len(prompt),
                "truncated_length": len(truncated),
            }
        )

        return truncated

    async def close(self) -> None:
        """Close the LLM client."""
        if self.provider == LLMProvider.OPENAI and self.client:
            await self.client.close()
        elif self.provider == LLMProvider.OPENROUTER and self.http_client:
            await self.http_client.aclose()
        logger.info("LLM client closed")


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def close_llm_client() -> None:
    """Close global LLM client."""
    global _llm_client
    if _llm_client:
        await _llm_client.close()
        _llm_client = None