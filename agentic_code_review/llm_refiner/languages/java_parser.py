"""Java parser implementation using Tree-sitter.

This module provides Java language parsing capabilities for the code refinement agent.
"""

import os
from typing import Optional

from tree_sitter import Language, Node, Parser, Tree

from agentic_code_review.llm_refiner.languages.base_parser import BaseParser, SyntaxNode, SyntaxNodeType
from agentic_code_review.llm_refiner.languages.parser_registry import ParserRegistry
from agentic_code_review.llm_refiner.languages.parser_utils import find_node_at_position, get_node_text


class JavaParser(BaseParser):
    """Java language parser using Tree-sitter."""

    def __init__(self) -> None:
        """Initialize the Java parser."""
        self.parser: Parser | None = None
        self.language: Language | None = None

    def setup_parser(self) -> None:
        """Set up the Tree-sitter parser for Java."""
        try:
            # Use the installed tree-sitter-java library
            self.parser = Parser()
            self.language = Language.build_library(  # type: ignore
                # Caches the language library in the users's cache directory
                os.path.expanduser("~/.cache/tree-sitter-java.so"),
                # Github repo containing language grammar
                ["vendor/tree-sitter-java"],
            )
            lang = Language("~/.cache/tree-sitter-java.so", "java")  # type: ignore
            if self.parser is not None:
                self.parser.set_language(lang)  # type: ignore
        except (ImportError, FileNotFoundError):
            # Try to use the library directly if vendor dir not available
            import tree_sitter_java

            self.parser = Parser()
            if self.parser is not None:
                self.parser.set_language(tree_sitter_java.language)  # type: ignore

    def parse_code(self, code: str) -> Tree:
        """Parse Java code into a Tree-sitter syntax tree.

        Args:
            code: Java source code

        Returns:
            Tree-sitter syntax tree
        """
        if self.parser is None:
            self.setup_parser()

        if self.parser is None:
            raise RuntimeError("Failed to initialize Java parser")

        return self.parser.parse(bytes(code, "utf-8"))

    def _get_node_type(self, node: Node) -> SyntaxNodeType:
        """Map Tree-sitter node types to SyntaxNodeType.

        Args:
            node: Tree-sitter node

        Returns:
            Corresponding SyntaxNodeType
        """
        # Dictionary mapping node types to SyntaxNodeType
        node_type_mapping = {
            # Method-like nodes
            "method_declaration": SyntaxNodeType.METHOD,
            "constructor_declaration": SyntaxNodeType.METHOD,
            # Class-like nodes
            "class_declaration": SyntaxNodeType.CLASS,
            "interface_declaration": SyntaxNodeType.CLASS,  # Treating interfaces as classes for simplicity
            "enum_declaration": SyntaxNodeType.CLASS,  # Treating enums as classes for simplicity
            # Other common node types
            "program": SyntaxNodeType.MODULE,
            "import_declaration": SyntaxNodeType.IMPORT,
            "block": SyntaxNodeType.BLOCK,
            "formal_parameters": SyntaxNodeType.PARAMETER,
        }

        # Statement-like nodes
        statement_types = {"local_variable_declaration", "expression_statement", "field_declaration"}

        node_type = node.type

        if node_type in node_type_mapping:
            return node_type_mapping[node_type]
        elif node_type in statement_types:
            return SyntaxNodeType.STATEMENT
        else:
            return SyntaxNodeType.OTHER

    def _get_node_name(self, node: Node, source_code: bytes) -> str:
        """Get a name for a Java node.

        Args:
            node: Tree-sitter node
            source_code: Source code as bytes

        Returns:
            Name of the node
        """
        node_type = node.type

        if node_type in ("method_declaration", "constructor_declaration"):
            # Find the identifier (method name)
            for child in node.children:
                if child.type == "identifier":
                    return get_node_text(child, source_code)
        elif node_type in ("class_declaration", "interface_declaration", "enum_declaration"):
            # Find the identifier (class/interface/enum name)
            for child in node.children:
                if child.type == "identifier":
                    return get_node_text(child, source_code)

        # Default case
        return node_type

    def _extract_syntax_node_recursive(self, node: Node, source_code: bytes, depth: int = 0) -> Optional[SyntaxNode]:
        """Recursively extract a SyntaxNode from a Tree-sitter Node.

        Args:
            node: Tree-sitter node
            source_code: Source code as bytes
            depth: Current recursion depth

        Returns:
            Corresponding SyntaxNode or None if not relevant
        """
        # Skip nodes we don't care about for the high-level structure
        if node.type in ("comment", "line_comment", "block_comment", "string_literal", "decimal_integer_literal"):
            return None

        # Extract relevant children
        children: list[SyntaxNode] = []
        for child in node.children:
            child_node = self._extract_syntax_node_recursive(child, source_code, depth + 1)
            if child_node:
                children.append(child_node)

        node_type = self._get_node_type(node)
        node_name = self._get_node_name(node, source_code)

        metadata = {}
        # Extract method signature for methods
        if node_type == SyntaxNodeType.METHOD:
            signature = self._get_function_signature(node, source_code)
            if signature:
                metadata["signature"] = signature

        # Extract class definition for classes
        if node_type == SyntaxNodeType.CLASS:
            class_def = self._get_class_definition(node, source_code)
            if class_def:
                metadata["class_definition"] = class_def

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
        """Extract a structured syntax tree from Java code.

        Args:
            code: Java source code

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

    def find_node_at_position(self, code: str, line: int, col: int) -> Optional[SyntaxNode]:
        """Find the syntax node at the given position in Java code.

        Args:
            code: Java source code
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

    def _extract_method_modifiers(self, node: Node, source_code: bytes) -> str:
        """Extract method modifiers (public, private, static, etc.).

        Args:
            node: Method node
            source_code: Source code as bytes

        Returns:
            String with all modifiers
        """
        modifiers = []

        # Look for modifiers
        for child in node.children:
            if child.type == "modifiers":
                for modifier_child in child.children:
                    modifiers.append(get_node_text(modifier_child, source_code))
                break

        return " ".join(modifiers) + (" " if modifiers else "")

    def get_function_signature(self, node: SyntaxNode) -> Optional[str]:
        """Extract method signature from a method node.

        Args:
            node: SyntaxNode representing a method

        Returns:
            Method signature as a string, or None if not applicable
        """
        if not node or not node.raw_node:
            return None

        # Use our internal implementation with the raw node
        return self._get_function_signature(node.raw_node)

    def _get_function_signature(self, node, source_code=None) -> str:
        """
        Extract the method signature from a Java method declaration.

        Args:
            node: The raw tree-sitter node representing the method.
            source_code: The source code string.

        Returns:
            A string representation of the method signature.
        """

        # Validate node
        if node is None or source_code is None:
            return ""

        # Only extract signatures from method declarations and constructor declarations
        if node.type not in ["method_declaration", "constructor_declaration"]:
            return ""

        signature_parts: list[str] = []
        method_name = ""

        # Process method components
        self._add_modifiers_to_signature(node, source_code, signature_parts)

        # Get return type and method name
        if node.type == "method_declaration":
            self._add_return_type_to_signature(node, source_code, signature_parts)

        # Extract method name
        method_name = self._extract_method_name(node, source_code)

        # Get parameters
        parameters = self._extract_parameters(node, source_code)

        # Get throws clause
        throws_clause = self._extract_throws_clause(node, source_code)

        # Combine components
        full_signature = " ".join(signature_parts) + f" {method_name}({parameters})"
        if throws_clause:
            full_signature += f" {throws_clause}"

        return full_signature

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

    def _get_class_definition(self, node, source_code=None) -> str:
        """
        Extract the class definition from a Java class declaration.

        Args:
            node: The raw tree-sitter node representing the class.
            source_code: The source code string.

        Returns:
            A string representation of the class definition.
        """

        # Validate node
        if node is None or source_code is None:
            return ""

        # Define valid types for class-like structures
        valid_types = {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}

        if node.type not in valid_types:
            return ""

        # Extract declaration type (class, interface, enum, etc.)
        declaration_type = self._get_declaration_type(node.type)

        # Process modifiers and class name
        modifiers = self._extract_class_modifiers(node, source_code)
        class_name = self._extract_class_name(node, source_code)
        type_parameters = self._extract_type_parameters(node, source_code)
        extends_clause = self._extract_extends_clause(node, source_code)
        implements_clause = self._extract_implements_clause(node, source_code)
        permits_clause = self._extract_permits_clause(node, source_code)

        # Combine components
        definition_parts = []
        if modifiers:
            definition_parts.append(modifiers)

        definition_parts.append(declaration_type)
        definition_parts.append(class_name)

        if type_parameters:
            definition_parts.append(type_parameters)
        if extends_clause:
            definition_parts.append(extends_clause)
        if implements_clause:
            definition_parts.append(implements_clause)
        if permits_clause:
            definition_parts.append(permits_clause)

        return " ".join(definition_parts)

    # Helper methods for get_class_definition
    def _get_declaration_type(self, node_type):
        """Get the type of declaration (class, interface, enum, record)."""
        declaration_map = {"class_declaration": "class", "interface_declaration": "interface", "enum_declaration": "enum", "record_declaration": "record"}
        return declaration_map.get(node_type, "class")

    def _extract_class_modifiers(self, node, source_code):
        """Extract class modifiers from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "modifiers":
                return get_node_text(child, source_code).strip()
        return ""

    def _extract_class_name(self, node, source_code):
        """Extract class name from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "identifier":
                return get_node_text(child, source_code)
        return ""

    def _extract_type_parameters(self, node, source_code):
        """Extract type parameters from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "type_parameters":
                return get_node_text(child, source_code)
        return ""

    def _extract_extends_clause(self, node, source_code):
        """Extract extends clause from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "superclass":
                extends_text = get_node_text(child, source_code).strip()
                if extends_text:
                    return extends_text
        return ""

    def _extract_implements_clause(self, node, source_code):
        """Extract implements clause from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "interfaces":
                implements_text = get_node_text(child, source_code).strip()
                if implements_text:
                    return implements_text
        return ""

    def _extract_permits_clause(self, node, source_code):
        """Extract permits clause from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "permits":
                permits_text = get_node_text(child, source_code).strip()
                if permits_text:
                    return permits_text
        return ""

    @classmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get the file extensions supported by the Java parser.

        Returns:
            Set of file extensions
        """
        return {".java"}

    @classmethod
    def get_language_name(cls) -> str:
        """Get the name of the language supported by this parser.

        Returns:
            Language name
        """
        return "Java"

    def _resolve_decorated_node(self, node: Node, target_type: str) -> Node | None:
        """Resolve decorated definitions to get the actual node.

        Args:
            node: Tree-sitter node, possibly a decorated node
            target_type: The target node type to look for

        Returns:
            The target node or None if not found
        """
        if node is None:
            return None

        if node.type == target_type:
            return node

        # Check if it's a decorated definition (Java has annotations)
        if node.type in {"decorated_definition", "annotated"}:
            for child in node.children:
                if child.type == target_type:
                    return child

        return None

    def is_valid_property_or_method(self, node) -> bool:
        """
        Check if the node is a valid field or method declaration.

        Args:
            node: The node to check.

        Returns:
            True if the node is a valid field or method declaration, False otherwise.
        """
        if node is None:
            return False

        valid_types = {"field_declaration", "method_declaration", "constructor_declaration", "static_initializer", "instance_initializer"}

        return node.type in valid_types

    # Helper methods for _get_function_signature
    def _add_modifiers_to_signature(self, node, source_code, signature_parts):
        """Add modifiers to the signature parts list."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "modifiers":
                modifier_text = get_node_text(child, source_code).strip()
                if modifier_text:
                    signature_parts.append(modifier_text)

    def _add_return_type_to_signature(self, node, source_code, signature_parts):
        """Add return type to the signature parts list."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        return_type_nodes = {"type_identifier", "primitive_type", "void_type", "array_type", "generic_type", "scoped_type_identifier"}

        for child in node.children:
            if child.type in return_type_nodes:
                return_type = get_node_text(child, source_code)
                signature_parts.append(return_type)

    def _extract_method_name(self, node, source_code):
        """Extract method name from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "identifier":
                return get_node_text(child, source_code)
        return ""

    def _extract_parameters(self, node, source_code):
        """Extract parameters from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "formal_parameters":
                return get_node_text(child, source_code)
        return "()"

    def _extract_throws_clause(self, node, source_code):
        """Extract throws clause from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "throws":
                return get_node_text(child, source_code)
        return ""


# Register the Java parser
ParserRegistry.register_parser(JavaParser)
