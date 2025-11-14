# Evaluation Export Feature

## Summary

Added export functionality for evaluation results and intermediate input data (the OTel spans/log events sent to the API).

## Changes Made

### 1. Model Updates (`models/evaluation.py`)

Added `input_data` field to `EvaluationResults` to store the OpenTelemetry spans sent to the evaluation API:

```python
@dataclass
class EvaluationResults:
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    results: List[EvaluationResult] = field(default_factory=list)
    input_data: Optional[Dict[str, Any]] = None  # Store OTel spans sent to API
```

The `input_data` structure:
- For session-scoped evaluators: `{"session_scoped": [...spans...], "trace_scoped": None}`
- For trace-scoped evaluators: `{"session_scoped": None, "trace_scoped": [...spans...]}`
- For mixed evaluators: Both fields populated
- For `--all-traces`: `{"session_scoped": [...], "trace_scoped": [{"trace_id": "...", "spans": [...]}, ...]}`

### 2. Client Updates (`client.py`)

Updated `evaluate_session()` and `evaluate_all_traces()` methods to:
1. Track all input data sent to API in `all_input_data` dict
2. Store session-scoped spans when calling session-scoped evaluators
3. Store trace-scoped spans when calling trace-scoped evaluators
4. Set `results.input_data` before returning

### 3. CLI Updates (`cli/evaluation/commands.py`)

Updated `_save_evaluation_results()` to:
1. Extract `input_data` from results dict
2. Save results (without input_data) to the main output file
3. Save input_data to separate file: `{filename}_input.json`

Example:
```bash
agentcore eval run --session-id abc123 --output results.json
```

Creates two files:
- `results.json` - Evaluation results
- `results_input.json` - OTel spans sent to API

### 4. Explicit Scope Logging

Both methods now clearly log what's being evaluated:

**Session-scoped evaluators:**
```
Session-scoped evaluators: Builtin.GoalSuccessRate
Collecting most recent 100 relevant items across all 5 traces
Sending 100 items (45 spans [30 with gen_ai attrs], 55 log events) for session-scoped evaluation
```

**Trace-scoped evaluators:**
```
Trace-scoped evaluators: Builtin.Helpfulness, Builtin.Accuracy
Evaluating latest trace only (out of 5 traces)
Sending 23 items (15 spans [8 with gen_ai attrs], 8 log events) to evaluation API
```

## Usage Examples

### Basic Usage (Results Only)
```bash
# Display results in terminal
agentcore eval run --session-id abc123 -e Builtin.Helpfulness
```

### Export Results and Input Data
```bash
# Save results and input data to files
agentcore eval run --session-id abc123 -e Builtin.Helpfulness --output eval_results.json

# Creates:
# - eval_results.json (evaluation results)
# - eval_results_input.json (OTel spans sent to API)
```

### Session-Scoped Evaluation
```bash
# GoalSuccessRate requires data from all traces
agentcore eval run --session-id abc123 -e Builtin.GoalSuccessRate --output results.json

# Input data will contain:
# {"session_scoped": [...100 most recent items...], "trace_scoped": null}
```

### All Traces Evaluation
```bash
# Evaluate each trace separately
agentcore eval run --session-id abc123 --all-traces -e Builtin.Helpfulness --output results.json

# Input data will contain:
# {"session_scoped": null, "trace_scoped": [
#   {"trace_id": "trace-1", "spans": [...]},
#   {"trace_id": "trace-2", "spans": [...]},
#   ...
# ]}
```

### Mixed Evaluators
```bash
# Both session-scoped and trace-scoped evaluators
agentcore eval run --session-id abc123 \
  -e Builtin.GoalSuccessRate \
  -e Builtin.Helpfulness \
  --output results.json

# Input data will contain both:
# {
#   "session_scoped": [...100 most recent items...],
#   "trace_scoped": [...latest trace items...]
# }
```

## Testing

All tests pass (41/41):
```bash
python -m pytest tests/operations/evaluation/ -v
```

## Benefits

1. **Debugging**: Can inspect exact data sent to evaluation API
2. **Reproducibility**: Can replay evaluations with same input
3. **Transparency**: Clear visibility into what evaluator received
4. **Audit Trail**: Track evaluation inputs over time
5. **Analysis**: Analyze what data patterns lead to specific scores
