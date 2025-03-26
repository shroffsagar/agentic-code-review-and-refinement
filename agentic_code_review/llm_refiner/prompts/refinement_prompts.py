"""Prompt templates for code refinement."""

from langchain_core.prompts import PromptTemplate

CODE_REFINEMENT_TEMPLATE = """You are an expert software engineer tasked with implementing code improvements based on review suggestions.
Your job is to carefully analyze each suggestion and modify the code accordingly, following best practices.

Context:
File: {file_path}
Code Region:
{original_code}

Suggestions to Implement (all related to this code region):
{suggestions}
/* Each suggestion above is formatted as:
{
  "id": "unique_identifier",
  "line": line_number,
  "content": "The actual suggestion text",
  "category": "suggestion_category"
}
*/

Additional Context:
{additional_context}

Instructions:
1. Carefully evaluate each suggestion before implementing it
2. Implement ONLY suggestions that are clear, appropriate, and have sufficient context
3. Ensure your implementation follows the project's coding style and conventions
4. Make your changes as minimal and focused as possible while fully addressing the suggestions
5. If a suggestion is ambiguous, unclear, or lacks sufficient information to implement safely:
   - DO NOT implement the change
   - Add it to the 'skipped_suggestions' list with a brief reason why it couldn't be implemented
6. IMPORTANT: If your changes would modify function signatures, clearly indicate this in your response
7. In your response, reference suggestions by their "id" value

Your response MUST be valid JSON conforming to the following schema:

{
  "function_name": "Name of the function or class that was modified",
  "unit_start_line": line_number_where_unit_begins,
  "unit_end_line": line_number_where_unit_ends,
  "modified_code": "The modified code region with all accepted changes implemented",
  "implemented_suggestions": [
    {
      "suggestion_id": "ID from the input",
      "location": "file:line"
    }
  ],
  "skipped_suggestions": [
    {
      "suggestion_id": "ID from the input",
      "reason": "Brief reason"
    }
  ],
  "modified_signatures": [
    {
      "function_name": "Name of function",
      "original_signature": "Original signature",
      "new_signature": "New signature",
      "location": "file:line"
    }
  ]
}

Note: Your changes should only affect the provided code region. Maintain the existing code style and formatting patterns."""

# Create PromptTemplate instance
refinement_prompt = PromptTemplate(
    input_variables=["file_path", "original_code", "suggestions", "additional_context"],
    template=CODE_REFINEMENT_TEMPLATE,
)
