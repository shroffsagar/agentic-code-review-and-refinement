"""Agent operations handling."""

import logging

from ...llm_refiner.llm_client import LLMClient
from ...llm_refiner.refinement_agent import RefinementAgent
from ...llm_reviewer import LLMReviewer
from ...models import FileToReview
from ..constants import REFINE_LABEL, REVIEW_LABEL
from ..decorators import with_pr_state_management
from ..managers.pr_manager import PRContext, PRManager

logger = logging.getLogger(__name__)


class AgentHandler:
    """Handles agent-related operations (review and refine)."""

    def __init__(self, pr_manager: PRManager) -> None:
        """Initialize the agent handler."""
        self.pr_manager = pr_manager
        self.reviewer = LLMReviewer()

        # Initialize refinement components
        self.llm_client = LLMClient()
        self.refinement_agent = RefinementAgent(
            pr_manager=pr_manager,
            llm_client=self.llm_client
        )

    @with_pr_state_management(
        operation_name="review",
        operation_label=REVIEW_LABEL,
        success_message="Code review completed! Check the inline comments for suggestions."
    )
    async def handle_review(self, context: PRContext) -> None:
        """Handle reviewing a pull request.

        Args:
            context: The PR context
        """
        # Get PR files
        logger.info(f"Getting files for PR #{context.pr_number}")
        files = self.pr_manager.get_pr_files(context)
        logger.info(f"Found {len(files)} files in PR #{context.pr_number}")

        # Collect files for review
        files_to_review = []
        for pr_file in files:
            # Skip deleted files
            if pr_file.status == "removed":
                logger.info(f"Skipping deleted file: {pr_file.filename}")
                continue

            # Extract code diff units for better context
            logger.info(f"Extracting code diff units for {pr_file.filename}")
            code_diff_units = self.pr_manager.extract_unique_code_diff_units(context, pr_file)

            if not code_diff_units:
                logger.info(f"No code diff units extracted from {pr_file.filename}, skipping review")
                continue

            logger.info(f"Extracted {len(code_diff_units)} code diff units from {pr_file.filename}")

            # Get current version of file content from the most recent code diff unit
            content = None
            for unit in code_diff_units:
                if unit.after_code:
                    content = unit.after_code
                    break

            if not content and pr_file.status != "added":
                logger.warning(f"Could not extract content for {pr_file.filename}, skipping review")
                continue

            file_to_review = FileToReview(
                file=pr_file,
                content=content,
                code_diff_units=code_diff_units
            )
            files_to_review.append(file_to_review)

        logger.info(f"Prepared {len(files_to_review)} files for review out of {len(files)} total files")

        # Perform review
        logger.info("Starting code review process")
        review_results = await self.reviewer.review_files(files_to_review)

        # Post comments
        total_comments = 0
        for file_path, comments in review_results.items():
            logger.info(f"Processing {len(comments)} comments for {file_path}")
            for comment in comments:
                try:
                    logger.info(f"Posting review comment for {file_path} - Category: {comment.category}, Side: {comment.side}, Line: {comment.line_number}")
                    self.pr_manager.post_review_comment(
                        context=context,
                        file_path=file_path,
                        line_number=comment.line_number,
                        message=f"# {comment.category} - {comment.severity}\n\n{comment.description}\n\n**Suggestion**: {comment.suggestion}",
                        side=comment.side
                    )
                    total_comments += 1
                except Exception as e:
                    logger.error(f"Failed to post comment for {file_path}: {e}")

        logger.info(f"Review completed. Posted {total_comments} comments across {len(review_results)} files")

    @with_pr_state_management(
        operation_name="refinement",
        operation_label=REFINE_LABEL,
        success_message="Code refinement completed! Check the PR diff to see the changes."
    )
    async def handle_refinement(self, context: PRContext) -> None:
        """Handle refining a pull request based on review comments.

        Args:
            context: The PR context
        """
        # Process the PR with our new language-agnostic refinement agent
        await self.refinement_agent.process_pr(context)
