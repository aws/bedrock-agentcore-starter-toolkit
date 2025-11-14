# Trace-Scoped Evaluation Filtering

## Overview

Applied consistent filtering to trace-scoped evaluations to match the filtering already used for session-scoped evaluations. This improves signal-to-noise ratio and reduces unnecessary data sent to the evaluation API.

## Issue

When evaluating traces with `--all-traces`, trace-scoped evaluations were sending ALL spans and logs, including infrastructure spans without `gen_ai.*` attributes. This created inconsistency:

**Before:**
- **Session-scoped** (GoalSuccessRate): Sent 56 items (32 gen_ai spans + 24 conversation logs)
- **Trace 1** (Helpfulness): Sent 93 items (75 spans + 18 logs) - includes 51 infrastructure spans
- **Trace 2** (Helpfulness): Sent 38 items (32 spans + 6 logs) - includes 24 infrastructure spans

This was confusing because trace-scoped evaluations were sending MORE data than session-scoped, even though they covered less scope.

## Solution

Applied the same filtering logic to trace-scoped evaluations:

### Filter Criteria (now consistent across all evaluations)

Only include:
1. **Spans with `gen_ai.*` attributes** - LLM calls, agent operations, tool invocations
2. **Log events with conversation data** - Messages with input/output fields

Exclude:
- Infrastructure spans (framework, networking, internal operations)
- Log events without conversation data

## Changes Made

### 1. Added Shared Filter Method

Created `_filter_relevant_items()` helper method (lines 67-95):
```python
def _filter_relevant_items(self, otel_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter to only high-signal items for evaluation.

    Keeps only:
    - Spans with gen_ai.* attributes (LLM calls, agent operations)
    - Log events with conversation data (input/output messages)
    """
```

### 2. Updated `_get_most_recent_session_spans()`

Refactored to use shared filter helper (line 125):
```python
# Before: Duplicated filtering logic
relevant_items = []
for item in all_otel_items:
    if 'spanId' in item and 'startTimeUnixNano' in item:
        has_genai = any(k.startswith('gen_ai') for k in item.get('attributes', {}).keys())
        if has_genai:
            relevant_items.append(item)
    # ... more code

# After: Use shared helper
relevant_items = self._filter_relevant_items(all_otel_items)
```

### 3. Updated `evaluate_session()` - Trace-Scoped Path

Added filtering for trace-scoped evaluations (lines 288-298):
```python
# Transform this trace to OTel format
otel_spans_unfiltered = transform_trace_data_to_otel(trace_data, latest_trace_only=True)

# NEW: Filter to relevant items
otel_spans = self._filter_relevant_items(otel_spans_unfiltered)

if not otel_spans:
    print("Warning: No relevant items found after filtering")
```

### 4. Updated `evaluate_all_traces()` - Each Trace

Added filtering for each trace in the loop (lines 468-479):
```python
# Transform this trace to OTel format
otel_spans_unfiltered = transform_trace_data_to_otel(
    trace_data,
    latest_trace_only=False,
    trace_id=tid
)

# NEW: Filter to relevant items
otel_spans = self._filter_relevant_items(otel_spans_unfiltered)

if not otel_spans:
    print(f"  Warning: No relevant items after filtering for trace {tid}, skipping")
    continue
```

## Expected Behavior After Changes

**After:**
- **Session-scoped** (GoalSuccessRate): Sends 56 items (32 gen_ai spans + 24 conversation logs)
- **Trace 1** (Helpfulness): Sends ~42 items (24 gen_ai spans + 18 logs) - infrastructure filtered out
- **Trace 2** (Helpfulness): Sends ~14 items (8 gen_ai spans + 6 logs) - infrastructure filtered out

### Example Output

```bash
agentcore eval run -e Builtin.GoalSuccessRate -e Builtin.Helpfulness --all-traces

Found 107 spans across 2 traces in session

Session-scoped evaluators: Builtin.GoalSuccessRate
Collecting most recent 100 relevant items across all 2 traces
Sending 56 items (32 spans [32 with gen_ai attrs], 24 log events)

Trace-scoped evaluators: Builtin.Helpfulness
Evaluating all 2 traces with trace-scoped evaluators

Evaluating trace 1/2: 6908319a0f2bf81a28558f1b1bdd1f14
  Sending 42 items (24 spans [24 with gen_ai attrs], 18 log events)

Evaluating trace 2/2: 6908317d61d2d1686f5c671b46c0e8ce
  Sending 14 items (8 spans [8 with gen_ai attrs], 6 log events)

Completed evaluation of 2 traces
```

## Benefits

### 1. Consistency
Both session-scoped and trace-scoped evaluations now use identical filtering logic.

### 2. Better Signal-to-Noise
Evaluators receive only relevant data:
- LLM interactions (gen_ai spans)
- Conversation messages (input/output logs)

### 3. Reduced Payload Size
Smaller payloads sent to evaluation API:
- Faster API calls
- Lower costs
- Less risk of hitting 100-item limit per trace

### 4. Clearer Metrics
All span counts now represent gen_ai spans, making metrics more meaningful:
- "24 spans with gen_ai attrs" out of "24 spans total" = 100% relevant

### 5. Better Error Handling
Added warning for traces with no relevant items:
```
Warning: No relevant items after filtering for trace xyz, skipping
```

## Testing

All 41 tests pass:
```bash
pytest tests/operations/evaluation/ -v
# 41 passed in 0.47s
```

No test changes required because:
- Filtering logic extracted to helper method (DRY principle)
- Existing session-scoped tests already validated filtering behavior
- Trace-scoped tests work with filtered data (they include gen_ai attributes)

## Technical Details

### Filtering Logic

**Spans:**
```python
if 'spanId' in item and 'startTimeUnixNano' in item:
    has_genai = any(k.startswith('gen_ai') for k in item.get('attributes', {}).keys())
    if has_genai:
        relevant_items.append(item)
```

**Log Events:**
```python
if 'body' in item and 'timeUnixNano' in item:
    body = item.get('body', {})
    if isinstance(body, dict) and ("input" in body or "output" in body):
        relevant_items.append(item)
```

### gen_ai.* Attributes

These OpenTelemetry attributes indicate AI/ML operations:
- `gen_ai.operation.name` - Operation type (e.g., "invoke_agent", "call_tool")
- `gen_ai.request.model` - Model used
- `gen_ai.usage.input_tokens` - Token counts
- `gen_ai.response.finish_reason` - Completion reason
- And more...

## Backward Compatibility

✅ **Fully backward compatible**

- No API changes
- No configuration changes
- No changes to output format
- Exported data structure unchanged (just contains filtered items)

## Files Modified

1. `src/bedrock_agentcore_starter_toolkit/operations/evaluation/client.py`
   - Added `_filter_relevant_items()` method (lines 67-95)
   - Updated `_get_most_recent_session_spans()` to use helper (line 125)
   - Updated `evaluate_session()` trace-scoped path (lines 288-311)
   - Updated `evaluate_all_traces()` trace loop (lines 468-496)

## Documentation Updates Needed

Consider updating:
- `docs/GETTING_STARTED_EVALUATION.md` - Explain filtering behavior
- `SESSION_SCOPED_FIX.md` - Note that filtering now applies to both modes

## Future Enhancements

1. **Configurable Filtering**
   ```python
   agentcore eval run --filter-mode [full|high-signal|minimal]
   ```

2. **Filter Statistics**
   ```
   Filtered 107 items → 42 relevant items (60% reduction)
   - Removed 51 infrastructure spans
   - Removed 14 logs without conversation data
   ```

3. **Custom Filter Rules**
   ```yaml
   evaluation:
     filtering:
       required_attributes: ["gen_ai.*"]
       include_infrastructure: false
       min_conversation_logs: true
   ```

## Conclusion

This change makes trace-scoped evaluations consistent with session-scoped evaluations by applying the same filtering logic. Users now get:
- Consistent behavior across evaluation modes
- Better signal-to-noise ratio
- Smaller payloads to evaluation API
- Clearer metrics (all reported spans have gen_ai attributes)

The filtering is transparent to users and requires no configuration changes.
