"""Agent operations handling."""

import logging

from ...code_analysis.code_analyzer import CodeAnalyzer
from ...code_analysis.language_config import LanguageRegistry
from ...llm_refiner.llm_client import LLMClient
from ...llm_refiner.refinement_agent import RefinementAgent
from ...llm_reviewer import LLMReviewer, ReviewComment
from ...models import FileToReview
from ..constants import REFINE_LABEL, REVIEW_LABEL
from ..decorators import with_pr_state_management
from ..managers.pr_manager import PRContext, PRFile, PRManager

logger = logging.getLogger(__name__)


class AgentHandler:
    """Handles agent-related operations (review and refine)."""

    def __init__(self, pr_manager: PRManager) -> None:
        """Initialize the agent handler."""
        self.pr_manager = pr_manager
        self.reviewer = LLMReviewer()

        # Initialize refinement components
        self.llm_client = LLMClient()
        
        # Initialize language registry and get a default language (Python)
        self.language_registry = LanguageRegistry()
        default_language = self.language_registry.get_language("python")
        
        # Initialize code analyzer with the default language
        if default_language:
            self.code_analyzer = CodeAnalyzer(default_language)
            logger.info("Initialized CodeAnalyzer with Python language support")
        else:
            # Fallback case - we should never hit this in practice if the language registry is properly configured
            logger.error("Failed to initialize CodeAnalyzer: Python language not available")
            raise RuntimeError("Failed to initialize CodeAnalyzer: Python language not available")
            
        self.refinement_agent = RefinementAgent(
            pr_manager=pr_manager,
            llm_client=self.llm_client,
            code_analyzer=self.code_analyzer,
            language_registry=self.language_registry,
        )

    def _should_review_file(self, file: PRFile) -> bool:
        """Determine if a file should be reviewed.

        Args:
            file: The file to check

        Returns:
            bool: True if the file should be reviewed, False otherwise
        """
        # Skip deleted files
        if file.status == "removed":
            return False

        # Skip certain file types
        ignored_extensions = {
            ".pyc",
            ".pyo",
            ".pyd",  # Python bytecode
            ".log",
            ".tmp",  # Logs and temporary files
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",  # Images
            ".pdf",
            ".doc",
            ".docx",  # Documents
            ".zip",
            ".tar",
            ".gz",
            ".7z",  # Archives
            ".env",
            ".env.example",  # Environment files
            ".gitignore",
            ".dockerignore",  # VCS ignore files
        }

        # Skip files with ignored extensions
        if any(file.filename.endswith(ext) for ext in ignored_extensions):
            return False

        # Skip files in certain directories
        ignored_dirs = {
            "node_modules/",
            "venv/",
            ".venv/",  # Dependencies
            "build/",
            "dist/",
            ".pytest_cache/",  # Build artifacts
            "__pycache__/",  # Python cache
        }

        if any(ignored_dir in file.filename for ignored_dir in ignored_dirs):
            return False

        return True

    def _is_test_file(self, filename: str) -> bool:
        """Check if a file is a test file.

        Args:
            filename: The name of the file to check

        Returns:
            bool: True if the file is a test file, False otherwise
        """
        test_indicators = [
            "/test_",
            "/tests/",  # Python test files/directories
            "_test.py",
            "test_",  # Python test file naming
            ".spec.ts",
            ".test.ts",  # TypeScript/JavaScript test files
            "/spec/",
            "/__tests__/",  # Test directories
        ]
        return any(indicator in filename for indicator in test_indicators)

    def _post_review_comments(self, context: PRContext, comments: list[ReviewComment]) -> None:
        """Post review comments to the PR.

        Args:
            context: The PR context
            comments: List of review comments to post
        """
        for comment in comments:
            try:
                # Extract file path and line number from the location
                # Location format: [file:line] or [file:start-end] or [file:line1, line2, ...]
                location_parts = comment.location.strip("[]").split(":")
                if len(location_parts) != 2:
                    logger.error(f"Invalid location format: {comment.location}")
                    continue
                    
                file_path = location_parts[0]
                line_part = location_parts[1]
                
                # Prepare the base message
                message = (
                    f"### {comment.category} Issue - {comment.severity} Severity\n\n"
                    f"**Description:**\n{comment.description}\n\n"
                    f"**Suggestion:**\n{comment.suggestion}"
                )
                
                # Handle different location formats
                if "," in line_part:
                    # Multiple lines - post file-level comment
                    message = (
                        f"### {comment.category} Issue - {comment.severity} Severity\n\n"
                        f"**File:** {file_path}\n"
                        f"**Lines:** {line_part}\n\n"
                        f"**Description:**\n{comment.description}\n\n"
                        f"**Suggestion:**\n{comment.suggestion}"
                    )
                    self.pr_manager.post_comment(context, message)
                else:
                    # Single line or range - post line-specific comment
                    line_number = int(line_part.split("-")[1] if "-" in line_part else line_part)
                    self.pr_manager.post_review_comment(
                        context=context,
                        file_path=file_path,
                        line_number=line_number,
                        message=message,
                    )
                    
            except (ValueError, IndexError) as e:
                logger.error(f"Failed to parse location {comment.location}: {e}")
                # Fallback to general comment if location parsing fails
                message = (
                    f"### {comment.category} Issue - {comment.severity} Severity\n\n"
                    f"**Location:** {comment.location}\n\n"
                    f"**Description:**\n{comment.description}\n\n"
                    f"**Suggestion:**\n{comment.suggestion}"
                )
                self.pr_manager.post_comment(context, message)

    @with_pr_state_management(
        operation_name="review",
        operation_label=REVIEW_LABEL,
        success_message=(
            "✅ **Code Review Completed Successfully**\n\n"
            "I've analyzed the code and added review comments for suggested "
            "improvements. You can review these suggestions and:\n\n"
            "- Implement them manually, or\n"
            "- Add the `agentic-refine` label to let me automatically apply "
            "the improvements\n\n"
            "Thank you for using the Agentic Code Review tool!"
        ),
    )
    async def handle_review(self, context: PRContext) -> None:
        """Handle a code review request.

        This method:
        1. Fetches all changed files from the PR
        2. Filters files that need review
        3. Prepares the files and their context for review
        4. Uses LLMReviewer to analyze the code
        5. Posts review comments

        Args:
            context: The PR context
        """
        logger.info(f"Starting code review for PR #{context.pr_number}")

        # Step 1: Fetch all changed files
        try:
            changed_files = self.pr_manager.get_pr_files(context)
            logger.info(f"Found {len(changed_files)} changed files")
        except Exception as e:
            logger.error("Failed to fetch PR files")
            raise Exception(f"Failed to fetch PR files: {e}") from e

        # Step 2: Filter files that need review
        files_to_review = []
        for file in changed_files:
            if not self._should_review_file(file):
                logger.info(f"Skipping review of file: {file.filename}")
                continue

            is_test = self._is_test_file(file.filename)
            files_to_review.append(
                FileToReview(
                    file=file,
                    content=None,  # We'll fetch content later if needed
                    is_test_file=is_test,
                )
            )

        if not files_to_review:
            logger.info("No files to review")
            self.pr_manager.post_comment(
                context,
                "i No files found that require review. This could be because:\n"
                "- All changed files are in ignored categories (e.g., images, logs)\n"
                "- All files were deleted\n"
                "- No files were changed",
            )
            return

        # Log details for each file being reviewed
        for file_to_review in files_to_review:
            logger.info(f"File prepared for review: {file_to_review.file_path} (Status: {file_to_review.file.status}, Is Test: {file_to_review.is_test_file})")

        logger.info(f"Prepared {len(files_to_review)} files for review")

        # Step 3: Review files using LLMReviewer
        try:
            review_results = await self.reviewer.review_files(files_to_review)

            # Step 4: Post comments for each file
            for file_path, comments in review_results.items():
                logger.info(f"Posting {len(comments)} comments for {file_path}")
                self._post_review_comments(context, comments)

        except Exception as e:
            logger.error("Failed to review files")
            raise Exception(f"Failed to review files: {e}") from e

    @with_pr_state_management(
        operation_name="refine",
        operation_label=REFINE_LABEL,
        success_message=(
            "✅ **Code Refinement Completed Successfully**\n\n"
            "I've automatically implemented the suggested improvements from "
            "the code review. The changes have been committed to this PR.\n\n"
            "Please review the changes and make any additional adjustments "
            "as needed.\n\n"
            "Thank you for using the Agentic Code Review tool!"
        ),
    )
    async def handle_refine(self, context: PRContext) -> None:
        """Handle a code refinement request.

        This method:
        1. Retrieves review comments from the PR
        2. Filters out resolved comments
        3. Uses RefinementAgent to implement suggested changes
        4. Commits the changes to the PR

        Args:
            context: The PR context
        """
        logger.info(f"Starting code refinement for PR #{context.pr_number}")

        try:
            # Process PR using refinement agent
            await self.refinement_agent.process_pr(context.pr_number)
            logger.info(f"Successfully completed refinement for PR #{context.pr_number}")
        except Exception as e:
            logger.error(f"Failed to refine code: {e}")
            raise Exception(f"Failed to refine code: {e}") from e
