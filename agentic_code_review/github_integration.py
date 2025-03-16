"""GitHub API integration module for accessing PR content and posting comments.

This module provides functionality to interact with GitHub's API for PR-related
operations such as accessing PR content and posting comments.
"""

import logging

from github import Github
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub's API."""

    def __init__(self, access_token: str) -> None:
        """Initialize the GitHub client.

        Args:
            access_token: GitHub personal access token with repo scope.
        """
        self.client = Github(access_token)
        logger.info("GitHub client initialized successfully")

    def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest | None:
        """Retrieve a pull request by repository name and PR number.

        Args:
            repo_name: Full repository name (e.g., 'owner/repo').
            pr_number: Pull request number.

        Returns:
            PullRequest object if found, None otherwise.
        """
        try:
            repo = self.client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            logger.info(f"Successfully retrieved PR #{pr_number} from {repo_name}")
            return pr
        except Exception as e:
            logger.error(f"Error retrieving PR #{pr_number} from {repo_name}: {e!s}")
            return None

    def post_comment(self, repo_name: str, pr_number: int, comment: str) -> bool:
        """Post a comment on a pull request.

        Args:
            repo_name: Full repository name (e.g., 'owner/repo').
            pr_number: Pull request number.
            comment: Comment text to post.

        Returns:
            bool: True if comment was posted successfully, False otherwise.
        """
        try:
            pr = self.get_pull_request(repo_name, pr_number)
            if pr:
                pr.create_issue_comment(comment)
                logger.info(f"Successfully posted comment on PR #{pr_number}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error posting comment on PR #{pr_number}: {e!s}")
            return False
