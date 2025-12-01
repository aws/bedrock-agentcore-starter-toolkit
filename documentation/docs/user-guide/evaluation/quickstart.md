# Evaluation Quickstart: Evaluate Your Agent! 🎯

This tutorial shows you how to use the Amazon Bedrock AgentCore starter toolkit CLI to evaluate your deployed agent's performance. You'll learn how to run on-demand evaluations and set up continuous monitoring with online evaluation.

The evaluation CLI provides commands to assess agent quality using built-in evaluators (like helpfulness and goal success) or create custom evaluators for your specific needs.

**📚 For comprehensive details, see the [AgentCore Evaluation Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html)**

## Prerequisites

Before you start, make sure you have:

- **Deployed Agent with Observability**: This quickstart assumes you already have an agent deployed with observability enabled and at least one completed session. If you don't have this set up yet:
  - Deploy an agent: Follow the [AgentCore Runtime Getting Started Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-getting-started.html)
  - Enable observability: Follow the [AgentCore Observability Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
  - Run at least one agent interaction to generate session data
- **AWS Credentials Configured**: See [Configuration and credential file settings in the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).
- **Python 3.10+** installed

## Step 1: Install the Toolkit

Install the AgentCore starter toolkit:

```bash
pip install bedrock-agentcore-starter-toolkit
```

Verify installation:

```bash
agentcore eval --help
```

**Success:** You should see the evaluation command options.

## Step 2: List Available Evaluators

View all available built-in and custom evaluators:

```bash
agentcore eval evaluator list
```

**Success:** You should see a table of evaluators:

```
Built-in Evaluators (13)

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ ID                            ┃ Name           ┃ Level      ┃ Description    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Builtin.GoalSuccessRate       │ Builtin.GoalS… │ SESSION    │ Task           │
│                               │                │            │ Completion     │
│                               │                │            │ Metric.        │
│                               │                │            │ Evaluates      │
│                               │                │            │ whether the    │
│                               │                │            │ conversation   │
│                               │                │            │ successfully   │
│                               │                │            │ meets the      │
│                               │                │            │ user's goals   │
│ Builtin.Helpfulness           │ Builtin.Helpf… │ TRACE      │ Response       │
│                               │                │            │ Quality        │
│                               │                │            │ Metric.        │
│                               │                │            │ Evaluates from │
│                               │                │            │ user's         │
│                               │                │            │ perspective    │
│                               │                │            │ how useful and │
│                               │                │            │ valuable the   │
│                               │                │            │ agent's        │
│                               │                │            │ response is    │
│ Builtin.Correctness           │ Builtin.Corre… │ TRACE      │ Response       │
│                               │                │            │ Quality        │
│                               │                │            │ Metric.        │
│                               │                │            │ Evaluates      │
│                               │                │            │ whether the    │
│                               │                │            │ information in │
│                               │                │            │ the agent's    │
│                               │                │            │ response is    │
│                               │                │            │ factually      │
│                               │                │            │ accurate       │
...

Total: 13 builtin evaluators
```

**Understanding Evaluator Levels:**
- **SESSION**: Evaluates entire conversation (e.g., goal completion)
- **TRACE**: Evaluates individual responses (e.g., helpfulness, correctness)
- **TOOL_CALL**: Evaluates tool selection and parameters

## Step 3: Run Your First Evaluation

Run an on-demand evaluation on your agent:

```bash
agentcore eval run --evaluator "Builtin.Helpfulness"
```

This automatically uses the agent ID and session ID from your `.bedrock_agentcore.yaml` configuration file.

> **Note:** You'll see "Using session from config: <session-id>" confirming that the session ID was loaded from your configuration file.

**Success:** You should see evaluation results:

```
Using session from config: 383c4a9d-5682-4186-a125-e226f9f6c141

Evaluating session: 383c4a9d-5682-4186-a125-e226f9f6c141
Mode: All traces (most recent 1000 spans)
Evaluators: Builtin.Helpfulness

╭──────────────────────────────────────────────────────────────────────────────╮
│ Evaluation Results                                                           │
│ Session: 383c4a9d-5682-4186-a125-e226f9f6c141                                │
╰──────────────────────────────────────────────────────────────────────────────╯

✓ Successful Evaluations

╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  Evaluator: Builtin.Helpfulness                                              │
│                                                                              │
│  Score: 0.83                                                                 │
│  Label: Very Helpful                                                         │
│                                                                              │
│  Explanation:                                                                │
│  The assistant's response effectively addresses the user's request by        │
│  providing comprehensive analysis...                                         │
│                                                                              │
│  Token Usage:                                                                │
│    - Input: 927                                                              │
│    - Output: 233                                                             │
│    - Total: 1,160                                                            │
│                                                                              │
│  Evaluated:                                                                  │
│    - Session: 383c4a9d-5682-4186-a125-e226f9f6c141                           │
│    - Trace: 6929ecf956ccc60c19c9a548698ae116                                 │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Multiple Evaluators

Evaluate with multiple evaluators simultaneously:

```bash
agentcore eval run \
  --evaluator "Builtin.Helpfulness" \
  --evaluator "Builtin.GoalSuccessRate" \
  --evaluator "Builtin.Correctness"
```

### Save Results

Export evaluation results to JSON:

```bash
agentcore eval run \
  --evaluator "Builtin.Helpfulness" \
  --output results.json
```

This creates two files:
- `results.json` - Evaluation scores and explanations
- `results_input.json` - Input data used for evaluation

## Step 4: Set Up Continuous Monitoring

Enable automatic evaluation of live agent traffic with online evaluation:

```bash
agentcore eval online create \
  --name production_eval_config \
  --sampling-rate 1.0 \
  --evaluator "Builtin.GoalSuccessRate" \
  --evaluator "Builtin.Helpfulness" \
  --description "Production evaluation for my agent"
```

> Note: The agent ID is automatically detected from your `.bedrock_agentcore.yaml` configuration file. To explicitly specify an agent, add `--agent-id <your-agent-id>`.

**Parameters:**
- `--sampling-rate`: Percentage of interactions to evaluate (0.01-100). Start with 1-5% for production.
- `--evaluator`: Evaluator IDs (specify multiple times)

**Success:** You should see:

```
Creating online evaluation config: production_eval_config
Agent ID: agent_lg-EVQuBO6Q0n
Region: us-east-1
Sampling Rate: 1.0%
Evaluators: ['Builtin.GoalSuccessRate', 'Builtin.Helpfulness']
Endpoint: DEFAULT

✓ Online evaluation config created successfully!

Config ID: production_eval_config-2HeyEjChSQ
Config Name: production_eval_config
Status: CREATING
Execution Role: arn:aws:iam::730335462089:role/AgentCoreEvalsSDK-us-east-1-4b7eba641e
Output Log Group: /aws/bedrock-agentcore/evaluations/results/production_eval_config-2HeyEjChSQ
```

**Notes:**
- If an IAM execution role doesn't exist, it will be auto-created
- The config starts in `CREATING` status and transitions to `ACTIVE` within a few seconds
- **Save the Config ID** - you'll need it to manage this configuration

## Step 5: Monitor Evaluation Results

### View Your Configurations

List all online evaluation configurations:

```bash
agentcore eval online list
```

You should see a table showing your configurations:

```
Found 2 online evaluation config(s)

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Config Name      ┃ Config ID        ┃ Status ┃ Execution ┃ Created           ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ production_eval… │ production_eval… │ ACTIVE │ ENABLED   │ 2025-11-28        │
│                  │                  │        │           │ 10:47:56.055000-… │
└──────────────────┴──────────────────┴────────┴───────────┴───────────────────┘
```

### Get Configuration Details

View details about a specific configuration:

```bash
agentcore eval online get --config-id production_eval_config-2HeyEjChSQ
```

You should see detailed configuration information:

```
Config Name: production_eval_config
Config ID: production_eval_config-2HeyEjChSQ
Status: ACTIVE
Execution Status: ENABLED
Sampling Rate: 1.0%
Evaluators: Builtin.GoalSuccessRate, Builtin.Helpfulness
Execution Role: arn:aws:iam::730335462089:role/AgentCoreEvalsSDK-us-east-1-4b7eba641e

Output Log Group: /aws/bedrock-agentcore/evaluations/results/production_eval_config-2HeyEjChSQ

Description: Production evaluation for my agent
```

> Replace `production_eval_config-2HeyEjChSQ` with your configuration ID from Step 4.

### View Results in CloudWatch

1. Open the [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. Navigate to **GenAI Observability** → **Bedrock AgentCore**
3. Select your agent and endpoint
4. View the **Evaluations** tab for detailed results

## Alternative: Without Configuration File

If you don't have a `.bedrock_agentcore.yaml` configuration file (or want to evaluate a different agent/session), you can explicitly specify the agent ID and session ID:

### Run Evaluation

```bash
agentcore eval run \
  --agent-id agent_myagent-ABC123xyz \
  --session-id 550e8400-e29b-41d4-a716-446655440000 \
  --evaluator "Builtin.Helpfulness"
```

> Replace `agent_myagent-ABC123xyz` with your agent ID and `550e8400-e29b-41d4-a716-446655440000` with your session ID.

### Create Online Evaluation

```bash
agentcore eval online create \
  --name production_eval_config \
  --agent-id agent_myagent-ABC123xyz \
  --sampling-rate 1.0 \
  --evaluator "Builtin.GoalSuccessRate" \
  --evaluator "Builtin.Helpfulness"
```

This approach is useful when:
- You deployed your agent outside of AgentCore Runtime
- You want to evaluate a specific session (not the latest)
- You're evaluating multiple agents and need to switch between them

## Next Steps

### Create Custom Evaluators

Create domain-specific evaluators for your use case. First, create a configuration file `evaluator-config.json`:

```json
{
  "llmAsAJudge": {
    "modelConfig": {
      "bedrockEvaluatorModelConfig": {
        "modelId": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "inferenceConfig": {
          "maxTokens": 500,
          "temperature": 1.0
        }
      }
    },
    "ratingScale": {
      "numerical": [
        {
          "value": 0.0,
          "label": "Poor",
          "definition": "Response is unhelpful or incorrect"
        },
        {
          "value": 0.5,
          "label": "Adequate",
          "definition": "Response is partially helpful"
        },
        {
          "value": 1.0,
          "label": "Excellent",
          "definition": "Response is highly helpful and accurate"
        }
      ]
    },
    "instructions": "Evaluate the assistant's response for helpfulness and accuracy. Context: {context}. Target to evaluate: {assistant_turn}"
  }
}
```

Then create the evaluator:

```bash
agentcore eval evaluator create \
  --name "my_custom_evaluator" \
  --config evaluator-config.json \
  --level TRACE \
  --description "Custom evaluator for my use case"
```

### Update Online Evaluation Configuration

Modify existing online evaluation configurations to adjust sampling rates, evaluators, or status:

```bash
# Change sampling rate
agentcore eval online update \
  --config-id production_eval_config-2HeyEjChSQ \
  --sampling-rate 5.0

# Disable temporarily
agentcore eval online update \
  --config-id production_eval_config-2HeyEjChSQ \
  --status DISABLED

# Update evaluators
agentcore eval online update \
  --config-id production_eval_config-2HeyEjChSQ \
  --evaluator "Builtin.Correctness" \
  --evaluator "Builtin.Faithfulness"
```

> Replace `production_eval_config-2HeyEjChSQ` with your configuration ID from Step 4.

## Troubleshooting

### "No agent specified" or Agent ID not found

**Problem**: Agent ID cannot be loaded from configuration file.

**Solution**: You can specify the agent ID explicitly:

```bash
# Find your agent ID from deployment
agentcore status

# Or specify it directly
agentcore eval run \
  --agent-id agent_myagent-ABC123xyz \
  --evaluator "Builtin.Helpfulness"
```

For online evaluation:
```bash
agentcore eval online create \
  --name my_eval_config \
  --agent-id agent_myagent-ABC123xyz \
  --evaluator "Builtin.Helpfulness"
```

### "No session ID provided"

**Problem**: Session ID cannot be loaded from configuration file.

**Solution**: Find and specify a session ID explicitly:

```bash
# List recent sessions using observability
agentcore obs list

# This will show output like:
# Session ID: 550e8400-e29b-41d4-a716-446655440000
# Trace Count: 5
# Start Time: 2024-11-28 10:30:00

# Use a session ID from the list
agentcore eval run \
  --session-id 550e8400-e29b-41d4-a716-446655440000 \
  --evaluator "Builtin.Helpfulness"
```

### "No spans found for session"

**Problem**: The session ID exists in config but no observability data is available.

**Common Causes**:
- Session is older than 7 days (default lookback period)
- Session hasn't completed yet
- Observability was not enabled when the session ran
- **CloudWatch logs haven't populated yet** (2-5 minute delay after agent invocation)

> **Note**: By default, the CLI looks back 7 days for session data. If your session is older, use `--days` to extend the lookback period (observability data is retained for up to 30 days).

**Solution**: Run a new agent interaction to generate fresh session data:

```bash
# Step 1: Invoke your agent to create a new session
agentcore invoke --input "Tell me about AWS"

# Step 2: Wait 2-5 minutes for CloudWatch logs to populate
# CloudWatch ingestion has a delay before logs become available

# Step 3: Run evaluation after waiting
agentcore eval run --evaluator "Builtin.Helpfulness"
```

**Important**: There is typically a **2-5 minute delay** between invoking your agent and when the observability data becomes available in CloudWatch for evaluation. If you get "No spans found", wait a few minutes and try again.

**For older sessions (8-30 days old)**, extend the lookback period:

```bash
# Evaluate a session from 14 days ago
agentcore eval run \
  --evaluator "Builtin.Helpfulness" \
  --days 14

# Or with explicit session ID
agentcore eval run \
  --session-id <your-old-session-id> \
  --evaluator "Builtin.Helpfulness" \
  --days 30
```

Verify an older session exists before evaluating:
```bash
agentcore obs list --session-id <your-session-id> --days 30
```

### "ValidationException: config name must match pattern"

**Solution**: Use underscores instead of hyphens in configuration names (e.g., `my_config` not `my-config`).
