"""Pull request management functionality."""

import logging
from dataclasses import dataclass
from typing import Any

from ..auth.authenticator import GitHubAuthenticator
from ..constants import IN_PROGRESS_LABEL

logger = logging.getLogger(__name__)


@dataclass
class PRContext:
    """Context for PR operations."""

    installation_id: int
    repository: dict[str, Any]
    pr_number: int


class PRManager:
    """Handles PR-related operations like comments and labels."""

    def __init__(self, authenticator: GitHubAuthenticator) -> None:
        self.authenticator = authenticator

    def post_comment(self, context: PRContext, message: str) -> None:
        """Post a comment on a pull request."""
        try:
            client = self.authenticator.get_installation_client(context.installation_id)
            repo = client.get_repo(context.repository["full_name"])
            pr = repo.get_pull(context.pr_number)
            pr.create_issue_comment(message)
            logger.info(f"Posted comment on PR #{context.pr_number}")
        except Exception as e:
            logger.error(f"Failed to post comment on PR #{context.pr_number}: {e}")
            raise

    def manage_labels(
        self,
        context: PRContext,
        *,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> None:
        """Manage labels on a PR."""
        client = self.authenticator.get_installation_client(context.installation_id)
        repo = client.get_repo(context.repository["full_name"])
        pr = repo.get_pull(context.pr_number)

        if add_labels:
            pr.add_to_labels(*add_labels)
        if remove_labels:
            pr.remove_from_labels(*remove_labels)

    def is_in_progress(self, context: PRContext) -> bool:
        """Check if a PR is currently being processed."""
        client = self.authenticator.get_installation_client(context.installation_id)
        repo = client.get_repo(context.repository["full_name"])
        pr = repo.get_pull(context.pr_number)
        return any(label.name == IN_PROGRESS_LABEL for label in pr.labels)
