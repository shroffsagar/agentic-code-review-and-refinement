"""Models for refinement agent responses."""

from typing import List

from pydantic import BaseModel, Field


class ImplementedSuggestion(BaseModel):
    """A suggestion that was successfully implemented."""

    suggestion_id: str = Field(description="Unique identifier of the suggestion")
    location: str = Field(description="File and line number where the change was made")


class SkippedSuggestion(BaseModel):
    """A suggestion that was skipped during implementation."""

    suggestion_id: str = Field(description="Unique identifier of the suggestion")
    reason: str = Field(description="Reason why the suggestion was skipped")


class ModifiedSignature(BaseModel):
    """A function signature that was modified."""

    function_name: str = Field(description="Name of the function that was modified")
    original_signature: str = Field(description="Original function signature")
    new_signature: str = Field(description="New function signature")
    location: str = Field(description="File and line number where the signature was modified")


class RefinementResponse(BaseModel):
    """Structured response from the refinement agent."""

    function_name: str = Field(description="Name of the function or class that was modified")
    unit_start_line: int = Field(description="Line number where the unit begins")
    unit_end_line: int = Field(description="Line number where the unit ends")
    modified_code: str = Field(description="The modified code region with all accepted changes implemented")
    implemented_suggestions: List[ImplementedSuggestion] = Field(
        description="List of suggestions that were successfully implemented"
    )
    skipped_suggestions: List[SkippedSuggestion] = Field(
        description="List of suggestions that were skipped during implementation"
    )
    modified_signatures: List[ModifiedSignature] = Field(
        description="List of function signatures that were modified"
    )
