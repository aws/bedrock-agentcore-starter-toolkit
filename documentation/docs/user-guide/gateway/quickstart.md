# QuickStart: A Fully Managed MCP Server in 5 Minutes! 🚀

Amazon Bedrock AgentCore Gateway provides an easy and secure way for developers to build, deploy, discover, and connect to tools at scale. AI agents need tools to perform real-world tasks—from querying databases to sending messages to analyzing documents. With Gateway, developers can convert APIs, Lambda functions, and existing services into Model Context Protocol (MCP)-compatible tools and make them available to agents through Gateway endpoints with just a few lines of code. Gateway supports OpenAPI, Smithy, and Lambda as input types, and is the only solution that provides both comprehensive ingress authentication and egress authentication in a fully-managed service. Gateway eliminates weeks of custom code development, infrastructure provisioning, and security implementation so developers can focus on building innovative agent applications.

In this quick start guide you will learn how to set up a Gateway and integrate it into your agents using the AgentCore Starter Toolkit. You can find more comprehensive guides and examples [**here**](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/02-AgentCore-gateway).

**Note: The AgentCore Starter Toolkit is intended to help developers get started quickly. The Boto3 Python library provides the most comprehensive set of operations for Gateways and Targets. You can find the Boto3 documentation [here](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html). For complete documentation see the [**developer guide**](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)**

## Prerequisites

⚠️ Before starting, make sure you have:

- **AWS Account** with credentials configured (`aws configure`)
- **Python 3.10+** installed
- **IAM Permissions** for creating roles, Lambda functions, and using Bedrock AgentCore
- **Model Access** - Enable Anthropic’s Claude Sonnet 3.7 in the Bedrock console (or another model for the demo agent)

## Step 1: Setup and Install

```bash
mkdir agentcore-gateway-quickstart
cd agentcore-gateway-quickstart
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Install Dependencies**

```bash
pip install boto3
pip install bedrock-agentcore-starter-toolkit
pip install strands-agents
```

## Step 2: Create and Configure Your Gateway

Creates a fully managed MCP server (Gateway) that transforms AWS Lambda functions into AI-accessible tools. The Gateway handles authentication, protocol translation, and provides a single endpoint for your agent to discover and use tools.

Save this as `setup_gateway.py`:

```python
"""
setup_gateway.py - Create and configure your Gateway with proper IAM permissions
Run this first to set up your Gateway infrastructure
"""

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import boto3
import json
import logging
import time

# ============= CONFIGURATION =============
# IMPORTANT: Set your AWS region here
REGION = "us-west-2"  # Change to your preferred region

def fix_gateway_role_trust_policy(role_name, account_id, region):
    """Ensure the Gateway role can be assumed by bedrock-agentcore service"""
    iam = boto3.client('iam')

    # Create correct trust policy for bedrock-agentcore
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }

    try:
        # Update the trust policy
        iam.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(trust_policy)
        )

        # Add Lambda invoke permissions
        policy_name = "LambdaInvokePolicy"
        lambda_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": f"arn:aws:lambda:{region}:{account_id}:function:AgentCoreLambdaTestFunction"
                }
            ]
        }

        try:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(lambda_policy)
            )
        except iam.exceptions.EntityAlreadyExistsException:
            pass  # Policy already exists

        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not update role trust policy: {e}")
        return False

def main():
    print(f"\\n📍 Setting up Gateway in region: {REGION}")
    print("=" * 50)

    # Validate AWS credentials
    try:
        sts = boto3.client('sts', region_name=REGION)
        caller_identity = sts.get_caller_identity()
        account_id = caller_identity['Account']
        print(f"✅ AWS Account: {account_id}")
    except Exception as e:
        print("❌ AWS credentials not configured. Run 'aws configure' first")
        exit(1)

    # Initialize the Gateway client
    client = GatewayClient(region_name=REGION)
    client.logger.setLevel(logging.ERROR)  # Reduce verbosity

    try:
        # Step 3.1: Create OAuth authorizer using Cognito
        print("\\n📐 Step 2.1: Creating OAuth authorization...")
        print("   • Setting up Cognito user pool for authentication")
        print("   • This provides secure access to your Gateway")

        cognito_response = client.create_oauth_authorizer_with_cognito("QuickStartGateway")
        print("   ✅ OAuth authorization configured")

        # Step 3.2: Create the Gateway
        print("\\n🚪 Step 2.2: Creating Gateway endpoint...")
        print("   • This is your MCP server URL")
        print("   • Auto-creates IAM execution role if needed")

        gateway = client.create_mcp_gateway(
            authorizer_config=cognito_response["authorizer_config"],
            enable_semantic_search=True  # Enable intelligent tool discovery
        )
        print(f"   ✅ Gateway created: {gateway['gatewayId']}")

        # Fix the auto-created role's trust policy
        role_arn = gateway.get('roleArn')
        if role_arn:
            role_name = role_arn.split('/')[-1]
            print("\\n🔧 Step 2.2.1: Configuring IAM permissions...")
            print("   • Updating role trust policy for bedrock-agentcore")
            print("   • Adding Lambda invoke permissions")

            if fix_gateway_role_trust_policy(role_name, account_id, REGION):
                print("   ✅ IAM permissions configured")
            else:
                print("   ⚠️  Manual IAM configuration may be needed")

        # Step 2.3: Add Lambda target with test tools
        print("\\n🛠️  Step 2.3: Adding Lambda tools...")
        print("   • Creates test Lambda with mock functions")
        print("   • Registers tools: get_weather, get_time")

        lambda_target = client.create_mcp_gateway_target(
            gateway=gateway,
            target_type="lambda"
        )
        print(f"   ✅ Tools added: {lambda_target.get('name', 'TestTarget')}")

        # Step 2.4: Get access token
        print("\\n🔑 Step 2.4: Getting access token...")
        print("   • OAuth token for API authentication")
        print("   • Valid for ~1 hour")

        access_token = client.get_access_token_for_cognito(cognito_response["client_info"])
        print("   ✅ Access token obtained")

        # Step 3.5: Save configuration
        print("\\n💾 Step 3.5: Saving configuration...")
        config = {
            "gateway_url": gateway['gatewayUrl'],
            "gateway_id": gateway['gatewayId'],
            "gateway_role_arn": gateway.get('roleArn', ''),
            "access_token": access_token,
            "region": REGION,
            "target_id": lambda_target['targetId'],
            "target_name": lambda_target.get('name', 'TestGatewayTarget'),
            "client_id": cognito_response["client_info"]["client_id"],
            "client_secret": cognito_response["client_info"]["client_secret"],
            "token_endpoint": cognito_response["client_info"]["token_endpoint"],
            "user_pool_id": cognito_response["client_info"]["user_pool_id"],
            "timestamp": time.time()
        }

        with open("gateway_config.json", "w") as f:
            json.dump(config, f, indent=2)

        print("   ✅ Configuration saved to gateway_config.json")

        # Wait for resources to be ready
        print("\\n⏳ Waiting for resources to be ready (30 seconds)...")
        print("   • DNS propagation")
        print("   • IAM permission propagation")
        print("   • Lambda configuration")
        time.sleep(30)

        print("\\n" + "=" * 50)
        print("✅ GATEWAY SETUP COMPLETE!")
        print("=" * 50)
        print(f"\\n📊 Gateway URL: {gateway['gatewayUrl']}")
        print(f"🔧 Test Tools Available:")
        print(f"   • {lambda_target.get('name', 'Target')}___get_weather (returns: 72°F, Sunny)")
        print(f"   • {lambda_target.get('name', 'Target')}___get_time (returns: 2:30 PM)")
        print(f"\\n👉 Next: Run 'python test_agent.py' to test your Gateway")

    except Exception as e:
        print(f"\\n❌ Setup failed: {e}")
        print("\\nTroubleshooting:")
        print("  • Check AWS credentials: 'aws configure'")
        print("  • Verify IAM permissions for creating resources")
        print("  • Ensure network connectivity to AWS")
        exit(1)

if __name__ == "__main__":
    main()
```

Run it:

```bash
python setup_gateway.py
```

## Step 3: Test Your Gateway with an Interactive Agent

Connects an AI agent (Claude) to your Gateway, enabling it to discover and use the Lambda tools. You'll have an interactive chat where Claude can respond to questions by calling your mock weather and time tools through the MCP protocol.

Save this as `test_agent.py`:

```python
"""
test_agent.py - Interactive agent using your Gateway tools
Run after setup_gateway.py to test your MCP server
"""

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import json
import time
import sys

# Load configuration
try:
    with open("gateway_config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    print("❌ Error: gateway_config.json not found!")
    print("👉 Run 'python setup_gateway.py' first")
    exit(1)

# Model configuration
MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Set your preferred Bedrock model here.

def check_token_age():
    """Check if token is still valid (tokens expire after ~1 hour)"""
    token_age = time.time() - config.get('timestamp', 0)
    if token_age > 3300:  # 55 minutes
        print("⚠️  Token may be expired (>55 minutes old)")
        print("👉 Run 'python setup_gateway.py' again to refresh")
        return False
    return True

def main():
    print("\\n🤖 Starting Interactive Agent")
    print("=" * 50)

    # Check token validity
    if not check_token_age():
        exit(1)

    # Create MCP transport
    def create_transport():
        return streamablehttp_client(
            config['gateway_url'],
            headers={"Authorization": f"Bearer {config['access_token']}"}
        )

    # Initialize Bedrock model
    print(f"📍 Region: {config['region']}")
    bedrock_model = BedrockModel(
        model_id=MODEL_ID,
        streaming=True
    )

    # Connect to Gateway
    mcp_client = MCPClient(create_transport)

    try:
        with mcp_client:
            # Discover available tools
            print("\\n🔍 Discovering tools...")
            tools = []
            pagination_token = None

            while True:
                tmp_tools = mcp_client.list_tools_sync(pagination_token=pagination_token)
                tools.extend(tmp_tools)
                if not tmp_tools.pagination_token:
                    break
                pagination_token = tmp_tools.pagination_token

            # Display discovered tools
            tool_names = [
                tool.tool_name if hasattr(tool, 'tool_name') else tool.name
                for tool in tools
            ]
            print(f"✅ Found {len(tools)} tools:")
            for name in tool_names:
                if '___' in name:
                    # Extract the actual tool name
                    _, tool_part = name.split('___', 1)
                    print(f"   • {tool_part}")
                else:
                    print(f"   • {name}")

            # Create agent with tools
            print("\\n🎯 Initializing agent...")
            agent = Agent(model=bedrock_model, tools=tools)
            print("✅ Agent ready!")

            # Interactive session
            print("\\n" + "=" * 50)
            print("💬 INTERACTIVE SESSION")
            print("=" * 50)
            print("\\nExample questions to try:")
            print("  • What's the weather in Seattle?")
            print("  • What time is it in New York?")
            print("  • Check the weather for London")
            print("\\n📝 Note: These are mock tools with fixed responses")
            print("Type 'exit' to quit\\n")

            while True:
                user_input = input("You: ")

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("\\n👋 Goodbye!")
                    break

                print("\\n🤔 Processing...")

                try:
                    response = agent(user_input)

                    # Extract and display response
                    if hasattr(response, 'message') and 'content' in response.message:
                        content = response.message['content']
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and 'text' in item:
                                    print(f"\\nAgent: {item['text']}")
                                else:
                                    print(f"\\nAgent: {item}")
                        else:
                            print(f"\\nAgent: {content}")
                    else:
                        print(f"\\nAgent: {response}")

                    print()  # Add spacing

                except Exception as e:
                    print(f"\\n❌ Error: {e}")
                    if "401" in str(e) or "Unauthorized" in str(e):
                        print("📝 Token expired. Run 'python setup_gateway.py' to refresh")
                        break
                    print()

    except Exception as e:
        print(f"\\n❌ Failed to connect: {e}")

        if "401 Unauthorized" in str(e):
            print("\\n📝 Authentication failed - token may be expired")
            print("👉 Run 'python setup_gateway.py' to get a new token")
        else:
            print("\\n📝 Troubleshooting tips:")
            print("  • Verify Gateway setup completed successfully")
            print("  • Check network connectivity")
            print("  • Wait a moment for IAM permissions to propagate")

if __name__ == "__main__":
    main()
```

Run it:

```bash
python test_agent.py
```

**Expected Output:**

- Gateway creation takes ~30 seconds
- Interactive agent starts automatically
- You can immediately test with questions
- Configuration is saved for reuse

---
**🥳🥳🥳 Congratulations - you successfully built an agent with MCP tools powered by AgentCore Gateway!**
---


## Adding Real-World APIs

After verifying the basic setup works, add real APIs to your Gateway. This example shows how to add external REST APIs (like weather services) to your Gateway, making them available as tools for your agent.

### Example: Weather API

```python
"""
add_api.py - Add real API integrations to your Gateway
This script demonstrates how to extend your Gateway with external APIs using OpenAPI specifications.
Your agent will be able to call these real services alongside the mock Lambda tools.
"""

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import boto3
import json

# Load configuration
with open("gateway_config.json", "r") as f:
    config = json.load(f)

client = GatewayClient(region_name=config['region'])

# Reconstruct gateway object from saved config
gateway = {
    "gatewayId": config['gateway_id'],
    "gatewayUrl": config['gateway_url'],
    "roleArn": config['gateway_role_arn']
}

# Define OpenAPI specification for a real weather API
weather_api_spec = {
    "openapi": "3.0.0",
    "info": {"title": "Weather API", "version": "1.0.0"},
    "servers": [{"url": "https://api.openweathermap.org/data/2.5"}],
    "paths": {
        "/weather": {
            "get": {
                "operationId": "getCurrentWeather",
                "description": "Get current weather for a city",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "City name"
                    }
                ],
                "responses": {"200": {"description": "Weather data"}}
            }
        }
    }
}

print("Adding OpenWeatherMap API to Gateway...")

# Add the API as a new target
target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="real-weather-api",
    target_type="openApiSchema",
    target_payload={"inlinePayload": json.dumps(weather_api_spec)},
    credentials={
        "api_key": "YOUR_API_KEY_HERE",  # Get from openweathermap.org
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "appid"
    }
)

print(f"✅ API added successfully!")
print(f"Target ID: {target['targetId']}")
print("\\n👉 Run 'python test_agent.py' again to use the new API")
```

### AWS PrivateLink Support

Gateway now supports private VPC connectivity:

```python
# Create VPC endpoint for private access
# Service name: com.amazonaws.{region}.bedrock-agentcore.gateway

# Example endpoint policy for OAuth-based Gateway
vpc_endpoint_policy = {
    "Statement": [{
        "Principal": "*",  # Required for OAuth (non-SigV4) authentication
        "Effect": "Allow",
        "Action": "*",
        "Resource": f"arn:aws:bedrock-agentcore:{REGION}::gateway/{gateway_id}"
    }]
}
```

### Invocation Logging

Monitor all Gateway invocations with:

- **CloudWatch Logs**: Real-time analysis at `/aws/bedrock-agentcore/gateways/{gateway-id}`
- **Amazon S3**: Long-term storage
- **Amazon Data Firehose**: Stream to analytics services

## Understanding OAuth in Gateway

🔒 **Why OAuth?** The Model Context Protocol requires OAuth 2.0 for security:

- Ensures only authorized agents can access your tools
- Provides auditable tool invocations
- Manages credentials securely without hardcoding

**How it works:**

1. Gateway creates a Cognito user pool automatically
1. Your agent authenticates using client credentials
1. Token is included in all requests (valid for 1 hour)
1. Gateway validates token before executing tools

## Troubleshooting

|Issue                      |Solution                                                                     |
|---------------------------|-----------------------------------------------------------------------------|
|“No module named ‘strands’”|Run: `pip install strands-agents`                                            |
|“Model not enabled”        |Enable Claude Sonnet 3.7 in Bedrock console → Model access                   |
|“AccessDeniedException”    |Check IAM permissions for `bedrock-agentcore:*`                              |
|Gateway not responding     |Wait 30-60 seconds after creation for DNS propagation                        |
|OAuth token expired        |Tokens expire after 1 hour, get new one with `get_access_token_for_cognito()`|


**Additional Troubleshooting**

If tools fail with "Access Denied" errors, create diagnose_gateway.py:

What this achieves: Runs comprehensive diagnostics to identify permission issues, role configuration problems, or token expiration. It tests each layer of the Gateway stack and provides specific fixes for any issues found.
```python
"""
diagnose_gateway.py - Comprehensive diagnostic for Gateway issues
This will test each layer of the Gateway stack to identify the problem
"""

import boto3
import json
import requests
import time
from botocore.exceptions import ClientError

# Load configuration
with open("gateway_config.json", "r") as f:
    config = json.load(f)

print("🔍 GATEWAY DIAGNOSTIC TOOL")
print("=" * 60)

# Initialize clients
sts = boto3.client('sts', region_name=config['region'])
lambda_client = boto3.client('lambda', region_name=config['region'])
iam = boto3.client('iam')
gateway_client = boto3.client('bedrock-agentcore-control', region_name=config['region'])

# Get account info
account_id = sts.get_caller_identity()['Account']
print(f"📍 Account: {account_id}")
print(f"📍 Region: {config['region']}")
print(f"📍 Gateway ID: {config['gateway_id']}")

# ============= TEST 1: Verify Lambda Exists =============
print("\\n" + "=" * 60)
print("TEST 1: Lambda Function")
print("-" * 60)

lambda_name = "AgentCoreLambdaTestFunction"
try:
    func = lambda_client.get_function(FunctionName=lambda_name)
    lambda_arn = func['Configuration']['FunctionArn']
    print(f"✅ Lambda exists: {lambda_arn}")

    # Check Lambda permissions
    policy = lambda_client.get_policy(FunctionName=lambda_name)
    policy_doc = json.loads(policy['Policy'])
    print(f"📋 Lambda has {len(policy_doc['Statement'])} permission statements:")

    for stmt in policy_doc['Statement']:
        principal = stmt.get('Principal', {})
        if isinstance(principal, dict):
            principal_str = principal.get('Service', principal.get('AWS', 'Unknown'))
        else:
            principal_str = principal
        print(f"   • {stmt['Sid']}: {principal_str}")

    # Check if bedrock-agentcore service can invoke
    has_bedrock_permission = any(
        stmt.get('Principal', {}).get('Service') == 'bedrock-agentcore.amazonaws.com' or
        stmt.get('Principal') == '*'
        for stmt in policy_doc['Statement']
    )

    if has_bedrock_permission:
        print("✅ Lambda has permission for bedrock-agentcore service")
    else:
        print("❌ Lambda missing bedrock-agentcore permission")

except Exception as e:
    print(f"❌ Lambda error: {e}")

# ============= TEST 2: Verify Gateway Role =============
print("\\n" + "=" * 60)
print("TEST 2: Gateway Execution Role")
print("-" * 60)

role_arn = config.get('gateway_role_arn', f"arn:aws:iam::{account_id}:role/AgentCoreGatewayExecutionRole")
role_name = role_arn.split('/')[-1]

try:
    role = iam.get_role(RoleName=role_name)
    print(f"✅ Role exists: {role_arn}")

    # Check trust policy
    trust_policy = role['Role']['AssumeRolePolicyDocument']
    can_be_assumed = any(
        stmt.get('Principal', {}).get('Service') == 'bedrock-agentcore.amazonaws.com'
        for stmt in trust_policy['Statement']
    )

    if can_be_assumed:
        print("✅ Role can be assumed by bedrock-agentcore")
    else:
        print("❌ Role cannot be assumed by bedrock-agentcore")

    # Check attached policies
    attached = iam.list_attached_role_policies(RoleName=role_name)
    print(f"📋 Attached policies: {len(attached['AttachedPolicies'])}")
    for policy in attached['AttachedPolicies']:
        print(f"   • {policy['PolicyName']}")

    # Check inline policies
    inline = iam.list_role_policies(RoleName=role_name)
    print(f"📋 Inline policies: {len(inline['PolicyNames'])}")
    for policy_name in inline['PolicyNames']:
        print(f"   • {policy_name}")

        # Get policy details
        policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
        statements = policy_doc['PolicyDocument']['Statement']

        # Check for Lambda invoke permission
        has_lambda_invoke = any(
            'lambda:InvokeFunction' in stmt.get('Action', []) or
            'lambda:*' in stmt.get('Action', [])
            for stmt in statements
        )

        if has_lambda_invoke:
            print("     ✅ Has lambda:InvokeFunction permission")
        else:
            print("     ❌ Missing lambda:InvokeFunction permission")

except Exception as e:
    print(f"❌ Role error: {e}")

# ============= TEST 3: Direct Lambda Test =============
print("\\n" + "=" * 60)
print("TEST 3: Direct Lambda Invocation")
print("-" * 60)

try:
    # Test direct Lambda invocation
    test_payload = {"location": "Seattle"}

    response = lambda_client.invoke(
        FunctionName=lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(test_payload),
        ClientContext=json.dumps({
            "custom": {
                "bedrockAgentCoreToolName": "get_weather"
            }
        }).encode('utf-8').hex()  # ClientContext must be base64
    )

    result = json.loads(response['Payload'].read())
    print(f"✅ Direct Lambda call succeeded")
    print(f"   Response: {result}")

except Exception as e:
    print(f"❌ Direct Lambda call failed: {e}")

# ============= TEST 4: Gateway Target Configuration =============
print("\\n" + "=" * 60)
print("TEST 4: Gateway Target Configuration")
print("-" * 60)

try:
    # Get gateway details
    gateway = gateway_client.get_gateway(gatewayIdentifier=config['gateway_id'])
    print(f"✅ Gateway status: {gateway['status']}")

    # List targets
    targets = gateway_client.list_gateway_targets(gatewayIdentifier=config['gateway_id'])
    print(f"📋 Gateway has {len(targets['targets'])} target(s):")

    for target in targets['targets']:
        print(f"   • {target['name']} (ID: {target['targetId']}, Status: {target['status']})")

        # Get target details
        target_details = gateway_client.get_gateway_target(
            gatewayIdentifier=config['gateway_id'],
            targetId=target['targetId']
        )

        # Check Lambda ARN
        lambda_config = target_details.get('targetConfiguration', {}).get('mcp', {}).get('lambda', {})
        if lambda_config:
            target_lambda = lambda_config.get('lambdaArn', 'Not found')
            print(f"     Lambda: {target_lambda}")

            if target_lambda == lambda_arn:
                print("     ✅ Target points to correct Lambda")
            else:
                print("     ❌ Target Lambda mismatch")

except Exception as e:
    print(f"❌ Gateway configuration error: {e}")

# ============= TEST 5: MCP Protocol Test =============
print("\\n" + "=" * 60)
print("TEST 5: MCP Protocol Tests")
print("-" * 60)

def test_mcp_request(method, params=None):
    """Test an MCP request"""
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": str(int(time.time())),
        "method": method,
        "params": params or {}
    }

    try:
        response = requests.post(
            config['gateway_url'],
            headers=headers,
            json=payload,
            timeout=10
        )

        print(f"   Status: {response.status_code}")

        if response.status_code == 401:
            print("   ❌ Authentication failed (token expired or invalid)")
            return None
        elif response.status_code == 403:
            print("   ❌ Authorization failed (no permission)")
            return None
        elif response.status_code == 200:
            result = response.json()
            if 'error' in result:
                print(f"   ❌ MCP Error: {result['error']}")
                return None
            else:
                print(f"   ✅ Success")
                return result
        else:
            print(f"   ❌ HTTP Error: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return None

# Test 5.1: List tools
print("\\n5.1 Testing tools/list:")
result = test_mcp_request("tools/list")
if result and 'result' in result:
    tools = result['result'].get('tools', [])
    print(f"   Found {len(tools)} tools")
    for tool in tools[:3]:  # Show first 3
        print(f"     • {tool['name']}")

# Test 5.2: Call get_weather tool
print("\\n5.2 Testing tools/call (get_weather):")
weather_tool_name = f"{config.get('target_name', 'TestGatewayTarget')}___get_weather"
result = test_mcp_request("tools/call", {
    "name": weather_tool_name,
    "arguments": {"location": "Seattle"}
})

if result and 'result' in result:
    print(f"   Tool response: {result['result']}")

# ============= TEST 6: AssumeRole Test =============
print("\\n" + "=" * 60)
print("TEST 6: Role Assumption Test")
print("-" * 60)

try:
    # Try to assume the Gateway role
    assumed = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName='GatewayDiagnosticTest'
    )

    print(f"✅ Successfully assumed role")

    # Create Lambda client with assumed role
    assumed_lambda = boto3.client(
        'lambda',
        region_name=config['region'],
        aws_access_key_id=assumed['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed['Credentials']['SecretAccessKey'],
        aws_session_token=assumed['Credentials']['SessionToken']
    )

    # Try to invoke Lambda with assumed role
    response = assumed_lambda.invoke(
        FunctionName=lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({"location": "Test"})
    )

    print(f"✅ Lambda invocation with assumed role succeeded")

except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'AccessDenied':
        print(f"❌ Cannot assume role: {e.response['Error']['Message']}")
    else:
        print(f"❌ Role assumption error: {e}")
except Exception as e:
    print(f"❌ Lambda invocation with assumed role failed: {e}")

# ============= SUMMARY =============
print("\\n" + "=" * 60)
print("DIAGNOSTIC SUMMARY")
print("=" * 60)

print("\\n🔍 Based on the tests above, here are the likely issues:\\n")

if 'has_bedrock_permission' in locals() and not has_bedrock_permission:
    print("⚠️  Lambda needs bedrock-agentcore service permission")
    print("   Fix: Add bedrock-agentcore.amazonaws.com as principal in Lambda policy")

if 'has_lambda_invoke' in locals() and not has_lambda_invoke:
    print("⚠️  Gateway role needs lambda:InvokeFunction permission")
    print("   Fix: Add lambda:InvokeFunction to the Gateway execution role")

print("\\n📝 Next steps:")
print("1. Review the test results above")
print("2. Fix any ❌ items")
print("3. Run 'python test_agent.py' again")

```
Run it:

```bash
python diagnose_gateway.py
```

## Quick Validation

```bash
# Check your Gateway is working
curl -X POST YOUR_GATEWAY_URL \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Watch live logs
aws logs tail /aws/bedrock-agentcore/gateways/YOUR_GATEWAY_ID --follow
```

## Clean Up

```bash
# Delete Gateway and all resources
aws bedrock-agentcore-control delete-gateway \
    --gateway-identifier YOUR_GATEWAY_ID \
    --region us-east-1

# Delete Cognito pool (optional)
aws cognito-idp delete-user-pool \
    --user-pool-id YOUR_POOL_ID \
    --region us-east-1
```

<details>
<summary><strong>➡️ Advanced: Custom Lambda Tools</strong></summary>

Create custom Lambda functions with specific tools:

```python
# Custom Lambda configuration
lambda_config = {
    "lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
    "toolSchema": {
        "inlinePayload": [
            {
                "name": "process_data",
                "description": "Process customer data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer identifier"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["analyze", "summarize", "export"]
                        }
                    },
                    "required": ["customer_id", "action"]
                }
            }
        ]
    }
}

# Lambda implementation example
def lambda_handler(event, context):
    tool_name = context.client_context.custom.get('bedrockAgentCoreToolName')

    if tool_name == 'process_data':
        customer_id = event.get('customer_id')
        action = event.get('action')

        # Your business logic here
        result = process_customer_data(customer_id, action)

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
```

</details>


If you're excited and want to learn more about Gateways and the other Target types. Continue through this guide.

### Adding OpenAPI Targets

Let's add an OpenAPI target. This code uses the OpenAPI schema for a NASA API that provides Mars weather information. You can get an API key sent to your email in a minute by filling out the form here: https://api.nasa.gov/.

**Open API Spec for NASA Mars weather API**
<div style="max-height: 200px; overflow: auto;">

```python
nasa_open_api_payload = {
  "openapi": "3.0.3",
  "info": {
    "title": "NASA InSight Mars Weather API",
    "description": "Returns per‑Sol weather summaries from the InSight lander for the seven most recent Martian sols.",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.nasa.gov"
    }
  ],
  "paths": {
    "/insight_weather/": {
      "get": {
        "summary": "Retrieve latest InSight Mars weather data",
        "operationId": "getInsightWeather",
        "parameters": [
          {
            "name": "feedtype",
            "in": "query",
            "required": true,
            "description": "Response format (only \"json\" is supported).",
            "schema": {
              "type": "string",
              "enum": [
                "json"
              ]
            }
          },
          {
            "name": "ver",
            "in": "query",
            "required": true,
            "description": "API version string. (only \"1.0\" supported)",
            "schema": {
              "type": "string",
              "enum": [
                "1.0"
              ]
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful response – weather data per Martian sol.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/InsightWeatherResponse"
                }
              }
            }
          },
          "400": {
            "description": "Bad request – missing or invalid parameters."
          },
          "429": {
            "description": "Too many requests – hourly rate limit exceeded (2 000 hits/IP)."
          },
          "500": {
            "description": "Internal server error."
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "InsightWeatherResponse": {
        "type": "object",
        "required": [
          "sol_keys"
        ],
        "description": "Top‑level object keyed by sol numbers plus metadata.",
        "properties": {
          "sol_keys": {
            "type": "array",
            "description": "List of sols (as strings) included in this payload.",
            "items": {
              "type": "string"
            }
          },
          "validity_checks": {
            "type": "object",
            "additionalProperties": {
              "$ref": "#/components/schemas/ValidityCheckPerSol"
            },
            "description": "Data‑quality provenance per sol and sensor."
          }
        },
        "additionalProperties": {
          "oneOf": [
            {
              "$ref": "#/components/schemas/SolWeather"
            }
          ]
        }
      },
      "SolWeather": {
        "type": "object",
        "properties": {
          "AT": {
            "$ref": "#/components/schemas/SensorData"
          },
          "HWS": {
            "$ref": "#/components/schemas/SensorData"
          },
          "PRE": {
            "$ref": "#/components/schemas/SensorData"
          },
          "WD": {
            "$ref": "#/components/schemas/WindDirection"
          },
          "Season": {
            "type": "string",
            "enum": [
              "winter",
              "spring",
              "summer",
              "fall"
            ]
          },
          "First_UTC": {
            "type": "string",
            "format": "date-time"
          },
          "Last_UTC": {
            "type": "string",
            "format": "date-time"
          }
        }
      },
      "SensorData": {
        "type": "object",
        "properties": {
          "av": {
            "type": "number"
          },
          "ct": {
            "type": "number"
          },
          "mn": {
            "type": "number"
          },
          "mx": {
            "type": "number"
          }
        }
      },
      "WindDirection": {
        "type": "object",
        "properties": {
          "most_common": {
            "$ref": "#/components/schemas/WindCompassPoint"
          }
        },
        "additionalProperties": {
          "$ref": "#/components/schemas/WindCompassPoint"
        }
      },
      "WindCompassPoint": {
        "type": "object",
        "properties": {
          "compass_degrees": {
            "type": "number"
          },
          "compass_point": {
            "type": "string"
          },
          "compass_right": {
            "type": "number"
          },
          "compass_up": {
            "type": "number"
          },
          "ct": {
            "type": "number"
          }
        }
      },
      "ValidityCheckPerSol": {
        "type": "object",
        "properties": {
          "AT": {
            "$ref": "#/components/schemas/SensorValidity"
          },
          "HWS": {
            "$ref": "#/components/schemas/SensorValidity"
          },
          "PRE": {
            "$ref": "#/components/schemas/SensorValidity"
          },
          "WD": {
            "$ref": "#/components/schemas/SensorValidity"
          }
        }
      },
      "SensorValidity": {
        "type": "object",
        "properties": {
          "sol_hours_with_data": {
            "type": "array",
            "items": {
              "type": "integer",
              "minimum": 0,
              "maximum": 23
            }
          },
          "valid": {
            "type": "boolean"
          }
        }
      }
    }
  }
}
```
</div>
<br/>

Use the following code to add an Open API target. **⚠️ Note: don't forget to add your api_key below.**
```python hl_lines="8"
open_api_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name=None,
    target_type="openApiSchema",
    # the API spec to use (note don't forget to )
    target_payload={
        "inlinePayload": json.dumps(nasa_open_api_payload)
    },
    # the credentials to use when interacting with this API
    credentials={
        "api_key": "<INSERT KEY>",
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "api_key"
    }
)
```
<details>
<summary>
<strong> ➡️ Advanced OpenAPI Configurations (Import API specs from S3 + set up APIs with OAuth)
</strong>
</summary>
You can also use an OpenAPI specification stored in S3 buckets by passing the following `target_payload` field. **⚠️ Note don't forget to fill in the S3 URI below.**
```python hl_lines="6"
{
    "s3": {
        "uri": "<INSERT S3 URI>"
    }
}
```

If you have an API that uses a key stored in a header value you can set the `credentials` field to the following. **⚠️ Note don't forget to fill in the api key and parameter name below.**
```json hl_lines="2 4"
{
    "api_key": "<INSERT KEY>",
    "credential_location": "HEADER",
    "credential_parameter_name": "<INSERT HEADER VALUE>"
}
```

Alternatively if you have an API that uses OAuth, set the `credentials` field to the following. **⚠️ Note don't forget to fill in all of the information below.**
```json hl_lines="6-13"
{
  "oauth2_provider_config": {
    "customOauth2ProviderConfig": {
      "oauthDiscovery": {
        "authorizationServerMetadata": {
          "issuer": "<INSERT ISSUER URL>",
          "authorizationEndpoint": "<INSERT AUTHORIZATION ENDPOINT>",
          "tokenEndpoint": "<INSERT TOKEN ENDPOINT>"
        }
      },
      "clientId": "<INSERT CLIENT ID>",
      "clientSecret": "<INSERT CLIENT SECRET>"
    }
  }
}
```
There are other supported `oauth_2_provider` types including Microsoft, GitHub, Google, Salesforce, and Slack. For information on the structure of those provider configs see the [identity documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idps.html).
</details>

### Adding Smithy API Model Targets
Let's add a Smithy API model target. Many AWS services use Smithy API models to describe their APIs. [This AWS-maintained GitHub repository](https://github.com/aws/api-models-aws/tree/main/models) has over the models of 350+ AWS services for download. For quick testing, we've made it possible to use a few of these models in the AgentCore Gateway without downloading them or storing them in S3. To create a Smithy API model target for DynamoDB simply run:

```python
# create a Smithy API model target for DynamoDB
smithy_target = client.create_mcp_gateway_target(gateway=gateway, name=None, target_type="smithyModel")
```

<details>
<summary>
<strong> ➡️ Add more Smithy API model targets</strong>
</summary>

Create a Smithy API model target from a Smithy API model stored in S3. **⚠️ Note don't forget to fill in the S3 URI below.**
```python hl_lines="7"
# create a Smithy API model target from a Smithy API model stored in S3
open_api_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name=None,
    target_type="smithyModel",
    target_payload={
        "s3": {
            "uri": "<INSERT S3 URI>"
        }
    },
)
```

Create a Smithy API model target from a Smithy API model inline. **⚠️ Note don't forget to load the Smithy model JSON into the smithy_model_json variable.**
```python hl_lines="6"
# create a Smithy API model target from a Smithy API model stored in S3
open_api_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name=None,
    target_type="smithyModel",
    target_payload={
        "inlinePayload": json.dumps(smithy_model_json)
    },
)
```
</details>
<br/>
<details>
<summary><h2 style="display:inline">➡️ More Operations on Gateways and Targets (Create, Read, Update, Delete, List) </h2></summary>

While the Starter Toolkit makes it easy to get started, the Boto3 Python client has a more complete set of operations including those for creating, reading, updating, deleting, and listing Gateways and Targets. Let's see how to use Boto3 to carry out these operations on Gateways and Targets.

### Setup

Instantiate the client
```python
import boto3

boto_client = boto3.client("bedrock-agentcore-control",
                           region_name="us-east-1")
```

### Listing Gateways/Targets
Run the below code to list all of the Gateways in your account.
```python
# list gateawys
gateways = boto_client.list_gateways()
```
Run the below code to list all of the Gateway Targets for a specific Gateway.
```python
# list targets
gateway_targets = boto_client.list_gateway_targets(gatewayIdentifier="<INSERT GATEWAY ID>")
```

### Getting Gateways/Targets
Run the below code to get the details of a Gateway
```python
# get a gateway
gateway_details = boto_client.get_gateway(gatewayIdentifier="<INSERT GATEWAY ID>")
```
Run the below code to get the details of a Gateway Target.
```python
# get a target
target_details = boto_client.get_gateway_target(gatewayIdentifier="<INSERT GATEWAY ID>", targetId="INSERT TARGET ID")
```

### Creating / Updating Gateways

Let's see how to create a Gateway. **⚠️ Note don't forget to fill in the required fields with appropriate values.**

Below is the structure of a create request for a Gateway:
```python
# the schema of a create request for a Gateway
create_gw_request = {
    "name": "string", # required - name of your gateway
    "description": "string", # optional - description of your gateway
    "clientToken": "string", # optional - used for idempotency
    "roleArn": "string", # required - execution role arn that Gateway will use when interacting with AWS resources
    "protocolType": "string", # required - must be MCP
    "protocolConfiguration": { # optional
        "mcp": {
            "supportedVersions": ["enum_string"], # optional - e.g. 2025-06-18
            "instructions": "string", # optional - instructions for agents using this MCP server
            "searchType": "enum_string" # optional - must be SEMANTIC if specified. This enables the tool search tool
        }
    },
    "authorizerType": "string", # required - must be CUSTOM_JWT
    "authorizerConfiguration": { # required - the configuration for your authorizer
        "customJWTAuthorizer": { # required the custom JWT authorizer setup
            "allowedAudience": [], # optional
            "allowedClients": [], # optional
            "discoveryUrl": "string" # required - the URL of the authorization server
        },
    },
    "kmsKeyArn": "string", # optional - an encryption key to use for encrypting your tool metadata stored on Gateway
    "exceptionLevel": "string", # optional - must be DEBUG if specified. Gateway will return verbose error messages when DEBUG is specified.
}
```

Let's take a look at a simpler example:
```python
# an example of a create request
example_create_gw_request = {
    "name": "TestGateway",
    "roleArn": "<INSERT ROLE ARN e.g. arn:aws:iam::123456789012:role/Admin>",
    "protocolType": "MCP",
    "authorizerType": "CUSTOM_JWT",
    "authorizerConfiguration":  {
        "customJWTAuthorizer": {
            "discoveryUrl": "<INSERT DISCOVERY URL e.g. https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration>",
            "allowedClients": ["<INSERT CLIENT ID>"]
        }
    }
}
```
Once you have filled in your request details, you can create a Gateway from that request with the following command:
```python
# create the gateway
gateway = boto_client.create_gateway(**example_create_gw_request)
```

Now let's see how to update a Gateway that we've already created. **⚠️ Note don't forget to fill in the required fields with appropriate values.**

Below is the structure of an update request for a Gateway:
```python
# the schema of an update request for a Gateway
update_gw_request = {
    "gatewayIdentifier": "string", # required - the ID of the existing gateway
    "name": "string", # required - name of your gateway
    "description": "string", # optional - description of your gateway
    "roleArn": "string", # required - execution role arn that Gateway will use when interacting with AWS resources
    "protocolType": "string", # required - must be MCP
    "protocolConfiguration": { # optional
        "mcp": {
            "supportedVersions": ["enum_string"], # optional - e.g. 2025-06-18
            "instructions": "string", # optional - instructions for agents using this MCP server
            "searchType": "enum_string" # optional - must be SEMANTIC if specified. This enables the tool search tool
        }
    },
    "authorizerType": "string", # required - must be CUSTOM_JWT
    "authorizerConfiguration": { # required - the configuration for your authorizer
        "customJWTAuthorizer": { # required the custom JWT authorizer setup
            "allowedAudience": [], # optional
            "allowedClients": [], # optional
            "discoveryUrl": "string" # required - the URL of the authorization server
        },
    },
    "kmsKeyArn": "string", # optional - an encryption key to use for encrypting your tool metadata stored on Gateway
}
```

Let's take a look at a simpler example:
```python
# an example of an update request
example_update_gw_request = {
    "gatewayIdentifier": "<INSERT ID OF CREATED GATEWAY>",
    "name": "TestGateway",
    "roleArn": "<INSERT ROLE ARN e.g. arn:aws:iam::123456789012:role/Admin>",
    "protocolType": "MCP",
    "authorizerType": "CUSTOM_JWT",
    "authorizerConfiguration":  {
        "customJWTAuthorizer": {
            "discoveryUrl": "<INSERT DISCOVERY URL e.g. https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration>",
            "allowedClients": ["<INSERT CLIENT ID>"]
        }
    }
}
```

Once you've filled in you request details you can update a Gateway using that request with the following command:
```python
# update the gateway
gateway = boto_client.update_gateway(**example_update_gw_request)
```

### Creating / Updating Targets

Let's see how to create a Gateway Target. **⚠️ Note don't forget to fill in the required fields with appropriate values.**

Below is the structure of a create request for a Gateway Target:
```python
# the schema of a create request for a Gateway Target
create_target_request = {
    "gatewayIdentifier": "string", # required - the ID of the Gateway to create this target on
    "name": "string", # required
    "description": "string", # optional - description of your target
    "clientToken": "string", # optional - used for idempotency
    "targetConfiguration": { # required
        "mcp": { # required - union - choose one of openApiSchema | smithyModel | lambda
            "openApiSchema": { # union - choose one of either s3 or inlinePayload
                "s3": {
                    "uri": "string",
                    "bucketOwnerAccountId": "string"
                },
                "inlinePayload": "string"
            },
            "smithyModel": { # union - choose one of either s3 or inlinePayload
                "s3": {
                    "uri": "string",
                    "bucketOwnerAccountId": "string"
                },
                "inlinePayload": "string"
            },
            "lambda": {
                "lambdaArn": "string",
                "toolSchema": { # union - choose one of either s3 or inlinePayload
                    "s3": {
                        "uri": "string",
                        "bucketOwnerAccountId": "string"
                     },
                    "inlinePayload": [
                        # <inline tool here>
                    ]
                }
            }
        }
    },
    "credentialProviderConfigurations": [
        {
            "credentialProviderType": "enum_string", # required - choose one of OAUTH | API_KEY | GATEWAY_IAM_ROLE
            "credentialProvider": { # optional (required if you choose OAUTH or API_KEY) - union - choose either apiKeyCredentialProvider | oauthCredentialProvider
                "oauthCredentialProvider": {
                    "providerArn": "string", # required - the ARN of the credential provider
                    "scopes": ["string"], # required - can be empty list in some cases
                },
                "apiKeyCredentialProvider": {
                    "providerArn": "string", # required - the ARN of the credential provider
                    "credentialLocation": "enum_string", # required - the location where the credential goes - choose HEADER | QUERY_PARAMETER
                    "credentialParameterName": "string", # required - the header key or parameter name e.g., “Authorization”, “X-API-KEY”
                    "credentialPrefix": "string"  # optional - the prefix the auth token needs e.g. “Bearer”
                }
            }
        }
    ]
}
```

Let's take a look at a simpler example:
```python
# example of a target creation request
example_create_target_request = {
    "gatewayIdentifier": "<INSERT GATEWAY ID",
    "name": "TestLambdaTarget",
    "targetConfiguration": {
        "mcp": {
            "lambda": {
                "lambdaArn": "<INSERT LAMBDA ARN e.g. arn:aws:lambda:us-west-2:123456789012:function:TestLambda>",
                "toolSchema": {
                    "s3": {
                        "uri": "<INSERT S3 URI>"
                    }
                }
            }
        }
    },
    "credentialProvider": [
        {
            "credentialProviderType": "GATEWAY_IAM_ROLE"
        }
    ]
}
```
Once you've filled in you request details you can create a Gateway Target using that request with the following command:
```python
# create the target
target = boto_client.create_gateway_target(**example_create_target_request)
```

Now let's see how to update a Gateway Target. **⚠️ Note don't forget to fill in the required fields with appropriate values.**

Below is the structure of an update request for a Target:
```python
# create a target
update_target_request = {
    "gatewayIdentifier": "string", # required - the ID of the Gateway to update this target on
    "targetId": "string", # required - the ID of the target to update
    "name": "string", # required
    "description": "string", # optional - description of your target
    "targetConfiguration": { # required
        "mcp": { # required - union - choose one of openApiSchema | smithyModel | lambda
            "openApiSchema": { # union - choose one of either s3 or inlinePayload
                "s3": {
                    "uri": "string",
                    "bucketOwnerAccountId": "string"
                },
                "inlinePayload": "string"
            },
            "smithyModel": { # union - choose one of either s3 or inlinePayload
                "s3": {
                    "uri": "string",
                    "bucketOwnerAccountId": "string"
                },
                "inlinePayload": "string"
            },
            "lambda": {
                "lambdaArn": "string",
                "toolSchema": { # union - choose one of either s3 or inlinePayload
                    "s3": {
                        "uri": "string",
                        "bucketOwnerAccountId": "string"
                     },
                    "inlinePayload": [
                        # <inline tool here>
                    ]
                }
            }
        }
    },
    "credentialProviderConfigurations": [
        {
            "credentialProviderType": "enum_string", # required - choose one of OAUTH | API_KEY | GATEWAY_IAM_ROLE
            "credentialProvider": { # optional (required if you choose OAUTH or API_KEY) - union - choose either apiKeyCredentialProvider | oauthCredentialProvider
                "oauthCredentialProvider": {
                    "providerArn": "string", # required
                    "scopes": ["string"], # required - can be empty list in some cases
                },
                "apiKeyCredentialProvider": {
                    "providerArn": "string", # required
                    "credentialLocation": "enum_string", # required - the location where the credential goes - choose HEADER | QUERY_PARAMETER
                    "credentialParameterName": "string", # required - the header key or parameter name e.g., “Authorization”, “X-API-KEY”
                    "credentialPrefix": "string"  # optional - the prefix the auth token needs e.g. “Bearer”
                }
            }
        }
    ]
}
```
Let's take a look at a simpler example:
```python
example_update_target_request = {
    "gatewayIdentifier": "<INSERT GATEWAY ID",
    "targetId": "<INSERT TARGET ID>",
    "name": "TestLambdaTarget",
    "targetConfiguration": {
        "mcp": {
            "lambda": {
                "lambdaArn": "<INSERT LAMBDA ARN e.g. arn:aws:lambda:us-west-2:123456789012:function:TestLambda>",
                "toolSchema": {
                    "s3": {
                        "uri": "<INSERT S3 URI>"
                    }
                }
            }
        }
    },
    "credentialProvider": [
        {
            "credentialProviderType": "GATEWAY_IAM_ROLE"
        }
    ]
}
```
Once you've filled in you request details you can create a Target using that request with the following command:
```python
# update a target
target = boto_client.update_gateway_target(**example_update_target_request)
```


### Deleting Gateways / Targets
Run the below code to delete a Gateway.
```python
# delete a gateway
delete_gateway_response = boto_client.delete_gateway(
    gatewayIdentifier="<INSERT GATEWAY ID>"
)
```

Run the below code to delete a Gateway Target.
```python
# delete a target
delete_target_response = boto_client.delete_gateway_target(
    gatewayIdentifier="<INSERT GATEWAY ID>",
    targetId="<INSERT TARGET ID>"
)
```
</details>


## Learn More

- **Comprehensive examples**: [GitHub samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/02-AgentCore-gateway)
- **Full API reference**: [Boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html)
- **Developer guide**: [Official documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
