"""Exceptions for Bedrock AgentCore Policy operations."""


class PolicyException(Exception):
    """Base exception for Policy operations."""

    pass


class PolicySetupException(PolicyException):
    """Exception raised when policy setup fails."""

    pass


class PolicyEngineNotFoundException(PolicyException):
    """Exception raised when a policy engine is not found."""

    pass


class PolicyNotFoundException(PolicyException):
    """Exception raised when a policy is not found."""

    pass


class PolicyGenerationNotFoundException(PolicyException):
    """Exception raised when a policy generation is not found."""

    pass


class PolicyValidationException(PolicyException):
    """Exception raised when policy validation fails."""

    pass


class PolicyGenerationException(PolicyException):
    """Exception raised when policy generation fails."""

    pass
