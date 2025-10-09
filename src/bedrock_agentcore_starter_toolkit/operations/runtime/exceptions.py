"""Exceptions for the Bedrock AgentCore Runtime module."""

from typing import List, Optional


class RuntimeException(Exception):
    """Base exception for all Runtime SDK errors."""

    pass


class RuntimeToolkitException(RuntimeException):
    """Raised when runtime operations fail with resource tracking."""

    def __init__(self, message: str, created_resources: Optional[List[str]] = None):
        """Initialize RuntimeToolkitException with optional resource tracking.

        Args:
            message: Error message
            created_resources: List of resources created before failure
        """
        self.created_resources = created_resources or []
        if created_resources:
            full_message = f"{message}. Resources created: {created_resources}"
        else:
            full_message = message
        super().__init__(full_message)
