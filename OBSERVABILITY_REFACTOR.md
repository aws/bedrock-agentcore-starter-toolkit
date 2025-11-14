# Observability Refactoring

## Overview

Refactored the evaluation feature into a proper observability module that can be used independently, with intuitive trace visualization capabilities.

## Architecture Changes

### New Structure

```
operations/
├── observability/          # NEW: Independent observability module
│   ├── __init__.py
│   ├── client.py          # ObservabilityClient (CloudWatch integration)
│   ├── query_builder.py   # CloudWatch query builders
│   ├── models/
│   │   ├── __init__.py
│   │   └── telemetry.py   # Span, RuntimeLog, TraceData models
│   └── visualizers/
│       ├── __init__.py
│       └── trace_visualizer.py  # Hierarchical trace visualization
│
├── evaluation/            # Evaluation leverages observability
│   ├── __init__.py
│   ├── evaluator.py       # Mock evaluator (future integration)
│   └── models/
│       └── evaluation.py  # Evaluation-specific models

cli/
├── observability/         # NEW: Observability CLI commands
│   ├── __init__.py
│   └── commands.py        # visualize-trace, visualize-session
│
└── evaluation/
    └── commands.py        # Existing evaluation commands
```

## Key Features

### 1. Independent Observability Module

The observability module is now completely independent and can be used by:
- Evaluation feature
- Other monitoring tools
- Debugging workflows
- Performance analysis

**Usage:**
```python
from bedrock_agentcore_starter_toolkit.operations.observability import (
    ObservabilityClient,
    TraceVisualizer,
    TraceData
)

# Query spans and traces
client = ObservabilityClient(region_name="us-east-1", agent_id="test-EPMVTFAk5W")
spans = client.query_spans_by_session(session_id, start_time, end_time)

# Visualize traces
trace_data = TraceData(spans=spans)
trace_data.group_spans_by_trace()

visualizer = TraceVisualizer()
visualizer.visualize_trace(trace_data, trace_id)
```

### 2. Hierarchical Trace Visualization

**TraceVisualizer** provides intuitive visualization of trace hierarchies:

#### Features:
- **Tree Structure**: Shows parent-child relationships clearly
- **Status Icons**:
  - ✓ (green) for OK spans
  - ❌ (red) for ERROR spans
  - ◦ (dim) for UNSET spans
- **Duration Colors**:
  - Green: < 100ms
  - Yellow: 100-1000ms
  - Orange: 1-5s
  - Red: > 5s
- **Detailed View**: Optional span IDs, service names, events
- **Summary View**: Table format showing all traces with stats

#### Example Output:

**Single Trace Visualization:**
```
🔍 Trace: 68f947ff49e0bf55... (19 spans, 126029.03ms)
└── ◦ POST /invocations [26279.52ms] (UNSET)
    ├── ◦ Bedrock AgentCore.ListEvents [90.84ms] (UNSET)
    ├── ◦ Bedrock AgentCore.CreateEvent [148.02ms] (UNSET)
    └── ✓ invoke_agent Strands Agents [25602.28ms] (OK)
        ├── ◦ Bedrock AgentCore.CreateEvent [185.98ms] (UNSET)
        ├── ✓ execute_event_loop_cycle [24348.86ms] (OK)
        │   └── ✓ chat [23846.06ms] (OK)
        │       └── ◦ chat us.anthropic.claude-3-7-sonnet [23843.57ms] (UNSET)
        └── ◦ Bedrock AgentCore.CreateEvent [232.33ms] (UNSET)
```

**Error Trace Visualization:**
```
🔍 Trace: 68f94d7c1eefa377... (14 spans, 75623.84ms, 4 errors)
├── ❌ POST /invocations [19553.59ms] (ERROR)
│   └── ❌ invoke_agent Strands Agents [19054.30ms] (ERROR)
│       ├── ◦ Bedrock AgentCore.CreateEvent [180.29ms] (UNSET)
│       └── ◦ Bedrock AgentCore.CreateEvent [159.86ms] (UNSET)
└── ❌ chat [17769.72ms] (ERROR)
    └── ❌ chat us.anthropic.claude-3-7-sonnet [17766.21ms] (ERROR)
```

**Session Summary:**
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Trace ID            ┃ Spans ┃ Duration (ms) ┃ Errors ┃ Status   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ 68f947ff49e0bf55... │    19 │     126029.03 │      - │ ✓ OK     │
│ 68f94d7c1eefa377... │    14 │      75623.84 │      4 │ ❌ ERROR │
│ 68f961a9245cace9... │    30 │     112901.09 │      - │ ✓ OK     │
└─────────────────────┴───────┴───────────────┴────────┴──────────┘
```

### 3. Span Hierarchy Building

**TraceData Model** now includes:
- `build_span_hierarchy(trace_id)`: Builds parent-child relationships
- `group_spans_by_trace()`: Groups spans by trace with sorting
- `children` field on Span: List of child spans

This enables:
- Recursive tree traversal
- Root span identification
- Understanding execution flow
- Error propagation visualization

## CLI Commands

### Observability Commands

```bash
# Visualize a single trace with hierarchy
agentcore observability visualize-trace \
  --trace-id 68f947ff49e0bf5530a9e79e492f5930 \
  --agent-id test-EPMVTFAk5W \
  --region us-east-1

# With detailed information (span IDs, services, events)
agentcore observability visualize-trace \
  --trace-id 68f947ff \
  --details

# Visualize all traces in a session (tree view)
agentcore observability visualize-session \
  --session-id eb358f6f-fc68-47ed-b09a-669abfaf4469 \
  --agent-id test-EPMVTFAk5W \
  --region us-east-1

# Session summary (table view)
agentcore observability visualize-session \
  --session-id eb358f6f \
  --summary
```

### Evaluation Commands (Unchanged)

```bash
agentcore evaluation query-spans --session-id <ID>
agentcore evaluation query-session --session-id <ID>
agentcore evaluation session-summary --session-id <ID>
```

## Benefits

### 1. **Separation of Concerns**
- Observability: Query and visualize telemetry data
- Evaluation: Analyze and score agent performance

### 2. **Reusability**
- Other features can use observability module independently
- No coupling to evaluation logic

### 3. **Intuitive Visualization**
- Hierarchical tree view shows execution flow clearly
- Color-coded status and durations
- Easy error identification with ❌ icons
- Parent-child relationships visible at a glance

### 4. **Debugging & Analysis**
- Quickly identify slow spans
- See error propagation paths
- Understand execution order
- Trace LLM calls and tool executions

### 5. **Production-Ready**
- Tested with real CloudWatch data
- 320 spans across 12 traces
- Handles complex agent workflows
- Performance: ~3-35 seconds for query + visualization

## Real-World Example

**Session: eb358f6f-fc68-47ed-b09a-669abfaf4469**
- **Agent**: test-EPMVTFAk5W
- **Spans**: 320 spans
- **Traces**: 12 distinct traces
- **Duration**: ~22 minutes total
- **Errors**: 4 errors in 1 trace
- **Success Rate**: 98.75%

**Trace Insights:**
- Root span: `POST /invocations` (26.3s)
  - Agent execution: `invoke_agent` (25.6s)
    - Event loop: `execute_event_loop_cycle` (24.3s)
      - LLM call: `chat` (23.8s)
        - Claude 3.7 Sonnet invocation (23.8s)

**Error Trace:**
- Trace 68f94d7c had 4 errors
- Root cause: Claude API call failed
- Error propagated through: chat → invoke_agent → POST endpoint

## Migration Guide

### For Developers Using the Module

**Before:**
```python
from bedrock_agentcore_starter_toolkit.operations.evaluation import (
    EvaluationClient, SessionData
)

client = EvaluationClient(...)
session_data = client.get_session_data(...)
```

**After (Observability):**
```python
from bedrock_agentcore_starter_toolkit.operations.observability import (
    ObservabilityClient, TraceData, TraceVisualizer
)

# Query data
client = ObservabilityClient(...)
trace_data = client.get_session_data(...)  # Returns TraceData

# Visualize
visualizer = TraceVisualizer()
visualizer.visualize_all_traces(trace_data)
```

**After (Evaluation):**
```python
from bedrock_agentcore_starter_toolkit.operations.observability import (
    ObservabilityClient
)
from bedrock_agentcore_starter_toolkit.operations.evaluation import (
    EvaluatorClient
)

# Get telemetry data
obs_client = ObservabilityClient(...)
trace_data = obs_client.get_session_data(...)

# Evaluate
eval_client = EvaluatorClient(...)
results = eval_client.evaluate_session(trace_data)
```

## Files Created

```
src/bedrock_agentcore_starter_toolkit/
├── operations/observability/
│   ├── __init__.py
│   ├── client.py
│   ├── query_builder.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── telemetry.py
│   └── visualizers/
│       ├── __init__.py
│       └── trace_visualizer.py
└── cli/observability/
    ├── __init__.py
    └── commands.py
```

## Backwards Compatibility

- `SessionData` aliased to `TraceData` for compatibility
- Existing evaluation commands unchanged
- EvaluationClient still works (but internally uses observability models)

## Testing

All features tested with production CloudWatch data:
- ✅ Trace visualization with 19 spans
- ✅ Error trace visualization (4 errors)
- ✅ Session summary (12 traces, 320 spans)
- ✅ Hierarchical tree rendering
- ✅ Parent-child relationships
- ✅ Details mode with span IDs

## Future Enhancements

1. **Export capabilities**: Save visualizations as JSON/HTML
2. **Filtering**: Filter spans by duration, status, service
3. **Search**: Find spans by attributes
4. **Comparison**: Compare traces side-by-side
5. **Real-time**: Stream spans as they arrive
6. **Flamegraphs**: Alternative visualization for performance analysis
7. **Integration**: Export to Jaeger/Zipkin format

## Conclusion

The observability module is now:
- ✅ **Independent**: Can be used by any feature
- ✅ **Intuitive**: Hierarchical trees show execution flow clearly
- ✅ **Production-ready**: Tested with real CloudWatch data
- ✅ **Feature-rich**: Detailed views, summaries, error highlighting
- ✅ **Extensible**: Easy to add new visualizations and exports
