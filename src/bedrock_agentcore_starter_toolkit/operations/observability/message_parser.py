"""Parser for extracting structured data from OpenTelemetry runtime logs.

This parser follows OpenTelemetry semantic conventions for GenAI:
https://opentelemetry.io/docs/specs/semconv/gen-ai/

Extracts:
- Messages (user/assistant/system conversations)
- Exceptions (errors with stack traces)
"""

import json
from typing import Any, Dict, List, Optional

from ..constants import InstrumentationScopes


class UnifiedLogParser:
    """OpenTelemetry-based parser for runtime logs."""

    def parse(self, raw_message: Optional[Dict[str, Any]], timestamp: str) -> List[Dict[str, Any]]:
        """Parse structured data from an OpenTelemetry runtime log.

        Returns a list of items, each with a 'type' field:
        - type='message': User/assistant/system conversation
        - type='exception': Error with stack trace

        Args:
            raw_message: Raw message dictionary from log
            timestamp: Log timestamp

        Returns:
            List of parsed items (messages, exceptions)
        """
        if not raw_message or not isinstance(raw_message, dict):
            return []

        # 1. Check for exceptions first (highest priority)
        exception = self._extract_exception(raw_message, timestamp)
        if exception:
            return [exception]  # If exception, only return exception

        # 2. Extract messages (conversations)
        return self._extract_messages(raw_message, timestamp)

    def _extract_exception(self, raw_message: Dict[str, Any], timestamp: str) -> Optional[Dict[str, Any]]:
        """Extract exception from OTEL attributes.

        OTEL format: attributes.exception.type, attributes.exception.message, attributes.exception.stacktrace
        """
        attributes = raw_message.get("attributes", {})

        exception_type = attributes.get("exception.type")
        exception_message = attributes.get("exception.message")
        exception_stacktrace = attributes.get("exception.stacktrace")

        if exception_type or exception_message or exception_stacktrace:
            return {
                "type": "exception",
                "exception_type": exception_type,
                "message": exception_message,
                "stacktrace": exception_stacktrace,
                "timestamp": timestamp,
            }

        return None

    def _extract_messages(self, raw_message: Dict[str, Any], timestamp: str) -> List[Dict[str, Any]]:
        """Extract conversation messages using scope-based routing.

        Routes to appropriate extractor based on scope.name:
        - LangChain/LangGraph: opentelemetry.instrumentation.langchain or openinference.instrumentation.langchain
        - Strands: strands.telemetry.tracer
        - Generic OTEL: Check for gen_ai events or input/output structure
        """
        body = raw_message.get("body", {})
        if not isinstance(body, dict):
            return []

        # Get scope name for instrumentation-based routing
        scope = raw_message.get("scope", {})
        scope_name = scope.get("name", "") if isinstance(scope, dict) else ""

        # Route based on scope.name (instrumentation source)
        if scope_name in (InstrumentationScopes.OTEL_LANGCHAIN, InstrumentationScopes.OPENINFERENCE_LANGCHAIN):
            return self._extract_from_langchain(body, timestamp)

        if scope_name == InstrumentationScopes.STRANDS:
            return self._extract_from_strands(body, timestamp)

        # Fallback: Generic OTEL extraction
        return self._extract_generic_otel(raw_message, body, timestamp)

    def _get_role_from_event_name(self, event_name: str) -> Optional[str]:
        """Infer message role from OTEL gen_ai event name.

        OTEL convention: gen_ai.{role}.message
        Examples: gen_ai.user.message, gen_ai.system.message

        Special case: gen_ai.choice = assistant response
        """
        # gen_ai.choice is assistant response
        if event_name == "gen_ai.choice":
            return "assistant"

        # Parse role from event name: gen_ai.{role}.message
        parts = event_name.split(".")
        if len(parts) >= 2:
            return parts[1]  # gen_ai.{role}...

        return None

    def _extract_content(self, body: Dict[str, Any]) -> Optional[str]:
        """Extract text content from body.

        OTEL GenAI format: body.content (string or array of content parts)
        """
        if "content" not in body:
            return None

        content = body["content"]

        # String content
        if isinstance(content, str):
            return content

        # Array of content parts (OTEL multimodal)
        if isinstance(content, list):
            return self._extract_text_from_array(content)

        # Dict with nested content
        if isinstance(content, dict):
            # Check for nested text/content fields
            for field in ["text", "content", "message"]:
                if field in content:
                    value = content[field]
                    if isinstance(value, str):
                        return value

        return None

    def _extract_generic_otel(
        self, raw_message: Dict[str, Any], body: Dict[str, Any], timestamp: str
    ) -> List[Dict[str, Any]]:
        """Extract from generic OTEL format (gen_ai events or input/output structure)."""
        attributes = raw_message.get("attributes", {})
        event_name = attributes.get("event.name", "") if isinstance(attributes, dict) else ""

        # Try gen_ai events first
        if event_name.startswith("gen_ai."):
            role = self._get_role_from_event_name(event_name)
            content = self._extract_content(body)
            if role and content:
                return [{"type": "message", "role": role, "content": content, "timestamp": timestamp}]

        # Try input/output structure
        if "input" in body or "output" in body:
            return self._extract_from_input_output(body, timestamp)

        # Try direct body with role+content
        if "role" in body and "content" in body:
            content = self._extract_content(body)
            if content:
                return [{"type": "message", "role": body["role"], "content": content, "timestamp": timestamp}]

        return []

    def _extract_from_strands(self, body: Dict[str, Any], timestamp: str) -> List[Dict[str, Any]]:
        """Extract from Strands instrumentation (uses standard input/output structure)."""
        return self._extract_from_input_output(body, timestamp)

    def _extract_from_input_output(self, body: Dict[str, Any], timestamp: str) -> List[Dict[str, Any]]:
        """Extract from input/output structure.

        Format: {"input": {"messages": [...]}, "output": {"messages": [...]}}
        Used by Strands and other frameworks.
        """
        messages = []

        for source_key in ["input", "output"]:
            source = body.get(source_key)
            if not isinstance(source, dict):
                continue

            msg_list = source.get("messages", [])
            if not isinstance(msg_list, list):
                continue

            for msg in msg_list:
                if not isinstance(msg, dict):
                    continue

                role = msg.get("role")
                content = self._extract_content(msg)

                if role and content:
                    messages.append(
                        {
                            "type": "message",
                            "role": role,
                            "content": content,
                            "timestamp": timestamp,
                        }
                    )

        return messages

    def _extract_from_langchain(self, body: Dict[str, Any], timestamp: str) -> List[Dict[str, Any]]:
        """Extract from LangChain/LangGraph - parse JSON string and extract content."""
        messages = []

        # Input: user message
        input_msg = self._parse_langchain_input(body)
        if input_msg:
            messages.append({"type": "message", "role": "user", "content": input_msg, "timestamp": timestamp})

        # Output: assistant message
        output_msg = self._parse_langchain_output(body)
        if output_msg:
            messages.append({"type": "message", "role": "assistant", "content": output_msg, "timestamp": timestamp})

        return messages

    def _parse_langchain_input(self, body: Dict[str, Any]) -> Optional[str]:
        """Parse LangChain input message."""
        try:
            input_data = body.get("input", {}).get("messages", [])
            if not input_data or not isinstance(input_data[0], dict):
                return None

            content_str = input_data[0].get("content", "")
            if not isinstance(content_str, str):
                return None

            parsed = json.loads(content_str)
            lc_msg = parsed.get("inputs", {}).get("messages", [{}])[0]
            return lc_msg.get("kwargs", {}).get("content")
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            return None

    def _parse_langchain_output(self, body: Dict[str, Any]) -> Optional[str]:
        """Parse LangChain output message with tool calls."""
        try:
            output_data = body.get("output", {}).get("messages", [])
            if not output_data or not isinstance(output_data[0], dict):
                return None

            content_str = output_data[0].get("content", "")
            if not isinstance(content_str, str):
                return None

            parsed = json.loads(content_str)
            outputs = parsed.get("outputs")

            # outputs can be string like "__end__" or dict with messages
            if not isinstance(outputs, dict):
                return None

            lc_msgs = outputs.get("messages", [])
            if not lc_msgs:
                return None

            # Get last message (assistant response)
            lc_msg = lc_msgs[-1]
            kwargs = lc_msg.get("kwargs", {})
            content = kwargs.get("content")
            tool_calls = kwargs.get("tool_calls", [])

            # Format content (string or list) with tool calls
            return self._format_langchain_content(content, tool_calls)
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            return None

    def _format_langchain_content(self, content: Any, tool_calls: list) -> Optional[str]:
        """Format LangChain content (string or list) with tool calls."""
        parts = []

        # Extract text from content
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))

        # Add tool calls
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                name = tool_call.get("name", "unknown")
                args = tool_call.get("args", {})
                parts.append(f"🔧 Tool: {name}({args})")

        return "\n".join(parts) if parts else None

    def _extract_text_from_array(self, content: list) -> Optional[str]:
        """Extract text from array of content parts (OTEL multimodal format)."""
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))

        return "\n".join(text_parts) if text_parts else None
