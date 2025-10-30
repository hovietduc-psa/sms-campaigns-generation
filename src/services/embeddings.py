"""
Embedding service for text vectorization.
"""
import logging
from typing import List, Optional, Dict
import asyncio
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self.dimensions = 1536  # OpenAI text-embedding-3-small dimensions

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)

            response = await client.embeddings.create(
                model=self.model,
                input=text
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere embedding provider."""

    def __init__(self, api_key: str, model: str = "embed-multilingual-v3.0"):
        self.api_key = api_key
        self.model = model
        self.dimensions = 1024  # Cohere multilingual model dimensions

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding using Cohere."""
        try:
            import cohere
            client = cohere.AsyncClient(api_key=self.api_key)

            response = await client.embed(
                texts=[text],
                model=self.model,
                input_type="search_document"
            )

            return response.embeddings[0]

        except Exception as e:
            logger.error(f"Cohere embedding failed: {e}")
            raise


class EmbeddingService:
    """Embedding service with caching and multiple providers."""

    def __init__(self, provider: str = "cohere", api_key: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            provider: Provider name ("openai" or "cohere")
            api_key: API key (if None, will try to get from environment)
        """
        self.provider_name = provider
        self.cache: Dict[str, List[float]] = {}
        self.cache_max_size = 1000

        # Initialize provider
        if provider == "openai":
            import os
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required for OpenAI embeddings")
            self.provider = OpenAIEmbeddingProvider(api_key)
            self.dimensions = 1536

        elif provider == "cohere":
            import os
            api_key = api_key or os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("Cohere API key required for Cohere embeddings")
            self.provider = CohereEmbeddingProvider(api_key)
            self.dimensions = 1024

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"Initialized {provider} embedding service")

    async def embed_text_async(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for text asynchronously.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector
        """
        # Check cache first
        if use_cache and text in self.cache:
            return self.cache[text]

        # Generate embedding
        embedding = await self.provider.embed_text(text)

        # Cache result
        if use_cache:
            self._cache_result(text, embedding)

        return embedding

    def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for text (synchronous wrapper).

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector
        """
        # Run async function in event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.embed_text_async(text, use_cache))

    def _cache_result(self, text: str, embedding: List[float]):
        """Cache embedding result."""
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.cache_max_size:
            # Simple FIFO - remove first entry
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        self.cache[text] = embedding

    def clear_cache(self):
        """Clear embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.cache_max_size,
            "utilization": len(self.cache) / self.cache_max_size
        }