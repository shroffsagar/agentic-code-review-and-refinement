"""GitHub App server implementation.

This module implements a GitHub App server using Flask and PyGithub,
handling webhook events and GitHub API interactions.
"""

import hashlib
import hmac
import logging
import os
from typing import Any

from flask import Flask, abort, request
from github import GithubIntegration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubApp:
    """GitHub App server implementation."""

    def __init__(self) -> None:
        """Initialize the GitHub App server."""
        # Load configuration
        self.app_id = os.getenv("GITHUB_APP_ID")
        self.private_key = os.getenv("GITHUB_PRIVATE_KEY")
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        self.enterprise_hostname = os.getenv("GITHUB_ENTERPRISE_HOSTNAME")

        if not all([self.app_id, self.private_key, self.webhook_secret]):
            raise ValueError("Missing required environment variables")

        logger.info(f"GitHub App ID: {self.app_id}")

        # Initialize GitHub integration
        base_url = (
            f"https://{self.enterprise_hostname}/api/v3"
            if self.enterprise_hostname
            else "https://api.github.com"
        )
        self.integration = GithubIntegration(
            self.app_id, self.private_key, base_url=base_url
        )

        # Create Flask app
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self) -> None:
        """Set up Flask routes."""

        @self.app.route("/api/webhook", methods=["POST"])
        def webhook() -> dict[str, Any]:
            """Handle incoming webhook events."""
            # Verify webhook signature
            signature = request.headers.get("X-Hub-Signature-256")
            if not self.verify_webhook_signature(request.get_data(), signature):
                abort(401, "Invalid signature")

            # Get event type and payload
            event_type = request.headers.get("X-GitHub-Event")
            payload = request.get_json()

            logger.info(f"Received GitHub event: {event_type}")

            # Handle workflow run events
            if event_type == "workflow_run":
                self.handle_workflow_run(payload)

            return {"status": "success"}

    def verify_webhook_signature(
        self, payload_body: bytes, signature_header: str | None
    ) -> bool:
        """Verify the GitHub webhook signature.

        Args:
            payload_body: The raw request body
            signature_header: The signature header from GitHub

        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not signature_header:
            return False

        sha_name, signature = signature_header.split("=")
        if sha_name != "sha256":
            return False

        mac = hmac.new(
            self.webhook_secret.encode(),  # type: ignore
            msg=payload_body,
            digestmod=hashlib.sha256,
        )
        return hmac.compare_digest(mac.hexdigest(), signature)

    def handle_workflow_run(self, payload: dict[str, Any]) -> None:
        """Handle workflow run events.

        Args:
            payload: The webhook payload
        """
        action = payload.get("action")
        workflow_run = payload.get("workflow_run", {})

        if action == "completed":
            conclusion = workflow_run.get("conclusion")
            if conclusion == "success":
                run_id = workflow_run.get("id")
                logger.info(f"Workflow run {run_id} completed successfully")
                # TODO: Implement post-workflow success logic
            elif conclusion == "failure":
                run_id = workflow_run.get("id")
                logger.error(f"Workflow run {run_id} failed")
                # TODO: Implement post-workflow failure logic

    def run(self, host: str = "0.0.0.0", port: int = 3000) -> None:
        """Run the GitHub App server.

        Args:
            host: The host to bind to
            port: The port to listen on
        """
        self.app.run(host=host, port=port)
