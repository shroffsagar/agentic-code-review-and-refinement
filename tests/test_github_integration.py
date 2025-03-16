"""Tests for the GitHub integration module."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_code_review.github_integration import GitHubClient


@pytest.fixture
def github_client() -> GitHubClient:
    """Create a GitHub client with a mock token."""
    return GitHubClient("mock_token")


def test_github_client_initialization(github_client: GitHubClient) -> None:
    """Test GitHub client initialization."""
    assert github_client.client is not None


@patch("github.Github")
def test_get_pull_request_success(
    mock_github: MagicMock,
    github_client: GitHubClient,
) -> None:
    """Test successful PR retrieval."""
    # Setup mock
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.title = "Test PR"
    mock_pr.body = "Test Description"
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo

    # Test
    with patch.object(github_client, "client", mock_github.return_value):
        pr = github_client.get_pull_request("owner/repo", 1)
        assert pr is not None
        assert pr.title == "Test PR"
        assert pr.body == "Test Description"


@patch("github.Github")
def test_get_pull_request_failure(
    mock_github: MagicMock,
    github_client: GitHubClient,
) -> None:
    """Test failed PR retrieval."""
    # Setup mock to raise an exception
    mock_github.return_value.get_repo.side_effect = Exception("API Error")

    # Test
    with patch.object(github_client, "client", mock_github.return_value):
        pr = github_client.get_pull_request("owner/repo", 1)
        assert pr is None


@patch("github.Github")
def test_post_comment_success(
    mock_github: MagicMock,
    github_client: GitHubClient,
) -> None:
    """Test successful comment posting."""
    # Setup mock
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo

    # Test
    with patch.object(github_client, "client", mock_github.return_value):
        success = github_client.post_comment("owner/repo", 1, "Test comment")
        assert success is True
        mock_pr.create_issue_comment.assert_called_once_with("Test comment")


@patch("github.Github")
def test_post_comment_failure(
    mock_github: MagicMock,
    github_client: GitHubClient,
) -> None:
    """Test failed comment posting."""
    # Setup mock to raise an exception
    mock_github.return_value.get_repo.side_effect = Exception("API Error")

    # Test
    with patch.object(github_client, "client", mock_github.return_value):
        success = github_client.post_comment("owner/repo", 1, "Test comment")
        assert success is False
