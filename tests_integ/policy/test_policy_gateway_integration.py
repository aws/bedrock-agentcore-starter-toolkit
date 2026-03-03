"""AgentCore Gateway with Policy Enforcement Integration Test.

This script demonstrates:
1. Creating a gateway with OAuth and Lambda target
2. Setting up policy engine with refund limit ($1000)
3. Testing policy enforcement (direct HTTP and agent)
4. Policy Generation: Generating policies from natural language
5. Policy Engine with Encryption Key and Tags
6. Creating Policies from Generation Assets
7. Cleanup
"""

import json
import time

import boto3
import requests
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
from bedrock_agentcore_starter_toolkit.operations.policy.client import PolicyClient
from bedrock_agentcore_starter_toolkit.utils.lambda_utils import create_lambda_function

# Configuration
REGION = "us-east-1"
REFUND_LIMIT = 1000


def initialize_clients(region):
    """Initialize gateway and policy clients once."""
    return {
        "gateway": GatewayClient(region_name=region),
        "policy": PolicyClient(region_name=region),
    }


def setup_infrastructure(clients):
    """Setup gateway, Lambda, and policy engine."""
    print("\n" + "=" * 60)
    print("Setting up infrastructure")
    print("=" * 60 + "\n")

    # Lambda code
    refund_lambda_code = """
def lambda_handler(event, context):
    amount = event.get('amount', 0)
    return {
        "status": "success",
        "message": f"Refund of ${amount} processed successfully",
        "amount": amount
    }
"""

    # Create gateway
    gateway_client = clients["gateway"]
    policy_client = clients["policy"]

    cognito_response = gateway_client.create_oauth_authorizer_with_cognito("PolicyDemo")
    gateway = gateway_client.create_mcp_gateway(
        name=f"RefundGateway{int(time.time())}",
        authorizer_config=cognito_response["authorizer_config"],
        enable_semantic_search=False,
    )
    gateway_client.fix_iam_permissions(gateway)
    time.sleep(30)

    # Create Lambda
    session = boto3.Session(region_name=REGION)
    lambda_arn = create_lambda_function(
        session=session,
        logger=gateway_client.logger,
        function_name=f"RefundTool-{int(time.time())}",
        lambda_code=refund_lambda_code,
        runtime="python3.13",
        handler="lambda_function.lambda_handler",
        gateway_role_arn=gateway["roleArn"],
        description="Refund tool for policy demo",
    )
    time.sleep(60)

    # Add Lambda target
    gateway_client.create_mcp_gateway_target(
        gateway=gateway,
        name="RefundTarget",
        target_type="lambda",
        target_payload={
            "lambdaArn": lambda_arn,
            "toolSchema": {
                "inlinePayload": [
                    {
                        "name": "process_refund",
                        "description": "Process a customer refund",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"amount": {"type": "integer", "description": "Refund amount in dollars"}},
                            "required": ["amount"],
                        },
                    }
                ]
            },
        },
    )

    # Create policy
    engine = policy_client.create_or_get_policy_engine(
        name=f"RefundPolicyEngine_{int(time.time())}", description="Policy engine for refund governance"
    )

    cedar_statement = (
        f"permit(principal, "
        f'action == AgentCore::Action::"RefundTarget___process_refund", '
        f'resource == AgentCore::Gateway::"{gateway["gatewayArn"]}") '
        f"when {{ context.input.amount < {REFUND_LIMIT} }};"
    )

    policy_client.create_or_get_policy(
        policy_engine_id=engine["policyEngineId"],
        name=f"refund_limit_policy_{int(time.time())}",
        description=f"Allow refunds under ${REFUND_LIMIT}",
        definition={"cedar": {"statement": cedar_statement}},
    )

    # Attach policy to gateway
    gateway_client.update_gateway_policy_engine(
        gateway_identifier=gateway["gatewayId"], policy_engine_arn=engine["policyEngineArn"], mode="ENFORCE"
    )

    # Save config
    config = {
        "gateway_url": gateway["gatewayUrl"],
        "gateway_id": gateway["gatewayId"],
        "gateway_arn": gateway["gatewayArn"],
        "policy_engine_id": engine["policyEngineId"],
        "client_info": cognito_response["client_info"],
        "region": REGION,
        "refund_limit": REFUND_LIMIT,
    }

    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("✅ Setup complete")
    print(f"Gateway: {gateway['gatewayUrl']}")
    print(f"Policy: Allow refunds < ${REFUND_LIMIT}")

    return config


def test_direct_http(config, access_token):
    """Test policy enforcement via direct HTTP."""
    print("\n" + "=" * 60)
    print("Testing Direct HTTP")
    print("=" * 60 + "\n")

    def test_refund(amount):
        response = requests.post(
            config["gateway_url"],
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "RefundTarget___process_refund", "arguments": {"amount": amount}},
            },
        )
        return response.text

    print(f"Test $500: {test_refund(500)}")
    print(f"Test $2000: {test_refund(2000)}")


def test_agent(config, access_token):
    """Test policy enforcement via agent."""
    print("\n" + "=" * 60)
    print("Testing Agent")
    print("=" * 60 + "\n")

    def get_tools(mcp_client):
        tools, token = [], None
        while True:
            result = mcp_client.list_tools_sync(pagination_token=token)
            tools.extend(result)
            if not result.pagination_token:
                break
            token = result.pagination_token
        return tools

    model = BedrockModel(inference_profile_id="anthropic.claude-3-7-sonnet-20250219-v1:0", streaming=True)
    mcp_client = MCPClient(
        lambda: streamablehttp_client(config["gateway_url"], headers={"Authorization": f"Bearer {access_token}"})
    )

    with mcp_client:
        agent = Agent(model=model, tools=get_tools(mcp_client))

        print("\n=== $500 Refund ===")
        print(agent("Process a refund of $500"))

        print("\n=== $2000 Refund ===")
        print(agent("Process a refund of $2000"))

        print("\n=== $500 Refund (again) ===")
        print(agent("Process a refund of $500"))


def test_policy_generation(config, clients):
    """Test policy generation from natural language."""
    print("\n" + "=" * 60)
    print("Testing Policy Generation")
    print("=" * 60 + "\n")

    policy_client = clients["policy"]
    natural_language_input = "Allow refunds for amounts less than $500"

    print(f"📝 Natural Language Input: '{natural_language_input}'")
    print(f"🎯 Target Resource: {config['gateway_arn']}")
    print("\n⏳ Generating Cedar policy...\n")

    try:
        result = policy_client.generate_policy(
            policy_engine_id=config["policy_engine_id"],
            name=f"policy_gen_test_{int(time.time())}",
            resource={"arn": config["gateway_arn"]},
            content={"rawText": natural_language_input},
            fetch_assets=True,
        )

        print("✅ Policy generation complete!\n")
        print(f"Generation ID: {result['policyGenerationId']}")
        print(f"Status: {result['status']}")

        if "generatedPolicies" in result and result["generatedPolicies"]:
            print(f"\n📜 Generated {len(result['generatedPolicies'])} Cedar Policies:\n")
            for i, policy_asset in enumerate(result["generatedPolicies"], 1):
                definition = policy_asset.get("definition", {})
                cedar = definition.get("cedar", {})
                statement = cedar.get("statement", "N/A")
                print(f"Policy {i}:")
                print(f"{statement}")
                print()
        else:
            print("\n⚠️ No policies were generated")

    except Exception as e:
        print(f"❌ Error during policy generation: {str(e)}")

    print("=" * 60)


def test_encryption_and_tags(config, clients):
    """Test policy engine with encryption key and tags."""
    print("\n" + "=" * 60)
    print("Testing Policy Engine with Encryption Key and Tags")
    print("=" * 60 + "\n")

    policy_client = clients["policy"]

    # Create KMS key
    print("🔑 Creating KMS key...")
    kms_client = boto3.client("kms", region_name=config["region"])
    kms_key = kms_client.create_key(
        Description="Test key for policy engine encryption", KeyUsage="ENCRYPT_DECRYPT", Origin="AWS_KMS"
    )
    encryption_key_arn = kms_key["KeyMetadata"]["Arn"]
    kms_key_id = kms_key["KeyMetadata"]["KeyId"]
    print(f"✅ KMS key created: {kms_key_id}\n")

    tags = {"Environment": "Test", "Team": "Security", "Purpose": "RefundGovernance"}
    time.sleep(60)
    print(f"🔐 Encryption Key ARN: {encryption_key_arn}")
    print(f"🏷️  Tags: {json.dumps(tags, indent=2)}")
    print("\n⏳ Creating policy engine...\n")

    try:
        secure_engine = policy_client.create_or_get_policy_engine(
            name=f"SecureRefundEngine_{int(time.time())}",
            description="Policy engine with encryption and tags",
            encryption_key_arn=encryption_key_arn,
            tags=tags,
        )

        print("✅ Policy engine created!\n")
        print(f"Engine ID: {secure_engine['policyEngineId']}")
        print(f"Status: {secure_engine['status']}")
        print(f"ARN: {secure_engine['policyEngineArn']}")

        config["secure_engine_id"] = secure_engine["policyEngineId"]
        config["secure_engine_arn"] = secure_engine["policyEngineArn"]
        config["kms_key_id"] = kms_key_id
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)

    except Exception as e:
        print(f"❌ Error creating policy engine: {str(e)}")
        kms_client.schedule_key_deletion(KeyId=kms_key_id, PendingWindowInDays=7)
        print("🗑️  KMS key scheduled for deletion")

    print("=" * 60)


def test_secure_policy_engine_enforcement(config, access_token, clients):
    """Test policy enforcement with secure policy engine."""
    print("\n" + "=" * 60)
    print("Testing Secure Policy Engine Enforcement")
    print("=" * 60 + "\n")

    if "secure_engine_id" not in config:
        print("⚠️ Secure engine not found, skipping test")
        return

    policy_client = clients["policy"]
    gateway_client = clients["gateway"]

    # Create policy for secure engine with $500 limit
    secure_limit = 500
    cedar_statement = (
        f"permit(principal, "
        f'action == AgentCore::Action::"RefundTarget___process_refund", '
        f'resource == AgentCore::Gateway::"{config["gateway_arn"]}") '
        f"when {{ context.input.amount < {secure_limit} }};"
    )

    print(f"📝 Creating policy with ${secure_limit} limit for secure engine...")
    policy = policy_client.create_or_get_policy(
        policy_engine_id=config["secure_engine_id"],
        name=f"secure_refund_policy_{int(time.time())}",
        description=f"Allow refunds under ${secure_limit}",
        definition={"cedar": {"statement": cedar_statement}},
    )
    print(f"✅ Policy created: {policy['policyId']}\n")

    # Attach secure policy engine to gateway
    print("🔗 Attaching secure policy engine to gateway...")
    gateway_client.update_gateway_policy_engine(
        gateway_identifier=config["gateway_id"], policy_engine_arn=config["secure_engine_arn"], mode="ENFORCE"
    )
    print("✅ Secure policy engine attached\n")

    time.sleep(5)

    # Test with secure policy engine
    def test_refund(amount):
        response = requests.post(
            config["gateway_url"],
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "RefundTarget___process_refund", "arguments": {"amount": amount}},
            },
        )
        return response.text

    print(f"🧪 Test $300 (should succeed): {test_refund(300)}")
    print(f"🧪 Test $600 (should fail): {test_refund(600)}")

    print("\n✅ Secure policy engine enforcement test complete")
    print("=" * 60)


def test_policy_from_generation_asset(config, clients):
    """Test creating policy from generation asset."""
    print("\n" + "=" * 60)
    print("Testing Create Policy from Generation Asset")
    print("=" * 60 + "\n")

    policy_client = clients["policy"]

    print("📝 Step 1: Generate policy from natural language\n")
    natural_language_input = "Allow refunds for amounts less than $750"

    try:
        generation_result = policy_client.generate_policy(
            policy_engine_id=config["policy_engine_id"],
            name=f"policy_gen_for_asset_{int(time.time())}",
            resource={"arn": config["gateway_arn"]},
            content={"rawText": natural_language_input},
            fetch_assets=True,
        )

        print(f"✅ Generation complete: {generation_result['policyGenerationId']}\n")

        if generation_result.get("generatedPolicies"):
            first_asset = generation_result["generatedPolicies"][0]
            asset_id = first_asset["policyGenerationAssetId"]
            generation_id = generation_result["policyGenerationId"]

            print("📜 Step 2: Create policy from generation asset\n")
            print(f"Generation ID: {generation_id}")
            print(f"Asset ID: {asset_id}\n")

            created_policy = policy_client.create_policy_from_generation_asset(
                policy_engine_id=config["policy_engine_id"],
                name=f"policy_from_asset_{int(time.time())}",
                policy_generation_id=generation_id,
                policy_generation_asset_id=asset_id,
                description="Policy created from generated asset",
                validation_mode="FAIL_ON_ANY_FINDINGS",
            )

            print("✅ Policy created from generation asset!\n")
            print(f"Policy ID: {created_policy['policyId']}")
            print(f"Policy Name: {created_policy['name']}")
            print(f"Status: {created_policy['status']}")
            print(f"ARN: {created_policy.get('policyArn', 'N/A')}")

            print("\n⏳ Waiting for policy to become active...")
            active_policy = policy_client._wait_for_policy_active(
                config["policy_engine_id"], created_policy["policyId"]
            )
            print(f"✅ Policy is now {active_policy['status']}")

            policy_details = policy_client.get_policy(config["policy_engine_id"], created_policy["policyId"])

            print("\n📋 Policy Definition:")
            definition = policy_details.get("definition", {})
            if "policyGeneration" in definition:
                print("  Type: Policy Generation Reference")
                print(f"  Generation ID: {definition['policyGeneration']['policyGenerationId']}")
                print(f"  Asset ID: {definition['policyGeneration']['policyGenerationAssetId']}")

        else:
            print("⚠️ No policy assets were generated")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n" + "=" * 60)


def cleanup(config, clients):
    """Cleanup all resources."""
    print("\n" + "=" * 60)
    print("Cleanup")
    print("=" * 60 + "\n")

    policy_client = clients["policy"]
    gateway_client = clients["gateway"]

    policy_client.cleanup_policy_engine(config["policy_engine_id"])

    if "secure_engine_id" in config:
        policy_client.cleanup_policy_engine(config["secure_engine_id"])
        print("✅ Secure policy engine cleanup complete")

    if "kms_key_id" in config:
        kms_client = boto3.client("kms", region_name=config["region"])
        kms_client.schedule_key_deletion(KeyId=config["kms_key_id"], PendingWindowInDays=7)
        print(f"✅ KMS key {config['kms_key_id']} scheduled for deletion (7 days)")

    gateway_client.cleanup_gateway(config["gateway_id"], config["client_info"])

    if "gateway2_id" in config:
        gateway_client.cleanup_gateway(config["gateway2_id"], config["client_info2"])
        print("✅ Gateway 2 cleanup complete")

    print("✅ Cleanup complete")


def main():
    """Main execution flow."""
    # Initialize clients
    clients = initialize_clients(REGION)

    # Setup
    config = setup_infrastructure(clients)

    # Get access token
    access_token = clients["gateway"].get_access_token_for_cognito(config["client_info"])
    print("✅ Access token obtained")

    # Run tests
    test_direct_http(config, access_token)
    test_agent(config, access_token)
    test_policy_generation(config, clients)
    test_encryption_and_tags(config, clients)
    test_secure_policy_engine_enforcement(config, access_token, clients)
    test_policy_from_generation_asset(config, clients)

    # Cleanup
    cleanup(config, clients)


if __name__ == "__main__":
    main()
