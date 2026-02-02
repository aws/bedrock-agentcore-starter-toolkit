"""Tests for memory formatters."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from bedrock_agentcore_starter_toolkit.operations.memory.memory_formatters import (
    DisplayConfig,
    extract_event_role,
    extract_event_text,
    extract_event_type,
    extract_record_text,
    format_content_preview,
    format_memory_age,
    format_namespaces,
    format_role_icon,
    format_truncation_hint,
    get_memory_status_icon,
    get_memory_status_style,
    get_strategy_status_style,
    get_strategy_type_icon,
    render_content_panel,
    truncate_text,
)


class TestStatusFormatters:
    """Test status formatting functions."""

    def test_get_memory_status_icon_active(self):
        assert get_memory_status_icon("ACTIVE") == "✓ "

    def test_get_memory_status_icon_creating(self):
        assert get_memory_status_icon("CREATING") == "⏳ "

    def test_get_memory_status_icon_failed(self):
        assert get_memory_status_icon("FAILED") == "❌ "

    def test_get_memory_status_icon_unknown(self):
        assert get_memory_status_icon("UNKNOWN") == "? "

    def test_get_memory_status_style_active(self):
        assert get_memory_status_style("ACTIVE") == "green"

    def test_get_memory_status_style_failed(self):
        assert get_memory_status_style("FAILED") == "red"

    def test_get_memory_status_style_unknown(self):
        assert get_memory_status_style("UNKNOWN") == "dim"

    def test_get_strategy_type_icon(self):
        assert get_strategy_type_icon("SEMANTIC") == ""

    def test_get_strategy_status_style(self):
        assert get_strategy_status_style("ACTIVE") == "green"


class TestFormatNamespaces:
    """Test namespace formatting."""

    def test_format_namespaces_empty(self):
        assert format_namespaces([]) == "[dim]None[/dim]"

    def test_format_namespaces_single(self):
        assert format_namespaces(["/users/{actorId}/"]) == "/users/{actorId}/"

    def test_format_namespaces_multiple(self):
        result = format_namespaces(["/a/", "/b/"])
        assert result == "/a/, /b/"


class TestFormatMemoryAge:
    """Test age formatting."""

    def test_format_memory_age_none(self):
        assert format_memory_age(None) == "N/A"

    def test_format_memory_age_seconds(self):
        now = datetime.now(timezone.utc)
        result = format_memory_age(now)
        assert "s ago" in result

    def test_format_memory_age_minutes(self):
        from datetime import timedelta

        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = format_memory_age(past)
        assert "m ago" in result

    def test_format_memory_age_hours(self):
        from datetime import timedelta

        past = datetime.now(timezone.utc) - timedelta(hours=3)
        result = format_memory_age(past)
        assert "h ago" in result

    def test_format_memory_age_days(self):
        from datetime import timedelta

        past = datetime.now(timezone.utc) - timedelta(days=5)
        result = format_memory_age(past)
        assert "d ago" in result

    def test_format_memory_age_no_timestamp(self):
        result = format_memory_age("2024-01-01")
        assert result == "2024-01-01"

    def test_format_memory_age_exception(self):
        mock_obj = MagicMock()
        mock_obj.timestamp.side_effect = Exception("error")
        result = format_memory_age(mock_obj)
        assert result is not None


class TestExtractRecordText:
    """Test record text extraction."""

    def test_extract_record_text_dict_content(self):
        record = {"content": {"text": "hello"}}
        assert extract_record_text(record) == "hello"

    def test_extract_record_text_string_content(self):
        record = {"content": "plain text"}
        assert extract_record_text(record) == "plain text"

    def test_extract_record_text_no_text_key(self):
        record = {"content": {"other": "value"}}
        result = extract_record_text(record)
        assert "other" in result

    def test_extract_record_text_empty(self):
        record = {}
        assert extract_record_text(record) == "{}"


class TestExtractEventText:
    """Test event text extraction."""

    def test_extract_event_text_valid(self):
        import json

        event = {
            "payload": [
                {"conversational": {"content": {"text": json.dumps({"message": {"content": [{"text": "hello"}]}})}}}
            ]
        }
        assert extract_event_text(event) == "hello"

    def test_extract_event_text_no_payload(self):
        assert extract_event_text({}) is None

    def test_extract_event_text_empty_payload(self):
        assert extract_event_text({"payload": []}) is None

    def test_extract_event_text_no_conversational(self):
        assert extract_event_text({"payload": [{"blob": {}}]}) is None

    def test_extract_event_text_no_content(self):
        event = {"payload": [{"conversational": {}}]}
        assert extract_event_text(event) is None

    def test_extract_event_text_invalid_json(self):
        event = {"payload": [{"conversational": {"content": {"text": "not json"}}}]}
        assert extract_event_text(event) is None


class TestExtractEventRole:
    """Test event role extraction."""

    def test_extract_event_role_user(self):
        event = {"payload": [{"conversational": {"role": "USER"}}]}
        assert extract_event_role(event) == "USER"

    def test_extract_event_role_assistant(self):
        event = {"payload": [{"conversational": {"role": "ASSISTANT"}}]}
        assert extract_event_role(event) == "ASSISTANT"

    def test_extract_event_role_no_payload(self):
        assert extract_event_role({}) is None

    def test_extract_event_role_no_conversational(self):
        assert extract_event_role({"payload": [{"blob": {}}]}) is None


class TestExtractEventType:
    """Test event type extraction."""

    def test_extract_event_type_conversational(self):
        event = {"payload": [{"conversational": {}}]}
        assert extract_event_type(event) == "conversational"

    def test_extract_event_type_blob(self):
        event = {"payload": [{"blob": {}}]}
        assert extract_event_type(event) == "blob"

    def test_extract_event_type_empty(self):
        assert extract_event_type({}) is None

    def test_extract_event_type_unknown(self):
        event = {"payload": [{"other": {}}]}
        assert extract_event_type(event) is None


class TestTruncation:
    """Test truncation functions."""

    def test_truncate_text_short(self):
        assert truncate_text("short", 10) == "short"

    def test_truncate_text_long(self):
        result = truncate_text("this is a long text", 10)
        assert result == "this is a ..."

    def test_truncate_text_verbose(self):
        result = truncate_text("this is a long text", 10, verbose=True)
        assert result == "this is a long text"

    def test_format_content_preview_newlines(self):
        result = format_content_preview("line1\nline2")
        assert "\n" not in result

    def test_format_content_preview_long(self):
        long_text = "x" * 200
        result = format_content_preview(long_text)
        assert len(result) <= DisplayConfig.MAX_PREVIEW_LENGTH + 3


class TestRenderContentPanel:
    """Test content panel rendering."""

    def test_render_content_panel_verbose(self):
        from rich.panel import Panel

        result = render_content_panel("content", verbose=True)
        assert isinstance(result, Panel)

    def test_render_content_panel_not_verbose(self):
        result = render_content_panel("content", verbose=False)
        assert isinstance(result, str)


class TestFormatTruncationHint:
    """Test truncation hint formatting."""

    def test_format_truncation_hint_none(self):
        assert format_truncation_hint(10, 10) == ""

    def test_format_truncation_hint_some(self):
        result = format_truncation_hint(5, 10)
        assert "5 more" in result


class TestFormatRoleIcon:
    """Test role icon formatting."""

    def test_format_role_icon_user(self):
        result = format_role_icon("USER")
        assert "User" in result
        assert "👤" in result

    def test_format_role_icon_assistant(self):
        result = format_role_icon("ASSISTANT")
        assert "Assistant" in result
        assert "🤖" in result

    def test_format_role_icon_none(self):
        result = format_role_icon(None)
        assert "Unknown" in result

    def test_format_role_icon_other(self):
        result = format_role_icon("SYSTEM")
        assert "SYSTEM" in result


# Tests for constants.py
class TestStrategyTypeConstants:
    """Test StrategyType enum methods."""

    def test_consolidation_wrapper_key_summary(self):
        from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType

        assert StrategyType.SUMMARY.consolidation_wrapper_key() == "summaryConsolidationConfiguration"

    def test_consolidation_wrapper_key_non_summary(self):
        from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType

        assert StrategyType.SEMANTIC.consolidation_wrapper_key() is None
        assert StrategyType.CUSTOM.consolidation_wrapper_key() is None

    def test_get_override_type_custom(self):
        from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType

        assert StrategyType.CUSTOM.get_override_type() == "CUSTOM_OVERRIDE"

    def test_get_override_type_non_custom(self):
        from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType

        assert StrategyType.SEMANTIC.get_override_type() is None
        assert StrategyType.SUMMARY.get_override_type() is None
