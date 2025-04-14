"""Configuration settings for the application.

This module contains all configuration settings using Pydantic for type-safe
configuration management.
"""

import logging
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Set up logging
logger = logging.getLogger(__name__)

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
    LLM_MODEL: str = "o3-mini"  # Updated to OpenAI's newest model
    LLM_TEMPERATURE: float = 0  # Lowered for more deterministic outputs
    LLM_MAX_TOKENS: int = 4000
    LLM_PROVIDER: str = "openai"  # New field to specify the LLM provider

    # Application settings
    LOG_LEVEL: str = "DEBUG"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Optional settings
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_ENTERPRISE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    def __init__(self, **kwargs):
        """Initialize settings with debug logging."""
        logger.info("Initializing Settings...")
        try:
            super().__init__(**kwargs)
            logger.info("Settings initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Settings: {e!s}")
            raise

# Create global settings instance
try:
    settings = Settings()
    logger.info("Global settings instance created successfully")
except Exception as e:
    logger.error(f"Error creating global settings instance: {e!s}")
    raise
