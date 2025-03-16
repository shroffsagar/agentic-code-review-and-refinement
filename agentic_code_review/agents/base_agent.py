"""Base agent implementation with GPT-4 integration.

This module provides the base agent class that handles interactions with
OpenAI's GPT-4 model and GitHub.
"""

import logging

from openai import OpenAI  # type: ignore

from agentic_code_review.github_integration import GitHubClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base agent class with GPT-4 and GitHub integration."""

    def __init__(
        self,
        github_token: str,
        openai_api_key: str,
        repo_name: str,
        pr_number: int,
    ) -> None:
        """Initialize the base agent.

        Args:
            github_token: GitHub personal access token.
            openai_api_key: OpenAI API key.
            repo_name: Full repository name (e.g., 'owner/repo').
            pr_number: Pull request number.
        """
        self.github_client = GitHubClient(github_token)
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.repo_name = repo_name
        self.pr_number = pr_number
        logger.info(f"Base agent initialized for PR #{pr_number}")

    def get_pr_content(self) -> str | None:
        """Retrieve the content of the pull request.

        Returns:
            str: PR content if successful, None otherwise.
        """
        try:
            pr = self.github_client.get_pull_request(self.repo_name, self.pr_number)
            if pr:
                return f"Title: {pr.title}\n\nDescription:\n{pr.body}"
            return None
        except Exception as e:
            logger.error(f"Error retrieving PR content: {e!s}")
            return None

    def call_gpt4(self, prompt: str) -> str | None:
        """Call GPT-4 with a prompt and return the response.

        Args:
            prompt: The prompt to send to GPT-4.

        Returns:
            The response text from GPT-4, or None if the call fails.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            content: str | None = response.choices[0].message.content
            return content
        except Exception as e:
            logger.error(f"Error calling GPT-4: {e!s}")
            return None

    def post_comment(self, comment: str) -> bool:
        """Post a comment on the pull request.

        Args:
            comment: The comment text to post.

        Returns:
            bool: True if comment was posted successfully, False otherwise.
        """
        return self.github_client.post_comment(self.repo_name, self.pr_number, comment)
