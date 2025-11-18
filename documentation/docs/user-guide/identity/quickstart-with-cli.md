# Getting Started with AgentCore Identity (CLI)

Amazon Bedrock AgentCore Identity provides secure OAuth 2.0 authentication for your AI agents. This quickstart demonstrates how to build an agent that authenticates users and accesses external services using the AgentCore CLI.

## What You'll Build

A simple agent that:
1. Accepts JWT bearer tokens for user authentication (inbound auth)
2. Obtains OAuth tokens to call external services on behalf of users (outbound auth)
3. Demonstrates the complete OAuth flow with user consent

## Prerequisites

- AWS account with appropriate permissions
- Python 3.10+ installed
- AWS CLI configured (`aws configure`)
- bedrock-agentcore-starter-toolkit installed

## Installation

```bash
# Create project directory
mkdir agentcore-identity-demo
cd agentcore-identity-demo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit strands-agents boto3
```

## Step 1: Create Cognito Pools (Automated)

The `setup-cognito` command creates both Cognito pools needed for Identity in one step:

```bash
agentcore identity setup-cognito
```

**What this creates:**

- **Cognito Agent User Pool**: Manages user authentication to your agent
- **Cognito Resource User Pool**: Enables agent to access external resources
- Test users with credentials for both pools
- Environment variables file for easy access

**Output shows:**

```
✅ Cognito pools created successfully!

🔐 Credentials saved securely to:
   • .agentcore_identity_cognito_user.json
   • .agentcore_identity_user.env
```

## Step 2: Load Environment Variables

```bash
# Bash/Zsh (for USER flow)
export $(grep -v '^#' .agentcore_identity_user.env | xargs)

# Verify variables are loaded
echo $RUNTIME_POOL_ID
echo $IDENTITY_CLIENT_ID
```

**Available variables (USER flow):**

- `RUNTIME_POOL_ID`, `RUNTIME_CLIENT_ID`, `RUNTIME_DISCOVERY_URL`
- `RUNTIME_USERNAME`, `RUNTIME_PASSWORD`
- `IDENTITY_POOL_ID`, `IDENTITY_CLIENT_ID`, `IDENTITY_CLIENT_SECRET`
- `IDENTITY_DISCOVERY_URL`, `IDENTITY_USERNAME`, `IDENTITY_PASSWORD`

## Step 3: Create Agent Code

Create `agent.py`:

```python
"""AgentCore Identity Quickstart: Inbound + Outbound Authentication"""
import os
import asyncio
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token

app = BedrockAgentCoreApp()

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

@tool
async def check_external_service() -> str:
    """Check authentication to external services via Identity OAuth."""
    # Reset state
    auth_url_holder["url"] = None
    auth_url_holder["needs_auth"] = False

    try:
        # Start token request with short timeout
        token_task = asyncio.create_task(get_identity_token())
        await asyncio.sleep(0.5)

        # Check if authorization is needed
        if auth_url_holder["needs_auth"] and auth_url_holder["url"]:
            token_task.cancel()
            try:
                await token_task
            except asyncio.CancelledError:
                pass

            return (
                f"🔐 Authorization Required\n\n"
                f"Please open this URL in your browser to authorize:\n"
                f"{auth_url_holder['url']}\n\n"
                f"After authorizing, call this tool again with the same session ID."
            )

        # Token obtained
        token = await token_task
        return (
            f"✅ Authenticated to external service\n"
            f"Token length: {len(token)} characters\n"
            f"Status: Active and cached for this session"
        )

    except Exception as e:
        return f"❌ Failed to authenticate: {str(e)}"

@app.entrypoint
async def invoke(payload, context):
    """Main entrypoint"""
    user_message = payload.get("prompt", "")

    agent = Agent(
        model=MODEL_ID,
        system_prompt=(
            "You are a helpful assistant with access to external services via OAuth.\n"
            "When check_external_service returns an authorization URL, "
            "present it clearly to the user and ask them to authorize."
        ),
        tools=[check_external_service]
    )

    response = await agent.invoke_async(user_message)
    response_text = str(response.message.get('content', [{}])[0].get('text', ''))

    return {"response": response_text}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:

```
bedrock-agentcore
bedrock-agentcore-starter-toolkit
strands-agents
boto3
```

## Step 4: Configure Agent with JWT Auth

```bash
agentcore configure \
  -e agent.py \
  --name identity_demo \
  --authorizer-config '{
    "customJWTAuthorizer": {
      "discoveryUrl": "'$RUNTIME_DISCOVERY_URL'",
      "allowedClients": ["'$RUNTIME_CLIENT_ID'"]
    }
  }' \
  --disable-memory
```

**What this does:**

- Configures agent with JWT authentication using Cognito Agent User Pool
- Creates execution role (or uses provided one)
- Saves configuration to `.bedrock_agentcore.yaml`

## Step 5: Create Credential Provider

```bash
agentcore identity create-credential-provider \
  --name ExternalServiceProvider \
  --type cognito \
  --client-id $IDENTITY_CLIENT_ID \
  --client-secret $IDENTITY_CLIENT_SECRET \
  --discovery-url $IDENTITY_DISCOVERY_URL \
  --cognito-pool-id $IDENTITY_POOL_ID
```

**What this does:**

- Creates OAuth credential provider in Identity service
- Saves provider configuration to `.bedrock_agentcore.yaml`
- IAM permissions will be added automatically during `launch`

## Step 6: Create Workload Identity

```bash
agentcore identity create-workload-identity \
  --name identity-demo-workload
```

**What this does:**

- Creates workload identity for agent-to-Identity authentication
- Enables OAuth flows for external service access

## Step 7: Deploy Agent

```bash
agentcore launch
```

**What happens during launch:**

- Agent container built and pushed to ECR
- Runtime instance created
- **IAM permissions automatically added** for Identity:
  - Trust policy updated
  - GetWorkloadAccessToken permissions
  - GetResourceOauth2Token permissions
  - Secrets Manager access for credential provider
- Agent endpoint created

**Look for this in the output:**

```
✅ Identity permissions added automatically
   Providers: ExternalServiceProvider
```

## Step 8: Invoke the Agent

### First Invocation (Triggers OAuth Flow)

```bash
# Get bearer token for Runtime authentication (auto-loads from env)
BEARER_TOKEN=$(agentcore identity get-cognito-inbound-token)

# Invoke agent
agentcore invoke '{"prompt": "Call the external service"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "demo_session_$(uuidgen | tr -d '-')"
```

**Expected Response:**

```
🔐 Authorization Required

To access the external service, please authorize:
https://bedrock-agentcore.us-west-2.amazonaws.com/identities/oauth2/authorize?request_uri=...

Login with Resource User Pool credentials:
Username: externaluser12345678
Password: Abc123...

After authorizing, invoke again with the same session ID.
```

### Complete OAuth Flow

1. **Copy the authorization URL** from the response
1. **Open in browser**
1. **Login** with Resource User Pool credentials (IDENTITY_USERNAME/IDENTITY_PASSWORD from env vars)
1. **Approve** the consent screen
1. **Invoke again** with the **same session ID**:

```bash
# Use the SAME session ID as before!
agentcore invoke '{"prompt": "Call the external service"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "demo_session_$(uuidgen | tr -d '-')"
```

**Expected Response:**

```
✅ External Service Response

Successfully called external service!
Token obtained and cached for this session.
Token length: 1234 characters

Subsequent calls in this session will use the cached token.
```

## Cleanup

```bash
# Delete all Identity resources
agentcore identity cleanup --agent identity_demo --force

# Destroy agent
agentcore destroy --agent identity_demo --force
```

**What gets cleaned up:**

- Credential provider (ExternalServiceProvider)
- Workload identity (identity-demo-workload)
- Both Cognito user pools
- IAM inline policies
- Configuration files (.agentcore_identity_*)

## Troubleshooting

### “Workload access token has not been set”

**Cause**: Using `agent(message)` instead of `await agent.invoke_async(message)`

**Fix**: Update your entrypoint to use `invoke_async`

### Authorization URL not showing in response

**Cause**: `on_auth_url` callback using `print()` which goes to logs

**Fix**: Use the pattern shown in this guide with `auth_url_holder`

### Token expired or authorization failed

**Solution**: Use a new session ID and start the OAuth flow again

### “Failed to get token: SECRET_HASH was not received”

**Cause**: Cognito client configured with secret but using password auth

**Fix**: Run `agentcore identity setup-cognito` again

## Next Steps

- Add multiple credential providers for different external services
- Implement M2M (machine-to-machine) OAuth flows
- Build production agents with Memory and Code Interpreter
- Explore VPC networking for secure service access

## Summary

You’ve built an agent with:

- ✅ Automated Cognito pool setup
- ✅ JWT authentication for user access
- ✅ OAuth 2.0 flows for external service calls
- ✅ Automatic IAM permission management
- ✅ Token caching per session
- ✅ Secure credential storage
- ✅ One-command cleanup
