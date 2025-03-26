"""Language-specific configurations for code analysis.

This module provides language-specific configurations and grammar loading
for different programming languages supported by tree-sitter.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Set

from tree_sitter import Language

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    """Configuration for a specific programming language."""

    name: str
    file_extensions: Set[str]
    grammar_path: str
    node_types: Dict[str, str]
    query_templates: Dict[str, str]


class LanguageRegistry:
    """Registry for managing language configurations."""

    _instance: Optional["LanguageRegistry"] = None
    _languages: Dict[str, Language] = {}
    _configs: Dict[str, LanguageConfig] = {}

    def __new__(cls) -> "LanguageRegistry":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry with supported languages."""
        if not self._configs:
            self._initialize_configs()

    def _initialize_configs(self) -> None:
        """Initialize language configurations."""
        # Python configuration
        self._configs["python"] = LanguageConfig(
            name="python",
            file_extensions={".py"},
            grammar_path="vendor/tree-sitter-python",
            node_types={
                "function": "function_definition",
                "method": "method_definition",
                "class": "class_definition",
                "module": "module",
                "import": "import_statement",
                "import_from": "import_from_statement",
            },
            query_templates={
                "function_definitions": """
                (function_definition
                    name: (identifier) @function.name
                    parameters: (parameters) @function.params
                    body: (block) @function.body)
                """,
                "class_definitions": """
                (class_definition
                    name: (identifier) @class.name
                    body: (block) @class.body)
                """,
                "method_definitions": """
                (method_definition
                    name: (identifier) @method.name
                    parameters: (parameters) @method.params
                    body: (block) @method.body)
                """,
            },
        )

        # Add more language configurations as needed

    def get_language(self, language_name: str) -> Optional[Language]:
        """Get a tree-sitter Language instance for the specified language.

        Args:
            language_name: Name of the language to get

        Returns:
            A tree-sitter Language instance, or None if not found
        """
        if language_name not in self._languages:
            config = self._configs.get(language_name)
            if not config:
                logger.error(f"No configuration found for language: {language_name}")
                return None

            try:
                grammar_path = Path(config.grammar_path)
                if not grammar_path.exists():
                    logger.error(f"Grammar path does not exist: {grammar_path}")
                    return None

                self._languages[language_name] = Language(
                    str(grammar_path / "src" / f"{language_name}.so"),
                    language_name
                )
            except Exception as e:
                logger.error(f"Failed to load language {language_name}: {e}")
                return None

        return self._languages[language_name]

    def get_config(self, language_name: str) -> Optional[LanguageConfig]:
        """Get the configuration for a specific language.

        Args:
            language_name: Name of the language to get config for

        Returns:
            The language configuration, or None if not found
        """
        return self._configs.get(language_name)

    def get_language_for_file(self, file_path: str) -> Optional[str]:
        """Get the language name for a file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            The language name, or None if not found
        """
        extension = Path(file_path).suffix.lower()
        for name, config in self._configs.items():
            if extension in config.file_extensions:
                return name
        return None

    def is_supported_language(self, language_name: str) -> bool:
        """Check if a language is supported.

        Args:
            language_name: Name of the language to check

        Returns:
            True if the language is supported, False otherwise
        """
        return language_name in self._configs 