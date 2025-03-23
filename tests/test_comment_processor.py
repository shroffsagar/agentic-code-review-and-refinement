"""Tests for the comment processor module."""

from unittest.mock import MagicMock

import pytest

from agentic_code_review.github_app.managers.pr_manager import PRComment, PRContext
from agentic_code_review.llm_refiner.comment_processor import CommentProcessor, ProcessedComment

# Constants to avoid magic numbers
LINE_NUMBER_MAIN = 10
LINE_NUMBER_UTILS = 25
COMMENT_COUNT = 2


@pytest.fixture
def pr_context():
    """Fixture for PRContext."""
    return PRContext(
        installation_id=12345,
        repository={"full_name": "test/repo"},
        pr_number=42,
    )


@pytest.fixture
def mock_pr_manager():
    """Fixture for mocked PRManager."""
    manager = MagicMock()
    manager.get_unresolved_comments = MagicMock()
    return manager


@pytest.fixture
def sample_pr_comments():
    """Fixture for sample PR comments."""
    return [
        PRComment(
            id=1,
            body="""Quality Issue - Medium Severity

Location: [src/main.py:10]

Description:
This function could be optimized by using a dictionary instead of a list.

Suggestion:
Replace the list with a dictionary for O(1) lookups.""",
            user_login="bot-user",
            path="src/main.py",
            position=LINE_NUMBER_MAIN,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            is_resolved=False,
        ),
        PRComment(
            id=2,
            body="""Security Issue - High Severity

Location: [src/utils.py:25]

Description:
Missing input validation could lead to SQL injection.

Suggestion:
Add parameterized queries instead of string concatenation.""",
            user_login="bot-user",
            path="src/utils.py",
            position=LINE_NUMBER_UTILS,
            created_at="2023-01-01T12:01:00Z",
            updated_at="2023-01-01T12:01:00Z",
            is_resolved=False,
        ),
        PRComment(
            id=3,
            body="This comment doesn't follow the structured format",  # Malformed comment
            user_login="bot-user",
            path="src/test.py",
            position=5,
            created_at="2023-01-01T12:02:00Z",
            updated_at="2023-01-01T12:02:00Z",
            is_resolved=False,
        ),
    ]


class TestCommentProcessor:
    """Test cases for the CommentProcessor class."""

    def test_parse_comment_body(self):
        """Test parsing structured review comments."""
        processor = CommentProcessor(MagicMock())

        # Test well-formed comment
        comment_body = """Quality Issue - Medium Severity

Location: [src/main.py:10]

Description:
This function could be optimized by using a dictionary instead of a list.

Suggestion:
Replace the list with a dictionary for O(1) lookups."""

        parse_result = processor._parse_comment_body(comment_body)
        category, severity, file_path, line_number, description, suggestion = parse_result

        assert category == "Quality"
        assert severity == "Medium"
        assert file_path == "src/main.py"
        assert line_number == LINE_NUMBER_MAIN
        assert "optimized by using a dictionary" in description
        assert "Replace the list with a dictionary" in suggestion

        # Test malformed comment
        malformed_body = "This is not a properly formatted review comment"

        parse_result = processor._parse_comment_body(malformed_body)
        category, severity, file_path, line_number, description, suggestion = parse_result

        assert category is None
        assert severity is None
        assert file_path is None
        assert line_number is None
        assert description is None
        assert suggestion is None

    @pytest.mark.asyncio
    async def test_get_unresolved_comments(self, pr_context, mock_pr_manager, sample_pr_comments):
        """Test retrieving unresolved comments."""
        # Set up the mock to return our sample comments
        mock_pr_manager.get_unresolved_comments.return_value = sample_pr_comments

        # Create the processor and call the method
        processor = CommentProcessor(mock_pr_manager)
        result = await processor.get_unresolved_comments(pr_context)

        # Verify the mock was called correctly
        mock_pr_manager.get_unresolved_comments.assert_called_once_with(pr_context)

        # Check that we got the right number of processed comments (malformed one should be filtered)
        assert len(result) == COMMENT_COUNT

        # Verify the returned comments are ProcessedComment objects with correctly parsed data
        assert isinstance(result[0], ProcessedComment)
        assert result[0].file_path == "src/main.py"
        assert result[0].line_number == LINE_NUMBER_MAIN
        assert result[0].category == "Quality"
        assert result[0].severity == "Medium"
        assert "optimized by using a dictionary" in result[0].description
        assert "Replace the list with a dictionary" in result[0].suggestion

        assert isinstance(result[1], ProcessedComment)
        assert result[1].file_path == "src/utils.py"
        assert result[1].line_number == LINE_NUMBER_UTILS
        assert result[1].category == "Security"
        assert result[1].severity == "High"
        assert "SQL injection" in result[1].description
        assert "parameterized queries" in result[1].suggestion

    def test_group_comments_by_file(self):
        """Test grouping comments by file."""
        # Create ProcessedComment objects for testing
        comment1 = PRComment(id=1, body="", user_login="", path="", position=None, created_at="", updated_at="", is_resolved=False)
        comment2 = PRComment(id=2, body="", user_login="", path="", position=None, created_at="", updated_at="", is_resolved=False)

        processed_comments = [
            ProcessedComment(
                comment=comment1,
                file_path="src/main.py",
                line_number=LINE_NUMBER_MAIN,
                category="Quality",
                severity="Medium",
                description="Issue 1",
                suggestion="Fix 1",
            ),
            ProcessedComment(
                comment=comment2,
                file_path="src/utils.py",
                line_number=LINE_NUMBER_UTILS,
                category="Security",
                severity="High",
                description="Issue 2",
                suggestion="Fix 2",
            ),
        ]

        # Create processor and group comments
        processor = CommentProcessor(MagicMock())
        result = processor.group_comments_by_file(processed_comments)

        # Check the result has the expected structure
        assert len(result) == COMMENT_COUNT
        assert "src/main.py" in result
        assert "src/utils.py" in result
        assert len(result["src/main.py"]) == 1
        assert len(result["src/utils.py"]) == 1
        assert result["src/main.py"][0].description == "Issue 1"
        assert result["src/utils.py"][0].description == "Issue 2"

    def test_comment_is_actionable(self):
        """Test the is_actionable property of ProcessedComment."""
        # Valid comment with all required fields
        valid_comment = PRComment(id=1, body="", user_login="", path="", position=None, created_at="", updated_at="", is_resolved=False)
        processed_valid = ProcessedComment(
            comment=valid_comment,
            file_path="src/main.py",
            line_number=LINE_NUMBER_MAIN,
            category="Quality",
            severity="Medium",
            description="Issue",
            suggestion="Fix",
        )
        assert processed_valid.is_actionable is True

        # Comment missing suggestion
        missing_suggestion = ProcessedComment(
            comment=valid_comment,
            file_path="src/main.py",
            line_number=LINE_NUMBER_MAIN,
            category="Quality",
            severity="Medium",
            description="Issue",
            suggestion=None,
        )
        assert missing_suggestion.is_actionable is False

        # Comment with empty suggestion
        empty_suggestion = ProcessedComment(
            comment=valid_comment,
            file_path="src/main.py",
            line_number=LINE_NUMBER_MAIN,
            category="Quality",
            severity="Medium",
            description="Issue",
            suggestion="",
        )
        assert empty_suggestion.is_actionable is False

        # Comment missing file path
        missing_file = ProcessedComment(
            comment=valid_comment,
            file_path=None,
            line_number=LINE_NUMBER_MAIN,
            category="Quality",
            severity="Medium",
            description="Issue",
            suggestion="Fix",
        )
        assert missing_file.is_actionable is False

        # Comment missing line number
        missing_line = ProcessedComment(
            comment=valid_comment,
            file_path="src/main.py",
            line_number=None,
            category="Quality",
            severity="Medium",
            description="Issue",
            suggestion="Fix",
        )
        assert missing_line.is_actionable is False
