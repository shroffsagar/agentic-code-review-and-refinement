"""Configuration settings for the application.

This module contains all configuration settings using Pydantic for type-safe
configuration management.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    All settings are loaded from environment variables.
    """

    # GitHub App settings
    GITHUB_APP_ID: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_WEBHOOK_SECRET: str

    # LLM settings
    LLM_API_KEY: str
    LLM_MODEL: str = "gpt-4-turbo-preview"  # Default to OpenAI's model
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000
    LLM_PROVIDER: str = "openai"  # New field to specify the LLM provider

    # Application settings
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Optional settings
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_ENTERPRISE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        case_sensitive=False,
    )


# Create global settings instance
settings = Settings()
