# AgentCore Quickstart

## Introduction

Build and deploy a production-ready AI agent in minutes with runtime hosting, memory, secure code execution, and observability. This guide shows how to use [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html), [Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html), [Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html), and [Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html).

For Gateway and Identity features, see the [Gateway quickstart](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/gateway/quickstart.md) and [Identity quickstart](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/identity/quickstart.md).

## Prerequisites

- **AWS Permissions**: Root users or privileged roles (such as admins) can skip this step. Others need to attach the [starter toolkit policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit) and [AmazonBedrockAgentCoreFullAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html) managed policy.
- [AWS CLI version 2.0 or later](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configured (`aws configure`)
- **Amazon Bedrock model access enabled for Claude 3.7 Sonnet** (Go to AWS Console → Bedrock → Model access → Enable “Claude 3.7 Sonnet” in your region). For information about using a different model with Strands Agents, see the Model Providers section in the [Strands Agents SDK](https://strandsagents.com/latest/documentation/docs/) documentation.
- Python 3.10 or newer

> **Important: Ensure AWS Region Consistency**
>
> Ensure the following are all configured to use the **same AWS region**:
>
> - Your `aws configure` default region
> - The region where you’ve enabled Bedrock model access
> - All resources created during deployment will use this region

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages (version 0.1.21 or later)
pip install "bedrock-agentcore-starter-toolkit>=0.1.21" strands-agents boto3
```

## Step 1: Create the Agent

Create `agentcore_starter_strands.py`:

```python
"""
Strands Agent sample with AgentCore
"""
import os
from strands import Agent, tool
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

ci_sessions = {}
current_session = None

@tool
def calculate(code: str) -> str:
    """Execute Python code for calculations or analysis."""
    session_id = current_session or 'default'

    if session_id not in ci_sessions:
        ci_sessions[session_id] = {
            'client': CodeInterpreter(REGION),
            'session_id': None
        }

    ci = ci_sessions[session_id]
    if not ci['session_id']:
        ci['session_id'] = ci['client'].start(
            name=f"session_{session_id[:30]}",
            session_timeout_seconds=1800
        )

    result = ci['client'].invoke("executeCode", {
        "code": code,
        "language": "python"
    })

    for event in result.get("stream", []):
        if stdout := event.get("result", {}).get("structuredContent", {}).get("stdout"):
            return stdout
    return "Executed"

@app.entrypoint
def invoke(payload, context):
    global current_session

    if not MEMORY_ID:
        return {"error": "Memory not configured"}

    actor_id = context.headers.get('X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id', 'user') if hasattr(context, 'headers') else 'user'

    session_id = getattr(context, 'session_id', 'default')
    current_session = session_id

    memory_config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={
            f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
            f"/users/{actor_id}/preferences": RetrievalConfig(top_k=3, relevance_score=0.5)
        }
    )

    agent = Agent(
        model=MODEL_ID,
        session_manager=AgentCoreMemorySessionManager(memory_config, REGION),
        system_prompt="You are a helpful assistant. Use tools when appropriate.",
        tools=[calculate]
    )

    result = agent(payload.get("prompt", ""))
    return {"response": result.message.get('content', [{}])[0].get('text', str(result))}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:

```text
strands-agents
bedrock-agentcore
```

## Step 2: Configure and Deploy

The AgentCore CLI automates deployment with provisioning.

### Configure the Agent

You’ll be prompted for the following during configuration:

1. **Execution Role**: For this tutorial, Press Enter to auto-create a new role with all required permissions.
1. **ECR Repository**: Press Enter to auto-create a new repository, or provide an existing ECR URI
1. **Requirements File**: Confirm the detected requirements.txt file or specify a different path
1. **OAuth Configuration**: Type `no` for this tutorial (OAuth is not required)
1. **Request Header Allowlist**: Type `no` for this tutorial (headers are not required)
1. **Memory Configuration**:

- If existing memories are found, choose from the list or press Enter to create a new one
- If creating new memory, type `yes` when asked to enable long-term memory extraction
- Note: Short-term memory is always enabled by default


Now run the configuration command:

```bash
agentcore configure -e agentcore_starter_strands.py
```

**Note**: If the memory configuration prompts do not appear during `agentcore configure`, refer to the [Troubleshooting](#troubleshooting) section (Memory Configuration Not Appearing) to ensure the correct toolkit version is installed.

### Deploy to AgentCore

Run the deployment command to build your container, push it to ECR, and create the AgentCore Runtime with Memory and observability enabled:

```bash
agentcore launch
```

The deployment performs memory resource provisioning with short-term and long-term strategies, Docker container build with dependencies, ECR repository push, AgentCore Runtime deployment with X-Ray tracing enabled, CloudWatch Transaction Search configuration, and endpoint activation with trace collection.

After successful deployment, you'll see the Memory ID, Agent ARN, and GenAI Observability Dashboard URL in the output—these indicate your deployment completed successfully.

**If deployment encounters errors or behaves unexpectedly**, check your configuration and verify resource provisioning status:

```bash
cat .bedrock_agentcore.yaml
```

```bash
agentcore status
```

Refer to the [Troubleshooting](#troubleshooting) section if you see any issues.

## Step 3: Monitor Deployment

Check the deployment status to verify that your Memory resources are provisioned and your agent runtime is ready. The status command shows your Memory ID, current provisioning status, memory type configuration, and observability settings. Run this command periodically until the Memory status shows as active.

```bash
agentcore status
```

**Note**: Long-term memory strategies require 2-5 minutes to activate. Short-term memory is provisioned immediately if long-term memory is not selected. Wait until the Memory Type shows “STM+LTM (3 strategies)” before proceeding to testing.

## Step 4: Test Memory and Code Interpreter

### Test Short-Term Memory (STM)

Short-term memory allows the agent to maintain context within a single session.

Store information in the current session (session IDs must be 33+ characters):

```bash
agentcore invoke '{"prompt": "Remember that my favorite agent platform is AgentCore"}'
```

If you invoke too early while memory is still provisioning, you’ll see a message indicating the current status and suggesting you wait and check with `agentcore status`.

Retrieve the information within the same session:

```bash
agentcore invoke '{"prompt": "What is my favorite agent platform?"}'
```

Expected response: “Your favorite agent platform is AgentCore.”

### Test Long-Term Memory (LTM) - Cross-Session Persistence

Long-term memory enables information persistence across different sessions through background extraction of facts and preferences.

Store facts in the first session:

```bash
agentcore invoke '{"prompt": "My email is user@example.com and I am an AgentCore user"}'
```

Wait for extraction that runs in the background by AgentCore. This typically takes 10-30 seconds. If you do not see the facts retrieved in the next step, wait a few more seconds and try again.

```bash
sleep 20
```

Create a new session and retrieve the extracted facts:

```bash
SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
agentcore invoke '{"prompt": "Tell me about myself?"}' --session-id $SESSION_ID
```

Expected response: “Your email address is user@example.com.” and “You appear to be a user of AgentCore, which seems to be your favorite agent platform.”

### Test Code Interpreter

Store data for analysis:

```bash
agentcore invoke '{"prompt": "My dataset has values: 23, 45, 67, 89, 12, 34, 56."}'
```

Create a visualization:

```bash
agentcore invoke '{"prompt": "Create a text-based bar chart visualization showing the distribution of values in my dataset with proper labels"}'
```

Expected: The agent generates matplotlib code to create a bar chart visualization.

## Step 5: View Traces and Logs

### Access CloudWatch Dashboard

Navigate to the GenAI Observability dashboard to view end-to-end request traces including agent execution tracking, memory retrieval operations, code interpreter executions, agent reasoning steps, and latency breakdown by component. The dashboard provides a service map view showing agent runtime connections to Memory and Code Interpreter services with request flow visualization and latency metrics, as well as detailed X-Ray traces for debugging and performance analysis.

Get the dashboard URL from the status output:

```bash
agentcore status
```

Navigate to the URL shown in the output, or go directly to the CloudWatch GenAI Observability dashboard and replace the region with yours: `https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core`

### View Agent Runtime Logs

To view your agent’s runtime logs, use the log command shown in the status output. The status command displays the exact log path and AWS CLI command for your specific agent.

First, get your agent’s log information:

```bash
agentcore status
```

Copy the `aws logs tail` command from the status output and execute it. The command will look similar to this format but with your specific agent ID and current date:

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --follow
```

For recent logs without following live updates, use the `--since` option shown in the status output:

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --since 1h
```

**Note**: The `--follow` flag provides a live stream of logs as they occur. If you don’t see immediate output, that’s normal—logs will appear as your agent processes requests.

## Clean Up

Remove all deployed resources including the runtime endpoint, agent, memory resources, ECR repository and images, and auto-created IAM roles:

```bash
agentcore destroy
```

## Troubleshooting

<details>
<summary><strong>Memory Configuration Not Appearing</strong></summary>

**“Memory option not showing during `agentcore configure`”:**

This typically occurs when using an outdated version of the starter toolkit. Ensure you have version 0.1.21 or later installed:

```bash
# Step 1: Verify current state
which python   # Should show .venv/bin/python
which agentcore  # Currently showing global path

# Step 2: Deactivate and reactivate venv to reset PATH
deactivate
source .venv/bin/activate

# Step 3: Check if that fixed it
which agentcore
# If NOW showing .venv/bin/agentcore -> RESOLVED, skip to Step 7
# If STILL showing global path -> continue to Step 4

# Step 4: Force local venv to take precedence in PATH
export PATH="$(pwd)/.venv/bin:$PATH"

# Step 5: Check again
which agentcore
# If NOW showing .venv/bin/agentcore -> RESOLVED, skip to Step 7
# If STILL showing global path -> continue to Step 6

# Step 6: Reinstall in local venv with forced precedence
pip install --force-reinstall --no-cache-dir "bedrock-agentcore-starter-toolkit>=0.1.21"

# Step 7: Final verification
which agentcore  # Must show: /path/to/your-project/.venv/bin/agentcore
pip show bedrock-agentcore-starter-toolkit  # Verify version >= 0.1.21
agentcore --version  # Double check it's working

# Step 8: Try configure again
agentcore configure -e agentcore_starter_strands.py

#If Step 6 still doesn't work, the nuclear option:
cd ..
mkdir fresh-agentcore-project && cd fresh-agentcore-project
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir "bedrock-agentcore-starter-toolkit>=0.1.21" strands-agents boto3
# Copy your agent code here, then reconfigure
```

**Additional checks:**

- Ensure you’re running `agentcore configure` from within the activated virtual environment
- If using an IDE (VSCode, PyCharm), restart the IDE after reinstalling
- Verify no system-wide agentcore installation conflicts: `pip list | grep bedrock-agentcore`

</details>

<details>
<summary><strong>Region Misconfiguration</strong></summary>

**If you need to change your region configuration:**

Clean up resources in the incorrect region:

```bash
agentcore destroy
```

Verify your AWS CLI is configured for the correct region:

```bash
aws configure get region
```

Or reconfigure for the correct region:

```bash
aws configure set region <your-desired-region>
```

Ensure Bedrock model access is enabled in the target region through AWS Console → Bedrock → Model access.

Copy your agent code and requirements.txt to the new folder, then return to **Step 2: Configure and Deploy**.

</details>

<details>
<summary><strong>Memory Issues</strong></summary>

**“Memory status is not active” error:**

Run the status command to check memory status:

```bash
agentcore status
```

If showing “provisioning”, wait 2-3 minutes and retry after status shows “STM+LTM (3 strategies)”.

**Cross-session memory not working:**

Verify long-term memory is active (not “provisioning”) and wait 15-30 seconds after storing facts for extraction to complete. Check extraction logs for completion status.

</details>

<details>
<summary><strong>Observability Issues</strong></summary>

**No traces appearing:**

Verify observability was enabled during configuration, check that your IAM permissions include CloudWatch and X-Ray access, and wait 30-60 seconds for traces to appear in CloudWatch. Traces are viewable at AWS Console → CloudWatch → Service Map or X-Ray → Traces.

**Missing memory logs:**

Check that the log group exists at `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/<memory-id>` and verify your IAM role has CloudWatch Logs permissions.

</details>

-----

## Summary

You’ve deployed a production agent with:

- **Runtime** for managed container orchestration
- **Memory** with STM for immediate context and LTM for cross-session persistence
- **Code Interpreter** for secure Python execution with data visualization capabilities
- **AWS X-Ray Tracing** automatically configured for distributed tracing
- **CloudWatch Integration** for logs and metrics with Transaction Search enabled

All services are automatically instrumented with X-Ray tracing, providing complete visibility into agent behavior, memory operations, and tool executions through the CloudWatch dashboard.
