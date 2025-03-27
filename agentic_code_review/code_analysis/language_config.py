"""Language-specific configurations for code analysis.

This module provides language-specific configurations and grammar loading
for different programming languages supported by tree-sitter.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tree_sitter import Language
from tree_sitter_languages import get_language

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    """Configuration for a specific programming language."""

    name: str
    file_extensions: set[str]
    node_types: dict[str, str]
    query_templates: dict[str, str]


class LanguageRegistry:
    """Registry for managing language configurations."""

    _instance: Optional["LanguageRegistry"] = None
    _languages: dict[str, Language] = {}
    _configs: dict[str, LanguageConfig] = {}

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
        logger.debug(f"Attempting to get language: {language_name}")
        if language_name not in self._languages:
            config = self._configs.get(language_name)
            if not config:
                logger.error(f"No configuration found for language: {language_name}")
                return None

            try:
                logger.debug(f"Calling tree-sitter-languages.get_language({language_name})")
                # Use tree-sitter-languages to get the pre-built grammar
                language = get_language(language_name)
                if language is None:
                    logger.error(f"Failed to get language {language_name} from tree-sitter-languages")
                    return None
                
                logger.debug(f"Successfully got language instance for {language_name}")
                # Store the language instance directly
                self._languages[language_name] = language
            except Exception as e:
                logger.error(f"Failed to load language {language_name}: {e}", exc_info=True)
                return None

        logger.debug(f"Returning cached language instance for {language_name}")
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
