"""Retry boto create calls with eventual consistency IAM role progigation issues."""

import logging
import time
from typing import Any, Callable

from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


def retry_create_with_eventual_iam_consistency(create_function: Callable[[], Any], execution_role_arn: str) -> Any:
    """Wrap a create boto call with retries on role validation execptions."""
    max_retries = 3
    base_delay = 5  # Start with 2 seconds
    max_delay = 15  # Max 32 seconds between retries

    for attempt in range(max_retries + 1):
        try:
            return create_function()  # Success
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")

            # Check if this is a role validation error
            role_validation = (
                error_code == "ValidationException"
                and "Role validation failed" in error_message
                and execution_role_arn in error_message
            )
            role_invalid_param = error_code == "InvalidParameterValueException" and "cannot be assumed" in error_message
            is_role_validation_error = role_validation or role_invalid_param

            if not is_role_validation_error or attempt == max_retries:
                # Not a role validation error, or we've exhausted retries
                if is_role_validation_error:
                    log.error(
                        "Role validation failed after %d attempts. The execution role may not be ready. Role: %s",
                        max_retries + 1,
                        execution_role_arn,
                    )
                raise e

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2**attempt), max_delay)
            log.info(
                "⏳ IAM role not ready to be asssumed (attempt %d/%d), retrying in %ds... Role: %s",
                attempt + 1,
                max_retries + 1,
                delay,
                execution_role_arn,
            )
            time.sleep(delay)
