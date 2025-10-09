"""Tests for Bedrock AgentCore import agent functionality."""

import json
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from dateutil.tz import tzlocal, tzutc

from bedrock_agentcore_starter_toolkit.services.import_agent.scripts import (
    bedrock_to_langchain,
    bedrock_to_strands,
)


@pytest.fixture
def enhanced_mock_boto3_clients(mock_boto3_clients, monkeypatch):
    """Enhanced mock AWS clients for import_agent tests with additional services."""
    # Get the existing mocks
    existing_mocks = mock_boto3_clients

    # Mock Memory operations for BedrockAgentCore client
    existing_mocks["bedrock_agentcore"].create_memory.return_value = {
        "memory": {
            "arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory-id-12345678",
            "id": "test-memory-id-12345678",
            "name": "test_agent_memory_12345678",
            "status": "ACTIVE",
        }
    }

    existing_mocks["bedrock_agentcore"].get_memory.return_value = {
        "memory": {
            "arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory-id-12345678",
            "id": "test-memory-id-12345678",
            "name": "test_agent_memory_12345678",
            "status": "ACTIVE",
        }
    }

    # Mock Gateway operations
    existing_mocks["bedrock_agentcore"].create_gateway.return_value = {
        "ResponseMetadata": {
            "RequestId": "test-request-id-123",
            "HTTPStatusCode": 202,
            "HTTPHeaders": {
                "date": "Tue, 29 Jul 2025 23:36:05 GMT",
                "content-type": "application/json",
                "content-length": "1023",
                "connection": "keep-alive",
                "x-amzn-requestid": "test-request-id-123",
            },
            "RetryAttempts": 0,
        },
        "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
        "gatewayId": "test-gateway-123",
        "gatewayUrl": "https://test-gateway-123.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
        "createdAt": datetime(2025, 7, 29, 23, 36, 5, 179310, tzinfo=tzutc()),
        "updatedAt": datetime(2025, 7, 29, 23, 36, 5, 179322, tzinfo=tzutc()),
        "status": "CREATING",
        "name": "test-gateway",
        "roleArn": "arn:aws:iam::123456789012:role/AgentCoreGatewayExecutionRole",
        "protocolType": "MCP",
        "protocolConfiguration": {"mcp": {"searchType": "SEMANTIC"}},
        "authorizerType": "CUSTOM_JWT",
        "authorizerConfiguration": {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_testpool/.well-known/openid-configuration",
                "allowedClients": ["test-client-id"],
            }
        },
        "workloadIdentityDetails": {
            "workloadIdentityArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:workload-identity-directory/default/workload-identity/test-gateway-123"
        },
    }

    existing_mocks["bedrock_agentcore"].get_gateway.return_value = {
        "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
        "gatewayId": "test-gateway-123",
        "status": "READY",
        "name": "test-gateway",
    }

    existing_mocks["bedrock_agentcore"].create_gateway_target.return_value = {
        "ResponseMetadata": {
            "RequestId": "test-target-request-id",
            "HTTPStatusCode": 202,
            "HTTPHeaders": {
                "date": "Tue, 29 Jul 2025 23:36:15 GMT",
                "content-type": "application/json",
                "content-length": "2596",
                "connection": "keep-alive",
                "x-amzn-requestid": "test-target-request-id",
            },
            "RetryAttempts": 0,
        },
        "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
        "targetId": "TEST123",
        "createdAt": datetime(2025, 7, 29, 23, 36, 15, 713279, tzinfo=tzutc()),
        "updatedAt": datetime(2025, 7, 29, 23, 36, 15, 713288, tzinfo=tzutc()),
        "status": "CREATING",
        "name": "test-target",
        "targetConfiguration": {
            "mcp": {
                "lambda": {
                    "lambdaArn": "arn:aws:lambda:us-west-2:123456789012:function:test-function",
                    "toolSchema": {"inlinePayload": []},
                }
            }
        },
        "credentialProviderConfigurations": [{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
    }

    existing_mocks["bedrock_agentcore"].get_gateway_target.return_value = {
        "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
        "targetId": "TEST123",
        "status": "READY",
        "name": "test-target",
    }

    existing_mocks["bedrock_agentcore"].create_api_key_credential_provider.return_value = {
        "credentialProviderArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/test-api-key-provider"
    }

    existing_mocks["bedrock_agentcore"].create_oauth2_credential_provider.return_value = {
        "credentialProviderArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/test-oauth2-provider"
    }

    # Mock Cognito client
    mock_cognito = Mock()
    mock_cognito.create_user_pool.return_value = {
        "UserPool": {
            "Id": "us-west-2_testpool",
            "Name": "test-pool",
            "CreationDate": datetime(2025, 7, 29, 16, 35, 4, 257000, tzinfo=tzlocal()),
            "LastModifiedDate": datetime(2025, 7, 29, 16, 35, 4, 257000, tzinfo=tzlocal()),
        }
    }

    mock_cognito.create_user_pool_domain.return_value = {"CloudFrontDomain": "test-domain.cloudfront.net"}

    mock_cognito.describe_user_pool_domain.return_value = {
        "DomainDescription": {"Domain": "test-domain", "Status": "ACTIVE", "UserPoolId": "us-west-2_testpool"}
    }

    mock_cognito.create_resource_server.return_value = {
        "ResourceServer": {
            "UserPoolId": "us-west-2_testpool",
            "Identifier": "test-resource-server",
            "Name": "Test Resource Server",
            "Scopes": [{"ScopeName": "invoke", "ScopeDescription": "Invoke scope"}],
        }
    }

    mock_cognito.create_user_pool_client.return_value = {
        "UserPoolClient": {
            "UserPoolId": "us-west-2_testpool",
            "ClientName": "test-client",
            "ClientId": "test-client-id",
            "ClientSecret": "test-client-secret",
            "LastModifiedDate": datetime(2025, 7, 29, 16, 35, 4, 257000, tzinfo=tzlocal()),
            "CreationDate": datetime(2025, 7, 29, 16, 35, 4, 257000, tzinfo=tzlocal()),
            "RefreshTokenValidity": 30,
            "TokenValidityUnits": {},
            "SupportedIdentityProviders": ["COGNITO"],
            "AllowedOAuthFlows": ["client_credentials"],
            "AllowedOAuthScopes": ["test-resource-server/invoke"],
            "AllowedOAuthFlowsUserPoolClient": True,
            "EnableTokenRevocation": True,
            "EnablePropagateAdditionalUserContextData": False,
            "AuthSessionValidity": 3,
        },
        "ResponseMetadata": {
            "RequestId": "test-cognito-request-id",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "date": "Tue, 29 Jul 2025 23:35:04 GMT",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "610",
                "connection": "keep-alive",
                "x-amzn-requestid": "test-cognito-request-id",
            },
            "RetryAttempts": 0,
        },
    }

    # Mock Cognito exceptions
    mock_cognito.exceptions = Mock()
    mock_cognito.exceptions.ClientError = Exception

    existing_mocks["cognito"] = mock_cognito

    # Mock IAM client
    mock_iam = Mock()

    # Create a proper trust policy for bedrock-agentcore
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole"}
        ],
    }

    mock_iam.create_role.return_value = {
        "Role": {
            "RoleName": "TestRole",
            "Arn": "arn:aws:iam::123456789012:role/TestRole",
            "CreateDate": datetime(2025, 7, 29, 16, 35, 4, tzinfo=tzutc()),
            "AssumeRolePolicyDocument": trust_policy,
        }
    }

    mock_iam.get_role.return_value = {
        "Role": {
            "RoleName": "TestRole",
            "Arn": "arn:aws:iam::123456789012:role/TestRole",
            "CreateDate": datetime(2025, 7, 29, 16, 35, 4, tzinfo=tzutc()),
            "AssumeRolePolicyDocument": trust_policy,
        }
    }

    mock_iam.create_policy.return_value = {
        "Policy": {
            "PolicyName": "TestPolicy",
            "Arn": "arn:aws:iam::123456789012:policy/TestPolicy",
            "CreateDate": datetime(2025, 7, 29, 16, 35, 4, tzinfo=tzutc()),
        }
    }

    mock_iam.attach_role_policy.return_value = {}

    # Mock IAM exceptions
    mock_iam.exceptions = Mock()
    mock_iam.exceptions.EntityAlreadyExistsException = Exception

    existing_mocks["iam"] = mock_iam

    # Mock Lambda client
    mock_lambda = Mock()
    mock_lambda.create_function.return_value = {
        "FunctionName": "test-function",
        "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:test-function",
        "Runtime": "python3.10",
        "Role": "arn:aws:iam::123456789012:role/TestRole",
        "Handler": "lambda_function.lambda_handler",
        "CodeSize": 1024,
        "Description": "Test function",
        "Timeout": 30,
        "MemorySize": 128,
        "LastModified": "2025-07-29T23:35:04.000+0000",
        "CodeSha256": "test-sha256",
        "Version": "$LATEST",
        "State": "Active",
        "StateReason": "The function is active",
        "StateReasonCode": "Idle",
        "LastUpdateStatus": "Successful",
        "LastUpdateStatusReason": "The function was successfully updated",
        "LastUpdateStatusReasonCode": "Idle",
        "PackageType": "Zip",
        "Architectures": ["x86_64"],
        "EphemeralStorage": {"Size": 512},
    }

    mock_lambda.get_function.return_value = {
        "Configuration": {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:test-function",
            "Runtime": "python3.10",
            "Role": "arn:aws:iam::123456789012:role/TestRole",
            "Handler": "lambda_function.lambda_handler",
            "CodeSize": 1024,
            "Description": "Test function",
            "Timeout": 30,
            "MemorySize": 128,
            "LastModified": "2025-07-29T23:35:04.000+0000",
            "CodeSha256": "test-sha256",
            "Version": "$LATEST",
            "State": "Active",
            "StateReason": "The function is active",
            "StateReasonCode": "Idle",
            "LastUpdateStatus": "Successful",
            "LastUpdateStatusReason": "The function was successfully updated",
            "LastUpdateStatusReasonCode": "Idle",
            "PackageType": "Zip",
            "Architectures": ["x86_64"],
            "EphemeralStorage": {"Size": 512},
        },
        "Code": {"RepositoryType": "S3", "Location": "https://test-bucket.s3.amazonaws.com/test-key"},
        "Tags": {},
    }

    mock_lambda.add_permission.return_value = {
        "Statement": '{"Sid":"AllowAgentCoreInvoke","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/TestRole"},"Action":"lambda:InvokeFunction","Resource":"arn:aws:lambda:us-west-2:123456789012:function:test-function"}'
    }

    mock_lambda.invoke.return_value = {
        "StatusCode": 200,
        "Payload": Mock(read=lambda: b'{"statusCode": 200, "body": "test response"}'),
    }

    # Mock Lambda exceptions
    mock_lambda.exceptions = Mock()
    mock_lambda.exceptions.ResourceConflictException = Exception

    existing_mocks["lambda"] = mock_lambda

    # Update the mock_client function to handle additional services
    def enhanced_mock_client(service_name, **kwargs):
        if service_name == "sts":
            return existing_mocks["sts"]
        elif service_name == "ecr":
            return existing_mocks["ecr"]
        elif service_name in ["bedrock_agentcore-test", "bedrock-agentcore-control", "bedrock-agentcore"]:
            return existing_mocks["bedrock_agentcore"]
        elif service_name == "cognito-idp":
            return existing_mocks["cognito"]
        elif service_name == "iam":
            return existing_mocks["iam"]
        elif service_name == "lambda":
            return existing_mocks["lambda"]
        return Mock()

    # Update the session mock to use the enhanced client
    existing_mocks["session"].client = enhanced_mock_client

    # Update the monkeypatch to use the enhanced client
    monkeypatch.setattr("boto3.client", enhanced_mock_client)

    return existing_mocks


class TestImportAgent:
    """Test Import Agent functionality."""

    def test_bedrock_to_strands(self, enhanced_mock_boto3_clients):
        """Test Bedrock to Strands import functionality."""

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(
            open(os.path.join(base_dir, "data", "bedrock_config_multi_agent.json"), "r", encoding="utf-8")
        )
        output_dir = os.path.join(base_dir, "output", "strands")
        os.makedirs(output_dir, exist_ok=True)

        bedrock_to_strands.BedrockStrandsTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives={}
        ).translate_bedrock_to_strands(os.path.join(output_dir, "strands_agent.py"))

    def test_bedrock_to_langchain(self, enhanced_mock_boto3_clients):
        """Test Bedrock to LangChain import functionality."""

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(
            open(os.path.join(base_dir, "data", "bedrock_config_multi_agent.json"), "r", encoding="utf-8")
        )
        output_dir = os.path.join(base_dir, "output", "langchain")
        os.makedirs(output_dir, exist_ok=True)

        bedrock_to_langchain.BedrockLangchainTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives={}
        ).translate_bedrock_to_langchain(os.path.join(output_dir, "langchain_agent.py"))

    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.time.sleep")
    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.MemoryClient")
    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.boto3.client")
    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.GatewayClient")
    @patch("uuid.uuid4")
    def test_bedrock_to_langchain_with_primitives(
        self,
        mock_uuid,
        mock_gateway_client_class,
        mock_boto3_client,
        mock_memory_client_class,
        mock_sleep,
        enhanced_mock_boto3_clients,
    ):
        """Test Bedrock to LangChain import with AgentCore memory and gateway enabled."""
        # Mock time.sleep to speed up tests
        mock_sleep.return_value = None
        # Mock UUID generation for consistent naming
        mock_uuid_instance = Mock()
        mock_uuid_instance.hex = "12345678abcdefgh"
        mock_uuid.return_value = mock_uuid_instance

        # Setup mock MemoryClient
        mock_memory_client = Mock()
        mock_memory_client_class.return_value = mock_memory_client
        mock_memory_client.create_memory_and_wait.return_value = {
            "id": "test-memory-id-123",
            "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:memory/test-memory-id-123",
            "name": "test_memory",
            "status": "ACTIVE",
        }

        # Setup mock boto3.client calls
        def mock_client_side_effect(service_name, **kwargs):
            if service_name == "sts":
                return enhanced_mock_boto3_clients["sts"]
            elif service_name == "iam":
                return enhanced_mock_boto3_clients["iam"]
            elif service_name == "lambda":
                return enhanced_mock_boto3_clients["lambda"]
            return Mock()

        mock_boto3_client.side_effect = mock_client_side_effect

        # Setup mock GatewayClient instance
        mock_gateway_client = Mock()
        mock_gateway_client_class.return_value = mock_gateway_client

        # Mock gateway creation methods
        mock_gateway_client.create_oauth_authorizer_with_cognito.return_value = {
            "authorizer_config": {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_testpool/.well-known/openid-configuration",
                    "allowedClients": ["test-client-id"],
                }
            },
            "client_info": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "user_pool_id": "us-west-2_testpool",
                "token_endpoint": "https://test-domain.auth.us-west-2.amazoncognito.com/oauth2/token",
                "scope": "TestGateway/invoke",
                "domain_prefix": "test-domain",
            },
        }

        mock_gateway_client.create_mcp_gateway.return_value = {
            "gatewayId": "test-gateway-123",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
            "gatewayUrl": "https://test-gateway-123.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
            "status": "READY",
            "roleArn": "arn:aws:iam::123456789012:role/AgentCoreGatewayExecutionRole",
        }

        mock_gateway_client.create_mcp_gateway_target.return_value = {
            "targetId": "test-target-123",
            "targetArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway-target/test-target-123",
            "status": "READY",
        }

        mock_gateway_client.get_access_token_for_cognito.return_value = "test-access-token"

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(open(os.path.join(base_dir, "data", "bedrock_config.json"), "r", encoding="utf-8"))
        output_dir = os.path.join(base_dir, "output", "langchain_with_primitives")
        os.makedirs(output_dir, exist_ok=True)

        enabled_primitives = {"memory": True, "code_interpreter": True, "observability": True, "gateway": True}

        translator = bedrock_to_langchain.BedrockLangchainTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        # This should use the mocked MemoryClient and GatewayClient
        translator.translate_bedrock_to_langchain(os.path.join(output_dir, "langchain_with_primitives.py"))

        # Verify that the memory mock was called
        mock_memory_client.create_memory_and_wait.assert_called_once()

        # Verify that gateway methods were called
        mock_gateway_client.create_oauth_authorizer_with_cognito.assert_called_once()
        mock_gateway_client.create_mcp_gateway.assert_called_once()

        # Verify that sleep was called (but didn't actually sleep)
        assert mock_sleep.call_count >= 1

    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.time.sleep")
    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.MemoryClient")
    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.boto3.client")
    @patch("bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate.GatewayClient")
    @patch("uuid.uuid4")
    def test_bedrock_to_strands_with_primitives(
        self,
        mock_uuid,
        mock_gateway_client_class,
        mock_boto3_client,
        mock_memory_client_class,
        mock_sleep,
        enhanced_mock_boto3_clients,
    ):
        """Test Bedrock to Strands import with AgentCore memory and gateway enabled."""
        # Mock time.sleep to speed up tests
        mock_sleep.return_value = None
        # Mock UUID generation for consistent naming
        mock_uuid_instance = Mock()
        mock_uuid_instance.hex = "12345678abcdefgh"
        mock_uuid.return_value = mock_uuid_instance

        # Setup mock MemoryClient
        mock_memory_client = Mock()
        mock_memory_client_class.return_value = mock_memory_client
        mock_memory_client.create_memory_and_wait.return_value = {
            "id": "test-memory-id-123",
            "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:memory/test-memory-id-123",
            "name": "test_memory",
            "status": "ACTIVE",
        }

        # Setup mock boto3.client calls
        def mock_client_side_effect(service_name, **kwargs):
            if service_name == "sts":
                return enhanced_mock_boto3_clients["sts"]
            elif service_name == "iam":
                return enhanced_mock_boto3_clients["iam"]
            elif service_name == "lambda":
                return enhanced_mock_boto3_clients["lambda"]
            return Mock()

        mock_boto3_client.side_effect = mock_client_side_effect

        # Setup mock GatewayClient instance
        mock_gateway_client = Mock()
        mock_gateway_client_class.return_value = mock_gateway_client

        # Mock gateway creation methods
        mock_gateway_client.create_oauth_authorizer_with_cognito.return_value = {
            "authorizer_config": {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_testpool/.well-known/openid-configuration",
                    "allowedClients": ["test-client-id"],
                }
            },
            "client_info": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "user_pool_id": "us-west-2_testpool",
                "token_endpoint": "https://test-domain.auth.us-west-2.amazoncognito.com/oauth2/token",
                "scope": "TestGateway/invoke",
                "domain_prefix": "test-domain",
            },
        }

        mock_gateway_client.create_mcp_gateway.return_value = {
            "gatewayId": "test-gateway-123",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
            "gatewayUrl": "https://test-gateway-123.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
            "status": "READY",
            "roleArn": "arn:aws:iam::123456789012:role/AgentCoreGatewayExecutionRole",
        }

        mock_gateway_client.create_mcp_gateway_target.return_value = {
            "targetId": "test-target-123",
            "targetArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway-target/test-target-123",
            "status": "READY",
        }

        mock_gateway_client.get_access_token_for_cognito.return_value = "test-access-token"

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(open(os.path.join(base_dir, "data", "bedrock_config.json"), "r", encoding="utf-8"))
        output_dir = os.path.join(base_dir, "output", "strands_with_primitives")
        os.makedirs(output_dir, exist_ok=True)

        enabled_primitives = {"memory": True, "code_interpreter": True, "observability": True, "gateway": True}

        translator = bedrock_to_strands.BedrockStrandsTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        # This should use the mocked MemoryClient and GatewayClient
        translator.translate_bedrock_to_strands(os.path.join(output_dir, "strands_with_primitives.py"))

        # Verify that the memory mock was called
        mock_memory_client.create_memory_and_wait.assert_called_once()

        # Verify that gateway methods were called
        mock_gateway_client.create_oauth_authorizer_with_cognito.assert_called_once()
        mock_gateway_client.create_mcp_gateway.assert_called_once()

        # Verify that sleep was called (but didn't actually sleep)
        assert mock_sleep.call_count >= 1

    def test_bedrock_to_langchain_with_function_schema_no_gateway(self, enhanced_mock_boto3_clients):
        """Test Bedrock to LangChain import with function schema action groups but no gateway."""
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(open(os.path.join(base_dir, "data", "bedrock_config.json"), "r", encoding="utf-8"))
        output_dir = os.path.join(base_dir, "output", "langchain_function_schema")
        os.makedirs(output_dir, exist_ok=True)

        # Enable some primitives but NOT gateway - this will force function schema processing
        enabled_primitives = {"memory": False, "code_interpreter": True, "observability": False, "gateway": False}

        translator = bedrock_to_langchain.BedrockLangchainTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        translator.translate_bedrock_to_langchain(os.path.join(output_dir, "langchain_function_schema.py"))

    def test_bedrock_to_strands_with_function_schema_no_gateway(self, enhanced_mock_boto3_clients):
        """Test Bedrock to Strands import with function schema action groups but no gateway."""
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(open(os.path.join(base_dir, "data", "bedrock_config.json"), "r", encoding="utf-8"))
        output_dir = os.path.join(base_dir, "output", "strands_function_schema")
        os.makedirs(output_dir, exist_ok=True)

        # Enable some primitives but NOT gateway - this will force function schema processing
        enabled_primitives = {"memory": False, "code_interpreter": True, "observability": False, "gateway": False}

        translator = bedrock_to_strands.BedrockStrandsTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        translator.translate_bedrock_to_strands(os.path.join(output_dir, "strands_function_schema.py"))

    def test_bedrock_to_langchain_with_no_schema_action_group(self, enhanced_mock_boto3_clients):
        """Test Bedrock to LangChain import with action group that has no schema (to cover branch coverage)."""
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        agent_config = json.load(
            open(os.path.join(base_dir, "data", "bedrock_config_no_schema.json"), "r", encoding="utf-8")
        )
        output_dir = os.path.join(base_dir, "output", "langchain_no_schema")
        os.makedirs(output_dir, exist_ok=True)

        # Enable some primitives but NOT gateway - this will force function schema processing
        enabled_primitives = {"memory": False, "code_interpreter": False, "observability": False, "gateway": False}

        translator = bedrock_to_langchain.BedrockLangchainTranslation(
            agent_config=agent_config, debug=False, output_dir=output_dir, enabled_primitives=enabled_primitives
        )

        translator.translate_bedrock_to_langchain(os.path.join(output_dir, "langchain_no_schema.py"))


# ruff: noqa: E501
