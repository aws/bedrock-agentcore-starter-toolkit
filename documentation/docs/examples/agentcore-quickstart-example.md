# AgentCore Quickstart

## Introduction

Build and deploy a production-ready AI agent in minutes with runtime hosting, memory, secure code execution, and observability. This guide shows how to use [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html), [Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html), [Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html), and [Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html).

For Gateway and Identity features, see the [Gateway quickstart](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/gateway/quickstart.md) and [Identity quickstart](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/identity/quickstart.md).

## Prerequisites

- **AWS Permissions**
  - **Root users or administrators**: Can skip this step
  - **Non-admin users (including SageMaker notebook users)**: Need comprehensive permissions beyond the [basic toolkit policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit). See the [Complete Non-Admin User Permissions](#complete-non-admin-user-permissions) section below for the full policy required.
- [AWS CLI version 2.0 or later](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configured (`aws configure`)
- **Amazon Bedrock model access enabled for Claude 3.7 Sonnet** (Go to AWS Console → Bedrock → Model access → Enable "Claude 3.7 Sonnet" in your region). For information about using a different model with Strands Agents, see the Model Providers section in the [Strands Agents SDK](https://strandsagents.com/latest/documentation/docs/) documentation.
- Python 3.10 or newer

> **Important: Ensure AWS Region Consistency**
>
> Ensure the following are all configured to use the **same AWS region**:
>
> - Your `aws configure` default region
> - The region where you've enabled Bedrock model access
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

```bash
agentcore configure -e agentcore_starter_strands.py

#Interactive prompts you'll see:

# 1. Execution Role: Press Enter to auto-create or provide existing role ARN/name
# 2. ECR Repository: Press Enter to auto-create or provide existing ECR URI
# 3. OAuth Configuration: Configure OAuth authorizer? (yes/no) - Type `no` for this tutorial
# 4. Request Header Allowlist: Configure request header allowlist? (yes/no) - Type `no` for this tutorial
# 5. Memory Configuration:
#    - If existing memories found: Choose from list or press Enter to create new
#    - If creating new: Enable long-term memory extraction? (yes/no) - Type `yes` for this tutorial
#    - Note: Short-term memory is always enabled by default
```
**For this tutorial**: When prompted for the execution role, press Enter to auto-create a new role with all required permissions for Runtime, Memory, Code Interpreter, and Observability.

**Note**: If the memory configuration prompts do not appear during `agentcore configure`, refer to the [Troubleshooting](#troubleshooting) section (Memory Configuration Not Appearing) to ensure the correct toolkit version is installed.


### Deploy to AgentCore

```bash
agentcore launch

# This performs:
#   1. Memory resource provisioning (STM + LTM strategies)
#   2. Docker container build with dependencies
#   3. ECR repository push
#   4. AgentCore Runtime deployment with X-Ray tracing enabled
#   5. CloudWatch Transaction Search configuration (automatic)
#   6. Endpoint activation with trace collection
```

**Expected output:**

```text
✅ Memory created: agentcore_starter_strands_mem-abc123
Observability is enabled, configuring Transaction Search...
✅ Transaction Search configured: resource_policy, trace_destination, indexing_rule
🔍 GenAI Observability Dashboard:
   https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
✅ Container deployed to Bedrock AgentCore
Agent ARN: arn:aws:bedrock-agentcore:us-west-2:123456789:runtime/agentcore_starter_strands-xyz
```

**If deployment encounters errors or behaves unexpectedly**, check your configuration:
```bash
cat .bedrock_agentcore.yaml  # Review deployed configuration
agentcore status              # Verify resource provisioning status
```
Refer to the [Troubleshooting](#troubleshooting) section if you see any issues.

## Step 3: Monitor Deployment

Check deployment status:

```bash
agentcore status

# Shows:
#   Memory ID: agentcore_starter_strands_mem-abc123
#   Memory Status: CREATING (if still provisioning)
#   Memory Type: STM+LTM (provisioning...) (if creating with LTM)
#   Memory Type: STM+LTM (3 strategies) (when active with strategies)
#   Memory Type: STM only (if configured without LTM)
#   Observability: Enabled
```

**Note**: LTM strategies require 2-5 minutes to activate. STM is provisioned immediately if LTM is not selected.

## Step 4: Test Memory and Code Interpreter

### Test Short-Term Memory (STM)

Testing within a single session:

```bash
# Store information (session IDs must be 33+ characters)
agentcore invoke '{"prompt": "Remember that my favorite agent platform is AgentCore"}'

# If invoked too early (memory still provisioning), you'll see:
# "Memory is still provisioning (current status: CREATING).
#  Long-term memory extraction takes 60-180 seconds to activate.
#
#  Please wait and check status with:
#    agentcore status"

# Retrieve within same session
agentcore invoke '{"prompt": "What is my favorite agent platform?"}'

# Expected response:
# "Your favorite agent platform is AgentCore."
```

### Test Long-Term Memory (LTM) - Cross-Session Persistence

LTM enables information persistence across different sessions. This requires waiting for LTM extraction after storing information.

```bash
# Session 1: Store facts
agentcore invoke '{"prompt": "My email is user@example.com and I am an AgentCore user"}'
```

Wait for extraction that runs in the background by AgentCore. This typically takes 10-30 seconds. If you do not see the facts, wait a few more seconds and try again.

```bash
sleep 20
# Session 2: Different runtime session retrieves the facts extracted from initial session
SESSION_ID=$(python -c "import uuid; print(uuid.uuid4())")
agentcore invoke '{"prompt": "Tell me about myself?"}' --session-id $SESSION_ID

# Expected response:
# "Your email address is user@example.com."
# "You appear to be a user of AgentCore, which seems to be your favorite agent platform."
```

### Test Code Interpreter

```bash
# Store data
agentcore invoke '{"prompt": "My dataset has values: 23, 45, 67, 89, 12, 34, 56."}'

# Create visualization
agentcore invoke '{"prompt": "Create a text-based bar chart visualization showing the distribution of values in my dataset with proper labels"}'

# Expected: Agent generates matplotlib code to create a bar chart
```

## Step 5: View Traces and Logs

### Access CloudWatch Dashboard

Navigate to the GenAI Observability dashboard to view end-to-end request traces including agent execution tracking, memory retrieval operations, code interpreter executions, agent reasoning steps, and latency breakdown by component. The dashboard provides a service map view showing agent runtime connections to Memory and Code Interpreter services with request flow visualization and latency metrics, as well as detailed X-Ray traces for debugging and performance analysis.

```bash
# Get the dashboard URL from status
agentcore status

# Navigate to the URL shown, or go directly to:
# https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
# Note: Replace the region
```

### View Agent Runtime Logs

```bash
# The correct log paths are shown in the invoke or status output
agentcore status

# You'll see log paths like:
# aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --follow

# Copy this command from the output to view logs
# For example:
aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --follow

# For recent logs, use the --since option as shown in the output:
aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --since 1h
```

## Clean Up

```bash
agentcore destroy

# Removes:
#   - Runtime endpoint and agent
#   - Memory resources (STM + LTM)
#   - ECR repository and images
#   - IAM roles (if auto-created)
#   - CloudWatch log groups (optional)
```

## Troubleshooting

<details>
<summary><strong>Memory Configuration Not Appearing</strong></summary>

**"Memory option not showing during `agentcore configure`":**

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

#If Step 6 still doesn’t work, the nuclear option:
cd ..
mkdir fresh-agentcore-project && cd fresh-agentcore-project
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir "bedrock-agentcore-starter-toolkit>=0.1.21" strands-agents boto3
# Copy your agent code here, then reconfigure
```

**Additional checks:**

- Ensure you're running `agentcore configure` from within the activated virtual environment
- If using an IDE (VSCode, PyCharm), restart the IDE after reinstalling
- Verify no system-wide agentcore installation conflicts: `pip list | grep bedrock-agentcore`

</details>

<details>
<summary><strong>Region Misconfiguration</strong></summary>

**If you need to change your region configuration:**

1. Clean up resources in the incorrect region:
   ```bash
   agentcore destroy

   # This removes:
   #   - Runtime endpoint and agent
   #   - Memory resources (STM + LTM)
   #   - ECR repository and images
   #   - IAM roles (if auto-created)
   #   - CloudWatch log groups (optional)
   ```

2. Verify your AWS CLI is configured for the correct region:
   ```bash
   aws configure get region
   # Or reconfigure for the correct region:
   aws configure set region <your-desired-region>
   ```

3. Ensure Bedrock model access is enabled in the target region (AWS Console → Bedrock → Model access)

4. Copy your agent code and requirements.txt to the new folder, then return to **Step 2: Configure and Deploy**

</details>

<details>
<summary><strong>Memory Issues</strong></summary>

**"Memory status is not active" error:**

- Run `agentcore status` to check memory status
- If showing "provisioning", wait 2-3 minutes
- Retry after status shows "STM+LTM (3 strategies)"

**Cross-session memory not working:**

- Verify LTM is active (not "provisioning")
- Wait 15-30 seconds after storing facts for extraction
- Check extraction logs for completion

</details>

<details>
<summary><strong>Permission Errors (Non-Admin Users)</strong></summary>

**Access denied errors during `agentcore configure`, `agentcore launch`, or `agentcore invoke`:**

Non-admin users (including SageMaker notebook users) need comprehensive permissions beyond the basic toolkit policy. Common errors include:

- `AccessDeniedException` for `bedrock-agentcore:CreateMemory`
- `AccessDeniedException` for `bedrock-agentcore:CreateAgentRuntime`
- `AccessDeniedException` for `bedrock-agentcore:CreateWorkloadIdentity`
- `AccessDeniedException` for `bedrock-agentcore:InvokeAgentRuntime`
- `AccessDeniedException` for `iam:PassRole`

**Solution**: Attach the complete non-admin user permissions policy to your IAM user or role. See [Complete Non-Admin User Permissions](#complete-non-admin-user-permissions) below.

</details>

<details>
<summary><strong>Observability Issues</strong></summary>

**No traces appearing:**

- Verify observability was enabled during `agentcore configure`
- Check IAM permissions include CloudWatch and X-Ray access
- Wait 30-60 seconds for traces to appear in CloudWatch
- Traces are viewable at: AWS Console → CloudWatch → Service Map or X-Ray → Traces

**Missing memory logs:**

- Check log group exists: `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/<memory-id>`
- Verify IAM role has CloudWatch Logs permissions

</details>

---

### Complete Non-Admin User Permissions

<details>
<summary><strong>Complete Non-Admin User Permissions</strong></summary>

### Why These Permissions Are Needed

The [basic toolkit policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit) documented in the AWS docs is insufficient for non-admin users. It's missing critical permissions for:

- **Memory operations**: Creating and managing memory resources
- **Agent runtime operations**: Creating and invoking agents
- **Identity operations**: Creating workload identities for authentication
- **Data plane access**: Invoking deployed agents
- **Cleanup operations**: Deleting resources during destroy

**Who needs this:**
- IAM users without `PowerUserAccess` or `AdministratorAccess`
- SageMaker notebook execution roles
- EC2 instance profiles
- Any role-based access in managed environments

**Why it works for admins but not others:**
- Admin policies (`PowerUserAccess`, `AdministratorAccess`) include wildcard permissions like `bedrock-agentcore:*`
- Non-admin users need every operation explicitly granted

### Complete Policy

Attach this policy to your IAM user or role in addition to the basic toolkit policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PassRoleForServices",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::*:role/AmazonBedrockAgentCore*",
                "arn:aws:iam::*:role/service-role/AmazonBedrockAgentCore*"
            ],
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": [
                        "bedrock-agentcore.amazonaws.com",
                        "codebuild.amazonaws.com",
                        "ecs-tasks.amazonaws.com"
                    ]
                }
            }
        },
        {
            "Sid": "BedrockAgentCoreControlPlane",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateAgentRuntime",
                "bedrock-agentcore:UpdateAgentRuntime",
                "bedrock-agentcore:DeleteAgentRuntime",
                "bedrock-agentcore:GetAgentRuntime",
                "bedrock-agentcore:ListAgentRuntimes",
                "bedrock-agentcore:CreateAgentRuntimeEndpoint",
                "bedrock-agentcore:UpdateAgentRuntimeEndpoint",
                "bedrock-agentcore:DeleteAgentRuntimeEndpoint",
                "bedrock-agentcore:GetAgentRuntimeEndpoint",
                "bedrock-agentcore:ListAgentRuntimeEndpoints",
                "bedrock-agentcore:CreateMemory",
                "bedrock-agentcore:UpdateMemory",
                "bedrock-agentcore:DeleteMemory",
                "bedrock-agentcore:GetMemory",
                "bedrock-agentcore:ListMemories"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BedrockAgentCoreIdentity",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateWorkloadIdentity",
                "bedrock-agentcore:GetWorkloadIdentity",
                "bedrock-agentcore:DeleteWorkloadIdentity",
                "bedrock-agentcore:ListWorkloadIdentities",
                "bedrock-agentcore:UpdateWorkloadIdentity"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:*:*:workload-identity-directory/*",
                "arn:aws:bedrock-agentcore:*:*:workload-identity-directory/*/workload-identity/*"
            ]
        },
        {
            "Sid": "BedrockAgentCoreDataPlane",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
            ],
            "Resource": "arn:aws:bedrock-agentcore:*:*:runtime/*"
        },
        {
            "Sid": "ECRCleanup",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchDeleteImage",
                "ecr:DeleteRepository"
            ],
            "Resource": "arn:aws:ecr:*:*:repository/bedrock-agentcore-*"
        },
        {
            "Sid": "CodeBuildCleanup",
            "Effect": "Allow",
            "Action": [
                "codebuild:DeleteProject"
            ],
            "Resource": "arn:aws:codebuild:*:*:project/bedrock-agentcore-*"
        }
    ]
}
```

### How to Attach This Policy

**For IAM Users:**
1. Go to **IAM Console** → **Users** → Select your user
2. Click **Add permissions** → **Create inline policy**
3. Switch to **JSON** tab and paste the policy above
4. Name it: `BedrockAgentCoreNonAdminAccess`
5. Click **Create policy**

**For SageMaker Execution Roles:**
1. Go to **IAM Console** → **Roles** → Find your SageMaker execution role
2. Click **Add permissions** → **Create inline policy**
3. Switch to **JSON** tab and paste the policy above
4. Name it: `BedrockAgentCoreNonAdminAccess`
5. Click **Create policy**

**For EC2 Instance Profiles or Other Roles:**
1. Go to **IAM Console** → **Roles** → Select your role
2. Click **Add permissions** → **Create inline policy**
3. Switch to **JSON** tab and paste the policy above
4. Name it: `BedrockAgentCoreNonAdminAccess`
5. Click **Create policy**

</details>


---

## Summary

You've deployed a production agent with:

- **Runtime** for managed container orchestration
- **Memory** with STM for immediate context and LTM for cross-session persistence
- **Code Interpreter** for secure Python execution with data visualization capabilities
- **AWS X-Ray Tracing** automatically configured for distributed tracing
- **CloudWatch Integration** for logs and metrics with Transaction Search enabled

All services are automatically instrumented with X-Ray tracing, providing complete visibility into agent behavior, memory operations, and tool executions through the CloudWatch dashboard.
