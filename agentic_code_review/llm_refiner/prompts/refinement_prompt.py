"""Prompt templates for code refinement.

This module contains the prompt templates used for generating code refinements
based on PR comments.
"""

from langchain_core.prompts import PromptTemplate

# Template for code refinement based on review comments
CODE_REFINEMENT_TEMPLATE = """
You are an expert software engineer implementing code changes based on specific review comments.
You will be provided with a file path, original code, and review comments. Your task is to incorporate the review comments into the original code.

File: {file_path}

ORIGINAL CODE:
```
{original_code}
```

REVIEW COMMENTS:
```
{comments}
```

KEY RULES:
1. Implement EXACTLY what each review suggestion requires and do not make any changes to the code that are not requested in the suggestion. 
For example, if a suggestion mentions "use lazy loading for this expensive operation", actually implement the lazy loading pattern as requested, not just make syntax changes.
2. Your code implementation should follow the suggestion given - verify this.
3. Pay special attention to algorithm suggestions and performance optimizations


RETURN FORMAT:
Return a structured response in this format:
{format_instructions}
"""

# Create a PromptTemplate instance
code_refinement_prompt = PromptTemplate(
    input_variables=[
        "file_path", 
        "original_code", 
        "comments", 
        "format_instructions"
    ],
    template=CODE_REFINEMENT_TEMPLATE
)

# Template for verifying code changes
CODE_VERIFICATION_TEMPLATE = """You are verifying code changes to ensure they correctly implement review comments.

ORIGINAL CODE:
```
{original_code}
```

MODIFIED CODE:
```
{modified_code}
```

CHANGES WERE MADE TO ADDRESS THESE REVIEW SUGGESTIONS:
{comments}

Verify:
1. The implementation EXACTLY matches what was requested in the suggestions
2. The proposed implementation actually fulfills the architectural or performance requirements mentioned
3. The code does what the explanation claims without discrepancies

Return a JSON document with your assessment:
{format_instructions}
"""

# Create a PromptTemplate instance for verification
code_verification_prompt = PromptTemplate(
    input_variables=[
        "original_code", 
        "modified_code", 
        "comments", 
        "format_instructions"
    ],
    template=CODE_VERIFICATION_TEMPLATE
) 