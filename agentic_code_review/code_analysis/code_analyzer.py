"""Code analysis manager using tree-sitter.

This module provides functionality for analyzing code using tree-sitter,
enabling efficient code structure analysis and position tracking.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from tree_sitter import Language, Node, Parser, Tree

logger = logging.getLogger(__name__)


@dataclass
class CodeNode:
    """Represents a node in the code tree with its relationships and metadata."""

    node: Node
    node_type: str
    name: Optional[str] = None
    start_point: tuple[int, int] = (0, 0)
    end_point: tuple[int, int] = (0, 0)
    parent: Optional["CodeNode"] = None
    children: list["CodeNode"] = None
    # Add tree-sitter specific fields
    node_id: int = 0  # tree-sitter's internal node ID
    tree_id: int = 0  # tree-sitter's tree ID for change tracking

    def __post_init__(self):
        """Initialize collections after dataclass initialization."""
        self.children = self.children or []
        # Store tree-sitter's native IDs
        self.node_id = self.node.id
        self.tree_id = self.node.tree.id

    def is_valid(self) -> bool:
        """Check if the node is still valid in the current tree.

        Returns:
            True if the node is valid, False otherwise
        """
        try:
            # Check if node exists in current tree
            if not self.node or not self.node.tree:
                return False

            # Check if node's parent chain is valid
            current = self.node
            while current.parent:
                if not current.parent.is_valid():
                    return False
                current = current.parent

            # Verify node's position is within tree bounds
            tree_size = len(self.node.tree.root_node.text)
            if self.node.start_byte >= tree_size or self.node.end_byte > tree_size:
                return False

            return True
        except Exception as e:
            logger.error(f"Node validation error: {e}")
            return False

    def get_full_path(self) -> str:
        """Get the full path from root to this node.

        Returns:
            String representing the node's path in the tree
        """
        path = []
        current = self
        while current:
            if current.name:
                path.append(f"{current.node_type}:{current.name}")
            else:
                path.append(current.node_type)
            current = current.parent
        return " > ".join(reversed(path))


class CodeAnalyzer:
    """Manages code analysis using tree-sitter."""

    def __init__(self, language: Language):
        """Initialize the code analyzer with a tree-sitter language.

        Args:
            language: The tree-sitter language to use for parsing
        """
        self.language = language
        self.parser = Parser()
        self.parser.set_language(language)
        self.node_mapping: dict[Node, CodeNode] = {}
        self.id_mapping: dict[tuple[int, int], CodeNode] = {}  # (node_id, tree_id) -> CodeNode
        self.current_tree_id: Optional[int] = None

    def parse_code(self, code: str) -> None:
        """Parse code and create the tree representation.

        Args:
            code: The source code to parse
        """
        tree = self.parser.parse(bytes(code, "utf-8"))
        self.current_tree_id = tree.id
        self._build_tree(tree)

    def _build_tree(self, tree: Tree) -> None:
        """Build the tree representation from a syntax tree.

        Args:
            tree: The syntax tree to build the tree from
        """
        self.node_mapping.clear()
        self.id_mapping.clear()
        self._create_nodes(tree.root_node)

    def _create_nodes(self, node: Node) -> None:
        """Create CodeNode objects for each node in the tree.

        Args:
            node: The current node to process
        """
        code_node = CodeNode(node=node, node_type=node.type, start_point=node.start_point, end_point=node.end_point, name=self._get_node_name(node))
        self.node_mapping[node] = code_node
        self.id_mapping[(code_node.node_id, code_node.tree_id)] = code_node

        # Set parent-child relationships
        for child in node.children:
            child_code_node = CodeNode(
                node=child, node_type=child.type, start_point=child.start_point, end_point=child.end_point, name=self._get_node_name(child), parent=code_node
            )
            code_node.children.append(child_code_node)
            self.node_mapping[child] = child_code_node
            self.id_mapping[(child_code_node.node_id, child_code_node.tree_id)] = child_code_node
            self._create_nodes(child)

    def _get_node_name(self, node: Node) -> Optional[str]:
        """Extract a meaningful name for a node if applicable.

        Args:
            node: The node to get the name for

        Returns:
            The node's name if it has one, None otherwise
        """
        if node.type in ["function_definition", "method_definition", "class_definition"]:
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8")
        return None

    def find_node_by_id(self, node_id: int, tree_id: int) -> Optional[CodeNode]:
        """Find a node by its ID and tree ID.

        Args:
            node_id: The node's ID
            tree_id: The tree's ID

        Returns:
            The node if found, None otherwise
        """
        return self.id_mapping.get((node_id, tree_id))

    def find_node_at_position(self, line: int, column: int) -> Optional[CodeNode]:
        """Find the most specific node at a given position.

        Args:
            line: The line number (0-based)
            column: The column number (0-based)

        Returns:
            The most specific node at the position, or None if not found
        """
        position = (line, column)
        matching_nodes = []

        for code_node in self.node_mapping.values():
            if not code_node.is_valid():
                continue
            if code_node.start_point <= position <= code_node.end_point:
                matching_nodes.append(code_node)

        if not matching_nodes:
            return None

        # Return the most specific (smallest) node
        return min(matching_nodes, key=lambda n: n.end_point[0] - n.start_point[0])

    def get_node_context(self, node: CodeNode) -> list[CodeNode]:
        """Get the context of a node (parent chain).

        Args:
            node: The node to get context for

        Returns:
            List of nodes from root to the given node
        """
        if not node.is_valid():
            return []

        context = []
        current = node
        while current:
            context.append(current)
            current = current.parent
        return list(reversed(context))

    def get_node_text(self, node: CodeNode) -> str:
        """Get the text content of a node.

        Args:
            node: The node to get text for

        Returns:
            The text content of the node
        """
        if not node.is_valid():
            return ""
        return node.node.text.decode("utf-8")

    def get_node_range(self, node: CodeNode) -> tuple[tuple[int, int], tuple[int, int]]:
        """Get the line and column range of a node.

        Args:
            node: The node to get range for

        Returns:
            Tuple of (start_point, end_point) where each point is (line, column)
        """
        if not node.is_valid():
            return ((0, 0), (0, 0))
        return node.start_point, node.end_point

    def validate_changes(self, modified_code: str) -> bool:
        """Validate that modified code can be parsed correctly.

        Args:
            modified_code: The modified code to validate

        Returns:
            True if the code is valid, False otherwise
        """
        try:
            # Try to parse the modified code
            tree = self.parser.parse(bytes(modified_code, "utf-8"))
            return tree.root_node is not None
        except Exception as e:
            logger.error(f"Code validation error: {e}")
            return False
