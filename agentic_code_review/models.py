"""Common data models for the Agentic Code Review system."""

from dataclasses import dataclass, field

from .github_app.models import PRFile
from .llm_refiner.models import CodeDiffUnit


@dataclass
class FileToReview:
    """Represents a file that needs to be reviewed with its context.

    This class is used throughout the system to represent files that need review,
    whether they come from GitHub PRs or other sources. It contains all necessary
    information for both GitHub operations and LLM review.
    """

    file: PRFile  # The GitHub PR file object
    content: str | None = None  # Full file content if needed
    is_test_file: bool = False  # Whether this is a test file
    additional_context: str | None = None  # Any extra context for the LLM
    code_diff_units: list[CodeDiffUnit] = field(default_factory=list)  # Code diff units extracted from the PR file

    @property
    def file_path(self) -> str:
        """Get the file path from the PR file object."""
        return self.file.filename

    @property
    def code_diff(self) -> str:
        """Get the code diff from the PR file object."""
        return self.file.patch or ""
