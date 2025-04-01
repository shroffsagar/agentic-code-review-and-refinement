"""Data models for the language-agnostic refinement agent.

This module contains Pydantic models used for structured data exchange in the refinement agent.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CodeContext:
    """Context information about a code segment."""

    def __init__(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        node_type: Optional[str] = None,
    ):
        """Initialize the code context.
        
        Args:
            file_path: Path to the file containing the code
            start_line: Start line number (1-based)
            end_line: End line number (1-based)
            node_type: Type of the node in the AST (if available)
        """
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.node_type = node_type


class CodeReviewComment(BaseModel):
    """A structured review comment from code review."""
    
    suggestion_id: str = Field(description="Unique ID of the review suggestion")
    body: str = Field(description="Full text of the review comment")
    file_path: str = Field(description="Path to the file where the issue was found")
    line_number: int = Field(description="Line number where the issue was found")
    
    
class ImplementedSuggestion(BaseModel):
    """A successfully implemented suggestion."""

    suggestion_id: str = Field(description="ID of the suggestion that was implemented")
    file_path: str = Field(description="Path to the file where the change was made")
    line_number: int = Field(description="Line number where the change was applied")


class SkippedSuggestion(BaseModel):
    """A suggestion that was skipped."""

    suggestion_id: str = Field(description="ID of the suggestion that was skipped")
    reason: str = Field(description="Reason why the suggestion could not be implemented")


class RefinementResponse(BaseModel):
    """Response from the LLM for code refinement."""

    function_name: str = Field(description="Name of the function or class that was modified")
    file_path: str = Field(description="Path to the file being modified")
    unit_start_line: int = Field(description="Line number where unit begins (1-based)")
    unit_end_line: int = Field(description="Line number where unit ends (1-based)")
    modified_code: str = Field(description="The modified code with all changes implemented")
    implemented_suggestions: List[ImplementedSuggestion] = Field(
        default_factory=list,
        description="List of suggestions that were successfully implemented"
    )
    skipped_suggestions: List[SkippedSuggestion] = Field(
        default_factory=list,
        description="List of suggestions that could not be implemented"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Brief explanation of changes made"
    )


class FileModification(BaseModel):
    """A modification to be applied to a file."""

    file_path: str = Field(description="Path to the file being modified")
    original_node_text: str = Field(description="Original text of the node being modified")
    modified_text: str = Field(description="Modified text to replace the original")
    start_line: int = Field(description="Start line number of the node (1-based)")
    end_line: int = Field(description="End line number of the node (1-based)")
    start_byte: int = Field(description="Start byte position of the node")
    end_byte: int = Field(description="End byte position of the node")
    suggestion_ids: List[str] = Field(
        default_factory=list,
        description="IDs of the suggestions addressed by this modification"
    )
    is_valid: bool = Field(default=True, description="Whether the modification is valid")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if the modification is invalid"
    )


class PatchResult(BaseModel):
    """Result of a patching operation."""

    success: bool = Field(description="Whether the patch was successfully applied")
    modified_content: Optional[str] = Field(
        default=None,
        description="The content after applying the patch"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if the patch failed"
    ) 