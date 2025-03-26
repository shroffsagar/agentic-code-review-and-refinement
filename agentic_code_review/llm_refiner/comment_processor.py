"""Process and group review comments for refinement."""

import logging
from typing import Optional

from ..code_analysis.code_analyzer import CodeAnalyzer, CodeNode
from ..code_analysis.language_config import LanguageRegistry
from ..code_analysis.signature_parser import Signature, SignatureParser
from ..github_app.models import PRComment

logger = logging.getLogger(__name__)


class CommentProcessor:
    """Processes and groups review comments for refinement."""

    def __init__(self):
        """Initialize the comment processor."""
        self.language_registry = LanguageRegistry()
        self.signature_parser = SignatureParser()

    def process_comments(self, comments: list[PRComment]) -> dict[str, list[PRComment]]:
        """Process and group comments by file.

        Args:
            comments: List of comments to process

        Returns:
            Dictionary mapping file paths to their comments
        """
        # Group comments by file
        file_comments: dict[str, list[PRComment]] = {}
        for comment in comments:
            if comment.path not in file_comments:
                file_comments[comment.path] = []
            file_comments[comment.path].append(comment)

        return file_comments

    def group_comments_by_context(self, comments: list[PRComment], code_analyzer: CodeAnalyzer) -> dict[CodeNode, list[PRComment]]:
        """Group comments by their code context.

        Args:
            comments: List of comments to group
            code_analyzer: The code analyzer for node lookup

        Returns:
            Dictionary mapping code nodes to their comments
        """
        grouped: dict[CodeNode, list[PRComment]] = {}

        for comment in comments:
            # Skip comments without node information
            if not comment.node_id or not comment.tree_id:
                logger.warning(f"Comment {comment.id} missing node information")
                continue

            # Find the corresponding node
            node = code_analyzer.find_node_by_id(comment.node_id, comment.tree_id)
            if not node or not node.is_valid():
                logger.warning(f"Invalid node for comment {comment.id}")
                continue

            # Group by the most specific valid node
            target_node = self._find_most_specific_node(node)
            if target_node:
                if target_node not in grouped:
                    grouped[target_node] = []
                grouped[target_node].append(comment)

        return grouped

    def _find_most_specific_node(self, node: CodeNode) -> Optional[CodeNode]:
        """Find the most specific valid node in the hierarchy.

        Args:
            node: The starting node

        Returns:
            The most specific valid node, or None if no valid nodes found
        """
        if not node.is_valid():
            return None

        # If node has no children or no valid children, return this node
        if not node.children or not any(child.is_valid() for child in node.children):
            return node

        # Find the most specific valid child
        valid_children = [child for child in node.children if child.is_valid()]
        if not valid_children:
            return node

        # Recursively find the most specific valid child
        most_specific = None
        for child in valid_children:
            specific = self._find_most_specific_node(child)
            if specific:
                most_specific = specific

        return most_specific or node

    def get_code_context(self, node: CodeNode, code_analyzer: CodeAnalyzer, file_content: str) -> str:
        """Get the code context for a node.

        Args:
            node: The code node
            code_analyzer: The code analyzer
            file_content: The full file content

        Returns:
            String containing the code context
        """
        if not node.is_valid():
            return ""

        # Get the node's text
        node_text = code_analyzer.get_node_text(node)

        # Get the node's path
        node_path = node.get_full_path()

        # Get the node's range
        start_point, end_point = code_analyzer.get_node_range(node)

        return f"""Code Context:
Path: {node_path}
Location: Line {start_point[0] + 1}, Column {start_point[1] + 1} to Line {end_point[0] + 1}, Column {end_point[1] + 1}
Code:
{node_text}"""

    def parse_signature(self, code: str, language: str) -> Optional[Signature]:
        """Parse a function signature from code.

        Args:
            code: The code containing the signature
            language: The programming language

        Returns:
            The parsed signature if successful, None otherwise
        """
        return self.signature_parser.parse_signature(code, language)
