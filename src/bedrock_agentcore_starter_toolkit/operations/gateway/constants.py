"""Constants for use in Bedrock AgentCore Gateway."""

API_MODEL_BUCKETS = {
    "ap-southeast-2": "amazonbedrockagentcore-built-sampleschemas455e0815-yigvs4je21kx",
    "us-west-2": "amazonbedrockagentcore-built-sampleschemas455e0815-omxvr7ybq9g8",
    "eu-central-1": "amazonbedrockagentcore-built-sampleschemas455e0815-egpctdjskcrf",
    "us-east-1": "amazonbedrockagentcore-built-sampleschemas455e0815-oj7jujcd8xiu",
}

CREATE_OPENAPI_TARGET_INVALID_CREDENTIALS_SHAPE_EXCEPTION_MESSAGE = """
            Provided credentials object was not formatted correctly. Correct formats below:

            API Key:
            {
                "api_key": "<key>",
                "credential_location": "HEADER | BODY",
                "credential_parameter_name": "<name of parameter>"
            }

            OAuth:
            {
                "oauth2_provider_config": {
                    "customOauth2ProviderConfig": {
                        <same as the agentcredentialprovider customOauth2ProviderConfig object>
                    }
                }
            }

            Example for OAuth:
            {
                "oauth2_provider_config": {
                    "customOauth2ProviderConfig": {
                      "oauthDiscovery" : {
                        "authorizationServerMetadata" : {
                          "issuer" : "< issuer endpoint >",
                          "authorizationEndpoint" : "< authorization endpoint >",
                          "tokenEndpoint" : "< token endpoint >"
                        }
                      },
                      "clientId" : "< client id >",
                      "clientSecret" : "< client secret >"
                    }
                }
            }
"""

GATEWAY_EXECUTION_POLICY_NAME = "BedrockAgentCoreGatewayExecutionPolicy"


def build_gateway_access_policy(region: str, account_id: str, gateway_name: str, partition: str = "aws") -> dict:
    """Build the base gateway execution policy.

    Credential-provider and Lambda-target permissions are attached separately, scoped to each
    resource, by append_credential_provider_permissions and append_lambda_target_permission.

    :param region: AWS region for resource ARNs.
    :param account_id: AWS account ID for resource ARNs.
    :param gateway_name: gateway name prefix used to scope the gateway ARN.
    :param partition: AWS partition (``aws``, ``aws-cn``, ``aws-us-gov``).
    :return: an IAM policy document.
    """
    prefix = f"arn:{partition}:bedrock-agentcore:{region}:{account_id}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GetGateway",
                "Effect": "Allow",
                "Action": ["bedrock-agentcore:GetGateway"],
                "Resource": [f"{prefix}:gateway/{gateway_name}-*"],
            },
            {
                "Sid": "GetConfigurationBundleVersion",
                "Effect": "Allow",
                "Action": ["bedrock-agentcore:GetConfigurationBundleVersion"],
                "Resource": [f"{prefix}:configuration-bundle/*"],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": "${aws:PrincipalAccount}",
                        "aws:RequestedRegion": region,
                    }
                },
            },
        ],
    }


def build_gateway_credential_provider_policy(
    region: str,
    account_id: str,
    provider_name: str,
    provider_kind: str,
    partition: str = "aws",
) -> dict:
    """Build a policy granting credential and secret access for a single OpenAPI provider.

    :param region: AWS region.
    :param account_id: AWS account ID.
    :param provider_name: the credential provider name (used to scope the secret ARN prefix).
    :param provider_kind: ``oauth2`` or ``apikey``.
    :param partition: AWS partition.
    :return: an IAM policy document.
    """
    bac = f"arn:{partition}:bedrock-agentcore:{region}:{account_id}"
    sm = f"arn:{partition}:secretsmanager:{region}:{account_id}"
    if provider_kind == "oauth2":
        token_action = "bedrock-agentcore:GetResourceOauth2Token"  # nosec B105 - IAM action name, not a secret
        provider_resource = f"{bac}:token-vault/default/oauth2credentialprovider/{provider_name}*"
        secret_resource = f"{sm}:secret:bedrock-agentcore-identity!default/oauth2/{provider_name}-*"
    elif provider_kind == "apikey":
        token_action = "bedrock-agentcore:GetResourceApiKey"  # nosec B105 - IAM action name, not a secret
        provider_resource = f"{bac}:token-vault/default/apikeycredentialprovider/{provider_name}*"
        secret_resource = f"{sm}:secret:bedrock-agentcore-identity!default/apikey/{provider_name}-*"
    else:
        raise ValueError(f"Unknown provider_kind: {provider_kind!r} (expected 'oauth2' or 'apikey')")

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GatewayCredentialProviderToken",
                "Effect": "Allow",
                "Action": [token_action],
                "Resource": [f"{bac}:token-vault/default", provider_resource],
            },
            {
                "Sid": "GatewayCredentialProviderSecret",
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": [secret_resource],
            },
        ],
    }


def build_gateway_lambda_invoke_policy(region: str, account_id: str, function_arn: str, partition: str = "aws") -> dict:
    """Build a policy granting invoke on a single Lambda function.

    :param region: AWS region (unused in ARN, kept for signature symmetry).
    :param account_id: AWS account ID for the ResourceAccount condition.
    :param function_arn: the exact Lambda function ARN the gateway target invokes.
    :param partition: AWS partition.
    :return: an IAM policy document.
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GatewayLambdaTargetInvoke",
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": [function_arn],
                "Condition": {"StringEquals": {"aws:ResourceAccount": account_id}},
            }
        ],
    }


POLICIES: set = set()

POLICIES_TO_CREATE: list = []

LAMBDA_FUNCTION_CODE = """
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
"""

LAMBDA_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

LAMBDA_CONFIG = {
    "inlinePayload": [
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
