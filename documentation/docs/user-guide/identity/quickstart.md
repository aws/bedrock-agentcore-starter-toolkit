# Getting Started with AgentCore Identity

Amazon Bedrock AgentCore Identity provides a secure way to manage identities for your AI agents and enable authenticated access to external services. This guide will help you get started with implementing identity features in your agent applications.

## Prerequisites

Before you begin, ensure you have:

- An AWS account with appropriate permissions
- Python 3.10+ installed
- The latest AWS CLI installed
- AWS credentials and region configured (`aws configure`)
- `jq` installed

This quickstart requires that you have an OAuth 2.0 authorization server. If you do not have one, Step 0.5 will create one for you using Amazon Cognito user pools. If you have an OAuth 2.0 authorization server with a client id, client secret, and a user configured, you may proceed to step 1. This authorization server will act as a resource credential provider, representing the authority that grants the agent an outbound OAuth 2.0 access token.

## Install the SDK and dependencies

Make a folder for this guide, create a Python virtual environment, and install the AgentCore SDK and the aws Python SDK (boto3)

```bash
mkdir agentcore-identity-quickstart
cd agentcore-identity-quickstart
python3 -m venv .venv
source .venv/bin/activate
pip install bedrock-agentcore boto3 strands-agents bedrock-agentcore-starter-toolkit pyjwt
```

Also create the `requirements.txt` file with the following content. This will be used later by the AgentCore deployment tool.

```
bedrock-agentcore
boto3
pyjwt
strands-agents
bedrock-agentcore-starter-toolkit
```

## Step 0.5: Create a Cognito user pool

This quickstart requires an OAuth 2.0 authorization server. If you do not have one available for testing, or if you want to keep your test separate from your authorization server, this script will use your AWS credentials to set up an Amazon Cognito instance for you to use as an authorization server. The script will create:

   * A Cognito user pool
   * An OAuth 2.0 client, and client secret for that user pool
   * A test user and password in that Cognito user pool


Deleting the Cognito user pool AgentCoreIdentityQuickStartPool will delete the associated client_id and user as well.

You may choose to save this script as `create_cognito.sh` and execute it from your command line, or paste the script into your command line.

```bash
#!/bin/bash

REGION=$(aws configure get region)

# Create user pool
USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name AgentCoreIdentityQuickStartPool \
  --query 'UserPool.Id' \
  --no-cli-pager \
  --output text)

# Create user pool domain
DOMAIN_NAME="agentcore-quickstart-$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 5)"
aws cognito-idp create-user-pool-domain \
  --domain $DOMAIN_NAME \
  --no-cli-pager \
  --user-pool-id $USER_POOL_ID > /dev/null

# Create user pool client with secret and hosted UI settings
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

# Generate random username and password
USERNAME="AgentCoreTestUser$(printf "%04d" $((RANDOM % 10000)))"
PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9!@#$%^&*()_+-=[]{}|;:,.<>?' < /dev/urandom | head -c 16)$(LC_ALL=C tr -dc '0-9' < /dev/urandom | head -c 1)"

# Create user with permanent password
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --output text > /dev/null

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --password $PASSWORD \
  --output text > /dev/null \
  --permanent

# Get region

ISSUER_URL="https://cognito-idp.$REGION.amazonaws.com/$USER_POOL_ID/.well-known/openid-configuration"
HOSTED_UI_URL="https://$DOMAIN_NAME.auth.$REGION.amazoncognito.com"

# Output results
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Client Secret: $CLIENT_SECRET"
echo "Issuer URL: $ISSUER_URL"
echo "Hosted UI URL: $HOSTED_UI_URL"
echo "Test User: $USERNAME"
echo "Test Password: $PASSWORD"

echo ""
echo "# Copy and paste these exports to set environment variables for later use:"
echo "export USER_POOL_ID='$USER_POOL_ID'"
echo "export CLIENT_ID='$CLIENT_ID'"
echo "export CLIENT_SECRET='$CLIENT_SECRET'"
echo "export ISSUER_URL='$ISSUER_URL'"
echo "export HOSTED_UI_URL='$HOSTED_UI_URL'"
echo "export COGNITO_USERNAME='$USERNAME'"
echo "export COGNITO_PASSWORD='$PASSWORD'"

```

## Step 1: Create a credential provider

Credential providers are how your agent accesses external services. Create a credential provider and configure it with an OAuth 2.0 client for your authorization server.

If you are using your own authorization server, set the environment variables `ISSUER_URL`, `CLIENT_ID`, and `CLIENT_SECRET` with their appropriate values from your authorization server. If you are using the previous script to create an authorization server for you with Cognito, copy the EXPORT statements from the output into your terminal to set the environment variables.

This credential provider will be used by your agent's code to get access tokens to act on behalf of your user.




```bash
#!/bin/bash
# please note the expected ISSUER_URL format for Bedrock AgentCore is the full url, including .well-known/openid-configuration
OAUTH2_CREDENTIAL_PROVIDER_RESPONSE=$(aws bedrock-agentcore-control create-oauth2-credential-provider \
  --name "AgentCoreIdentityQuickStartProvider" \
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
echo "# Copy and paste these exports to set environment variables for later use:"
echo "export OAUTH2_CALLBACK_URL='$OAUTH2_CALLBACK_URL'"

```


## Step 1.5: Add the callback URL to your OAuth 2.0 authorization server

To prevent unauthorized redirects, add the callback URL retrieved from [CreateOauth2CredentialProvider](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateOauth2CredentialProvider.html) or [GetOauth2CredentialProvider](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_GetOauth2CredentialProvider.html) to your OAuth 2.0 authorization server.

If you are using your own authorization server, configure the OAuth2 credential provider callback URL in your authorization server callback URL settings. 

If you are using the previous script to create an authorization server with Cognito, copy the EXPORT statements from the output into your terminal to set the environment variables and update the Cognito user pool client with the OAuth2 credential provider callback URL.


```bash
#!/bin/bash

aws cognito-idp update-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-id $CLIENT_ID \
    --client-name AgentCoreQuickStart \
    --allowed-o-auth-flows "code" \
    --allowed-o-auth-scopes "openid" "profile" "email" \
    --allowed-o-auth-flows-user-pool-client \
    --supported-identity-providers "COGNITO" \
    --callback-urls "$OAUTH2_CALLBACK_URL"
```

## Step 2: Create a sample agent that initiates an OAuth 2.0 flow

**Prerequisite**: An OAuth2 callback URL must be configured on the workload identity during creation via [CreateWorkloadIdentity](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateWorkloadIdentity.html) or updated using [UpdateWorkloadIdentity](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_UpdateWorkloadIdentity.html) to handle the session binding flow. For more details, see [OAuth2 Authorization URL Session Binding](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/oauth2-authorization-url-session-binding.html).

The `requires_access_token` usage must set the `callback_url` to the same value configured on the workload identity. This is not required when launching and invoking the agent **locally**, as the configuration is done automatically by the starter toolkit.

In this step, we will create an agent that initiates an OAuth 2.0 authorization flow to get tokens to act on behalf of the user. For simplicity, the agent will not make actual calls to external services on behalf of a user, but will prove to us that it has obtained consent to act on behalf of our test user.


### Agent code

Create a file named `agentcoreidentityquickstart.py`, and save this code.

```python
"""
AgentCore Identity Outbound Token Agent

This agent demonstrates the USER_FEDERATION OAuth 2.0 flow.

It handles the OAuth 2.0 user consent flow and inspects the resulting OAuth 2.0 access token.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity import requires_access_token
import asyncio
import jwt
import logging

app = BedrockAgentCoreApp()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def decode_jwt(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        return {"error": f"Error decoding JWT: {str(e)}"}

class StreamingQueue:
    def __init__(self):
        self.finished = False
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def finish(self):
        self.finished = True
        await self.queue.put(None)

    async def stream(self):
        while True:
            item = await self.queue.get()
            if item is None and self.finished:
                break
            yield item

queue = StreamingQueue()

async def handle_auth_url(url):
    await queue.put(f"Authorization URL, please copy to your preferred browser: {url}")

@requires_access_token(
    provider_name="AgentCoreIdentityQuickStartProvider",
    scopes=["openid"],
    auth_flow="USER_FEDERATION",
    on_auth_url=handle_auth_url, # streams authorization URL to client
    force_authentication=True
    callback_url='<insert_oauth2_callback_url_for_session_binding; not required for *local* agent launch and invocations>'
)
async def introspect_with_decorator(*, access_token: str):
    """Introspect token using decorator"""
    logger.info("Inside introspect_with_decorator - decorator succeeded")
    await queue.put({
        "message": "Successfully received an access token to act on behalf of your user!",
        "token_claims": decode_jwt(access_token),
        "token_length": len(access_token),
        "token_preview": f"{access_token[:50]}...{access_token[-10:]}"
    })
    await queue.finish()

@app.entrypoint
async def agent_invocation(payload, context):
    """Handler that uses only the decorator approach"""
    logger.info("Agent invocation started")

    # Start the agent task and immediately begin streaming
    task = asyncio.create_task(introspect_with_decorator())

    # Stream items as they come in
    async for item in queue.stream():
        yield item

    # Wait for task completion
    await task


if __name__ == "__main__":
    app.run()


```

## Step 3:  Deploy the agent to AgentCore Runtime

We will host this agent on AgentCore Runtime. We can do this easily with the AgentCore SDK we installed earlier.

From your terminal, run `agentcore configure -e agentcoreidentityquickstart.py` and `agentcore launch` . The deployment will work with the defaults set by `agentcore configure`, but you may customize them. Ensure that you select "No" for the `Configure OAuth authorizer instead` step. We want to use IAM authorization for this guide.

### Update the IAM policy of the agent to be able to access the token vault, and client secret

You will need to update the IAM policy of your agent that was created by or used with `agentcore configure`. This script will read your agent's configuration YAML and append the appropriate policy. You can copy and paste this script, or save it to a file and execute it.

```bash
#!/bin/bash

# Parse values from .bedrock_agentcore.yaml
EXECUTION_ROLE=$(grep "execution_role:" .bedrock_agentcore.yaml | head -1 | awk '{print $2}')
AWS_ACCOUNT=$(grep "account:" .bedrock_agentcore.yaml | head -1 | awk '{print $2}' | tr -d "'")
REGION=$(grep "region:" .bedrock_agentcore.yaml | awk '{print $2}')

echo "Parsed values:"
echo "Execution Role: $EXECUTION_ROLE"
echo "Account: $AWS_ACCOUNT"
echo "Region: $REGION"

# Create the policy document with proper variable substitution
cat > agentcore-identity-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AccessTokenVault",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetResourceOauth2Token",
        "secretsmanager:GetSecretValue"
      ],
      "Resource": ["arn:aws:bedrock-agentcore:${REGION}:${AWS_ACCOUNT}:workload-identity-directory/default/workload-identity/*",
        "arn:aws:bedrock-agentcore:${REGION}:${AWS_ACCOUNT}:token-vault/default/oauth2credentialprovider/AgentCoreIdentityQuickStartProvider",
        "arn:aws:bedrock-agentcore:${REGION}:${AWS_ACCOUNT}:workload-identity-directory/default",
        "arn:aws:bedrock-agentcore:${REGION}:${AWS_ACCOUNT}:token-vault/default",
        "arn:aws:secretsmanager:${REGION}:${AWS_ACCOUNT}:secret:bedrock-agentcore-identity!default/oauth2/AgentCoreIdentityQuickStartProvider*"
      ]
    }
  ]
}
EOF

# Create the policy
POLICY_ARN=$(aws iam create-policy \
    --policy-name AgentCoreIdentityQuickStartPolicy$(LC_ALL=C tr -dc '0-9' < /dev/urandom | head -c 4) \
    --policy-document file://agentcore-identity-policy.json \
    --query 'Policy.Arn' \
    --output text)

# Extract role name from ARN and attach policy
ROLE_NAME=$(echo $EXECUTION_ROLE | awk -F'/' '{print $NF}')
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN

echo "Policy created and attached: $POLICY_ARN"

# Cleanup
rm agentcore-identity-policy.json
```

## Step 4: Invoke the agent!

Now that this is all set up, you can invoke the agent. For this demo, we will use the `agentcore invoke` command and our IAM credentials. We will need to pass the `--user-id` and `--session-id` arguments when using IAM authentication.

`agentcore invoke "TestPayload" --agent agentcoreidentityquickstart --user-id "SampleUserID" --session-id "ALongThirtyThreeCharacterMinimumSessionIdYouCanChangeThisAsYouNeed"`

The agent will then return a URL to your `agentcore invoke` command. Copy and paste that URL into your preferred browser, and you will then be redirected to your authorization server's login page. The `--user-id` parameter is the user ID you are presenting to AgentCore Identity. The `--session-id` parameter is the session ID, which must be at least 33 characters long.

Enter the username and password for your user on your authorization server when prompted on your browser, or use your preferred authentication method you have configured. If you used the script from Step 0.5 to create a Cognito instance, you can retrieve this from your terminal history.

Your browser should redirect to your configured OAuth2 callback URL, which handles the [session binding flow](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/oauth2-authorization-url-session-binding.html). Ensure your OAuth2 callback server provides clear success and error responses to indicate the authorization status.

Note that if you interrupt an invocation without completing authorization, you may need to request a new URL using a new session ID (`--session-id` parameter).


### Debugging

Should you encounter any errors or unexpected behaviors, the output of the agent is captured in CloudWatch logs. A log tailing command is provided after you run `agentcore launch`

## Clean Up

After you're done, you can delete the Cognito user pool, Amazon ECR repo, CodeBuild Project, IAM roles for the agent and CodeBuild project, and finally delete the agent, and credential provider.

## Security Best Practices

When working with identity information:

1. **Never hardcode credentials** in your agent code
2. **Use environment variables or AWS Secrets Manager** for sensitive information
3. **Apply least privilege principle** when configuring IAM permissions
4. **Regularly rotate credentials** for external services
5. **Audit access logs** to monitor agent activity
6. **Implement proper error handling** for authentication failures
