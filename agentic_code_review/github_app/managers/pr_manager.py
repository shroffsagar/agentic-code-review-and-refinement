"""Pull request management functionality."""

import logging
from dataclasses import dataclass
from typing import Any, NamedTuple, cast

from github.PullRequest import PullRequest

from ..auth.authenticator import GitHubAuthenticator
from ..constants import IN_PROGRESS_LABEL

logger = logging.getLogger(__name__)


class PRFile(NamedTuple):
    """Represents a file in a pull request."""

    filename: str
    patch: str | None
    status: str  # 'added', 'removed', 'modified', or 'renamed'
    additions: int
    deletions: int
    changes: int
    previous_filename: str | None


@dataclass
class PRContext:
    """Context for PR operations."""

    installation_id: int
    repository: dict[str, Any]
    pr_number: int


@dataclass
class PRComment:
    """Represents a comment in a pull request."""

    id: int
    body: str
    user_login: str
    path: str
    position: int | None  # Can be None for comments not tied to a specific line
    created_at: str
    updated_at: str
    is_resolved: bool


class PRManager:
    """Handles PR-related operations like comments and labels."""

    def __init__(self, authenticator: GitHubAuthenticator) -> None:
        """Initialize the PR manager."""
        self.authenticator = authenticator

    def _get_pr(self, context: PRContext) -> PullRequest:
        """Get a pull request by number.

        Args:
            context: The PR context containing repo and PR information

        Returns:
            The pull request object

        Raises:
            Exception: If there's an error getting the PR
        """
        client = self.authenticator.get_installation_client(context.installation_id)
        repo = client.get_repo(context.repository["full_name"])
        return cast(PullRequest, repo.get_pull(context.pr_number))

    def get_pr_files(self, context: PRContext) -> list[PRFile]:
        """Get the files changed in a pull request.

        This method fetches all files that were modified, added, or deleted in the PR.
        For each file, it includes the patch (diff) if available, along with statistics
        about the changes.

        Args:
            context: The PR context

        Returns:
            A list of PRFile objects containing file changes and metadata

        Raises:
            Exception: If there's an error fetching the PR files
        """
        try:
            pr = self._get_pr(context)
            files = []

            for file in pr.get_files():
                pr_file = PRFile(
                    filename=file.filename,
                    patch=file.patch,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    previous_filename=file.previous_filename if hasattr(file, "previous_filename") else None,
                )
                files.append(pr_file)

            logger.info(f"Fetched {len(files)} files from PR #{context.pr_number}")
            return files
        except Exception as e:
            logger.error(f"Failed to fetch files for PR #{context.pr_number}: {e}")
            raise

    def post_comment(self, context: PRContext, message: str) -> None:
        """Post a comment on a pull request."""
        try:
            pr = self._get_pr(context)
            pr.create_issue_comment(message)
            logger.info(f"Posted comment on PR #{context.pr_number}")
        except Exception as e:
            logger.error(f"Failed to post comment on PR #{context.pr_number}: {e}")
            raise

    def get_unresolved_comments(self, context: PRContext) -> list[PRComment]:
        """Get all unresolved review comments on a pull request.

        This method fetches all review comments and filters out those that have been resolved.

        Args:
            context: The PR context

        Returns:
            A list of PRComment objects representing unresolved comments

        Raises:
            Exception: If there's an error fetching the PR comments
        """
        try:
            pr = self._get_pr(context)
            unresolved_comments = []

            # Get all review comments on the PR
            for comment in pr.get_review_comments():
                # Check if the comment is resolved
                # Note: GitHub API doesn't directly expose resolution status,
                # we'd need to check the review thread or specific markers in the comment body
                # For now, we're treating all comments as unresolved
                is_resolved = False

                # Create a PRComment object
                pr_comment = PRComment(
                    id=comment.id,
                    body=comment.body,
                    user_login=comment.user.login,
                    path=comment.path,
                    position=comment.position,
                    created_at=comment.created_at.isoformat(),
                    updated_at=comment.updated_at.isoformat(),
                    is_resolved=is_resolved,
                )

                if not is_resolved:
                    unresolved_comments.append(pr_comment)

            logger.info(f"Fetched {len(unresolved_comments)} unresolved comments from PR #{context.pr_number}")
            return unresolved_comments
        except Exception as e:
            logger.error(f"Failed to fetch comments for PR #{context.pr_number}: {e}")
            raise

    def manage_labels(
        self,
        context: PRContext,
        *,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> None:
        """Manage labels on a PR."""
        pr = self._get_pr(context)

        if add_labels:
            pr.add_to_labels(*add_labels)
        if remove_labels:
            pr.remove_from_labels(*remove_labels)

    def is_in_progress(self, context: PRContext) -> bool:
        """Check if a PR is currently being processed."""
        pr = self._get_pr(context)
        return any(label.name == IN_PROGRESS_LABEL for label in pr.labels)
