"""Shared test fixtures for Bedrock AgentCore Starter Toolkit tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from bedrock_agentcore import BedrockAgentCoreApp


@pytest.fixture
def mock_boto3_clients(monkeypatch):
    """Mock AWS clients (STS, ECR, BedrockAgentCore, Cognito, IAM, Lambda) and MemoryClient."""
    from datetime import datetime

    from dateutil.tz import tzlocal, tzutc

    # Mock STS client
    mock_sts = Mock()
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

    # Mock ECR client
    mock_ecr = Mock()
    mock_ecr.create_repository.return_value = {
        "repository": {"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo"}
    }
    mock_ecr.get_authorization_token.return_value = {
        "authorizationData": [
            {
                "authorizationToken": "dXNlcjpwYXNz",  # base64 encoded "user:pass"
                "proxyEndpoint": "https://123456789012.dkr.ecr.us-west-2.amazonaws.com",
            }
        ]
    }
    mock_ecr.describe_repositories.return_value = {
        "repositories": [{"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/existing-repo"}]
    }
    # Mock exceptions
    mock_ecr.exceptions = Mock()
    mock_ecr.exceptions.RepositoryAlreadyExistsException = Exception

    # Mock BedrockAgentCore client
    mock_bedrock_agentcore = Mock()
    mock_bedrock_agentcore.create_agent_runtime.return_value = {
        "agentRuntimeId": "test-agent-id",
        "agentRuntimeArn": "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
    }
    mock_bedrock_agentcore.update_agent_runtime.return_value = {
        "agentRuntimeArn": "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
    }
    mock_bedrock_agentcore.get_agent_runtime_endpoint.return_value = {
        "status": "READY",
        "agentRuntimeEndpointArn": (
            "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
        ),
    }
    mock_bedrock_agentcore.invoke_agent_runtime.return_value = {"response": [{"data": "test response"}]}
    # Mock exceptions
    mock_bedrock_agentcore.exceptions = Mock()
    mock_bedrock_agentcore.exceptions.ResourceNotFoundException = Exception

    mock_bedrock_agentcore.create_memory.return_value = {
        "memory": {
            "arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory-id-12345678",
            "id": "test-memory-id-12345678",
            "name": "test_agent_memory_12345678",
            "status": "ACTIVE",
        }
    }

    mock_bedrock_agentcore.get_memory.return_value = {
        "memory": {
            "arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory-id-12345678",
            "id": "test-memory-id-12345678",
            "name": "test_agent_memory_12345678",
            "status": "ACTIVE",
        }
    }

    # Mock Gateway operations
    mock_bedrock_agentcore.create_gateway.return_value = {
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

    mock_bedrock_agentcore.get_gateway.return_value = {
        "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
        "gatewayId": "test-gateway-123",
        "status": "READY",
        "name": "test-gateway",
    }

    mock_bedrock_agentcore.create_gateway_target.return_value = {
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

    mock_bedrock_agentcore.get_gateway_target.return_value = {
        "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
        "targetId": "TEST123",
        "status": "READY",
        "name": "test-target",
    }

    mock_bedrock_agentcore.create_api_key_credential_provider.return_value = {
        "credentialProviderArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/test-api-key-provider"
    }

    mock_bedrock_agentcore.create_oauth2_credential_provider.return_value = {
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

    # Mock boto3.client calls
    def mock_client(service_name, **kwargs):
        if service_name == "sts":
            return mock_sts
        elif service_name == "ecr":
            return mock_ecr
        elif service_name in ["bedrock_agentcore-test", "bedrock-agentcore-control", "bedrock-agentcore"]:
            return mock_bedrock_agentcore
        elif service_name == "cognito-idp":
            return mock_cognito
        elif service_name == "iam":
            return mock_iam
        elif service_name == "lambda":
            return mock_lambda
        return Mock()

    # Mock boto3.Session
    mock_session = Mock()
    mock_session.region_name = "us-west-2"
    mock_session.get_credentials.return_value.get_frozen_credentials.return_value = Mock(
        access_key="test-key", secret_key="test-secret", token="test-token"
    )
    mock_session.client = mock_client

    monkeypatch.setattr("boto3.client", mock_client)
    monkeypatch.setattr("boto3.Session", lambda *args, **kwargs: mock_session)

    return {
        "sts": mock_sts,
        "ecr": mock_ecr,
        "bedrock_agentcore": mock_bedrock_agentcore,
        "cognito": mock_cognito,
        "iam": mock_iam,
        "lambda": mock_lambda,
        "session": mock_session,
    }


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess operations for container runtime."""
    mock_run = Mock()
    mock_run.returncode = 0
    mock_run.stdout = "Docker version 20.10.0"

    mock_popen = Mock()
    mock_popen.stdout = ["Step 1/5 : FROM python:3.10", "Successfully built abc123"]
    mock_popen.wait.return_value = 0
    mock_popen.returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: mock_run)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: mock_popen)

    return {"run": mock_run, "popen": mock_popen}


@pytest.fixture
def mock_bedrock_agentcore_app():
    """Mock BedrockAgentCoreApp instance for testing."""
    app = BedrockAgentCoreApp()

    @app.entrypoint
    def test_handler(payload):
        return {"result": "test"}

    return app


@pytest.fixture
def mock_container_runtime(monkeypatch):
    """Mock container runtime operations."""
    from bedrock_agentcore_starter_toolkit.utils.runtime.container import ContainerRuntime

    # Create a mock runtime object with all required attributes and methods
    mock_runtime = Mock(spec=ContainerRuntime)
    mock_runtime.runtime = "docker"
    mock_runtime.has_local_runtime = True  # Add the new attribute
    mock_runtime.get_name.return_value = "Docker"
    mock_runtime.build.return_value = (True, ["Successfully built test-image"])
    mock_runtime.login.return_value = True
    mock_runtime.tag.return_value = True
    mock_runtime.push.return_value = True
    mock_runtime.generate_dockerfile.return_value = Path("/tmp/Dockerfile")

    # Set class attributes for compatibility
    mock_runtime.DEFAULT_RUNTIME = "auto"
    mock_runtime.DEFAULT_PLATFORM = "linux/arm64"

    # Mock the ContainerRuntime class constructor
    def mock_constructor(*args, **kwargs):
        return mock_runtime

    monkeypatch.setattr("bedrock_agentcore_starter_toolkit.utils.runtime.container.ContainerRuntime", mock_constructor)

    return mock_runtime


# ruff: noqa: E501
