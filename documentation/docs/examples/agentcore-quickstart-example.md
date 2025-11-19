# AgentCore Quickstart

## Introduction

Build and deploy a production-ready AI agent in minutes with runtime hosting, memory, secure code execution, Identity authentication, and observability. This guide shows how to use [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html), [Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html), [Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html), [Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html), and [Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html).

For Gateway features, see the [Gateway quickstart](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/gateway/quickstart.md).

## Prerequisites

Before you start, make sure you have:

- **AWS permissions**: AWS root users or users with privileged roles (such as the AdministratorAccess role) can skip this step. Others need to attach the [starter toolkit policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit) and [AmazonBedrockAgentCoreFullAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/BedrockAgentCoreFullAccess.html) managed policy.
- **AWS CLI version 2.0 or later**: Configure the AWS CLI using `aws configure`. For more information, see the [AWS Command Line Interface User Guide for Version 2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
- **Python 3.10 or newer**

> **Important: Ensure AWS Region Consistency**
>
> Ensure the following are all configured to use the **same AWS region**:
>
> - Your `aws configure` default region
> - The region where you've enabled Bedrock model access
> - All resources created during deployment will use this region

### Install the AgentCore starter toolkit

Install the AgentCore starter toolkit:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages (version 0.1.21 or later)
pip install "bedrock-agentcore-starter-toolkit>=0.1.34" strands-agents strands-agents-tools boto3
```

## Step 0: Set up Identity authentication

In this step, you’ll create Cognito user pools for both inbound (user-to-agent) and outbound (agent-to-service) authentication.

### Create Cognito pools

The `setup-cognito` command creates both Cognito pools needed for Identity in one step:

```bash
agentcore identity setup-cognito
```

**What this creates:**

- **Cognito Agent User Pool**: Manages user authentication to your agent
- **Cognito Resource User Pool**: Enables agent to access external resources
- Test users with credentials for both pools
- Environment variables file for easy access

**Expected output:**

```
✅ Cognito pools created successfully!

🔐 Credentials saved securely to:
   • .agentcore_identity_cognito_user.json
   • .agentcore_identity_user.env
```

### Load environment variables

Load the generated credentials into your shell:

```bash
# Load environment variables
export $(grep -v '^#' .agentcore_identity_user.env | xargs)

# Verify variables are loaded
echo $RUNTIME_POOL_ID
echo $IDENTITY_CLIENT_ID
```

**Available variables:**

- `RUNTIME_POOL_ID`, `RUNTIME_CLIENT_ID`, `RUNTIME_DISCOVERY_URL` - For user-to-agent authentication
- `RUNTIME_USERNAME`, `RUNTIME_PASSWORD` - Test user credentials
- `IDENTITY_POOL_ID`, `IDENTITY_CLIENT_ID`, `IDENTITY_CLIENT_SECRET` - For agent-to-service OAuth
- `IDENTITY_DISCOVERY_URL`, `IDENTITY_USERNAME`, `IDENTITY_PASSWORD` - OAuth test credentials

## Step 1: Create the agent

Create `agent.py`:

```python
"""
Strands Agent sample with AgentCore Runtime, Memory, Code Interpreter, and Identity
"""
import os
import asyncio
from strands import Agent
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token

app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Store authorization URL to return to user
auth_url_holder = {"url": None, "needs_auth": False}

@requires_access_token(
    provider_name="ExternalServiceProvider",
    scopes=["openid"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: auth_url_holder.update({"url": url, "needs_auth": True}),
    force_authentication=False
)
async def get_identity_token(*, access_token: str) -> str:
    """Get OAuth token from Identity service"""
    auth_url_holder["needs_auth"] = False
    return access_token

def format_response(result) -> str:
    """Extract code from metrics and format with LLM response."""
    parts = []

    # Extract executed code from metrics
    try:
        tool_metrics = result.metrics.tool_metrics.get('code_interpreter')
        if tool_metrics and hasattr(tool_metrics, 'tool'):
            action = tool_metrics.tool['input']['code_interpreter_input']['action']
            if 'code' in action:
                parts.append(f"## Executed Code:\n```{action.get('language', 'python')}\n{action['code']}\n```\n---\n")
    except (AttributeError, KeyError):
        pass  # No code to extract

    # Add LLM response
    parts.append(f"## 📊 Result:\n{str(result)}")
    return "\n".join(parts)

@app.entrypoint
def invoke(payload, context):
    session_id = getattr(context, 'session_id', 'default')

    # Configure memory if available
    session_manager = None
    if MEMORY_ID:
        session_manager = AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id="quickstart-user",
                retrieval_config={
                    "/users/quickstart-user/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
                    "/users/quickstart-user/preferences": RetrievalConfig(top_k=3, relevance_score=0.5)
                }
            ),
            REGION
        )

    # Create code interpreter
    code_interpreter = AgentCoreCodeInterpreter(
        region=REGION,
        session_name=session_id,
        auto_create=True,
        persist_sessions=True
    )


    # Define external service check tool
    async def check_external_service() -> str:
        """Check authentication to external services via Identity OAuth."""
        auth_url_holder["url"] = None
        auth_url_holder["needs_auth"] = False

        try:
            token_task = asyncio.create_task(get_identity_token())
            await asyncio.sleep(0.5)

            if auth_url_holder["needs_auth"] and auth_url_holder["url"]:
                token_task.cancel()
                try:
                    await token_task
                except asyncio.CancelledError:
                    pass

                return (
                    f"🔐 Authorization Required\n\n"
                    f"Open this URL to authorize:\n{auth_url_holder['url']}\n\n"
                    f"After authorizing, invoke again with the same session ID."
                )

            token = await token_task
            return (
                f"✅ Authenticated to external service\n"
                f"Token length: {len(token)} characters\n"
                f"Status: Active and cached"
            )
        except Exception as e:
            return f"❌ Failed to authenticate: {str(e)}"

    agent = Agent(
        model=MODEL_ID,
        session_manager=session_manager,
        system_prompt="""You are a helpful assistant with code execution and external service access. Use tools when appropriate.
When check_external_service returns an authorization URL, present it clearly to the user.""",
        tools=[code_interpreter.code_interpreter, check_external_service]
    )

    result = agent(payload.get("prompt", ""))
    return {"response": format_response(result)}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:

```text
strands-agents
bedrock-agentcore
strands-agents-tools
```

## Step 2: Configure and deploy the agent

In this step, you’ll use the AgentCore CLI to configure and deploy your agent with JWT authentication.

### Configure the agent with JWT authentication

Configure the agent with memory, execution settings, and JWT authentication for user access:

**For this tutorial:** When prompted for deployment type, press Enter to use the recommended Direct Code Deploy option. When prompted for the execution role, press Enter to auto-create a new role with all required permissions for the Runtime, Memory, Code Interpreter, and Observability features. When prompted for long-term memory, type yes.

```bash
agentcore configure \
  -e agent.py \
  --authorizer-config "{
    \"customJWTAuthorizer\": {
      \"discoveryUrl\": \"$RUNTIME_DISCOVERY_URL\",
      \"allowedClients\": [\"$RUNTIME_CLIENT_ID\"]
    }
  }"
```

**What this does:**

- Configures JWT authentication using the Cognito Agent User Pool
- Sets up memory and execution settings (interactive prompts)
- Saves configuration to `.bedrock_agentcore.yaml`

**Interactive prompts:**

1. Dependency File: Confirm the detected requirements.txt file or specify a different path
2. Deployment Configuration:
    - Select deployment type (1 for Direct Code Deploy - recommended, 2 for Container)
    - If Direct Code Deploy: Select Python runtime version (1 for PYTHON_3_10)
3. Execution Role: Press Enter to auto-create or provide existing role ARN/name
4. S3 Bucket: Press Enter to auto-create or provide existing S3 URI/path
5. Authorization Configuration: Configure OAuth authorizer? (yes/no) - Type `no` for this tutorial
6. Request Header Allowlist: Configure request header allowlist? (yes/no) - Type `no` for this tutorial
7. Memory Configuration: Press Enter to create new memory and Enable long-term memory extraction? (yes/no) - Type `yes` for this tutorial



### Create Identity resources

Create the credential provider and workload identity for OAuth flows:

##### Create credential provider (uses Resource User Pool)
```bash
agentcore identity create-credential-provider \
  --name ExternalServiceProvider \
  --type cognito \
  --client-id $IDENTITY_CLIENT_ID \
  --client-secret $IDENTITY_CLIENT_SECRET \
  --discovery-url $IDENTITY_DISCOVERY_URL \
  --cognito-pool-id $IDENTITY_POOL_ID
```

##### Create workload identity
```bash
agentcore identity create-workload-identity \
  --name quickstart-workload
```

**What this does:**

- Registers the Resource User Pool as an OAuth credential provider
- Creates workload identity for agent-to-Identity authentication
- Saves configuration to `.bedrock_agentcore.yaml`
- IAM permissions will be added automatically during launch

### Deploy to AgentCore

Launch your agent to the AgentCore runtime environment:

```bash
agentcore launch
```

**What happens during launch:**

- Memory resource provisioning (STM + LTM strategies)
- **Identity IAM permissions automatically added**:
  - Trust policy updated for workload identity
  - GetWorkloadAccessToken permissions
  - GetResourceOauth2Token permissions
  - Secrets Manager access for credential provider
- Docker container build with dependencies
- ECR repository push
- AgentCore Runtime deployment with X-Ray tracing enabled
- CloudWatch Transaction Search configuration
- Endpoint activation with trace collection

**Expected output:**

```text
Creating memory resource for agent: agentcore_starter_strands
⏳ Creating memory resource (this may take 30-180 seconds)...
✅ Memory is ACTIVE (took 159s)
✅ Identity permissions added automatically
   Providers: ExternalServiceProvider
✅ Container deployed to Bedrock AgentCore
Agent ARN: arn:aws:bedrock-agentcore:us-west-2:123456789:runtime/agentcore_starter_strands-xyz
```

## Step 3: Monitor deployment

Check the agent’s deployment status:

```bash
agentcore status

# Shows:
#   Memory ID: agentcore_starter_strands_mem-abc123
#   Memory Type: STM+LTM (3 strategies)
#   Observability: Enabled
#   Identity: 1 credential provider, 1 workload identity
```

## Step 4: Test Memory, Code Interpreter, and Identity

In this section, you’ll test your agent’s memory capabilities, code execution, and OAuth authentication.

### Get bearer token for authentication

Generate a JWT bearer token for agent invocation:

```bash
# Auto-loads credentials from environment
BEARER_TOKEN=$(agentcore identity get-cognito-inbound-token)
```

### Test Short-Term Memory (STM)

Test short-term memory within a single session:

```bash
# Generate unique session ID
SESSION_ID="session_$(uuidgen | tr -d '-')"

# Store information
agentcore invoke '{"prompt": "Remember that my favorite agent platform is AgentCore"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "$SESSION_ID"

# Retrieve within same session
agentcore invoke '{"prompt": "What is my favorite agent platform?"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "$SESSION_ID"

# Expected response:
# "Your favorite agent platform is AgentCore."
```

### Test long-term memory – cross-session persistence

Long-term memory (LTM) lets information persist across different sessions:

```bash
# Session 1: Store facts
agentcore invoke '{"prompt": "My email is user@example.com and I am an AgentCore user"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "session_$(uuidgen | tr -d '-')"

# Wait for extraction (10-30 seconds)
sleep 20

# Session 2: Different session retrieves extracted facts
agentcore invoke '{"prompt": "Tell me about myself?"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "session_$(uuidgen | tr -d '-')"

# Expected response:
# "Your email address is user@example.com."
# "You are an AgentCore user and your favorite platform is AgentCore."
```

### Test Code Interpreter

Test AgentCore Code Interpreter:

```bash
# Store data
agentcore invoke '{"prompt": "My dataset has values: 23, 45, 67, 89, 12, 34, 56."}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "session_$(uuidgen | tr -d '-')"

# Create visualization
agentcore invoke '{"prompt": "Create a text-based bar chart visualization showing the distribution of values in my dataset with proper labels"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "session_$(uuidgen | tr -d '-')"

# Expected: Agent generates matplotlib code to create a bar chart
```

### Test Identity OAuth Flow

Test OAuth authentication to external services:

```bash
# First invocation - triggers OAuth authorization
SESSION_ID="oauth_$(uuidgen | tr -d '-')"

agentcore invoke '{"prompt": "Call check_external_service to authenticate"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "$SESSION_ID"

# Expected response includes authorization URL:
# "🔐 Authorization Required
#
#  Open this URL to authorize:
#  https://bedrock-agentcore.us-west-2.amazonaws.com/identities/oauth2/authorize?request_uri=..."
```

**Complete the OAuth flow:**

1. **Copy the authorization URL** from the response
1. **Open in browser**
1. **Login** with Resource User Pool credentials (`$IDENTITY_USERNAME` / `$IDENTITY_PASSWORD`)
1. **Approve** the consent screen
1. **Invoke again** with the **same session ID**:

```bash
# Second invocation - uses cached token
agentcore invoke '{"prompt": "Call check_external_service"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "$SESSION_ID"

# Expected response:
# "✅ Authenticated to external service
#  Token length: 1234 characters
#  Status: Active and cached"
```

## Step 5: View Traces and Logs

In this section, you’ll use observability features to monitor your agent’s performance.

### Access the Amazon CloudWatch dashboard

Navigate to the GenAI Observability dashboard to view end-to-end request traces including agent execution tracking, memory retrieval operations, code interpreter executions, Identity OAuth operations, and latency breakdown by component:

```bash
# Get the dashboard URL from status
agentcore status

# Navigate to the URL shown, or go directly to:
# https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core
# Note: Replace the Region
```

### View AgentCore Runtime logs

Access detailed AgentCore Runtime logs for debugging and monitoring:

```bash
# The correct log paths are shown in the invoke or status output
agentcore status

# Copy the log command from the output, for example:
aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --follow

# For recent logs:
aws logs tail /aws/bedrock-agentcore/runtimes/AGENT_ID-DEFAULT --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs]" --since 1h
```

## Clean up

Remove all resources created during this tutorial:

```bash
# Clean up Identity resources
agentcore identity cleanup --force

# Clean up Runtime, Memory, and other resources
agentcore destroy

# This removes:
#   - Identity: Credential providers, workload identities, Cognito pools
#   - AgentCore Runtime endpoint and agent
#   - AgentCore Memory resources (STM + LTM)
#   - Amazon ECR repository and images
#   - IAM roles (if auto-created)
#   - CloudWatch log groups (optional)
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
agentcore configure -e agentcore_starter_strands.py --authorizer-config "..."
```

</details>

<details>
<summary><strong>Identity Issues</strong></summary>

**Authorization URL not showing in agent response:**

- Verify the `auth_url_holder` pattern is used in your agent code
- Check that `on_auth_url` callback is storing the URL (not printing to logs)
- Ensure you’re calling the external service tool in your prompt

**“Failed to get token: SECRET_HASH was not received”:**

- The Cognito client has a secret but you’re using password auth
- Solution: Run `agentcore identity setup-cognito` again to create client without secret

**Token expired or authorization failed:**

- Use a new session ID and start the OAuth flow again
- Session IDs must be 33+ characters (use `uuidgen` pattern shown in examples)

**Cross-invocation OAuth not working:**

- Ensure you’re using the **same session ID** for both invocations
- Token is cached per session - different session IDs won’t share tokens
- Wait a few seconds between authorization and second invocation

</details>

<details>
<summary><strong>Region Misconfiguration</strong></summary>

**If you need to change your region configuration:**

1. Clean up resources in the incorrect region:

   ```bash
   agentcore identity cleanup --force
   agentcore destroy
   ```
1. Verify your AWS CLI is configured for the correct region:

   ```bash
   aws configure get region
   # Or reconfigure:
   aws configure set region <your-desired-region>
   ```
1. Ensure Bedrock model access is enabled in the target region
1. Return to **Step 0: Set up Identity authentication**

</details>

<details>
<summary><strong>Memory Issues</strong></summary>

**Cross-session memory not working:**

- Verify LTM is active (not “provisioning”)
- Wait 15-30 seconds after storing facts for extraction
- Check extraction logs for completion

</details>

<details>
<summary><strong>Observability Issues</strong></summary>

**No traces appearing:**

- Verify observability was enabled during `agentcore configure`
- Check IAM permissions include CloudWatch and X-Ray access
- Wait 30-60 seconds for traces to appear in CloudWatch

**Missing Identity operation traces:**

- Verify Identity permissions were added during `agentcore launch`
- Check the agent invocation includes `--bearer-token`
- OAuth operations appear in X-Ray traces as separate segments

</details>

-----

## Summary

You’ve deployed a production agent with:

- **Runtime** for managed container orchestration
- **Identity** with JWT authentication (inbound) and OAuth 2.0 flows (outbound)
- **Memory** with STM for immediate context and LTM for cross-session persistence
- **Code Interpreter** for secure Python execution with data visualization capabilities
- **AWS X-Ray Tracing** automatically configured for distributed tracing
- **CloudWatch Integration** for logs and metrics with Transaction Search enabled

All services are automatically instrumented with X-Ray tracing, providing complete visibility into agent behavior, OAuth flows, memory operations, and tool executions through the CloudWatch dashboard.
