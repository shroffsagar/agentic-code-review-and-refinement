"""LLM-powered code reviewer implementation."""

import logging
from typing import cast

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

from agentic_code_review.config import settings

from ..models import FileToReview
from .prompts.review_prompts import code_review_prompt, test_review_prompt

logger = logging.getLogger(__name__)


class ReviewComment(BaseModel):
    """Model for a single review comment."""

    location: str = Field(description="File and line number where the issue was found")
    category: str = Field(
        description="Category of the issue",
        # Define valid categories
        pattern="^(Quality|Performance|Security|Testing|Maintainability|Coverage)$",
    )
    severity: str = Field(description="Severity level of the issue", pattern="^(High|Medium|Low)$")
    description: str = Field(description="Detailed description of the issue")
    suggestion: str = Field(description="Suggested improvement")


class ReviewResponse(BaseModel):
    """Model for the complete review response."""

    comments: list[ReviewComment] = Field(description="List of review comments")


class LLMReviewer:
    """LLM-powered code reviewer using langchain."""

    def __init__(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> None:
        """Initialize the LLM reviewer.

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
        self.llm = base_llm.with_structured_output(ReviewResponse)

    async def review_file(self, file: FileToReview) -> list[ReviewComment]:
        """Review a single file and return review comments.

        Args:
            file: FileToReview object containing file information and changes

        Returns:
            List of ReviewComment objects containing the review feedback
        """
        try:
            # Select appropriate prompt based on file type
            prompt = test_review_prompt if file.is_test_file else code_review_prompt

            # Create format instructions manually
            format_instructions = """
            {
              "comments": [
                {
                  "location": "string (format: [filename:line_number], e.g. [main.py:42])",
                  "category": "string (one of: Quality, Performance, Security, Testing, Maintainability, Coverage)",
                  "severity": "string (one of: High, Medium, Low)",
                  "description": "string (detailed description of the issue)",
                  "suggestion": "string (concrete suggestion for improvement)"
                }
              ]
            }
            """

            # Format prompt with file information
            formatted_prompt = prompt.format(
                file_path=file.file_path,
                code_diff=file.code_diff,
                additional_context=file.additional_context or "No additional context provided.",
                format_instructions=format_instructions,
            )

            # Get LLM response with structured output
            response = await self.llm.ainvoke(formatted_prompt)
            # Cast the response to ReviewResponse to satisfy type checker
            typed_response = cast(ReviewResponse, response)
            return typed_response.comments

        except Exception as e:
            logger.error(f"Error reviewing file {file.file_path}: {e}")
            raise

    async def review_files(self, files: list[FileToReview]) -> dict[str, list[ReviewComment]]:
        """Review multiple files and return review comments for each.

        Args:
            files: List of FileToReview objects to review

        Returns:
            Dictionary mapping file paths to lists of ReviewComment objects
        """
        results = {}
        for file in files:
            try:
                results[file.file_path] = await self.review_file(file)
            except Exception as e:
                logger.error(f"Failed to review {file.file_path}: {e}")
                results[file.file_path] = []
        return results
