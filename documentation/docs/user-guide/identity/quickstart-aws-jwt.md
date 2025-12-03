# Getting Started with AWS IAM JWT Federation (CLI)

Amazon Bedrock AgentCore supports AWS IAM JWT federation for M2M (machine-to-machine) authentication. This quickstart demonstrates how to build an agent that authenticates with external services using AWS-signed JWTs.

## What You'll Build

A simple agent that:
1. Obtains AWS-signed JWTs via STS:GetWebIdentityToken
2. Uses the JWT to authenticate with external services
3. Demonstrates secretless M2M authentication

## When to Use AWS JWT vs OAuth

| Use AWS JWT When | Use OAuth When |
|------------------|----------------|
| Agent acts with its own identity | Agent acts on behalf of a user |
| External service accepts OIDC tokens | External service requires OAuth |
| You want no secrets to manage | You need user consent flows |
| M2M authentication | User delegation |

## Prerequisites

- AWS account with appropriate permissions
- Python 3.10+ installed
- AWS CLI configured (`aws configure`)
- bedrock-agentcore-starter-toolkit installed
- boto3 >= 1.35.0 (for new STS APIs)

## Installation

```bash
# Create project directory
mkdir agentcore-aws-jwt-demo
cd agentcore-aws-jwt-demo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit strands-agents boto3 pyjwt

# Verify boto3 version (must be >= 1.35.0)
python -c "import boto3; print(f'boto3 version: {boto3.__version__}')"
```

## Step 1: Create Agent Code

Create `agent.py`:

```python
"""AgentCore AWS IAM JWT Demo: M2M Authentication without Secrets"""
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_iam_access_token

app = BedrockAgentCoreApp()

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


@tool
@requires_iam_access_token(
    audience=["https://api.example.com"],
    signing_algorithm="ES384",
    duration_seconds=300,
)
def authenticate_external_service(*, access_token: str = "") -> str:
    """Authenticate with external service using AWS IAM JWT.

    This tool automatically obtains an AWS-signed JWT token.
    No parameters needed - just call this tool to authenticate.
    """
    import jwt

    # Decode without verification to inspect claims (for demo)
    # In production, the external service verifies the signature
    decoded = jwt.decode(access_token, options={"verify_signature": False})

    return (
        f"✅ AWS IAM JWT Token Obtained!\n\n"
        f"Token Length: {len(access_token)} characters\n"
        f"Issuer: {decoded.get('iss')}\n"
        f"Audience: {decoded.get('aud')}\n"
        f"Subject (IAM Role): {decoded.get('sub')}\n"
        f"Expires: {decoded.get('exp')}\n\n"
        f"This JWT is signed by AWS STS and can be verified by any service "
        f"that fetches the JWKS from the issuer's well-known endpoint."
    )


@app.entrypoint
async def invoke(payload, context):
    """Main entrypoint"""
    user_message = payload.get("prompt", "")

    agent = Agent(
        model=MODEL_ID,
        system_prompt=(
            "You are a helpful assistant that can authenticate with external services "
            "using AWS IAM JWT federation. When asked about authentication, use the "
            "authenticate_external_service tool - it requires no parameters."
        ),
        tools=[authenticate_external_service]
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
boto3>=1.35.0
pyjwt
```

## Step 2: Configure Agent

```bash
agentcore configure \
  -e agent.py \
  --name aws_jwt_demo \
  --disable-memory
```

**What this does:**

- Creates execution role (or uses provided one)
- Saves configuration to `.bedrock_agentcore.yaml`

## Step 3: Enable AWS IAM JWT Federation

```bash
agentcore identity setup-aws-jwt --audience https://api.example.com
```

**What this does:**

- Enables AWS IAM Outbound Web Identity Federation for your account (one-time, idempotent)
- Stores the audience configuration in `.bedrock_agentcore.yaml`
- Displays the issuer URL for configuring your external service

**Output shows:**

```
╭─────────────────────────────────────────── ✅ Success ───────────────────────────────────────────╮
│ AWS IAM JWT Federation Configured                                                                │
│                                                                                                  │
│ Issuer URL: https://a1b4d687-aba8-487e-b79c-e86e3c217388.tokens.sts.global.api.aws              │
│ Audiences: https://api.example.com                                                               │
│ Algorithm: ES384                                                                                 │
│ Duration: 300s                                                                                   │
│                                                                                                  │
│ Next Steps:                                                                                      │
│ 1. Configure your external service to trust this issuer URL                                      │
│ 2. Run agentcore launch to deploy (IAM permissions auto-added)                                   │
│ 3. Use @requires_iam_access_token(audience=[...]) in your agent                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯

⚠️  External Service Configuration Required

Your external service must be configured to:
  1. Trust issuer: https://a1b4d687-aba8-487e-b79c-e86e3c217388.tokens.sts.global.api.aws
  2. Validate audience: https://api.example.com
  3. Fetch JWKS from: https://a1b4d687-aba8-487e-b79c-e86e3c217388.tokens.sts.global.api.aws/.well-known/jwks.json
```

**To add more audiences later:**

```bash
agentcore identity setup-aws-jwt --audience https://api2.example.com
```

## Step 4: Verify Configuration

```bash
agentcore identity list-aws-jwt
```

**Output shows:**

```
                     AWS IAM JWT Federation Configuration
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property           ┃ Value                                                  ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Enabled            │ ✅ Yes                                                 │
│ Issuer URL         │ https://a1b4d687-...tokens.sts.global.api.aws         │
│ Signing Algorithm  │ ES384                                                  │
│ Duration (seconds) │ 300                                                    │
│ Audiences          │ https://api.example.com                                │
└────────────────────┴────────────────────────────────────────────────────────┘
```

## Step 5: Deploy Agent

```bash
agentcore launch
```

**What happens during launch:**

- Agent code deployed
- Runtime instance created
- **IAM permissions automatically added** for AWS JWT:
  - `sts:GetWebIdentityToken` with audience condition
  - `sts:TagGetWebIdentityToken` for custom claims
- Agent endpoint created

**Look for this in the output:**

```
✅ AWS IAM JWT permissions added automatically
   Audiences: https://api.example.com
```

## Step 6: Invoke the Agent

```bash
agentcore invoke '{"prompt": "Please authenticate with the external service"}'
```

**Expected Response:**

```
✅ AWS IAM JWT Token Obtained!

Token Length: 960 characters
Issuer: https://a1b4d687-aba8-487e-b79c-e86e3c217388.tokens.sts.global.api.aws
Audience: https://api.example.com
Subject (IAM Role): arn:aws:sts::123456789012:assumed-role/AgentCoreExecutionRole/...
Expires: 1700000300

This JWT is signed by AWS STS and can be verified by any service
that fetches the JWKS from the issuer's well-known endpoint.
```

**No authorization flow needed!** The token is obtained automatically.

## Understanding the JWT Claims

The AWS IAM JWT contains these claims:

```json
{
  "iss": "https://a1b4d687-aba8-487e-b79c-e86e3c217388.tokens.sts.global.api.aws",
  "aud": "https://api.example.com",
  "sub": "arn:aws:sts::123456789012:assumed-role/AgentCoreExecutionRole/...",
  "iat": 1700000000,
  "exp": 1700000300,
  "jti": "unique-token-id",
  "https://sts.amazonaws.com/": {
    "aws_account": "123456789012",
    "source_region": "us-west-2"
  }
}
```

## Cleanup

```bash
# Destroy agent
agentcore destroy --agent aws_jwt_demo --force
```

**Note:** AWS IAM JWT federation enablement is account-wide and typically doesn't need cleanup. The IAM inline policy (`AgentCoreAwsJwtAccess`) is deleted with the agent's execution role.

## Troubleshooting

### "FeatureDisabledException" error

**Cause**: AWS IAM JWT federation not enabled for the account

**Fix**: Run `agentcore identity setup-aws-jwt --audience <url>`

### "AccessDenied" when getting token

**Cause**: IAM policy doesn't allow the audience

**Fix**:
1. Re-run `agentcore launch` to update IAM policy, or
2. Manually add the STS permission to your execution role

### "No AWS region configured" error

**Cause**: Region not set

**Fix**: Specify `--region` or configure AWS CLI:
```bash
aws configure set region us-west-2
```

### Token audience doesn't match

**Cause**: External service expects different audience value

**Fix**: Add the correct audience:
```bash
agentcore identity setup-aws-jwt --audience https://correct-audience.example.com
agentcore launch  # Re-deploy to update IAM policy
```

### External service rejects the JWT

**Cause**: External service not configured to trust AWS issuer

**Fix**: Configure your external service with:
1. Issuer URL from `agentcore identity list-aws-jwt`
2. JWKS URL: `{issuer_url}/.well-known/jwks.json`

### boto3 too old

**Cause**: boto3 doesn't have the new STS API

**Fix**: Upgrade boto3:
```bash
pip install --upgrade boto3 botocore
```

## Decorator Reference

```python
@requires_iam_access_token(
    audience=["https://api.example.com"],  # Required: list of audiences
    signing_algorithm="ES384",              # Optional: ES384 (default) or RS256
    duration_seconds=300,                   # Optional: 60-3600, default 300
    tags=[{"Key": "env", "Value": "prod"}], # Optional: custom JWT claims
    into="access_token",                    # Optional: parameter name for token
)
def my_function(*, access_token: str = "") -> str:
    # access_token contains the AWS-signed JWT
    ...
```

**Important:** Use `access_token: str = ""` (with default value) so the LLM doesn't ask for it.

## Summary

You've built an agent with:

- ✅ AWS IAM JWT federation enabled (one-time account setup)
- ✅ Automatic JWT token acquisition
- ✅ No secrets to manage
- ✅ Automatic IAM permission management
- ✅ Secretless M2M authentication
