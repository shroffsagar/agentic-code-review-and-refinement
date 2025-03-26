"""LLM client for code generation and validation."""

import logging
from typing import Optional

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

from agentic_code_review.config import settings
from .models import RefinementResponse

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM services."""

    def __init__(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> None:
        """Initialize the LLM client.

        Args:
            model_name: Optional name of the LLM model to use (defaults to settings.LLM_MODEL)
            temperature: Optional temperature for model responses (defaults to settings.LLM_TEMPERATURE)
            max_tokens: Optional maximum tokens for model responses (defaults to settings.LLM_MAX_TOKENS)
        """
        if not settings.LLM_API_KEY:
            logger.error("LLM_API_KEY environment variable is not set")
            raise ValueError("LLM_API_KEY environment variable is not set")

        base_llm = ChatOpenAI(
            model_name=model_name or settings.LLM_MODEL,
            temperature=temperature or settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            api_key=settings.LLM_API_KEY,
        )
        # Configure LLM to return structured output
        self.llm = base_llm.with_structured_output(RefinementResponse)

    async def generate_code(self, prompt: str) -> Optional[RefinementResponse]:
        """Generate code based on a prompt.

        Args:
            prompt: The prompt for code generation

        Returns:
            Structured response with code changes or None if generation fails
        """
        try:
            # Get LLM response with structured output
            response = await self.llm.ainvoke(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return None

    async def validate_code(self, code: str) -> bool:
        """Validate generated code.

        Args:
            code: The code to validate

        Returns:
            True if code is valid, False otherwise
        """
        try:
            # TODO: Implement actual code validation using AST parsing
            # For now, return True
            return True
        except Exception as e:
            logger.error(f"Error validating code: {e}")
            return False
