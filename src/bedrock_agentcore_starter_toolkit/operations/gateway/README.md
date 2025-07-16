# Bedrock AgentCore Gateway

Bedrock AgentCore Gateway is a primitive within the Bedrock AgentCore SDK that enables you to:
- Convert REST APIs (OpenAPI) into MCP tools
- Expose Lambda functions as MCP tools
- Handle authentication automatically with EZ Auth
- Enable semantic search across your tools

## Quick Start

### Using the CLI (Recommended)

```bash
# Create a Gateway with Lambda target
agentcore create_mcp_gateway \
  --name my-gateway \
  --target arn:aws:lambda:us-west-2:123:function:MyFunction \
  --execution-role arn:aws:iam::123:role/BedrockAgentCoreGatewayRole

# Short form
agentcore create_mcp_gateway \
  -n my-gateway \
  -t arn:aws:lambda:us-west-2:123:function:MyFunction \
  -r BedrockAgentCoreGatewayRole

# Create a Gateway to use with targets defined in OpenAPI or Smithy
agentcore create_mcp_gateway \
--region us-west-2 \
--name gateway-name

# Create a Gateway Target with predefined smithy model
agentcore create_mcp_gateway_target \
--region us-east-1 \
--gateway-arn arn:aws:bedrock-agentcore:us-east-1:123:gateway/gateway-id \
--gateway-url https://gateway-id.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp \
--role-arn arn:aws:iam::123:role/BedrockAgentCoreGatewayRole \
--target-type smithyModel

# Create a Gateway Target with OpenAPI target (OAuth with API Key)
agentcore create_mcp_gateway_target \
--region us-east-1 \
--gateway-arn arn:aws:bedrock-agentcore:us-east-1:123:gateway/gateway-id \
--gateway-url https://gateway-id.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp \
--role-arn arn:aws:iam::123:role/BedrockAgentCoreGatewayRole \
--target-type openApiSchema
--credentials "{\"api_key\": \"Bearer 123234bc\", \"credential_location\": \"HEADER\", \"credential_parameter_name\": \"Authorization\"}" \
--target-payload "{\"s3\": \"s3://mybucket/openApiSchema.json\"}}"

# Create a Gateway Target with OpenAPI target (OAuth with credential provider)
agentcore create_mcp_gateway_target \
--region us-east-1 \
--gateway-arn arn:aws:bedrock-agentcore:us-east-1:123:gateway/gateway-id \
--gateway-url https://gateway-id.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp \
--role-arn arn:aws:iam::123:role/BedrockAgentCoreGatewayRole \
--target-type openApiSchema
--credentials "{\"oauth2_provider_config\": { \"customOauth2ProviderConfig\": {\"oauthDiscovery\" : {\"authorizationServerMetadata\" : {\"issuer\" : \"<issuer>\",\"authorizationEndpoint\" : \"<authorizationEndpoint>\",\"tokenEndpoint\" : \"<tokenEndpoint>\"}},\"clientId\" : \"<clientId>\",\"clientSecret\" : \"<clientSecret>\" }}}" \
--target-payload "{\"s3\": \"s3://mybucket/openApiSchema.json\"}}"
```

The CLI automatically:
- Detects target type from ARN patterns or file extensions
- Sets up Cognito OAuth (EZ Auth)
- Detects your AWS region and account
- Builds full role ARN from role name


### Using the SDK

For programmatic access in scripts, notebooks, or CI/CD:

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json

# Initialize client
client = GatewayClient(region_name='us-west-2')

# EZ Auth - automatically sets up Cognito OAuth
cognito_result = client.create_oauth_authorizer_with_cognito("my-gateway")

# Create Gateway with OpenAPI schema target
gateway = client.create_mcp_gateway(
    name="my-gateway",
    role_arn="arn:aws:iam::123:role/BedrockAgentCoreGatewayExecutionRole",
    authorizer_config=cognito_result['authorizer_config']
)

target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="sample_target",
    target_type='openApiSchema',
    target_payload= {
        "s3": {
            "uri": "s3://openapischemas/sample-openapi-schema.json",
            "bucketOwnerAccountId": "012345678912"
        }
    },
    credentials={
        "api_key": "abc123",
        "credential_location": "HEADER",
        "credential_parameter_name": "Authorization"
    }
)
print(f"MCP Endpoint: {gateway['gatewayUrl']}")
print(f"OAuth Credentials:")
print(f"  Client ID: {cognito_result['client_info']['client_id']}")
print(f"  Client Secret: {cognito_result['client_info']['client_secret']}")
print(f"  Scope: {cognito_result['client_info']['scope']}")
```

## Key Features

### EZ Auth
Eliminates the complexity of OAuth setup:
```python
# Without EZ Auth: 8+ manual steps
# With EZ Auth: 1 line
cognito_result = client.create_oauth_authorizer_with_cognito("my-gateway")
```

### Semantic Search
Enable intelligent tool discovery:
```python
gateway = client.create_mcp_gateway(
    name="my-gateway",
    role_arn="arn:aws:iam::123:role/BedrockAgentCoreGatewayExecutionRole",
    authorizer_config=cognito_result['authorizer_config'],
    enable_semantic_search=True # Enable semantic search.
)
```

### Multiple Target Types

#### Lambda Functions
```python
# Auto-generated schema (default)
gateway = client.create_mcp_gateway(
    name="my-gateway",
    role_arn="arn:aws:iam::123:role/BedrockAgentCoreGatewayExecutionRole",
    authorizer_config=cognito_result['authorizer_config']
)

# Create a lambda target
lambda_target = client.create_mcp_gateway_target(
    name="lambda-target",
    gateway=gateway,
    target_type='lambda'
)
```

#### OpenAPI (REST APIs)
```python
# Inline OpenAPI
openapi_spec = {
    "openapi": "3.0.0",
    "info": {"title": "My API", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "responses": {"200": {"description": "Success"}}
            }
        }
    }
}
openAPI_inline_target = client.create_mcp_gateway_target(
    name="inlineTarget",
    gateway=gateway,
    credentials={
        "api_key": "abc123",
        "credential_location": "HEADER",
        "credential_parameter_name": "Authorization"
    },
    target_type='openApiSchema',
    target_payload= {
        "inlinePayload": openapi_spec
    }
)

# From S3
openAPI_target = client.create_mcp_gateway_target(
    name="s3target",
    gateway=gateway,
    credentials={
        "api_key": "abc123",
        "credential_location": "HEADER",
        "credential_parameter_name": "Authorization"
    },
    target_type='openApiSchema',
    target_payload= {
        "s3": {
            "uri": "s3://openapischemas/sample-openapi-schema.json",
            "bucketOwnerAccountId": "012345678912"
        }
    }
)
```

## MCP Integration

Once created, use any MCP client to interact with your Gateway:

```python
import httpx

# Get token
token = client.get_access_token_for_cognito(cognito_result['client_info'])

# List tools
async with httpx.AsyncClient() as http:
    response = await http.post(
        gateway.get_mcp_url(),
        headers={"Authorization": f"Bearer {token}"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
    )
    tools = response.json()

# Invoke a tool
response = await http.post(
    gateway.get_mcp_url(),
    headers={"Authorization": f"Bearer {token}"},
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "listUsers",
            "arguments": {}
        }
    }
)
```

## Prerequisites

**AWS Account**: Must be allowlisted for Bedrock AgentCore beta
**IAM Execution Role**: With trust relationship to BedrockAgentCore service
**Permissions**: Role needs access to your backends (Lambda invoke, S3 read, etc.)
**Custom Boto3 SDK**: Download from Bedrock AgentCore documentation

## Testing

See `tests/bedrock_agentcore/gateway/` for integration tests covering all target types.

## API Reference

### GatewayClient

- `create_oauth_authorizer_with_cognito(gateway_name)` - Set up Cognito OAuth automatically
- `create_mcp_gateway(...)` - Create a gateway
- `create_mcp_gateway_target(...)` - Create a gateway target
- `get_test_token_for_cognito(client_info)` - Get OAuth token for testing

### List of all builtin schemas
```doc
1. confluence
2. onedrive
3. dynamodb
4. cloudwatch
5. slack
6. smartsheet
7. sap-business-partner
8. tavily
9. jira
10. sap-product-master-data
11. genericHTTP
12. sap-material-stock
13. sap-physical-inventory
14. salesforce
15. servicenow
16. bambooHR
17. brave-search
18. msExchange
19. sap-bill-of-material
20. sharepoint
21. asana
22. zendesk
23. msTeams
24. pagerduty
25. zoom
26. bedrock-runtime
27. bedrock-agent-runtime
```
