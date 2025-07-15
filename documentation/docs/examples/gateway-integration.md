# Gateway Integration Examples

## Lambda Function as MCP Tool

```python
from bedrock_agentcore.gateway import GatewayClient
import json

client = GatewayClient(region_name='us-west-2')

# Define Lambda tools with detailed schemas
lambda_config = {
    "arn": "arn:aws:lambda:us-west-2:123:function:DataProcessor",
    "tools": [
        {
            "name": "process_data",
            "description": "Process user data in JSON or CSV format",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data": {"type": "string"},
                    "format": {"type": "string"}  # Note: enum not supported, document in description
                },
                "required": ["data", "format"]
            }
        },
        {
            "name": "validate_data",
            "description": "Validate data structure",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data": {"type": "string"}
                },
                "required": ["data"]
            }
        }
    ]
}

# Create Gateway with semantic search enabled
cognito = client.create_oauth_authorizer_with_cognito("data-processor")
gateway = client.setup_gateway(
    gateway_name="data-processor",
    target_source=json.dumps(lambda_config),
    execution_role_arn="arn:aws:iam::123:role/ExecutionRole",
    authorizer_config=cognito['authorizer_config'],
    target_type='lambda',
    enable_semantic_search=True,
    description="Data processing gateway with validation tools"
)

print(f"Gateway created: {gateway.get_mcp_url()}")
```

## OpenAPI Integration

### From S3

```python
gateway = client.setup_gateway(
    gateway_name="my-api",
    target_source="s3://my-bucket/api-spec.json",
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config'],
    target_type='openapi'
)
```

### Inline OpenAPI Specification

```python
openapi_spec = {
    "openapi": "3.0.0",
    "info": {"title": "User API", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List all users",
                "responses": {"200": {"description": "User list"}}
            }
        },
        "/users/{id}": {
            "get": {
                "operationId": "getUser",
                "summary": "Get user by ID",
                "parameters": [{
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                }],
                "responses": {"200": {"description": "User found"}}
            }
        }
    }
}

gateway = client.setup_gateway(
    gateway_name="user-api",
    target_source=json.dumps(openapi_spec),
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config'],
    target_type='openapi'
)
```

### YAML OpenAPI (from file)

```python
import yaml

# Load YAML OpenAPI spec
with open('openapi.yaml', 'r') as f:
    yaml_content = f.read()
    openapi_spec = yaml.safe_load(yaml_content)

# Convert to JSON string for inline use
gateway = client.setup_gateway(
    gateway_name="yaml-api",
    target_source=json.dumps(openapi_spec),
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config'],
    target_type='openapi'
)

# Or use S3 (YAML files work directly)
gateway = client.setup_gateway(
    gateway_name="yaml-api",
    target_source="s3://my-bucket/openapi.yaml",
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config'],
    target_type='openapi'
)
```

## OAuth Token Management

When integrating Gateway with any agent framework, you'll need to handle OAuth tokens properly:

```python
import os
from datetime import datetime, timedelta
import httpx
import asyncio

class GatewayTokenManager:
    """Manages OAuth tokens with automatic refresh"""

    def __init__(self, client_id, client_secret, token_endpoint, scope):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = token_endpoint
        self.scope = scope
        self._token = None
        self._expires_at = None

    async def get_token(self):
        """Get valid token, refreshing if needed"""
        if self._token and self._expires_at > datetime.now():
            return self._token

        # Fetch new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'scope': self.scope
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            data = response.json()
            self._token = data['access_token']
            # Buffer expiry by 5 minutes
            expires_in = data.get('expires_in', 3600) - 300
            self._expires_at = datetime.now() + timedelta(seconds=expires_in)
            return self._token
```

## Generic Agent Integration

Here's how to integrate Gateway with any agent framework:

```python
import os
import asyncio
from bedrock_agentcore import BedrockAgentCoreApp

# Initialize token manager with Gateway credentials
token_manager = GatewayTokenManager(
    client_id=os.environ['GATEWAY_CLIENT_ID'],
    client_secret=os.environ['GATEWAY_CLIENT_SECRET'],
    token_endpoint=os.environ['GATEWAY_TOKEN_ENDPOINT'],
    scope=os.environ['GATEWAY_SCOPE']
)

# Gateway MCP endpoint
GATEWAY_URL = os.environ['GATEWAY_MCP_URL']

# Generic function to call Gateway tools
async def call_gateway_tool(tool_name: str, arguments: dict):
    """Call any tool exposed through Gateway"""
    token = await token_manager.get_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GATEWAY_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        )

        result = response.json()
        if 'error' in result:
            raise Exception(f"Tool error: {result['error']}")

        return result.get('result')

# Example: Using in your agent logic
async def process_user_request(user_message: str):
    # Parse intent from user message
    if "weather" in user_message.lower():
        # Extract location (this would be done by your agent's NLU)
        location = extract_location(user_message)
        weather_data = await call_gateway_tool("get_weather", {"location": location})
        return f"The weather in {location} is: {weather_data}"

    elif "user" in user_message.lower():
        # Get user information
        user_id = extract_user_id(user_message)
        user_data = await call_gateway_tool("getUser", {"id": user_id})
        return f"User information: {user_data}"

    return "I couldn't understand your request."
```

## Complete Example: Weather Agent

```python
from bedrock_agentcore.gateway import GatewayClient
import json
import asyncio
import httpx

# Step 1: Create Gateway
async def setup_weather_gateway():
    client = GatewayClient(region_name='us-west-2')

    # Configure Lambda with weather tools
    lambda_config = {
        "arn": "arn:aws:lambda:us-west-2:123:function:WeatherService",
        "tools": [
            {
                "name": "get_current_weather",
                "description": "Get current weather for a city",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "country": {"type": "string"}
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "get_forecast",
                "description": "Get 5-day weather forecast",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "days": {"type": "number"}
                    },
                    "required": ["city"]
                }
            }
        ]
    }

    # Create Gateway with EZ Auth
    cognito = client.create_oauth_authorizer_with_cognito("weather-service")
    gateway = client.setup_gateway(
        gateway_name="weather-service",
        target_source=json.dumps(lambda_config),
        execution_role_arn="arn:aws:iam::123:role/WeatherExecutionRole",
        authorizer_config=cognito['authorizer_config'],
        target_type='lambda',
        enable_semantic_search=True
    )

    return gateway, cognito['client_info']

# Step 2: Use the Gateway
async def weather_agent():
    gateway, client_info = await setup_weather_gateway()

    # Initialize token manager
    token_manager = GatewayTokenManager(
        client_id=client_info['client_id'],
        client_secret=client_info['client_secret'],
        token_endpoint=client_info['token_endpoint'],
        scope=client_info['scope']
    )

    # Get weather for multiple cities
    cities = ["Seattle", "New York", "London"]

    for city in cities:
        token = await token_manager.get_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                gateway.get_mcp_url(),
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "get_current_weather",
                        "arguments": {"city": city}
                    }
                }
            )

            result = response.json()
            print(f"Weather in {city}: {result.get('result')}")

# Run the agent
if __name__ == "__main__":
    asyncio.run(weather_agent())
```
