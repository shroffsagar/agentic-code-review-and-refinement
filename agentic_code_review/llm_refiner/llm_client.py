"""LLM client for code generation and verification.

This module provides functionality for communicating with LLM services
to generate and verify code changes.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
import json

from langchain_core.pydantic_v1 import BaseModel
from langchain_openai import ChatOpenAI

from agentic_code_review.config import settings
from .models import RefinementResponse

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMClient:
    """Client for interacting with LLM services."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Initialize the LLM client.

        Args:
            model_name: Optional model name to use (defaults to settings.LLM_MODEL)
            temperature: Optional temperature setting (defaults to settings.LLM_TEMPERATURE)
            max_tokens: Optional max tokens setting (defaults to settings.LLM_MAX_TOKENS)
        """
        if not settings.LLM_API_KEY:
            logger.error("LLM_API_KEY environment variable is not set")
            raise ValueError("LLM_API_KEY environment variable is not set")

        # Store the base LLM
        self.base_llm = ChatOpenAI(
            model_name=model_name or settings.LLM_MODEL,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            api_key=settings.LLM_API_KEY,
        )

    async def generate_code(self, prompt: str, response_model: Type[T] = RefinementResponse) -> Optional[T]:
        """Generate code based on a prompt.

        Args:
            prompt: The prompt for code generation
            response_model: The Pydantic model class for structured output (defaults to RefinementResponse)

        Returns:
            An instance of the specified response model, or None if generation failed
        """
        try:
            # Log the full prompt without truncation
            logger.info(f"FULL PROMPT TO LLM: {prompt}")
            
            llm_with_model = self.base_llm.with_structured_output(response_model)
            
            # Get LLM response
            response = await llm_with_model.ainvoke(prompt)
            
            # Log the complete response without truncation
            response_log = None
            if response:
                try:
                    if hasattr(response, "model_dump"):
                        response_log = json.dumps(response.model_dump(), indent=2)
                    elif hasattr(response, "dict"):
                        response_log = json.dumps(response.dict(), indent=2)
                    else:
                        response_log = str(response)
                        
                    logger.info(f"FULL LLM RESPONSE: {response_log}")
                except Exception as log_error:
                    logger.error(f"Error serializing response for logging: {log_error}")
                    response_log = str(response)
                    logger.info(f"FULL LLM RESPONSE (as string): {response_log}")
            else:
                logger.warning("Received empty response from LLM")
            
            return response
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return None
            
    async def verify_code(self, original_code: str, modified_code: str) -> Dict[str, Any]:
        """Verify that modifications to code are appropriate and correct.

        Args:
            original_code: The original code
            modified_code: The modified code

        Returns:
            Dictionary with verification results
        """
        prompt = f"""
        Please verify that the following code modification is appropriate and correct.
        
        ORIGINAL CODE:
        ```
        {original_code}
        ```
        
        MODIFIED CODE:
        ```
        {modified_code}
        ```
        
        Analyze the changes and verify:
        1. The change is syntactically correct
        2. The changes are minimal and focused
        3. The changes do not introduce new issues
        4. The changes do not change the overall behavior of the code
        
        Return a JSON response with the following fields:
        - is_valid: boolean indicating if the change is valid
        - issues: array of issues found (empty if valid)
        - explanation: brief explanation of why the change is valid or not
        """
        
        try:
            # Log the full verification prompt without truncation
            logger.info(f"FULL VERIFICATION PROMPT TO LLM: {prompt}")
            
            # Define a response model for verification
            verification_model = {
                "is_valid": bool,
                "issues": List[str],
                "explanation": str
            }
            
            # Configure LLM with structured output
            llm_for_verification = self.base_llm.with_structured_output(verification_model, method='function_calling')
            
            # Get LLM response
            response = await llm_for_verification.ainvoke(prompt)
            
            # Log the full verification response without truncation
            if response:
                logger.info(f"FULL VERIFICATION RESPONSE: {json.dumps(response, indent=2)}")
            else:
                logger.warning("Received empty verification response from LLM")
                
            return response
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {
                "is_valid": False,
                "issues": [f"Error during verification: {str(e)}"],
                "explanation": "Failed to verify code due to an error"
            } 