"""Pytest configuration and shared fixtures."""

import os
import pytest
from typing import Generator

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
        "GITHUB_TOKEN": "test_token",
        "OPENAI_API_KEY": "test_key",
    }
    # Store original env vars
    original_env = {k: os.environ.get(k) for k in env_vars}
    
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