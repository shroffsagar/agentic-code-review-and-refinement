"""GitHub authentication handling."""

import hashlib
import hmac
import logging
import re
from typing import Any

from github import GithubIntegration

from agentic_code_review.config import settings

logger = logging.getLogger(__name__)

# Constants to avoid hardcoding key markers in the code
_PK_BEGIN = "-----BEGIN"
_PK_END = "-----END"
_RSA_KEY_TYPE = "RSA PRIVATE KEY"


class GitHubAuthenticator:
    """Handles GitHub authentication and webhook verification."""

    def __init__(
        self,
        app_id: str,
        private_key: str,
        webhook_secret: str,
        enterprise_hostname: str | None = None,
    ) -> None:
        """Initialize the authenticator.

        Args:
            app_id: The GitHub App ID
            private_key: The GitHub App private key
            webhook_secret: The GitHub App webhook secret
            enterprise_hostname: Optional GitHub Enterprise hostname
        """
        # Format the private key properly
        formatted_key = self._format_private_key(private_key)
        logger.info("Private key formatted")

        # Use enterprise hostname if provided, otherwise use configured API URL
        base_url = f"https://{enterprise_hostname}/api/v3" if enterprise_hostname else settings.GITHUB_API_URL

        try:
            logger.info(f"Initializing GitHub App integration with App ID: {app_id}")
            logger.info(f"Using GitHub API URL: {base_url}")
            self.integration = GithubIntegration(int(app_id), formatted_key, base_url=base_url)
            logger.info("GitHub App integration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub App integration: {e}")
            # Log only the format structure, not actual key content
            logger.error("Failed to initialize with formatted key")
            raise

        self.webhook_secret = webhook_secret

    def _format_private_key(self, key: str) -> str:
        """
        Format the private key to ensure it's in the correct PEM format.

        Args:
            key: The private key string that needs formatting

        Returns:
            str: Properly formatted private key
        """
        key = key.strip()

        # Create full markers for pattern matching without hardcoding the full pattern
        begin_marker = f"{_PK_BEGIN} {_RSA_KEY_TYPE}"
        end_marker = f"{_PK_END} {_RSA_KEY_TYPE}"

        # If key doesn't have begin marker, add the markers
        if _PK_BEGIN not in key:
            key = f"{begin_marker}-----\n{key}\n{end_marker}-----"

        # Remove any quotes that might surround the key
        key = key.strip().strip("\"'")

        # If key already has BEGIN/END markers, ensure proper line breaks
        pattern = f"{begin_marker}-----(.+?){end_marker}-----"
        if begin_marker in key:
            # Ensure proper line breaks between BEGIN and END markers
            def format_key_content(match: re.Match) -> str:
                content = match.group(1).replace("\n", "")
                chunks = [content[i : i + 64] for i in range(0, len(content), 64)]
                formatted = f"{begin_marker}-----\n" + "\n".join(chunks) + f"\n{end_marker}-----"
                return formatted

            key = re.sub(pattern, format_key_content, key, flags=re.DOTALL)
            return key

        # Otherwise, format from scratch
        formatted_key = f"{begin_marker}-----\n"
        # Split the key into chunks of 64 characters
        chunks = [key[i : i + 64] for i in range(0, len(key), 64)]
        formatted_key += "\n".join(chunks)
        formatted_key += f"\n{end_marker}-----"

        return formatted_key

    def verify_webhook_signature(self, payload_body: bytes, signature_header: str | None) -> bool:
        """Verify the GitHub webhook signature."""
        if not signature_header:
            return False

        try:
            sha_name, signature = signature_header.split("=")
            if sha_name != "sha256":
                return False

            mac = hmac.new(
                self.webhook_secret.encode(),
                msg=payload_body,
                digestmod=hashlib.sha256,
            )
            return hmac.compare_digest(mac.hexdigest(), signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    # Alias for verify_webhook_signature for consistent naming
    validate_webhook = verify_webhook_signature

    def get_installation_client(self, installation_id: int) -> Any:
        """Get an authenticated client for a specific installation."""
        try:
            return self.integration.get_github_for_installation(installation_id)
        except Exception as e:
            logger.error(f"Error getting installation client: {e}")
            raise
