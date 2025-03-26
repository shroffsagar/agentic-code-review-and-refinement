"""GitHub PR manager for handling pull request operations.

This module provides functionality for interacting with GitHub pull requests,
including comment management and code analysis.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from github import Github, PullRequest, Repository
from github.PullRequestReviewComment import PullRequestReviewComment

from ..code_analysis.code_analyzer import CodeAnalyzer
from ..code_analysis.language_config import LanguageRegistry
from ..github_app.authenticator import GitHubAuthenticator
from ..github_app.models import PRComment, PRContext

logger = logging.getLogger(__name__)


@dataclass
class PRFile:
    """Represents a file in a pull request."""

    path: str
    content: str
    code_analyzer: Optional[CodeAnalyzer] = None


class PRManager:
    """Manages GitHub pull request operations."""

    def __init__(self, authenticator: GitHubAuthenticator):
        """Initialize the PR manager.

        Args:
            authenticator: The GitHub authenticator to use
        """
        self.authenticator = authenticator
        self.github = Github(authenticator.get_token())
        self.language_registry = LanguageRegistry()

    def get_pr(self, context: PRContext) -> Optional[PullRequest]:
        """Get a pull request by its context.

        Args:
            context: The PR context containing repository and PR number

        Returns:
            The pull request if found, None otherwise
        """
        try:
            repo = self.github.get_repo(context.repo)
            return repo.get_pull(context.pr_number)
        except Exception as e:
            logger.error(f"Failed to get PR #{context.pr_number}: {e}")
            return None

    def get_file_content(self, repo: Repository, path: str, ref: str) -> Optional[str]:
        """Get the content of a file at a specific reference.

        Args:
            repo: The GitHub repository
            path: The path to the file
            ref: The git reference (branch, commit, etc.)

        Returns:
            The file content if found, None otherwise
        """
        try:
            contents = repo.get_contents(path, ref=ref)
            if contents.type == "file":
                return contents.decoded_content.decode("utf-8")
            logger.error(f"Path {path} is not a file")
            return None
        except Exception as e:
            logger.error(f"Failed to get content of {path}: {e}")
            return None

    def get_unresolved_comments(self, context: PRContext) -> list[PRComment]:
        """Get all unresolved review comments on a pull request.

        Args:
            context: The PR context

        Returns:
            List of unresolved comments with their code context
        """
        pr = self.get_pr(context)
        if not pr:
            return []

        # Get all review comments
        comments = []
        for review in pr.get_reviews():
            for comment in review.get_comments():
                if not comment.is_resolved():
                    comments.append(self._convert_to_pr_comment(comment))

        # Group comments by file
        file_comments: dict[str, list[PRComment]] = {}
        for comment in comments:
            if comment.path not in file_comments:
                file_comments[comment.path] = []
            file_comments[comment.path].append(comment)

        # Process each file's comments
        processed_comments = []
        for file_path, file_comment_list in file_comments.items():
            # Get file content
            content = self.get_file_content(pr.base.repo, file_path, pr.base.sha)
            if not content:
                logger.error(f"Failed to get content for {file_path}")
                continue

            # Get language and create code analyzer
            language = self.language_registry.get_language_for_file(file_path)
            if not language:
                logger.error(f"Unsupported file type: {file_path}")
                continue

            lang = self.language_registry.get_language(language)
            if not lang:
                logger.error(f"Failed to load language for {file_path}")
                continue

            # Create code analyzer and parse code
            code_analyzer = CodeAnalyzer(lang)
            code_analyzer.parse_code(content)

            # Process comments for this file
            for comment in file_comment_list:
                try:
                    # Find the code node at the comment's position
                    code_node = code_analyzer.find_node_at_position(
                        comment.line_number - 1,  # Convert to 0-based
                        comment.column_number - 1,
                    )

                    if code_node:
                        # Store node-based tracking information
                        comment.node_id = code_node.node_id
                        comment.tree_id = code_node.tree_id
                        comment.node_type = code_node.node_type
                        comment.node_name = code_node.name

                        # Get the context (parent chain)
                        context_nodes = code_analyzer.get_node_context(code_node)
                        comment.code_context = self._get_code_context(context_nodes, content)
                    else:
                        comment.code_context = None

                    processed_comments.append(comment)
                except Exception as e:
                    logger.error(f"Failed to process comment {comment.id}: {e}")
                    processed_comments.append(comment)

        return processed_comments

    def _convert_to_pr_comment(self, comment: PullRequestReviewComment) -> PRComment:
        """Convert a GitHub review comment to our PRComment model.

        Args:
            comment: The GitHub review comment

        Returns:
            A PRComment instance
        """
        return PRComment(
            id=comment.id,
            body=comment.body,
            path=comment.path,
            line_number=comment.line,
            column_number=comment.column or 1,
            commit_id=comment.commit_id,
            user=comment.user.login,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            is_resolved=comment.is_resolved(),
            code_context=None,  # Will be populated later
        )

    def _get_code_context(self, context_nodes: list["CodeNode"], content: str) -> str:
        """Get the code context from a list of context nodes.

        Args:
            context_nodes: List of nodes in the context chain
            content: The full file content

        Returns:
            A string representation of the code context
        """
        if not context_nodes:
            return ""

        # Get the code for each node in the context
        context_parts = []
        for node in context_nodes:
            if node.name:
                context_parts.append(f"{node.node_type}: {node.name}")
            else:
                context_parts.append(node.node_type)

        return " > ".join(context_parts)

    def post_comment(
        self,
        context: PRContext,
        file_path: str,
        line_number: int,
        body: str,
        commit_id: Optional[str] = None,
    ) -> Optional[PRComment]:
        """Post a new review comment on a pull request.

        Args:
            context: The PR context
            file_path: The path to the file
            line_number: The line number to comment on
            body: The comment body
            commit_id: The commit ID to comment on

        Returns:
            The posted comment if successful, None otherwise
        """
        pr = self.get_pr(context)
        if not pr:
            return None

        try:
            # Use the latest commit if none specified
            if not commit_id:
                commit_id = pr.get_commits().reversed[0].sha

            # Create the review comment
            review = pr.create_review(
                body="Code Review",
                event="COMMENT",
                commit_id=commit_id,
            )

            # Add the comment
            comment = review.create_comment(
                body=body,
                path=file_path,
                line=line_number,
                side="RIGHT",
            )

            return self._convert_to_pr_comment(comment)
        except Exception as e:
            logger.error(f"Failed to post comment: {e}")
            return None

    def manage_labels(self, context: PRContext, labels: set[str]) -> bool:
        """Manage labels on a pull request.

        Args:
            context: The PR context
            labels: Set of labels to apply

        Returns:
            True if successful, False otherwise
        """
        pr = self.get_pr(context)
        if not pr:
            return False

        try:
            # Get current labels
            current_labels = {label.name for label in pr.labels}

            # Add new labels
            for label in labels:
                if label not in current_labels:
                    pr.add_to_labels(label)

            # Remove labels that are no longer needed
            for label in current_labels:
                if label not in labels:
                    pr.remove_from_labels(label)

            return True
        except Exception as e:
            logger.error(f"Failed to manage labels: {e}")
            return False
