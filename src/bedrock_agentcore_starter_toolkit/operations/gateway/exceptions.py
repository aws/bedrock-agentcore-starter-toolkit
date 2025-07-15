"""Exceptions for the Bedrock AgentCore Gateway module."""


class GatewayException(Exception):
    """Base exception for all Gateway SDK errors."""

    pass


class GatewaySetupException(GatewayException):
    """Raised when gateway or Cognito setup fails."""

    pass
