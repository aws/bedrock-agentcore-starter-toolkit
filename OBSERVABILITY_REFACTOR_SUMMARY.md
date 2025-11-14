# Observability Refactor Summary

## Overview
This document summarizes the refactoring and improvements made to the observability module to fix critical issues, simplify code, and improve robustness across different LLM frameworks.

## Issues Fixed

### 1. Incorrect Trace Duration Calculation ✓
**Problem**: Trace header showed cumulative duration (sum of all spans including nested) instead of actual trace duration.
- **Before**: 42891.70ms (incorrect - summing nested spans)
- **After**: 7664ms (correct - earliest start to latest end)

**Solution**: Created `TraceData.calculate_trace_duration()` static method to calculate actual duration from earliest start timestamp to latest end timestamp, with fallback to root span durations.

### 2. Missing Messages in Output ✓
**Problem**: Runtime logs were queried (17 logs found) but messages weren't displayed.
- **Root Cause**: Runtime logs were only fetched conditionally based on flags
- **Solution**: Always fetch runtime logs when displaying traces, with verbose flag controlling truncation only

### 3. Tool Use Not Displayed ✓
**Problem**: Tool use blocks, tool results, and tool definitions from runtime logs weren't being extracted or displayed.
- **Solution**: Implemented comprehensive tool extraction supporting:
  - Tool use blocks with inputs (🔧 icon)
  - Tool results with content (🔧 icon)
  - Tool definitions in system messages (🛠️ icon)
  - Both camelCase (`toolUse`, `toolResult`) and snake_case (`tool_use`, `tool_result`)

### 4. Tool Content Truncated in Verbose Mode ✓
**Problem**: Tool inputs/outputs were truncated even with `--verbose` flag.
- **Solution**: Changed truncation check from `startswith("🔧")` to `"🔧" in content` to preserve all tool-related content

### 5. Tool Results Showing as User Messages ✓
**Problem**: Tool results were showing as "User:" messages instead of proper tool format.
- **Solution**: Added priority-based role determination where tool results override event-based role

### 6. System Messages Missing Tool Definitions ✓
**Problem**: System messages with tool definitions didn't show available tools.
- **Solution**: Added extraction of `tools` array from message body with formatted display

### 7. Brittle Message Extraction Logic ✓
**Problem**: Logic was fragile and wouldn't work reliably across different models/frameworks.
- **Solution**: Refactored into systematic helper methods with better defaults and fallbacks

## Code Simplifications

### 1. Simplified `get_messages_by_span()` - 36% reduction
**Before**: 67 lines with repetitive dictionary checks
**After**: 43 lines using `or` operator and `setdefault()`

```python
# Before: Repetitive pattern
exception = log.get_exception()
if exception:
    if log.span_id not in items_by_span:
        items_by_span[log.span_id] = []
    items_by_span[log.span_id].append(exception)
    continue

# After: Concise pattern
item = log.get_exception() or log.get_gen_ai_message() or log.get_event_payload()
if item:
    items_by_span.setdefault(log.span_id, []).append(item)
```

**Benefits**:
- Eliminated duplicate dictionary initialization code
- Priority-based extraction is clear and explicit
- Easier to maintain and extend

### 2. Extracted Trace Duration Calculation
**Before**: Duplicate duration calculation logic in 2 files (22 lines total)
**After**: Single `TraceData.calculate_trace_duration()` method (22 lines, used in 2 places)

```python
# Before: Duplicated in trace_visualizer.py and telemetry.py
start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]
if start_times and end_times:
    total_duration = (max(end_times) - min(start_times)) / 1_000_000
else:
    root_spans = [s for s in spans if not s.parent_span_id]
    total_duration = sum(s.duration_ms or 0 for s in root_spans)

# After: Reusable method
total_duration = TraceData.calculate_trace_duration(spans)
```

**Benefits**:
- Single source of truth for duration calculation
- Consistent behavior across codebase
- Easier to test and maintain

### 3. Refactored Message Extraction into Helper Methods
Extracted `get_gen_ai_message()` into focused helper methods:

```python
# Helper methods (new):
_get_nested_value()        # Try multiple key variations (camelCase, snake_case)
_extract_content_parts()   # Extract text, tool_use, tool_result, tools
_build_content_string()    # Format extracted parts for display
_determine_role()          # Context-aware role determination

# Main method now just orchestrates:
def get_gen_ai_message(self):
    attributes = self.raw_message.get("attributes", {})
    event_name = attributes.get("event.name", "")

    if not event_name.startswith("gen_ai."):
        return None

    body = self.raw_message.get("body", {})
    parts = self._extract_content_parts(body)

    if not any(parts.values()):
        return None

    content = self._build_content_string(parts)
    role = self._determine_role(event_name, parts)

    return {
        "type": "message",
        "role": role,
        "content": content,
        "timestamp": self.timestamp,
        "event_name": event_name,
    }
```

**Benefits**:
- Clear separation of concerns
- Each method has single responsibility
- Easier to test individual components
- More robust error handling

## Framework Compatibility

The refactored code now supports multiple naming conventions:

| Feature | AWS/Bedrock | Standard | Type Field |
|---------|-------------|----------|------------|
| Tool use | `toolUse` | `tool_use` | `type: "tool_use"` |
| Tool result | `toolResult` | `tool_result` | `type: "tool_result"` |
| Tool ID | `toolUseId` | `tool_use_id` | `id` |

## Test Results

### Test Coverage
```
Total Tests: 174 (171 original + 3 new)
Pass Rate: 100%
Coverage: 77%
```

### New Tests Added
1. `test_calculate_trace_duration_with_timestamps` - Tests duration from timestamps
2. `test_calculate_trace_duration_fallback_to_durations` - Tests fallback to span durations
3. `test_calculate_trace_duration_multiple_root_spans` - Tests multiple root spans

### Coverage by Module
| Module | Coverage | Status |
|--------|----------|--------|
| query_builder.py | 100% | ✓ Excellent |
| client.py | 82% | ✓ Good |
| telemetry.py | 80% | ✓ Good |
| commands.py | 79% | ✓ Good |
| trace_visualizer.py | 66% | ⚠️ Needs improvement |

### Test Execution
```bash
# Run all observability tests
uv run pytest tests/operations/observability/ tests/cli/observability/ -v

# Results
174 passed in 0.76s
```

## Files Modified

### Core Logic
1. **`src/bedrock_agentcore_starter_toolkit/operations/observability/models/telemetry.py`**
   - Added `_get_nested_value()` helper for flexible key lookup
   - Refactored `get_gen_ai_message()` into focused helpers
   - Added `calculate_trace_duration()` static method
   - Simplified `get_messages_by_span()` (36% reduction)
   - Enhanced tool use/result extraction

2. **`src/bedrock_agentcore_starter_toolkit/operations/observability/visualizers/trace_visualizer.py`**
   - Updated `_format_trace_header()` to use `calculate_trace_duration()`
   - Fixed truncation logic for tool content
   - Added tool role display formatting

3. **`src/bedrock_agentcore_starter_toolkit/cli/observability/commands.py`**
   - Changed `_show_trace_view()` to always fetch runtime logs
   - Changed `_show_last_trace_from_session()` to always fetch runtime logs
   - Updated `_show_session_view()` to fetch logs for trace display

### Tests
4. **`tests/operations/observability/test_telemetry.py`**
   - Added `TestTraceDataHelperMethods` class with 3 new tests
   - Existing tests continue to pass

5. **`tests/operations/observability/test_trace_visualizer.py`**
   - Updated test to verify full span ID display
   - All tests continue to pass

## Command Examples

The refactored CLI now properly displays all messages and tool interactions:

```bash
# Show specific trace with all details
agentcore obs show --trace-id 690156557a198c640accf1ab0fae04dd

# Show latest trace from session with full details (no truncation)
agentcore obs show --session-id eb358f6f --verbose

# Show all traces in session
agentcore obs show --session-id eb358f6f --all

# List all traces in session with input/output preview
agentcore obs list --session-id eb358f6f

# Export trace to JSON
agentcore obs show --trace-id 690156557a198c... -o trace.json
```

## Debug Mode

Added environment variable for troubleshooting:

```bash
# Enable debug output
export BEDROCK_AGENTCORE_DEBUG=1
agentcore obs show --session-id <session-id>

# Output includes:
# - Number of runtime logs processed
# - Event name for each log
# - Extraction results (message/event/exception)
# - Total items extracted per span
```

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Issues Fixed** | 7 major issues |
| **Code Reduction** | 24 lines removed |
| **Test Coverage** | 77% overall |
| **Tests Added** | 3 new tests |
| **Tests Passing** | 174/174 (100%) |
| **Framework Support** | Multiple (AWS, Standard, Type-based) |

## Key Improvements

1. ✅ **Correctness**: Fixed trace duration calculation
2. ✅ **Completeness**: All messages, tool use, and exceptions now displayed
3. ✅ **Simplicity**: 36% reduction in `get_messages_by_span()`
4. ✅ **Robustness**: Works across different LLM frameworks
5. ✅ **Maintainability**: Clear separation of concerns with helper methods
6. ✅ **Testability**: 100% test pass rate with comprehensive coverage
7. ✅ **Debuggability**: Added debug mode for troubleshooting

## Next Steps (Optional)

To reach 90%+ coverage:
1. Add CLI integration tests for actual command execution
2. Add tests for edge cases in trace_visualizer.py
3. Add tests for error handling paths in commands.py
4. Add tests for runtime log scenarios with complex nested structures
