"""Test agent implementation for validating basic functionality.

This module provides a simple test agent that validates the core functionality
of accessing PRs, calling GPT-4, and posting comments.
"""

import logging

from agentic_code_review.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TestAgent(BaseAgent):
    """Test agent for validating basic functionality."""

    def run(self) -> bool:
        """Run the test agent to validate basic functionality.

        This method:
        1. Retrieves PR content
        2. Makes a test call to GPT-4
        3. Posts a test comment

        Returns:
            bool: True if all operations were successful, False otherwise.
        """
        # Step 1: Get PR content
        pr_content = self.get_pr_content()
        if not pr_content:
            logger.error("Failed to retrieve PR content")
            return False

        # Step 2: Make a test call to GPT-4
        test_prompt = "This is a test message. Please respond with 'Test successful!'"
        gpt_response = self.call_gpt4(test_prompt)
        if not gpt_response:
            logger.error("Failed to get response from GPT-4")
            return False

        # Step 3: Post a test comment
        test_comment = (
            "🤖 Test Agent Comment\n\n"
            "This is a test comment from the Agentic Code Review system.\n"
            "If you're seeing this, the basic functionality is working!\n\n"
            f"GPT-4 Response: {gpt_response}"
        )
        if not self.post_comment(test_comment):
            logger.error("Failed to post test comment")
            return False

        logger.info("Test agent completed successfully")
        return True
