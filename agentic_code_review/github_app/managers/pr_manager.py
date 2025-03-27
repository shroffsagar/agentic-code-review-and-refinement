"""GitHub PR manager for handling pull request operations.

This module provides functionality for interacting with GitHub pull requests,
including comment management and code analysis.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from github import Github, PullRequest, Repository, PullRequestComment

from ...code_analysis.code_analyzer import CodeAnalyzer
from ...code_analysis.language_config import LanguageRegistry
from ..auth.authenticator import GitHubAuthenticator
from ..models import PRComment, PRContext
from ..constants import IN_PROGRESS_LABEL

logger = logging.getLogger(__name__)


@dataclass
class PRFile:
    """Represents a file in a pull request."""

    filename: str
    patch: str | None
    status: str
    additions: int
    deletions: int
    changes: int
    previous_filename: str | None = None


class PRManager:
    """Manages GitHub pull request operations."""

    def __init__(self, authenticator: GitHubAuthenticator):
        """Initialize the PR manager.

        Args:
            authenticator: The GitHub authenticator to use
        """
        self.authenticator = authenticator
        # We'll get installation-specific clients as needed instead of a global client
        self.language_registry = LanguageRegistry()
        # Cache for installation clients
        self._installation_clients = {}

    def _get_pr(self, context: PRContext) -> PullRequest:
        """Get a pull request by its context.

        Args:
            context: The PR context containing repository and PR number

        Returns:
            The pull request if found, None otherwise
        """
        client = self.authenticator.get_installation_client(context.installation_id)
        repo = client.get_repo(context.repo["full_name"])
        return repo.get_pull(context.pr_number)

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
        pr = self._get_pr(context)
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

    def _convert_to_pr_comment(self, comment: PullRequestComment) -> PRComment:
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

    def post_comment(self, context: PRContext, message: str) -> None:
        """Post a comment on a pull request."""
        try:
            pr = self._get_pr(context)
            pr.create_issue_comment(message)
            logger.info(f"Posted comment on PR #{context.pr_number}")
        except Exception as e:
            logger.error(f"Failed to post comment on PR #{context.pr_number}: {e}")
            raise

    def manage_labels(
        self,
        context: PRContext,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> bool:
        """Manage labels on a pull request.

        Args:
            context: The PR context
            add_labels: List of labels to add
            remove_labels: List of labels to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            pr = self._get_pr(context)
            # Get current labels
            current_labels = {label.name for label in pr.labels}

            # Add new labels
            if add_labels:
                for label in add_labels:
                    if label not in current_labels:
                        pr.add_to_labels(label)

            # Remove specified labels
            if remove_labels:
                for label in remove_labels:
                    if label in current_labels:
                        pr.remove_from_labels(label)

            return True
        except Exception as e:
            logger.error(f"Failed to manage labels: {e}")
            return False

    def is_in_progress(self, context: PRContext) -> bool:
        """Check if a PR is currently being processed.

        Args:
            context: The PR context

        Returns:
            True if the PR is being processed, False otherwise
        """
        try:
            pr = self._get_pr(context)
            # Check for in-progress label
            current_labels = {label.name for label in pr.labels}
            return IN_PROGRESS_LABEL in current_labels
        except Exception as e:
            logger.error(f"Failed to check PR status: {e}")
            return False

    def get_pr_files(self, context: PRContext) -> list[PRFile]:
        """Get all files changed in a pull request.

        Args:
            context: The PR context

        Returns:
            List of PRFile objects representing changed files
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

