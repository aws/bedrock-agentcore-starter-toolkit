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
agentcore identity setup-cognito --auth-flow user
```

**What this creates:**

- **Runtime User Pool**: For authenticating users to your agent (inbound)
- **Identity User Pool**: For your agent to access external services (outbound)
- Test users with credentials for both pools
- Environment variables file for easy access

## Step 2: Load Environment Variables

```bash
# Bash/Zsh (for USER flow)
export $(cat .agentcore_identity_user.env | xargs)

# For M2M flow, use:
# export $(cat .agentcore_identity_m2m.env | xargs)

# Verify variables are loaded
echo $RUNTIME_POOL_ID
echo $IDENTITY_CLIENT_ID
```

**Available variables (USER flow):**

- `RUNTIME_POOL_ID`, `RUNTIME_CLIENT_ID`, `RUNTIME_DISCOVERY_URL`
- `RUNTIME_USERNAME`, `RUNTIME_PASSWORD`
- `IDENTITY_POOL_ID`, `IDENTITY_CLIENT_ID`, `IDENTITY_CLIENT_SECRET`
- `IDENTITY_DISCOVERY_URL`, `IDENTITY_USERNAME`, `IDENTITY_PASSWORD`

**For M2M flow, identity variables are:**

- `IDENTITY_POOL_ID`, `IDENTITY_CLIENT_ID`, `IDENTITY_CLIENT_SECRET`
- `IDENTITY_TOKEN_ENDPOINT`, `IDENTITY_RESOURCE_SERVER`

## Step 3: Create Agent Code

Create `agent.py`:

```python
"""Identity Demo Agent - OAuth 2.0 USER_FEDERATION Flow"""

from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token

app = BedrockAgentCoreApp()

# Store authorization URL for returning to user
auth_url_holder = {"url": None}

@requires_access_token(
    provider_name="ExternalServiceProvider",
    scopes=["openid"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: auth_url_holder.update({"url": url}),
    force_authentication=False
)
async def get_external_service_token(*, access_token: str) -> str:
    """Get OAuth token for external service"""
    return access_token

@app.entrypoint
async def invoke(payload, context):
    """Main entrypoint"""

    user_message = payload.get("prompt", "")

    try:
        auth_url_holder["url"] = None  # Reset
        token = await get_external_service_token()

        # If URL was set, authorization is needed
        if auth_url_holder["url"]:
            return {
                "response": (
                    f"🔐 Authorization Required\n\n"
                    f"To access the external service, please authorize:\n"
                    f"{auth_url_holder['url']}\n\n"
                    f"Login with Identity Pool credentials:\n"
                    f"Username: {auth_url_holder.get('username', 'see IDENTITY_USERNAME')}\n"
                    f"Password: {auth_url_holder.get('password', 'see IDENTITY_PASSWORD')}\n\n"
                    f"After authorizing, invoke again with the same session ID."
                )
            }

        # Token obtained - success
        return {
            "response": (
                f"✅ External Service Response\n\n"
                f"Successfully called external service!\n"
                f"Token obtained and cached for this session.\n"
                f"Token length: {len(token)} characters\n\n"
                f"Subsequent calls in this session will use the cached token."
            )
        }

    except Exception as e:
        return {"response": f"❌ Error: {str(e)}"}

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

- Configures agent with JWT authentication using Runtime pool
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
  --name identity-demo-workload \
  --callback-urls http://localhost:8081/oauth2/callback
```

**What this does:**

- Creates workload identity for agent-to-Identity authentication
- Registers OAuth callback URLs
- Links workload to agent configuration

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
# Get bearer token for Runtime authentication
BEARER_TOKEN=$(agentcore identity get-inbound-token \
  --pool-id $RUNTIME_POOL_ID \
  --client-id $RUNTIME_CLIENT_ID \
  --username $RUNTIME_USERNAME \
  --password $RUNTIME_PASSWORD)

# Invoke agent
agentcore invoke '{"prompt": "Call the external service"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "demo_session_$(date +%s)"
```

**Expected Response:**

```
🔐 Authorization Required

To access the external service, please authorize:
https://bedrock-agentcore.us-west-2.amazonaws.com/identities/oauth2/authorize?request_uri=...

Login with Identity Pool credentials:
Username: externaluser12345678
Password: Abc123...

After authorizing, invoke again with the same session ID.
```

### Complete OAuth Flow

1. **Copy the authorization URL** from the response
1. **Open in browser**
1. **Login** with Identity Pool credentials (IDENTITY_USERNAME/IDENTITY_PASSWORD from env vars)
1. **Approve** the consent screen
1. **Invoke again** with the **same session ID**:

```bash
# Use the SAME session ID as before!
agentcore invoke '{"prompt": "Call the external service"}' \
  --bearer-token "$BEARER_TOKEN" \
  --session-id "demo_session_1234567890"  # Same session ID!
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
- Both Cognito user pools (Runtime + Identity)
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

**Fix**: Run `agentcore identity setup-cognito` again (creates client without secret)


## Next Steps

- Add multiple credential providers for different external services
- Implement M2M (machine-to-machine) OAuth flows
- Build production agents with Memory and Code Interpreter
- Explore VPC networking for secure service access

## Summary

You’ve built an agent with:

- ✅ Automated Cognito pool setup (no bash scripts)
- ✅ JWT authentication for user access
- ✅ OAuth 2.0 flows for external service calls
- ✅ Automatic IAM permission management
- ✅ Token caching per session
- ✅ Secure credential storage
- ✅ One-command cleanup
