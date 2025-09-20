# QuickStart: A Fully Managed MCP Server in 5 Minutes! 🚀

Amazon Bedrock AgentCore Gateway provides an easy and secure way for developers to build, deploy, discover, and connect to tools at scale. AI agents need tools to perform real-world tasks—from querying databases to sending messages to analyzing documents. With Gateway, developers can convert APIs, Lambda functions, and existing services into Model Context Protocol (MCP)-compatible tools and make them available to agents through Gateway endpoints with just a few lines of code. Gateway supports OpenAPI, Smithy, and Lambda as input types, and is the only solution that provides both comprehensive ingress authentication and egress authentication in a fully-managed service. Gateway eliminates weeks of custom code development, infrastructure provisioning, and security implementation so developers can focus on building innovative agent applications.

In this quick start guide you will learn how to set up a Gateway and integrate it into your agents using the AgentCore Starter Toolkit. You can find more comprehensive guides and examples [**here**](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/02-AgentCore-gateway).

**Note: The AgentCore Starter Toolkit is intended to help developers get started quickly. The Boto3 Python library provides the most comprehensive set of operations for Gateways and Targets. You can find the Boto3 documentation [here](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html). For complete documentation see the [**developer guide**](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)**

## Prerequisites

Before starting, make sure you have:

- **AWS Account** with credentials configured (`aws configure`)
- **Python 3.10+** installed
- **IAM Permissions** for creating roles, Lambda functions, and using Bedrock AgentCore
- **Model Access** - Enable Anthropic’s Claude Sonnet 3.7 in the Bedrock console (or another model for the demo agent)

## Step 1: Setup and Install

```bash
mkdir agentcore-gateway-quickstart
cd agentcore-gateway-quickstart
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```

**Install Dependencies**

```bash
pip install boto3
pip install bedrock-agentcore-starter-toolkit
pip install strands-agents
```


## Step 2: Create Gateway Setup Script

Create a new file called `setup_gateway.py` with the following complete code.

```python
"""
Setup script to create Gateway with Lambda target and save configuration
Run this first: python setup_gateway.py
"""

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json
import logging
import time

def setup_gateway():
    # Configuration
    region = "us-east-1"  # Change to your preferred region

    print("🚀 Setting up AgentCore Gateway...")
    print(f"Region: {region}\n")

    # Initialize client
    client = GatewayClient(region_name=region)
    client.logger.setLevel(logging.INFO)

    # Step 2.1: Create OAuth authorizer
    print("Step 2.1: Creating OAuth authorization server...")
    cognito_response = client.create_oauth_authorizer_with_cognito("TestGateway")
    print("✓ Authorization server created\n")

    # Step 2.2: Create Gateway
    print("Step 2.2: Creating Gateway...")
    gateway = client.create_mcp_gateway(
        # the name of the Gateway - if you don't set one, one will be generated.
        name=None,
        # the role arn that the Gateway will use - if you don't set one, one will be created.
        # NOTE: if you are using your own role make sure it has a trust policy that trusts bedrock-agentcore.amazonaws.com
        role_arn=None,
        # the OAuth authorization server details. If you are providing your own authorization server,
        # then pass an input of the following form: {"customJWTAuthorizer": {"allowedClients": ["<INSERT CLIENT ID>"], "discoveryUrl": "<INSERT DISCOVERY URL">}}
        authorizer_config=cognito_response["authorizer_config"],
        # enable semantic search
        enable_semantic_search=True,
    )
    print(f"✓ Gateway created: {gateway['gatewayUrl']}\n")

    # If role_arn was not provided, fix IAM permissions
    # NOTE: This is handled internally by the toolkit when no role is provided
    client.fix_iam_permissions(gateway)
    print("⏳ Waiting 30s for IAM propagation...")
    time.sleep(30)
    print("✓ IAM permissions configured\n")

    # Step 2.3: Add Lambda target
    print("Step 2.3: Adding Lambda target...")
    lambda_target = client.create_mcp_gateway_target(
        # the gateway created in the previous step
        gateway=gateway,
        # the name of the Target - if you don't set one, one will be generated.
        name=None,
        # the type of the Target
        target_type="lambda",
        # the target details - set this to define your own lambda if you pre-created one.
        # Otherwise leave this None and one will be created for you.
        target_payload=None,
        # you will see later in the tutorial how to use this to connect to APIs using API keys and OAuth credentials.
        credentials=None,
    )
    print("✓ Lambda target added\n")

    # Step 2.4: Save configuration for agent
    config = {
        "gateway_url": gateway["gatewayUrl"],
        "gateway_id": gateway["gatewayId"],
        "region": region,
        "client_info": cognito_response["client_info"]
    }

    with open("gateway_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("=" * 60)
    print("✅ Gateway setup complete!")
    print(f"Gateway URL: {gateway['gatewayUrl']}")
    print(f"Gateway ID: {gateway['gatewayId']}")
    print("\nConfiguration saved to: gateway_config.json")
    print("\nNext step: Run 'python run_agent.py' to test your Gateway")
    print("=" * 60)

    return config

if __name__ == "__main__":
    setup_gateway()
```

See below for step-by-step understanding of each component.

<details>
<summary>
<strong>📚 Understanding the Setup Script - Step by Step Explanation</strong>
</summary>

#### Import Required Libraries

First, import the necessary libraries for gateway creation and configuration.

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json
import logging
import time
```

#### Create the Setup Function

Initialize the setup function with your AWS region configuration.

```python
def setup_gateway():
    # Configuration
    region = "us-east-1"  # Change to your preferred region

    print("🚀 Setting up AgentCore Gateway...")
    print(f"Region: {region}\n")

    # Initialize client
    client = GatewayClient(region_name=region)
    client.logger.setLevel(logging.INFO)
```

### Step 2.1: Creating an OAuth Authorization Server

🔑 Gateways are secured by OAuth authorization servers which ensure that only allowed users can access your Gateway. Let’s create an OAuth authorization server using Amazon Cognito.

```python
    # Step 2.1: Create OAuth authorizer
    print("Step 2.1: Creating OAuth authorization server...")
    cognito_response = client.create_oauth_authorizer_with_cognito("TestGateway")
    print("✓ Authorization server created\n")
```

**What happens here**: This creates a Cognito user pool with OAuth 2.0 client credentials flow configured. You’ll get a client ID and secret that can be used to obtain access tokens.

### Step 2.2: Creating a Gateway

🌉 Now, let’s create a Gateway. The Gateway acts as your MCP server endpoint that agents will connect to.

```python
    # Step 2.2: Create Gateway
    print("Step 2.2: Creating Gateway...")
    gateway = client.create_mcp_gateway(
        # the name of the Gateway - if you don't set one, one will be generated.
        name=None,
        # the role arn that the Gateway will use - if you don't set one, one will be created.
        # NOTE: if you are using your own role make sure it has a trust policy that trusts bedrock-agentcore.amazonaws.com
        role_arn=None,
        # the OAuth authorization server details. If you are providing your own authorization server,
        # then pass an input of the following form: {"customJWTAuthorizer": {"allowedClients": ["<INSERT CLIENT ID>"], "discoveryUrl": "<INSERT DISCOVERY URL">}}
        authorizer_config=cognito_response["authorizer_config"],
        # enable semantic search
        enable_semantic_search=True,
    )
    print(f"✓ Gateway created: {gateway['gatewayUrl']}\n")

    # If role_arn was not provided, fix IAM permissions
    # NOTE: This is handled internally by the toolkit when no role is provided
    client.fix_iam_permissions(gateway)
    print("⏳ Waiting 30s for IAM propagation...")
    time.sleep(30)
    print("✓ IAM permissions configured\n")
```

**What happens here**: Creates a Gateway with MCP protocol support, configures OAuth authorization, and enables semantic search for tool discovery. If you don’t provide a role, one is created and configured automatically.

### Step 2.3: Adding Lambda Targets

🛠️ Let’s add a Lambda function target. This code will automatically create a Lambda function with weather and time tools.

```python
    # Step 2.3: Add Lambda target
    print("Step 2.3: Adding Lambda target...")
    lambda_target = client.create_mcp_gateway_target(
        # the gateway created in the previous step
        gateway=gateway,
        # the name of the Target - if you don't set one, one will be generated.
        name=None,
        # the type of the Target
        target_type="lambda",
        # the target details - set this to define your own lambda if you pre-created one.
        # Otherwise leave this None and one will be created for you.
        target_payload=None,
        # you will see later in the tutorial how to use this to connect to APIs using API keys and OAuth credentials.
        credentials=None,
    )
    print("✓ Lambda target added\n")
```

**What happens here**: Creates a test Lambda function with two tools (get_weather and get_time) and registers it as a target in your Gateway.

### Step 2.4: Save Configuration

Save the gateway configuration to a file for use by the agent.

```python
    # Step 2.4: Save configuration for agent
    config = {
        "gateway_url": gateway["gatewayUrl"],
        "gateway_id": gateway["gatewayId"],
        "region": region,
        "client_info": cognito_response["client_info"]
    }

    with open("gateway_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("=" * 60)
    print("✅ Gateway setup complete!")
    print(f"Gateway URL: {gateway['gatewayUrl']}")
    print(f"Gateway ID: {gateway['gatewayId']}")
    print("\nConfiguration saved to: gateway_config.json")
    print("\nNext step: Run 'python run_agent.py' to test your Gateway")
    print("=" * 60)

    return config

if __name__ == "__main__":
    setup_gateway()
```

</details>

### Run the Setup

Execute the setup script to create your Gateway and Lambda target.

```bash
python setup_gateway.py
```

**What to expect**: The script will take about 2-3 minutes to complete. You’ll see progress messages for each step.

## Step 3: Using the Gateway with an Agent

Create a new file called `run_agent.py` with the following code:

```python
"""
Agent script to test the Gateway
Run this after setup: python run_agent.py
"""

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json
import sys

def create_streamable_http_transport(mcp_url: str, access_token: str):
    return streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {access_token}"})

def get_full_tools_list(client):
    """Get all tools with pagination support"""
    more_tools = True
    tools = []
    pagination_token = None
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            more_tools = True
            pagination_token = tmp_tools.pagination_token
    return tools

def run_agent():
    # Load configuration
    try:
        with open("gateway_config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Error: gateway_config.json not found!")
        print("Please run 'python setup_gateway.py' first to create the Gateway.")
        sys.exit(1)

    gateway_url = config["gateway_url"]
    client_info = config["client_info"]

    # Get access token for the agent
    print("Getting access token...")
    client = GatewayClient(region_name=config["region"])
    access_token = client.get_access_token_for_cognito(client_info)
    print("✓ Access token obtained\n")

    # Model configuration - change if needed
    model_id = "anthropic.claude-3-7-sonnet-20250219-v1:0"

    print("🤖 Starting AgentCore Gateway Test Agent")
    print(f"Gateway URL: {gateway_url}")
    print(f"Model: {model_id}")
    print("-" * 60)

    # Setup Bedrock model
    bedrockmodel = BedrockModel(
        inference_profile_id=model_id,
        streaming=True,
    )

    # Setup MCP client
    mcp_client = MCPClient(lambda: create_streamable_http_transport(gateway_url, access_token))

    with mcp_client:
        # List available tools
        tools = get_full_tools_list(mcp_client)
        print(f"\n📋 Available tools: {[tool.tool_name for tool in tools]}")
        print("-" * 60)

        # Create agent
        agent = Agent(model=bedrockmodel, tools=tools)

        # Interactive loop
        print("\n💬 Interactive Agent Ready!")
        print("Try asking: 'What's the weather in Seattle?'")
        print("Type 'exit', 'quit', or 'bye' to end.\n")

        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("👋 Goodbye!")
                break

            print("\n🤔 Thinking...\n")
            response = agent(user_input)
            print(f"\nAgent: {response.message.get('content', response)}\n")

if __name__ == "__main__":
    run_agent()
```

### Run Your Agent

Test your Gateway by running the agent and interacting with the tools.

```bash
python run_agent.py
```

That’s it! The agent will start and you can ask questions like:

- “What’s the weather in Seattle?”
- “What time is it in New York?”

## What You’ve Built

- **MCP Server (Gateway)**: A managed endpoint at `https://gateway-id.gateway.bedrock-agentcore.region.amazonaws.com/mcp`
- **Lambda Tools**: Mock functions that return test data (weather: “72°F, Sunny”, time: “2:30 PM”)
- **OAuth Authentication**: Secure access using Cognito tokens
- **AI Agent**: Claude-powered assistant that can discover and use your tools

---
## **🥳🥳🥳 Congratulations - you successfully built an agent with MCP tools powered by AgentCore Gateway!**
---




## Troubleshooting

|Issue                      |Solution                                                                     |
|---------------------------|-----------------------------------------------------------------------------|
|“No module named ‘strands’”|Run: `pip install strands-agents`                                            |
|“Model not enabled”        |Enable Claude Sonnet 3.7 in Bedrock console → Model access                   |
|“AccessDeniedException”    |Check IAM permissions for `bedrock-agentcore:*`                              |
|Gateway not responding     |Wait 30-60 seconds after creation for DNS propagation                        |
|OAuth token expired        |Tokens expire after 1 hour, get new one with `get_access_token_for_cognito()`|


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

## Cleanup

Create `cleanup_gateway.py`:

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json

with open("gateway_config.json", "r") as f:
    config = json.load(f)

client = GatewayClient(region_name=config["region"])
client.cleanup_gateway(config["gateway_id"], config["client_info"])
print("✅ Cleanup complete!")
```

Run: `python cleanup_gateway.py`


### Next Steps

- **Custom Lambda Tools**: Create Lambda functions with your business logic
- **Add Your Own APIs**: Extend your Gateway with OpenAPI specifications for real services
- **Production Setup**: Configure VPC endpoints, custom domains, and monitoring


## Custom Lambda Tools

Create your own Lambda functions with custom business logic and add them as Gateway targets. Lambda targets allow you to implement any custom tool logic in Python, Node.js, or other supported runtimes.

<details>
<summary>
<strong> ➡️ Creating Custom Lambda Tools</strong>
</summary>

Create a file `create_custom_lambda.py`:

```python
"""Create a custom Lambda function and add it as a Gateway target"""

import boto3
import json
import io
import zipfile
import time
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

def create_custom_lambda(region, gateway_role_arn):
    lambda_client = boto3.client('lambda', region_name=region)
    iam = boto3.client('iam')

    # Lambda code
    lambda_code = '''
import json

def lambda_handler(event, context):
    tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', 'unknown')

    if 'calculate_sum' in tool_name:
        a = event.get('a', 0)
        b = event.get('b', 0)
        return {
            'statusCode': 200,
            'body': json.dumps({'result': a + b})
        }
    elif 'multiply' in tool_name:
        x = event.get('x', 0)
        y = event.get('y', 0)
        return {
            'statusCode': 200,
            'body': json.dumps({'result': x * y})
        }

    return {'statusCode': 200, 'body': json.dumps({'error': 'Unknown tool'})}
'''

    # Create zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)
    zip_buffer.seek(0)

    # Create execution role
    role_name = 'CustomCalculatorLambdaRole'
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            })
        )
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        role_arn = role['Role']['Arn']
        print(f"Created Lambda execution role: {role_arn}")
        time.sleep(10)
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']

    # Create Lambda
    function_name = 'CustomCalculatorFunction'
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_buffer.read()},
            Description='Custom calculator for AgentCore Gateway'
        )
        lambda_arn = response['FunctionArn']
        print(f"Created Lambda: {lambda_arn}")

        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='AllowAgentCoreInvoke',
            Action='lambda:InvokeFunction',
            Principal=gateway_role_arn
        )
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.get_function(FunctionName=function_name)
        lambda_arn = response['Configuration']['FunctionArn']
        print(f"Lambda already exists: {lambda_arn}")

    return lambda_arn

# Main execution
with open("gateway_config.json", "r") as f:
    config = json.load(f)

client = GatewayClient(region_name=config["region"])
gateway = client.client.get_gateway(gatewayIdentifier=config["gateway_id"])

print("Creating custom Lambda function...")
lambda_arn = create_custom_lambda(config["region"], gateway["roleArn"])

# Add as target
target_payload = {
    "lambdaArn": lambda_arn,
    "toolSchema": {
        "inlinePayload": [
            {
                "name": "calculate_sum",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "multiply",
                "description": "Multiply two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "First number"},
                        "y": {"type": "number", "description": "Second number"}
                    },
                    "required": ["x", "y"]
                }
            }
        ]
    }
}

target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="CustomCalculator",
    target_type="lambda",
    target_payload=target_payload
)

print(f"✓ Custom Lambda target added: {target['targetId']}")
print("\nRun 'python run_agent.py' and try: 'Calculate the sum of 42 and 58'")
```

Run: `python create_custom_lambda.py` then `python run_agent.py` to test.

</details>

If you're excited and want to learn more about Gateways and the other Target types. Continue through this guide.

## Adding Your Own APIs

### NASA API Integration

Integrate real APIs like NASA’s Astronomy Picture of the Day. Get your API key from https://api.nasa.gov/ (instant via email), then create `add_nasa_api.py`:

 This example shows how to add external REST APIs to your Gateway, making them available as tools for your agent.


```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json

with open("gateway_config.json", "r") as f:
    config = json.load(f)

client = GatewayClient(region_name=config["region"])

nasa_spec = {
    "openapi": "3.0.0",
    "info": {"title": "NASA API", "version": "1.0.0"},
    "servers": [{"url": "https://api.nasa.gov"}],
    "paths": {
        "/planetary/apod": {
            "get": {
                "operationId": "getAstronomyPictureOfDay",
                "summary": "Get NASA's Astronomy Picture of the Day",
                "parameters": [
                    {
                        "name": "date",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": "Date in YYYY-MM-DD format"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "explanation": {"type": "string"},
                                        "url": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

gateway = client.client.get_gateway(gatewayIdentifier=config["gateway_id"])

nasa_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="NasaApi",
    target_type="openApiSchema",
    target_payload={"inlinePayload": json.dumps(nasa_spec)},
    credentials={
        "api_key": "YOUR_NASA_API_KEY",  # Replace with your key
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "api_key"
    }
)

print(f"✓ NASA API added! Try: 'Get NASA's astronomy picture for 2024-12-25'")
print("Run 'python run_agent.py' and try: 'Get NASA's astronomy picture for 2024-12-25'")
```


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

Use the following code to add an Open API target.
**Note: don't forget to add your api_key below.**
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

If you have an API that uses a key stored in a header value you can set the `credentials` field to the following.
**Note don't forget to fill in the api key and parameter name below.**
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


<details>
<summary>Advanced: AWS PrivateLink for VPC Connectivity</summary>

Create private connection between your VPC and Gateway:

```bash
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-12345678 \
    --service-name com.amazonaws.region.bedrock-agentcore.gateway
```

</details>

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
