# Evaluation Config Fix

## Issues

### Issue 1: Missing ObservabilityClient Parameters

When running `agentcore eval run` without explicit CLI arguments, the command failed with:

```
TypeError: ObservabilityClient.__init__() missing 2 required positional arguments: 'region_name' and 'agent_id'
```

**Root Cause**: The `evaluate_session()` method was initializing `ObservabilityClient` without required parameters.

### Issue 2: Missing get_session_data Parameters

After fixing Issue 1, a second error occurred:

```
TypeError: ObservabilityClient.get_session_data() missing 1 required positional argument: 'end_time_ms'
```

**Root Cause**: The call to `get_session_data()` was missing required time range parameters (`start_time_ms` and `end_time_ms`).

## Fixes Applied

### 1. Updated `EvaluationClient.evaluate_session()` Method

**File**: `src/bedrock_agentcore_starter_toolkit/operations/evaluation/client.py`

#### Fix 1a: Required Parameters

Changed method signature to require `agent_id` and `region`:

```python
def evaluate_session(
    self,
    session_id: str,
    evaluators: List[str],
    agent_id: str,        # ✅ Now required
    region: str           # ✅ Now required
) -> EvaluationResults:
```

#### Fix 1b: ObservabilityClient Initialization

```python
obs_client = ObservabilityClient(
    region_name=region,
    agent_id=agent_id,
    runtime_suffix="DEFAULT"
)
```

#### Fix 1c: Time Range for get_session_data

Added default 7-day time range (matching observability CLI pattern):

```python
from datetime import datetime, timedelta

# Get default time range (last 7 days)
end_time = datetime.now()
start_time = end_time - timedelta(days=7)
start_time_ms = int(start_time.timestamp() * 1000)
end_time_ms = int(end_time.timestamp() * 1000)

trace_data = obs_client.get_session_data(
    session_id=session_id,
    start_time_ms=start_time_ms,      # ✅ Required parameter
    end_time_ms=end_time_ms,          # ✅ Required parameter
    include_runtime_logs=True
)
```

### 2. Updated CLI Command to Extract Config Values

**File**: `src/bedrock_agentcore_starter_toolkit/cli/evaluation/commands.py`

Added logic to extract `agent_id` and `region` from config file (same pattern as observability CLI):

```python
# Get session ID, agent_id, and region from config if not provided
config = _get_agent_config_from_file(agent_name)

# Extract session_id
if not session_id:
    if config and config.get("session_id"):
        session_id = config["session_id"]
    else:
        # Error handling

# Extract agent_id
if not agent_id:
    if config and config.get("agent_id"):
        agent_id = config["agent_id"]
    else:
        # Error handling

# Extract region
if not region:
    if config and config.get("region"):
        region = config["region"]
    else:
        # Error handling
```

Pass all parameters to evaluate_session:

```python
results = eval_client.evaluate_session(
    session_id=session_id,
    evaluators=evaluator_list,
    agent_id=agent_id,      # ✅ Passed from config
    region=region           # ✅ Passed from config
)
```

### 3. Updated Tests

**File**: `tests/operations/evaluation/test_client.py`

Added comprehensive test for session evaluation:

```python
@patch("bedrock_agentcore_starter_toolkit.operations.evaluation.client.ObservabilityClient")
def test_evaluate_session_success(self, mock_obs_client_class):
    """Test successful session evaluation."""

    # Verifies ObservabilityClient is created with correct params
    mock_obs_client_class.assert_called_once_with(
        region_name="us-west-2",
        agent_id="agent-456",
        runtime_suffix="DEFAULT"
    )

    # Verifies get_session_data is called with time range
    assert call_args.kwargs["session_id"] == "session-123"
    assert "start_time_ms" in call_args.kwargs
    assert "end_time_ms" in call_args.kwargs
    assert call_args.kwargs["include_runtime_logs"] is True
```

## Test Results

```bash
$ uv run pytest tests/operations/evaluation/ -v

============================== 41 passed in 0.51s ===============================
```

- ✅ Added 1 new test for session evaluation
- ✅ All 41 tests passing (100% pass rate)
- ✅ No regressions

## Usage

Now works correctly with config file:

```bash
# Uses session_id, agent_id, and region from .bedrock_agentcore.yaml
agentcore eval run

# Or override with CLI arguments
agentcore eval run --session-id <id> --agent-id <id> --region us-west-2
```

Config file format (`.bedrock_agentcore.yaml`):

```yaml
agents:
  default:
    bedrock_agentcore:
      agent_id: "your-agent-id"
      agent_session_id: "your-session-id"
    aws:
      region: "us-west-2"
```

## Summary

The fixes ensure that:
1. ✅ **ObservabilityClient initialization** - Correctly passes `region_name`, `agent_id`, and `runtime_suffix`
2. ✅ **Time range parameters** - Provides default 7-day window for `get_session_data()`
3. ✅ **Config extraction** - Extracts `session_id`, `agent_id`, and `region` from `.bedrock_agentcore.yaml`
4. ✅ **CLI argument override** - All parameters can be overridden via CLI flags
5. ✅ **Clear error messages** - User-friendly errors if required values are missing
6. ✅ **All tests passing** - 41/41 tests (100% pass rate)
7. ✅ **Consistent pattern** - Follows same approach as observability CLI

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| `evaluate_session()` params | `session_id`, `evaluators`, `agent_id?` | `session_id`, `evaluators`, `agent_id`, `region` |
| ObservabilityClient init | `ObservabilityClient()` ❌ | `ObservabilityClient(region_name, agent_id, runtime_suffix)` ✅ |
| `get_session_data()` call | `(session_id, agent_id)` ❌ | `(session_id, start_time_ms, end_time_ms, include_runtime_logs)` ✅ |
| Time range | Not provided ❌ | Last 7 days (default) ✅ |
| CLI config extraction | Only `session_id` | `session_id`, `agent_id`, `region` ✅ |

The evaluation feature now works correctly when using config file values! 🚀
