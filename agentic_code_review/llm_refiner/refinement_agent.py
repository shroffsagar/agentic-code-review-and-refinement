"""Refinement Agent for implementing code changes based on review comments."""

import json
from typing import Optional

from agentic_code_review.code_analysis.code_analyzer import CodeAnalyzer
from agentic_code_review.code_analysis.language_config import LanguageConfig
from agentic_code_review.github_app.models import PRComment
from agentic_code_review.github_app.pr_manager import PRManager
from agentic_code_review.llm_refiner.comment_processor import CommentProcessor
from agentic_code_review.llm_refiner.llm_client import LLMClient
from agentic_code_review.llm_refiner.models import (
    ImplementedSuggestion,
    ModifiedSignature,
    RefinementResponse,
    SkippedSuggestion,
)
from agentic_code_review.llm_refiner.prompts.refinement_prompts import CODE_REFINEMENT_TEMPLATE


class RefinementAgent:
    """Agent responsible for implementing code changes based on review comments."""

    def __init__(
        self,
        pr_manager: PRManager,
        llm_client: LLMClient,
        code_analyzer: CodeAnalyzer,
        language_config: LanguageConfig,
    ):
        """Initialize the Refinement Agent.

        Args:
            pr_manager: Manager for GitHub PR operations
            llm_client: Client for LLM interactions
            code_analyzer: Analyzer for code analysis
            language_config: Configuration for language-specific settings
        """
        self.pr_manager = pr_manager
        self.llm_client = llm_client
        self.code_analyzer = code_analyzer
        self.language_config = language_config
        self.comment_processor = CommentProcessor()

    async def process_pr(self, pr_number: int) -> None:
        """Process a pull request and implement approved suggestions.

        Args:
            pr_number: The number of the pull request to process
        """
        # Get unresolved comments
        comments = await self.pr_manager.get_unresolved_comments(pr_number)

        # Process and group comments
        grouped_comments = self.comment_processor.process_comments(comments)

        # Process each file's comments
        for file_path, file_comments in grouped_comments.items():
            await self._process_file_comments(pr_number, file_path, file_comments)

    async def _process_file_comments(self, pr_number: int, file_path: str, comments: list[PRComment]) -> None:
        """Process comments for a specific file.

        Args:
            pr_number: The PR number
            file_path: Path to the file being processed
            comments: List of comments for the file
        """
        try:
            # Get current file content
            file_content = await self.pr_manager.get_file_content(pr_number, file_path)
            if not file_content:
                logger.error(f"Failed to get content for {file_path}")
                return

            # Parse code
            self.code_analyzer.parse_code(file_content)

            # Group comments by code unit
            unit_comments = self.comment_processor.group_comments_by_context(comments, self.code_analyzer)

            # Process each unit's comments
            for unit, unit_comments in unit_comments.items():
                try:
                    # Verify node is still valid
                    if not unit.is_valid():
                        logger.warning(f"Node {unit.node_id} is no longer valid, skipping comments")
                        continue

                    # Get code context
                    context = self._get_code_context(unit)

                    # Generate changes
                    response = await self._generate_changes(file_path, context["code_snippet"], unit_comments, context)

                    if response:
                        # Validate changes before applying
                        if not self.code_analyzer.validate_changes(response.modified_code):
                            logger.error(f"Invalid changes generated for {file_path}")
                            continue

                        # Apply changes
                        await self._apply_changes(pr_number, file_path, response)

                        # Handle signature changes
                        if response.modified_signatures:
                            await self._handle_signature_changes(pr_number, file_path, response.modified_signatures)

                        # Resolve implemented suggestions
                        for suggestion in response.implemented_suggestions:
                            await self.pr_manager.resolve_comment(suggestion.suggestion_id)

                except Exception as e:
                    logger.error(f"Failed to process unit in {file_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to process comments for {file_path}: {e}")

    def _get_code_context(self, node: "CodeNode") -> dict:
        """Get code context for a node.

        Args:
            node: The code node to get context for

        Returns:
            Dictionary containing code context
        """
        # Get the code snippet
        code_snippet = self.code_analyzer.get_node_text(node)

        # Get additional context
        context_nodes = self.code_analyzer.get_node_context(node)
        additional_context = self._format_context(context_nodes)

        return {
            "code_snippet": code_snippet,
            "additional_context": additional_context,
            "node_type": node.node_type,
            "node_name": node.name,
            "node_id": node.node_id,
            "tree_id": node.tree_id,
        }

    def _format_context(self, context_nodes: list["CodeNode"]) -> str:
        """Format context nodes into a readable string.

        Args:
            context_nodes: List of context nodes

        Returns:
            Formatted context string
        """
        context_parts = []
        for node in context_nodes:
            if node.name:
                context_parts.append(f"{node.node_type}: {node.name}")
            else:
                context_parts.append(node.node_type)
        return " > ".join(context_parts)

    async def _generate_changes(
        self,
        file_path: str,
        code_snippet: str,
        comments: list[PRComment],
        context: dict,
    ) -> Optional[RefinementResponse]:
        """Generate code changes based on comments and context.

        Args:
            file_path: Path to the file
            code_snippet: The code to modify
            comments: List of comments for this code region
            context: Additional code context

        Returns:
            Structured response with changes or None if generation fails
        """
        # Format suggestions
        suggestions = [
            {
                "id": comment.id,
                "line": comment.line_number,
                "content": comment.body,
                "category": comment.category,
            }
            for comment in comments
        ]

        # Generate prompt
        prompt = CODE_REFINEMENT_TEMPLATE.format(
            file_path=file_path,
            original_code=code_snippet,
            suggestions=json.dumps(suggestions, indent=2),
            additional_context=context.get("additional_context", ""),
        )

        # Get response from LLM
        response_text = await self.llm_client.generate_code(prompt)
        if not response_text:
            return None

        try:
            # Parse response
            response_data = json.loads(response_text)

            # Convert to structured response
            return RefinementResponse(
                function_name=response_data["function_name"],
                unit_start_line=response_data["unit_start_line"],
                unit_end_line=response_data["unit_end_line"],
                modified_code=response_data["modified_code"],
                implemented_suggestions=[ImplementedSuggestion(**s) for s in response_data["implemented_suggestions"]],
                skipped_suggestions=[SkippedSuggestion(**s) for s in response_data["skipped_suggestions"]],
                modified_signatures=[ModifiedSignature(**s) for s in response_data["modified_signatures"]],
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            return None

    async def _apply_changes(self, pr_number: int, file_path: str, response: RefinementResponse) -> None:
        """Apply code changes to the PR.

        Args:
            pr_number: The PR number
            file_path: Path to the file
            response: Structured response with changes
        """
        try:
            # Validate changes again before committing
            if not self.code_analyzer.validate_changes(response.modified_code):
                logger.error(f"Invalid changes detected for {file_path}")
                return

            await self.pr_manager.commit_changes(pr_number, file_path, response.modified_code)
        except Exception as e:
            logger.error(f"Failed to apply changes to {file_path}: {e}")
            raise

    async def _handle_signature_changes(
        self,
        pr_number: int,
        file_path: str,
        signature_changes: list[ModifiedSignature],
    ) -> None:
        """Handle function signature changes and update dependent code.

        Args:
            pr_number: The PR number
            file_path: Path to the file
            signature_changes: List of signature changes
        """
        try:
            for change in signature_changes:
                # Find function node
                function_node = self._find_function_node(change.function_name)
                if not function_node or not function_node.is_valid():
                    logger.warning(f"Could not find function {change.function_name}")
                    continue

                # Get function context
                context = self._get_code_context(function_node)

                # Generate update prompt
                prompt = f"""Update the following code to match the new function signature:

Original signature: {change.original_signature}
New signature: {change.new_signature}

Code to update:
{context["code_snippet"]}

Generate only the updated code that matches the new signature."""

                # Get updated code
                updated_code = await self.llm_client.generate_code(prompt)
                if updated_code:
                    # Validate changes
                    if not self.code_analyzer.validate_changes(updated_code):
                        logger.error(f"Invalid signature change for {change.function_name}")
                        continue

                    # Apply changes
                    await self.pr_manager.commit_changes(pr_number, file_path, updated_code)

        except Exception as e:
            logger.error(f"Failed to handle signature changes for {file_path}: {e}")
            raise

    def _find_function_node(self, function_name: str) -> Optional["CodeNode"]:
        """Find a function node by name.

        Args:
            function_name: Name of the function to find

        Returns:
            The function node if found, None otherwise
        """
        # This is a simplified implementation. In practice, you might want to
        # maintain a mapping of function names to nodes or implement a more
        # sophisticated search.
        for node in self.code_analyzer.node_mapping.values():
            if node.name == function_name and node.node_type in ["function_definition", "method_definition"]:
                return node
        return None
