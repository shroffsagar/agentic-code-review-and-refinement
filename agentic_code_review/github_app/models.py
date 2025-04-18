"""Models for GitHub integration.

This module contains data models used throughout the GitHub integration.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PRContext:
    """Context for PR operations."""

    repo: dict[str, Any]
    pr_number: int
    installation_id: int


@dataclass
class PRComment:
    """Represents a review comment on a pull request."""

    id: str
    path: str
    line_number: int  # Keep for display purposes
    column_number: int  # Keep for display purposes
    body: str
    category: str
    code_context: Optional[str] = None
    # Replace line-based tracking with node-based tracking
    node_id: Optional[int] = None  # tree-sitter's node ID
    tree_id: Optional[int] = None  # tree-sitter's tree ID
    node_type: Optional[str] = None  # Type of code node
    node_name: Optional[str] = None  # Name of code node if applicable


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
