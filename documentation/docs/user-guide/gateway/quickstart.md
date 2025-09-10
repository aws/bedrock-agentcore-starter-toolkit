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

## Step 0: Setup Folder and Virtual Environment

Create a new folder for this quickstart and initialize a Python virtual environment:

```bash
mkdir agentcore-gateway-quickstart
cd agentcore-gateway-quickstart
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Step 1: Install Dependencies

```bash
pip install boto3 bedrock-agentcore-starter-toolkit strands-agents
```

## Complete Working Example

Save this as `gateway_quickstart.py` and run it to create your Gateway and test it with an agent:

```python
"""
gateway_quickstart.py - Complete Gateway setup and test
This script creates a Gateway, adds tools, and runs an interactive agent
"""

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import json
import logging
import time

# ============= CONFIGURATION =============
# IMPORTANT: Set your AWS region here
REGION = "us-east-1"  # Change to your preferred region
MODEL_ID = "anthropic.claude-3-7-sonnet-20250219-v1:0"  # Or your preferred model

def setup_gateway():
    """Create Gateway with OAuth authorization and Lambda tools"""

    print(f"\n📍 Setting up Gateway in region: {REGION}")
    print("=" * 50)

    # Initialize the Gateway client
    client = GatewayClient(region_name=REGION)
    client.logger.setLevel(logging.INFO)

    # Step 1: Create OAuth authorizer using Cognito
    # This automatically sets up a Cognito user pool for authentication
    print("\n1️⃣ Creating OAuth authorization server...")
    cognito_response = client.create_oauth_authorizer_with_cognito("TestGateway")
    print("✅ OAuth authorizer created")

    # Step 2: Create the Gateway
    print("\n2️⃣ Creating Gateway...")
    gateway = client.create_mcp_gateway(
        # name=None,  # Optional: Gateway name (auto-generated if not provided)
        # role_arn=None,  # Optional: IAM role ARN (auto-created if not provided)
        authorizer_config=cognito_response["authorizer_config"],  # Required: OAuth config
        enable_semantic_search=True  # Optional: Enable tool search capabilities
    )
    print(f"✅ Gateway created: {gateway['gatewayId']}")
    print(f"   Gateway URL: {gateway['gatewayUrl']}")

    # Step 3: Add Lambda target with test tools
    print("\n3️⃣ Adding Lambda target with tools...")
    lambda_target = client.create_mcp_gateway_target(
        gateway=gateway,  # Required: The gateway object from step 2
        # name=None,  # Optional: Target name (auto-generated if not provided)
        target_type="lambda",  # Required: Type of target (lambda, openApiSchema, smithyModel)
        # target_payload=None,  # Optional: Custom Lambda config (creates test Lambda if None)
        # credentials=None  # Optional: For API targets requiring API keys or OAuth
    )
    print(f"✅ Lambda target added: {lambda_target['targetId']}")

    # Step 4: Get access token for testing
    print("\n4️⃣ Getting OAuth access token...")
    access_token = client.get_access_token_for_cognito(cognito_response["client_info"])
    print("✅ Access token obtained")

    # Wait for Gateway to be fully ready
    print("\n⏳ Waiting for Gateway to be ready (DNS propagation)...")
    time.sleep(10)

    return {
        "gateway": gateway,
        "access_token": access_token,
        "client_info": cognito_response["client_info"],
        "client": client
    }

def run_interactive_agent(config):
    """Run an interactive agent that uses the Gateway tools"""

    print("\n5️⃣ Starting Interactive Agent")
    print("=" * 50)

    def create_transport():
        return streamablehttp_client(
            config['gateway']['gatewayUrl'],
            headers={"Authorization": f"Bearer {config['access_token']}"}
        )

    # Initialize Bedrock model
    bedrock_model = BedrockModel(
        inference_profile_id=MODEL_ID,
        streaming=True,
    )

    # Initialize MCP client
    mcp_client = MCPClient(create_transport)

    with mcp_client:
        # List available tools
        tools = []
        pagination_token = None
        while True:
            tmp_tools = mcp_client.list_tools_sync(pagination_token=pagination_token)
            tools.extend(tmp_tools)
            if not tmp_tools.pagination_token:
                break
            pagination_token = tmp_tools.pagination_token

        print(f"\n📋 Available tools: {[tool.tool_name for tool in tools]}")

        # Create agent
        agent = Agent(model=bedrock_model, tools=tools)

        print("\n🤖 Interactive Agent Ready!")
        print("Ask questions like:")
        print("  - What's the weather in Seattle?")
        print("  - What time is it in EST?")
        print("Type 'exit' or 'quit' to stop.\n")

        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break

            print("\n🤔 Thinking...\n")
            response = agent(user_input)
            print(f"Agent: {response.message['content']}\n")

def save_configuration(config):
    """Save configuration for later use"""

    # Save config for reuse
    config_to_save = {
        "gateway_url": config['gateway']['gatewayUrl'],
        "gateway_id": config['gateway']['gatewayId'],
        "region": REGION,
        "client_info": config['client_info']
    }

    with open("gateway_config.json", "w") as f:
        json.dump(config_to_save, f, indent=2)

    print("\n💾 Configuration saved to gateway_config.json")
    print("\n📚 Next steps:")
    print(f"   1. View in console: https://console.aws.amazon.com/bedrock-agentcore/")
    print(f"   2. Check logs: /aws/bedrock-agentcore/gateways/{config['gateway']['gatewayId']}")
    print("   3. Add real APIs using the examples in this guide")

def main():
    """Main execution flow"""
    try:
        # Setup Gateway
        config = setup_gateway()

        # Save configuration
        save_configuration(config)

        # Run interactive agent
        run_interactive_agent(config)

        print("\n✅ Success! Your Gateway is ready for production use.")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials: aws configure list")
        print("2. Verify IAM permissions for bedrock-agentcore:*")
        print("3. Ensure Claude Sonnet 3.7 is enabled in Bedrock console")
        print("4. Try a different region if the service isn't available")

if __name__ == "__main__":
    main()
```

## Run the Complete Example

```bash
python gateway_quickstart.py
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

After verifying the basic setup works, add real APIs to your Gateway:

### Example: NASA Mars Weather API

```python
"""
add_nasa_api.py - Add NASA Mars weather API to existing Gateway
"""

import json
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

# Load saved configuration
with open("gateway_config.json", "r") as f:
    config = json.load(f)

client = GatewayClient(region_name=config['region'])

# Reconstruct gateway object
gateway = {
    "gatewayId": config['gateway_id'],
    "gatewayUrl": config['gateway_url'],
    "roleArn": "YOUR_ROLE_ARN"  # Get from console or initial output
}

# NASA API specification (simplified for readability)
nasa_spec = {
    "openapi": "3.0.3",
    "info": {
        "title": "NASA InSight Mars Weather API",
        "description": "Returns Mars weather data",
        "version": "1.0.0"
    },
    "servers": [{"url": "https://api.nasa.gov"}],
    "paths": {
        "/insight_weather/": {
            "get": {
                "operationId": "getMarsWeather",
                "summary": "Get Mars weather data",
                "parameters": [
                    {
                        "name": "feedtype",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "enum": ["json"]}
                    },
                    {
                        "name": "ver",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "enum": ["1.0"]}
                    }
                ],
                "responses": {
                    "200": {"description": "Weather data"}
                }
            }
        }
    }
}

# Add the API (get free API key from https://api.nasa.gov/)
target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="nasa-mars-weather",
    target_type="openApiSchema",
    target_payload={"inlinePayload": json.dumps(nasa_spec)},
    credentials={
        "api_key": "YOUR_NASA_API_KEY",  # Get from api.nasa.gov
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "api_key"
    }
)

print(f"✅ NASA API added: {target['targetId']}")
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
