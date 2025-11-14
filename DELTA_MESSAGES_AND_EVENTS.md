# Delta Messages and Event Payloads - Enhanced Implementation

## Overview

Enhanced the `--show-messages` flag to display **delta messages** (only new data at each span) and **event payloads** from runtime logs, providing intuitive, non-repetitive visibility into agent execution.

## Key Features

### 1. Delta Messages (No Repetition)
**Problem**: Previously, showing full conversation history at each span level caused repetition - the same messages appeared multiple times as they propagated through parent spans.

**Solution**: Track which messages have been shown in parent spans and only display NEW messages at each level.

**Implementation**:
- Pass `seen_messages` set through tree traversal
- Each span marks its messages as "seen" for child spans
- Children only display messages not in the `seen_messages` set
- Results in clean, intuitive output where each message appears exactly once

### 2. Event Payloads
**Enhancement**: Display payloads from ALL runtime log events, not just chat messages.

**Supported Event Types**:
- **Chat Messages**: `gen_ai.system.message`, `gen_ai.user.message`, `gen_ai.assistant.message`
- **Tracer Events**: `strands.telemetry.tracer` (shows input/output of operations)
- **Generic Events**: Any other event with body/attributes
- **Log Messages**: General log entries with messages

**Display Format**:
```
└─ 📋 Data (2 msg, 1 event):
    ⚙️ System: You are a helpful assistant...
    👤 User: Create a text-based bar chart...
    📦 Event: strands.telemetry.tracer
       output={'messages': [...]}, input={'messages': [...]}
```

## Implementation Details

### 1. Enhanced RuntimeLog Model

Added methods to extract different types of data:

```python
class RuntimeLog:
    def get_gen_ai_message(self) -> Optional[Dict[str, Any]]:
        """Extract chat messages from gen_ai.* events."""
        # Returns: {type: "message", role, content, timestamp, event_name}

    def get_event_payload(self) -> Optional[Dict[str, Any]]:
        """Extract event payloads from non-gen_ai events."""
        # Returns: {type: "event", event_name, payload, timestamp, attributes}
```

### 2. Combined Message/Event Collection

Updated `TraceData.get_messages_by_span()` to collect both:

```python
def get_messages_by_span(self) -> Dict[str, List[Dict[str, Any]]]:
    """Extract both chat messages and event payloads grouped by span ID."""
    # Collects messages: {type: "message", ...}
    # Collects events: {type: "event", ...}
    # Sorts by timestamp
    # Returns: Dict[span_id -> List[item]]
```

### 3. Delta Tracking in Visualizer

Updated tree traversal to track seen messages:

```python
def _add_span_to_tree(..., seen_messages: Optional[set] = None):
    """Add span with delta message tracking."""
    # Display span with only new messages
    # Mark current span's messages as "seen"
    # Pass seen_messages to children
```

### 4. Unique Item Identification

Created method to generate unique IDs for deduplication:

```python
def _get_item_id(self, item: Dict[str, Any]) -> str:
    """Create unique identifier for message or event."""
    # For messages: msg_{timestamp}_{role}_{content_hash}
    # For events: evt_{timestamp}_{event_name}_{payload_hash}
```

### 5. Smart Payload Formatting

Format event payloads intelligently:

```python
def _format_event_payload(self, payload: Dict[str, Any]) -> str:
    """Format event payload for display."""
    # Extracts important keys: type, name, id, status, message, error, result, count, data
    # Shows up to 3 most relevant fields
    # Truncates long values
    # Returns: "key1=value1, key2=value2, key3=value3"
```

## Example Output

### Single Trace Visualization

```bash
agentcore observability visualize-trace \
  --trace-id 68f947ff \
  --agent-id test-EPMVTFAk5W \
  --region us-east-1 \
  --show-messages
```

**Output**:
```
🔍 Trace: 68f947ff49e0bf55... (19 spans, 126029.03ms)
└── ◦ POST /invocations [26279.52ms] (UNSET)
      └─ 📡 HTTP: POST /invocations [200]
      └─ 📋 Data (2 event):
          📦 Event: unknown
             message=Attempting to instrument while already instrumented
          📦 Event: unknown
             message=Invocation completed successfully (26.279s)
    └── ✓ invoke_agent Strands Agents [25602.28ms] (OK)
          └─ 🤖 Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0
          └─ 🎯 Tokens: in: 411, out: 117
          └─ 📋 Data (1 event):
              📦 Event: strands.telemetry.tracer
                 output={'messages': [...]}, input={'messages': [...]}
        ├── ✓ execute_event_loop_cycle [24348.86ms] (OK)
        │     └─ 📋 Data (1 event):
        │         📦 Event: strands.telemetry.tracer
        │            input={'messages': [...]}
        │   └── ✓ chat [23846.06ms] (OK)
        │         └─ 📋 Data (1 event):
        │             📦 Event: strands.telemetry.tracer
        │                output={'messages': [...]}, input={'messages': [...]}
        │       └── ◦ chat us.anthropic.claude-3-7-sonnet [23843.57ms] (UNSET)
        │             └─ 🤖 Model: us.anthropic.claude-3-7-sonnet-20250219-v1:0
        │             └─ 🎯 Tokens: in: 411, out: 117
        │             └─ 📋 Data (2 msg):
        │                 ⚙️ System: You are a helpful assistant. Use tools when appropriate.
        │                 👤 User: Create a text-based bar chart visualization...
```

**Key Observations**:
- POST span shows 2 events (instrumentation warning, completion message)
- invoke_agent shows 1 NEW event (not repeating parent's events)
- execute_event_loop_cycle shows 1 NEW event (not repeating grandparent's events)
- chat shows 1 NEW event
- Deepest chat span shows 2 messages (system + user) - these ONLY appear here, not repeated above

### Session Visualization

```bash
agentcore observability visualize-session \
  --session-id eb358f6f \
  --show-messages
```

Shows delta messages across all 12 traces in the session, with each span only displaying its unique data.

## Benefits

### 1. Intuitive Output
- **No Repetition**: Each message/event appears exactly once
- **Context Preserved**: Can still see the hierarchy and flow
- **Clean Display**: Easy to read and understand

### 2. Complete Visibility
- **Chat Messages**: See all system/user/assistant messages
- **Event Payloads**: See tracer events, log messages, and other operational data
- **API Metadata**: Model, tokens, request IDs, HTTP status
- **Timing**: Duration at each level

### 3. Efficient Display
- **Smart Truncation**: Long messages truncated to 200 chars
- **Key Fields Only**: Event payloads show most important fields
- **Hierarchical**: Delta approach shows data at the right level

### 4. Debugging Power
- **Trace Execution**: See exact sequence of operations
- **Data Flow**: See inputs/outputs at each level
- **Error Context**: See what data led to errors
- **Performance**: Token usage and timing at each step

## Usage

### Basic Usage
```bash
# Show single trace with delta messages and events
agentcore observability visualize-trace \
  --trace-id <trace-id> \
  --show-messages

# Show full session with delta messages and events
agentcore observability visualize-session \
  --session-id <session-id> \
  --show-messages

# Combine with details for maximum visibility
agentcore observability visualize-session \
  --session-id <session-id> \
  --show-messages \
  --details
```

### Output Components

#### Data Section Header
```
└─ 📋 Data (2 msg, 1 event):
```
- Shows count of messages vs events
- Only appears if there's NEW data at this span

#### Chat Messages
```
⚙️ System: You are a helpful assistant...
👤 User: Create a bar chart...
🤖 Assistant: I'll help you create...
```
- Role-based icons and colors
- Truncated to 200 characters
- Only NEW messages (not seen in parents)

#### Event Payloads
```
📦 Event: strands.telemetry.tracer
   output={'messages': [...]}, input={'messages': [...]}
```
- Event name shown
- Key payload fields extracted
- Formatted for readability

## Performance

### Query Optimization
- **1 Runtime Log Query**: Per trace/session (not per span)
- **Memory Grouping**: Messages grouped by span ID in memory
- **Set-Based Deduplication**: O(1) lookup for seen messages

### Test Results (Session eb358f6f)
- **Spans**: 320 spans across 12 traces
- **Runtime Logs**: ~100 logs queried once
- **Total Time**: ~5-7 seconds
- **Memory**: Efficient - seen_messages set grows linearly with unique messages

## Files Modified

### Core Models (`operations/observability/models/telemetry.py`)
- Enhanced `RuntimeLog.get_gen_ai_message()` to include type and event_name
- Added `RuntimeLog.get_event_payload()` to extract non-gen_ai events
- Updated `TraceData.get_messages_by_span()` to collect both messages and events

### Visualizer (`operations/observability/visualizers/trace_visualizer.py`)
- Updated `_add_span_to_tree()` to track seen_messages
- Added `_get_item_id()` for unique message/event identification
- Enhanced `_format_span()` to filter and display only delta items
- Added `_format_event_payload()` to format event payloads intelligently
- Updated display to show mixed message/event counts

### CLI Commands (`cli/observability/commands.py`)
- Queries runtime logs when `--show-messages` is enabled
- Passes runtime logs to TraceData
- Updated help text: "Show chat messages, LLM metadata, and API details"

## Advanced Features

### Message Types Supported
- **gen_ai.system.message**: System prompts
- **gen_ai.user.message**: User inputs
- **gen_ai.assistant.message**: Assistant responses
- **gen_ai.choice**: Alternative message format

### Event Types Supported
- **strands.telemetry.tracer**: Operation tracer events
- **Custom events**: Any event with event.name attribute
- **Log messages**: General log entries with body/message

### Payload Extraction
Intelligently extracts from:
- `body.content[]`: Array of content items
- `body.text`: Direct text field
- `body` (dict): Structured payload data
- `body` (string): Raw message

### Key Fields Extracted
Priority fields shown in event payloads:
1. `type`, `name`, `id`
2. `status`, `message`, `error`
3. `result`, `count`, `data`
4. First 3 fields if none of above present

## Testing

Tested with real production data:
- ✅ Single trace with 19 spans - delta messages work perfectly
- ✅ Session with 320 spans, 12 traces - no repetition across traces
- ✅ Event payloads extracted and displayed
- ✅ Mixed messages + events displayed correctly
- ✅ Performance: 5-7 seconds for full session
- ✅ Memory efficient: set-based deduplication

## Example Use Cases

### 1. Debugging Chat Issues
See exactly what system prompt and user message were sent to the LLM, along with token usage and timing.

### 2. Tracing Data Flow
See inputs and outputs at each operation level (tracer events) to understand data transformations.

### 3. Error Investigation
When a span fails, see what events and messages led up to the failure.

### 4. Performance Analysis
Token usage and timing combined with actual messages shows cost and latency drivers.

### 5. Conversation History
See the complete conversation without repetition - each message appears once at the appropriate level.

## Future Enhancements

1. **Full Message Display**: Option to show complete messages without truncation
2. **Payload Expansion**: Interactive expansion of truncated payloads
3. **Filter by Type**: Show only messages, only events, or both
4. **Export**: Export conversation history and event logs as JSON
5. **Search**: Search for keywords in messages/events
6. **Statistics**: Token usage summary, event counts, etc.
