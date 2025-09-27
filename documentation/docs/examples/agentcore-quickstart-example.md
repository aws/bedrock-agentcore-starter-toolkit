# Amazon Bedrock AgentCore Runtime: Memory + Code Interpreter Quickstart

## Introduction

This guide demonstrates deploying an AI agent that combines:

- **Short-term and long-term memory** for conversation persistence
- **Code Interpreter tool** for dynamic Python execution in AWS’s secure sandbox
- **Built-in observability** via AWS X-Ray tracing and CloudWatch for monitoring agent behavior, memory operations, and tool usage

You’ll build and deploy an agent with memory persistence, secure code execution, and full observability to production in under 15 minutes.


## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Access to Amazon Bedrock Claude 3.7 Sonnet model
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

- **AgentCore Runtime**: Container orchestration service that hosts your agent
- **Memory Service**: Dual-layer storage with STM (exact conversation storage) and LTM (intelligent fact extraction)
- **Code Interpreter**: AWS-managed Python sandbox with 4GB RAM and pre-installed libraries
- **Strands Framework**: Simplifies agent creation with memory session management
- **AWS X-Ray & CloudWatch**: Automatic tracing and logging for complete visibility

## Step 1: Create the Agent

Create `memory_ci_agent.py`:

```python
"""
Strands Agent Assistant - With AgentCore Memory and Tools
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

code_interpreter = None
code_session_id = None

@tool
def calculate(code: str) -> str:
    """Execute Python code for calculations."""
    global code_interpreter, code_session_id
    
    if not code_interpreter:
        code_interpreter = CodeInterpreter(REGION)
    
    if not code_session_id:
        code_session_id = code_interpreter.start(
            name="calc_session",
            session_timeout_seconds=1800
        )
    
    result = code_interpreter.invoke("executeCode", {
        "code": code,
        "language": "python"
    })
    
    for event in result.get("stream", []):
        if stdout := event.get("result", {}).get("structuredContent", {}).get("stdout"):
            return stdout
    return "Executed"

@app.entrypoint
def invoke(payload, context):
    if not MEMORY_ID:
        return {"error": "Memory not configured"}
    
    session_id = getattr(context, 'session_id', 'default')
    
    memory_config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id="user",
        retrieval_config={
            "/users/user/facts": RetrievalConfig(
                top_k=3,
                relevance_score=0.5  # Reduces API calls
            )
        }
    )
    
    agent = Agent(
        session_manager=AgentCoreMemorySessionManager(memory_config, REGION),
        system_prompt="""Personal finance assistant with memory and calculations.
        For ANY calculation, use the calculate tool - never do mental math.""",
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
agentcore configure --e memory_ci_agent.py

# Interactive prompts:
# Execution role (press Enter to auto-create)
# ECR repository (press Enter to auto-create)
# Enable long-term memory extraction? → yes
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
# Memory: STM+LTM (provisioning...) - if still creating
# Memory: STM+LTM (3 strategies) - when active
# Observability: Enabled
```

**Note:** LTM strategies require 2-5 minutes to activate. STM is available immediately.

## Step 4: Test Core Functionality

### Test Short-Term Memory (Immediate)

STM works immediately after deployment. Test within a single session:

```bash
# Store information (session IDs must be 33+ characters)
agentcore invoke '{"prompt": "Remember that my favorite programming language is Python and I prefer tabs over spaces"}'

# Expected response:
# "I've noted that your favorite programming language is Python and you prefer tabs over spaces..."

# Retrieve within same session
agentcore invoke '{"prompt": "What is my favorite programming language?"}'

# Expected response:
# "Your favorite programming language is Python."
```

### Test Code Interpreter with Memory

```bash
# Store data
agentcore invoke '{"prompt": "My dataset has values: 23, 45, 67, 89, 12, 34, 56"}'

# Calculate using remembered data
agentcore invoke '{"prompt": "Calculate the mean and standard deviation of my dataset"}'

# Expected response:
# "Based on your dataset [23, 45, 67, 89, 12, 34, 56], the mean is 46.57 and the standard deviation is 25.73"
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


## Step 6: Test Long-Term Memory (Cross-Session)

**Pre-requisite:** You must have enabled Long Term Memory during agentcore configure. 
LTM enables information persistence across different sessions. This requires waiting for LTM extraction after storing information.

### Verify LTM is Active

```bash
agentcore status
# Must show: "Memory: STM+LTM (3 strategies)"
# If showing "provisioning", wait 2-3 minutes
```

### Session 1: Provide Information

```bash
# Store facts in first session
agentcore invoke '{"prompt": "My email is user@example.com and I work at TechCorp as a senior engineer"}' --session-id ltm_test_session_one_2024_january_user123_xyz
```

### Wait for Extraction

```bash
# Wait 15-30 seconds for LTM extraction
sleep 20

# To verify extraction through the GenAI Observability Dashboard:
# 1. Open the dashboard URL from 'agentcore status'
# 2. Navigate to the "Traces" section
# 3. Filter for your session ID or recent timeframe
# 4. Look for completed extraction spans

# Alternatively, verify LTM is active through status check:
agentcore status | grep Memory
# Should show: Memory: STM+LTM (3 strategies)
```

### Session 2: Retrieve from Different Session

```bash
agentcore invoke '{"prompt": "What company do I work for?"}' --session-id ltm_test_session_two_2024_february_user456_abc

# Expected response:
# "You work at TechCorp."
```

**What’s happening:** The second session has a completely different ID but successfully retrieves facts stored by the first session through LTM.


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
- **Code Interpreter** for secure Python execution
- **AWS X-Ray Tracing** automatically configured for distributed tracing
- **CloudWatch Integration** for logs and metrics with Transaction Search enabled

All services are automatically instrumented with X-Ray tracing, providing complete visibility into agent behavior, memory operations, and tool executions through the CloudWatch dashboard.​​​​​​​​​​​​​​​