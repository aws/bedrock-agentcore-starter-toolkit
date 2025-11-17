"""Data models for observability spans, traces, and logs."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...constants import AttributePrefixes


@dataclass
class Span:
    """Represents an OpenTelemetry span with trace and timing information."""

    trace_id: str
    span_id: str
    span_name: str
    session_id: Optional[str] = None
    start_time_unix_nano: Optional[int] = None
    end_time_unix_nano: Optional[int] = None
    duration_ms: Optional[float] = None
    status_code: Optional[str] = None
    status_message: Optional[str] = None
    parent_span_id: Optional[str] = None
    kind: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    service_name: Optional[str] = None
    resource_id: Optional[str] = None
    service_type: Optional[str] = None
    timestamp: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None
    children: List["Span"] = field(default_factory=list, repr=False)  # Child spans for hierarchy

    @classmethod
    def from_cloudwatch_result(cls, result: Any) -> "Span":
        """Create a Span from CloudWatch Logs Insights query result.

        Args:
            result: List of field dictionaries from CloudWatch query result

        Returns:
            Span object populated from the result
        """
        # CloudWatch returns a list of field objects directly
        fields = result if isinstance(result, list) else result.get("fields", [])

        # Helper to safely get field value
        def get_field(field_name: str, default: Any = None) -> Any:
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        # Helper to parse JSON string fields
        def parse_json_field(field_name: str) -> Any:
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    import json

                    return json.loads(value)
                except Exception:
                    return value
            return value

        # Helper to convert to float safely
        def get_float_field(field_name: str) -> Optional[float]:
            value = get_field(field_name)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            return None

        # Helper to convert to int safely
        def get_int_field(field_name: str) -> Optional[int]:
            value = get_field(field_name)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            return None

        # Parse @message to get attributes and resource.attributes
        raw_message = parse_json_field("@message")
        attributes = {}
        resource_attributes = {}

        if raw_message and isinstance(raw_message, dict):
            # Extract attributes from @message
            attributes = raw_message.get("attributes", {})
            if not isinstance(attributes, dict):
                attributes = {}

            # Extract resource.attributes from @message
            resource_data = raw_message.get("resource", {})
            if isinstance(resource_data, dict):
                resource_attributes = resource_data.get("attributes", {})
                if not isinstance(resource_attributes, dict):
                    resource_attributes = {}

        return cls(
            trace_id=get_field("traceId", ""),
            span_id=get_field("spanId", ""),
            span_name=get_field("spanName", ""),
            session_id=get_field("sessionId"),
            start_time_unix_nano=get_int_field("startTimeUnixNano"),
            end_time_unix_nano=get_int_field("endTimeUnixNano"),
            duration_ms=get_float_field("durationMs"),
            status_code=get_field("statusCode"),
            status_message=get_field("statusMessage"),
            parent_span_id=get_field("parentSpanId"),
            kind=get_field("kind"),
            events=parse_json_field("events") or [],
            attributes=attributes,
            resource_attributes=resource_attributes,
            service_name=get_field("serviceName"),
            resource_id=get_field("resourceId"),
            service_type=get_field("serviceType"),
            timestamp=get_field("@timestamp"),
            raw_message=raw_message,
        )


@dataclass
class RuntimeLog:
    """Represents a runtime log entry from agent-specific log groups."""

    timestamp: str
    message: str
    span_id: Optional[str] = None
    trace_id: Optional[str] = None
    log_stream: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None

    def _get_nested_value(self, obj: Dict[str, Any], *keys: str) -> Any:
        """Get value from dict trying multiple key variations (camelCase, snake_case, etc).

        Args:
            obj: Dictionary to search
            *keys: Possible key names to try

        Returns:
            First matching value or None
        """
        for key in keys:
            if key in obj:
                return obj[key]
        return None

    def get_gen_ai_message(self) -> Optional[Dict[str, Any]]:
        """Extract GenAI message from runtime log using generic discovery approach.

        Works with any model by flexibly discovering role and content from multiple
        possible locations rather than hardcoding specific formats.

        Returns:
            Dictionary with message details (role, content, timestamp) or None
        """
        if not self.raw_message or not isinstance(self.raw_message, dict):
            return None

        attributes = self.raw_message.get("attributes", {})
        event_name = attributes.get("event.name", "")

        if not event_name.startswith(f"{AttributePrefixes.GEN_AI}."):
            return None

        body = self.raw_message.get("body", {})

        # Step 1: Discover the role from multiple possible sources
        role = self._discover_role(event_name, body)
        if not role:
            return None

        # Step 2: Discover content from multiple possible locations
        content = self._discover_content(body, role)
        if not content:
            return None

        return {
            "type": "message",
            "role": role,
            "content": content,
            "timestamp": self.timestamp,
            "event_name": event_name,
        }

    def _discover_role(self, event_name: str, body: Dict[str, Any]) -> Optional[str]:
        """Discover message role from event name or body structure.

        Args:
            event_name: The gen_ai event name
            body: The event body

        Returns:
            Role string (user, assistant, system, tool) or None
        """
        # PRIORITY 1: Check for tool results first (highest priority)
        # Tool results should be identified as "tool" regardless of other role fields
        if self._has_tool_result_indicators(body):
            return "tool"

        # PRIORITY 2: Check for tool use (indicates assistant role)
        if self._has_tool_use_indicators(body):
            return "assistant"

        # PRIORITY 3: Extract from event name pattern gen_ai.{role}.message
        if "." in event_name:
            parts = event_name.split(".")
            if len(parts) >= 3 and parts[2] == "message":
                # gen_ai.user.message -> user, gen_ai.assistant.message -> assistant
                return parts[1]

        # PRIORITY 4: Check body.message.role (nested message format)
        if isinstance(body.get("message"), dict):
            role = body["message"].get("role")
            if role and role != "user":  # Don't trust "user" role if it has tool content
                return role

        # PRIORITY 5: Check body.role directly
        role = body.get("role")
        if role and role != "user":  # Don't trust "user" role if it has tool content
            return role

        # PRIORITY 6: Fallback - try legacy method for complex formats
        if not isinstance(body.get("message"), dict):
            parts = self._extract_content_parts(body)
            if parts["text"] or parts["tool_use"] or parts["tool_result"]:
                return self._determine_role(event_name, parts)

        # PRIORITY 7: Last resort - trust the role field even if "user"
        if isinstance(body.get("message"), dict):
            role = body["message"].get("role")
            if role:
                return role
        role = body.get("role")
        if role:
            return role

        return None

    def _has_tool_result_indicators(self, body: Dict[str, Any]) -> bool:
        """Check if body contains tool result indicators.

        Args:
            body: Event body

        Returns:
            True if this appears to be a tool result
        """
        # Body must be a dictionary to have tool result indicators
        if not isinstance(body, dict):
            return False

        # Direct tool result fields
        if self._get_nested_value(body, "toolResult", "tool_result"):
            return True

        # Tool call ID (indicates response to a tool call)
        if body.get("tool_call_id"):
            return True

        # Check nested message for tool result
        if isinstance(body.get("message"), dict):
            msg = body["message"]
            if msg.get("tool_call_id"):
                return True
            if self._get_nested_value(msg, "toolResult", "tool_result"):
                return True

        # Check content array for tool results
        content = body.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if self._get_nested_value(item, "toolResult", "tool_result"):
                        return True
                    if item.get("type") == "tool_result":
                        return True

        # Check nested message.content for tool results
        if isinstance(body.get("message"), dict):
            content = body["message"].get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if self._get_nested_value(item, "toolResult", "tool_result"):
                            return True
                        if item.get("type") == "tool_result":
                            return True

        return False

    def _has_tool_use_indicators(self, body: Dict[str, Any]) -> bool:
        """Check if body contains tool use indicators.

        Args:
            body: Event body

        Returns:
            True if this appears to be tool use (assistant with tools)
        """
        # Body must be a dictionary to have tool use indicators
        if not isinstance(body, dict):
            return False

        # Direct tool_calls field
        if body.get("tool_calls"):
            return True

        # Check nested message for tool_calls
        if isinstance(body.get("message"), dict):
            if body["message"].get("tool_calls"):
                return True

        # Check content array for tool use
        content = body.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if self._get_nested_value(item, "toolUse", "tool_use"):
                        return True
                    if item.get("type") in ("tool_use", "tool_call"):
                        return True
                    # Has tool-like structure (name + input/arguments)
                    if item.get("name") and (item.get("input") or item.get("arguments")):
                        return True

        # Check nested message.content for tool use
        if isinstance(body.get("message"), dict):
            content = body["message"].get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if self._get_nested_value(item, "toolUse", "tool_use"):
                            return True
                        if item.get("type") in ("tool_use", "tool_call"):
                            return True

        return False

    def _discover_content(self, body: Dict[str, Any], role: str) -> Optional[str]:
        """Discover message content from body structure.

        Args:
            body: The event body (can be dict or string)
            role: The message role

        Returns:
            Content string or None
        """
        # Handle string body directly (simple message format)
        if isinstance(body, str):
            return body

        if not isinstance(body, dict):
            return None

        content_parts = []

        # Location 1: body.message.content (nested format like gen_ai.choice)
        if isinstance(body.get("message"), dict):
            message = body["message"]
            content_items = message.get("content", [])
            content_parts.extend(self._extract_text_and_tools_from_content_array(content_items))

        # Location 2: body.content (direct format like gen_ai.user.message)
        if not content_parts and "content" in body:
            content_items = body.get("content")

            # Handle string content directly
            if isinstance(content_items, str):
                content_parts.append(content_items)
            # Handle array content
            elif isinstance(content_items, list):
                content_parts.extend(self._extract_text_and_tools_from_content_array(content_items))

        # Location 3: Try legacy extraction for complex tool use formats
        if not content_parts:
            parts = self._extract_content_parts(body)
            if parts["text"] or parts["tool_use"] or parts["tool_result"] or parts["tools"]:
                legacy_content = self._build_content_string(parts)
                if legacy_content:
                    return legacy_content

        # Special handling for tool messages - add formatting
        if role == "tool" and content_parts:
            # Extract tool_call_id from multiple locations
            tool_id = body.get("tool_call_id", "") or body.get("id", "")
            if "message" in body and isinstance(body["message"], dict):
                tool_id = body["message"].get("tool_call_id", tool_id) or body["message"].get("id", tool_id)

            return f"🔧 Tool Result [{tool_id}]:\n" + "\n".join(content_parts)

        # Special handling for assistant with tool_calls - append tool use info
        if role == "assistant":
            tool_calls = body.get("tool_calls", [])
            if not tool_calls and isinstance(body.get("message"), dict):
                tool_calls = body["message"].get("tool_calls", [])

            for tool_call in tool_calls:
                if isinstance(tool_call, dict):
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_id = tool_call.get("id", "")
                    content_parts.append(f"🔧 Tool Use: {tool_name} [ID: {tool_id}]")

        if not content_parts:
            return None

        return "\n".join(content_parts)

    def _extract_text_and_tools_from_content_array(self, content_items: Any) -> List[str]:
        """Extract text strings and tool use blocks from a content array.

        Args:
            content_items: Content array (list of items or single string)

        Returns:
            List of formatted strings (text + tool use descriptions)
        """
        parts = []

        if not content_items:
            return parts

        # Handle single string
        if isinstance(content_items, str):
            return [content_items]

        # Handle array of items
        if isinstance(content_items, list):
            import json

            for item in content_items:
                if isinstance(item, str):
                    # Direct string in array
                    parts.append(item)
                elif isinstance(item, dict):
                    # Extract text content
                    if "text" in item:
                        parts.append(item["text"])
                    elif "content" in item and isinstance(item["content"], str):
                        parts.append(item["content"])

                    # Extract tool use (multiple formats)
                    tool_info = self._try_parse_tool_use(item)
                    if tool_info:
                        tool_name = tool_info["name"]
                        tool_input = tool_info["input"]
                        parts.append(f"🔧 Tool Use: {tool_name}")
                        if tool_input:
                            parts.append(f"   Input: {json.dumps(tool_input, indent=2)}")

                    # Extract tool result
                    result_info = self._try_parse_tool_result(item)
                    if result_info:
                        result_id = result_info["id"] or "unknown"
                        result_content = result_info["content"]
                        parts.append(f"🔧 Tool Result [{result_id[:8]}...]:")
                        if isinstance(result_content, str):
                            parts.append(f"   {result_content}")
                        else:
                            parts.append(f"   {json.dumps(result_content, indent=2)}")

        return parts

    def _extract_text_from_content_array(self, content_items: Any) -> List[str]:
        """Extract text strings from a content array (without tool formatting).

        DEPRECATED: Use _extract_text_and_tools_from_content_array instead.

        Args:
            content_items: Content array (list of items or single string)

        Returns:
            List of text strings
        """
        text_parts = []

        if not content_items:
            return text_parts

        # Handle single string
        if isinstance(content_items, str):
            return [content_items]

        # Handle array of items
        if isinstance(content_items, list):
            for item in content_items:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    # Extract from dict items
                    if "text" in item:
                        text_parts.append(item["text"])
                    elif "content" in item and isinstance(item["content"], str):
                        text_parts.append(item["content"])

        return text_parts

    def _extract_content_parts(self, body: Any) -> Dict[str, Any]:
        """Extract all content parts from message body (model-agnostic).

        Handles multiple formats defensively:
        - Text: string body, text field, content string, nested content
        - Tool use: various nesting and naming patterns
        - Tool results: multiple ID field variations
        - Tool definitions: direct or nested structures

        Returns:
            Dict with keys: text, tool_use, tool_result, tools
        """
        parts = {"text": [], "tool_use": [], "tool_result": [], "tools": []}

        # Handle string body directly
        if isinstance(body, str):
            parts["text"].append(body)
            return parts

        if not isinstance(body, dict):
            return parts

        # Extract text content from multiple possible locations
        self._extract_text_content(body, parts)

        # Extract tool use from various structures
        self._extract_tool_use(body, parts)

        # Extract tool results
        self._extract_tool_results(body, parts)

        # Extract tool definitions
        self._extract_tool_definitions(body, parts)

        return parts

    def _extract_text_content(self, body: Dict[str, Any], parts: Dict[str, Any]) -> None:
        """Extract text content from multiple possible locations."""
        # Direct text field
        if "text" in body and isinstance(body["text"], str):
            parts["text"].append(body["text"])

        # Direct content string (e.g., OpenAI, Anthropic simple messages)
        if "content" in body and isinstance(body["content"], str):
            parts["text"].append(body["content"])

        # Content array with text items
        if "content" in body and isinstance(body["content"], list):
            for item in body["content"]:
                if isinstance(item, str):
                    parts["text"].append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts["text"].append(item["text"])

        # Nested message.content format (Nova gen_ai.choice events)
        if "message" in body and isinstance(body["message"], dict):
            message = body["message"]
            if "content" in message and isinstance(message["content"], list):
                for item in message["content"]:
                    if isinstance(item, dict) and "text" in item:
                        parts["text"].append(item["text"])

    def _extract_tool_use(self, body: Dict[str, Any], parts: Dict[str, Any]) -> None:
        """Extract tool use from multiple structures and naming patterns."""
        # Pattern 1: Content array with tool items (Bedrock style)
        if "content" in body and isinstance(body["content"], list):
            for item in body["content"]:
                if not isinstance(item, dict):
                    continue

                # Try to extract as tool use
                tool_info = self._try_parse_tool_use(item)
                if tool_info:
                    parts["tool_use"].append(tool_info)

        # Pattern 2: Message-level tool_calls array (OpenAI, others)
        if "tool_calls" in body and isinstance(body["tool_calls"], list):
            for tool_call in body["tool_calls"]:
                if isinstance(tool_call, dict):
                    tool_info = self._try_parse_tool_use(tool_call)
                    if tool_info:
                        parts["tool_use"].append(tool_info)

        # Pattern 3: Direct tool usage fields at message level
        tool_info = self._try_parse_tool_use(body)
        if tool_info:
            parts["tool_use"].append(tool_info)

    def _try_parse_tool_use(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to parse tool use from an item with flexible field matching.

        Returns tool_use dict or None if not a tool use.
        """
        # Check if this looks like a tool use (various indicators)
        is_tool_use = (
            self._get_nested_value(item, "toolUse", "tool_use") is not None
            or item.get("type") in ("tool_use", "function", "tool_call")
            or ("function" in item and isinstance(item["function"], dict))
            or ("name" in item and ("input" in item or "arguments" in item or "parameters" in item))
        )

        if not is_tool_use:
            return None

        # Extract tool info from various structures
        tool_data = self._get_nested_value(item, "toolUse", "tool_use") or item

        # Handle nested function structure (OpenAI style)
        if "function" in item and isinstance(item["function"], dict):
            tool_data = item["function"]

        # Extract name (required for tool use)
        tool_name = tool_data.get("name")
        if not tool_name:
            return None

        # Extract input/arguments with defensive parsing
        tool_input = self._extract_tool_arguments(tool_data)

        # Extract ID from multiple possible fields
        tool_id = (
            item.get("id")
            or tool_data.get("id")
            or self._get_nested_value(tool_data, "toolUseId", "tool_use_id", "call_id")
        )

        return {"name": tool_name, "input": tool_input, "id": tool_id}

    def _extract_tool_arguments(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tool arguments/input with defensive parsing for multiple formats."""
        # Try multiple field names
        args = tool_data.get("input") or tool_data.get("arguments") or tool_data.get("parameters") or {}

        # Handle JSON string arguments (OpenAI style)
        if isinstance(args, str):
            try:
                import json

                return json.loads(args)
            except (json.JSONDecodeError, ValueError):
                # Return as raw string in dict if parse fails
                return {"raw_arguments": args}

        # Return dict as-is
        if isinstance(args, dict):
            return args

        # Fallback for unexpected types
        return {"value": str(args)} if args else {}

    def _extract_tool_results(self, body: Dict[str, Any], parts: Dict[str, Any]) -> None:
        """Extract tool results from multiple structures."""
        # Pattern 1: Content array with tool result items (Bedrock style)
        if "content" in body and isinstance(body["content"], list):
            for item in body["content"]:
                if not isinstance(item, dict):
                    continue

                result_info = self._try_parse_tool_result(item)
                if result_info:
                    parts["tool_result"].append(result_info)

        # Pattern 2: Message-level tool result (OpenAI tool role)
        if body.get("role") == "tool":
            result_info = self._try_parse_tool_result(body)
            if result_info:
                parts["tool_result"].append(result_info)

    def _try_parse_tool_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to parse tool result from an item with flexible field matching."""
        # Check if this looks like a tool result
        is_tool_result = (
            self._get_nested_value(item, "toolResult", "tool_result") is not None
            or item.get("type") == "tool_result"
            or item.get("role") == "tool"
            or "tool_call_id" in item
        )

        if not is_tool_result:
            return None

        # Extract result data
        result_data = self._get_nested_value(item, "toolResult", "tool_result") or item

        # Extract ID from multiple possible fields
        result_id = result_data.get("tool_call_id") or self._get_nested_value(
            result_data, "toolUseId", "tool_use_id", "id"
        )

        # Extract content
        result_content = result_data.get("content", "")

        return {"id": result_id, "content": result_content}

    def _extract_tool_definitions(self, body: Dict[str, Any], parts: Dict[str, Any]) -> None:
        """Extract tool definitions from multiple structures."""
        tools = body.get("tools", [])
        if not isinstance(tools, list):
            return

        for tool in tools:
            if not isinstance(tool, dict):
                continue

            # Pattern 1: Direct format (Bedrock style)
            if "name" in tool:
                parts["tools"].append({"name": tool.get("name", "unknown"), "description": tool.get("description", "")})
            # Pattern 2: Nested function format (OpenAI style)
            elif tool.get("type") == "function" and "function" in tool:
                function_data = tool["function"]
                if isinstance(function_data, dict):
                    parts["tools"].append(
                        {
                            "name": function_data.get("name", "unknown"),
                            "description": function_data.get("description", ""),
                        }
                    )
            # Pattern 3: Try to extract name from any nested structure
            else:
                # Look for name in nested structures
                for key in ["function", "tool", "definition"]:
                    if key in tool and isinstance(tool[key], dict):
                        nested = tool[key]
                        if "name" in nested:
                            parts["tools"].append(
                                {"name": nested.get("name", "unknown"), "description": nested.get("description", "")}
                            )
                            break

    def _build_content_string(self, parts: Dict[str, Any]) -> str:
        """Build formatted content string from extracted parts."""
        import json

        sections = []

        # Add text content
        if parts["text"]:
            sections.append("\n".join(parts["text"]))

        # Add tool uses
        for tool_use in parts["tool_use"]:
            sections.append(f"🔧 Tool Use: {tool_use['name']}")
            if tool_use["input"]:
                sections.append(f"   Input: {json.dumps(tool_use['input'], indent=2)}")

        # Add tool results
        for tool_result in parts["tool_result"]:
            result_id = tool_result["id"] or "unknown"
            sections.append(f"🔧 Tool Result [{result_id[:8]}...]:")
            content = tool_result["content"]
            if isinstance(content, str):
                sections.append(f"   {content}")
            else:
                sections.append(f"   {json.dumps(content, indent=2)}")

        # Add tool definitions
        if parts["tools"]:
            sections.append("🛠️ Available Tools:")
            for tool in parts["tools"]:
                sections.append(f"  - {tool['name']}: {tool['description']}")

        return "\n".join(sections) if sections else ""

    def _determine_role(self, event_name: str, parts: Dict[str, Any]) -> Optional[str]:
        """Determine message role from event name and content."""
        # Tool results override event-based role
        if parts["tool_result"]:
            return "tool"

        # Event name based role
        if "system.message" in event_name:
            return "system"
        elif "user.message" in event_name:
            return "user"
        elif "assistant.message" in event_name or "choice" in event_name:
            return "assistant"
        elif "tool" in event_name:
            return "tool"

        return None

    def get_exception(self) -> Optional[Dict[str, Any]]:
        """Extract exception information from runtime log if present.

        Returns:
            Dictionary with exception details or None
        """
        if not self.raw_message or not isinstance(self.raw_message, dict):
            return None

        attributes = self.raw_message.get("attributes", {})
        if not attributes:
            return None

        # Check for exception attributes
        exception_type = attributes.get("exception.type")
        exception_message = attributes.get("exception.message")
        exception_stacktrace = attributes.get("exception.stacktrace")

        if exception_type or exception_message or exception_stacktrace:
            return {
                "type": "exception",
                "exception_type": exception_type,
                "message": exception_message,
                "stacktrace": exception_stacktrace,
                "timestamp": self.timestamp,
            }

        return None

    def get_event_payload(self) -> Optional[Dict[str, Any]]:
        """Extract event payload from runtime log.

        Returns:
            Dictionary with event details or None
        """
        if not self.raw_message or not isinstance(self.raw_message, dict):
            return None

        attributes = self.raw_message.get("attributes", {})
        body = self.raw_message.get("body", {})

        if not attributes and not body:
            return None

        # Skip if this is an exception (handled by get_exception)
        if attributes.get("exception.type") or attributes.get("exception.message"):
            return None

        # Get event name - try multiple possible attribute names
        event_name = (
            attributes.get("event.name")
            or attributes.get("name")
            or attributes.get("event_type")
            or attributes.get("log.level")  # For log-level events
            or ""
        )

        # Skip gen_ai messages (handled separately)
        if event_name.startswith(f"{AttributePrefixes.GEN_AI}."):
            return None

        # Extract meaningful payload data
        payload_data = {}

        # Try to get structured body
        if isinstance(body, dict):
            # For events, the body often contains the actual payload
            payload_data = body
        elif isinstance(body, str):
            # Try to parse as JSON
            try:
                import json

                payload_data = json.loads(body)
            except (json.JSONDecodeError, ValueError, TypeError):
                payload_data = {"message": body}

        # If no event name found but we have a message, use that as event description
        if not event_name and payload_data:
            # Try to derive event name from message or other fields
            if "message" in payload_data:
                # Use first 50 chars of message as event name
                msg = str(payload_data["message"])[:50]
                event_name = msg if len(msg) < 50 else msg + "..."
            elif "severity" in attributes or "log.level" in attributes:
                # This is a log event
                severity = attributes.get("severity") or attributes.get("log.level", "")
                event_name = f"log.{severity}" if severity else "log.message"

        if payload_data or event_name:
            return {
                "type": "event",
                "event_name": event_name or "log.event",
                "payload": payload_data,
                "timestamp": self.timestamp,
                "attributes": attributes,
            }

        return None

    @classmethod
    def from_cloudwatch_result(cls, result: Any) -> "RuntimeLog":
        """Create a RuntimeLog from CloudWatch Logs Insights query result.

        Args:
            result: List of field dictionaries from CloudWatch query result

        Returns:
            RuntimeLog object populated from the result
        """
        # CloudWatch returns a list of field objects directly
        fields = result if isinstance(result, list) else result.get("fields", [])

        def get_field(field_name: str, default: Any = None) -> Any:
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        def parse_json_field(field_name: str) -> Any:
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    import json

                    return json.loads(value)
                except Exception:
                    return value
            return value

        return cls(
            timestamp=get_field("@timestamp", ""),
            message=get_field("@message", ""),
            span_id=get_field("spanId"),
            trace_id=get_field("traceId"),
            log_stream=get_field("@logStream"),
            raw_message=parse_json_field("@message"),
        )


@dataclass
class TraceData:
    """Complete trace/session data including spans and runtime logs."""

    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    spans: List[Span] = field(default_factory=list)
    runtime_logs: List[RuntimeLog] = field(default_factory=list)
    traces: Dict[str, List[Span]] = field(default_factory=dict)
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    def group_spans_by_trace(self) -> None:
        """Group spans by trace_id for easier navigation."""
        self.traces = {}
        for span in self.spans:
            if span.trace_id not in self.traces:
                self.traces[span.trace_id] = []
            self.traces[span.trace_id].append(span)

        # Sort spans within each trace by start time
        for trace_id in self.traces:
            self.traces[trace_id].sort(key=lambda s: s.start_time_unix_nano or 0)

    def get_trace_ids(self) -> List[str]:
        """Get all unique trace IDs from spans."""
        return list(set(span.trace_id for span in self.spans if span.trace_id))

    @staticmethod
    def calculate_trace_duration(spans: List[Span]) -> float:
        """Calculate actual trace duration from earliest start to latest end time.

        Args:
            spans: List of spans in the trace

        Returns:
            Duration in milliseconds
        """
        start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
        end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]

        if start_times and end_times:
            # Convert nanoseconds to milliseconds
            return (max(end_times) - min(start_times)) / 1_000_000

        # Fallback: use root span duration
        root_spans = [s for s in spans if not s.parent_span_id]
        return sum(s.duration_ms or 0 for s in root_spans)

    @staticmethod
    def count_error_spans(spans: List[Span]) -> int:
        """Count number of spans with ERROR status.

        Args:
            spans: List of spans to check

        Returns:
            Number of spans with status_code == "ERROR"

        Examples:
            >>> spans = [Span(..., status_code="OK"), Span(..., status_code="ERROR")]
            >>> TraceData.count_error_spans(spans)
            1
        """
        return sum(1 for span in spans if span.status_code == "ERROR")

    def get_messages_by_span(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract chat messages, exceptions, and event payloads from runtime logs grouped by span ID.

        Returns:
            Dictionary mapping span_id to list of messages/events/exceptions with type, content, etc.
        """
        items_by_span: Dict[str, List[Dict[str, Any]]] = {}

        for log in self.runtime_logs:
            if not log.span_id:
                continue

            # Try extracting in priority order: exception > message > event
            item = log.get_exception() or log.get_gen_ai_message() or log.get_event_payload()

            if item:
                items_by_span.setdefault(log.span_id, []).append(item)

        # Sort items by timestamp within each span
        for items in items_by_span.values():
            items.sort(key=lambda m: m.get("timestamp", ""))

        return items_by_span

    def build_span_hierarchy(self, trace_id: str) -> List[Span]:
        """Build hierarchical structure of spans for a trace.

        Args:
            trace_id: The trace ID to build hierarchy for

        Returns:
            List of root spans (spans without parents in this trace)
        """
        if trace_id not in self.traces:
            return []

        # Create a map of span_id to span
        span_map = {span.span_id: span for span in self.traces[trace_id]}

        # Create a map of parent_span_id to list of children
        children_map: Dict[Optional[str], List[Span]] = {}
        root_spans: List[Span] = []

        for span in self.traces[trace_id]:
            parent_id = span.parent_span_id

            # Check if parent exists in this trace
            if parent_id and parent_id in span_map:
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(span)
            else:
                # No parent or parent not in trace = root span
                root_spans.append(span)

        # Attach children to each span
        for span in self.traces[trace_id]:
            span.children = children_map.get(span.span_id, [])

        return root_spans

    def filter_error_traces(self) -> Dict[str, List[Span]]:
        """Filter traces to only those containing errors.

        Returns:
            Dictionary mapping trace_id to list of spans for traces with errors
        """
        return {
            trace_id: spans_list
            for trace_id, spans_list in self.traces.items()
            if any(span.status_code == "ERROR" for span in spans_list)
        }

    def get_trace_messages(self, trace_id: str) -> tuple[str, str]:
        """Extract input and output messages for a trace.

        Finds the last user message (input) and last assistant message (output)
        from runtime logs associated with this trace.

        Args:
            trace_id: The trace ID to extract messages for

        Returns:
            Tuple of (input_text, output_text). Empty strings if not found.
        """
        from ...constants import TruncationConfig

        input_text = ""
        output_text = ""

        # Get runtime logs for this trace
        trace_logs = [log for log in self.runtime_logs if log.trace_id == trace_id]

        if not trace_logs:
            return input_text, output_text

        # Extract and sort messages by timestamp
        messages = []
        for log in trace_logs:
            try:
                msg = log.get_gen_ai_message()
                if msg:
                    messages.append(msg)
            except Exception:
                continue

        messages.sort(key=lambda m: m.get("timestamp", ""))

        # Find last user message (trace input)
        user_messages = [m for m in messages if m.get("role") == "user"]
        if user_messages:
            content = user_messages[-1].get("content", "")
            input_text = TruncationConfig.truncate(content, length=TruncationConfig.LIST_PREVIEW_LENGTH)

        # Find last assistant message (trace output)
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        if assistant_messages:
            content = assistant_messages[-1].get("content", "")
            output_text = TruncationConfig.truncate(content, length=TruncationConfig.LIST_PREVIEW_LENGTH)

        return input_text, output_text

    def to_dict(self) -> Dict[str, Any]:
        """Export complete trace data to dictionary for JSON serialization.

        Returns:
            Dictionary with all trace data including spans, logs, and messages
        """

        # Helper to convert span to dict recursively
        def span_to_dict(span: Span) -> Dict[str, Any]:
            return {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "span_name": span.span_name,
                "session_id": span.session_id,
                "start_time_unix_nano": span.start_time_unix_nano,
                "end_time_unix_nano": span.end_time_unix_nano,
                "duration_ms": span.duration_ms,
                "status_code": span.status_code,
                "status_message": span.status_message,
                "parent_span_id": span.parent_span_id,
                "kind": span.kind,
                "events": span.events,
                "attributes": span.attributes,
                "resource_attributes": span.resource_attributes,
                "service_name": span.service_name,
                "resource_id": span.resource_id,
                "service_type": span.service_type,
                "timestamp": span.timestamp,
                "children": [span_to_dict(child) for child in span.children],
            }

        # Convert runtime logs to dict
        def log_to_dict(log: RuntimeLog) -> Dict[str, Any]:
            result = {
                "timestamp": log.timestamp,
                "message": log.message,
                "span_id": log.span_id,
                "trace_id": log.trace_id,
                "log_stream": log.log_stream,
            }

            # Add parsed exception data (highest priority)
            exception = log.get_exception()
            if exception:
                result["parsed_exception"] = exception

            # Add parsed message and event data
            gen_ai_message = log.get_gen_ai_message()
            if gen_ai_message:
                result["parsed_gen_ai_message"] = gen_ai_message

            event_payload = log.get_event_payload()
            if event_payload:
                result["parsed_event_payload"] = event_payload

            # Include raw message for full details
            if log.raw_message:
                result["raw_message"] = log.raw_message

            return result

        # Build hierarchies for all traces
        traces_with_hierarchy = {}
        for trace_id in self.traces:
            spans = self.traces[trace_id]
            root_spans = self.build_span_hierarchy(trace_id)

            traces_with_hierarchy[trace_id] = {
                "trace_id": trace_id,
                "span_count": len(spans),
                "total_duration_ms": self.calculate_trace_duration(spans),
                "error_count": sum(1 for span in spans if span.status_code == "ERROR"),
                "root_spans": [span_to_dict(span) for span in root_spans],
            }

        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "trace_count": len(self.traces),
            "total_span_count": len(self.spans),
            "traces": traces_with_hierarchy,
            "runtime_logs": [log_to_dict(log) for log in self.runtime_logs],
        }
