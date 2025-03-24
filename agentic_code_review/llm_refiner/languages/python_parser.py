"""Python parser implementation using Tree-sitter.

This module provides Python language parsing capabilities for the code refinement agent.
"""

import os
from typing import ClassVar, Optional, Union

from tree_sitter import Language, Node, Parser, Tree

from agentic_code_review.llm_refiner.languages.base_parser import BaseParser, SyntaxNode, SyntaxNodeType
from agentic_code_review.llm_refiner.languages.parser_registry import ParserRegistry
from agentic_code_review.llm_refiner.languages.parser_utils import find_node_at_position, get_node_text


class PythonParser(BaseParser):
    """Python language parser using Tree-sitter."""

    # Node type mapping for common Python syntax elements
    _NODE_TYPE_MAP: ClassVar[dict[str, SyntaxNodeType]] = {
        "function_definition": SyntaxNodeType.FUNCTION,
        "class_definition": SyntaxNodeType.CLASS,
        "module": SyntaxNodeType.MODULE,
        "import_statement": SyntaxNodeType.IMPORT,
        "import_from_statement": SyntaxNodeType.IMPORT,
        "assignment": SyntaxNodeType.STATEMENT,
        "expression_statement": SyntaxNodeType.STATEMENT,
        "block": SyntaxNodeType.BLOCK,
        "parameters": SyntaxNodeType.PARAMETER,
    }

    def __init__(self) -> None:
        """Initialize the Python parser."""
        self.parser: Parser | None = None
        self.language: Language | None = None

    def setup_parser(self) -> None:
        """Set up the Tree-sitter parser for Python."""
        try:
            # Use the installed tree-sitter-python library
            self.parser = Parser()
            self.language = Language.build_library(  # type: ignore
                # Caches the language library in the users's cache directory
                os.path.expanduser("~/.cache/tree-sitter-python.so"),
                # Github repo containing language grammar
                ["vendor/tree-sitter-python"],
            )
            lang = Language("~/.cache/tree-sitter-python.so", "python")  # type: ignore
            if self.parser is not None:
                self.parser.set_language(lang)  # type: ignore
        except (ImportError, FileNotFoundError):
            # Try to use the library directly if vendor dir not available
            import tree_sitter_python

            self.parser = Parser()
            if self.parser is not None:
                self.parser.set_language(tree_sitter_python.language)  # type: ignore

    def parse_code(self, code: str) -> Tree:
        """Parse Python code into a Tree-sitter syntax tree.

        Args:
            code: Python source code

        Returns:
            Tree-sitter syntax tree
        """
        if self.parser is None:
            self.setup_parser()

        if self.parser is None:
            raise RuntimeError("Failed to initialize Python parser")

        return self.parser.parse(bytes(code, "utf-8"))

    def _get_node_type(self, node: Node) -> SyntaxNodeType:
        """Map Tree-sitter node types to language-agnostic SyntaxNodeType.

        Args:
            node: Tree-sitter node

        Returns:
            Corresponding SyntaxNodeType
        """
        node_type = node.type

        # Check if the node type is in our mapping dictionary
        if node_type in self._NODE_TYPE_MAP:
            return self._NODE_TYPE_MAP[node_type]

        # Special case for decorated definitions - need to check children
        if node_type == "decorated_definition":
            # Check children to determine the actual type
            for child in node.children:
                child_type = child.type
                if child_type in self._NODE_TYPE_MAP:
                    return self._NODE_TYPE_MAP[child_type]

        # Default case
        return SyntaxNodeType.OTHER

    def _get_node_name(self, node: Node, source_code: bytes) -> str:
        """Get a name for a Python node.

        Args:
            node: Tree-sitter node
            source_code: Source code as bytes

        Returns:
            Name of the node
        """
        node_type = node.type

        # Dictionary of node types that have identifiers and where to find them
        name_extractors = {
            "function_definition": "identifier",
            "class_definition": "identifier",
        }

        # Handle regular nodes with identifiers
        if node_type in name_extractors:
            identifier_type = name_extractors[node_type]
            for child in node.children:
                if child.type == identifier_type:
                    return get_node_text(child, source_code)

        # Special case for decorated definitions
        elif node_type == "decorated_definition":
            # Look for the actual definition
            for child in node.children:
                if child.type in name_extractors:
                    return self._get_node_name(child, source_code)

        # Default case
        return node_type

    def _extract_syntax_node_recursive(self, node: Node, source_code: bytes, depth: int = 0) -> SyntaxNode | None:
        """Recursively extract a SyntaxNode from a Tree-sitter Node.

        Args:
            node: Tree-sitter node
            source_code: Source code as bytes
            depth: Current recursion depth

        Returns:
            Corresponding SyntaxNode or None if not relevant
        """
        # Skip nodes we don't care about for the high-level structure
        if node.type in ("comment", "string", "integer", "float", "true", "false", "none"):
            return None

        # Extract relevant children
        children: list[SyntaxNode] = []
        for child in node.children:
            child_node = self._extract_syntax_node_recursive(child, source_code, depth + 1)
            if child_node:
                children.append(child_node)

        node_type = self._get_node_type(node)
        node_name = self._get_node_name(node, source_code)

        # Dictionary mapping node types to metadata extraction functions
        metadata_extractors = {
            SyntaxNodeType.FUNCTION: lambda n: {"signature": self._get_function_signature(n, source_code)},
            SyntaxNodeType.CLASS: lambda n: {"class_definition": self._get_class_definition(n, source_code)},
        }

        # Extract metadata based on node type
        metadata = {}
        if node_type in metadata_extractors:
            try:
                extracted_metadata = metadata_extractors[node_type](node)
                # Only add non-None values
                metadata.update({k: v for k, v in extracted_metadata.items() if v is not None})
            except Exception as e:
                # Log the error but continue with tree extraction
                print(f"Error extracting metadata for {node_type}: {e}")

        return SyntaxNode(
            node_type=node_type,
            name=node_name,
            start_point=(node.start_point[0], node.start_point[1]),
            end_point=(node.end_point[0], node.end_point[1]),
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            children=children,
            raw_node=node,
            metadata=metadata,
        )

    def extract_syntax_tree(self, code: str) -> SyntaxNode:
        """Extract a structured syntax tree from Python code.

        Args:
            code: Python source code

        Returns:
            Root SyntaxNode containing the hierarchical structure
        """
        tree = self.parse_code(code)
        source_code = bytes(code, "utf-8")
        root_node = self._extract_syntax_node_recursive(tree.root_node, source_code)

        # If we somehow don't get a root node (shouldn't happen), create a minimal one
        if not root_node:
            root_node = SyntaxNode(
                node_type=SyntaxNodeType.MODULE,
                name="module",
                start_point=(0, 0),
                end_point=(code.count("\n"), len(code.splitlines()[-1]) if code.splitlines() else 0),
                start_byte=0,
                end_byte=len(code),
                children=[],
                raw_node=tree.root_node,
            )

        return root_node

    def find_node_at_position(self, code: str, line: int, col: int) -> SyntaxNode | None:
        """Find the syntax node at the given position in Python code.

        Args:
            code: Python source code
            line: Line number (0-indexed)
            col: Column number (0-indexed)

        Returns:
            SyntaxNode at the position, or None if not found
        """
        tree = self.parse_code(code)
        source_code = bytes(code, "utf-8")

        # Use the utility function to find the raw Tree-sitter node
        raw_node = find_node_at_position(tree.root_node, line, col, source_code)
        if not raw_node:
            return None

        # Convert to SyntaxNode
        syntax_tree = self.extract_syntax_tree(code)
        return syntax_tree.find_node_at_position(line, col)

    def get_function_signature(self, node: SyntaxNode) -> Optional[str]:
        """Extract function signature from a function node.

        Args:
            node: SyntaxNode representing a function

        Returns:
            Function signature as a string, or None if not applicable
        """
        if not node or not node.raw_node:
            return None

        # Extract source code from metadata if available
        source_code = None
        if hasattr(node, "metadata") and "source_code" in node.metadata:
            source_code = node.metadata["source_code"]

        # Use our internal implementation with the raw node
        return self._get_function_signature(node.raw_node, source_code)

    def _get_function_signature(self, node: Node, source_code: Optional[bytes] = None) -> Optional[str]:
        """Extract function signature from a Python function node.

        Args:
            node: Tree-sitter node representing a function
            source_code: Source code as bytes

        Returns:
            Function signature as a string, or None if not applicable
        """
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        if node is None or source_code is None:
            return None

        # Resolve decorated definitions to get the actual function
        function_node = self._resolve_decorated_node(node, "function_definition")
        if function_node is None:
            return None

        # Dictionary mapping child node types to their role in signature
        signature_parts: dict[str, Optional[str]] = {
            "identifier": None,  # Function name
            "parameters": None,  # Parameter list
            "->": None,  # Return type indicator
        }

        # Extract each part from the children
        return_type_index = None
        for i, child in enumerate(function_node.children):
            if child.type in signature_parts:
                signature_parts[child.type] = get_node_text(child, source_code)
                # Mark position of return type indicator
                if child.type == "->":
                    return_type_index = i

        # Get return type if available (it follows the '->' token)
        return_type = ""
        if return_type_index is not None and return_type_index + 1 < len(function_node.children):
            return_type_text = get_node_text(function_node.children[return_type_index + 1], source_code)
            if return_type_text:
                return_type = f" -> {return_type_text}"

        # Use default values for missing parts to avoid rendering "None" in output
        identifier = signature_parts["identifier"] or ""
        parameters = signature_parts["parameters"] or "()"

        return f"def {identifier}{parameters}{return_type}:"

    def _validate_node_input(self, node_or_syntax_node: Union[Node, SyntaxNode], source_code: Optional[bytes] = None) -> tuple[Optional[Node], bool]:
        """Validate node input and extract the underlying Tree-sitter node.

        Args:
            node_or_syntax_node: Node or SyntaxNode representing a AST node
            source_code: Source code as bytes

        Returns:
            Tuple of (node, valid_source) where node is the Tree-sitter node and
            valid_source indicates if we have valid source code
        """
        # Handle SyntaxNode input
        if isinstance(node_or_syntax_node, SyntaxNode):
            node = node_or_syntax_node.raw_node
            # We no longer have the code in SyntaxNode, so source_code is required
            if source_code is None:
                return None, False
        else:
            node = node_or_syntax_node

        return node, source_code is not None

    def _resolve_decorated_node(self, node: Node, target_type: str) -> Node | None:
        """Resolve decorated definitions to get the actual node.

        Args:
            node: Tree-sitter node, possibly a decorated_definition
            target_type: The target node type to look for in children

        Returns:
            The target node or None if not found
        """
        if node is None:
            return None

        if node.type == target_type:
            return node

        # Check if it's a decorated definition
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type == target_type:
                    return child

        return None

    def get_class_definition(self, node: SyntaxNode) -> Optional[str]:
        """Extract class definition from a class node.

        Args:
            node: SyntaxNode representing a class

        Returns:
            Class definition as a string, or None if not applicable
        """
        if not node or not node.raw_node:
            return None

        # Use our internal implementation with the raw node
        return self._get_class_definition(node.raw_node)

    def _get_class_definition(self, node: Node, source_code: Optional[bytes] = None) -> Optional[str]:
        """Extract class definition from a Python class node.

        Args:
            node: Tree-sitter node representing a class
            source_code: Source code as bytes

        Returns:
            Class definition as a string, or None if not applicable
        """
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        if node is None or source_code is None:
            return None

        # Resolve decorated definitions to get the actual class
        class_node = self._resolve_decorated_node(node, "class_definition")
        if class_node is None:
            return None

        # Dictionary mapping child node types to their role in class definition
        definition_parts: dict[str, Optional[str]] = {
            "identifier": None,  # Class name
            "argument_list": None,  # Parent classes
        }

        # Extract each part from the children
        for child in class_node.children:
            if child.type in definition_parts:
                part_text = get_node_text(child, source_code)
                if part_text:
                    definition_parts[child.type] = part_text

        # Use default values to avoid rendering "None" in output
        class_name = definition_parts["identifier"] or "UnnamedClass"
        parent_classes = definition_parts["argument_list"] or ""

        return f"class {class_name}{parent_classes}:"

    @classmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get the file extensions supported by the Python parser.

        Returns:
            Set of file extensions
        """
        return {".py", ".pyi"}

    @classmethod
    def get_language_name(cls) -> str:
        """Get the name of the language supported by this parser.

        Returns:
            Language name
        """
        return "Python"


# Register the Python parser
ParserRegistry.register_parser(PythonParser)
