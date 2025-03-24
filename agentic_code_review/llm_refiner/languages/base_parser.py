"""Base parser interface for Tree-sitter language integration.

This module defines the abstract base class that all language-specific parsers must implement.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Optional

from tree_sitter import Node, Tree


class SyntaxNodeType(Enum):
    """Enumeration of common syntax node types across languages."""

    FUNCTION = auto()
    METHOD = auto()
    CLASS = auto()
    MODULE = auto()
    IMPORT = auto()
    VARIABLE = auto()
    STATEMENT = auto()
    BLOCK = auto()
    PARAMETER = auto()
    EXPRESSION = auto()
    OTHER = auto()


class SyntaxNode:
    """Representation of a syntax node in the source code."""

    def __init__(
        self,
        node_type: SyntaxNodeType,
        name: str,
        start_point: tuple[int, int],
        end_point: tuple[int, int],
        start_byte: int,
        end_byte: int,
        children: Optional[list["SyntaxNode"]] = None,
        raw_node: Optional[Node] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize a syntax node.

        Args:
            node_type: Type of the syntax node
            name: Name of the node (e.g., function name, class name)
            start_point: Starting position as (line, column)
            end_point: Ending position as (line, column)
            start_byte: Starting byte position in the source
            end_byte: Ending byte position in the source
            children: List of child nodes
            raw_node: The original Tree-sitter node
            metadata: Additional language-specific metadata
        """
        self.node_type = node_type
        self.name = name
        self.start_point = start_point
        self.end_point = end_point
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.children = children or []
        self.raw_node = raw_node
        self.metadata = metadata or {}

    def contains_position(self, line: int, col: int) -> bool:
        """Check if this node contains the given position.

        Args:
            line: Line number (0-indexed)
            col: Column number (0-indexed)

        Returns:
            True if the position is within this node's range
        """
        if line < self.start_point[0] or line > self.end_point[0]:
            return False

        if line == self.start_point[0] and col < self.start_point[1]:
            return False

        if line == self.end_point[0] and col > self.end_point[1]:
            return False

        return True

    def find_node_at_position(self, line: int, col: int) -> Optional["SyntaxNode"]:
        """Find the deepest node that contains the given position.

        Args:
            line: Line number (0-indexed)
            col: Column number (0-indexed)

        Returns:
            The node containing the position, or None if not found
        """
        if not self.contains_position(line, col):
            return None

        # Check children first to find the deepest node
        for child in self.children:
            node = child.find_node_at_position(line, col)
            if node:
                return node

        # If no child contains the position, return self
        return self


class BaseParser(ABC):
    """Abstract base class for language-specific parsers."""

    @abstractmethod
    def setup_parser(self) -> None:
        """Set up the Tree-sitter parser for the specific language."""
        pass

    @abstractmethod
    def parse_code(self, code: str) -> Tree:
        """Parse code string into a Tree-sitter syntax tree.

        Args:
            code: Source code string

        Returns:
            Tree-sitter syntax tree
        """
        pass

    @abstractmethod
    def extract_syntax_tree(self, code: str) -> SyntaxNode:
        """Extract a structured syntax tree from code.

        Args:
            code: Source code string

        Returns:
            Root SyntaxNode containing the hierarchical structure
        """
        pass

    @abstractmethod
    def find_node_at_position(self, code: str, line: int, col: int) -> Optional[SyntaxNode]:
        """Find the syntax node at the given position.

        Args:
            code: Source code string
            line: Line number (0-indexed)
            col: Column number (0-indexed)

        Returns:
            SyntaxNode at the position, or None if not found
        """
        pass

    @abstractmethod
    def get_function_signature(self, node: SyntaxNode) -> Optional[str]:
        """Extract function signature from a function/method node.

        Args:
            node: SyntaxNode representing a function or method

        Returns:
            Function signature as a string, or None if not applicable
        """
        pass

    @abstractmethod
    def get_class_definition(self, node: SyntaxNode) -> Optional[str]:
        """Extract class definition from a class node.

        Args:
            node: SyntaxNode representing a class

        Returns:
            Class definition as a string, or None if not applicable
        """
        pass

    @classmethod
    @abstractmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get the file extensions supported by this parser.

        Returns:
            Set of file extensions (e.g., {".py", ".pyi"})
        """
        pass

    @classmethod
    @abstractmethod
    def get_language_name(cls) -> str:
        """Get the name of the language supported by this parser.

        Returns:
            Language name (e.g., "Python", "JavaScript")
        """
        pass


def extract_relevant_code(node: SyntaxNode, full_source: str, include_context: bool = False) -> str:
    """Extract only the relevant code for a given node.

    Args:
        node: The syntax node
        full_source: The full source code (only accessed when needed)
        include_context: Whether to include minimal surrounding context

    Returns:
        Relevant code snippet for the node
    """
    # Basic extraction from source using byte positions
    code_snippet = full_source[node.start_byte : node.end_byte]

    # Optionally add minimal context
    if include_context:
        # Add function/class signature for blocks inside them
        # Add imports for references
        # Add type definitions if needed
        pass

    return code_snippet
