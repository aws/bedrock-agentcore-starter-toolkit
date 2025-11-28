# Integration Tests

This directory contains end-to-end integration tests for the evaluation functionality.

## Test Files

### Comprehensive Workflow Tests

#### `test_eval_workflow.py`
**Python/Notebook API Integration Test**

Tests the complete developer workflow using the Python notebook API:
1. List evaluators (builtin and custom)
2. Create a new custom evaluator
3. Run evaluation with builtin evaluator (`Builtin.GoalSuccessRate`)
4. Run evaluation with custom evaluator
5. Export results to JSON (including input data)
6. Get evaluator details and export to JSON
7. Update custom evaluator description
8. Duplicate custom evaluator
9. Delete custom evaluators (cleanup)

**Usage:**
```bash
# Set environment variables (optional)
export TEST_AGENT_ID="your-agent-id"
export TEST_SESSION_ID="your-session-id"
export TEST_REGION="us-east-1"

# Run test
python tests_integ/test_eval_workflow.py
```

**Output:** Test artifacts saved to `/tmp/eval_test_output/`

---

#### `test_eval_cli_workflow.sh`
**CLI Integration Test**

Tests the same workflow using the CLI commands:
1. `agentcore eval evaluator list` - List all evaluators
2. `agentcore eval evaluator create` - Create custom evaluator from JSON config
3. `agentcore eval run` - Run with builtin evaluator + export
4. `agentcore eval run` - Run with custom evaluator + export
5. `agentcore eval evaluator get` - Get details + export
6. `agentcore eval evaluator update` - Update description
7. `agentcore eval evaluator delete` - Delete evaluator

**Usage:**
```bash
# Set environment variables (optional)
export TEST_AGENT_ID="your-agent-id"
export TEST_SESSION_ID="your-session-id"
export TEST_REGION="us-east-1"

# Run test
./tests_integ/test_eval_cli_workflow.sh
```

**Output:** Test artifacts saved to `/tmp/eval_cli_test_output/`

---

### Legacy Tests

#### `test_eval_complete.py`
Original comprehensive test covering scope-based filtering and basic CRUD operations.

#### `test_eval_cli_simple.sh`
Simple CLI test verifying basic evaluation works.

#### `test_eval_cli.sh`
Another CLI test variant.

---

## What's Tested

### Core Functionality
- ✅ List evaluators (builtin and custom)
- ✅ Create custom evaluators with full config
- ✅ Run evaluations with builtin evaluators
- ✅ Run evaluations with custom evaluators
- ✅ Get evaluator details
- ✅ Update evaluator metadata
- ✅ Duplicate evaluators
- ✅ Delete evaluators

### Export Functionality
- ✅ Export evaluation results to JSON
- ✅ Export input data (spans) to separate JSON file
- ✅ Export evaluator details to JSON
- ✅ Verify exported JSON structure

### Code Architecture
- ✅ Shared business logic (`evaluator_operations` module)
- ✅ Shared display logic (`formatters` module)
- ✅ Consistent behavior between CLI and Python API
- ✅ Proper error handling

---

## Running All Tests

```bash
# Run comprehensive workflow tests
python tests_integ/test_eval_workflow.py
./tests_integ/test_eval_cli_workflow.sh

# Run legacy tests
python tests_integ/test_eval_complete.py
./tests_integ/test_eval_cli_simple.sh
```

---

## Requirements

- AWS credentials configured
- Access to Bedrock AgentCore
- Valid agent with session data
- Permissions to create/delete custom evaluators

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_AGENT_ID` | Agent ID for testing | `agent_lg-EVQuBO6Q0n` |
| `TEST_SESSION_ID` | Session ID with trace data | `383c4a9d-5682-4186-a125-e226f9f6c141` |
| `TEST_REGION` | AWS region | `us-east-1` |

---

## Test Output

Both comprehensive tests create detailed output directories with:
- Evaluation results (JSON)
- Input data / spans (JSON)
- Evaluator details (JSON)
- Evaluator configs (JSON)
- Command outputs (text logs)

Use these artifacts for debugging or verification.
