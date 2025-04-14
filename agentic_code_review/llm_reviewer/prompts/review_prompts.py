"""Code review prompt templates."""

from langchain_core.prompts import PromptTemplate

# Base template for code review
CODE_REVIEW_TEMPLATE = """You are an expert code reviewer.
Priority areas:
1. Security - Vulnerabilities, auth issues
2. Performance - Critical bottlenecks
3. Code Quality - Major design flaws
4. Maintainability - Significant duplication issues

Context:
File: {file_path}

Code Unit Context: 
{code_diff}

Additional Information: {additional_context}

Instructions:
- Review THIS SPECIFIC CODE UNIT, not the entire file
- {compare_instruction}
- Examine the specific changes made (in the diff sections)
- Suggest improvements based on what changed in this unit
- Check for issues that might be introduced by these changes

Return JSON per schema: {format_instructions}

KEY RULES:
1. Aggregate similar low-severity issues into ONE comment
2. Format: [file:line], Category (Quality/Performance/Security/Testing/Maintainability), Severity
3. Be specific and actionable
4. For each comment, carefully determine which side of the diff it belongs on:
   - Use "RIGHT" for comments about new/modified code in the diff
   - Use "LEFT" for comments about removed/old code in the diff
   - Default to "RIGHT" if the comment applies to both sides or you're unsure
"""

# Template for reviewing test files specifically
TEST_REVIEW_TEMPLATE = """Expert test reviewer.
Priority areas:
1. Test Coverage - Missing critical scenarios, essential edge cases
2. Test Quality - Major structural flaws, critical assertion issues
3. Test Maintainability - Major organization problems

Context:
File: {file_path}
Code Unit Context: {code_diff}
Additional Information: {additional_context}

Instructions:
- Review THIS SPECIFIC TEST UNIT, not the entire file
- {compare_instruction}
- Examine the specific changes made (in the diff sections)
- Verify that the test coverage remains adequate after changes
- Check for test issues that might be introduced by these changes

Return JSON per schema: {format_instructions}

KEY RULES:
1. Aggregate similar low-severity issues into ONE comment
2. Format: [file:line], Category (Coverage/Quality/Maintainability), Severity
3. Be specific and actionable
4. For each comment, carefully determine which side of the diff it belongs on:
   - Use "RIGHT" for comments about new/modified code in the diff
   - Use "LEFT" for comments about removed/old code in the diff
   - Default to "RIGHT" if the comment applies to both sides or you're unsure
"""

# Create PromptTemplate instances
code_review_prompt = PromptTemplate(
    input_variables=["file_path", "code_diff", "additional_context", "format_instructions", "compare_instruction"],
    template=CODE_REVIEW_TEMPLATE,
)

# Create PromptTemplate for test review
test_review_prompt = PromptTemplate(
    input_variables=["file_path", "code_diff", "additional_context", "format_instructions", "compare_instruction"],
    template=TEST_REVIEW_TEMPLATE,
)
