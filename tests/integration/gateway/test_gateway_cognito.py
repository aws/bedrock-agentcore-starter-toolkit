import json
import logging
import os
import uuid

import boto3

from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gateway-test")


def test_cognito_gateway():
    region = os.environ.get("AWS_REGION", "us-west-2")

    # Initialize the client
    client = GatewayClient(region_name=region)

    # Your account ID
    account_id = boto3.client("sts").get_caller_identity()["Account"]

    # Generate a unique identifier
    unique_id = str(uuid.uuid4())[:8]  # Using first 8 chars of a UUID

    # Configuration with unique name
    gateway_name = f"test-gateway-cognito-{unique_id}"
    execution_role_arn = f"arn:aws:iam::{account_id}:role/BedrockAgentCoreGatewayExecutionRole"

    # Define Lambda ARN
    lambda_arn = f"arn:aws:lambda:us-west-2:{account_id}:function:BedrockAgentCoreTestFunction"

    try:
        # Step 1: Create Cognito resources
        logger.info("🔐 Setting up Cognito OAuth...")
        cognito_result = client.create_oauth_authorizer_with_cognito(gateway_name)

        logger.info("\n📝 Cognito Setup Complete:")
        logger.info("  Client ID: %s", cognito_result["client_info"]["client_id"])
        logger.info("  User Pool ID: %s", cognito_result["client_info"]["user_pool_id"])
        logger.info("  Token Endpoint: %s", cognito_result["client_info"]["token_endpoint"])
        # Don't log client_secret

        # Step 2: Create Gateway with Cognito auth
        logger.info("\n🚀 Creating Gateway...")

        # Define Lambda configuration with tool schema
        lambda_config = {
            "arn": lambda_arn,
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
                {
                    "name": "get_time",
                    "description": "Get time for a timezone",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"timezone": {"type": "string"}},
                        "required": ["timezone"],
                    },
                },
            ],
        }

        gateway = client.create_mcp_gateway(
            name=gateway_name,
            role_arn=execution_role_arn,
            authorizer_config=cognito_result["authorizer_config"],
        )
        _ = client.create_mcp_gateway_target(gateway=gateway, target_type="lambda", target_payload=lambda_config)

        # Step 3: Get a test token
        logger.info("\n🎫 Getting test token...")
        test_token = client.get_access_token_for_cognito(cognito_result["client_info"])
        # Only show token prefix, mask the rest for security
        logger.info("✓ Got token: %s...[MASKED]", test_token[:10])

        # Step 4: Test the MCP endpoint
        logger.info("\n🧪 Testing MCP endpoint...")
        mcp_url = gateway["gatewayUrl"]
        logger.info("MCP URL: %s", mcp_url)

        # Test with curl command but mask the token
        logger.info("\n📋 Test with this curl command:")
        logger.info(
            """
curl -X POST '%s' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer [YOUR_TOKEN]' \\
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
        """,
            mcp_url,
        )

        # Save info for later use - mask the token in logs
        output_path = os.path.join(os.path.dirname(__file__), "gateway_info.json")
        with open(output_path, "w") as f:
            json.dump(
                {
                    "gateway_id": gateway.id,
                    "mcp_url": mcp_url,
                    "cognito_info": {
                        "client_id": cognito_result["client_info"]["client_id"],
                        "user_pool_id": cognito_result["client_info"]["user_pool_id"],
                        "token_endpoint": cognito_result["client_info"]["token_endpoint"],
                        "domain_prefix": cognito_result["client_info"]["domain_prefix"],
                    },
                    "test_token": "[TOKEN_MASKED_FOR_SECURITY]",  # Don't save the actual token
                },
                f,
                indent=2,
            )

        logger.info("\n✅ Gateway info saved to %s", output_path)

    except Exception as e:
        logger.error("❌ Error: %s", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_cognito_gateway()
