# Using AgentCore Identity for OAuth Token Management (Self-Hosted Agent)

Amazon Bedrock AgentCore Identity provides a secure way to manage OAuth token flows for your AI agents. If your agent needs to access third-party services on behalf of users, you'd normally have to build OAuth authorization flows, token storage, refresh logic, and secret management yourself. AgentCore Identity handles all of that for you.

## What You'll Build

You'll create a local Python agent that uses AgentCore Identity to obtain an OAuth 2.0 access token on behalf of a user. The agent never touches the OAuth provider directly - AgentCore Identity handles the authorization code exchange, token storage, and refresh behind the scenes.

## Key Concepts

- **Credential provider**: Tells AgentCore Identity how to talk to your OAuth server (discovery URL, client ID/secret).
- **Workload identity**: Represents your agent. AgentCore issues workload tokens that your agent uses to request OAuth tokens.
- **Session binding**: After the user authorizes in the browser, your app calls `completeResourceTokenAuth` to bind the OAuth session to the user — so the agent can retrieve the token.

## Prerequisites

Before you begin, ensure you have:

- An AWS account with appropriate permissions (IAM, Cognito, and Bedrock AgentCore access)
- Python 3.10+ installed
- The latest AWS CLI installed
- `jq` installed

Authenticate with AWS:

```bash
# If you have AWS IAM Identity Center (SSO) configured:
aws sso login

# If you use the AWS console login:
aws login
```

Verify your credentials are working:

```bash
aws sts get-caller-identity
```

Set your region (if not already configured):

```bash
export AWS_REGION="us-east-1"
```

> **Note:** All commands in this guide assume `us-east-1`. Replace with your preferred region if needed.

## Install the SDK and Dependencies

```bash
mkdir agentcore-identity-quickstart
cd agentcore-identity-quickstart

python3 -m venv .venv
source .venv/bin/activate

pip install boto3 bedrock-agentcore pyjwt strands-agents strands-agents-builder botocore[crt]
```

## Step 1: Create a Cognito User Pool

This quickstart requires an OAuth authorization server. If you already have one with a client ID, client secret, and a test user configured, skip to Step 2 and set the `ISSUER_URL`, `CLIENT_ID`, and `CLIENT_SECRET` environment variables with your values.

If you do not have one, this script creates an Amazon Cognito user pool to use as the authorization server. You may save it as `create_cognito.sh` or paste it directly into your terminal.

```bash
#!/bin/bash

REGION=$(aws configure get region)

USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name AgentCoreIdentityQuickStartPool \
  --query 'UserPool.Id' \
  --no-cli-pager \
  --output text)

DOMAIN_NAME="agentcore-quickstart-$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 5)"
aws cognito-idp create-user-pool-domain \
  --domain $DOMAIN_NAME \
  --no-cli-pager \
  --user-pool-id $USER_POOL_ID > /dev/null

CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name AgentCoreQuickStart \
  --generate-secret \
  --callback-urls "https://bedrock-agentcore.$REGION.amazonaws.com/identities/oauth2/callback" \
  --allowed-o-auth-flows "code" \
  --allowed-o-auth-scopes "openid" "profile" "email" \
  --allowed-o-auth-flows-user-pool-client \
  --supported-identity-providers "COGNITO" \
  --query 'UserPoolClient.{ClientId:ClientId,ClientSecret:ClientSecret}' \
  --output json)

CLIENT_ID=$(echo $CLIENT_RESPONSE | jq -r '.ClientId')
CLIENT_SECRET=$(echo $CLIENT_RESPONSE | jq -r '.ClientSecret')

USERNAME="AgentCoreTestUser$(printf "%04d" $((RANDOM % 10000)))"
PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 16)Aa1!"

aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --output text > /dev/null

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --password $PASSWORD \
  --output text \
  --permanent > /dev/null

ISSUER_URL="https://cognito-idp.$REGION.amazonaws.com/$USER_POOL_ID/.well-known/openid-configuration"
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Client Secret: $CLIENT_SECRET"
echo "Issuer URL: $ISSUER_URL"
echo "Test User: $USERNAME"
echo "Test Password: $PASSWORD"
echo ""
echo "export USER_POOL_ID='$USER_POOL_ID'"
echo "export CLIENT_ID='$CLIENT_ID'"
echo "export CLIENT_SECRET='$CLIENT_SECRET'"
echo "export ISSUER_URL='$ISSUER_URL'"
echo "export COGNITO_USERNAME='$USERNAME'"
echo "export COGNITO_PASSWORD='$PASSWORD'"
```

Copy and paste the export lines printed by the script into your terminal.

## Step 2: Create a Credential Provider

Credential providers tell AgentCore Identity how to interact with your OAuth authorization server on behalf of your agent.

If you are using your own authorization server, set `ISSUER_URL`, `CLIENT_ID`, and `CLIENT_SECRET` with your values. If you used the Cognito script from Step 1, the exports are already set.

```bash
#!/bin/bash

OAUTH2_CREDENTIAL_PROVIDER_RESPONSE=$(aws bedrock-agentcore-control create-oauth2-credential-provider \
  --name "AgentCoreIdentityStandaloneProvider" \
  --credential-provider-vendor "CustomOauth2" \
  --oauth2-provider-config-input '{
    "customOauth2ProviderConfig": {
      "oauthDiscovery": {
        "discoveryUrl": "'$ISSUER_URL'"
      },
      "clientId": "'$CLIENT_ID'",
      "clientSecret": "'$CLIENT_SECRET'"
    }
  }' \
  --output json)

OAUTH2_CALLBACK_URL=$(echo $OAUTH2_CREDENTIAL_PROVIDER_RESPONSE | jq -r '.callbackUrl')
echo "OAuth2 Callback URL: $OAUTH2_CALLBACK_URL"
echo ""
echo "export OAUTH2_CALLBACK_URL='$OAUTH2_CALLBACK_URL'"
```

Copy and paste the export line into your terminal.

Update the Cognito user pool client with the credential provider's callback URL:

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --callback-urls "https://bedrock-agentcore.$REGION.amazonaws.com/identities/oauth2/callback" "$OAUTH2_CALLBACK_URL" \
  --allowed-o-auth-flows "code" \
  --allowed-o-auth-scopes "openid" "profile" "email" \
  --allowed-o-auth-flows-user-pool-client \
  --supported-identity-providers "COGNITO" > /dev/null
```

## Step 3: Create a Workload Identity

A workload identity tells AgentCore Identity who is requesting tokens. For local development, register `http://127.0.0.1:8080/callback` as the allowed return URL.

```bash
aws bedrock-agentcore-control create-workload-identity \
  --name "standalone-agent-identity"

aws bedrock-agentcore-control update-workload-identity \
  --name "standalone-agent-identity" \
  --allowed-resource-oauth2-return-urls "http://127.0.0.1:8080/callback"
```

## Step 4: Create the Sample Agent

This single file contains both the agent and a minimal web application. The agent uses AgentCore Identity to initiate an OAuth 2.0 grant. The web application handles the session binding callback — in production, this would be your user-facing web app (e.g., `https://myagentapp.com`) and your web application would likely be separate from your agent.

For local development, the web app listens on `http://127.0.0.1:8080`.

Create a file named `agent.py`:

```python
import json
import os
import sys
import time
import base64
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import boto3

# ---------------------------------------------------------------------------
# Configuration — all values can be overridden via environment variables.
# ---------------------------------------------------------------------------
REGION = os.environ.get("AWS_REGION", "us-east-1")
CREDENTIAL_PROVIDER = os.environ.get("CREDENTIAL_PROVIDER_NAME", "AgentCoreIdentityStandaloneProvider")
USER_ID = os.environ.get("AGENT_USER_ID", "quickstart-user")
CALLBACK_PORT = int(os.environ.get("CALLBACK_PORT", "8080"))
CALLBACK_URL = f"http://127.0.0.1:{CALLBACK_PORT}/callback"

# The control-plane client manages long-lived resources like credential
# providers and workload identities.
control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

# The data-plane client handles runtime operations: issuing workload tokens,
# initiating OAuth flows, and retrieving access tokens.
data_client = boto3.client("bedrock-agentcore", region_name=REGION)

# Shared flag — the callback handler sets this to True once the user has
# completed authorization in the browser, so the agent can stop polling.
authorization_complete = threading.Event()


# ---------------------------------------------------------------------------
# Web application (session binding handler)
#
# This minimal HTTP server handles the OAuth callback redirect. After the
# user authorizes in the browser, AgentCore Identity redirects here with a
# session_id. The handler calls completeResourceTokenAuth to bind the OAuth
# session to the user — so the agent can later retrieve the access token.
#
# In production, this would be your real web app (e.g. https://myagentapp.com).
# For local development, plain HTTP on 127.0.0.1 works fine.
# ---------------------------------------------------------------------------

class AppHandler(BaseHTTPRequestHandler):
    """Handles the OAuth 2.0 session binding callback from AgentCore Identity."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        # AgentCore Identity appends ?session_id=... to the callback URL.
        session_id = parse_qs(parsed.query).get("session_id", [None])[0]
        if not session_id:
            self._respond(400, "<h1>Error</h1><p>Missing session_id</p>")
            return

        try:
            # This is the key call: it tells AgentCore Identity that the user
            # has authorized, binding the OAuth session to this user ID.
            data_client.complete_resource_token_auth(
                sessionUri=session_id, userIdentifier={"userId": USER_ID},
            )
            self._respond(200,
                "<h1>Authorization Complete!</h1>"
                "<p>Token stored in AgentCore Identity. You can close this tab.</p>")
            print(f"[INFO]  Session bound for session_id={session_id[:20]}...")

            # Signal the agent's polling loop that authorization is done.
            authorization_complete.set()
        except Exception as exc:
            self._respond(500, f"<h1>Error</h1><pre>{exc}</pre>")

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(f"<html><body>{body}</body></html>".encode())

    def log_message(self, format, *args):
        pass  # Suppress default HTTP request logging.


def start_app_server():
    """Start the local callback server in the background."""
    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), AppHandler)
    print(f"[INFO]  App server listening on http://127.0.0.1:{CALLBACK_PORT}/callback")
    server.serve_forever()


# ---------------------------------------------------------------------------
# Agent logic
# ---------------------------------------------------------------------------

def ensure_workload_identity(name="standalone-agent-identity"):
    """Check if the workload identity exists; create it if not."""
    try:
        control_client.get_workload_identity(name=name)
        print(f"[INFO]  Workload identity '{name}' exists — reusing.")
    except control_client.exceptions.ResourceNotFoundException:
        control_client.create_workload_identity(name=name)
        print(f"[INFO]  Workload identity '{name}' created.")
    return name


def decode_jwt(token):
    """Decode a JWT payload without verifying the signature (for display only)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def run_agent():
    print("=" * 60)
    print("  AgentCore Identity — Local Agent")
    print("=" * 60)

    # Step A: Ensure the workload identity exists.
    workload_name = ensure_workload_identity()

    # Step B: Get a short-lived workload token. This token identifies the
    # agent (not the end user) and is used to request OAuth tokens.
    token = data_client.get_workload_access_token_for_user_id(
        workloadName=workload_name, userId=USER_ID,
    )["workloadAccessToken"]

    # Step C: Ask AgentCore Identity to start an OAuth 2.0 authorization
    # code flow. Because forceAuthentication=True, this always returns an
    # authorizationUrl the user must visit — even if a cached token exists.
    response = data_client.get_resource_oauth2_token(
        workloadIdentityToken=token,
        resourceCredentialProviderName=CREDENTIAL_PROVIDER,
        scopes=["openid", "profile", "email"],
        oauth2Flow="USER_FEDERATION",
        forceAuthentication=True,
        resourceOauth2ReturnUrl=CALLBACK_URL,
    )

    auth_url = response.get("authorizationUrl")
    session_uri = response.get("sessionUri")

    if auth_url:
        # Automatically open the authorization URL in the user's default browser.
        print(f"\n  Opening your browser to authorize...\n\n  {auth_url}\n")
        webbrowser.open(auth_url)

        # Poll until the callback handler signals that authorization is complete,
        # rather than requiring the user to manually press Enter.
        print("  Waiting for you to complete authorization in the browser...")
        while not authorization_complete.wait(timeout=2):
            pass  # Keep waiting in 2-second intervals.
        print("[INFO]  Authorization callback received.")

        # Step D: Get a fresh workload token (the previous one may have expired
        # while the user was authorizing in the browser).
        token = data_client.get_workload_access_token_for_user_id(
            workloadName=workload_name, userId=USER_ID,
        )["workloadAccessToken"]

        # Step E: Now retrieve the actual OAuth access token. This time
        # forceAuthentication=False, so AgentCore returns the token that was
        # stored when the user completed the browser flow.
        response = data_client.get_resource_oauth2_token(
            workloadIdentityToken=token,
            resourceCredentialProviderName=CREDENTIAL_PROVIDER,
            scopes=["openid", "profile", "email"],
            oauth2Flow="USER_FEDERATION",
            forceAuthentication=False,
            resourceOauth2ReturnUrl=CALLBACK_URL,
            sessionUri=session_uri,
        )

    access_token = response.get("accessToken")
    if not access_token:
        print("[ERROR] No access token received. Re-run and complete browser authorization.")
        sys.exit(1)

    # The agent now has an OAuth access token for the user.
    # AgentCore Identity handled the entire OAuth flow — authorization code
    # exchange, token storage, and session binding — so you didn't have to
    # write any OAuth code yourself.
    print()
    print("=" * 60)
    print("  Access token retrieved!")
    print()
    print("  Your agent now has consent to act on behalf of the user.")
    print("  AgentCore Identity handled the entire OAuth flow for you —")
    print("  no OAuth code required.")
    print("=" * 60)
    print()
    print(f"  Token preview: {access_token[:50]}...{access_token[-10:]}")

    claims = decode_jwt(access_token)
    if claims:
        print()
        print(json.dumps(claims, indent=2))

    print()
    print("[INFO]  Done. The OAuth flow completed successfully.")


if __name__ == "__main__":
    # Start the callback server in a background thread, then run the agent.
    threading.Thread(target=start_app_server, daemon=True).start()
    run_agent()
```

## Step 5: Run the Agent

Set the required environment variables and run:

```bash
export CREDENTIAL_PROVIDER_NAME="AgentCoreIdentityStandaloneProvider"
export AWS_REGION="us-east-1"
export AGENT_USER_ID="quickstart-user"

python3 agent.py
```

## Step 6: Test the OAuth Flow

1. The agent automatically opens the OAuth authorization URL in your default browser.
2. Log in with the Cognito test user credentials (`COGNITO_USERNAME` / `COGNITO_PASSWORD` from Step 1).
3. Your browser redirects to `http://127.0.0.1:8080/callback`. You should see "Authorization Complete!".
4. The agent automatically detects the callback and retrieves the access token.

> **Note:** If your browser doesn't open automatically, copy the URL printed in the terminal and open it manually. If you interrupt the agent without completing authorization, re-run it to get a new authorization URL.

### Expected Output

```
============================================================
  AgentCore Identity — Local Agent
============================================================

[INFO]  App server listening on http://127.0.0.1:8080/callback
[INFO]  Workload identity 'standalone-agent-identity' exists — reusing.

  Opening your browser to authorize...

  https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/authorize?...

  Waiting for you to complete authorization in the browser...
[INFO]  Session bound for session_id=ZGQxN2ZlYjEtODcy...
[INFO]  Authorization callback received.

============================================================
  Access token retrieved!

  Your agent now has consent to act on behalf of the user.
  AgentCore Identity handled the entire OAuth flow for you —
  no OAuth code required.
============================================================

  Token preview: eyJraWQiOiJxT0x0VGFhcVwiLCJhbGciOiJSUzI1...QuickStart

{
  "sub": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "cognito:username": "AgentCoreTestUser1234",
  "token_use": "access",
  "auth_time": 1234567890,
  "exp": 1234571490
}

[INFO]  Done. The OAuth flow completed successfully.
```

## Clean Up

```bash
aws bedrock-agentcore-control delete-workload-identity --name "standalone-agent-identity"
aws bedrock-agentcore-control delete-oauth2-credential-provider --name "AgentCoreIdentityStandaloneProvider"
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
```

## Security Best Practices

1. **Never hardcode credentials** in your agent code.
2. **Use `aws sso login` or environment variables** for AWS credentials.
3. **Apply least-privilege IAM policies** scoped to specific resources.
4. **Use a proper TLS certificate** from a trusted CA in production.
5. **Rotate OAuth client secrets** periodically.
6. **Audit access logs** via CloudTrail.
7. **In production**, the application server should validate user sessions before calling `CompleteResourceTokenAuth`.

## Troubleshooting

### `NoCredentialProviders` or `ExpiredToken`

**Cause**: AWS credentials are missing or expired.

**Fix**: Re-run `aws sso login` or `aws login` and try again.

### `ResourceNotFoundException` on workload identity

**Cause**: The workload identity was deleted or never created.

**Fix**: Re-run the Step 3 commands to recreate it.

### Browser shows `error=redirect_mismatch`

**Cause**: The Cognito callback URLs don't include the AgentCore credential provider's callback URL.

**Fix**: Re-run the `update-user-pool-client` command from Step 2.

### No access token received

**Cause**: You closed the browser before completing authorization.

**Fix**: Re-run `python3 agent.py` to get a fresh authorization URL.

### Port 8080 already in use

**Cause**: Another process is using port 8080.

**Fix**: Either stop that process, or set `export CALLBACK_PORT=9090` and update the workload identity's allowed return URLs to match.

### `InvalidParameterException` on `create-user-pool-domain`

**Cause**: The domain name is already taken.

**Fix**: Re-run the script — it generates a random suffix each time.
