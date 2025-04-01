"""GitHub PR manager for handling pull request operations.

This module provides functionality for interacting with GitHub pull requests,
including comment management and code analysis.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import time

from github import Github, PullRequest, Repository, PullRequestComment

# Remove imports from deprecated code_analysis
# from ...code_analysis.code_analyzer import CodeAnalyzer
# from ...code_analysis.language_config import LanguageRegistry

# Import FileModification from the new location
from ...llm_refiner.models import FileModification

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
        # Remove the language registry initialization as it's no longer needed
        # self.language_registry = LanguageRegistry()
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
            List of unresolved comments
        """
        pr = self._get_pr(context)
        
        # Get all review comments directly from PR and filter unresolved ones
        comments = []
        for comment in pr.get_review_comments():
            if not self._is_comment_resolved_or_rejected(comment):
                comments.append(self._convert_to_pr_comment(comment))

        return comments

    def _is_comment_resolved_or_rejected(self, comment: PullRequestComment) -> bool:
        """Check if a pull request comment is resolved or rejected.
        
        Args:
            comment: The GitHub PullRequestComment object
            
        Returns:
            bool: True if resolved or rejected, False otherwise
        """
        try:
            # Check for thumbs down reaction (rejected by reviewer)
            if any(reaction.content == "-1" for reaction in comment.get_reactions()):
                logger.debug(f"Comment {comment.id} has been rejected (thumbs down)")
                return True
            
            # Check if comment is outdated (position is None indicates resolution)
            if comment.position is None:
                logger.debug(f"Comment {comment.id} appears to be outdated (position is None)")
                return True
            
            # Check for replies that indicate the suggestion was implemented
            for reply in comment.replies:
                if reply.body.strip() == "✅ This suggestion has been implemented":
                    logger.info(f"Comment {comment.id} marked as implemented via reply")
                    return True
                else:
                    logger.debug(f"Reply body: {reply.body}")
            
            return False
        except Exception as e:
            logger.error(f"Error checking comment resolution status: {e}")
            return False  # Default to unresolved for safety

    def _convert_to_pr_comment(self, comment: PullRequestComment) -> PRComment:
        """Convert a GitHub review comment to our PRComment model.

        Args:
            comment: The GitHub review comment

        Returns:
            A PRComment instance
        """
        # Extract category from markdown if present, otherwise use a default
        category = "General"
        if comment.body and comment.body.startswith("#"):
            category = comment.body.split("\n")[0].strip("# ").split(" - ")[0]

        return PRComment(
            id=comment.id,
            body=comment.body,
            path=comment.path,
            line_number=comment.line,
            column_number=1,  # Default to column 1 since GitHub API doesn't provide column info
            category=category,
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
        """Post a general comment on a pull request.
        
        This method is used for posting general PR comments that are not tied to specific code lines.
        For inline code review comments, use post_review_comment instead.

        Args:
            context: The PR context
            message: The comment message
        """
        try:
            pr = self._get_pr(context)
            pr.create_issue_comment(message)
            logger.info(f"Posted general comment on PR #{context.pr_number}")
        except Exception as e:
            logger.error(f"Failed to post comment on PR #{context.pr_number}: {e}")
            raise

    def post_review_comment(
        self,
        context: PRContext,
        file_path: str,
        line_number: int,
        message: str,
        side: Optional[str] = None,
    ) -> None:
        """Post an inline review comment on a specific line of code.

        Args:
            context: The PR context
            file_path: Path to the file being commented on
            line_number: Line number to comment on
            message: The review comment message
            side: Which side of the diff to comment on (optional)
        """
        pr = self._get_pr(context)
        
        # Get the latest commit from the PR
        commits = list(pr.get_commits().reversed)
        if not commits:
            raise ValueError("No commits found in the PR")
        
        commit = commits[0]
        logger.debug(f"Using commit {commit.sha} for review comment")

        # Create a review comment directly on the code line
        pr.create_review_comment(
            body=message,
            commit=commit,
            path=file_path,
            line=line_number
        )
        logger.info(f"Posted review comment on line {line_number} of {file_path}")

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

    def _create_refinement_branch(self, repo: Repository, original_branch: str, original_sha: str) -> Optional[str]:
        """Create a new refinement branch from the original branch.
        
        Args:
            repo: The GitHub repository
            original_branch: Name of the original branch
            original_sha: SHA of the commit to branch from
            
        Returns:
            Name of the new branch if successful, None otherwise
        """
        timestamp = int(time.time())
        refinement_branch = f"{original_branch}-refinement-{timestamp}"
        
        logger.info(f"Creating new refinement branch: {refinement_branch} from {original_branch}")
        
        try:
            # Create a new branch from the original branch's HEAD
            repo.create_git_ref(
                ref=f"refs/heads/{refinement_branch}",
                sha=original_sha
            )
            logger.info(f"Created new branch {refinement_branch} at {original_sha[:7]}")
            return refinement_branch
        except Exception as branch_error:
            logger.error(f"Failed to create new branch: {branch_error}")
            return None
    
    def _update_file_on_branch(self, repo: Repository, file_path: str, 
                             content: str, branch: str, commit_message: str) -> bool:
        """Update or create a file on a specific branch.
        
        Args:
            repo: The GitHub repository
            file_path: Path to the file
            content: New content for the file
            branch: Branch to update
            commit_message: Commit message base
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to get the file to check if it exists
            try:
                file = repo.get_contents(file_path, ref=branch)
                update_message = f"{commit_message} - Update {file_path}"
                logger.info(f"Updating existing file: {file_path}")
                
                # Use update_file if the file exists
                result = repo.update_file(
                    path=file_path,
                    message=update_message,
                    content=content,
                    sha=file.sha,
                    branch=branch
                )
                logger.info(f"Successfully updated {file_path} (commit: {result['commit'].sha[:7]})")
                
            except Exception as not_found_error:
                # If file doesn't exist, create it
                create_message = f"{commit_message} - Create {file_path}"
                logger.info(f"Creating new file: {file_path}")
                
                result = repo.create_file(
                    path=file_path,
                    message=create_message,
                    content=content,
                    branch=branch
                )
                logger.info(f"Successfully created {file_path} (commit: {result['commit'].sha[:7]})")
                
            return True
            
        except Exception as file_error:
            logger.error(f"Failed to update file {file_path}: {file_error}")
            return False
            
    def _create_refinement_pr(self, repo: Repository, context: PRContext, 
                            refinement_branch: str, original_branch: str, 
                            successful_files: List[str]) -> Optional[PullRequest]:
        """Create a pull request with the refinement changes.
        
        Args:
            repo: The GitHub repository
            context: The PR context
            refinement_branch: Name of the branch with changes
            original_branch: Name of the original PR branch
            successful_files: List of successfully modified files
            
        Returns:
            The new PR if created successfully, None otherwise
        """
        refinement_pr_title = f"Automated code refinements for PR #{context.pr_number}"
        refinement_pr_body = f"""
        This PR contains automated code refinements based on review comments.
        
        Original PR: #{context.pr_number}
        Files modified: {', '.join(successful_files)}
        
        These changes were implemented by the automated code refinement system.
        Please review and merge if the changes look good.
        """
        
        try:
            new_pr = repo.create_pull(
                title=refinement_pr_title,
                body=refinement_pr_body,
                head=refinement_branch,
                base=original_branch
            )
            logger.info(f"Created new PR #{new_pr.number} for refinements")
            
            # Add a comment on the original PR
            self.post_comment(
                context,
                f"✅ Created PR #{new_pr.number} with automated code refinements. [View changes]({new_pr.html_url})"
            )
            return new_pr
        except Exception as pr_error:
            logger.error(f"Failed to create refinement PR: {pr_error}")
            return None

    def commit_changes(self, context: PRContext, changes: Dict[str, str], commit_message: str) -> bool:
        """Commit changes to files in a pull request.
        
        This method creates a new branch from the PR's current head branch, 
        applies all changes to that branch, and then creates a new PR to merge 
        the changes back into the original PR branch. This approach preserves 
        the original PR branch while allowing reviewers to see and approve the 
        automated changes.

        Args:
            context: The PR context
            changes: Dictionary mapping file paths to their modified content
            commit_message: The base commit message (will be appended with file info)

        Returns:
            True if all files were successfully committed, False otherwise
        """
        try:
            # Get PR and repository information
            pr = self._get_pr(context)
            repo = pr.base.repo
            original_branch = pr.head.ref
            original_branch_sha = pr.head.sha
            
            # Create a new branch for refinements
            refinement_branch = self._create_refinement_branch(repo, original_branch, original_branch_sha)
            if not refinement_branch:
                return False
            
            # Track file operations
            successful_files = []
            failed_files = []
            
            # Process each file
            for file_path, modified_content in changes.items():
                success = self._update_file_on_branch(
                    repo, file_path, modified_content, refinement_branch, commit_message
                )
                
                if success:
                    successful_files.append(file_path)
                else:
                    failed_files.append(file_path)
            
            # Log summary of operations
            if successful_files:
                logger.info(f"Successfully committed changes to {len(successful_files)} files: {', '.join(successful_files)}")
                
                # Create PR with the changes
                new_pr = self._create_refinement_pr(
                    repo, context, refinement_branch, original_branch, successful_files
                )
                
                # Even if PR creation fails, return success if files were committed
                if not new_pr and len(failed_files) == 0:
                    return True
            
            if failed_files:
                logger.error(f"Failed to commit changes to {len(failed_files)} files: {', '.join(failed_files)}")
                
            # Return success if no files failed
            return len(failed_files) == 0
                
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return False

    def resolve_comments(self, context: PRContext, suggestions: List[Tuple[str, str]]) -> None:
        """Resolve comments for implemented suggestions.
        
        Args:
            context: The PR context
            suggestions: List of tuples containing (suggestion_id, file_path)
        """
        try:
            pr = self._get_pr(context)
            
            for suggestion_id, file_path in suggestions:
                try:
                    # Ensure suggestion_id is an integer for PR API call
                    try:
                        comment_id = int(suggestion_id)
                    except ValueError:
                        logger.error(f"Invalid comment ID format: {suggestion_id}")
                        continue
                    
                    try:
                        # Get the review comment
                        comment = pr.get_review_comment(comment_id)
                        if comment:
                            logger.info(f"Found comment {comment_id} for {file_path}")
                            
                            # Method 1: Use resolve() method if available (GitHub API v4)
                            if hasattr(comment, 'resolve'):
                                try:
                                    comment.resolve()
                                    logger.info(f"Resolved comment {comment_id} using resolve() method")
                                    continue
                                except Exception as resolve_error:
                                    logger.warning(f"Failed to use resolve() method for comment {comment_id}: {resolve_error}")
                                    # Fall through to alternative methods
                            
                            # Method 2: Try different ways to add a reply comment
                            resolution_message = "✅ This suggestion has been implemented."
                            
                            # First try create_review_comment_reply on PR object
                            try:
                                if hasattr(pr, 'create_review_comment_reply'):
                                    pr.create_review_comment_reply(
                                        comment_id=comment_id,
                                        body=resolution_message
                                    )
                                    logger.info(f"Added resolution reply to comment {comment_id} using PR.create_review_comment_reply")
                                    continue
                            except Exception as reply_error1:
                                logger.warning(f"Failed to add reply via PR.create_review_comment_reply: {reply_error1}")
                            
                            # Next try reply() method on comment object
                            try:
                                if hasattr(comment, 'reply'):
                                    comment.reply(resolution_message)
                                    logger.info(f"Added resolution reply to comment {comment_id} using comment.reply")
                                    continue
                            except Exception as reply_error2:
                                logger.warning(f"Failed to add reply via comment.reply: {reply_error2}")
                            
                            # Last try create_reply on comment object
                            try:
                                if hasattr(comment, 'create_reply'):
                                    comment.create_reply(resolution_message)
                                    logger.info(f"Added resolution reply to comment {comment_id} using comment.create_reply")
                                    continue
                            except Exception as reply_error3:
                                logger.warning(f"Failed to add reply via comment.create_reply: {reply_error3}")
                            
                            logger.error(f"No method succeeded in resolving comment {comment_id}")
                        else:
                            logger.warning(f"Comment {comment_id} not found")
                    except Exception as fetch_error:
                        logger.error(f"Failed to fetch comment {comment_id}: {fetch_error}")
                        
                except Exception as e:
                    logger.error(f"Failed to resolve comment {suggestion_id}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to resolve comments: {e}")
            raise

