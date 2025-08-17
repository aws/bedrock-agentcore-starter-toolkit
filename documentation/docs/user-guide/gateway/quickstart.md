# QuickStart: A Fully Managed MCP Server in 5 Minutes! 🚀

Amazon Bedrock AgentCore Gateway provides an easy and secure way for developers to build, deploy, discover, and connect to tools at scale. AI agents need tools to perform real-world tasks—from querying databases to sending messages to analyzing documents. With Gateway, developers can convert APIs, Lambda functions, and existing services into Model Context Protocol (MCP)-compatible tools and make them available to agents through Gateway endpoints with just a few lines of code. Gateway supports OpenAPI, Smithy, and Lambda as input types, and is the only solution that provides both comprehensive ingress authentication and egress authentication in a fully-managed service. Gateway eliminates weeks of custom code development, infrastructure provisioning, and security implementation so developers can focus on building innovative agent applications.

In the quick start guide you will learn how to set up a Gateway and integrate it into your agents using the AgentCore Starter Toolkit. You can find more comprehensive guides and examples [**here**](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/02-AgentCore-gateway).

**Note: The AgentCore Starter Toolkit is intended to help developers get started quickly. The Boto3 Python library provides the most comprehensive set of operations for Gateways and Targets. You can find the Boto3 documentation [here](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html). For complete documentation see the [**developer guide**](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)**


## Prerequisites

⚠️ Before starting, make sure you have:

- **AWS Account** with credentials configured (`aws configure`). 
- **Python 3.10+** installed.
- **Access to** Anthropic's Sonnet 3.7 (or another model) for running the demo agent below.

## Step 1: Install and Create Your Agent

```bash
pip install boto3
pip install bedrock-agentcore-starter-toolkit
pip install strands-agents
```

## Python Quick Start
Let's walk through how you can get started quickly using the Bedrock AgentCore Starter Toolkit.

### Setup
Start by importing the client needed to create Gateways:
```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json
import logging

region = "us-east-1"
client = GatewayClient(region_name=region)
client.logger.setLevel(logging.DEBUG)

```

### Creating an OAuth Authorization Server
🔒 Gateways are secured by OAuth authorization servers which ensure that only allowed users can access your Gateway. Let's create an OAuth authorization server to use with this Gateway. If you already have an OAuth authorization server, you can skip this step. 
```python
# create cognito authorizer
cognito_response = client.create_oauth_authorizer_with_cognito("TestGateway")
```

### Creating a Gateway
🌉 Now, let's create a Gateway.
```python
# create the gateway.
gateway = client.create_mcp_gateway(
    # the name of the Gateway - if you don't set one, one will be generated.
    name=None,
    # the role arn that the Gateway will use - if you don't set one, one will be created. 
    # NOTE: if you are using your own role make sure it has a trust policy that trusts bedrock-agentcore.amazonaws.com
    role_arn=None,
    # the OAuth authorization server details. If you are providing your own authorization server, then pass an input of the following form: {"customJWTAuthorizer": {"allowedClients": ["<INSERT CLIENT ID>"], "discoveryUrl": "<INSERT DISCOVERY URL">}}
    authorizer_config=cognito_response["authorizer_config"],
    # enable semantic search
    enable_semantic_search=True,
)
```

Now that we have a Gateway set up let's add a target. Targets can be Lambda functions, Open API schemas, or Smithy schemas (another type of API schema). Each Gateway can have multiple targets and each target can have many APIs. 

### Adding Lambda Targets

🛠️ Let's add a Lambda function target. This code will automatically create a Lambda function for you and will add the appropriate target configuration. If you want to add your own Lambda ARN / customize the schema, skip this step.

```python
# create a lambda target.
lambda_target = client.create_mcp_gateway_target(
    # the gateway created in the previous step
    gateway=gateway,
    # the name of the Target - if you don't set one, one will be generated.
    name=None,
    # the type of the Target
    target_type="lambda",
    # the target details - set this to define your own lambda if you pre-created one. Otherwise leave this None and one will be created for you.
    target_payload=None,
     # you will see later in the tutorial how to use this to connect to APIs using API keys and OAuth credentials.
    credentials=None,
)

```

<details>
<summary>
<strong> ➡️ Adding a custom Lambda</strong>
</summary>
Each Lambda target needs a schema defining the tools that the Lambda function implements. Your agent will see this schema and will send requests to your Lambda function in this format. You can decide how to implement the code for these tools in your Lambda. 

The schema has the following structure. **⚠️ Note don't forget to fill in the lambdaArn with your function ARN**

```python hl_lines="1"
lambda_target_payload = {
    "lambdaArn": "<INSERT YOUR LAMBDA FUNCTION ARN>",
    "toolSchema": {
        "inlinePayload": [
            # first tool
            {
                # name of the tool
                "name": "get_weather",
                # description of the tool
                "description": "Get weather for a location",
                "inputSchema": {
                    "type": "object",
                    # parameters of the tool
                    "properties": {
                        # first parameter, named "location"
                        "location": {
                            # type of the parameter, must be one of string | number | object | array | boolean | integer
                            "type": "string",
                            # description of the parameter
                            "description": "the location e.g. seattle, wa"
                        }
                    },
                    # which parameters are required to invoke this tool
                    "required": [
                        "location"
                    ]
                }
            },
            # second tool
            {
                "name": "get_time",
                "description": "Get time for a timezone",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "timezone"
                    ]
                }
            }
        ]
    }
}
```
You can create a target with this schema with the following:
```python
lambda_target = client.create_mcp_gateway_target(
    # the gateway created in the previous step
    gateway=gateway,
    # the name of the Target - if you don't set one, one will be generated.
    name=None,
    # the type of the Target
    target_type="lambda",
    # the target details - set this to define your own lambda if you pre-created one. Otherwise leave this None and one will be created for you.
    target_payload=lambda_target_payload
     # you will see later in the tutorial how to use this to connect to APIs using API keys and OAuth credentials.
    credentials=None,
)
```

Here is an example of a simple Lambda function that implements these tools.
```python
import json

def lambda_handler(event, context):
    # Extract tool name from context
    tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', 'unknown')

    if 'get_weather' in tool_name:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'location': event.get('location', 'Unknown'),
                'temperature': '72°F',
                'conditions': 'Sunny'
            })
        }
    elif 'get_time' in tool_name:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'timezone': event.get('timezone', 'UTC'),
                'time': '2:30 PM'
            })
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Unknown tool'})
        }
```
</details>


### Using the Gateway

🔐 To use this Gateway, we first need to obtain an OAuth access token. If you followed the steps to create a Cognito authorization server then you can obtain an access token with the following code:
```python
# get access token
access_token = client.get_access_token_for_cognito(cognito_response["client_info"])
```

🗒️ Copy and paste the below code to set up a simple agent that we can use to test out the Gateway. Note AgentCore Gateway can integrate with any Agent that uses MCP including agents / code not running on AWS. 

```python
from strands import Agent
import logging
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client 
import os

def create_streamable_http_transport(mcp_url: str, access_token: str):
       return streamablehttp_client(mcp_url, headers={"Authorization": f"Bearer {access_token}"})

def get_full_tools_list(client):
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

def run_agent(mcp_url: str, access_token: str, bedrock_model_id: str):
    bedrockmodel = BedrockModel(
        inference_profile_id=bedrock_model_id,
        streaming=True,
    )
     
    mcp_client = MCPClient(lambda: create_streamable_http_transport(mcp_url, access_token))
     
    with mcp_client:
        tools = get_full_tools_list(mcp_client)
        print(f"Found the following tools: {[tool.tool_name for tool in tools]}")
        agent = Agent(model=bedrockmodel,tools=tools)
        print("\nThis is an interactive Strands Agent. Ask me something. When you're finished, say exit or quit: ")
        while True:
            user_input = input()
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break
            print("\nThinking...\n")
            agent(user_input)
```

✅ Now, let's run the agent:
```python
# Run your agent!
run_agent(gateway["gatewayUrl"], access_token, "anthropic.claude-3-7-sonnet-20250219-v1:0")
```

---
**🥳🥳🥳 Congratulations - you successfully built an agent with MCP tools powered by AgentCore Gateway!**
--


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

