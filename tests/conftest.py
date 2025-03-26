"""Pytest configuration and shared fixtures."""

import logging
import os
from collections.abc import Generator

import pytest

from agentic_code_review.utils.logging import setup_logging


@pytest.fixture(autouse=True)
def setup_test_logging() -> Generator[None, None, None]:
    """Set up logging for tests."""
    # Configure logging for tests
    setup_logging(level="DEBUG")
    yield
    # Clean up after tests
    logging.getLogger("agentic_code_review").handlers = []


@pytest.fixture
def test_env() -> Generator[dict[str, str], None, None]:
    """Set up test environment variables."""
    env_vars = {
        "ACR_GITHUB_TOKEN": "test_token",  # pragma: allowlist secret
        "ACR_LLM_API_KEY": "test_key",  # pragma: allowlist secret
        "ACR_LLM_MODEL": "gpt-4-turbo-preview",
        "ACR_LLM_TEMPERATURE": "0.0",
        "ACR_LOG_LEVEL": "DEBUG",
        "ACR_PORT": "3000",
        "ACR_GITHUB_APP_ID": "12345",
        "ACR_GITHUB_PRIVATE_KEY": "test_key",  # pragma: allowlist secret
        "ACR_GITHUB_WEBHOOK_SECRET": "test_secret",  # pragma: allowlist secret
        "ACR_GITHUB_ENTERPRISE_URL": "https://github.com",
    }
    # Store original env vars
    original_env = {k: os.environ.get(k, "") for k in env_vars}

    # Set test env vars
    for key, value in env_vars.items():
        os.environ[key] = value

    yield env_vars

    # Restore original env vars
    for key in env_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]
