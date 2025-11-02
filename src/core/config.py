"""
Application configuration settings.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application Configuration
    APP_NAME: str = "SMS Campaign Generation System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/sms_campaigns",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 10

    # LLM Provider Configuration
    LLM_PROVIDER: str = "openai"  # "openai" | "openrouter"

    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_TIMEOUT: int = 60

    # OpenRouter Configuration
    OPENROUTER_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenRouter API key"
    )
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"
    OPENROUTER_MAX_TOKENS: int = 4000
    OPENROUTER_TEMPERATURE: float = 0.7
    OPENROUTER_TIMEOUT: int = 60

    # API Configuration
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Security Configuration
    SECRET_KEY: str = Field(
        description="Secret key for JWT tokens",
        min_length=32
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*.yourdomain.com"]

    # Rate Limiting Configuration
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_TIME_WINDOW: int = 60

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "text"
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    # Performance Configuration
    MAX_WORKERS: int = 4
    REQUEST_TIMEOUT: int = 120
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # Monitoring Configuration
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 30

    # Feature Flags
    ENABLE_CACHING: bool = True
    ENABLE_METRICS_COLLECTION: bool = True
    ENABLE_DETAILED_LOGGING: bool = True
    ENABLE_AUTO_CORRECTION: bool = True
    ENABLE_FLOW_VALIDATION: bool = True

    @field_validator('LLM_PROVIDER')
    @classmethod
    def validate_llm_provider(cls, v):
        """Validate LLM provider."""
        valid_providers = ['openai', 'openrouter']
        if v.lower() not in valid_providers:
            raise ValueError(f'LLM_PROVIDER must be one of: {valid_providers}')
        return v.lower()

    @model_validator(mode='before')
    @classmethod
    def validate_api_keys(cls, data):
        """Validate API keys based on LLM provider."""
        if isinstance(data, dict):
            provider = data.get('LLM_PROVIDER', 'openai').lower()
            openai_key = data.get('OPENAI_API_KEY')
            openrouter_key = data.get('OPENROUTER_API_KEY')

            if provider == 'openai':
                if not openai_key or (isinstance(openai_key, str) and openai_key.strip() == ''):
                    raise ValueError('OPENAI_API_KEY is required when LLM_PROVIDER is "openai"')
            elif provider == 'openrouter':
                if not openrouter_key or (isinstance(openrouter_key, str) and openrouter_key.strip() == ''):
                    raise ValueError('OPENROUTER_API_KEY is required when LLM_PROVIDER is "openrouter"')

        return data

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def database_config(self) -> dict:
        """Get database configuration dictionary."""
        return {
            "url": self.DATABASE_URL,
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_timeout": self.DATABASE_POOL_TIMEOUT,
            "pool_recycle": self.DATABASE_POOL_RECYCLE,
        }

    @property
    def redis_config(self) -> dict:
        """Get Redis configuration dictionary."""
        return {
            "url": self.REDIS_URL,
            "password": self.REDIS_PASSWORD,
            "db": self.REDIS_DB,
            "max_connections": self.REDIS_MAX_CONNECTIONS,
        }

    @property
    def openai_config(self) -> dict:
        """Get OpenAI configuration dictionary."""
        return {
            "api_key": self.OPENAI_API_KEY,
            "model": self.OPENAI_MODEL,
            "max_tokens": self.OPENAI_MAX_TOKENS,
            "temperature": self.OPENAI_TEMPERATURE,
            "timeout": self.OPENAI_TIMEOUT,
        }

    @property
    def openrouter_config(self) -> dict:
        """Get OpenRouter configuration dictionary."""
        return {
            "api_key": self.OPENROUTER_API_KEY,
            "model": self.OPENROUTER_MODEL,
            "max_tokens": self.OPENROUTER_MAX_TOKENS,
            "temperature": self.OPENROUTER_TEMPERATURE,
            "timeout": self.OPENROUTER_TIMEOUT,
        }

    @property
    def llm_config(self) -> dict:
        """Get current LLM provider configuration dictionary."""
        if self.LLM_PROVIDER.lower() == "openrouter":
            return self.openrouter_config
        return self.openai_config


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()