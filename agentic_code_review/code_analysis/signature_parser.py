"""Signature parsing for different programming languages.

This module provides functionality for parsing function and method signatures
in different programming languages.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from tree_sitter import Node

from .language_config import LanguageRegistry

logger = logging.getLogger(__name__)


@dataclass
class Parameter:
    """Represents a function parameter with its type and name."""

    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


@dataclass
class Signature:
    """Represents a function or method signature."""

    name: str
    parameters: list[Parameter]
    return_type: Optional[str] = None
    is_method: bool = False
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False


class SignatureParser:
    """Parser for function and method signatures."""

    def __init__(self):
        """Initialize the signature parser."""
        self.language_registry = LanguageRegistry()

    def parse_signature(self, node: Node, language: str) -> Optional[Signature]:
        """Parse a function or method signature from a tree-sitter node.

        Args:
            node: The tree-sitter node to parse
            language: The programming language

        Returns:
            A Signature object if successful, None otherwise
        """
        config = self.language_registry.get_config(language)
        if not config:
            logger.error(f"No configuration found for language: {language}")
            return None

        if language == "python":
            return self._parse_python_signature(node, config)
        else:
            logger.error(f"Signature parsing not implemented for language: {language}")
            return None

    def _parse_python_signature(self, node: Node, config: "LanguageConfig") -> Optional[Signature]:
        """Parse a Python function or method signature.

        Args:
            node: The tree-sitter node to parse
            config: The language configuration

        Returns:
            A Signature object if successful, None otherwise
        """
        try:
            # Get the name
            name_node = next((child for child in node.children if child.type == "identifier"), None)
            if not name_node:
                return None
            name = name_node.text.decode("utf-8")

            # Get parameters
            params_node = next((child for child in node.children if child.type == "parameters"), None)
            if not params_node:
                return None
            parameters = self._parse_python_parameters(params_node)

            # Determine if it's a method
            is_method = node.type == config.node_types["method"]

            # Check for async
            is_async = any(child.type == "async" for child in node.children)

            # Check for static/class method decorators
            is_static = False
            is_classmethod = False
            if node.parent and node.parent.type == "decorated_definition":
                for decorator in node.parent.children:
                    if decorator.type == "decorator":
                        decorator_name = decorator.children[0].text.decode("utf-8")
                        if decorator_name == "staticmethod":
                            is_static = True
                        elif decorator_name == "classmethod":
                            is_classmethod = True

            return Signature(name=name, parameters=parameters, is_method=is_method, is_async=is_async, is_static=is_static, is_classmethod=is_classmethod)

        except Exception as e:
            logger.error(f"Failed to parse Python signature: {e}")
            return None

    def _parse_python_parameters(self, params_node: Node) -> list[Parameter]:
        """Parse Python function parameters.

        Args:
            params_node: The parameters node to parse

        Returns:
            List of Parameter objects
        """
        parameters = []
        for child in params_node.children:
            if child.type == "identifier":
                # Simple parameter without type or default
                parameters.append(Parameter(name=child.text.decode("utf-8")))
            elif child.type == "typed_parameter":
                # Parameter with type annotation
                name = next((c.text.decode("utf-8") for c in child.children if c.type == "identifier"), None)
                type_annotation = next((c.text.decode("utf-8") for c in child.children if c.type == "type"), None)
                if name:
                    parameters.append(Parameter(name=name, type_annotation=type_annotation))
            elif child.type == "default_parameter":
                # Parameter with default value
                name = next((c.text.decode("utf-8") for c in child.children if c.type == "identifier"), None)
                default_value = next((c.text.decode("utf-8") for c in child.children if c.type == "expression"), None)
                if name:
                    parameters.append(Parameter(name=name, default_value=default_value))

        return parameters
