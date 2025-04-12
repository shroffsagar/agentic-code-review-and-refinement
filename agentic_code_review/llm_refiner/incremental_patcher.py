"""Incremental code patching using tree-sitter.

This module provides functionality for incrementally applying patches to code
using tree-sitter in a language-agnostic way.
"""

import logging
from typing import Optional

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

from agentic_code_review.utils.code_formatter import format_code

from .context_extractor import ContextExtractor
from .models import FileModification, PatchResult

logger = logging.getLogger(__name__)

# Maximum number of characters to show in error context
MAX_ERROR_CONTEXT_LENGTH = 50


class IncrementalPatcher:
    """Apply code changes incrementally using tree-sitter."""

    def __init__(self, file_content: str, file_path: str):
        """Initialize the incremental patcher.

        Args:
            file_content: The initial file content
            file_path: The path to the file
        """
        self.current_content = file_content
        self.file_path = file_path
        self.extractor = ContextExtractor()
        self.language_id = self.extractor._detect_language(file_path)

        # Initialize the tree if language is supported
        if self.language_id:
            try:
                parser = get_parser(self.language_id)
                self.tree = parser.parse(bytes(file_content, 'utf-8'))
            except Exception as e:
                logger.error(f"Failed to parse code during initialization: {e}")
                self.tree = None
        else:
            self.tree = None

        self.modifications: list[FileModification] = []

    def get_node_at_line(self, line: int) -> Optional[Node]:
        """Get the node at a specific line.

        Args:
            line: The line number (1-based)

        Returns:
            The node at that line, or None if not found
        """
        if not self.tree:
            return None

        return self.extractor.find_node_at_line(self.tree, line)

    def get_containing_code_unit(self, line: int) -> Optional[Node]:
        """Get the containing code unit for a line.

        Args:
            line: The line number (1-based)

        Returns:
            The node representing the containing code unit, or None if not found
        """
        node = self.get_node_at_line(line)
        if not node:
            return None

        return self.extractor.find_containing_code_unit(node)

    def get_node_text(self, node: Node) -> str:
        """Get the text for a node.

        Args:
            node: The node

        Returns:
            The text of the node
        """
        if not node:
            return ""

        start_byte = node.start_byte
        end_byte = node.end_byte
        return self.current_content[start_byte:end_byte]

    def register_modification(self, node: Node, new_text: str, suggestion_ids: list[str]) -> FileModification:
        """Register a modification to be applied.

        Args:
            node: The node to modify
            new_text: The new text for the node
            suggestion_ids: The IDs of the suggestions that prompted this modification

        Returns:
            The registered FileModification
        """
        original_text = self.get_node_text(node)

        # Store both line and byte positions for more reliable tracking
        modification = FileModification(
            file_path=self.file_path,
            original_node_text=original_text,
            modified_text=new_text,
            start_line=node.start_point[0] + 1,  # Convert to 1-based
            end_line=node.end_point[0] + 1,      # Convert to 1-based
            start_byte=node.start_byte,          # Store byte positions for precise tracking
            end_byte=node.end_byte,
            suggestion_ids=suggestion_ids
        )

        self.modifications.append(modification)
        return modification

    def register_imports_modification(self, new_imports: str, suggestion_ids: list[str]) -> FileModification:
        """Register a modification to add imports at the top of the file.

        Args:
            new_imports: The new import statements to add.
            suggestion_ids: IDs of the suggestions prompting this modification.

        Returns:
            A FileModification instance, or None if no new imports are provided.
        """
        if not new_imports or new_imports.strip() == "":
            return None  # Nothing to insert

        # Find where to insert imports (after any header items)
        insertion_line, insertion_byte = self._find_imports_insertion_point()

        # Check if we need to add a newline before the import
        modified_text = new_imports + "\n"  # Always end with a newline

        # If we're not at the beginning of the file, check if we need to insert a newline
        if insertion_byte > 0:
            # Check if there's already a newline at the insertion point
            needs_newline = insertion_byte < len(self.current_content) and self.current_content[insertion_byte-1] != '\n'
            if needs_newline:
                # If there's no newline before our insertion point, add one
                modified_text = "\n" + modified_text
                logger.debug(f"Adding leading newline before imports at byte position {insertion_byte}")
            else:
                logger.debug(f"No need for leading newline before imports at byte position {insertion_byte}")

        modification = FileModification(
            file_path=self.file_path,
            original_node_text="",  # We're inserting new content
            modified_text=modified_text,  # Use our properly formatted text
            start_line=insertion_line + 1,  # Convert 0-based to 1-based
            end_line=insertion_line + 1,
            start_byte=insertion_byte,
            end_byte=insertion_byte,
            suggestion_ids=suggestion_ids
        )

        # Apply this modification first
        self.modifications.insert(0, modification)
        return modification

    def _find_imports_insertion_point(self) -> tuple[int, int]:
        """
        Determine the best insertion point for import statements.

        Priority:
          1. After the last import statement.
          2. For Java, after the package declaration if no imports.
          3. For Python, after the module docstring if no imports.
          4. For JS/TS, after header comments or hashbang.
          5. Otherwise, beginning of the file.

        Returns:
            A tuple (line_number, byte_position) for the insertion point.
        """
        if not self.tree or not self.tree.root_node.children:
            return (0, 0)  # Empty file or parse issue

        last_import = None
        last_package = None
        module_docstring = None
        last_header = None

        # Iterate through top-level nodes only
        for idx, node in enumerate(self.tree.root_node.children):
            # For Python files
            if self.language_id == "python":
                # If the very first node is a docstring, mark it
                if idx == 0 and node.type == "string":
                    module_docstring = node
                elif node.type in ("import_statement", "import_from_statement"):
                    last_import = node
                # Stop when a non-header element is encountered
                elif node.type not in ("string", "import_statement", "import_from_statement"):
                    break

            # For Java files
            elif self.language_id == "java":
                if node.type == "package_declaration":
                    last_package = node
                elif node.type == "import_declaration":
                    last_import = node
                else:
                    break

            # For JavaScript/TypeScript
            elif self.language_id in ("javascript", "typescript"):
                if node.type == "import_statement":
                    last_import = node
                elif node.type in ("comment", "hashbang"):
                    # Save the header comment that appears last
                    last_header = node
                else:
                    break

            # For any unsupported languages, we default to the top
            else:
                break

        # Choose insertion point based on priority
        if last_import:
            return (last_import.end_point[0], last_import.end_byte)
        if self.language_id == "java" and last_package:
            return (last_package.end_point[0], last_package.end_byte)
        if self.language_id == "python" and module_docstring:
            return (module_docstring.end_point[0], module_docstring.end_byte)
        if self.language_id in ("javascript", "typescript") and last_header:
            return (last_header.end_point[0], last_header.end_byte)
        return (0, 0)

    def apply_modification(self, modification: FileModification) -> PatchResult:
        """Apply a single modification to the current content.

        Args:
            modification: The modification to apply

        Returns:
            Result of the patching operation
        """
        if not self.tree and self.language_id:
            # Try to parse the current content if we don't have a tree
            try:
                parser = get_parser(self.language_id)
                self.tree = parser.parse(bytes(self.current_content, 'utf-8'))
            except Exception as e:
                logger.error(f"Failed to parse code during modification application: {e}")
                self.tree = None

        if self.tree:
            # Use tree-sitter for incremental updates
            return self._apply_with_tree_sitter(modification)
        else:
            # If tree-sitter isn't available, fail gracefully
            return PatchResult(
                success=False,
                error_message="Cannot apply changes without tree-sitter support for this language"
            )

    def _apply_with_tree_sitter(self, modification: FileModification) -> PatchResult:
        """Apply a modification using tree-sitter for incremental updates.

        Args:
            modification: The modification to apply

        Returns:
            Result of the patching operation
        """
        try:
            # Use byte positions to find and apply changes
            # This is more reliable than line numbers which can shift
            start_byte = modification.start_byte
            end_byte = modification.end_byte

            # Verify the content at the byte positions
            current_content_at_position = self.current_content[start_byte:end_byte]

            # If content has changed, we need to find the node by traversal
            if current_content_at_position.strip() != modification.original_node_text.strip():
                logger.debug("Content at byte positions has changed, locating node by traversal")
                # Try to find the node by searching the tree
                target_node = self._find_node_by_content(modification.original_node_text)
                if not target_node:
                    return PatchResult(
                        success=False,
                        error_message="Could not find matching node for modification"
                    )
                # Update byte positions to the new location
                start_byte = target_node.start_byte
                end_byte = target_node.end_byte

            # Calculate the new end position in terms of bytes and points
            new_end_byte = start_byte + len(modification.modified_text)

            # Calculate the new end point (line, column)
            start_point = self._get_point_from_byte(start_byte)
            old_end_point = self._get_point_from_byte(end_byte)

            lines = modification.modified_text.split('\n')
            if len(lines) == 1:
                # Single line change
                new_end_point = (
                    start_point[0],
                    start_point[1] + len(lines[0])
                )
            else:
                # Multi-line change
                new_end_point = (
                    start_point[0] + len(lines) - 1,
                    len(lines[-1])
                )

            # Apply the edit to tree-sitter's tree
            self.tree.edit(
                start_byte=start_byte,
                old_end_byte=end_byte,
                new_end_byte=new_end_byte,
                start_point=start_point,
                old_end_point=old_end_point,
                new_end_point=new_end_point
            )

            # Update the content
            updated_content = (
                self.current_content[:start_byte] +
                modification.modified_text +
                self.current_content[end_byte:]
            )

            # Reparse the content to keep the tree in sync, using incremental parsing
            parser = get_parser(self.language_id)
            self.tree = parser.parse(bytes(updated_content, 'utf-8'), self.tree)

            # Update current content
            self.current_content = updated_content

            # Update byte positions for all remaining modifications
            self._update_modifications_after_edit(
                edit_start_byte=start_byte,
                old_end_byte=end_byte,
                new_end_byte=new_end_byte
            )

            return PatchResult(
                success=True,
                modified_content=self.current_content
            )

        except Exception as e:
            logger.error(f"Failed to apply modification with tree-sitter: {e}")
            return PatchResult(
                success=False,
                error_message=f"Failed to apply modification: {e!s}"
            )

    def _get_point_from_byte(self, byte_position: int) -> tuple[int, int]:
        """Get line and column coordinates from a byte position.

        Args:
            byte_position: The byte position in the content

        Returns:
            Tuple of (line, column) coordinates
        """
        # Get content up to the byte position
        content_before = self.current_content[:byte_position]

        # Count lines and get the last line
        lines = content_before.split('\n')
        line = len(lines) - 1  # 0-based

        # Get column in the last line
        col = len(lines[-1])

        return (line, col)

    def _find_node_by_content(self, content: str) -> Optional[Node]:
        """Find a node by its content.

        Args:
            content: The content to search for

        Returns:
            The node with matching content, or None if not found
        """
        if not self.tree:
            return None

        # Normalize content for comparison
        normalized_content = content.strip()

        # Walk the tree looking for matching content
        for node in self._walk_tree(self.tree.root_node):
            node_text = self.get_node_text(node).strip()
            if node_text == normalized_content:
                return node

        return None

    def _update_modifications_after_edit(self, edit_start_byte: int, old_end_byte: int, new_end_byte: int) -> None:
        """Update byte positions of pending modifications after an edit.

        Args:
            edit_start_byte: Start byte of the edit
            old_end_byte: Old end byte of the edit
            new_end_byte: New end byte of the edit
        """
        # Calculate the delta (how many bytes were added or removed)
        delta = new_end_byte - old_end_byte

        for i, mod in enumerate(self.modifications):
            # Skip modifications that have already been applied
            if mod.start_byte == edit_start_byte and mod.end_byte == old_end_byte:
                continue

            # Update byte positions based on edit location
            if mod.start_byte > old_end_byte:
                # If modification starts after the edit, shift by delta
                self.modifications[i].start_byte += delta
                self.modifications[i].end_byte += delta
            elif mod.start_byte < edit_start_byte and mod.end_byte > edit_start_byte:
                # If edit happens inside a modification that hasn't been applied yet,
                # extend the end position by delta
                self.modifications[i].end_byte += delta

    def _walk_tree(self, node: Node) -> list[Node]:
        """Walk the tree in a depth-first manner.

        Args:
            node: The root node

        Returns:
            List of all nodes in the tree
        """
        result = [node]
        for child in node.children:
            result.extend(self._walk_tree(child))
        return result

    def apply_all_modifications(self) -> PatchResult:
        """Apply all registered modifications.

        Returns:
            Result of the patching operation
        """
        if not self.modifications:
            return PatchResult(
                success=True,
                modified_content=self.current_content
            )

        # Apply each modification, in order
        # Each successful application will update the tree and byte positions
        for i, modification in enumerate(self.modifications):
            logger.info(f"Applying modification {i+1}/{len(self.modifications)}")
            result = self.apply_modification(modification)
            if not result.success:
                return result

        # Format the code if the language is supported
        if self.language_id:
            try:
                # Apply code formatting to the entire file content after all modifications have been applied
                # This is intentional - we format the complete file after all modifications, not each modification
                formatted_content = format_code(self.current_content, self.language_id)
                if formatted_content:
                    # Update the current content with formatted code
                    self.current_content = formatted_content
                    logger.info(f"Applied code formatting to {self.file_path}")

                    # Re-parse the tree to keep it in sync with the formatted content
                    try:
                        parser = get_parser(self.language_id)
                        self.tree = parser.parse(bytes(self.current_content, 'utf-8'))
                        logger.debug("Successfully re-parsed tree after formatting")
                    except Exception as parse_error:
                        logger.warning(f"Failed to re-parse tree after formatting: {parse_error}")
                        # Continue with the updated content but stale tree
                else:
                    logger.warning(f"Code formatting failed for {self.file_path}, using unformatted content")
            except Exception as e:
                logger.error(f"Error during code formatting for {self.file_path}: {e}")
                # Continue with unformatted content

        return PatchResult(
            success=True,
            modified_content=self.current_content
        )

    def validate_result(self) -> bool:
        """Validate that the resulting code is syntactically valid.

        Returns:
            True if the code is valid, False otherwise
        """
        if not self.language_id:
            # We can't validate without a language
            logger.info("Skipping validation for unsupported language")
            return True

        # Parse the code from scratch
        try:
            parser = get_parser(self.language_id)
            tree = parser.parse(bytes(self.current_content, 'utf-8'))
            if not tree:
                logger.error("Failed to parse modified code")
                return False
        except Exception as e:
            logger.error(f"Failed to parse modified code: {e}")
            return False

        # Check for syntax errors, but report details
        error_count = 0
        error_messages = []

        def count_errors(node):
            nonlocal error_count
            if node.type == 'ERROR':
                error_count += 1
                context = (
                    self.get_node_text(node)[:MAX_ERROR_CONTEXT_LENGTH] + "..."
                    if len(self.get_node_text(node)) > MAX_ERROR_CONTEXT_LENGTH
                    else self.get_node_text(node)
                )
                error_msg = f"Syntax error at line {node.start_point[0]+1}: {context}"
                error_messages.append(error_msg)
                return True

            has_error = False
            for child in node.children:
                if count_errors(child):
                    has_error = True
            return has_error

        has_errors = count_errors(tree.root_node)

        # Log detailed error information
        if has_errors:
            logger.error(f"Found {error_count} syntax errors in modified code")
            for msg in error_messages[:5]:  # Show only first 5 errors
                logger.error(f"  {msg}")

            return False
        else:
            return True

    def get_implemented_suggestions(self) -> list[str]:
        """Get the IDs of all implemented suggestions.

        Returns:
            List of implemented suggestion IDs
        """
        suggestion_ids = []
        for modification in self.modifications:
            suggestion_ids.extend(modification.suggestion_ids)
        return suggestion_ids
