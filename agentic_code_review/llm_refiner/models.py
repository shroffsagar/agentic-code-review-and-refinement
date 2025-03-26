"""Models for refinement agent responses."""

from dataclasses import dataclass


@dataclass
class ImplementedSuggestion:
    """A suggestion that was successfully implemented."""

    suggestion_id: str
    location: str


@dataclass
class SkippedSuggestion:
    """A suggestion that was skipped during implementation."""

    suggestion_id: str
    reason: str


@dataclass
class ModifiedSignature:
    """A function signature that was modified."""

    function_name: str
    original_signature: str
    new_signature: str
    location: str


@dataclass
class RefinementResponse:
    """Structured response from the refinement agent."""

    function_name: str
    unit_start_line: int
    unit_end_line: int
    modified_code: str
    implemented_suggestions: list[ImplementedSuggestion]
    skipped_suggestions: list[SkippedSuggestion]
    modified_signatures: list[ModifiedSignature]
