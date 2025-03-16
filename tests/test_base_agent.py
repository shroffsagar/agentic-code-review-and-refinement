"""Tests for the base agent implementation."""

from unittest.mock import MagicMock, patch

import pytest
from github.PullRequest import PullRequest

from agentic_code_review.agents.base_agent import BaseAgent


@pytest.fixture
def base_agent() -> BaseAgent:
    """Create a base agent with mock credentials."""
    # pragma: allowlist secret
    return BaseAgent(
        github_token="mock_github_token",  # pragma: allowlist secret
        openai_api_key="mock_openai_key",  # pragma: allowlist secret
        repo_name="owner/repo",
        pr_number=1,
    )


@patch("agentic_code_review.agents.base_agent.GitHubClient")
def test_base_agent_initialization(
    mock_github_client: MagicMock,
    base_agent: BaseAgent,
) -> None:
    """Test base agent initialization."""
    assert base_agent.github_client is not None
    assert base_agent.openai_client is not None
    assert base_agent.repo_name == "owner/repo"
    assert base_agent.pr_number == 1


@patch("agentic_code_review.agents.base_agent.GitHubClient")
def test_get_pr_content_success(
    mock_github_client: MagicMock,
    base_agent: BaseAgent,
) -> None:
    """Test successful PR content retrieval."""
    # Setup mock
    mock_pr = MagicMock(spec=PullRequest)
    mock_pr.title = "Test PR"
    mock_pr.body = "Test Description"
    mock_github_client.return_value.get_pull_request.return_value = mock_pr

    # Test
    with patch.object(base_agent, "github_client", mock_github_client.return_value):
        content = base_agent.get_pr_content()
        assert content is not None
        assert content["title"] == "Test PR"
        assert content["body"] == "Test Description"


@patch("agentic_code_review.agents.base_agent.GitHubClient")
def test_get_pr_content_failure(
    mock_github_client: MagicMock,
    base_agent: BaseAgent,
) -> None:
    """Test failed PR content retrieval."""
    # Setup mock to return None
    mock_github_client.return_value.get_pull_request.return_value = None

    # Test
    with patch.object(base_agent, "github_client", mock_github_client.return_value):
        content = base_agent.get_pr_content()
        assert content is None


@patch("openai.OpenAI")
def test_call_gpt4_success(mock_openai: MagicMock, base_agent: BaseAgent) -> None:
    """Test successful GPT-4 API call."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    # Test
    with patch.object(base_agent, "openai_client", mock_openai.return_value):
        response = base_agent.call_gpt4("Test prompt")
        assert response is not None
        assert response == "Test response"


@patch("openai.OpenAI")
def test_call_gpt4_failure(mock_openai: MagicMock, base_agent: BaseAgent) -> None:
    """Test failed GPT-4 API call."""
    # Setup mock to raise an exception
    err = Exception("API Error")
    mock_openai.return_value.chat.completions.create.side_effect = err

    # Test
    with patch.object(base_agent, "openai_client", mock_openai.return_value):
        response = base_agent.call_gpt4("Test prompt")
        assert response is None


@patch("agentic_code_review.agents.base_agent.GitHubClient")
def test_post_comment_success(
    mock_github_client: MagicMock,
    base_agent: BaseAgent,
) -> None:
    """Test successful comment posting."""
    # Setup mock
    mock_github_client.return_value.post_comment.return_value = True

    # Test
    with patch.object(base_agent, "github_client", mock_github_client.return_value):
        success = base_agent.post_comment("Test comment")
        assert success is True


@patch("agentic_code_review.agents.base_agent.GitHubClient")
def test_post_comment_failure(
    mock_github_client: MagicMock,
    base_agent: BaseAgent,
) -> None:
    """Test failed comment posting."""
    # Setup mock
    mock_github_client.return_value.post_comment.return_value = False

    # Test
    with patch.object(base_agent, "github_client", mock_github_client.return_value):
        success = base_agent.post_comment("Test comment")
        assert success is False
