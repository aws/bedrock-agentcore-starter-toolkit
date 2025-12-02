"""Constants for Bedrock AgentCore Policy operations."""

from enum import Enum

# Pagination defaults
DEFAULT_MAX_RESULTS = 10
MAX_RESULTS_LIMIT = 100

# Polling configuration
DEFAULT_MAX_ATTEMPTS = 30
DEFAULT_POLL_DELAY = 2  # seconds


class PolicyEngineStatus(Enum):
    """Policy engine statuses."""

    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    CREATE_FAILED = "CREATE_FAILED"
    UPDATE_FAILED = "UPDATE_FAILED"
    DELETE_FAILED = "DELETE_FAILED"


class PolicyStatus(Enum):
    """Policy statuses (same values as PolicyEngineStatus)."""

    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    CREATE_FAILED = "CREATE_FAILED"
    UPDATE_FAILED = "UPDATE_FAILED"
    DELETE_FAILED = "DELETE_FAILED"


class PolicyGenerationStatus(Enum):
    """Policy generation statuses."""

    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    GENERATE_FAILED = "GENERATE_FAILED"
    DELETE_FAILED = "DELETE_FAILED"


class ValidationMode(Enum):
    """Policy validation modes."""

    FAIL_ON_ANY_FINDINGS = "FAIL_ON_ANY_FINDINGS"
    IGNORE_ALL_FINDINGS = "IGNORE_ALL_FINDINGS"


class FindingType(Enum):
    """Finding types for policy validation."""

    VALID = "VALID"
    INVALID = "INVALID"
    NOT_TRANSLATABLE = "NOT_TRANSLATABLE"
    ALLOW_ALL = "ALLOW_ALL"
    ALLOW_NONE = "ALLOW_NONE"
    DENY_ALL = "DENY_ALL"
    DENY_NONE = "DENY_NONE"
