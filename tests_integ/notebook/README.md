# Evaluation Integration Test Notebook

## Overview

The `evaluation_test_clean.ipynb` notebook provides comprehensive integration tests for the Evaluation API. It tests all major features including listing evaluators, running evaluations, creating custom evaluators, and exporting results.

## Setup

### Prerequisites

1. AWS credentials configured with access to:
   - Bedrock AgentCore Evaluation API
   - CloudWatch Logs (for session data)

2. An active agent with recent sessions (within last 7 days) for auto-fetch to work

### Quick Start

1. **Open the notebook** in Jupyter, VS Code, or JupyterLab

2. **Run Cell 1** to verify correct package loading:
   - Adds local `src` directory to Python path
   - Imports from local evaluation toolkit (not installed package)
   - Verifies `get_latest_session()` method exists

3. **Configure Cell 2** with your values:
   ```python
   TEST_AGENT_ID = "your-agent-id"        # Required
   TEST_SESSION_ID = "your-session-id"    # Or None for auto-fetch
   TEST_REGION = "us-east-1"              # Your AWS region
   ```

4. **Run the remaining cells** sequentially to execute all tests

## Configuration Options

### Option 1: Explicit Session ID (Recommended)

```python
TEST_AGENT_ID = "agent_lg-EVQuBO6Q0n"
TEST_SESSION_ID = "cc8a8e69-8bed-4e5f-9a06-9a58550fd713"  # Your actual session ID
TEST_REGION = "us-east-1"
```

**Pros:**
- Always works regardless of CloudWatch data availability
- Faster (no query needed)
- Predictable results

**Use when:**
- You know the specific session you want to evaluate
- Testing with older sessions (>7 days)

### Option 2: Auto-fetch Latest Session

```python
TEST_AGENT_ID = "agent_lg-EVQuBO6Q0n"
TEST_SESSION_ID = None  # Auto-fetch latest
TEST_REGION = "us-east-1"
```

**Pros:**
- Convenient for testing with most recent sessions
- No need to manually find session IDs

**Cons:**
- Requires agent to have sessions in last 7 days
- Depends on CloudWatch Logs availability
- May fail if no sessions found

**Use when:**
- Testing with latest agent interactions
- You don't know specific session IDs

## Tests Included

The notebook includes 10 comprehensive tests:

1. **Initialize Evaluation Client** - Create client with agent ID and region
2. **List Evaluators** - Fetch all available evaluators (builtin and custom)
3. **Get Evaluator Details** - Retrieve configuration for a specific evaluator
4. **Run Evaluation** - Execute evaluation with auto-fetch or explicit session
5. **Multiple Evaluators** - Run evaluation with multiple evaluators at once
6. **Export Results** - Save evaluation results to JSON file
7. **Create Custom Evaluator** - Define a custom LLM-as-judge evaluator
8. **Run Custom Evaluator** - Execute evaluation with custom evaluator
9. **Update Custom Evaluator** - Modify evaluator description
10. **Delete Custom Evaluator** - Clean up test evaluator

## Troubleshooting

### "ValueError: No session_id provided and could not fetch latest session"

**Cause:** Auto-fetch failed to find any sessions in the last 7 days.

**Solutions:**
1. Provide an explicit session ID instead:
   ```python
   TEST_SESSION_ID = "your-actual-session-id"
   ```

2. Check if agent has recent sessions (last 7 days)

3. Run the test script to diagnose:
   ```bash
   cd tests_integ
   python test_auto_fetch_session.py
   ```

4. Check the debug output for specific errors in the notebook output

### "Wrong package! Not using bedrock-agentcore-starter-toolkit-evaluation"

**Cause:** Notebook is importing from installed package instead of local source.

**Solution:** The first cell should fix this automatically. If not:
1. Restart the kernel
2. Run Cell 1 first before any other cells
3. Verify the output shows the local path

### Auto-fetch returns None

**Possible causes:**
- Agent has no sessions in last 7 days
- CloudWatch Logs not accessible
- Agent ID incorrect
- Region mismatch

**Debug steps:**
1. Check recent debug output from `get_latest_session()`
2. Verify agent ID is correct
3. Confirm AWS credentials have CloudWatch Logs read access
4. Try with explicit session ID to isolate the issue

## Auto-fetch Implementation Details

The auto-fetch feature:

1. **Queries CloudWatch Logs** for spans from the last 7 days
2. **Filters by agent ID** to get only relevant sessions
3. **Groups spans by session** and tracks timestamps
4. **Returns most recent session** based on latest activity

**Location:**
- Business logic: `src/bedrock_agentcore_starter_toolkit/operations/evaluation/processor.py:40`
- Client interface: `src/bedrock_agentcore_starter_toolkit/notebook/evaluation/client.py:107`

**Parameters:**
- Lookback window: 7 days (configurable via `DEFAULT_LOOKBACK_DAYS`)
- Query uses `ObservabilityClient.query_spans_by_agent()`

## Additional Resources

- **SETUP_KERNEL.md** - Instructions for configuring Jupyter kernel with local venv
- **test_auto_fetch_session.py** - Standalone test script for debugging auto-fetch
- **API Documentation** - See docstrings in `client.py` for full API reference

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run `test_auto_fetch_session.py` for diagnostic information
3. Review debug output in notebook cells
4. Verify AWS credentials and permissions
