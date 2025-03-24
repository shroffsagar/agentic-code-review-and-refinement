"""Parser registry for managing language-specific parsers.

This module provides functionality to register and retrieve parsers for different languages.
"""

import os
from typing import ClassVar, Optional

from agentic_code_review.llm_refiner.languages.base_parser import BaseParser


class ParserRegistry:
    """Registry for language-specific parsers."""

    _parsers: ClassVar[dict[str, type[BaseParser]]] = {}
    _extension_map: ClassVar[dict[str, type[BaseParser]]] = {}
    _instances: ClassVar[dict[str, BaseParser]] = {}

    @classmethod
    def register_parser(cls, parser_class: type[BaseParser]) -> None:
        """Register a parser class for a specific language.

        Args:
            parser_class: The parser class to register
        """
        language_name = parser_class.get_language_name()
        cls._parsers[language_name] = parser_class

        # Map file extensions to this parser
        for ext in parser_class.get_supported_extensions():
            cls._extension_map[ext] = parser_class

    @classmethod
    def get_parser_for_language(cls, language_name: str) -> Optional[BaseParser]:
        """Get a parser instance for a specific language.

        Args:
            language_name: Name of the language

        Returns:
            Parser instance for the language or None if not found
        """
        if language_name not in cls._parsers:
            return None

        if language_name not in cls._instances:
            parser_class = cls._parsers[language_name]
            parser = parser_class()
            parser.setup_parser()
            cls._instances[language_name] = parser

        return cls._instances[language_name]

    @classmethod
    def get_parser_for_file(cls, file_path: str) -> Optional[BaseParser]:
        """Get a parser instance for a specific file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            Parser instance for the file or None if no parser supports this file type
        """
        _, ext = os.path.splitext(file_path.lower())
        if ext not in cls._extension_map:
            return None

        parser_class = cls._extension_map[ext]
        language_name = parser_class.get_language_name()

        return cls.get_parser_for_language(language_name)

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get a list of supported language names.

        Returns:
            List of supported language names
        """
        return list(cls._parsers.keys())

    @classmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get a set of all supported file extensions.

        Returns:
            Set of supported file extensions
        """
        return set(cls._extension_map.keys())
