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

BEDROCK_AGENTCORE_TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

AGENTCORE_FULL_ACCESS = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAgentCoreFullAccess",
            "Effect": "Allow",
            "Action": ["bedrock-agentcore:*"],
            "Resource": "arn:aws:bedrock-agentcore:*:*:*",
        },
        {
            "Sid": "GetSecretValue",
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": "*",
        },
        {
            "Sid": "LambdaInvokeAccess",
            "Effect": "Allow",
            "Action": ["lambda:InvokeFunction"],
            "Resource": "arn:aws:lambda:*:*:function:*",
        },
    ],
}

POLICIES_TO_CREATE = [("BedrockAgentCoreGatewayStarterFullAccess", AGENTCORE_FULL_ACCESS)]

POLICIES = {
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
}

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
