"""Agent operations handling."""

import logging

from ...llm_refiner.llm_client import LLMClient
from ...llm_refiner.refinement_agent import RefinementAgent
from ...llm_reviewer import LLMReviewer
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
        files = self.pr_manager.get_pr_files(context)
        
        # Collect files for review
        files_to_review = []
        for pr_file in files:
            # Skip deleted files
            if pr_file.status == "removed":
                continue
                
            # Get file content
            pr = self.pr_manager._get_pr(context)
            content = self.pr_manager.get_file_content(pr.head.repo, pr_file.filename, pr.head.ref)
            
            if content:
                file_to_review = FileToReview(
                    file=pr_file,
                    content=content
                )
                files_to_review.append(file_to_review)
        
        # Perform review
        review_results = await self.reviewer.review_files(files_to_review)
        
        # Post comments
        for file_path, comments in review_results.items():
            for comment in comments:
                try:
                    self.pr_manager.post_review_comment(
                        context=context,
                        file_path=file_path,
                        line_number=comment.line_number,
                        message=f"# {comment.category} - {comment.severity}\n\n{comment.description}\n\n**Suggestion**: {comment.suggestion}"
                    )
                except Exception as e:
                    logger.error(f"Failed to post comment for {file_path}: {e}")

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
