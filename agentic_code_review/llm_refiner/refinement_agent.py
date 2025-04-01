"""Refinement Agent for implementing code changes based on review comments.

This module provides the main RefinementAgent class that orchestrates the process
of extracting context, generating changes with an LLM, and applying those changes.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Set

from tree_sitter import Node

from agentic_code_review.github_app.managers.pr_manager import PRManager, PRContext
from agentic_code_review.github_app.models import PRComment

from .comment_processor import CommentProcessor
from .context_extractor import ContextExtractor
from .incremental_patcher import IncrementalPatcher
from .llm_client import LLMClient
from .models import RefinementResponse, FileModification, ImplementedSuggestion, SkippedSuggestion, CodeReviewComment
from .prompts.refinement_prompt import code_refinement_prompt

logger = logging.getLogger(__name__)


class RefinementAgent:
    """Agent responsible for implementing code changes based on review comments."""

    def __init__(self, pr_manager: PRManager, llm_client: LLMClient):
        """Initialize the Refinement Agent.

        Args:
            pr_manager: Manager for GitHub PR operations
            llm_client: Client for LLM interactions
        """
        self.pr_manager = pr_manager
        self.llm_client = llm_client
        self.comment_processor = CommentProcessor()
        self.context_extractor = ContextExtractor()
        
    async def process_pr(self, context: PRContext) -> bool:
        """Process a pull request and implement suggested changes.
        
        Args:
            context: The PR context
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Get unresolved comments
            comments = self.pr_manager.get_unresolved_comments(context)
            if not comments:
                logger.info("No unresolved comments to process")
                return True
            
            # Log the comments being processed
            logger.info(f"Processing {len(comments)} unresolved comments")
            for comment in comments:
                logger.info(f"Comment ID {comment.id} at {comment.path}:{comment.line_number}:\n{comment.body}")
                
            # Group comments by file
            file_comments = self.comment_processor.group_comments_by_file(comments)
            
            # Log the file grouping
            logger.info(f"Comments grouped by file: {', '.join(f'{file}: {len(comments)}' for file, comments in file_comments.items())}")
            
            # Process each file
            processed_files: List[str] = []  # List of successfully processed file paths
            failed_files: List[Tuple[str, str]] = []  # List of (file_path, failure_reason) tuples
            
            # Track all changes and suggestions
            all_changes: Dict[str, str] = {}  # Dictionary mapping file paths to their modified content
            all_implemented_suggestions: List[Tuple[str, str]] = []  # List of (suggestion_id, file_path) tuples
            all_skipped_suggestions: List[Tuple[str, str, str]] = []  # List of (suggestion_id, file_path, reason) tuples
            
            for file_path, file_comments in file_comments.items():
                logger.info(f"Processing file: {file_path}")
                result, changes, implemented, skipped = await self._process_file(context, file_path, file_comments)
                
                if result:
                    processed_files.append(file_path)
                    # Accumulate changes instead of committing immediately
                    if changes:
                        all_changes[file_path] = changes[file_path]
                    if implemented:
                        all_implemented_suggestions.extend(implemented)
                        logger.info(f"Implemented suggestions for {file_path}: {[id for id, _ in implemented]}")
                    if skipped:
                        all_skipped_suggestions.extend(skipped)
                        logger.info(f"Skipped suggestions for {file_path}: {[id for id, _, _ in skipped]}")
                else:
                    failed_files.append((file_path, "Failed to process file"))
                    logger.error(f"Failed to process file: {file_path}")
            
            # Flag to track commit success
            commit_success = False
            
            # Make a single commit with all accumulated changes
            if all_changes:
                commit_message = "Implement code improvements based on review suggestions"
                
                # Log the changes being committed
                for file_path, content in all_changes.items():
                    logger.info(f"FULL CHANGES TO COMMIT for {file_path}:\n{content}")
                
                commit_result = self.pr_manager.commit_changes(
                    context,
                    all_changes,
                    commit_message
                )
                
                if commit_result:
                    commit_success = True
                    logger.info(f"Successfully committed changes to {len(all_changes)} files")
                    
                    # Only resolve comments if the commit was successful
                    if all_implemented_suggestions:
                        logger.info(f"Resolving {len(all_implemented_suggestions)} implemented suggestions")
                        self.pr_manager.resolve_comments(context, all_implemented_suggestions)
                else:
                    logger.error(f"Failed to commit changes to {len(all_changes)} files")
                    # Mark files as failed if the commit fails
                    for file_path in all_changes.keys():
                        if file_path in processed_files:
                            processed_files.remove(file_path)
                            failed_files.append((file_path, "Failed to commit changes"))
            else:
                logger.info("No changes to commit")
                
            # Report results, including skipped suggestions
            await self._report_processing_results(context, processed_files, failed_files, all_skipped_suggestions)
            
            # If we had files to process but none were successful, return False
            if len(file_comments) > 0 and len(processed_files) == 0:
                return False
                
            # Otherwise, return True if we either had no changes or committed successfully
            return len(all_changes) == 0 or commit_success
            
        except Exception as e:
            logger.error(f"Failed to process PR: {e}")
            # The decorator will handle error reporting and label cleanup
            return False
            
    async def _process_file(self, context: PRContext, file_path: str, comments: List[PRComment]) -> Tuple[bool, Optional[Dict[str, str]], Optional[List[Tuple[str, str]]], Optional[List[Tuple[str, str, str]]]]:
        """Process a file and apply code refinements.
        
        Args:
            context: The PR context
            file_path: Path to the file
            comments: List of comments for the file
            
        Returns:
            Tuple of (success, changes_dict, implemented_suggestions, skipped_suggestions)
            - success: True if processing was successful
            - changes_dict: Dictionary of file paths to modified content, or None if no changes
            - implemented_suggestions: List of (suggestion_id, file_path) tuples for resolved comments
            - skipped_suggestions: List of (suggestion_id, file_path, reason) tuples for skipped suggestions
        """
        try:
            # Get the file content
            pr = self.pr_manager._get_pr(context)
            file_content = self.pr_manager.get_file_content(pr.head.repo, file_path, pr.head.ref)
            if not file_content:
                logger.error(f"Failed to get content for {file_path}")
                return False, None, None, None
                
            # Initialize the incremental patcher for this file
            patcher = IncrementalPatcher(file_content, file_path)
            
            # Group comments by code unit instead of proximity
            comments_by_code_unit = self.comment_processor.group_comments_by_code_unit(comments, file_content, file_path)
            logger.info(f"Found {len(comments_by_code_unit)} code units with comments in {file_path}")
            
            # Log the code unit grouping
            for i, unit_comments in enumerate(comments_by_code_unit):
                if unit_comments:
                    comment_ids = [str(c.id) for c in unit_comments]
                    lines = [str(c.line_number) for c in unit_comments]
                    logger.info(f"Code unit {i+1}: Comment IDs {', '.join(comment_ids)} at lines {', '.join(lines)}")
            
            # Track skipped suggestions
            skipped_suggestions: List[Tuple[str, str, str]] = []
            
            # Process each code unit's comments together
            for unit_comments in comments_by_code_unit:
                if not unit_comments:
                    continue
                    
                # Get the primary comment (for line number reference)
                primary_comment = unit_comments[0]
                line = primary_comment.line_number
                
                # Extract code context for the comment
                context_result = self.context_extractor.extract_context(file_path, file_content, line)
                if not context_result:
                    logger.warning(f"Could not extract context for comment at line {line} in {file_path}")
                    continue
                    
                # Extract the code and context
                code_text, code_context = context_result
                
                # Log the extracted code context
                logger.info(f"Extracted code context for line {line}:\n{code_text}")
                
                # Extract file-level context
                file_level_context = self.context_extractor.extract_file_level_context(file_path, file_content)
                
                # Generate changes
                response = await self._generate_changes(file_path, code_text, unit_comments, file_level_context)
                if not response:
                    logger.warning(f"Failed to generate changes for comments at line {line} in {file_path}")
                    continue
                
                # Collect skipped suggestions
                for skipped in response.skipped_suggestions:
                    skipped_suggestions.append((skipped.suggestion_id, file_path, skipped.reason))
                    
                # Find the node that should be modified
                node = patcher.get_containing_code_unit(line)
                if not node:
                    logger.warning(f"Could not find node for comment at line {line} in {file_path}")
                    continue
                    
                # Register the modification with the patcher
                # Ensure all suggestion IDs are strings
                suggestion_ids = [str(comment.id) for comment in unit_comments]
                patcher.register_modification(node, response.modified_code, suggestion_ids)
                
            # Apply all modifications
            result = patcher.apply_all_modifications()
            if not result.success:
                logger.error(f"Failed to apply modifications to {file_path}: {result.error_message}")
                return False, None, None, None
                
            # Validate the result
            if not patcher.validate_result():
                logger.error(f"Validation failed for {file_path}")
                return False, None, None, None
                
            # Instead of committing here, return the changes to be committed later
            implemented_suggestions = patcher.get_implemented_suggestions()
            # Ensure all suggestion IDs are strings
            suggestion_tuples = [(str(id), file_path) for id in implemented_suggestions]
            
            # Return success, changes dict, implemented suggestions, and skipped suggestions
            return True, {file_path: result.modified_content}, suggestion_tuples, skipped_suggestions
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return False, None, None, None
    
    async def _generate_changes(
        self,
        file_path: str,
        code_snippet: str,
        comments: List[PRComment],
        additional_context: Dict[str, Any]
    ) -> Optional[RefinementResponse]:
        """Generate code changes based on comments and context.

        Args:
            file_path: Path to the file being modified
            code_snippet: The code snippet to modify
            comments: List of comments to address
            additional_context: Additional context about the file

        Returns:
            RefinementResponse if successful, None otherwise
        """
        try:
            # Convert PR comments to structured CodeReviewComment objects
            structured_comments = []
            
            for comment in comments:
                # Create structured comment with minimal processing
                structured_comment = CodeReviewComment(
                    suggestion_id=str(comment.id),
                    body=comment.body,
                    file_path=file_path,
                    line_number=comment.line_number
                )
                structured_comments.append(structured_comment)
            
            # Convert structured comments to JSON for the prompt
            comments_json = json.dumps([comment.model_dump() for comment in structured_comments], indent=2)
            
            # Create format instructions for RefinementResponse
            format_instructions = """
            {
              "function_name": "Name of the function or class that was modified",
              "file_path": "Path to the file being modified",
              "unit_start_line": line_number_where_unit_begins,
              "unit_end_line": line_number_where_unit_ends,
              "modified_code": "The modified code region with all accepted changes implemented",
              "implemented_suggestions": [
                {
                  "suggestion_id": "ID from the input",
                  "file_path": "Path to the file being modified",
                  "line_number": line_number_where_change_was_applied
                }
              ],
              "skipped_suggestions": [
                {
                  "suggestion_id": "ID from the input",
                  "reason": "Brief reason"
                }
              ],
              "explanation": "Brief explanation of changes made"
            }
            """
            
            # Format the prompt using the template
            formatted_prompt = code_refinement_prompt.format(
                original_code=code_snippet,
                comments=comments_json,
                format_instructions=format_instructions
            )
            
            # Call the LLM to generate changes
            response = await self.llm_client.generate_code(
                prompt=formatted_prompt,
                response_model=RefinementResponse
            )
            
            # Check that we have a valid response
            if not response or not response.modified_code:
                logger.error("LLM response missing required fields")
                return None
                
            # Add suggestion IDs to the response
            for comment in comments:
                # Ensure comment.id is a string
                comment_id = str(comment.id)
                
                # Check if it's already in implemented or skipped suggestions
                if not any(s.suggestion_id == comment_id for s in response.implemented_suggestions) and \
                   not any(s.suggestion_id == comment_id for s in response.skipped_suggestions):
                    # Add as implemented by default
                    response.implemented_suggestions.append(
                        ImplementedSuggestion(
                            suggestion_id=comment_id,
                            file_path=file_path,
                            line_number=comment.line_number
                        )
                    )
                    
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate changes: {e}")
            return None
    
    async def _report_processing_results(
        self, 
        context: PRContext, 
        processed_files: List[str],
        failed_items: List[Tuple[str, str]],
        skipped_suggestions: List[Tuple[str, str, str]] = None
    ) -> None:
        """Report processing results back to the PR.
        
        Args:
            context: The PR context
            processed_files: List of successfully processed files
            failed_items: List of (file_path, reason) tuples for failures
            skipped_suggestions: List of (suggestion_id, file_path, reason) tuples for skipped suggestions
        """
        # Build the status report
        report = ["## 🤖 Refinement Agent Processing Report\n"]
        
        # Successful files
        if processed_files:
            report.append("### ✅ Successfully Processed\n")
            for file_path in processed_files:
                report.append(f"- `{file_path}`")
            report.append("")
        
        # Failed items
        if failed_items:
            report.append("### ⚠️ Processing Failures\n")
            for item, reason in failed_items:
                report.append(f"- `{item}`: {reason}")
            report.append("")
        
        # Skipped suggestions
        if skipped_suggestions and len(skipped_suggestions) > 0:
            report.append("### ⏩ Skipped Suggestions\n")
            # Group skipped suggestions by file path for better readability
            skipped_by_file: Dict[str, List[Tuple[str, str]]] = {}
            for suggestion_id, file_path, reason in skipped_suggestions:
                if file_path not in skipped_by_file:
                    skipped_by_file[file_path] = []
                skipped_by_file[file_path].append((suggestion_id, reason))
            
            # List skipped suggestions by file
            for file_path, suggestions in skipped_by_file.items():
                report.append(f"**In `{file_path}`:**")
                for suggestion_id, reason in suggestions:
                    report.append(f"- Comment ID {suggestion_id}: {reason}")
                report.append("")
        
        # Add a summary with stats
        total_files = len(processed_files) + len(failed_items)
        total_suggestions = len(skipped_suggestions) if skipped_suggestions else 0
        success_rate = len(processed_files) / total_files * 100 if total_files > 0 else 0
        
        report.append("### 📊 Summary\n")
        report.append(f"- Processed {len(processed_files)} out of {total_files} files ({success_rate:.1f}% success rate)")
        if skipped_suggestions:
            report.append(f"- Skipped {len(skipped_suggestions)} suggestions")
        
        # Post the report as a comment
        try:
            self.pr_manager.post_comment(context, "\n".join(report))
        except Exception as e:
            logger.error(f"Failed to post processing report: {e}")
                