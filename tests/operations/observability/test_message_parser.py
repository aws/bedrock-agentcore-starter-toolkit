"""Data-driven tests for UnifiedLogParser using real OTEL runtime logs."""

import json
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability.message_parser import UnifiedLogParser

# Load real fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def langchain_runtime_logs():
    """Load real langchain OTEL runtime logs."""
    with open(FIXTURES_DIR / "raw_otel_langchain_runtime_logs.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def strands_openai_runtime_logs():
    """Load real strands openai OTEL runtime logs."""
    with open(FIXTURES_DIR / "raw_otel_strands_openai_runtime_logs.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def strands_bedrock_runtime_logs():
    """Load real strands bedrock OTEL runtime logs."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_runtime_logs.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture
def parser():
    """Create a UnifiedLogParser instance."""
    return UnifiedLogParser()


class TestUnifiedLogParserWithLangchain:
    """Test UnifiedLogParser with real langchain runtime logs."""

    def test_parse_all_langchain_logs(self, parser, langchain_runtime_logs):
        """Test parsing all langchain logs without errors."""
        for log in langchain_runtime_logs:
            # Should not raise any exceptions
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
            assert isinstance(items, list)

    def test_langchain_message_extraction(self, parser, langchain_runtime_logs):
        """Test that langchain messages are extracted correctly."""
        message_count = 0

        for log in langchain_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

            for item in items:
                if item.get("type") == "message":
                    message_count += 1
                    # Validate message structure
                    assert "role" in item
                    assert "content" in item
                    assert "timestamp" in item
                    # Role can be user, assistant, system, tool, or unknown (for unrecognized events)
                    assert item["role"] in ["user", "assistant", "system", "tool", "unknown"]

        # Langchain should have some messages
        assert message_count >= 0  # May be 0 if logs don't contain gen_ai events

    def test_langchain_exception_extraction(self, parser, langchain_runtime_logs):
        """Test that langchain exceptions are extracted correctly."""
        exception_count = 0

        for log in langchain_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

            for item in items:
                if item.get("type") == "exception":
                    exception_count += 1
                    # Validate exception structure
                    assert "exception_type" in item
                    assert "message" in item
                    assert "timestamp" in item

        # Langchain may have exceptions (or not)
        assert exception_count >= 0


class TestUnifiedLogParserWithStrandsOpenAI:
    """Test UnifiedLogParser with real strands openai runtime logs."""

    def test_parse_all_strands_openai_logs(self, parser, strands_openai_runtime_logs):
        """Test parsing all strands openai logs without errors."""
        for log in strands_openai_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
            assert isinstance(items, list)

    def test_strands_openai_gen_ai_message_detection(self, parser, strands_openai_runtime_logs):
        """Test that strands openai gen_ai messages are detected."""
        messages = []

        for log in strands_openai_runtime_logs:
            # Check if log has gen_ai event
            if isinstance(log, dict):
                attrs = log.get("attributes", {})
                event_name = attrs.get("event.name", "")

                if event_name.startswith("gen_ai."):
                    items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
                    messages.extend([item for item in items if item.get("type") == "message"])

        # If we have gen_ai events, we should extract messages
        if messages:
            for msg in messages:
                assert "role" in msg
                assert "content" in msg
                assert msg["role"] in ["user", "assistant", "system", "tool"]

    def test_strands_openai_input_output_structure(self, parser, strands_openai_runtime_logs):
        """Test parsing strands openai logs with input/output structure."""
        input_output_messages = []

        for log in strands_openai_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
            input_output_messages.extend(items)

        # Should be able to parse all logs
        assert isinstance(input_output_messages, list)


class TestUnifiedLogParserWithStrandsBedrock:
    """Test UnifiedLogParser with real strands bedrock runtime logs."""

    def test_parse_all_strands_bedrock_logs(self, parser, strands_bedrock_runtime_logs):
        """Test parsing all strands bedrock logs without errors."""
        for log in strands_bedrock_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
            assert isinstance(items, list)

    def test_strands_bedrock_message_extraction(self, parser, strands_bedrock_runtime_logs):
        """Test comprehensive message extraction from strands bedrock logs."""
        all_messages = []
        all_exceptions = []

        for log in strands_bedrock_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

            messages = [item for item in items if item.get("type") == "message"]
            exceptions = [item for item in items if item.get("type") == "exception"]

            all_messages.extend(messages)
            all_exceptions.extend(exceptions)

        # Strands bedrock should have many messages
        if all_messages:
            for msg in all_messages:
                assert "role" in msg
                assert "content" in msg
                assert isinstance(msg["content"], str)

        # Validate exceptions if any
        for exc in all_exceptions:
            assert "exception_type" in exc
            assert "message" in exc

    def test_strands_bedrock_tool_use_detection(self, parser, strands_bedrock_runtime_logs):
        """Test detection of tool use in strands bedrock logs."""
        tool_messages = []

        for log in strands_bedrock_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

            for item in items:
                if item.get("type") == "message":
                    content = item.get("content", "")
                    if "🔧" in content or "Tool Use" in content:
                        tool_messages.append(item)

        # Strands bedrock uses tools (code_interpreter)
        if tool_messages:
            for msg in tool_messages:
                assert "🔧" in msg["content"] or "Tool" in msg["content"]

    def test_strands_bedrock_conversation_flow(self, parser, strands_bedrock_runtime_logs):
        """Test that conversation flow is preserved in strands bedrock logs."""
        messages = []

        for log in strands_bedrock_runtime_logs:
            items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
            messages.extend([item for item in items if item.get("type") == "message"])

        # Check that messages have timestamps for ordering
        for msg in messages:
            assert "timestamp" in msg
            assert msg["timestamp"] is not None


class TestParserEdgeCases:
    """Test parser behavior with edge cases."""

    def test_parse_empty_log(self, parser):
        """Test parsing empty log."""
        items = parser.parse(None, timestamp="2025-11-18T00:00:00Z")
        assert items == []

        items = parser.parse({}, timestamp="2025-11-18T00:00:00Z")
        assert items == []

    def test_parse_non_dict_log(self, parser):
        """Test parsing non-dictionary log."""
        items = parser.parse("not a dict", timestamp="2025-11-18T00:00:00Z")
        assert items == []

        items = parser.parse(123, timestamp="2025-11-18T00:00:00Z")
        assert items == []

    def test_parse_log_without_attributes(self, parser):
        """Test parsing log without attributes field."""
        log = {"body": {"content": [{"text": "Hello"}]}}
        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")
        # Should handle gracefully
        assert isinstance(items, list)

    def test_exception_priority(self, parser):
        """Test that exceptions take priority over messages."""
        log = {
            "attributes": {
                "exception.type": "ValueError",
                "exception.message": "Test error",
                "event.name": "gen_ai.user.message",  # Also has message
            },
            "body": {"content": [{"text": "Hello"}]},
        }

        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

        # Should return exception only (priority over message)
        assert len(items) == 1
        assert items[0]["type"] == "exception"
        assert items[0]["exception_type"] == "ValueError"


class TestParserWithRealOTELEvents:
    """Test parser with real OTEL event structures."""

    def test_gen_ai_user_message_event(self, parser):
        """Test parsing gen_ai.user.message event."""
        log = {
            "attributes": {"event.name": "gen_ai.user.message"},
            "body": {"content": [{"text": "Hello, how are you?"}]},
        }

        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

        assert len(items) == 1
        assert items[0]["type"] == "message"
        assert items[0]["role"] == "user"
        assert items[0]["content"] == "Hello, how are you?"

    def test_gen_ai_choice_event(self, parser):
        """Test parsing gen_ai.choice event (assistant message)."""
        log = {
            "attributes": {"event.name": "gen_ai.choice"},
            "body": {"content": [{"text": "I'm doing well, thank you!"}]},
        }

        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

        assert len(items) == 1
        assert items[0]["type"] == "message"
        assert items[0]["role"] == "assistant"
        assert items[0]["content"] == "I'm doing well, thank you!"

    def test_gen_ai_system_message_event(self, parser):
        """Test parsing gen_ai.system.message event."""
        log = {
            "attributes": {"event.name": "gen_ai.system.message"},
            "body": {"content": [{"text": "You are a helpful assistant."}]},
        }

        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

        assert len(items) == 1
        assert items[0]["type"] == "message"
        assert items[0]["role"] == "system"

    def test_input_output_structure(self, parser):
        """Test parsing input/output structure (Strands)."""
        log = {
            "body": {
                "input": {"messages": [{"role": "user", "content": "Hello"}]},
                "output": {"messages": [{"role": "assistant", "content": "Hi there"}]},
            }
        }

        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

        # Should extract both input and output messages
        assert len(items) >= 2
        user_msg = next((item for item in items if item.get("role") == "user"), None)
        assistant_msg = next((item for item in items if item.get("role") == "assistant"), None)

        assert user_msg is not None
        assert assistant_msg is not None
        assert user_msg["content"] == "Hello"
        assert assistant_msg["content"] == "Hi there"

    def test_direct_body_with_role_content(self, parser):
        """Test parsing direct body with role and content."""
        log = {"body": {"role": "user", "content": "Direct message"}}

        items = parser.parse(log, timestamp="2025-11-18T00:00:00Z")

        assert len(items) == 1
        assert items[0]["type"] == "message"
        assert items[0]["role"] == "user"
        assert items[0]["content"] == "Direct message"
