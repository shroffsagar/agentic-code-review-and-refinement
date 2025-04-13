"""Diff processing and code unit extraction.

This module provides functionality for extracting complete code units from diffs,
allowing for better context when analyzing and applying code changes.
"""

import logging
import re
from typing import Optional, Tuple

from ..github_app.models import PRFile
from .context_extractor import ContextExtractor
from .models import CodeContext, CodeDiffUnit

logger = logging.getLogger(__name__)

# Regex pattern for extracting line numbers from change headers
CHANGE_HEADER_PATTERN = re.compile(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')
# Pattern to find all change headers in a patch
FIND_CHANGES_PATTERN = re.compile(r'(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*)')


class DiffExtractor:
    """Extract complete code units from diffs."""

    def __init__(self):
        """Initialize the diff extractor."""
        self.context_extractor = ContextExtractor()

    def _extract_line_numbers(self, change_header: str) -> tuple[Optional[int], Optional[int]]:
        """Extract old and new line numbers from a change header.

        Args:
            change_header: The change header line (e.g., "@@ -10,7 +10,8 @@")

        Returns:
            Tuple of (old_start_line, new_start_line) or (None, None) if parsing fails
        """
        match = CHANGE_HEADER_PATTERN.match(change_header)
        if not match:
            logger.warning(f"Invalid change header format: {change_header}")
            return None, None

        return int(match.group(1)), int(match.group(2))

    def _extract_change_content(self, patch: str, change_header: str) -> Tuple[str, int, int]:
        """Extract the complete content of a change section from the patch with line numbers.

        Args:
            patch: The complete file patch
            change_header: The change header to find

        Returns:
            Tuple of (change_content, old_start_line, new_start_line)
            where change_content is the complete change content including the header and all changed lines,
            old_start_line is the starting line number in the old file,
            and new_start_line is the starting line number in the new file
        """
        logger.debug(f"Extracting change content from patch: {change_header}")
        
        # Find the position of this change header in the patch
        start_pos = patch.find(change_header)
        if start_pos == -1:
            logger.warning(f"Could not find change header in patch: {change_header}")
            return change_header, 0, 0

        # Find the end of this change section by looking for the next change header or end of patch
        next_change = FIND_CHANGES_PATTERN.search(patch, start_pos + len(change_header))
        if next_change:
            end_pos = next_change.start()
        else:
            end_pos = len(patch)

        # Extract the complete change section
        raw_change_content = patch[start_pos:end_pos].strip()
        
        # Extract line numbers from header
        old_start, new_start = self._extract_line_numbers(change_header)
        if old_start is None or new_start is None:
            logger.warning(f"Could not extract line numbers from header: {change_header}")
            return raw_change_content, 0, 0
        
        # Add line numbers to the diff content
        annotated_diff = self._add_line_numbers(raw_change_content, old_start, new_start)
        return annotated_diff, old_start, new_start
    
    def _add_line_numbers(self, diff_content: str, old_start: int, new_start: int) -> str:
        """Add precise line numbers to each line of the diff.
        
        Args:
            diff_content: Raw diff content
            old_start: Starting line number in the old file
            new_start: Starting line number in the new file
            
        Returns:
            Diff content with line numbers added to each line
        """
        lines = diff_content.split('\n')
        if not lines:
            return diff_content
            
        # The first line is the diff header, keep it as is
        result = [lines[0]]
        
        # Track current line positions
        old_line = old_start
        new_line = new_start
        
        # Process each line after the header
        for line in lines[1:]:
            if not line:
                result.append(line)
                continue
                
            if line.startswith('\\'):
                # Special case for "\ No newline at end of file"
                result.append(line)
                continue
                
            if line.startswith('+'):
                # Added line (only in new file)
                result.append(f"+{new_line}: {line[1:]}")
                new_line += 1
            elif line.startswith('-'):
                # Removed line (only in old file)
                result.append(f"-{old_line}: {line[1:]}")
                old_line += 1
            elif line.startswith(' '):
                # Context line (in both files)
                # We show both line numbers for clarity
                result.append(f" {old_line},{new_line}: {line[1:]}")
                old_line += 1
                new_line += 1
            else:
                # Anything else, keep as is
                result.append(line)
                
        return '\n'.join(result)

    def _extract_code_context(self, file_path: str, line: int, content: Optional[str]) -> tuple[Optional[str], Optional[CodeContext]]:
        """Extract code and context at a given line.

        Args:
            file_path: Path to the file
            line: Line number to extract context from
            content: File content

        Returns:
            Tuple of (code_text, code_context) or (None, None) if extraction fails
        """
        if not content or line <= 0:
            return None, None

        try:
            extraction_result = self.context_extractor.extract_context(
                file_path=file_path,
                file_content=content,
                line=line
            )

            if extraction_result:
                code, context = extraction_result
                logger.debug(f"Extracted context at line {line}: {context.start_line}-{context.end_line}")
                return code, context
            else:
                logger.warning(f"Failed to extract context at line {line}")
                return None, None

        except Exception as e:
            logger.error(f"Error extracting context at line {line}: {e}")
            return None, None

    def _get_unit_key(self, code_diff_unit: CodeDiffUnit) -> Optional[tuple]:
        """Get a unique key for a code diff unit based on its context.

        Args:
            code_diff_unit: The code diff unit

        Returns:
            A tuple that can be used as a unique identifier, or None if not possible
        """
        if code_diff_unit.before_context:
            return ("before",
                   code_diff_unit.before_context.start_line,
                   code_diff_unit.before_context.end_line)
        elif code_diff_unit.after_context:
            return ("after",
                   code_diff_unit.after_context.start_line,
                   code_diff_unit.after_context.end_line)
        return None

    def extract_code_unit_from_change(
        self,
        change_header: str,
        file_path: str,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None
    ) -> Optional[CodeDiffUnit]:
        """Extract a complete code unit from a change section.

        Args:
            change_header: The change header line (e.g., "@@ -10,7 +10,8 @@")
            file_path: Path to the file being modified
            before_content: Complete file content before the change
            after_content: Complete file content after the change

        Returns:
            A CodeDiffUnit or None if extraction failed
        """
        try:
            # Extract line numbers from change header
            old_start, new_start = self._extract_line_numbers(change_header)
            if old_start is None or new_start is None:
                return None

            # Extract code context from before and after versions
            before_code, before_context = self._extract_code_context(
                file_path, old_start, before_content)
            after_code, after_context = self._extract_code_context(
                file_path, new_start, after_content)

            # Require at least one context
            if not before_context and not after_context:
                logger.warning(f"Could not extract any context from {file_path}")
                return None

            # Create and return the CodeDiffUnit
            return CodeDiffUnit(
                file_path=file_path,
                before_code=before_code,
                after_code=after_code,
                before_context=before_context,
                after_context=after_context,
                diff_texts=[change_header]
            )

        except Exception as e:
            logger.error(f"Error extracting code unit from {file_path}: {e}", exc_info=True)
            return None

    def collect_unique_diff_units(
        self,
        patch: str,
        file_path: str,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None
    ) -> list[CodeDiffUnit]:
        """Collect all unique code diff units from a file patch.

        Args:
            patch: The PR file patch
            file_path: Path to the file being modified
            before_content: Complete file content before the change
            after_content: Complete file content after the change

        Returns:
            A list of unique CodeDiffUnit objects
        """
        if not patch:
            logger.warning(f"Empty patch provided for {file_path}")
            return []

        try:
            # Extract all change headers
            change_headers = FIND_CHANGES_PATTERN.findall(patch)
            if not change_headers:
                logger.warning(f"No changes found in patch for {file_path}")
                return []

            logger.debug(f"Found {len(change_headers)} changes in {file_path}")

            # Process each change header and track unique units
            unique_units = {}

            for i, header in enumerate(change_headers):
                # Get the complete change content with line numbers
                change_content, old_start, new_start = self._extract_change_content(patch, header)

                # Extract the code unit for this change
                code_diff_unit = self.extract_code_unit_from_change(
                    change_header=header,
                    file_path=file_path,
                    before_content=before_content,
                    after_content=after_content
                )

                if not code_diff_unit:
                    continue

                # Get a unique key for this code unit
                unit_key = self._get_unit_key(code_diff_unit)
                if not unit_key:
                    continue

                # Store unique units, merging diffs for the same unit
                if unit_key in unique_units:
                    # Add this change to the existing unit
                    unique_units[unit_key].add_diff_text(change_content)
                else:
                    # Store new unit with full change content
                    code_diff_unit.diff_texts = [change_content]
                    unique_units[unit_key] = code_diff_unit

            result = list(unique_units.values())
            logger.info(f"Extracted {len(result)} unique code diff units from {file_path}")
            return result

        except Exception as e:
            logger.error(f"Error collecting unique diff units from {file_path}: {e}", exc_info=True)
            return []

    def collect_unique_units_from_pr_file(
        self,
        pr_file: PRFile,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None
    ) -> list[CodeDiffUnit]:
        """Collect all unique code diff units from a PR file.

        Args:
            pr_file: The PR file to extract from
            before_content: Complete file content before the change
            after_content: Complete file content after the change

        Returns:
            A list of unique CodeDiffUnit objects
        """
        if not pr_file.patch:
            logger.warning(f"No patch available for {pr_file.filename}")
            return []

        return self.collect_unique_diff_units(
            patch=pr_file.patch,
            file_path=pr_file.filename,
            before_content=before_content,
            after_content=after_content
        )
