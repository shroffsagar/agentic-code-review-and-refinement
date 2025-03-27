"""Code review prompt templates."""

from langchain_core.prompts import PromptTemplate

# Base template for code review
CODE_REVIEW_TEMPLATE = """Expert code reviewer. Focus on high-impact issues only.
Priority areas:
1. Security - Vulnerabilities, auth issues
2. Performance - Critical bottlenecks
3. Code Quality - Major design flaws
4. Testing - Missing critical test coverage
5. Maintainability - Significant duplication issues

Context:
File: {file_path}
Changes: {code_diff}
Context: {additional_context}

Return JSON per schema: {format_instructions}

KEY RULES:
1. ONLY report High and critical Medium severity issues
2. Aggregate similar low-severity issues into ONE comment
3. Format: [file:line], Category (Quality/Performance/Security/Testing/Maintainability), Severity
4. Be specific and actionable

Focus only on substantive issues. Be concise."""

# Create PromptTemplate instances
code_review_prompt = PromptTemplate(
    input_variables=["file_path", "code_diff", "additional_context", "format_instructions"],
    template=CODE_REVIEW_TEMPLATE,
)

# Template for reviewing test files specifically
TEST_REVIEW_TEMPLATE = """Expert test reviewer. Focus on high-impact issues only.
Priority areas:
1. Test Coverage - Missing critical scenarios, essential edge cases
2. Test Quality - Major structural flaws, critical assertion issues
3. Test Maintainability - Major organization problems

Context:
File: {file_path}
Changes: {code_diff}
Context: {additional_context}

Return JSON per schema: {format_instructions}

KEY RULES:
1. ONLY report High and critical Medium severity issues
2. Aggregate similar low-severity issues into ONE comment
3. Format: [file:line], Category (Coverage/Quality/Maintainability), Severity
4. Be specific and actionable

Focus only on substantive issues. Be concise."""

# Create PromptTemplate for test review
test_review_prompt = PromptTemplate(
    input_variables=["file_path", "code_diff", "additional_context", "format_instructions"],
    template=TEST_REVIEW_TEMPLATE,
)
