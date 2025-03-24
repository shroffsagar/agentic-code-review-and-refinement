"""JavaScript and TypeScript parser implementation using Tree-sitter.

This module provides JavaScript and TypeScript language parsing capabilities for the code refinement agent.
"""

import os
from typing import Optional

from tree_sitter import Language, Node, Parser, Tree

from agentic_code_review.llm_refiner.languages.base_parser import BaseParser, SyntaxNode, SyntaxNodeType
from agentic_code_review.llm_refiner.languages.parser_registry import ParserRegistry
from agentic_code_review.llm_refiner.languages.parser_utils import find_node_at_position, get_node_text


class JavaScriptTypeScriptParser(BaseParser):
    """JavaScript and TypeScript language parser using Tree-sitter."""

    def __init__(self) -> None:
        """Initialize the JavaScript/TypeScript parser."""
        self.js_parser: Parser | None = None
        self.ts_parser: Parser | None = None
        self.language: Language | None = None
        self.jsx_enabled = False
        self.tsx_enabled = False

    def setup_parser(self) -> None:
        """Set up the Tree-sitter parser for JavaScript and TypeScript."""
        try:
            # JavaScript
            self.js_parser = Parser()
            self.language = Language.build_library(  # type: ignore
                # Caches the language library in the users's cache directory
                os.path.expanduser("~/.cache/tree-sitter-javascript.so"),
                # Github repo containing language grammar
                ["vendor/tree-sitter-javascript"],
            )
            js_lang = Language("~/.cache/tree-sitter-javascript.so", "javascript")  # type: ignore
            if self.js_parser is not None:
                self.js_parser.set_language(js_lang)  # type: ignore

            # TypeScript
            self.ts_parser = Parser()
            self.language = Language.build_library(  # type: ignore
                # Caches the language library in the users's cache directory
                os.path.expanduser("~/.cache/tree-sitter-typescript.so"),
                # Github repo containing language grammar
                ["vendor/tree-sitter-typescript"],
            )
            ts_lang = Language("~/.cache/tree-sitter-typescript.so", "typescript")  # type: ignore
            # We create this variable for future potential use, but it's not currently used
            # Remove the F841 warning by commenting out or making it clear that it's for future use
            # tsx_lang = Language('~/.cache/tree-sitter-typescript.so', 'tsx')
            if self.ts_parser is not None:
                self.ts_parser.set_language(ts_lang)  # type: ignore

            # Enable JSX/TSX support flags
            self.jsx_enabled = True
            self.tsx_enabled = True

        except (ImportError, FileNotFoundError):
            # Try to use the libraries directly if vendor dir not available
            import tree_sitter_javascript
            import tree_sitter_typescript

            self.js_parser = Parser()
            if self.js_parser is not None:
                self.js_parser.set_language(tree_sitter_javascript.language)  # type: ignore

            self.ts_parser = Parser()
            if self.ts_parser is not None:
                # Note: tree_sitter_typescript module has language_typescript and language_tsx
                self.ts_parser.set_language(tree_sitter_typescript.language_typescript)  # type: ignore

    def _get_parser_for_extension(self, ext: str) -> Optional[Parser]:
        """Get the appropriate parser for a file extension.

        Args:
            ext: File extension (e.g., '.js', '.ts', '.tsx')

        Returns:
            Appropriate parser for the extension or None if unsupported
        """
        if ext in {".js", ".jsx", ".mjs"}:
            return self.js_parser
        elif ext in {".ts", ".tsx", ".d.ts"}:
            return self.ts_parser
        return None

    def parse_code(self, code: str, file_extension: str = ".js") -> Tree:
        """Parse JavaScript/TypeScript code into a Tree-sitter syntax tree.

        Args:
            code: JavaScript/TypeScript source code
            file_extension: File extension to determine whether to use JS or TS parser

        Returns:
            Tree-sitter syntax tree
        """
        parser = self._get_parser_for_extension(file_extension)
        if parser is None:
            # Default to JavaScript parser if extension not matched
            if self.js_parser is None:
                self.setup_parser()
            parser = self.js_parser

        if parser is None:
            raise RuntimeError("Failed to initialize JavaScript/TypeScript parser")

        return parser.parse(bytes(code, "utf-8"))

    def _get_node_type(self, node: Node) -> SyntaxNodeType:
        """Map Tree-sitter node types to SyntaxNodeType.

        Args:
            node: Tree-sitter node

        Returns:
            Corresponding SyntaxNodeType
        """
        # Dictionary mapping node types to SyntaxNodeType
        node_type_mapping = {
            # Function-like nodes
            "function": SyntaxNodeType.FUNCTION,
            "function_declaration": SyntaxNodeType.FUNCTION,
            "method_definition": SyntaxNodeType.FUNCTION,
            "arrow_function": SyntaxNodeType.FUNCTION,
            "generator_function": SyntaxNodeType.FUNCTION,
            "generator_function_declaration": SyntaxNodeType.FUNCTION,
            # Class-like nodes
            "class": SyntaxNodeType.CLASS,
            "class_declaration": SyntaxNodeType.CLASS,
            # Other common node types
            "program": SyntaxNodeType.MODULE,
            "statement_block": SyntaxNodeType.BLOCK,
            "block": SyntaxNodeType.BLOCK,
            "formal_parameters": SyntaxNodeType.PARAMETER,
        }

        # Import nodes
        import_types = {"import_statement", "import", "import_declaration"}

        # Statement nodes
        statement_types = {"variable_declaration", "lexical_declaration", "assignment_expression"}

        node_type = node.type

        if node_type in node_type_mapping:
            return node_type_mapping[node_type]
        elif node_type in import_types:
            return SyntaxNodeType.IMPORT
        elif node_type in statement_types:
            return SyntaxNodeType.STATEMENT
        else:
            return SyntaxNodeType.OTHER

    def _get_node_name(self, node: Node, source_code: bytes) -> str:
        """Get a name for a JavaScript/TypeScript node.

        Args:
            node: Tree-sitter node
            source_code: Source code as bytes

        Returns:
            Name of the node
        """
        node_type = node.type

        if node_type in ("function_declaration", "method_definition"):
            # Find the identifier (function/method name)
            for child in node.children:
                if child.type in {"identifier", "property_identifier"}:
                    return get_node_text(child, source_code)
        elif node_type in ("class", "class_declaration"):
            # Find the identifier (class name)
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
        if node.type in ("comment", "string", "number", "true", "false", "null", "undefined"):
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
        # Extract function signature for functions
        if node_type == SyntaxNodeType.FUNCTION:
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

    def extract_syntax_tree(self, code: str, file_extension: str = ".js") -> SyntaxNode:
        """Extract a structured syntax tree from JavaScript or TypeScript code.

        Args:
            code: JavaScript or TypeScript source code
            file_extension: File extension to determine which parser to use

        Returns:
            Root SyntaxNode containing the hierarchical structure
        """
        tree = self.parse_code(code, file_extension)
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

    def find_node_at_position(self, code: str, line: int, col: int, file_extension: str = ".js") -> Optional[SyntaxNode]:
        """Find the syntax node at the given position in JavaScript or TypeScript code.

        Args:
            code: JavaScript or TypeScript source code
            line: Line number (0-indexed)
            col: Column number (0-indexed)
            file_extension: File extension to determine which parser to use

        Returns:
            SyntaxNode at the position, or None if not found
        """
        tree = self.parse_code(code, file_extension)
        source_code = bytes(code, "utf-8")

        # Use the utility function to find the raw Tree-sitter node
        raw_node = find_node_at_position(tree.root_node, line, col, source_code)
        if not raw_node:
            return None

        # Convert to SyntaxNode
        syntax_tree = self.extract_syntax_tree(code, file_extension)
        return syntax_tree.find_node_at_position(line, col)

    def get_function_signature(self, node: SyntaxNode) -> Optional[str]:
        """Extract function signature from a function/method node.

        Args:
            node: SyntaxNode representing a function or method

        Returns:
            Function signature as a string, or None if not applicable
        """
        if not node or not node.raw_node:
            return None

        # Use our internal implementation with the raw node
        return self._get_function_signature(node.raw_node)

    def _get_function_signature(self, node, source_code=None) -> str:
        """
        Extract the function signature from a JavaScript/TypeScript function.

        Args:
            node: The raw tree-sitter node representing the function.
            source_code: The source code string.

        Returns:
            A string representation of the function signature.
        """

        # Validate node
        if node is None or source_code is None:
            return ""

        # List of valid function-like node types
        valid_types = {"function", "function_declaration", "method_definition", "arrow_function", "generator_function", "generator_function_declaration"}

        if node.type not in valid_types:
            return ""

        # Extract function components
        fn_name = self._extract_function_name(node, source_code)
        params = self._extract_function_parameters(node, source_code)
        return_type = self._extract_function_return_type(node, source_code)

        # Build signature
        signature = ""

        # Add function/method keyword for certain types
        if node.type in {"function", "function_declaration", "generator_function", "generator_function_declaration"}:
            signature += "function "

        # Add generator asterisk if applicable
        if node.type in {"generator_function", "generator_function_declaration"}:
            signature += "* "

        # Add function name if available
        if fn_name:
            signature += fn_name

        # Add parameters
        signature += f"({params})"

        # Add return type if available
        if return_type:
            signature += f": {return_type}"

        return signature

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
        Extract the class definition from a JavaScript/TypeScript class declaration.

        Args:
            node: The raw tree-sitter node representing the class.
            source_code: The source code string.

        Returns:
            A string representation of the class definition.
        """

        # Validate node
        if node is None or source_code is None:
            return ""

        if node.type not in {"class", "class_declaration"}:
            return ""

        # Extract class components
        class_name = self._extract_class_name(node, source_code)
        extends_clause = self._extract_extends_clause(node, source_code)
        implements_clause = self._extract_implements_clause(node, source_code)

        # Build definition
        definition = "class"

        if class_name:
            definition += f" {class_name}"

        if extends_clause:
            definition += f" {extends_clause}"

        if implements_clause:
            definition += f" {implements_clause}"

        return definition

    # Helper methods for _get_function_signature
    def _extract_function_name(self, node, source_code):
        """Extract function name from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        # Define valid function declaration types
        function_declaration_types = {"function_declaration", "generator_function_declaration"}

        # Try to get name based on node type
        if node.type in function_declaration_types:
            for child in node.children:
                if child.type == "identifier":
                    return get_node_text(child, source_code)

        elif node.type == "method_definition":
            for child in node.children:
                if child.type == "property_identifier":
                    return get_node_text(child, source_code)

        # For arrow functions, we might not have a direct name
        return ""

    def _extract_function_parameters(self, node, source_code):
        """Extract function parameters from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type in {"formal_parameters", "call_signature"}:
                return get_node_text(child, source_code)

        return ""

    def _extract_function_return_type(self, node, source_code):
        """Extract function return type from the node (TypeScript)."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "type_annotation":
                return get_node_text(child, source_code).replace(":", "").strip()

        return ""

    # Helper methods for _get_class_definition
    def _extract_class_name(self, node, source_code):
        """Extract class name from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        # Define valid identifier types
        identifier_types = {"identifier", "type_identifier"}

        for child in node.children:
            if child.type in identifier_types:
                return get_node_text(child, source_code)

        return ""

    def _extract_extends_clause(self, node, source_code):
        """Extract extends clause from the node."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "class_heritage":
                for heritage_child in child.children:
                    if heritage_child.type == "extends_clause":
                        return get_node_text(heritage_child, source_code)

        return ""

    def _extract_implements_clause(self, node, source_code):
        """Extract implements clause from the node (TypeScript)."""
        from agentic_code_review.llm_refiner.languages.parser_utils import get_node_text

        for child in node.children:
            if child.type == "class_heritage":
                for heritage_child in child.children:
                    if heritage_child.type == "implements_clause":
                        return get_node_text(heritage_child, source_code)

        return ""

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

        # Check if it's a decorated definition (TS has decorators)
        if node.type in {"decorated_definition", "decorator_list"}:
            for child in node.children:
                if child.type == target_type:
                    return child

        return None

    @classmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get the file extensions supported by the JavaScript/TypeScript parser.

        Returns:
            Set of file extensions
        """
        return {".js", ".jsx", ".mjs", ".ts", ".tsx", ".d.ts"}

    @classmethod
    def get_language_name(cls) -> str:
        """Get the name of the language supported by this parser.

        Returns:
            Language name
        """
        return "JavaScript/TypeScript"

    def is_valid_property_or_method(self, node) -> bool:
        """
        Check if the node is a valid property or method.

        Args:
            node: The node to check.

        Returns:
            True if the node is a valid property or method, False otherwise.
        """
        if node is None:
            return False

        valid_types = {"method_definition", "field_definition", "lexical_declaration", "public_field_definition", "property_signature"}

        return node.type in valid_types


# Register the JavaScript/TypeScript parser
ParserRegistry.register_parser(JavaScriptTypeScriptParser)
