"""Comment processor for the refinement agent.

This module handles the retrieval and processing of unresolved review comments,
preparing them for the code refinement process.
"""

import logging
import re
from dataclasses import dataclass

from ..github_app.managers.pr_manager import PRComment, PRContext, PRManager

logger = logging.getLogger(__name__)


@dataclass
class ProcessedComment:
    """A processed review comment ready for refinement.

    This class contains the original PR comment along with additional context
    and processing information needed for refinement.
    """

    comment: PRComment
    file_path: str
    line_number: int | None
    category: str | None = None
    severity: str | None = None
    description: str | None = None
    suggestion: str | None = None

    @property
    def is_actionable(self) -> bool:
        """Determine if this comment contains an actionable suggestion."""
        return self.suggestion is not None and len(self.suggestion.strip()) > 0 and self.file_path is not None and self.line_number is not None


class CommentProcessor:
    """Processes PR comments to prepare them for code refinement."""

    # Regular expressions for parsing review comment format
    CATEGORY_SEVERITY_PATTERN = re.compile(r"(Quality|Performance|Security|Testing|Maintainability|Coverage) Issue - (High|Medium|Low) Severity")
    LOCATION_PATTERN = re.compile(r"Location: \[([^:\]]+):(\d+)\]")
    DESCRIPTION_PATTERN = re.compile(r"Description:\s*(.*?)(?=\n\nSuggestion:|\Z)", re.DOTALL)
    SUGGESTION_PATTERN = re.compile(r"Suggestion:\s*(.*?)(?=\Z)", re.DOTALL)

    def __init__(self, pr_manager: PRManager) -> None:
        """Initialize the comment processor.

        Args:
            pr_manager: The PR manager to use for fetching comments
        """
        self.pr_manager = pr_manager

    def _parse_comment_body(self, body: str) -> tuple[str | None, str | None, str | None, int | None, str | None, str | None]:
        """Parse a review comment body to extract structured information.

        Args:
            body: The comment body text

        Returns:
            A tuple containing (category, severity, file_path, line_number, description, suggestion)
        """
        # Default values
        category = None
        severity = None
        file_path = None
        line_number = None
        description = None
        suggestion = None

        # Extract category and severity
        category_severity_match = self.CATEGORY_SEVERITY_PATTERN.search(body)
        if category_severity_match:
            category = category_severity_match.group(1)
            severity = category_severity_match.group(2)

        # Extract location (file path and line number)
        location_match = self.LOCATION_PATTERN.search(body)
        if location_match:
            file_path = location_match.group(1)
            try:
                line_number = int(location_match.group(2))
            except ValueError:
                logger.warning(f"Failed to parse line number from: {location_match.group(2)}")

        # Extract description
        description_match = self.DESCRIPTION_PATTERN.search(body)
        if description_match:
            description = description_match.group(1).strip()

        # Extract suggestion
        suggestion_match = self.SUGGESTION_PATTERN.search(body)
        if suggestion_match:
            suggestion = suggestion_match.group(1).strip()

        return category, severity, file_path, line_number, description, suggestion

    async def get_unresolved_comments(self, context: PRContext) -> list[ProcessedComment]:
        """Retrieve and process all unresolved comments from a PR.

        Args:
            context: The PR context

        Returns:
            A list of processed comments ready for refinement

        Raises:
            Exception: If there's an error processing the comments
        """
        try:
            # Get raw comments from PR
            raw_comments = self.pr_manager.get_unresolved_comments(context)
            logger.info(f"Retrieved {len(raw_comments)} unresolved comments from PR #{context.pr_number}")

            # Process each comment
            processed_comments = []
            for comment in raw_comments:
                # Parse the structured comment body
                category, severity, file_path, line_number, description, suggestion = self._parse_comment_body(comment.body)

                # Use the parsed file path and line number if available, otherwise fall back to GitHub's data
                file_path = file_path or comment.path
                line_number = line_number or comment.position

                processed = ProcessedComment(
                    comment=comment,
                    file_path=file_path,
                    line_number=line_number,
                    category=category,
                    severity=severity,
                    description=description,
                    suggestion=suggestion,
                )

                if processed.is_actionable:
                    processed_comments.append(processed)

            logger.info(f"Processed {len(processed_comments)} actionable comments from PR #{context.pr_number}")
            return processed_comments

        except Exception as e:
            logger.error(f"Error processing comments for PR #{context.pr_number}: {e}")
            raise

    def group_comments_by_file(self, comments: list[ProcessedComment]) -> dict[str, list[ProcessedComment]]:
        """Group comments by the file they apply to.

        Args:
            comments: The list of processed comments to group

        Returns:
            A dictionary mapping file paths to lists of comments
        """
        result: dict[str, list[ProcessedComment]] = {}

        for comment in comments:
            if comment.file_path not in result:
                result[comment.file_path] = []
            result[comment.file_path].append(comment)

        logger.info(f"Grouped comments into {len(result)} files")
        return result
