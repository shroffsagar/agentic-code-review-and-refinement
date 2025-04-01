"""Context extraction for code using tree-sitter.

This module provides functionality for extracting relevant code context
from source files using tree-sitter in a language-agnostic way.
"""

import logging
from typing import Optional, Dict, Any, Tuple, List
import os

from tree_sitter import Parser, Language, Tree, Node
from tree_sitter_languages import get_language

from .models import CodeContext

logger = logging.getLogger(__name__)


class ContextExtractor:
    """Extract code context using tree-sitter in a language-agnostic way."""
    
    def __init__(self):
        """Initialize the context extractor."""
        self._parsers: Dict[str, Parser] = {}
        self._languages: Dict[str, Language] = {}
        
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect the language based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language identifier compatible with tree-sitter, or None if not detected
        """
        _, ext = os.path.splitext(file_path.lower())
        
        # Simple mapping of file extensions to tree-sitter language identifiers
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rb': 'ruby',
            '.rs': 'rust',
            '.php': 'php',
            '.cs': 'c_sharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.html': 'html',
            '.json': 'json',
            '.md': 'markdown',
        }
        
        if ext in extension_map:
            return extension_map[ext]
            
        logger.warning(f"Could not detect language for file extension: {ext}")
        return None
        
    def _get_language(self, language_id: str) -> Optional[Language]:
        """Get a tree-sitter language by ID.
        
        Args:
            language_id: The language identifier
            
        Returns:
            The tree-sitter Language instance, or None if not available
        """
        if language_id in self._languages:
            return self._languages[language_id]
            
        try:
            language = get_language(language_id)
            if language:
                self._languages[language_id] = language
                return language
        except Exception as e:
            logger.error(f"Failed to load language {language_id}: {e}")
            
        return None
        
    def _get_parser(self, language_id: str) -> Optional[Parser]:
        """Get a parser for the specified language.
        
        Args:
            language_id: The language identifier
            
        Returns:
            A configured Parser instance, or None if language is not available
        """
        if language_id in self._parsers:
            return self._parsers[language_id]
            
        language = self._get_language(language_id)
        if not language:
            return None
            
        parser = Parser()
        parser.set_language(language)
        self._parsers[language_id] = parser
        return parser
    
    def parse_code(self, code: str, language_id: str) -> Optional[Tree]:
        """Parse code with tree-sitter.
        
        Args:
            code: The source code to parse
            language_id: The language identifier
            
        Returns:
            The parse tree, or None if parsing failed
        """
        parser = self._get_parser(language_id)
        if not parser:
            return None
            
        try:
            return parser.parse(bytes(code, 'utf-8'))
        except Exception as e:
            logger.error(f"Failed to parse code: {e}")
            return None
            
    def find_node_at_line(self, tree: Tree, line: int) -> Optional[Node]:
        """Find the node at a specific line.
        
        Args:
            tree: The parse tree
            line: The line number (1-based)
            
        Returns:
            The node at that line, or None if not found
        """
        # Convert to 0-based index
        zero_based_line = line - 1
        
        # Find the node at this position (start of line)
        return tree.root_node.descendant_for_point_range(
            (zero_based_line, 0),
            (zero_based_line, 0)
        )
        
    def find_containing_code_unit(self, node: Node) -> Node:
        """Find the containing code unit for a node.
        
        This method walks up the tree to find a node that represents a complete
        code unit such as a function, class, or other significant structure.
        It uses heuristics that work across languages.
        
        Args:
            node: The starting node
            
        Returns:
            The node representing the containing code unit
        """
        if not node:
            return None
            
        # Start with the given node
        current = node
        best_candidate = node
        
        # Walk up the tree looking for a code unit
        while current.parent:
            parent = current.parent
            
            # If we've reached the root, stop
            if parent.parent is None:
                break
                
            current = parent
            
            # Heuristics for identifying code units:
            # 1. Spans multiple lines
            # 2. Has multiple children
            # 3. Has meaningful depth in the tree
            spans_multiple_lines = current.end_point[0] - current.start_point[0] >= 2
            has_multiple_children = len([c for c in current.children if c.is_named]) >= 2
            
            # Check if this looks like a complete code unit
            if spans_multiple_lines and has_multiple_children:
                # Higher-quality candidate than what we've seen so far
                best_candidate = current
                
                # If this node has a type that suggests a definition, prefer it
                node_type = current.type.lower()
                definition_indicators = ['function', 'method', 'class', 'def', 'procedure']
                
                if any(indicator in node_type for indicator in definition_indicators):
                    # This is likely a function, method, or class definition
                    return current
        
        return best_candidate
        
    def extract_context(self, file_path: str, file_content: str, line: int) -> Optional[Tuple[str, CodeContext]]:
        """Extract code context for a specific line.
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
            line: Line number (1-based)
            
        Returns:
            Tuple of (code_text, code_context) or None if extraction failed
        """
        # Detect language
        language_id = self._detect_language(file_path)
        if not language_id:
            logger.warning(f"Could not detect language for {file_path}")
            return self._fallback_context_extraction(file_content, line, file_path)
            
        # Parse the code
        tree = self.parse_code(file_content, language_id)
        if not tree:
            logger.warning(f"Could not parse {file_path}")
            return self._fallback_context_extraction(file_content, line, file_path)
            
        # Find the node at the specified line
        node = self.find_node_at_line(tree, line)
        if not node:
            logger.warning(f"Could not find node at line {line} in {file_path}")
            return self._fallback_context_extraction(file_content, line, file_path)
            
        # Find the containing code unit
        unit_node = self.find_containing_code_unit(node)
        if not unit_node:
            logger.warning(f"Could not find containing code unit at line {line} in {file_path}")
            return self._fallback_context_extraction(file_content, line, file_path)
            
        # Extract the code context
        start_byte = unit_node.start_byte
        end_byte = unit_node.end_byte
        code_text = file_content[start_byte:end_byte]
        
        # Create context object
        context = CodeContext(
            file_path=file_path,
            start_line=unit_node.start_point[0] + 1,  # Convert to 1-based
            end_line=unit_node.end_point[0] + 1,      # Convert to 1-based
            node_type=unit_node.type
        )
        
        return code_text, context
        
    def _fallback_context_extraction(self, content: str, line: int, file_path: str) -> Optional[Tuple[str, CodeContext]]:
        """Extract context using a simple line-based fallback approach.
        
        Args:
            content: File content
            line: Line number (1-based)
            file_path: Path to the file
            
        Returns:
            Tuple of (code_text, code_context) using a simple approach
        """
        lines = content.splitlines()
        if not lines or line > len(lines):
            return None
            
        # Extract a window of lines around the target line
        # Use a larger window to increase chances of capturing the whole code unit
        window_size = 15
        start_line = max(1, line - window_size)
        end_line = min(len(lines), line + window_size)
        
        # Extract the lines
        extracted_lines = lines[start_line-1:end_line]
        code_text = '\n'.join(extracted_lines)
        
        # Create context object
        context = CodeContext(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            node_type=None  # No node type available in fallback mode
        )
        
        return code_text, context
        
    def extract_file_level_context(self, file_path: str, file_content: str) -> Dict[str, Any]:
        """Extract file-level context information to provide metadata about the file.
        
        This method captures key information about the file to help the LLM understand
        the file's context and dependencies, including:
        
        1. File path: The full path to the file in the repository
        2. File extension: The file extension (e.g., '.py', '.js')
        3. Language: The programming language detected based on the file extension
        4. Imports: A list of import statements found in the first 50 lines of the file,
           using language-specific detection patterns for Python, JavaScript, TypeScript,
           Java, Rust, and Go
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
            
        Returns:
            Dictionary with file-level context information containing at minimum:
            {
                "file_path": str,            # Full path to the file
                "extension": str,            # File extension with dot (e.g., '.py')
                "language": Optional[str],   # Detected programming language or None
                "imports": List[str]         # List of import statements found
            }
        """
        context = {
            "file_path": file_path,
            "extension": os.path.splitext(file_path)[1],
            "imports": [],
            "language": self._detect_language(file_path)
        }
        
        # Extract imports using simple line-based analysis
        # This is a basic implementation that works across many languages
        import_indicators = {
            'python': ['import ', 'from '],
            'javascript': ['import ', 'require('],
            'typescript': ['import ', 'require('],
            'java': ['import '],
            'rust': ['use '],
            'go': ['import '],
        }
        
        lang = context["language"]
        if lang in import_indicators:
            indicators = import_indicators[lang]
            lines = file_content.splitlines()
            
            for line in lines[:50]:  # Look only at the first 50 lines
                line_stripped = line.strip()
                if any(line_stripped.startswith(indicator) for indicator in indicators):
                    context["imports"].append(line_stripped)
        
        return context 