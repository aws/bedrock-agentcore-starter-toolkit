# OpenAI Compatibility Analysis

## Current Format Support

The current implementation supports:
- ✅ AWS Bedrock (camelCase): `toolUse`, `toolResult`, `toolUseId`
- ✅ Standard (snake_case): `tool_use`, `tool_result`, `tool_use_id`
- ✅ Type-based: `{"type": "tool_use", ...}`
- ❌ OpenAI format

## OpenAI Format Examples

### OpenAI Tool Call (Assistant Message)
```json
{
  "role": "assistant",
  "content": "I'll calculate that for you.",
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "calculate",
        "arguments": "{\"expression\": \"2+2\"}"
      }
    }
  ]
}
```

### OpenAI Tool Result (Tool Message)
```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "4"
}
```

### OpenAI System Message with Tools
```json
{
  "role": "system",
  "content": "You are a helpful assistant.",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "calculate",
        "description": "Perform calculations",
        "parameters": {...}
      }
    }
  ]
}
```

## Compatibility Issues

### Issue 1: Tool Calls Location
**Current Code**: Looks in `body.get("content", [])` array for tool_use
**OpenAI**: Uses `body.get("tool_calls", [])` at message level

```python
# Current (AWS/Bedrock):
content_array = body.get("content", [])  # Tool use inside content array

# OpenAI needs:
tool_calls = body.get("tool_calls", [])  # Tool calls at message level
```

### Issue 2: Nested Function Structure
**Current Code**: Expects `tool_info.get("name")` and `tool_info.get("input")`
**OpenAI**: Has nested structure `tool_call["function"]["name"]` and `tool_call["function"]["arguments"]`

```python
# Current (AWS/Bedrock):
{
  "type": "tool_use",
  "name": "calculate",
  "input": {"expression": "2+2"}
}

# OpenAI:
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "calculate",
    "arguments": "{\"expression\": \"2+2\"}"  # JSON string, not object!
  }
}
```

### Issue 3: Arguments vs Input
**Current Code**: Uses `tool_info.get("input", {})`
**OpenAI**: Uses `function["arguments"]` as JSON string (needs parsing)

### Issue 4: Tool Call ID
**Current Code**: Looks for `toolUseId`, `tool_use_id`, `id`
**OpenAI**: Uses `tool_call_id` for results, `id` for calls

### Issue 5: Type Field
**Current Code**: Checks `item.get("type") == "tool_use"`
**OpenAI**: Uses `item.get("type") == "function"`

## Impact Assessment

| Feature | Current Support | OpenAI Format | Works? |
|---------|----------------|---------------|--------|
| Text messages | ✅ | ✅ | ✅ Yes |
| Tool use extraction | ✅ | ❌ | ❌ No - different structure |
| Tool results | ✅ | ❌ | ❌ No - different ID field |
| Tool definitions | ✅ | ⚠️ | ⚠️ Partial - nested structure |
| Role detection | ✅ | ✅ | ✅ Yes |

## Recommended Fixes

### Option 1: Add OpenAI Support to Existing Logic (Minimal Changes)

```python
def _extract_content_parts(self, body: Any) -> Dict[str, Any]:
    """Extract all content parts from message body."""
    parts = {
        "text": [],
        "tool_use": [],
        "tool_result": [],
        "tools": []
    }

    if isinstance(body, str):
        parts["text"].append(body)
        return parts

    if not isinstance(body, dict):
        return parts

    # Handle direct text field
    if "text" in body:
        parts["text"].append(body["text"])

    # Handle content array (AWS/Bedrock style)
    content_array = body.get("content", [])
    if isinstance(content_array, list):
        for item in content_array:
            if not isinstance(item, dict):
                continue

            # Text content
            if "text" in item:
                parts["text"].append(item["text"])

            # Tool use - AWS/Bedrock style
            tool_use_data = self._get_nested_value(item, "toolUse", "tool_use")
            if tool_use_data or item.get("type") == "tool_use":
                tool_info = tool_use_data if isinstance(tool_use_data, dict) else item
                tool_name = tool_info.get("name", "unknown")
                tool_input = tool_info.get("input", {})

                parts["tool_use"].append({
                    "name": tool_name,
                    "input": tool_input,
                    "id": self._get_nested_value(tool_info, "toolUseId", "tool_use_id", "id")
                })

            # Tool result - AWS/Bedrock style
            tool_result_data = self._get_nested_value(item, "toolResult", "tool_result")
            if tool_result_data or item.get("type") == "tool_result":
                result_info = tool_result_data if isinstance(tool_result_data, dict) else item
                result_id = self._get_nested_value(result_info, "toolUseId", "tool_use_id", "id")
                result_content = result_info.get("content", "")

                parts["tool_result"].append({
                    "id": result_id,
                    "content": result_content
                })

    # NEW: Handle OpenAI tool_calls at message level
    tool_calls = body.get("tool_calls", [])
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            # OpenAI function call structure
            if tool_call.get("type") == "function":
                function_data = tool_call.get("function", {})
                tool_name = function_data.get("name", "unknown")

                # Parse arguments JSON string
                arguments_str = function_data.get("arguments", "{}")
                try:
                    import json
                    tool_input = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
                except (json.JSONDecodeError, ValueError):
                    tool_input = {"raw": arguments_str}

                parts["tool_use"].append({
                    "name": tool_name,
                    "input": tool_input,
                    "id": tool_call.get("id")
                })

    # NEW: Handle OpenAI tool result (role=tool at message level)
    if body.get("role") == "tool":
        tool_call_id = body.get("tool_call_id")
        content = body.get("content", "")

        parts["tool_result"].append({
            "id": tool_call_id,
            "content": content
        })

    # Handle tool definitions (both formats)
    tools = body.get("tools", [])
    if isinstance(tools, list):
        for tool in tools:
            if not isinstance(tool, dict):
                continue

            # AWS/Bedrock direct format
            if "name" in tool:
                parts["tools"].append({
                    "name": tool.get("name", "unknown"),
                    "description": tool.get("description", "")
                })
            # OpenAI nested format
            elif tool.get("type") == "function":
                function_data = tool.get("function", {})
                parts["tools"].append({
                    "name": function_data.get("name", "unknown"),
                    "description": function_data.get("description", "")
                })

    return parts
```

### Option 2: Framework-Specific Extractors (Better Separation)

```python
def _extract_content_parts(self, body: Any) -> Dict[str, Any]:
    """Extract all content parts from message body."""
    parts = {
        "text": [],
        "tool_use": [],
        "tool_result": [],
        "tools": []
    }

    if isinstance(body, str):
        parts["text"].append(body)
        return parts

    if not isinstance(body, dict):
        return parts

    # Detect framework and extract accordingly
    if "tool_calls" in body:
        # OpenAI format
        self._extract_openai_format(body, parts)
    elif "content" in body and isinstance(body["content"], list):
        # AWS/Bedrock format
        self._extract_bedrock_format(body, parts)
    else:
        # Generic/fallback
        self._extract_generic_format(body, parts)

    return parts

def _extract_openai_format(self, body: Dict, parts: Dict) -> None:
    """Extract OpenAI-specific format."""
    # Handle text content
    if "content" in body and isinstance(body["content"], str):
        parts["text"].append(body["content"])

    # Handle tool calls
    for tool_call in body.get("tool_calls", []):
        if tool_call.get("type") == "function":
            function_data = tool_call.get("function", {})
            arguments_str = function_data.get("arguments", "{}")

            try:
                import json
                tool_input = json.loads(arguments_str)
            except:
                tool_input = {"raw": arguments_str}

            parts["tool_use"].append({
                "name": function_data.get("name", "unknown"),
                "input": tool_input,
                "id": tool_call.get("id")
            })

    # Handle tool results
    if body.get("role") == "tool":
        parts["tool_result"].append({
            "id": body.get("tool_call_id"),
            "content": body.get("content", "")
        })

    # Handle tool definitions
    for tool in body.get("tools", []):
        if tool.get("type") == "function":
            function_data = tool.get("function", {})
            parts["tools"].append({
                "name": function_data.get("name", "unknown"),
                "description": function_data.get("description", "")
            })

def _extract_bedrock_format(self, body: Dict, parts: Dict) -> None:
    """Extract AWS/Bedrock-specific format (current implementation)."""
    # Current implementation goes here...
```

## Testing Strategy

Add test cases for OpenAI format:

```python
def test_runtime_log_get_gen_ai_message_openai_tool_call(self):
    """Test extracting OpenAI-style tool call."""
    cloudwatch_result = [
        {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
        {
            "field": "@message",
            "value": json.dumps({
                "attributes": {"event.name": "gen_ai.assistant.message"},
                "body": {
                    "content": "I'll calculate that.",
                    "tool_calls": [{
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "calculate",
                            "arguments": '{"expression": "2+2"}'
                        }
                    }]
                }
            })
        },
        {"field": "spanId", "value": "span-123"},
        {"field": "traceId", "value": "trace-456"},
    ]

    log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
    message = log.get_gen_ai_message()

    assert message is not None
    assert message["role"] == "assistant"
    assert "calculate that" in message["content"]
    assert "🔧 Tool Use: calculate" in message["content"]
    assert "expression" in message["content"]

def test_runtime_log_get_gen_ai_message_openai_tool_result(self):
    """Test extracting OpenAI-style tool result."""
    cloudwatch_result = [
        {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
        {
            "field": "@message",
            "value": json.dumps({
                "attributes": {"event.name": "gen_ai.tool.message"},
                "body": {
                    "role": "tool",
                    "tool_call_id": "call_abc123",
                    "content": "4"
                }
            })
        },
        {"field": "spanId", "value": "span-123"},
        {"field": "traceId", "value": "trace-456"},
    ]

    log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
    message = log.get_gen_ai_message()

    assert message is not None
    assert message["role"] == "tool"
    assert "call_abc123" in message["content"]
    assert "4" in message["content"]
```

## Recommendation

**Option 1 (Add OpenAI Support)** is recommended because:
1. ✅ Maintains backward compatibility
2. ✅ Minimal code changes
3. ✅ Follows existing patterns
4. ✅ Easy to test
5. ✅ Doesn't require refactoring

Would you like me to implement Option 1 to add OpenAI support?
