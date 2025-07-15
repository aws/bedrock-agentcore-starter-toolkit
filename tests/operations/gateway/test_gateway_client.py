from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.gateway import (
    GatewayClient,
)


@pytest.fixture
def mock_boto_client():
    """Mock boto3 client"""
    with patch("boto3.client") as mock:
        yield mock


@pytest.fixture
def mock_session():
    """Mock boto3 session"""
    with patch("boto3.Session") as mock:
        yield mock


@pytest.fixture
def gateway_client(mock_boto_client, mock_session):
    """Create GatewayClient instance with mocked dependencies"""
    return GatewayClient(region_name="us-west-2")


class TestGatewayClient:
    @patch("bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient.create_oauth_authorizer_with_cognito")
    def test_setup_gateway_lambda(self, mock_create_oauth_authorizer_with_cognito, gateway_client, mock_boto_client):
        """Test creating gateway with Lambda target"""
        # Mock responses
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_create_oauth_authorizer_with_cognito.return_value = {
            "authorizer_config": {
                "customJWTAuthorizer": {"allowedClients": ["allowedClient"], "discoveryUrl": "aRandomUrl"}
            },
            "client_info": {
                "client_id": "client",
                "client_secret": "clientSecret",
                "user_pool_id": "poolId",
                "token_endpoint": "tokenEndpoint",
                "scope": "my-gateway/invoke",
                "domain_prefix": "some-prefix",
            },
        }

        # Mock gateway creation
        mock_bedrock.create_gateway.return_value = {
            "gatewayId": "TEST123",
            "gatewayArn": "arn:aws:bedrock_agentcore:us-west-2:123:gateway/TEST123",
            "gatewayUrl": "https://TEST456.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
            "status": "READY",
            "roleArn": "roleArn",
        }

        # Mock target creation
        mock_bedrock.create_gateway_target.return_value = {
            "targetId": "TARGET123",
            "status": "READY",
        }

        # Mock get operations for status checking
        mock_bedrock.get_gateway.return_value = {
            "gatewayId": "TEST456",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:gateway/TEST456",
            "gatewayUrl": "https://TEST456.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
            "status": "READY",
        }

        mock_bedrock.get_gateway_target.return_value = {
            "targetId": "TARGET123",
            "status": "READY",
        }
        with patch.object(gateway_client.session, "client") as mock_session_client:
            session_client = Mock()
            mock_session_client.return_value = session_client
            session_client.exceptions.EntityAlreadyExistsException = ValueError
            session_client.exceptions.ResourceConflictException = ValueError
            session_client.create_role.return_value = {"Role": {"Arn": "arn"}}
            session_client.create_function.return_value = {"FunctionArn": "arn"}
            # Test Lambda target
            gateway = gateway_client.create_mcp_gateway(
                name="test-lambda",
                role_arn="arn:aws:iam::123:role/TestRole",
            )
            _ = gateway_client.create_mcp_gateway_target(gateway=gateway)

        # Verify calls
        assert mock_bedrock.create_gateway.called
        assert mock_bedrock.create_gateway_target.called

        # Check target config for Lambda
        target_call = mock_bedrock.create_gateway_target.call_args[1]
        assert "lambdaArn" in target_call["targetConfiguration"]["mcp"]["lambda"]
        assert target_call["credentialProviderConfigurations"] == [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

    @patch("bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient.create_oauth_authorizer_with_cognito")
    def test_setup_gateway_openapi(self, mock_create_oauth_authorizer_with_cognito, gateway_client):
        """Test creating gateway with OpenAPI target"""
        # Mock responses
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_create_oauth_authorizer_with_cognito.return_value = {
            "authorizer_config": {
                "customJWTAuthorizer": {"allowedClients": ["allowedClient"], "discoveryUrl": "aRandomUrl"}
            },
            "client_info": {
                "client_id": "client",
                "client_secret": "clientSecret",
                "user_pool_id": "poolId",
                "token_endpoint": "tokenEndpoint",
                "scope": "my-gateway/invoke",
                "domain_prefix": "some-prefix",
            },
        }

        mock_bedrock.create_gateway.return_value = {
            "gatewayId": "TEST456",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:gateway/TEST456",
            "gatewayUrl": "TEST456.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp",
            "status": "READY",
            "roleArn": "someRole",
        }

        mock_bedrock.create_gateway_target.return_value = {
            "targetId": "TARGET456",
            "status": "READY",
        }

        mock_bedrock.get_gateway.return_value = {"gatewayId": "TEST456", "status": "READY", "roleArn": "someRole"}
        mock_bedrock.get_gateway_target.return_value = {
            "targetId": "TARGET456",
            "status": "READY",
        }
        with patch.object(gateway_client.session, "client") as mock_acps:
            acps_client = Mock()
            mock_acps.return_value = acps_client
            acps_client.create_api_key_credential_provider.return_value = {"credentialProviderArn": "arn"}
            # Test OpenAPI from S3
            gateway = gateway_client.create_mcp_gateway(
                name="test-lambda",
                role_arn="arn:aws:iam::123:role/TestRole",
            )
            _ = gateway_client.create_mcp_gateway_target(
                gateway=gateway,
                target_type="openApiSchema",
                target_payload={"s3": {"uri": "s3://my-bucket/openapi.json"}},
                credentials={
                    "api_key": "MyKey",
                    "credential_location": "HEADER",
                    "credential_parameter_name": "MyHeader",
                },
            )

        # Check S3 config
        target_call = mock_bedrock.create_gateway_target.call_args[1]
        assert "s3" in target_call["targetConfiguration"]["mcp"]["openApiSchema"]
        assert target_call["targetConfiguration"]["mcp"]["openApiSchema"]["s3"]["uri"] == "s3://my-bucket/openapi.json"

    # def test_create_oauth_authorizer_with_cognito(self, gateway_client, mock_boto_client):
    #     """Test Cognito OAuth setup"""
    #     with patch.object(gateway_client.session, "client") as mock_cognito:
    #         cognito_client = Mock()
    #         mock_cognito.return_value = cognito_client

    #         # Mock Cognito responses
    #         cognito_client.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_TEST123"}}
    #         cognito_client.create_user_pool_domain.return_value = {}
    #         cognito_client.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "ACTIVE"}}
    #         cognito_client.create_resource_server.return_value = {}
    #         cognito_client.create_user_pool_client.return_value = {
    #             "UserPoolClient": {
    #                 "ClientId": "testclientid",
    #                 "ClientSecret": "testclientsecret",
    #             }
    #         }

    #         result = gateway_client.create_oauth_authorizer_with_cognito("test-gateway")

    #         assert result["client_info"]["client_id"] == "testclientid"
    #         assert result["client_info"]["client_secret"] == "testclientsecret"
    #         assert "us-west-2_TEST123" in result["authorizer_config"]["customJWTAuthorizer"]["discoveryUrl"]

    @patch("bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient.create_oauth_authorizer_with_cognito")
    def test_error_handling(self, mock_create_oauth_authorizer_with_cognito, gateway_client):
        """Test error handling in setup_gateway"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_create_oauth_authorizer_with_cognito.return_value = {
            "authorizer_config": {
                "customJWTAuthorizer": {"allowedClients": ["allowedClient"], "discoveryUrl": "aRandomUrl"}
            },
            "client_info": {
                "client_id": "client",
                "client_secret": "clientSecret",
                "user_pool_id": "poolId",
                "token_endpoint": "tokenEndpoint",
                "scope": "my-gateway/invoke",
                "domain_prefix": "some-prefix",
            },
        }

        # Simulate API error
        mock_bedrock.create_gateway.side_effect = ValueError("API Error")

        with pytest.raises(ValueError):
            gateway_client.create_mcp_gateway(name="test-error", role_arn="arn:aws:iam::123:role/Test")

    def test_get_test_token_for_cognito_network_error_with_retry(self, gateway_client):
        """Test token retrieval with network error and retry logic"""
        import urllib3.exceptions

        client_info = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scope": "test-gateway/invoke",
            "token_endpoint": "https://test-domain.auth.us-west-2.amazoncognito.com/oauth2/token",
            "domain_prefix": "test-domain",
        }

        # Mock successful response after retries
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data.decode.return_value = '{"access_token": "retry_success_token", "token_type": "Bearer"}'

        with patch("urllib3.PoolManager") as mock_pool_manager, patch("time.sleep") as mock_sleep:
            mock_http = Mock()
            mock_pool_manager.return_value = mock_http

            # First 2 calls fail with DNS error, third succeeds
            name_error = Exception("NameResolutionError")
            mock_http.request.side_effect = [
                urllib3.exceptions.MaxRetryError(
                    None, "https://test-domain.auth.us-west-2.amazoncognito.com/oauth2/token", reason=name_error
                ),
                urllib3.exceptions.MaxRetryError(
                    None, "https://test-domain.auth.us-west-2.amazoncognito.com/oauth2/token", reason=name_error
                ),
                mock_response,
            ]

            # Call the method
            token = gateway_client.get_access_token_for_cognito(client_info)

            # Verify success after retries
            assert token == "retry_success_token"

            # Verify retry logic was called
            assert mock_http.request.call_count == 3

            # Verify sleep was called for DNS propagation + retries
            # First call: DNS propagation (60s), then 2 retry delays (10s each)
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert 10 in sleep_calls  # DNS propagation wait
            assert sleep_calls.count(10) == 2  # Two retry delays
