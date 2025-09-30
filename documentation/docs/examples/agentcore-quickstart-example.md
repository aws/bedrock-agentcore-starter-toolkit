
# Amazon Bedrock AgentCore Runtime: Memory + Code Interpreter Quickstart

## Introduction

This guide demonstrates deploying an AI agent that combines:

- **AgentCore Runtime**: Managed compute service that runs your containerized agent with automatic scaling and built-in observability.
- **Short-term and long-term memory** for conversation persistence within and across sessions
- **Code Interpreter tool** for dynamic Python execution in AWS’s secure sandbox
- **Built-in observability** via AWS X-Ray tracing and CloudWatch for monitoring agent behavior, memory operations, and tool usage

You’ll build and deploy an agent with runtime hosting, memory persistence, secure code execution, and full observability to production in under 15 minutes.

## Prerequisites

- **AWS Permissions:** If you are a root user or using Admin credentails, then you can skip this pre-requisite. If you need specific permissions to use the starter toolkit. See the [Permissions Reference](#permissions-reference) section for the complete IAM policy.
- AWS CLI configured (`aws configure`)
- **Amazon Bedrock model access enabled for Claude 3.7 Sonnet** (Go to AWS Console → Bedrock → Model access → Enable “Claude 3.7 Sonnet” in your region). For information about using a different model with the Strands Agents see the Model Providers section in the [Strands Agents SDK](https://strandsagents.com/latest/documentation/docs/) documentation.
- Python 3.10 or newer

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages
pip install bedrock-agentcore-starter-toolkit strands-agents boto3
```

## Understanding the Architecture

Key components in this implementation:

- **Runtime**: Managed compute service that runs your containerized agent with automatic scaling. See [AgentCore Runtime docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- **Memory Service**: Dual-layer storage with short-term memory (chronological event storage with 30-day retention) and long-term memory (extraction of user preferences, semantic facts, and session summaries). See [AgentCore Memory docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- **Code Interpreter**: AWS-managed Python sandbox with pre-installed libraries. See [AgentCore Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html)
- **Strands Framework**: Simplifies agent creation with memory session management
- **AWS X-Ray & CloudWatch**: Automatic tracing and logging for complete visibility

## Step 1: Create the Agent

Create `strands_agentcore_starter.py`:

```python
"""
Strands Agent with AgentCore Memory and Code Interpreter
"""
import os
from strands import Agent, tool
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION", "us-west-2")
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

```
strands-agents
bedrock-agentcore
```

## Step 2: Configure and Deploy

The AgentCore CLI automates deployment with intelligent provisioning:

### Configure the Agent

```bash
agentcore configure -e strands_agentcore_starter.py

# Interactive prompts:
# Execution role (press Enter to auto-create)
# ECR repository (press Enter to auto-create)
# Memory configuration:
#   - If existing memories found: Choose from list or press Enter to create new
#   - If creating new: Enable long-term memory extraction? (yes/no) → yes
#   Note: Short-term memory is always enabled by default
```

**What’s happening:** The toolkit analyzes your code, detects the memory integration, prepares deployment configurations, and creates IAM roles with permissions for Memory. When observability is enabled, Transaction Search is automatically configured.

### Deploy to Runtime

```bash
agentcore launch

# This performs:
# 1. Memory resource provisioning (STM + LTM strategies)
# 2. Docker container build with dependencies
# 3. ECR repository push
# 4. AgentCore Runtime deployment with X-Ray tracing enabled
# 5. CloudWatch Transaction Search configuration (automatic)
# 6. Endpoint activation with trace collection
```

**Expected output:**

```
✅ Memory created: bedrock_agentcore_memory_ci_agent_memory-abc123
Observability is enabled, configuring Transaction Search...
✅ Transaction Search configured: resource_policy, trace_destination, indexing_rule
🔍 GenAI Observability Dashboard:
   https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
✅ Container deployed to Bedrock AgentCore
Agent ARN: arn:aws:bedrock-agentcore:us-west-2:123456789:runtime/memory_ci_agent-xyz
```

## Step 3: Monitor Deployment

Check deployment status:

```bash
agentcore status

# Shows:
# Memory ID: bedrock_agentcore_memory_ci_agent_memory-abc123
# Memory Status: CREATING - if still provisioning
# Memory Type: STM+LTM (provisioning...) - if creating with LTM
# Memory Type: STM+LTM (3 strategies) - when active with strategies
# Memory Type: STM only - if configured without LTM
# Observability: Enabled
```

**Note:** LTM strategies require 2-5 minutes to activate. STM is available immediately.

## Step 4: Test Memory and Code Interpreter

### Test Short-Term Memory (STM) - Immediate

STM works immediately after deployment. Test within a single session:

```bash
# Store information (session IDs must be 33+ characters)
agentcore invoke '{"prompt": "Remember that my favorite programming language is Python and I prefer tabs over spaces"}' --session-id test_session_2024_01_user123_preferences_abc

# If invoked too early (Memory still provisioning), you'll see:
# "Memory is still provisioning (current status: CREATING).
#  Long-term memory extraction takes 60-90 seconds to activate.
#
#  Please wait and check status with:
#    agentcore status"
# "I've noted that your favorite programming language is Python and you prefer tabs over spaces..."

# Retrieve within same session
agentcore invoke '{"prompt": "What is my favorite programming language?"}' --session-id test_session_2024_01_user123_preferences_abc

# Expected response:
# "Your favorite programming language is Python."
```

### Test Long-Term Memory (LTM) - Cross-Session Persistence

LTM enables information persistence across different sessions. This requires waiting for LTM extraction after storing information.

```bash
# First verify LTM is active
agentcore status
# Must show: Memory Status: ACTIVE and Memory Type: STM+LTM (3 strategies)
# If Memory Status shows "CREATING", wait 2-3 minutes

# Session 1: Store facts
agentcore invoke '{"prompt": "My email is user@example.com and I work at TechCorp as a senior engineer"}' --session-id ltm_test_session_one_2024_january_user123_xyz

# Wait for extraction
sleep 20

# Session 2: Different session retrieves the facts
agentcore invoke '{"prompt": "What company do I work for?"}' --session-id ltm_test_session_two_2024_february_user456_abc

# Expected response:
# "You work at TechCorp."
```

### Test Code Interpreter

```bash
# Store data
agentcore invoke '{"prompt": "My dataset has values: 23, 45, 67, 89, 12, 34, 56"}' --session-id test_session_2024_01_user123_preferences_abc

# Calculate using remembered data
agentcore invoke '{"prompt": "Calculate the mean and standard deviation of my dataset"}' --session-id test_session_2024_01_user123_preferences_abc

# Create visualization
agentcore invoke '{"prompt": "Create a text based bar chart visualization showing the distribution of values in my dataset with proper labels"}' --session-id test_session_2024_01_user123_preferences_abc

# Expected: Agent generates matplotlib code to create a bar chart
```

## Step 5: View Traces and Logs

### Access CloudWatch Dashboard

Navigate to the GenAI Observability dashboard:

```bash
# Get the dashboard URL from status
agentcore status

# Navigate to the URL shown, or go directly to:
# https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
```

**What you’ll see:**

**Service Map View:**

- Agent runtime connections to Memory and Code Interpreter services
- Request flow visualization
- Latency by service

**Traces View (via X-Ray):**

- End-to-end request traces
- Memory retrieval operations
- Code Interpreter executions
- Agent reasoning steps
- Latency breakdown by component

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
# - Runtime endpoint and agent
# - Memory resources (STM + LTM)
# - ECR repository and images
# - IAM roles (if auto-created)
# - CloudWatch log groups (optional)
```

## Permissions Reference

### Developer Permissions for Starter Toolkit

To use the starter toolkit (`agentcore configure` and `agentcore launch` commands), you need the following IAM policy attached to your AWS user or role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAgentCoreRuntimeOperations",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateAgentRuntime",
                "bedrock-agentcore:UpdateAgentRuntime",
                "bedrock-agentcore:GetAgentRuntime",
                "bedrock-agentcore:GetAgentRuntimeEndpoint",
                "bedrock-agentcore:ListAgentRuntimes",
                "bedrock-agentcore:ListAgentRuntimeEndpoints",
                "bedrock-agentcore:DeleteAgentRuntime",
                "bedrock-agentcore:DeleteAgentRuntimeEndpoint"
            ],
            "Resource": "arn:aws:bedrock-agentcore:*:*:runtime/*"
        },
        {
            "Sid": "BedrockAgentCoreMemoryOperations",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateMemory",
                "bedrock-agentcore:UpdateMemory",
                "bedrock-agentcore:GetMemory",
                "bedrock-agentcore:DeleteMemory",
                "bedrock-agentcore:ListMemories"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:*:*:memory/*",
                "*"
            ]
        },
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:TagRole",
                "iam:ListRolePolicies",
                "iam:ListAttachedRolePolicies"
            ],
            "Resource": [
                "arn:aws:iam::*:role/*BedrockAgentCore*",
                "arn:aws:iam::*:role/service-role/*BedrockAgentCore*"
            ]
        },
        {
            "Sid": "CodeBuildProjectAccess",
            "Effect": "Allow",
            "Action": [
                "codebuild:StartBuild",
                "codebuild:BatchGetBuilds",
                "codebuild:ListBuildsForProject",
                "codebuild:CreateProject",
                "codebuild:UpdateProject",
                "codebuild:BatchGetProjects"
            ],
            "Resource": [
                "arn:aws:codebuild:*:*:project/bedrock-agentcore-*",
                "arn:aws:codebuild:*:*:build/bedrock-agentcore-*"
            ]
        },
        {
            "Sid": "CodeBuildListAccess",
            "Effect": "Allow",
            "Action": [
                "codebuild:ListProjects"
            ],
            "Resource": "*"
        },
        {
            "Sid": "IAMPassRoleAccess",
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/AmazonBedrockAgentCore*",
                "arn:aws:iam::*:role/service-role/AmazonBedrockAgentCore*"
            ]
        },
        {
            "Sid": "CloudWatchLogsAccess",
            "Effect": "Allow",
            "Action": [
                "logs:GetLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:PutResourcePolicy"
            ],
            "Resource": [
                "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*",
                "arn:aws:logs:*:*:log-group:/aws/codebuild/*",
                "arn:aws:logs:*:*:log-group:*"
            ]
        },
        {
            "Sid": "S3Access",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:CreateBucket",
                "s3:PutLifecycleConfiguration"
            ],
            "Resource": [
                "arn:aws:s3:::bedrock-agentcore-*",
                "arn:aws:s3:::bedrock-agentcore-*/*"
            ]
        },
        {
            "Sid": "ECRRepositoryAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:CreateRepository",
                "ecr:DescribeRepositories",
                "ecr:GetRepositoryPolicy",
                "ecr:InitiateLayerUpload",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage",
                "ecr:UploadLayerPart",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:ListImages",
                "ecr:BatchDeleteImage",
                "ecr:DeleteRepository",
                "ecr:TagResource"
            ],
            "Resource": [
                "arn:aws:ecr:*:*:repository/bedrock-agentcore-*"
            ]
        },
        {
            "Sid": "ECRAuthorizationAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "XRayConfiguration",
            "Effect": "Allow",
            "Action": [
                "xray:UpdateTraceSegmentDestination",
                "xray:UpdateIndexingRule",
                "xray:GetTraceSegmentDestination",
                "xray:GetIndexingRules"
            ],
            "Resource": "*"
        },
        {
            "Sid": "STSGetCallerIdentity",
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

### Auto-Generated Execution Role

**Important**: The starter toolkit automatically creates an execution role with all necessary permissions when you run `agentcore configure`. You do NOT need to create this role manually. The auto-generated role includes permissions for:

- **Memory operations** (create, read, write, retrieve)
- **Code Interpreter sessions** (create, invoke, manage)
- **Model invocation** (Bedrock models)
- **CloudWatch logging and X-Ray tracing**
- **ECR image access**

The execution role is created with a name pattern: `AmazonBedrockAgentCoreSDKRuntime-{region}-{hash}`

For reference, the auto-generated execution role includes these additional permissions for Memory and Code Interpreter:

**Memory Permissions (automatically included):**

```json
{
    "Sid": "BedrockAgentCoreMemoryCreateMemory",
    "Effect": "Allow",
    "Action": [
        "bedrock-agentcore:CreateMemory"
    ],
    "Resource": "*"
},
{
    "Sid": "BedrockAgentCoreMemory",
    "Effect": "Allow",
    "Action": [
        "bedrock-agentcore:CreateEvent",
        "bedrock-agentcore:GetEvent",
        "bedrock-agentcore:GetMemory",
        "bedrock-agentcore:GetMemoryRecord",
        "bedrock-agentcore:ListActors",
        "bedrock-agentcore:ListEvents",
        "bedrock-agentcore:ListMemoryRecords",
        "bedrock-agentcore:ListSessions",
        "bedrock-agentcore:DeleteEvent",
        "bedrock-agentcore:DeleteMemoryRecord",
        "bedrock-agentcore:RetrieveMemoryRecords"
    ],
    "Resource": [
        "arn:aws:bedrock-agentcore:{region}:{account_id}:memory/*"
    ]
}
```

**Code Interpreter Permissions (automatically included):**

```json
{
    "Sid": "BedrockAgentCoreCodeInterpreter",
    "Effect": "Allow",
    "Action": [
        "bedrock-agentcore:CreateCodeInterpreter",
        "bedrock-agentcore:StartCodeInterpreterSession",
        "bedrock-agentcore:InvokeCodeInterpreter",
        "bedrock-agentcore:StopCodeInterpreterSession",
        "bedrock-agentcore:DeleteCodeInterpreter",
        "bedrock-agentcore:ListCodeInterpreters",
        "bedrock-agentcore:GetCodeInterpreter",
        "bedrock-agentcore:GetCodeInterpreterSession",
        "bedrock-agentcore:ListCodeInterpreterSessions"
    ],
    "Resource": [
        "arn:aws:bedrock-agentcore:{region}:aws:code-interpreter/*",
        "arn:aws:bedrock-agentcore:{region}:{account_id}:code-interpreter/*",
        "arn:aws:bedrock-agentcore:{region}:{account_id}:code-interpreter-custom/*"
    ]
}
```


### Understanding Memory Selection

The toolkit provides intelligent memory management:

**Reusing Existing Memory:**
- Lists up to 10 existing memory resources from your account
- Useful for sharing memory across agents or redeploying
- Preserves all existing conversation history and extracted facts

**Creating New Memory:**
- Short-term memory (STM) always enabled - stores exact conversations
- Optional long-term memory (LTM) - extracts facts, preferences, and summaries
- Each agent can have its own isolated memory or share with others

## Troubleshooting

### Memory Issues

**“Memory status is not active” error:**

- Run `agentcore status` to check memory status
- If showing “provisioning”, wait 2-3 minutes
- Retry after status shows “STM+LTM (3 strategies)”

**Cross-session memory not working:**

- Verify LTM is active (not “provisioning”)
- Wait 15-30 seconds after storing facts for extraction
- Check extraction logs for completion

### Observability Issues

**No traces appearing:**

- Verify observability was enabled during `agentcore configure`
- Check IAM permissions include CloudWatch and X-Ray access
- Wait 30-60 seconds for traces to appear in CloudWatch
- Traces are viewable at: AWS Console → CloudWatch → Service Map or X-Ray → Traces

**Missing memory logs:**

- Check log group exists: `/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/<memory-id>`
- Verify IAM role has CloudWatch Logs permissions

### Performance Issues

**Code Interpreter timeout:**

- Simplify calculations or break into smaller steps
- Check CloudWatch logs for actual execution details

**High latency (>1s):**

- Check X-Ray trace breakdown to identify bottleneck
- First Code Interpreter call is slower (~500ms for session creation)

## Summary

You’ve deployed a production agent with:

- **AgentCore Runtime** for managed container orchestration
- **Memory Service** with STM for immediate context and LTM for cross-session persistence
- **Code Interpreter** for secure Python execution with data visualization capabilities
- **AWS X-Ray Tracing** automatically configured for distributed tracing
- **CloudWatch Integration** for logs and metrics with Transaction Search enabled

All services are automatically instrumented with X-Ray tracing, providing complete visibility into agent behavior, memory operations, and tool executions through the CloudWatch dashboard.​​​​​​​​​​​​​​​​
