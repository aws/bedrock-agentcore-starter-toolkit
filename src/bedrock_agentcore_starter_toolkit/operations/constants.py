"""Shared constants for observability and evaluation operations."""

import os

# Default Time Ranges
DEFAULT_LOOKBACK_DAYS = int(os.getenv("AGENTCORE_DEFAULT_LOOKBACK_DAYS", "7"))


# Query Batch Sizes
DEFAULT_BATCH_SIZE = int(os.getenv("AGENTCORE_BATCH_SIZE", "50"))


# OpenTelemetry Field Names
class OTelFields:
    """Standard OpenTelemetry field names used across spans and logs."""

    SPAN_ID = "spanId"
    TRACE_ID = "traceId"
    SESSION_ID = "sessionId"
    START_TIME = "startTimeUnixNano"
    END_TIME = "endTimeUnixNano"
    ATTRIBUTES = "attributes"
    BODY = "body"
    TIME_UNIX_NANO = "timeUnixNano"
    PARENT_SPAN_ID = "parentSpanId"
    NAME = "name"
    STATUS_CODE = "statusCode"


# Attribute Prefixes
class AttributePrefixes:
    """Common attribute prefixes used in OpenTelemetry spans."""

    GEN_AI = "gen_ai"
    LLM = "llm"
    EXCEPTION = "exception"
    EVENT = "event"
    SESSION = "session"
    TRACE = "trace"


# Gen AI Specific Attributes
class GenAIAttributes:
    """GenAI-specific attribute names."""

    PROMPT = f"{AttributePrefixes.GEN_AI}.prompt"
    COMPLETION = f"{AttributePrefixes.GEN_AI}.completion"
    USER_MESSAGE = f"{AttributePrefixes.GEN_AI}.user.message"
    SYSTEM_MESSAGE = f"{AttributePrefixes.GEN_AI}.system.message"
    ASSISTANT_MESSAGE = f"{AttributePrefixes.GEN_AI}.assistant.message"
    TOOL_MESSAGE = f"{AttributePrefixes.GEN_AI}.tool.message"
    CHOICE = f"{AttributePrefixes.GEN_AI}.choice"

    # Request/Response attributes (provider-agnostic)
    REQUEST_MODEL_INPUT = f"{AttributePrefixes.GEN_AI}.request.model.input"
    RESPONSE_MODEL_OUTPUT = f"{AttributePrefixes.GEN_AI}.response.model.output"

    # Provider-specific invocation attributes (priority order)
    INVOCATION_BEDROCK = "aws.bedrock.invocation"  # AWS Bedrock
    INVOCATION_REQUEST_BODY = "request.body"  # Generic HTTP request
    INVOCATION_RESPONSE_BODY = "response.body"  # Generic HTTP response
    INVOCATION_INPUT = "input"  # Generic input
    INVOCATION_OUTPUT = "output"  # Generic output


# LLM Specific Attributes
class LLMAttributes:
    """LLM-specific attribute names."""

    PROMPTS = f"{AttributePrefixes.LLM}.prompts"
    RESPONSES = f"{AttributePrefixes.LLM}.responses"


# Instrumentation Scope Names
class InstrumentationScopes:
    """Standard scope.name values for different instrumentation sources."""

    OTEL_LANGCHAIN = "opentelemetry.instrumentation.langchain"
    OPENINFERENCE_LANGCHAIN = "openinference.instrumentation.langchain"
    STRANDS = "strands.telemetry.tracer"


# Default Runtime Configuration
DEFAULT_RUNTIME_ENDPOINT = os.getenv("AGENTCORE_RUNTIME_ENDPOINT", "DEFAULT")
# Deprecated - kept for backward compatibility
DEFAULT_RUNTIME_SUFFIX = DEFAULT_RUNTIME_ENDPOINT


# Truncation Configuration
class TruncationConfig:
    """Configuration for content truncation in display."""

    DEFAULT_CONTENT_LENGTH = int(os.getenv("AGENTCORE_TRUNCATE_AT", "250"))
    TOOL_USE_LENGTH = int(os.getenv("AGENTCORE_TOOL_TRUNCATE_AT", "150"))
    TRUNCATION_MARKER = "..."
    LIST_PREVIEW_LENGTH = 80  # For list command input/output preview

    @classmethod
    def truncate(cls, text: str, length: int = None, is_tool_use: bool = False) -> str:
        """Truncate text to specified length.

        Args:
            text: Text to truncate
            length: Custom length (overrides default)
            is_tool_use: Whether this is tool use content (uses shorter limit)

        Returns:
            Truncated text with marker if needed
        """
        if length is None:
            length = cls.TOOL_USE_LENGTH if is_tool_use else cls.DEFAULT_CONTENT_LENGTH

        if len(text) > length:
            return text[:length] + cls.TRUNCATION_MARKER
        return text
