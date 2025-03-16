"""Agent operations handling."""

import logging
from typing import Any

from ..constants import IN_PROGRESS_LABEL, REFINE_LABEL, REVIEW_LABEL
from ..managers.pr_manager import PRContext, PRManager

logger = logging.getLogger(__name__)


class AgentHandler:
    """Handles agent-related operations (review and refine)."""

    def __init__(self, pr_manager: PRManager) -> None:
        self.pr_manager = pr_manager

    def handle_review(
        self, installation_id: int, repository: dict[str, Any], pr_number: int
    ) -> None:
        """Handle a code review request."""
        logger.info(f"Starting review for PR #{pr_number}")
        context = PRContext(installation_id, repository, pr_number)

        try:
            self.pr_manager.manage_labels(
                context, add_labels=[IN_PROGRESS_LABEL], remove_labels=[REVIEW_LABEL]
            )

            # TODO: Implement review logic
            logger.info(f"Completed review for PR #{pr_number}")

        except Exception as e:
            self._handle_error(context, e, "review")
            raise
        finally:
            self.pr_manager.manage_labels(context, remove_labels=[IN_PROGRESS_LABEL])

    def handle_refine(
        self, installation_id: int, repository: dict[str, Any], pr_number: int
    ) -> None:
        """Handle a code refinement request."""
        logger.info(f"Starting refinement for PR #{pr_number}")
        context = PRContext(installation_id, repository, pr_number)

        try:
            self.pr_manager.manage_labels(
                context, add_labels=[IN_PROGRESS_LABEL], remove_labels=[REFINE_LABEL]
            )

            # TODO: Implement refinement logic
            logger.info(f"Completed refinement for PR #{pr_number}")

        except Exception as e:
            self._handle_error(context, e, "refine")
            raise
        finally:
            self.pr_manager.manage_labels(context, remove_labels=[IN_PROGRESS_LABEL])

    def _handle_error(
        self, context: PRContext, error: Exception, operation: str
    ) -> None:
        """Handle errors in agent operations."""
        logger.error(
            f"Error in {operation} operation for PR #{context.pr_number}: {error}"
        )
        error_msg = (
            f"❌ An error occurred while performing {operation} on this PR:\n"
            f"```\n{error!s}\n```\n"
            f"Please add the {operation} label again to retry, or contact support "
            "if the issue persists."
        )
        self.pr_manager.post_comment(context, error_msg)
