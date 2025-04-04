"""LLM-powered code refinement system.

This package contains the components for the language-agnostic refinement agent,
which processes review comments and applies suggested improvements to code.
"""

from .context_extractor import ContextExtractor
from .incremental_patcher import IncrementalPatcher
from .llm_client import LLMClient
from .comment_processor import CommentProcessor
from .models import (
    CodeContext,
    FileModification,
    ImplementedSuggestion,
    PatchResult,
    RefinementResponse,
    SkippedSuggestion,
)
from .refinement_agent import RefinementAgent

__all__ = [
    "ContextExtractor",
    "IncrementalPatcher",
    "LLMClient",
    "CommentProcessor",
    "CodeContext",
    "FileModification",
    "ImplementedSuggestion",
    "PatchResult",
    "RefinementResponse",
    "SkippedSuggestion",
    "RefinementAgent",
] 