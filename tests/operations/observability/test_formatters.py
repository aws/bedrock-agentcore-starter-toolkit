"""Unit tests for formatting utilities."""

from bedrock_agentcore_starter_toolkit.operations.observability.formatters import (
    calculate_age_seconds,
    extract_completion,
    extract_input_data,
    extract_invocation_payload,
    extract_output_data,
    extract_prompt,
    format_age,
    format_duration_ms,
    format_duration_seconds,
    format_status_display,
    format_timestamp_relative,
    get_duration_style,
    get_span_attribute,
    get_status_icon,
    get_status_style,
    has_llm_attributes,
    truncate_for_display,
)


class TestFormatAge:
    """Test age formatting function."""

    def test_format_age_seconds(self):
        """Test formatting age in seconds."""
        assert format_age(0) == "0s ago"
        assert format_age(30) == "30s ago"
        assert format_age(59) == "59s ago"

    def test_format_age_minutes(self):
        """Test formatting age in minutes."""
        assert format_age(60) == "1m ago"
        assert format_age(120) == "2m ago"
        assert format_age(3540) == "59m ago"  # 59 minutes

    def test_format_age_hours(self):
        """Test formatting age in hours."""
        assert format_age(3600) == "1h ago"
        assert format_age(7200) == "2h ago"
        assert format_age(82800) == "23h ago"  # 23 hours

    def test_format_age_days(self):
        """Test formatting age in days."""
        assert format_age(86400) == "1d ago"
        assert format_age(172800) == "2d ago"
        assert format_age(604800) == "7d ago"


class TestFormatDuration:
    """Test duration formatting functions."""

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        assert format_duration_seconds(0) == "0.0s"
        assert format_duration_seconds(500) == "0.5s"
        assert format_duration_seconds(1234.5) == "1.2s"
        assert format_duration_seconds(5000) == "5.0s"

    def test_format_duration_ms_with_unit(self):
        """Test formatting duration in milliseconds with unit."""
        assert format_duration_ms(0) == "0.00ms"
        assert format_duration_ms(50.12345) == "50.12ms"
        assert format_duration_ms(1234.567) == "1234.57ms"

    def test_format_duration_ms_without_unit(self):
        """Test formatting duration without unit suffix."""
        assert format_duration_ms(1234.567, include_unit=False) == "1234.57"
        assert format_duration_ms(50.1, include_unit=False) == "50.10"

    def test_get_duration_style_fast(self):
        """Test duration style for fast operations."""
        assert get_duration_style(0) == "green"
        assert get_duration_style(50) == "green"
        assert get_duration_style(99) == "green"

    def test_get_duration_style_moderate(self):
        """Test duration style for moderate operations."""
        assert get_duration_style(100) == "yellow"
        assert get_duration_style(500) == "yellow"
        assert get_duration_style(999) == "yellow"

    def test_get_duration_style_slow(self):
        """Test duration style for slow operations."""
        assert get_duration_style(1000) == "orange1"
        assert get_duration_style(2500) == "orange1"
        assert get_duration_style(4999) == "orange1"

    def test_get_duration_style_very_slow(self):
        """Test duration style for very slow operations."""
        assert get_duration_style(5000) == "red"
        assert get_duration_style(10000) == "red"


class TestTimestampFormatting:
    """Test timestamp formatting functions."""

    def test_calculate_age_seconds(self):
        """Test age calculation from nanosecond timestamps."""
        now_nano = 1000000000000  # 1 billion nanoseconds
        timestamp_nano = 995000000000  # 5 seconds earlier

        age = calculate_age_seconds(timestamp_nano, now_nano)
        assert age == 5.0

    def test_format_timestamp_relative(self):
        """Test relative timestamp formatting."""
        now_nano = 1000000000000
        five_seconds_ago = 995000000000

        result = format_timestamp_relative(five_seconds_ago, now_nano)
        assert result == "5s ago"

    def test_format_timestamp_relative_minutes(self):
        """Test relative timestamp with minutes."""
        now_nano = 1000000000000
        two_minutes_ago = now_nano - (120 * 1_000_000_000)

        result = format_timestamp_relative(two_minutes_ago, now_nano)
        assert result == "2m ago"


class TestStatusFormatting:
    """Test status formatting functions."""

    def test_get_status_icon_ok(self):
        """Test status icon for OK status."""
        assert get_status_icon("OK") == "✓ "

    def test_get_status_icon_error(self):
        """Test status icon for ERROR status."""
        assert get_status_icon("ERROR") == "❌ "

    def test_get_status_icon_unset(self):
        """Test status icon for UNSET status."""
        assert get_status_icon("UNSET") == "⚠ "
        assert get_status_icon("") == "⚠ "
        assert get_status_icon("OTHER") == "⚠ "

    def test_get_status_style_ok(self):
        """Test status style for OK status."""
        assert get_status_style("OK") == "green"

    def test_get_status_style_error(self):
        """Test status style for ERROR status."""
        assert get_status_style("ERROR") == "red"

    def test_get_status_style_unset(self):
        """Test status style for UNSET status."""
        assert get_status_style("UNSET") == "dim"
        assert get_status_style("") == "dim"
        assert get_status_style("OTHER") == "dim"

    def test_format_status_display_with_errors(self):
        """Test status display with errors."""
        text, style = format_status_display(True)
        assert text == "❌ ERROR"
        assert style == "red"

    def test_format_status_display_without_errors(self):
        """Test status display without errors."""
        text, style = format_status_display(False)
        assert text == "✓ OK"
        assert style == "green"


class TestGetSpanAttribute:
    """Test generic span attribute extraction."""

    def test_get_span_attribute_first_match(self):
        """Test getting first matching attribute."""
        attrs = {
            "gen_ai.prompt": "First",
            "llm.prompts": "Second",
        }
        result = get_span_attribute(attrs, "gen_ai.prompt", "llm.prompts")
        assert result == "First"

    def test_get_span_attribute_fallback(self):
        """Test falling back to second attribute."""
        attrs = {
            "llm.prompts": "Second",
        }
        result = get_span_attribute(attrs, "gen_ai.prompt", "llm.prompts")
        assert result == "Second"

    def test_get_span_attribute_not_found(self):
        """Test when no attributes match."""
        attrs = {"other": "value"}
        result = get_span_attribute(attrs, "gen_ai.prompt", "llm.prompts")
        assert result is None

    def test_get_span_attribute_single_name(self):
        """Test with single attribute name."""
        attrs = {"test": "value"}
        result = get_span_attribute(attrs, "test")
        assert result == "value"

    def test_get_span_attribute_empty_dict(self):
        """Test with empty attributes dictionary."""
        result = get_span_attribute({}, "gen_ai.prompt")
        assert result is None


class TestExtractPrompt:
    """Test prompt extraction from span attributes."""

    def test_extract_prompt_from_gen_ai(self):
        """Test extracting prompt from gen_ai attribute."""
        attrs = {"gen_ai.prompt": "Hello, how are you?"}
        result = extract_prompt(attrs)
        assert result == "Hello, how are you?"

    def test_extract_prompt_from_llm(self):
        """Test extracting prompt from llm attribute."""
        attrs = {"llm.prompts": "Tell me a story"}
        result = extract_prompt(attrs)
        assert result == "Tell me a story"

    def test_extract_prompt_priority(self):
        """Test that gen_ai.prompt takes priority over llm.prompts."""
        attrs = {
            "gen_ai.prompt": "Priority",
            "llm.prompts": "Fallback",
        }
        result = extract_prompt(attrs)
        assert result == "Priority"

    def test_extract_prompt_not_found(self):
        """Test when no prompt attribute exists."""
        attrs = {"other": "value"}
        result = extract_prompt(attrs)
        assert result is None

    def test_extract_prompt_converts_to_string(self):
        """Test that non-string values are converted to string."""
        attrs = {"gen_ai.prompt": ["message1", "message2"]}
        result = extract_prompt(attrs)
        assert isinstance(result, str)
        assert "message1" in result


class TestExtractCompletion:
    """Test completion extraction from span attributes."""

    def test_extract_completion_from_gen_ai(self):
        """Test extracting completion from gen_ai attribute."""
        attrs = {"gen_ai.completion": "I'm doing well, thank you!"}
        result = extract_completion(attrs)
        assert result == "I'm doing well, thank you!"

    def test_extract_completion_from_llm(self):
        """Test extracting completion from llm attribute."""
        attrs = {"llm.responses": "Here is your answer"}
        result = extract_completion(attrs)
        assert result == "Here is your answer"

    def test_extract_completion_not_found(self):
        """Test when no completion attribute exists."""
        attrs = {"other": "value"}
        result = extract_completion(attrs)
        assert result is None


class TestExtractInvocationPayload:
    """Test invocation payload extraction."""

    def test_extract_invocation_from_request_model_input(self):
        """Test extracting from gen_ai.request.model.input."""
        attrs = {"gen_ai.request.model.input": '{"messages": []}'}
        result = extract_invocation_payload(attrs)
        assert result == '{"messages": []}'

    def test_extract_invocation_from_bedrock(self):
        """Test extracting from aws.bedrock.invocation."""
        attrs = {"aws.bedrock.invocation": '{"request": "data"}'}
        result = extract_invocation_payload(attrs)
        assert result == '{"request": "data"}'

    def test_extract_invocation_from_request_body(self):
        """Test extracting from request.body."""
        attrs = {"request.body": '{"input": "test"}'}
        result = extract_invocation_payload(attrs)
        assert result == '{"input": "test"}'

    def test_extract_invocation_from_input(self):
        """Test extracting from generic input attribute."""
        attrs = {"input": "test data"}
        result = extract_invocation_payload(attrs)
        assert result == "test data"

    def test_extract_invocation_priority_order(self):
        """Test that attributes are checked in priority order."""
        attrs = {
            "gen_ai.request.model.input": "First",
            "aws.bedrock.invocation": "Second",
            "request.body": "Third",
            "input": "Fourth",
        }
        result = extract_invocation_payload(attrs)
        assert result == "First"

    def test_extract_invocation_not_found(self):
        """Test when no invocation attribute exists."""
        attrs = {"other": "value"}
        result = extract_invocation_payload(attrs)
        assert result is None


class TestExtractInputData:
    """Test input data extraction."""

    def test_extract_input_from_request_model_input(self):
        """Test extracting input from gen_ai.request.model.input."""
        attrs = {"gen_ai.request.model.input": "input text"}
        result = extract_input_data(attrs)
        assert result == "input text"

    def test_extract_input_from_invocation_input(self):
        """Test extracting input from invocation input."""
        attrs = {"input": "test input"}
        result = extract_input_data(attrs)
        assert result == "test input"

    def test_extract_input_from_request_body(self):
        """Test extracting input from request body."""
        attrs = {"request.body": "request data"}
        result = extract_input_data(attrs)
        assert result == "request data"

    def test_extract_input_not_found(self):
        """Test when no input attribute exists."""
        attrs = {"other": "value"}
        result = extract_input_data(attrs)
        assert result is None


class TestExtractOutputData:
    """Test output data extraction."""

    def test_extract_output_from_response_model_output(self):
        """Test extracting output from gen_ai.response.model.output."""
        attrs = {"gen_ai.response.model.output": "output text"}
        result = extract_output_data(attrs)
        assert result == "output text"

    def test_extract_output_from_invocation_output(self):
        """Test extracting output from invocation output."""
        attrs = {"output": "test output"}
        result = extract_output_data(attrs)
        assert result == "test output"

    def test_extract_output_from_response_body(self):
        """Test extracting output from response body."""
        attrs = {"response.body": "response data"}
        result = extract_output_data(attrs)
        assert result == "response data"

    def test_extract_output_not_found(self):
        """Test when no output attribute exists."""
        attrs = {"other": "value"}
        result = extract_output_data(attrs)
        assert result is None


class TestTruncateForDisplay:
    """Test truncation for display."""

    def test_truncate_short_text_not_truncated(self):
        """Test that short text is not truncated."""
        text = "Short text"
        result = truncate_for_display(text, verbose=False)
        assert result == "Short text"
        assert "..." not in result

    def test_truncate_long_text_normal_mode(self):
        """Test that long text is truncated in normal mode."""
        text = "x" * 300
        result = truncate_for_display(text, verbose=False)
        assert len(result) <= 253  # 250 + "..." marker
        assert result.endswith("...")

    def test_truncate_long_text_verbose_mode(self):
        """Test that long text is NOT truncated in verbose mode."""
        text = "x" * 300
        result = truncate_for_display(text, verbose=True)
        assert result == text
        assert "..." not in result

    def test_truncate_tool_use_shorter_limit(self):
        """Test that tool use content uses shorter truncation limit."""
        text = "x" * 200
        result = truncate_for_display(text, verbose=False, is_tool_use=True)
        # Tool use limit is 150 + "..." = 153
        assert len(result) <= 153
        assert result.endswith("...")

    def test_truncate_tool_use_verbose_no_truncation(self):
        """Test that verbose mode works with tool use flag."""
        text = "x" * 200
        result = truncate_for_display(text, verbose=True, is_tool_use=True)
        assert result == text

    def test_truncate_at_exact_limit(self):
        """Test text at exact truncation limit."""
        text = "x" * 250
        result = truncate_for_display(text, verbose=False)
        # Should not be truncated (not > 250)
        assert result == text

    def test_truncate_one_over_limit(self):
        """Test text one character over limit."""
        text = "x" * 251
        result = truncate_for_display(text, verbose=False)
        # Should be truncated
        assert result.endswith("...")
        assert len(result) == 253  # 250 + "..."


class TestHasLLMAttributes:
    """Test LLM attribute detection."""

    def test_has_llm_attributes_with_prompt(self):
        """Test detection with prompt attribute."""
        attrs = {"gen_ai.prompt": "test"}
        assert has_llm_attributes(attrs) is True

    def test_has_llm_attributes_with_completion(self):
        """Test detection with completion attribute."""
        attrs = {"gen_ai.completion": "response"}
        assert has_llm_attributes(attrs) is True

    def test_has_llm_attributes_with_invocation(self):
        """Test detection with invocation attribute."""
        attrs = {"gen_ai.request.model.input": "data"}
        assert has_llm_attributes(attrs) is True

    def test_has_llm_attributes_with_multiple(self):
        """Test detection with multiple LLM attributes."""
        attrs = {
            "gen_ai.prompt": "test",
            "gen_ai.completion": "response",
        }
        assert has_llm_attributes(attrs) is True

    def test_has_llm_attributes_none(self):
        """Test detection with no LLM attributes."""
        attrs = {
            "span.kind": "internal",
            "http.status_code": 200,
        }
        assert has_llm_attributes(attrs) is False

    def test_has_llm_attributes_empty_dict(self):
        """Test detection with empty attributes."""
        assert has_llm_attributes({}) is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_format_age_negative(self):
        """Test formatting negative age (future timestamp)."""
        # Should handle gracefully
        result = format_age(-10)
        assert isinstance(result, str)

    def test_format_duration_negative(self):
        """Test formatting negative duration."""
        result = format_duration_ms(-100)
        assert isinstance(result, str)

    def test_extract_with_none_value(self):
        """Test extraction when attribute value is None."""
        attrs = {"gen_ai.prompt": None}
        result = extract_prompt(attrs)
        # Should return None since value is None
        assert result is None

    def test_truncate_empty_string(self):
        """Test truncating empty string."""
        result = truncate_for_display("", verbose=False)
        assert result == ""

    def test_get_span_attribute_with_empty_string_value(self):
        """Test that empty string is still returned as a valid value."""
        attrs = {"test": ""}
        result = get_span_attribute(attrs, "test")
        assert result == ""  # Empty string is valid, not None
