"""GitHub App server implementation.

This module implements a GitHub App server using Flask and PyGithub,
handling webhook events and GitHub API interactions.
"""

import asyncio
import logging
from typing import Any

from flask import Flask, request

from agentic_code_review.config import settings

from .auth.authenticator import GitHubAuthenticator
from .handlers.agent_handler import AgentHandler
from .managers.pr_manager import PRContext, PRManager

# Configure logging
logger = logging.getLogger(__name__)


class GitHubApp:
    """GitHub App server implementation."""

    def __init__(self) -> None:
        """Initialize the GitHub App server."""
        self.authenticator = GitHubAuthenticator(
            app_id=settings.GITHUB_APP_ID,
            private_key=settings.GITHUB_PRIVATE_KEY,
            webhook_secret=settings.GITHUB_WEBHOOK_SECRET,
            enterprise_hostname=settings.GITHUB_ENTERPRISE_URL,
        )

        self.pr_manager = PRManager(self.authenticator)
        self.agent_handler = AgentHandler(self.pr_manager)

        self.app = Flask(__name__)

        # Add request logger
        @self.app.before_request
        def log_request_info() -> None:
            logger.info("⭐️ NEW REQUEST RECEIVED ⭐️")
            logger.info(f"Path: {request.path}")
            logger.info(f"Method: {request.method}")
            # logger.info(f"Headers: {dict(request.headers)}")
            # if request.data:
            #     logger.info(f"Data: {request.data.decode()}")

        self.setup_routes()

    def setup_routes(self) -> None:
        """Set up Flask routes."""

        @self.app.route("/", methods=["GET"])
        def home() -> dict[str, Any]:
            """Basic health check endpoint."""
            logger.info("Health check endpoint called")
            return {"status": "healthy", "message": "GitHub App is running"}

        @self.app.route("/api/webhook", methods=["POST"])
        def webhook() -> dict[str, Any]:
            logger.info("Webhook endpoint called")
            return self._handle_webhook()

    def _handle_webhook(self) -> dict[str, Any]:
        """Handle incoming webhook events."""
        try:
            logger.info("🔔 Received webhook request")
            # logger.info("📋 Headers:")
            # for key, value in request.headers.items():
            #     logger.info(f"  {key}: {value}")

            signature = request.headers.get("X-Hub-Signature-256")
            payload_data = request.get_data()

            # logger.info("📦 Payload data:")
            # try:
            #     payload_str = payload_data.decode()
            #     logger.info(f"  {payload_str}")
            # except Exception as e:
            #     logger.error(f"Failed to decode payload: {e}")

            # Verify webhook signature
            if signature is None or not self.authenticator.verify_webhook_signature(payload_data, signature):
                logger.error("❌ Invalid webhook signature")
                return {"error": "Invalid signature", "status": "error"}, 401  # type: ignore

            # Process based on event type
            event_type = request.headers.get("X-GitHub-Event")
            logger.info(f"📣 Event type: {event_type}")

            payload = request.get_json()
            action = payload.get("action")
            logger.info(f"Action: {action}")

            # Handle both direct label events and pull request events
            if event_type in ["pull_request", "issues"] and action == "labeled":
                logger.info("Label added event detected")
                self._handle_labeled_event(payload)
            else:
                logger.info(f"Ignoring event type: {event_type} with action: {action}")

            return {"status": "success"}
        except Exception as e:
            logger.exception("❌ Error processing webhook:")
            return {"status": "error", "message": str(e)}, 500  # type: ignore

    def _handle_labeled_event(self, payload: dict[str, Any]) -> None:
        """Handle labeled events from both PRs and issues."""
        try:
            logger.info("🏷️ Processing labeled event")

            # Extract common fields, handling both PR and issue payloads
            repository = payload.get("repository", {})
            installation_id = payload.get("installation", {}).get("id")

            # Try to get PR number from either PR or issue payload
            pr_data = payload.get("pull_request") or payload
            pr_number = pr_data.get("number")

            # Get the label that was added
            label_name = payload.get("label", {}).get("name")

            logger.info(f"📌 Processing labeled event - PR/Issue: {pr_number}, Label: {label_name}")

            if not all([repository, pr_number, installation_id]):
                logger.error("❌ Missing required payload information")
                logger.error(f"Repository: {repository}")
                logger.error(f"PR/Issue Number: {pr_number}")
                logger.error(f"Installation ID: {installation_id}")
                return

            # Create PR context
            pr_context = PRContext(
                installation_id=int(installation_id) if installation_id else 0,
                repo=repository,
                pr_number=int(pr_number) if pr_number else 0,
            )

            if self.pr_manager.is_in_progress(pr_context):
                msg = "⏳ This PR is currently being processed. Please wait for the current operation to complete."
                logger.info("⚠️ PR is already being processed")
                self.pr_manager.post_comment(pr_context, msg)
                return

            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Pass to the appropriate handler based on label
                if label_name == "agentic-review":
                    loop.run_until_complete(
                        self.agent_handler.handle_review(pr_context)
                    )
                elif label_name == "agentic-refine":
                    loop.run_until_complete(
                        self.agent_handler.handle_refinement(pr_context)
                    )
                else:
                    logger.info(f"⏭️ Ignoring non-matching label: {label_name}")
            finally:
                loop.close()

        except Exception:
            logger.exception("❌ Error handling labeled event:")

    def run(self, host: str = "0.0.0.0", port: int = 3000) -> None:
        """Run the GitHub App server."""
        # Enable Flask development mode
        self.app.run(host=host, port=port, debug=True)
