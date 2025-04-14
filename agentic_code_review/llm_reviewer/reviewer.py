"""LLM-powered code reviewer implementation."""

import logging
import difflib
from enum import Enum, auto

from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

from agentic_code_review.config import settings

from ..llm_refiner.models import CodeDiffUnit
from ..models import FileToReview
from .prompts.review_prompts import code_review_prompt, test_review_prompt

logger = logging.getLogger(__name__)


class ReviewComment(BaseModel):
    """Model for a single review comment."""

    file_path: str = Field(description="Path to the file where the issue was found")
    line_number: int = Field(description="Line number where the issue was found")
    category: str = Field(
        description="Category of the issue",
        # Define valid categories
        pattern="^(Quality|Performance|Security|Testing|Maintainability|Coverage)$",
    )
    severity: str = Field(description="Severity level of the issue", pattern="^(High|Medium|Low)$")
    description: str = Field(description="Detailed description of the issue")
    suggestion: str = Field(description="Suggested improvement")
    side: str = Field(description="Which side of the diff to place the comment on", pattern="^(LEFT|RIGHT)$")


class ReviewResponse(BaseModel):
    """Model for the complete review response."""

    comments: list[ReviewComment] = Field(description="List of review comments")


# Template for formatting code unit context
CODE_UNIT_TEMPLATE = """## Code Unit in {file_path}

{before_section}

{after_section}

{changes_section}"""

BEFORE_SECTION_TEMPLATE = """### Before (lines {line_range}):
```
{code}
```"""

AFTER_SECTION_TEMPLATE = """### After (lines {line_range}):
```
{code}
```"""

CHANGES_SECTION_TEMPLATE = """## Changes:

{diff_blocks}"""

DIFF_BLOCK_TEMPLATE = """```diff
{diff_text}
```"""


class ChangeType(Enum):
    """Enum representing the type of code change."""
    NEW = auto()
    REMOVED = auto()
    MODIFIED = auto()


class LLMReviewer:
    """LLM-powered code reviewer using langchain."""

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
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
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            api_key=settings.LLM_API_KEY,
            disabled_params={"parallel_tool_calls": None}
        )
        logger.info(f"Using model: {settings.LLM_MODEL}")
        logger.info(f"Using max tokens: {settings.LLM_MAX_TOKENS}")
        # Configure LLM to return structured output
        self.llm = base_llm.with_structured_output(ReviewResponse)

        # Create reusable prompt templates
        self.code_unit_template = PromptTemplate(
            input_variables=["file_path", "before_section", "after_section", "changes_section"],
            template=CODE_UNIT_TEMPLATE
        )
        self.before_section_template = PromptTemplate(
            input_variables=["line_range", "code"],
            template=BEFORE_SECTION_TEMPLATE
        )
        self.after_section_template = PromptTemplate(
            input_variables=["line_range", "code"],
            template=AFTER_SECTION_TEMPLATE
        )
        self.changes_section_template = PromptTemplate(
            input_variables=["diff_blocks"],
            template=CHANGES_SECTION_TEMPLATE
        )
        self.diff_block_template = PromptTemplate(
            input_variables=["diff_text"],
            template=DIFF_BLOCK_TEMPLATE
        )

    async def review_unit(self, file_path: str, code_unit: CodeDiffUnit, is_test_file: bool, additional_context: str = None) -> list[ReviewComment]:
        """Review a single code unit and return review comments.

        Args:
            file_path: Path to the file
            code_unit: CodeDiffUnit object containing the unit to review
            is_test_file: Whether this is a test file
            additional_context: Any additional context for the LLM

        Returns:
            List of ReviewComment objects containing the review feedback
        """
        try:
            # Determine change type to optimize token usage
            change_type = self._determine_change_type(code_unit)
            logger.debug(f"Detected change type: {change_type}")

            # Format context and get compare instruction based on change type
            unit_context, compare_instruction = self._format_context_by_change_type(file_path, code_unit, change_type, is_test_file)
            
            logger.debug(f"Using compare instruction: '{compare_instruction}'")
            logger.debug(f"Prepared context with {len(unit_context)} characters")

            # Select prompt and get review from LLM
            prompt = test_review_prompt if is_test_file else code_review_prompt

            # Format instructions for the LLM response
            format_instructions = """
            {
              "comments": [
                {
                  "file_path": "string (e.g. main.py)",
                  "line_number": "integer (e.g. 42)",
                  "category": "string (one of: Quality, Performance, Security, Testing, Maintainability, Coverage)",
                  "severity": "string (one of: High, Medium, Low)",
                  "description": "string (detailed description of the issue)",
                  "suggestion": "string (concrete suggestion with examples for improvement)",
                  "side": "string (one of: LEFT, RIGHT) - LEFT for old/deleted code, RIGHT for new/modified code"
                }
              ]
            }
            """

            # Format prompt and get response
            formatted_prompt = prompt.format(
                file_path=file_path,
                code_diff=unit_context,
                additional_context=additional_context or "No additional context provided.",
                format_instructions=format_instructions,
                compare_instruction=compare_instruction
            )

            # Log the complete request to the LLM
            logger.debug(f"=== LLM REQUEST for {file_path} ===")
            logger.debug(f"Prompt length: {len(formatted_prompt)}")
            # check if logger debug mode is on
            if logger.getEffectiveLevel() == logging.DEBUG:
                print("PROMPT (print) : ", formatted_prompt)
                # logger.debug("PROMPT (logger) : ")
                # logger.debug(formatted_prompt)
            logger.debug("="*50)

            # Get response from LLM
            response: ReviewResponse = await self.llm.ainvoke(formatted_prompt)

            # Log the complete LLM response
            logger.debug(f"=== LLM RESPONSE for {file_path} ===")
            if response.comments:
                for i, comment in enumerate(response.comments, 1):
                    logger.debug(f"Comment {i}:")
                    logger.debug(f"  File: {comment.file_path}")
                    logger.debug(f"  Line: {comment.line_number}")
                    logger.debug(f"  Category: {comment.category}")
                    logger.debug(f"  Severity: {comment.severity}")
                    logger.debug(f"  Side: {comment.side}")
                    logger.debug(f"  Description: {comment.description}")
                    logger.debug(f"  Suggestion: {comment.suggestion}")
                    logger.debug("-"*30)
            else:
                logger.debug("No comments returned from LLM")
            logger.debug("="*50)

            # Log summary
            comment_count = len(response.comments)
            if comment_count > 0:
                logger.info(f"Found {comment_count} issues in code unit")
            else:
                logger.info("No issues found in code unit")

            return response.comments

        except Exception as e:
            logger.error(f"Error reviewing code unit in {file_path}: {e}")
            raise

    def _determine_change_type(self, code_unit: CodeDiffUnit) -> ChangeType:
        """Determine the type of change for a code unit.
        
        Args:
            code_unit: The code unit to analyze
            
        Returns:
            ChangeType indicating change type: NEW, REMOVED, or MODIFIED
        """
        # New code added (no before code)
        if not code_unit.before_code and code_unit.after_code:
            return ChangeType.NEW
        
        # Code removed (no after code)
        if code_unit.before_code and not code_unit.after_code:
            return ChangeType.REMOVED
        
        # Code modified (both before and after exist)
        return ChangeType.MODIFIED
        
    def _format_context_by_change_type(self, file_path: str, code_unit: CodeDiffUnit, change_type: ChangeType, is_test_file: bool = False) -> tuple[str, str]:
        """Format the code context and generate compare instruction based on the type of change.
        
        Args:
            file_path: Path to the file
            code_unit: CodeDiffUnit containing the code to review
            change_type: Type of change (NEW, REMOVED, or MODIFIED)
            is_test_file: Whether this is a test file
            
        Returns:
            Tuple of (formatted_context_string, compare_instruction)
        """
        # Always include diff sections if available
        changes_section = ""
        if code_unit.diff_texts:
            diff_blocks = "\n\n".join([
                self.diff_block_template.format(diff_text=diff_text)
                for diff_text in code_unit.diff_texts
            ])
            changes_section = self.changes_section_template.format(diff_blocks=diff_blocks)
        
        # Generate compare instruction based on change type
        if change_type == ChangeType.NEW:
            compare_instruction = "Review the new code for correctness, efficiency, and seamless integration."
            
            after_section = ""
            if code_unit.after_context and code_unit.after_code:
                after_lines = f"{code_unit.after_context.start_line}-{code_unit.after_context.end_line}"
                after_section = self.after_section_template.format(
                    line_range=after_lines,
                    code=code_unit.after_code
                )
            
            # Combine sections
            unit_context = self.code_unit_template.format(
                file_path=file_path,
                before_section="",  # Skip before section for new functions
                after_section=after_section,
                changes_section=changes_section
            )
        
        # For removed functions, include only diff and before section
        elif change_type == ChangeType.REMOVED:
            compare_instruction = "Assess the removed code for its previous functionality and its impact on the system."
            
            before_section = ""
            if code_unit.before_context and code_unit.before_code:
                before_lines = f"{code_unit.before_context.start_line}-{code_unit.before_context.end_line}" 
                before_section = self.before_section_template.format(
                    line_range=before_lines,
                    code=code_unit.before_code
                )
            
            # Combine sections
            unit_context = self.code_unit_template.format(
                file_path=file_path,
                before_section=before_section,
                after_section="",  # Skip after section for removed functions
                changes_section=changes_section
            )
        
        # For modified functions, include diff and determine if both versions are needed
        else:
            # Determine complexity of change to decide if both before and after are needed
            include_both_versions = self._is_complex_change(code_unit)
            
            if include_both_versions:
                compare_instruction = "Compare the before and after code to evaluate changes in logic, performance, and maintainability."
            else:
                compare_instruction = "Review the updated code and its diff to confirm that the changes improve or maintain existing logic, performance, and code quality."
            
            before_section = ""
            if include_both_versions and code_unit.before_context and code_unit.before_code:
                before_lines = f"{code_unit.before_context.start_line}-{code_unit.before_context.end_line}"
                before_section = self.before_section_template.format(
                    line_range=before_lines,
                    code=code_unit.before_code
                )
            
            after_section = ""
            if code_unit.after_context and code_unit.after_code:
                after_lines = f"{code_unit.after_context.start_line}-{code_unit.after_context.end_line}"
                after_section = self.after_section_template.format(
                    line_range=after_lines,
                    code=code_unit.after_code
                )
            
            # Combine sections
            unit_context = self.code_unit_template.format(
                file_path=file_path,
                before_section=before_section,
                after_section=after_section,
                changes_section=changes_section
            )
            
        # Add test-specific wording if needed
        if is_test_file and "test" not in compare_instruction:
            compare_instruction += " test"
            
        # Clean up any empty lines caused by missing sections
        unit_context = unit_context.replace("\n\n\n", "\n\n")
        
        return unit_context, compare_instruction
        
    def _is_complex_change(self, code_unit: CodeDiffUnit) -> bool:
        """Determine if a change is complex enough to warrant including both before and after versions.
        
        Args:
            code_unit: The code unit to analyze
                
        Returns:
            True if the change is complex, False otherwise.
        """
        # If we don't have both before and after, it's not a complex change.
        if not code_unit.before_code or not code_unit.after_code:
            return False

        # Preprocess the code: strip excessive whitespace and split into non-empty lines.
        before_lines = [line for line in code_unit.before_code.strip().split("\n") if line.strip()]
        after_lines = [line for line in code_unit.after_code.strip().split("\n") if line.strip()]

        # If either snippet is very short, include both for context.
        if len(before_lines) < 5 or len(after_lines) < 5:
            return True

        # Calculate a simple change percentage based on line count.
        total_lines = max(len(before_lines), len(after_lines))
        line_diff = abs(len(before_lines) - len(after_lines))
        change_percentage = line_diff / total_lines if total_lines > 0 else 0

        logger.debug(f"Line change percentage: {change_percentage:.2f}")
        if change_percentage > 0.3:
            return True

        # Use a similarity ratio to assess how much the content changed.
        # Normalize strings to minimize differences due to formatting.
        before_clean = "\n".join(before_lines)
        after_clean = "\n".join(after_lines)
        similarity = difflib.SequenceMatcher(None, before_clean, after_clean).ratio()
        logger.debug(f"Similarity ratio: {similarity:.2f}")

        # If the content similarity is below a threshold, mark as complex.
        if similarity < 0.7:
            return True

        # Finally, use the number of diff hunks as a proxy for complexity.
        if len(code_unit.diff_texts) >= 3:
            return True

        # Default: not a complex change.
        return False

    async def review_file(self, file: FileToReview) -> list[ReviewComment]:
        """Review a single file by reviewing each code unit separately.

        Args:
            file: FileToReview object containing file information and changes

        Returns:
            List of ReviewComment objects containing the review feedback
        """
        try:
            logger.info(f"Starting code review for file: {file.file_path}")
            logger.debug(f"File status: {file.file.status}, Changes: +{file.file.additions} -{file.file.deletions}")

            if not file.code_diff_units:
                logger.warning(f"No code diff units found for {file.file_path}, skipping review")
                return []

            all_comments = []

            # Process each code unit separately
            for i, unit in enumerate(file.code_diff_units, 1):
                logger.info(f"Processing unit {i}/{len(file.code_diff_units)} in {file.file_path}")
                unit_comments = await self.review_unit(
                    file_path=file.file_path,
                    code_unit=unit,
                    is_test_file=file.is_test_file,
                    additional_context=file.additional_context
                )
                all_comments.extend(unit_comments)

            # Log overall results
            if all_comments:
                logger.info(f"File review complete. Found {len(all_comments)} total issues in {file.file_path}")
            else:
                logger.info(f"File review complete. No issues found in {file.file_path}")

            return all_comments

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
        logger.info(f"Starting review of {len(files)} files")
        results = {}
        total_comments = 0

        for i, file in enumerate(files, 1):
            try:
                logger.info(f"Processing file {i}/{len(files)}: {file.file_path}")
                comments = await self.review_file(file)
                results[file.file_path] = comments
                total_comments += len(comments)
            except Exception as e:
                logger.error(f"Failed to review {file.file_path}: {e}")
                results[file.file_path] = []

        logger.info(f"Review complete. Found {total_comments} total issues across {len(files)} files")
        return results
