"""GitHub authentication handling."""

import hashlib
import hmac
from typing import Any

from github import GithubIntegration


class GitHubAuthenticator:
    """Handles GitHub authentication and webhook verification."""

    def __init__(
        self,
        app_id: str,
        private_key: str,
        webhook_secret: str,
        enterprise_hostname: str | None = None,
    ) -> None:
        base_url = (
            f"https://{enterprise_hostname}/api/v3"
            if enterprise_hostname
            else "https://api.github.com"
        )
        self.integration = GithubIntegration(app_id, private_key, base_url=base_url)
        self.webhook_secret = webhook_secret

    def verify_webhook_signature(
        self, payload_body: bytes, signature_header: str | None
    ) -> bool:
        """Verify the GitHub webhook signature."""
        if not signature_header:
            return False

        sha_name, signature = signature_header.split("=")
        if sha_name != "sha256":
            return False

        mac = hmac.new(
            self.webhook_secret.encode(),
            msg=payload_body,
            digestmod=hashlib.sha256,
        )
        return hmac.compare_digest(mac.hexdigest(), signature)

    def get_installation_client(self, installation_id: int) -> Any:
        """Get an authenticated client for a specific installation."""
        return self.integration.get_github_for_installation(installation_id)
