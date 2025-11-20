"""Formatting utilities for observability data display."""

from typing import Any, Dict, Optional

from ..constants import GenAIAttributes, LLMAttributes, TruncationConfig

# Time conversion constants
NANOSECONDS_PER_SECOND = 1_000_000_000
NANOSECONDS_PER_MILLISECOND = 1_000_000
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400


def format_age(age_seconds: float) -> str:
    """Format age in seconds to human-readable relative time.

    Args:
        age_seconds: Age in seconds

    Returns:
        Formatted string like "5s ago", "2m ago", "3h ago", "1d ago"

    Examples:
        >>> format_age(30)
        '30s ago'
        >>> format_age(90)
        '1m ago'
        >>> format_age(7200)
        '2h ago'
    """
    if age_seconds < SECONDS_PER_MINUTE:
        return f"{int(age_seconds)}s ago"
    elif age_seconds < SECONDS_PER_HOUR:
        return f"{int(age_seconds / SECONDS_PER_MINUTE)}m ago"
    elif age_seconds < SECONDS_PER_DAY:
        return f"{int(age_seconds / SECONDS_PER_HOUR)}h ago"
    else:
        return f"{int(age_seconds / SECONDS_PER_DAY)}d ago"


def format_duration_seconds(duration_ms: float) -> str:
    """Format duration in milliseconds to seconds with 1 decimal place.

    Args:
        duration_ms: Duration in milliseconds

    Returns:
        Formatted string like "2.3s"

    Examples:
        >>> format_duration_seconds(1234.5)
        '1.2s'
        >>> format_duration_seconds(500)
        '0.5s'
    """
    return f"{duration_ms / 1000:.1f}s"


def calculate_age_seconds(timestamp_nano: int, now_nano: int) -> float:
    """Calculate age in seconds from nanosecond timestamps.

    Args:
        timestamp_nano: Event timestamp in nanoseconds
        now_nano: Current time in nanoseconds

    Returns:
        Age in seconds

    Examples:
        >>> calculate_age_seconds(1000000000000, 1005000000000)
        5.0
    """
    return (now_nano - timestamp_nano) / NANOSECONDS_PER_SECOND


def format_timestamp_relative(timestamp_nano: int, now_nano: int) -> str:
    """Format nanosecond timestamp as relative age.

    Args:
        timestamp_nano: Event timestamp in nanoseconds
        now_nano: Current time in nanoseconds

    Returns:
        Formatted relative age string

    Examples:
        >>> format_timestamp_relative(1000000000000, 1005000000000)
        '5s ago'
    """
    age_seconds = calculate_age_seconds(timestamp_nano, now_nano)
    return format_age(age_seconds)


def get_duration_style(duration_ms: float) -> str:
    """Get Rich console style based on duration.

    Color codes duration values to quickly identify slow operations:
    - Green: < 100ms (fast)
    - Yellow: 100ms - 1s (moderate)
    - Orange: 1s - 5s (slow)
    - Red: > 5s (very slow)

    Args:
        duration_ms: Duration in milliseconds

    Returns:
        Rich style string ("green", "yellow", "orange1", "red")

    Examples:
        >>> get_duration_style(50)
        'green'
        >>> get_duration_style(500)
        'yellow'
        >>> get_duration_style(2000)
        'orange1'
        >>> get_duration_style(6000)
        'red'
    """
    if duration_ms < 100:
        return "green"
    elif duration_ms < 1000:
        return "yellow"
    elif duration_ms < 5000:
        return "orange1"
    else:
        return "red"


def format_duration_ms(duration_ms: float, include_unit: bool = True) -> str:
    """Format duration in milliseconds with 2 decimal places.

    Args:
        duration_ms: Duration in milliseconds
        include_unit: Whether to include 'ms' suffix (default: True)

    Returns:
        Formatted duration string

    Examples:
        >>> format_duration_ms(1234.567)
        '1234.57ms'
        >>> format_duration_ms(1234.567, include_unit=False)
        '1234.57'
        >>> format_duration_ms(50.1)
        '50.10ms'
    """
    formatted = f"{duration_ms:.2f}"
    return f"{formatted}ms" if include_unit else formatted


def get_status_icon(status_code: str) -> str:
    """Get emoji icon for span status code.

    Args:
        status_code: Status code ("OK", "ERROR", or other)

    Returns:
        Icon string: ✓ for OK, ❌ for ERROR, ⚠ for others

    Examples:
        >>> get_status_icon("OK")
        '✓ '
        >>> get_status_icon("ERROR")
        '❌ '
        >>> get_status_icon("UNSET")
        '⚠ '
    """
    if status_code == "ERROR":
        return "❌ "
    elif status_code == "OK":
        return "✓ "
    else:
        return "⚠ "


def get_status_style(status_code: str) -> str:
    """Get Rich console style for span status code.

    Args:
        status_code: Status code ("OK", "ERROR", or other)

    Returns:
        Rich style string: "green" for OK, "red" for ERROR, "dim" for others

    Examples:
        >>> get_status_style("OK")
        'green'
        >>> get_status_style("ERROR")
        'red'
        >>> get_status_style("UNSET")
        'dim'
    """
    if status_code == "ERROR":
        return "red"
    elif status_code == "OK":
        return "green"
    else:
        return "dim"


def format_status_display(has_errors: bool) -> tuple[str, str]:
    """Format status display text and style based on error presence.

    Args:
        has_errors: Whether errors are present

    Returns:
        Tuple of (status_text, style) for display

    Examples:
        >>> format_status_display(True)
        ('❌ ERROR', 'red')
        >>> format_status_display(False)
        ('✓ OK', 'green')
    """
    if has_errors:
        return "❌ ERROR", "red"
    else:
        return "✓ OK", "green"


# Attribute extraction helpers


def get_span_attribute(attributes: Dict[str, Any], *attr_names: str) -> Optional[Any]:
    """Get first available attribute from a list of attribute names.

    Args:
        attributes: Span attributes dictionary
        *attr_names: Variable number of attribute names to check in priority order

    Returns:
        Value of first available attribute, or None if none found

    Examples:
        >>> attrs = {"gen_ai.prompt": "Hello", "llm.prompts": "World"}
        >>> get_span_attribute(attrs, "gen_ai.prompt", "llm.prompts")
        'Hello'
        >>> get_span_attribute(attrs, "missing", "llm.prompts")
        'World'
        >>> get_span_attribute(attrs, "missing")
        None
    """
    for attr_name in attr_names:
        value = attributes.get(attr_name)
        if value is not None:
            return value
    return None


def extract_prompt(attributes: Dict[str, Any]) -> Optional[str]:
    """Extract prompt/user message from span attributes.

    Checks GenAI and LLM attribute patterns in priority order.

    Args:
        attributes: Span attributes dictionary

    Returns:
        Prompt string if found, None otherwise

    Examples:
        >>> extract_prompt({"gen_ai.prompt": "Hello"})
        'Hello'
        >>> extract_prompt({"llm.prompts": "World"})
        'World'
    """
    value = get_span_attribute(
        attributes,
        GenAIAttributes.PROMPT,
        LLMAttributes.PROMPTS,
    )
    return str(value) if value is not None else None


def extract_completion(attributes: Dict[str, Any]) -> Optional[str]:
    """Extract completion/assistant response from span attributes.

    Checks GenAI and LLM attribute patterns in priority order.

    Args:
        attributes: Span attributes dictionary

    Returns:
        Completion string if found, None otherwise

    Examples:
        >>> extract_completion({"gen_ai.completion": "Response"})
        'Response'
        >>> extract_completion({"llm.responses": "Answer"})
        'Answer'
    """
    value = get_span_attribute(
        attributes,
        GenAIAttributes.COMPLETION,
        LLMAttributes.RESPONSES,
    )
    return str(value) if value is not None else None


def extract_invocation_payload(attributes: Dict[str, Any]) -> Optional[str]:
    """Extract invocation request payload from span attributes.

    Checks multiple GenAI attribute patterns for invocation data.

    Args:
        attributes: Span attributes dictionary

    Returns:
        Invocation payload string if found, None otherwise

    Examples:
        >>> extract_invocation_payload({"gen_ai.request.model.input": "{...}"})
        '{...}'
    """
    value = get_span_attribute(
        attributes,
        GenAIAttributes.REQUEST_MODEL_INPUT,
        GenAIAttributes.INVOCATION_BEDROCK,
        GenAIAttributes.INVOCATION_REQUEST_BODY,
        GenAIAttributes.INVOCATION_INPUT,
    )
    return str(value) if value is not None else None


def extract_input_data(attributes: Dict[str, Any]) -> Optional[str]:
    """Extract input data from span attributes.

    Checks multiple GenAI attribute patterns for input data.

    Args:
        attributes: Span attributes dictionary

    Returns:
        Input data string if found, None otherwise

    Examples:
        >>> extract_input_data({"gen_ai.request.model.input": "{...}"})
        '{...}'
    """
    value = get_span_attribute(
        attributes,
        GenAIAttributes.REQUEST_MODEL_INPUT,
        GenAIAttributes.INVOCATION_INPUT,
        GenAIAttributes.INVOCATION_REQUEST_BODY,
    )
    return str(value) if value is not None else None


def extract_output_data(attributes: Dict[str, Any]) -> Optional[str]:
    """Extract output data from span attributes.

    Checks multiple GenAI attribute patterns for output data.

    Args:
        attributes: Span attributes dictionary

    Returns:
        Output data string if found, None otherwise

    Examples:
        >>> extract_output_data({"gen_ai.response.model.output": "{...}"})
        '{...}'
    """
    value = get_span_attribute(
        attributes,
        GenAIAttributes.RESPONSE_MODEL_OUTPUT,
        GenAIAttributes.INVOCATION_OUTPUT,
        GenAIAttributes.INVOCATION_RESPONSE_BODY,
    )
    return str(value) if value is not None else None


def truncate_for_display(text: str, verbose: bool = False, is_tool_use: bool = False) -> str:
    """Truncate text for display based on verbose mode and content type.

    Args:
        text: Text to truncate
        verbose: If True, skip truncation and return full text
        is_tool_use: If True, use tool-specific truncation length

    Returns:
        Truncated or original text

    Examples:
        >>> truncate_for_display("Short text", verbose=False)
        'Short text'
        >>> long_text = "x" * 300
        >>> result = truncate_for_display(long_text, verbose=False)
        >>> len(result) <= 253  # 250 + "..." marker
        True
        >>> truncate_for_display(long_text, verbose=True) == long_text
        True
    """
    if verbose:
        return text
    return TruncationConfig.truncate(text, is_tool_use=is_tool_use)


def has_llm_attributes(attributes: Dict[str, Any]) -> bool:
    """Check if span has any LLM-related attributes.

    Args:
        attributes: Span attributes dictionary

    Returns:
        True if span has prompt, completion, or invocation attributes

    Examples:
        >>> has_llm_attributes({"gen_ai.prompt": "Hello"})
        True
        >>> has_llm_attributes({"span.kind": "internal"})
        False
    """
    return any(
        [
            extract_prompt(attributes) is not None,
            extract_completion(attributes) is not None,
            extract_invocation_payload(attributes) is not None,
        ]
    )
