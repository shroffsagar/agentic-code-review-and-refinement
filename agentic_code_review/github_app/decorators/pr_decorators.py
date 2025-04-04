"""Decorators for GitHub Pull Request operations."""

import functools
import inspect
import logging

from ..constants import IN_PROGRESS_LABEL
from ..managers.pr_manager import PRContext

logger = logging.getLogger(__name__)


def with_pr_state_management(operation_name: str, operation_label: str, success_message: str):
    """Decorator to manage GitHub PR state throughout an operation's lifecycle.

    This decorator provides a consistent way to handle PR operations by managing:
    1. PR context initialization
    2. Label management (adding/removing in-progress)
    3. Success message posting
    4. Error handling and error message posting

    Example:
        @with_pr_state_management(
            operation_name="review",
            operation_label=REVIEW_LABEL,
            success_message="Review completed successfully!"
        )
        async def handle_review(self, context: PRContext) -> None:
            # Only need to implement the core review logic
            pass

    Args:
        operation_name: Name of the operation (e.g., "review", "refine")
        operation_label: Label to remove when operation starts
        success_message: Message to post on successful completion

    Returns:
        Decorator function that wraps PR operations
    """

    def decorator(func):
        # Check if the function is async
        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(self, context: PRContext, *args, **kwargs):
            return await _handle_operation(
                self,
                func,
                operation_name,
                operation_label,
                success_message,
                context.installation_id,
                context.repo,
                context.pr_number,
                True,
                *args,
                **kwargs,
            )

        @functools.wraps(func)
        def sync_wrapper(self, context: PRContext, *args, **kwargs):
            return _handle_operation(
                self,
                func,
                operation_name,
                operation_label,
                success_message,
                context.installation_id,
                context.repo,
                context.pr_number,
                False,
                *args,
                **kwargs,
            )

        async def _handle_operation(
            self,
            func,
            operation_name,
            operation_label,
            success_message,
            installation_id,
            repository,
            pr_number,
            is_async_wrapper,
            *args,
            **kwargs,
        ):
            """Handle the PR operation with proper state management."""
            # Initialize PR context
            context = PRContext(
                installation_id=installation_id,
                repo=repository,  # This is already a dict from the webhook payload
                pr_number=pr_number,
            )
            logger.info(f"Starting {operation_name} for PR #{pr_number}")
            success = False

            try:
                # Update PR state to in-progress
                self.pr_manager.manage_labels(
                    context,
                    add_labels=[IN_PROGRESS_LABEL],
                    remove_labels=[operation_label],
                )

                # Execute the actual operation
                if is_async_wrapper and inspect.iscoroutinefunction(func):
                    result = await func(self, context, *args, **kwargs)
                else:
                    result = func(self, context, *args, **kwargs)

                logger.info(f"Completed {operation_name} for PR #{pr_number}")
                success = True
                return result

            except Exception as e:
                # Handle any errors
                logger.error(f"Error in {operation_name} operation for PR #{pr_number}: {e}")
                error_msg = (
                    f"❌ An error occurred while performing "
                    f"{operation_name} on this PR:\n"
                    f"```\n{e!s}\n```\n"
                    f"Please add the {operation_name} label again to retry, "
                    "or contact support if the issue persists."
                )
                self.pr_manager.post_comment(context, error_msg)
                raise

            finally:
                # Clean up PR state
                self.pr_manager.manage_labels(context, remove_labels=[IN_PROGRESS_LABEL])
                if success:
                    self.pr_manager.post_comment(context, success_message)

        # Return the appropriate wrapper based on whether the function is async
        return async_wrapper if is_async else sync_wrapper

    return decorator
