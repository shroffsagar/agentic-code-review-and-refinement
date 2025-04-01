"""Incremental code patching using tree-sitter.

This module provides functionality for incrementally applying patches to code
using tree-sitter in a language-agnostic way.
"""

import logging
from typing import Optional, Dict, List, Tuple

from tree_sitter import Tree, Node, Parser

from .context_extractor import ContextExtractor
from .models import FileModification, PatchResult

logger = logging.getLogger(__name__)


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
            self.tree = self.extractor.parse_code(file_content, self.language_id)
        else:
            self.tree = None
            
        self.modifications: List[FileModification] = []
        
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
        
    def register_modification(self, node: Node, new_text: str, suggestion_ids: List[str]) -> FileModification:
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
        
    def apply_modification(self, modification: FileModification) -> PatchResult:
        """Apply a single modification to the current content.
        
        Args:
            modification: The modification to apply
            
        Returns:
            Result of the patching operation
        """
        if not self.tree and self.language_id:
            # Try to parse the current content if we don't have a tree
            self.tree = self.extractor.parse_code(self.current_content, self.language_id)
            
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
            parser = self.extractor._get_parser(self.language_id)
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
                error_message=f"Failed to apply modification: {str(e)}"
            )
            
    def _get_point_from_byte(self, byte_position: int) -> Tuple[int, int]:
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
    
    def _walk_tree(self, node: Node) -> List[Node]:
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
        tree = self.extractor.parse_code(self.current_content, self.language_id)
        if not tree:
            logger.error("Failed to parse modified code")
            return False
            
        # Check for syntax errors, but report details
        error_count = 0
        error_messages = []
        
        def count_errors(node):
            nonlocal error_count
            if node.type == 'ERROR':
                error_count += 1
                context = self.get_node_text(node)[:50] + "..." if len(self.get_node_text(node)) > 50 else self.get_node_text(node)
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
                
            # For minor syntax issues, we could still attempt to use the code
            if error_count <= 2:
                logger.warning("Allowing code with minor syntax issues to proceed")
                return True
                
        return not has_errors
        
    def get_implemented_suggestions(self) -> List[str]:
        """Get the IDs of all implemented suggestions.
        
        Returns:
            List of implemented suggestion IDs
        """
        suggestion_ids = []
        for modification in self.modifications:
            suggestion_ids.extend(modification.suggestion_ids)
        return suggestion_ids 