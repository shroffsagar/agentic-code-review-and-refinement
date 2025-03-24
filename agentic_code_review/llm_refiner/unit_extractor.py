"""Syntactic unit extractor for code refinement.

This module provides functionality to extract meaningful syntactic units
(functions, classes, methods, etc.) from code for targeted refinement.
"""

import logging
from dataclasses import dataclass, field
from typing import ClassVar, Optional

from .languages.base_parser import SyntaxNode, SyntaxNodeType, extract_relevant_code
from .languages.parser_registry import ParserRegistry

logger = logging.getLogger(__name__)


@dataclass
class SyntacticUnit:
    """A syntactic unit extracted from code for refinement.

    This represents a self-contained unit of code (like a function, class, or method)
    that can be refined independently.
    """

    node: SyntaxNode
    code: str
    file_path: str
    unit_type: SyntaxNodeType
    name: str
    start_line: int
    end_line: int
    parent_unit: Optional["SyntacticUnit"] = None
    children: list["SyntacticUnit"] = field(default_factory=list)

    @property
    def signature(self) -> Optional[str]:
        """Get the signature of this unit if available."""
        if self.unit_type in (SyntaxNodeType.FUNCTION, SyntaxNodeType.METHOD):
            return self.node.metadata.get("signature")
        elif self.unit_type == SyntaxNodeType.CLASS:
            return self.node.metadata.get("class_definition")
        return None

    @property
    def location_str(self) -> str:
        """Get a string representation of this unit's location."""
        return f"{self.file_path}:{self.start_line}-{self.end_line}"

    @property
    def full_path(self) -> str:
        """Get the full path to this unit, including parent contexts."""
        if self.parent_unit:
            return f"{self.parent_unit.full_path}.{self.name}"
        return self.name


class SyntacticUnitExtractor:
    """Extracts syntactic units from code for targeted refinement."""

    # Types of nodes that represent meaningful syntactic units
    UNIT_TYPES: ClassVar[set[SyntaxNodeType]] = {
        SyntaxNodeType.FUNCTION,
        SyntaxNodeType.METHOD,
        SyntaxNodeType.CLASS,
        SyntaxNodeType.MODULE,
    }

    def __init__(self) -> None:
        """Initialize the syntactic unit extractor."""
        pass

    def extract_units_from_file(self, file_path: str, file_content: str) -> list[SyntacticUnit]:
        """Extract syntactic units from a file.

        Args:
            file_path: The path to the file
            file_content: The content of the file

        Returns:
            A list of syntactic units extracted from the file

        Raises:
            ValueError: If no parser is available for the file
        """
        logger.debug(f"Extracting syntactic units from {file_path}")

        # Get the appropriate parser for this file
        parser = ParserRegistry.get_parser_for_file(file_path)
        if not parser:
            raise ValueError(f"No parser available for file: {file_path}")

        # Parse the code and extract the syntax tree
        syntax_tree = parser.extract_syntax_tree(file_content)

        # Extract units from the syntax tree
        return self._extract_units_recursive(syntax_tree, file_content, file_path)

    def extract_unit_at_location(self, file_path: str, file_content: str, line: int, col: int = 0) -> Optional[SyntacticUnit]:
        """Extract the syntactic unit at a specific location in the file.

        Args:
            file_path: The path to the file
            file_content: The content of the file
            line: The line number (0-indexed)
            col: The column number (0-indexed)

        Returns:
            The syntactic unit at the location, or None if not found

        Raises:
            ValueError: If no parser is available for the file
        """
        logger.debug(f"Extracting syntactic unit at {file_path}:{line}:{col}")

        # Get the appropriate parser for this file
        parser = ParserRegistry.get_parser_for_file(file_path)
        if not parser:
            raise ValueError(f"No parser available for file: {file_path}")

        # Find the node at the specified position
        node = parser.find_node_at_position(file_content, line, col)
        if not node:
            logger.warning(f"No node found at position {line}:{col} in {file_path}")
            return None

        # Find the closest containing unit
        unit_node = self._find_closest_unit_node(node)
        if not unit_node:
            logger.warning(f"No unit node found containing position {line}:{col} in {file_path}")
            return None

        # Extract the code for this unit
        code = extract_relevant_code(unit_node, file_content)

        # Create and return the syntactic unit
        return SyntacticUnit(
            node=unit_node,
            code=code,
            file_path=file_path,
            unit_type=unit_node.node_type,
            name=unit_node.name,
            start_line=unit_node.start_point[0],
            end_line=unit_node.end_point[0],
        )

    def extract_units_at_specific_lines(self, file_path: str, file_content: str, line_ranges: list[tuple[int, int]]) -> list[SyntacticUnit]:
        """Extract syntactic units that overlap with specified line ranges.

        Args:
            file_path: The path to the file
            file_content: The content of the file
            line_ranges: List of (start_line, end_line) tuples (0-indexed)

        Returns:
            List of syntactic units that overlap with the specified line ranges

        Raises:
            ValueError: If no parser is available for the file
        """
        # Extract all units from the file
        all_units = self.extract_units_from_file(file_path, file_content)

        # Filter units that overlap with any of the specified line ranges
        result = []
        for unit in all_units:
            for start_line, end_line in line_ranges:
                # Check if unit overlaps with the line range
                if unit.start_line <= end_line and unit.end_line >= start_line:
                    result.append(unit)
                    break

        return result

    def _extract_units_recursive(self, node: SyntaxNode, full_content: str, file_path: str, parent: Optional[SyntacticUnit] = None) -> list[SyntacticUnit]:
        """Recursively extract syntactic units from a syntax tree.

        Args:
            node: The current syntax node
            full_content: The full content of the file
            file_path: The path to the file
            parent: The parent syntactic unit, if any

        Returns:
            A list of syntactic units extracted from the node and its children
        """
        result = []

        # Check if this node is a unit we care about
        is_unit = node.node_type in self.UNIT_TYPES

        # Create a syntactic unit for this node if it's a unit type
        current_unit = None
        if is_unit:
            code = extract_relevant_code(node, full_content)
            current_unit = SyntacticUnit(
                node=node,
                code=code,
                file_path=file_path,
                unit_type=node.node_type,
                name=node.name,
                start_line=node.start_point[0],
                end_line=node.end_point[0],
                parent_unit=parent,
            )
            result.append(current_unit)

        # Recursively process children
        for child in node.children:
            child_units = self._extract_units_recursive(child, full_content, file_path, current_unit or parent)

            # Add child units to result
            result.extend(child_units)

            # Add child units as children of current unit if appropriate
            if current_unit and child_units:
                for child_unit in child_units:
                    if child_unit.parent_unit == current_unit:
                        current_unit.children.append(child_unit)

        return result

    def _find_closest_unit_node(self, node: SyntaxNode) -> Optional[SyntaxNode]:
        """Find the closest containing node that represents a syntactic unit.

        Args:
            node: The node to start from

        Returns:
            The closest containing unit node, or None if not found
        """
        current = node

        # First check if the current node is a unit
        if current.node_type in self.UNIT_TYPES:
            return current

        # Traverse up the tree looking for a unit node
        while hasattr(current, "raw_node") and current.raw_node and hasattr(current.raw_node, "parent"):
            parent_node = current.raw_node.parent
            if not parent_node:
                break

            # We need to handle the case where parent_node is Node but not SyntaxNode
            if isinstance(parent_node, SyntaxNode):
                if hasattr(parent_node, "node_type") and parent_node.node_type in self.UNIT_TYPES:
                    return parent_node
                current = parent_node
            else:
                # For regular Node objects, just continue traversing up
                current = parent_node  # type: ignore

        return None
