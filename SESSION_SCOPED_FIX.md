# Session-Scoped Evaluator Fix

## Issue

When using `--all-traces` with session-scoped evaluators like `Builtin.GoalSuccessRate`, the evaluator was incorrectly being run once per trace instead of once per session.

## Root Cause

In the `evaluate_all_traces()` method, the loop that iterates through traces was using `evaluators` (all evaluators) instead of `trace_scoped` (only trace-scoped evaluators):

```python
# BEFORE (INCORRECT)
for i, tid in enumerate(trace_ids, 1):
    # ... transform trace ...

    for evaluator in evaluators:  # ❌ Wrong! Includes session-scoped evaluators
        response = self.evaluate(otel_spans, [evaluator])
```

This caused session-scoped evaluators to:
1. Run multiple times (once per trace) instead of once per session
2. Use single-trace data instead of all session data
3. Produce incorrect results

## Fix

Changed the loop to only iterate over trace-scoped evaluators:

```python
# AFTER (CORRECT)
for i, tid in enumerate(trace_ids, 1):
    # ... transform trace ...

    for evaluator in trace_scoped:  # ✅ Correct! Only trace-scoped evaluators
        response = self.evaluate(otel_spans, [evaluator])
```

Also wrapped the entire trace loop in the `if trace_scoped:` block to avoid unnecessary work when only session-scoped evaluators are specified.

## Behavior After Fix

### With `--all-traces` and Mixed Evaluators

```bash
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.GoalSuccessRate \
  -e Builtin.Helpfulness
```

**Output:**
```
Found 45 spans across 3 traces in session

Session-scoped evaluators: Builtin.GoalSuccessRate
Collecting most recent 100 relevant items across all 3 traces
Sending 100 items (52 spans [35 with gen_ai attrs], 48 log events)
✓ GoalSuccessRate: 1.00

Trace-scoped evaluators: Builtin.Helpfulness
Evaluating all 3 traces with trace-scoped evaluators

Evaluating trace 1/3: trace-abc123
  Sending 15 items...
  ✓ Helpfulness: 0.83

Evaluating trace 2/3: trace-def456
  Sending 18 items...
  ✓ Helpfulness: 0.91

Evaluating trace 3/3: trace-xyz789
  Sending 12 items...
  ✓ Helpfulness: 0.75

Completed evaluation of 3 traces
```

### With `--all-traces` and Only Session-Scoped

```bash
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.GoalSuccessRate
```

**Output:**
```
Found 45 spans across 3 traces in session

Session-scoped evaluators: Builtin.GoalSuccessRate
Collecting most recent 100 relevant items across all 3 traces
Sending 100 items (52 spans [35 with gen_ai attrs], 48 log events)
✓ GoalSuccessRate: 1.00
```

**Note:** No trace loop runs since there are no trace-scoped evaluators.

## Key Principles

### Session-Scoped Evaluators
- **Always** use data from ALL traces in session
- **Always** run only ONCE per session
- **Never** affected by `--trace-id` or `--all-traces` flags
- Examples: `Builtin.GoalSuccessRate`

### Trace-Scoped Evaluators
- Use data from a single trace
- Run once per trace with `--all-traces`
- Run once for latest/specific trace by default
- Examples: `Builtin.Helpfulness`, `Builtin.Accuracy`

## Code Changes

### File: `src/bedrock_agentcore_starter_toolkit/operations/evaluation/client.py`

**Lines 434-495:** Updated `evaluate_all_traces()` method

**Key Changes:**
1. Line 470: Changed `for evaluator in evaluators:` to `for evaluator in trace_scoped:`
2. Line 441: Added comment clarifying trace loop only runs for trace-scoped evaluators
3. Line 468: Added comment explaining session-scoped evaluators already ran
4. Line 495: Moved completion message inside `if trace_scoped:` block

## Testing

All tests pass:
```bash
pytest tests/operations/evaluation/ -v
# 41 passed in 0.43s
```

## Documentation Updates

Updated documentation to clarify behavior:

### File: `docs/GETTING_STARTED_EVALUATION.md`

**Section: Builtin.GoalSuccessRate**
- Added "Important" note explaining it always uses all session data
- Clarified behavior with different flags

**Section: Mode 3 (All Traces)**
- Added note that session-scoped evaluators still run once
- Updated example output to show separation of evaluator types

## Impact

### Before Fix
- ❌ Session-scoped evaluators ran incorrectly with `--all-traces`
- ❌ GoalSuccessRate produced wrong results (evaluated per-trace instead of per-session)
- ❌ Wasted API calls (running session evaluator multiple times)
- ❌ Confusing output (no clear separation of evaluator types)

### After Fix
- ✅ Session-scoped evaluators always run once with all data
- ✅ GoalSuccessRate produces correct results
- ✅ Optimal API usage (one call for session, one per trace for trace evaluators)
- ✅ Clear output showing evaluator separation

## Examples

### Example 1: Session-Scoped Only

```bash
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.GoalSuccessRate
```

**Behavior:**
- Collects most recent 100 items across all 3 traces
- Runs GoalSuccessRate once
- Does NOT iterate through individual traces
- Returns 1 result

### Example 2: Trace-Scoped Only

```bash
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.Helpfulness
```

**Behavior:**
- Does NOT run session-scoped collection
- Iterates through all 3 traces
- Runs Helpfulness for each trace
- Returns 3 results (one per trace)

### Example 3: Mixed Evaluators

```bash
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.GoalSuccessRate \
  -e Builtin.Helpfulness
```

**Behavior:**
1. Runs GoalSuccessRate once with all session data (1 API call)
2. Iterates through all 3 traces
3. Runs Helpfulness for each trace (3 API calls)
4. Returns 4 results (1 session + 3 trace)

## Verification

To verify the fix is working:

```bash
# Test 1: Session-scoped only - should run once
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.GoalSuccessRate

# Expected: Single evaluation, no trace loop

# Test 2: Mixed evaluators - should separate clearly
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.GoalSuccessRate \
  -e Builtin.Helpfulness

# Expected:
# - "Session-scoped evaluators: Builtin.GoalSuccessRate"
# - One session evaluation
# - "Trace-scoped evaluators: Builtin.Helpfulness"
# - Multiple trace evaluations

# Test 3: Trace-scoped only - should skip session collection
agentcore eval run --session-id abc123 --all-traces \
  -e Builtin.Helpfulness

# Expected: Only trace loop, no session collection
```

## Future Considerations

1. **Dynamic Evaluator Scope Detection**
   - Currently hardcoded in `SESSION_SCOPED_EVALUATORS` set
   - TODO: Query control plane API to determine evaluator scope dynamically

2. **Explicit User Communication**
   - Consider adding flag like `--session-scope-only` for clarity
   - Or warning when `--trace-id` is used with session-scoped evaluator

3. **Result Grouping**
   - Consider grouping results by scope in output
   - Separate session results from trace results visually

## Related Issues

- User requested: "since the goal success rate is session scoped always run it session scoped even if --all traces is specified"
- Root cause: Loop variable using wrong list
- Impact: Incorrect evaluation results, wasted API calls

## Conclusion

The fix ensures that session-scoped evaluators like `Builtin.GoalSuccessRate` always:
1. Use data from ALL traces in the session
2. Run only ONCE per session
3. Produce correct results regardless of evaluation mode flags

This maintains the semantic meaning of "session-scoped" and provides predictable, correct behavior.
