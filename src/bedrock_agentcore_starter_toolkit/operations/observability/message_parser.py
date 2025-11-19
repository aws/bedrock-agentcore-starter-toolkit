"""Parser for extracting structured data from OpenTelemetry runtime logs.

This parser follows OpenTelemetry semantic conventions for GenAI:
https://opentelemetry.io/docs/specs/semconv/gen-ai/

Extracts:
- Messages (user/assistant/system conversations)
- Exceptions (errors with stack traces)
"""

from typing import Any, Dict, List, Optional


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
        """Extract conversation messages following OTEL conventions.

        Strategy priority (first match wins):
        1. OTEL gen_ai events (gen_ai.user.message, gen_ai.choice, etc)
        2. input/output structure (Strands, custom frameworks)
        3. Direct body with role+content (single message)
        """
        body = raw_message.get("body", {})
        if not isinstance(body, dict):
            return []

        attributes = raw_message.get("attributes", {})
        event_name = attributes.get("event.name", "") if isinstance(attributes, dict) else ""

        # Strategy 1: OTEL gen_ai events
        if event_name.startswith("gen_ai."):
            role = self._get_role_from_event_name(event_name)
            content = self._extract_content(body)
            if role and content:
                return [
                    {
                        "type": "message",
                        "role": role,
                        "content": content,
                        "timestamp": timestamp,
                    }
                ]

        # Strategy 2: input/output structure (Strands)
        if "input" in body or "output" in body:
            return self._extract_from_input_output(body, timestamp)

        # Strategy 3: Single message in body
        if "role" in body and "content" in body:
            content = self._extract_content(body)
            if content:
                return [
                    {
                        "type": "message",
                        "role": body["role"],
                        "content": content,
                        "timestamp": timestamp,
                    }
                ]

        return []

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

    def _extract_from_input_output(self, body: Dict[str, Any], timestamp: str) -> List[Dict[str, Any]]:
        """Extract from input/output structure (Strands format).

        Format: {"input": {"messages": [...]}, "output": {"messages": [...]}}
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

    def _extract_text_from_array(self, content: list) -> Optional[str]:
        """Extract text from array of content parts (OTEL multimodal format)."""
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))

        return "\n".join(text_parts) if text_parts else None
