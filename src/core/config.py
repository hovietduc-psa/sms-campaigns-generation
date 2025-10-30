"""
Configuration settings for the campaign generation API.
"""
import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    api_title: str = "Campaign Generation API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # OpenAI Configuration
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    openai_mini_model: str = os.getenv("OPENAI_MINI_MODEL", "gpt-4o-mini")

    # GROQ Configuration (fallback)
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    groq_model: str = "llama-3.3-70b-versatile"

    # Qdrant Configuration (for templates)
    qdrant_url: Optional[str] = os.getenv("QDRANT_URL")
    qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY")

    # Cohere Configuration (for embeddings)
    cohere_api_key: Optional[str] = os.getenv("COHERE_API_KEY")

    # OpenRouter Configuration (alternative AI provider)
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_model_primary: str = os.getenv("OPENROUTER_MODEL_PRIMARY", "openai/gpt-4o")
    openrouter_model_fallback: str = os.getenv("OPENROUTER_MODEL_FALLBACK", "openai/gpt-4o-mini")
    openrouter_model_embedding: str = os.getenv("OPENROUTER_MODEL_EMBEDDING", "text-embedding-3-small")

    # Database Configuration (optional, for storing campaigns)
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # Logging Configuration
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings