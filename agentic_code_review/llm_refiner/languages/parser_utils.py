"""Utility functions for Tree-sitter parser implementations.

This module provides common functionality used across language-specific parsers.
"""

from typing import Optional

from tree_sitter import Node


def traverse_tree(node: Node) -> list[Node]:
    """Traverse a Tree-sitter node tree and return all nodes in depth-first order.

    Args:
        node: The root Tree-sitter node

    Returns:
        List of all nodes in the tree in depth-first order
    """
    nodes = [node]
    for child in node.children:
        nodes.extend(traverse_tree(child))
    return nodes


def get_node_text(node: Node, source_code: bytes) -> str:
    """Extract text for a node from source code.

    Args:
        node: Tree-sitter node
        source_code: Source code as bytes

    Returns:
        Text content of the node
    """
    return source_code[node.start_byte : node.end_byte].decode("utf-8")


def get_node_name(node: Node, source_code: bytes) -> str:
    """Get a meaningful name for a node based on its type.

    This is a generic implementation. Language-specific parsers should
    override this with more specific logic.

    Args:
        node: Tree-sitter node
        source_code: Source code as bytes

    Returns:
        Name of the node or its type as fallback
    """
    # Default implementation just returns the node type
    return node.type


def find_node_at_position(root: Node, line: int, column: int, source_code: bytes) -> Optional[Node]:
    """Find the smallest node containing the given position.

    Args:
        root: The root Tree-sitter node to search from
        line: Line number (0-indexed)
        column: Column number (0-indexed)
        source_code: Source code as bytes

    Returns:
        The smallest node containing the position, or None if not found
    """
    if not (
        root.start_point[0] <= line <= root.end_point[0]
        and (line > root.start_point[0] or column >= root.start_point[1])
        and (line < root.end_point[0] or column <= root.end_point[1])
    ):
        return None

    # Check children first to find the smallest container
    for child in root.children:
        result = find_node_at_position(child, line, column, source_code)
        if result:
            return result

    return root


def clean_whitespace(text: str) -> str:
    """Clean excessive whitespace from text.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    import re

    return re.sub(r"\s+", " ", text).strip()


def extract_qualified_name(node: Node, source_code: bytes) -> str:
    """Extract a qualified name from a node.

    This is a generic implementation. Language-specific parsers should
    override this with language-specific logic.

    Args:
        node: Tree-sitter node
        source_code: Source code as bytes

    Returns:
        Qualified name
    """
    return get_node_text(node, source_code)
