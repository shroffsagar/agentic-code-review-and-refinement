"""Process and group PR comments for refinement.

This module provides functionality for processing and grouping PR comments
to prepare them for refinement.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from tree_sitter import Node

from agentic_code_review.github_app.models import PRComment
from .context_extractor import ContextExtractor

logger = logging.getLogger(__name__)


class CommentProcessor:
    """Process and group PR comments for refinement."""

    def __init__(self):
        """Initialize the comment processor."""
        pass

    def group_comments_by_file(self, comments: List[PRComment]) -> Dict[str, List[PRComment]]:
        """Group comments by their file path.

        Args:
            comments: List of comments to group

        Returns:
            Dictionary mapping file paths to their comments
        """
        file_comments: Dict[str, List[PRComment]] = {}
        
        for comment in comments:
            if comment.path not in file_comments:
                file_comments[comment.path] = []
            file_comments[comment.path].append(comment)
            
        return file_comments
        
    def group_comments_by_proximity(self, comments: List[PRComment], proximity_threshold: int = 10) -> List[List[PRComment]]:
        """Group comments by their proximity in the file.

        Comments that are within proximity_threshold lines of each other
        are likely to be related and are grouped together.

        Args:
            comments: List of comments to group
            proximity_threshold: Maximum line distance for comments to be considered related

        Returns:
            List of comment groups
        """
        if not comments:
            return []
            
        # Sort comments by line number
        sorted_comments = sorted(comments, key=lambda c: c.line_number)
        
        # Initialize groups
        groups: List[List[PRComment]] = [[sorted_comments[0]]]
        
        # Group comments based on proximity
        for comment in sorted_comments[1:]:
            last_group = groups[-1]
            last_comment = last_group[-1]
            
            # If the comment is within the proximity threshold of the last comment in the group,
            # add it to the same group
            if abs(comment.line_number - last_comment.line_number) <= proximity_threshold:
                last_group.append(comment)
            else:
                # Start a new group
                groups.append([comment])
                
        return groups
        
    def group_comments_by_code_unit(self, comments: List[PRComment], file_content: str, file_path: str) -> List[List[PRComment]]:
        """Group comments by the code unit (function/method/class) they belong to.

        Comments that belong to the same code unit (function, method, class) are grouped together
        regardless of their line distance.

        Args:
            comments: List of comments to group
            file_content: Content of the file
            file_path: Path to the file

        Returns:
            List of comment groups, where each group contains comments for the same code unit
        """
        if not comments:
            return []
            
        # Create a context extractor
        context_extractor = ContextExtractor()
        
        # Map for tracking which code unit each comment belongs to
        # We'll use the code unit's start line and end line as its identifier
        unit_to_comments: Dict[Optional[Tuple[int, int]], List[PRComment]] = {}
        
        # Assign each comment to its containing code unit
        for comment in comments:
            # Extract context for this comment line
            context_result = context_extractor.extract_context(file_path, file_content, comment.line_number)
            
            if context_result:
                # If we found a context, use the code unit's range as identifier
                _, code_context = context_result
                unit_id = (code_context.start_line, code_context.end_line)
            else:
                # If no context found, use None as the identifier
                unit_id = None
            
            if unit_id not in unit_to_comments:
                unit_to_comments[unit_id] = []
                
            unit_to_comments[unit_id].append(comment)
        
        # Convert the dictionary to a list of lists
        result = list(unit_to_comments.values())
        
        # Sort each group by line number
        for group in result:
            group.sort(key=lambda c: c.line_number)
            
        return result
    
    def group_comments_by_context(self, comments: List[PRComment], node_mapping: Dict[int, Set[int]]) -> Dict[int, List[PRComment]]:
        """Group comments by their code context using node mapping.

        Args:
            comments: List of comments to group
            node_mapping: Mapping from line numbers to node IDs

        Returns:
            Dictionary mapping node IDs to their comments
        """
        node_comments: Dict[int, List[PRComment]] = {}
        
        for comment in comments:
            line_number = comment.line_number
            
            # Find nodes for this line
            if line_number in node_mapping:
                nodes = node_mapping[line_number]
                
                # Use the first node (usually the most specific)
                if nodes:
                    node_id = next(iter(nodes))
                    
                    if node_id not in node_comments:
                        node_comments[node_id] = []
                    node_comments[node_id].append(comment)
            else:
                # If no node is found, log a warning
                logger.warning(f"No node found for comment at line {line_number}")
                
        return node_comments 