"""Code formatting utilities.

This module provides functions for automatically formatting code after patching.
It leverages standard formatting tools like autopep8 for Python.

To add support for a new language:
1. Create a new formatter function following the pattern of _format_python
2. Add it to the FORMATTERS dictionary in _initialize_formatters
"""

import logging
import os
import subprocess
import tempfile
from collections.abc import Callable
from typing import Optional

logger = logging.getLogger(__name__)

# Type for formatter functions
FormatterFunc = Callable[[str], Optional[str]]

# Map of language IDs to their formatter functions
FORMATTERS: dict[str, FormatterFunc] = {}

def format_code(code_content: str, language_id: str) -> Optional[str]:
    """Format code content using the appropriate formatter for the language.

    Args:
        code_content: The content of the code to format
        language_id: The language identifier (e.g., 'python', 'javascript')

    Returns:
        The formatted code content if successful, None otherwise
    """
    # Initialize formatters if not already done
    if not FORMATTERS:
        _initialize_formatters()

    # Log the original code content
    #logger.info(f"Original code to format ({language_id}):\n{code_content}")

    # Get the formatter for the language
    formatter = FORMATTERS.get(language_id)
    if formatter:
        formatted_content = formatter(code_content)
        if formatted_content:
            # Log original and formatted code for comparison
            logger.debug(f"Formatting comparison for {language_id}:")
            logger.debug(f"ORIGINAL:\n{code_content}")
            logger.debug(f"FORMATTED:\n{formatted_content}")
        return formatted_content
    else:
        logger.info(f"No formatter available for '{language_id}' language")
        return None

def _initialize_formatters():
    """Initialize the map of language formatters.

    Add new language formatters here as they are implemented.
    The key should match the language_id from the tree-sitter parser.
    """
    # Currently supported languages
    FORMATTERS["python"] = _format_python

    # Examples for future language support:
    # FORMATTERS["javascript"] = _format_javascript
    # FORMATTERS["typescript"] = _format_typescript
    # FORMATTERS["java"] = _format_java

def _format_python(code_content: str) -> Optional[str]:
    """Format Python code using autopep8.

    Args:
        code_content: The Python code content to format

    Returns:
        The formatted code content if successful, None otherwise
    """
    # Create a temporary file with the code content
    temp_path = None
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(code_content)

        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as output_file:
            output_path = output_file.name

        # Use autopep8 with aggressive flag
        formatter_cmd = ["poetry", "run", "autopep8", "--aggressive"]

        try:
            cmd = [*formatter_cmd, temp_path]

            logger.debug("Attempting to format with autopep8")

            # Redirect output to output file
            with open(output_path, "w") as output_file:
                result = subprocess.run(
                    cmd,
                    stdout=output_file,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )

            if result.returncode == 0:
                logger.debug("Successfully formatted with autopep8")
                with open(output_path) as f:
                    formatted_content = f.read()

                return formatted_content
            else:
                logger.debug(f"autopep8 formatting failed: {result.stderr}")
                return None
        except Exception as e:
            logger.debug(f"Error using autopep8: {e}")
            return None

    except Exception as e:
        logger.error(f"Error during Python code formatting: {e}")
        return None
    finally:
        # Clean up the temporary files
        for path in [temp_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to remove temporary file: {cleanup_error}")

# Template for adding new language formatters:
"""
def _format_javascript(code_content: str) -> Optional[str]:
    '''Format JavaScript code using prettier.

    Args:
        code_content: The JavaScript code content to format

    Returns:
        The formatted code content if successful, None otherwise
    '''
    # Implementation similar to _format_python but using the appropriate tool
    pass
"""
