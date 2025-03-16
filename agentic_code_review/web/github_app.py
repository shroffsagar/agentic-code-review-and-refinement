"""GitHub App server implementation.

This module implements a GitHub App server using Flask and PyGithub,
handling webhook events and GitHub API interactions.
"""

import logging
import os
from typing import Any

from flask import Flask, abort, request

from .auth.authenticator import GitHubAuthenticator
from .constants import REFINE_LABEL, REVIEW_LABEL
from .handlers.agent_handler import AgentHandler
from .managers.pr_manager import PRContext, PRManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubApp:
    """GitHub App server implementation."""

    def __init__(self) -> None:
        """Initialize the GitHub App server."""
        self.authenticator = GitHubAuthenticator(
            app_id=os.environ["GITHUB_APP_ID"],
            private_key=os.environ["GITHUB_PRIVATE_KEY"],
            webhook_secret=os.environ["GITHUB_WEBHOOK_SECRET"],
            enterprise_hostname=os.getenv("GITHUB_ENTERPRISE_HOSTNAME"),
        )

        self.pr_manager = PRManager(self.authenticator)
        self.agent_handler = AgentHandler(self.pr_manager)

        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self) -> None:
        """Set up Flask routes."""

        @self.app.route("/api/webhook", methods=["POST"])
        def webhook() -> dict[str, Any]:
            return self._handle_webhook()

    def _handle_webhook(self) -> dict[str, Any]:
        """Handle incoming webhook events."""
        signature = request.headers.get("X-Hub-Signature-256")
        payload_data = request.get_data()

        if not self.authenticator.verify_webhook_signature(payload_data, signature):
            abort(401, "Invalid signature")

        event_type = request.headers.get("X-GitHub-Event")
        if event_type == "label":
            self._handle_label_event(request.get_json())

        return {"status": "success"}

    def _handle_label_event(self, payload: dict[str, Any]) -> None:
        """Handle label events."""
        if payload.get("action") != "labeled":
            return

        repository = payload.get("repository", {})
        pr_number = payload.get("pull_request", {}).get("number")
        installation_id = payload.get("installation", {}).get("id")
        label_name = payload.get("label", {}).get("name")

        if not all([repository, pr_number, installation_id]):
            logger.error("Missing required payload information")
            return

        context = PRContext(installation_id, repository, pr_number)

        if self.pr_manager.is_in_progress(context):
            msg = (
                "⏳ This PR is currently being processed. "
                "Please wait for the current operation to complete."
            )
            self.pr_manager.post_comment(context, msg)
            return

        if label_name == REVIEW_LABEL:
            self.agent_handler.handle_review(installation_id, repository, pr_number)
        elif label_name == REFINE_LABEL:
            self.agent_handler.handle_refine(installation_id, repository, pr_number)

    def run(self, host: str = "0.0.0.0", port: int = 3000) -> None:
        """Run the GitHub App server."""
        self.app.run(host=host, port=port)
