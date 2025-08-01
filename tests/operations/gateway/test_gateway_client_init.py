"""Tests for Bedrock AgentCore Gateway Client functionality - Part 1."""

import json
import logging
from unittest.mock import Mock, call, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
from bedrock_agentcore_starter_toolkit.operations.gateway.constants import (
    API_MODEL_BUCKETS,
    CREATE_OPENAPI_TARGET_INVALID_CREDENTIALS_SHAPE_EXCEPTION_MESSAGE,
    LAMBDA_CONFIG,
)
from bedrock_agentcore_starter_toolkit.operations.gateway.exceptions import GatewaySetupException


class TestGatewayClientInitialization:
    """Test GatewayClient initialization."""

    @patch("boto3.client")
    @patch("boto3.Session")
    def test_init_with_default_region(self, mock_session, mock_client):
        """Test GatewayClient initialization with default region."""
        mock_boto3_client = Mock()
        mock_client.return_value = mock_boto3_client
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        client = GatewayClient()

        # Verify default region is set
        assert client.region == "us-west-2"

        # Verify boto3 client is created with correct parameters
        mock_client.assert_called_once_with("bedrock-agentcore-control", region_name="us-west-2")

        # Verify session is created with correct region
        mock_session.assert_called_once_with(region_name="us-west-2")

        # Verify client and session are set
        assert client.client == mock_boto3_client
        assert client.session == mock_session_instance

    @patch("boto3.client")
    @patch("boto3.Session")
    def test_init_with_custom_region(self, mock_session, mock_client):
        """Test GatewayClient initialization with custom region."""
        mock_boto3_client = Mock()
        mock_client.return_value = mock_boto3_client
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        client = GatewayClient(region_name="eu-west-1")

        # Verify custom region is set
        assert client.region == "eu-west-1"

        # Verify boto3 client is created with custom region
        mock_client.assert_called_once_with("bedrock-agentcore-control", region_name="eu-west-1")

        # Verify session is created with custom region
        mock_session.assert_called_once_with(region_name="eu-west-1")

    @patch("boto3.client")
    @patch("boto3.Session")
    def test_init_with_endpoint_url(self, mock_session, mock_client):
        """Test GatewayClient initialization with custom endpoint URL."""
        mock_boto3_client = Mock()
        mock_client.return_value = mock_boto3_client
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        endpoint_url = "https://custom-endpoint.example.com"
        client = GatewayClient(region_name="us-east-1", endpoint_url=endpoint_url)

        # Verify region is set
        assert client.region == "us-east-1"

        # Verify boto3 client is created with endpoint URL
        mock_client.assert_called_once_with(
            "bedrock-agentcore-control", region_name="us-east-1", endpoint_url=endpoint_url
        )

    @patch("boto3.client")
    @patch("boto3.Session")
    def test_init_logger_setup(self, mock_session, mock_client):
        """Test that logger is properly initialized."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.handlers = []  # No existing handlers
            mock_get_logger.return_value = mock_logger

            mock_handler = Mock()
            with patch("logging.StreamHandler", return_value=mock_handler):
                with patch("logging.Formatter") as mock_formatter:
                    mock_formatter_instance = Mock()
                    mock_formatter.return_value = mock_formatter_instance

                    GatewayClient()

                    # Verify logger setup
                    mock_get_logger.assert_called_once_with("bedrock_agentcore.gateway")
                    mock_handler.setFormatter.assert_called_once_with(mock_formatter_instance)
                    mock_logger.addHandler.assert_called_once_with(mock_handler)
                    mock_logger.setLevel.assert_called_once_with(logging.INFO)

    def test_generate_random_id(self):
        """Test generate_random_id static method."""
        # Test that it returns a string of length 8
        random_id = GatewayClient.generate_random_id()
        assert isinstance(random_id, str)
        assert len(random_id) == 8

        # Test that multiple calls return different IDs
        random_id2 = GatewayClient.generate_random_id()
        assert random_id != random_id2


class TestCreateMCPGateway:
    """Test create_mcp_gateway method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient()
            self.client.client = Mock()
            self.client.session = Mock()
            self.client.logger = Mock()

    def test_create_mcp_gateway_with_all_parameters(self):
        """Test create_mcp_gateway with all parameters provided."""
        # Mock the create_gateway response
        mock_gateway_response = {
            "gatewayId": "test-gateway-123",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
            "gatewayUrl": "https://test-gateway.us-west-2.amazonaws.com",
            "status": "CREATING",
        }
        self.client.client.create_gateway.return_value = mock_gateway_response

        # Mock the wait_for_ready method
        with patch.object(self.client, "_GatewayClient__wait_for_ready") as mock_wait:
            authorizer_config = {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://example.com/.well-known/openid_configuration",
                    "allowedClients": ["client1"],
                }
            }

            result = self.client.create_mcp_gateway(
                name="TestGateway",
                role_arn="arn:aws:iam::123456789012:role/TestRole",
                authorizer_config=authorizer_config,
                enable_semantic_search=True,
            )

            # Verify create_gateway was called with correct parameters
            expected_request = {
                "name": "TestGateway",
                "roleArn": "arn:aws:iam::123456789012:role/TestRole",
                "protocolType": "MCP",
                "authorizerType": "CUSTOM_JWT",
                "authorizerConfiguration": authorizer_config,
                "protocolConfiguration": {"mcp": {"searchType": "SEMANTIC"}},
            }
            self.client.client.create_gateway.assert_called_once_with(**expected_request)

            # Verify wait_for_ready was called
            mock_wait.assert_called_once_with(
                method=self.client.client.get_gateway,
                identifiers={"gatewayIdentifier": "test-gateway-123"},
                resource_name="Gateway",
            )

            # Verify return value
            assert result == mock_gateway_response

    def test_create_mcp_gateway_with_defaults(self):
        """Test create_mcp_gateway with default parameters."""
        # Mock dependencies
        mock_gateway_response = {
            "gatewayId": "test-gateway-456",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-456",
            "gatewayUrl": "https://test-gateway.us-west-2.amazonaws.com",
        }
        self.client.client.create_gateway.return_value = mock_gateway_response

        with patch.object(self.client, "_GatewayClient__wait_for_ready"):
            with patch(
                "bedrock_agentcore_starter_toolkit.operations.gateway.client.create_gateway_execution_role"
            ) as mock_create_role:
                mock_create_role.return_value = "arn:aws:iam::123456789012:role/CreatedRole"

                with patch.object(self.client, "create_oauth_authorizer_with_cognito") as mock_create_auth:
                    mock_auth_config = {
                        "customJWTAuthorizer": {
                            "discoveryUrl": "https://cognito.amazonaws.com/.well-known/openid_configuration",
                            "allowedClients": ["cognito-client"],
                        }
                    }
                    mock_create_auth.return_value = {"authorizer_config": mock_auth_config}

                    # Mock generate_random_id to return predictable value
                    with patch.object(GatewayClient, "generate_random_id", return_value="12345678"):
                        self.client.create_mcp_gateway()

                        # Verify role creation was called
                        mock_create_role.assert_called_once_with(self.client.session, self.client.logger)

                        # Verify authorizer creation was called
                        mock_create_auth.assert_called_once_with("TestGateway12345678")

                        # Verify create_gateway was called with generated values
                        call_args = self.client.client.create_gateway.call_args[1]
                        assert call_args["name"] == "TestGateway12345678"
                        assert call_args["roleArn"] == "arn:aws:iam::123456789012:role/CreatedRole"
                        assert call_args["authorizerConfiguration"] == mock_auth_config

    def test_create_mcp_gateway_without_semantic_search(self):
        """Test create_mcp_gateway with semantic search disabled."""
        mock_gateway_response = {"gatewayId": "test-gateway", "gatewayArn": "test-arn", "gatewayUrl": "test-url"}
        self.client.client.create_gateway.return_value = mock_gateway_response

        with patch.object(self.client, "_GatewayClient__wait_for_ready"):
            with patch(
                "bedrock_agentcore_starter_toolkit.operations.gateway.client.create_gateway_execution_role"
            ) as mock_create_role:
                mock_create_role.return_value = "arn:aws:iam::123456789012:role/TestRole"

                with patch.object(self.client, "create_oauth_authorizer_with_cognito") as mock_create_auth:
                    mock_create_auth.return_value = {"authorizer_config": {"test": "config"}}

                    self.client.create_mcp_gateway(enable_semantic_search=False)

                    # Verify protocolConfiguration is not included when semantic search is disabled
                    call_args = self.client.client.create_gateway.call_args[1]
                    assert "protocolConfiguration" not in call_args

    def test_create_mcp_gateway_client_error(self):
        """Test create_mcp_gateway handles client errors."""
        # Mock create_gateway to raise ClientError
        client_error = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            operation_name="CreateGateway",
        )
        self.client.client.create_gateway.side_effect = client_error

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.gateway.client.create_gateway_execution_role"
        ) as mock_create_role:
            mock_create_role.return_value = "arn:aws:iam::123456789012:role/TestRole"

            with patch.object(self.client, "create_oauth_authorizer_with_cognito") as mock_create_auth:
                mock_create_auth.return_value = {"authorizer_config": {"test": "config"}}

                with pytest.raises(ClientError):
                    self.client.create_mcp_gateway()


class TestWaitForReady:
    """Test __wait_for_ready method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient()

    def test_wait_for_ready_success(self):
        """Test __wait_for_ready when resource becomes ready."""
        mock_method = Mock()
        mock_method.side_effect = [{"status": "CREATING"}, {"status": "CREATING"}, {"status": "READY"}]

        with patch("time.sleep") as mock_sleep:
            # Should not raise any exception
            self.client._GatewayClient__wait_for_ready(
                resource_name="TestResource",
                method=mock_method,
                identifiers={"id": "test-123"},
                max_attempts=5,
                delay=1,
            )

            # Verify method was called 3 times
            assert mock_method.call_count == 3
            mock_method.assert_has_calls([call(id="test-123"), call(id="test-123"), call(id="test-123")])

            # Verify sleep was called 2 times (not on the last successful call)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_has_calls([call(1), call(1)])

    def test_wait_for_ready_timeout(self):
        """Test __wait_for_ready when resource times out."""
        mock_method = Mock()
        mock_method.return_value = {"status": "CREATING"}

        with patch("time.sleep"):
            with pytest.raises(TimeoutError, match="TestResource not ready after 3 attempts"):
                self.client._GatewayClient__wait_for_ready(
                    resource_name="TestResource",
                    method=mock_method,
                    identifiers={"id": "test-123"},
                    max_attempts=3,
                    delay=1,
                )

    def test_wait_for_ready_failure_status(self):
        """Test __wait_for_ready when resource fails."""
        mock_method = Mock()
        mock_method.return_value = {"status": "FAILED", "error": "Something went wrong"}

        with pytest.raises(Exception, match="TestResource failed"):
            self.client._GatewayClient__wait_for_ready(
                resource_name="TestResource", method=mock_method, identifiers={"id": "test-123"}
            )

    def test_wait_for_ready_unknown_status(self):
        """Test __wait_for_ready with unknown status."""
        mock_method = Mock()
        mock_method.return_value = {"status": "UNKNOWN"}

        with pytest.raises(Exception, match="TestResource failed"):
            self.client._GatewayClient__wait_for_ready(
                resource_name="TestResource", method=mock_method, identifiers={"id": "test-123"}
            )

    def test_wait_for_ready_no_status(self):
        """Test __wait_for_ready when response has no status."""
        mock_method = Mock()
        mock_method.return_value = {"other_field": "value"}

        with pytest.raises(Exception, match="TestResource failed"):
            self.client._GatewayClient__wait_for_ready(
                resource_name="TestResource", method=mock_method, identifiers={"id": "test-123"}
            )


class TestCreateMCPGatewayTarget:
    """Test create_mcp_gateway_target method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient()
            self.client.client = Mock()
            self.client.session = Mock()
            self.client.logger = Mock()

        self.gateway = {
            "gatewayId": "test-gateway-123",
            "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
            "gatewayUrl": "https://test-gateway.us-west-2.amazonaws.com",
            "roleArn": "arn:aws:iam::123456789012:role/TestRole",
        }

    def test_create_mcp_gateway_target_lambda_with_defaults(self):
        """Test create_mcp_gateway_target with lambda target and default values."""
        mock_target_response = {
            "targetId": "test-target-123",
            "targetArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway-target/test-target-123",
        }
        self.client.client.create_gateway_target.return_value = mock_target_response

        with patch.object(self.client, "_GatewayClient__wait_for_ready"):
            with patch.object(self.client, "_GatewayClient__handle_lambda_target_creation") as mock_handle_lambda:
                mock_lambda_config = {
                    "targetConfiguration": {
                        "mcp": {"lambda": {"lambdaArn": "test-lambda-arn", "toolSchema": LAMBDA_CONFIG}}
                    },
                    "credentialProviderConfigurations": [{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
                }
                mock_handle_lambda.return_value = mock_lambda_config

                with patch.object(GatewayClient, "generate_random_id", return_value="12345678"):
                    result = self.client.create_mcp_gateway_target(gateway=self.gateway, target_type="lambda")

                    # Verify lambda handler was called
                    mock_handle_lambda.assert_called_once_with(self.gateway["roleArn"])

                    # Verify create_gateway_target was called with correct parameters
                    expected_request = {
                        "gatewayIdentifier": "test-gateway-123",
                        "name": "TestGatewayTarget12345678",
                        "targetConfiguration": {"mcp": {"lambda": None}},
                        **mock_lambda_config,
                    }
                    # Remove the duplicate targetConfiguration
                    expected_request["targetConfiguration"] = mock_lambda_config["targetConfiguration"]

                    call_args = self.client.client.create_gateway_target.call_args[1]
                    assert call_args["gatewayIdentifier"] == expected_request["gatewayIdentifier"]
                    assert call_args["name"] == expected_request["name"]

                    assert result == mock_target_response

    def test_create_mcp_gateway_target_openapi_schema(self):
        """Test create_mcp_gateway_target with OpenAPI schema target."""
        mock_target_response = {"targetId": "openapi-target-456"}
        self.client.client.create_gateway_target.return_value = mock_target_response

        openapi_payload = {"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0.0"}}

        credentials = {
            "api_key": "test-api-key",
            "credential_location": "HEADER",
            "credential_parameter_name": "X-API-Key",
        }

        with patch.object(self.client, "_GatewayClient__wait_for_ready"):
            with patch.object(
                self.client, "_GatewayClient__handle_openapi_target_credential_provider_creation"
            ) as mock_handle_openapi:
                mock_cred_config = {
                    "credentialProviderConfigurations": [
                        {
                            "credentialProviderType": "API_KEY",
                            "credentialProvider": {"apiKeyCredentialProvider": {"providerArn": "test-arn"}},
                        }
                    ]
                }
                mock_handle_openapi.return_value = mock_cred_config

                self.client.create_mcp_gateway_target(
                    gateway=self.gateway,
                    name="OpenAPITarget",
                    target_type="openApiSchema",
                    target_payload=json.dumps(openapi_payload),
                    credentials=credentials,
                )

                # Verify OpenAPI handler was called
                mock_handle_openapi.assert_called_once_with(name="OpenAPITarget", credentials=credentials)

                # Verify create_gateway_target was called
                call_args = self.client.client.create_gateway_target.call_args[1]
                assert call_args["name"] == "OpenAPITarget"
                assert call_args["targetConfiguration"]["mcp"]["openApiSchema"] == json.dumps(openapi_payload)

    def test_create_mcp_gateway_target_smithy_model_with_defaults(self):
        """Test create_mcp_gateway_target with smithy model and default payload."""
        self.client.region = "us-west-2"  # Set region that has bucket mapping

        mock_target_response = {"targetId": "smithy-target-789"}
        self.client.client.create_gateway_target.return_value = mock_target_response

        with patch.object(self.client, "_GatewayClient__wait_for_ready"):
            self.client.create_mcp_gateway_target(gateway=self.gateway, target_type="smithyModel")

            # Verify create_gateway_target was called with smithy configuration
            call_args = self.client.client.create_gateway_target.call_args[1]
            expected_bucket = API_MODEL_BUCKETS["us-west-2"]
            expected_uri = f"s3://{expected_bucket}/dynamodb-smithy.json"

            assert call_args["targetConfiguration"]["mcp"]["smithyModel"]["s3"]["uri"] == expected_uri
            assert call_args["credentialProviderConfigurations"] == [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

    def test_create_mcp_gateway_target_smithy_model_unsupported_region(self):
        """Test create_mcp_gateway_target with smithy model in unsupported region."""
        self.client.region = "unsupported-region"

        with pytest.raises(Exception, match="Automatic smithyModel creation is not supported in this region"):
            self.client.create_mcp_gateway_target(gateway=self.gateway, target_type="smithyModel")

    def test_create_mcp_gateway_target_openapi_without_payload_raises_exception(self):
        """Test create_mcp_gateway_target with OpenAPI schema but no payload."""
        with pytest.raises(Exception, match="You must provide a target configuration for your OpenAPI specification"):
            self.client.create_mcp_gateway_target(gateway=self.gateway, target_type="openApiSchema")

    def test_create_mcp_gateway_target_with_explicit_name_and_payload(self):
        """Test create_mcp_gateway_target with explicit name and payload."""
        mock_target_response = {"targetId": "explicit-target"}
        self.client.client.create_gateway_target.return_value = mock_target_response

        custom_payload = {"custom": "configuration"}

        with patch.object(self.client, "_GatewayClient__wait_for_ready"):
            self.client.create_mcp_gateway_target(
                gateway=self.gateway,
                name="ExplicitTarget",
                target_type="lambda",
                target_payload=json.dumps(custom_payload),
            )

            # Verify create_gateway_target was called with explicit values
            call_args = self.client.client.create_gateway_target.call_args[1]
            assert call_args["name"] == "ExplicitTarget"
            assert call_args["targetConfiguration"]["mcp"]["lambda"] == json.dumps(custom_payload)


class TestHandleLambdaTargetCreation:
    """Test __handle_lambda_target_creation method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient()
            self.client.session = Mock()
            self.client.logger = Mock()

    def test_handle_lambda_target_creation(self):
        """Test __handle_lambda_target_creation method."""
        role_arn = "arn:aws:iam::123456789012:role/TestRole"
        lambda_arn = "arn:aws:lambda:us-west-2:123456789012:function:TestFunction"

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.gateway.client.create_test_lambda"
        ) as mock_create_lambda:
            mock_create_lambda.return_value = lambda_arn

            result = self.client._GatewayClient__handle_lambda_target_creation(role_arn)

            # Verify create_test_lambda was called with correct parameters
            mock_create_lambda.assert_called_once_with(
                self.client.session, logger=self.client.logger, gateway_role_arn=role_arn
            )

            # Verify return value structure
            expected_result = {
                "targetConfiguration": {"mcp": {"lambda": {"lambdaArn": lambda_arn, "toolSchema": LAMBDA_CONFIG}}}
            }
            assert result == expected_result


class TestHandleOpenAPITargetCredentialProviderCreation:
    """Test __handle_openapi_target_credential_provider_creation method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient()
            self.client.session = Mock()
            self.client.logger = Mock()

        # Mock the agentcredentialprovider client
        self.mock_acps_client = Mock()
        self.client.session.client.return_value = self.mock_acps_client

    def test_handle_openapi_target_api_key_credentials(self):
        """Test __handle_openapi_target_credential_provider_creation with API key."""
        name = "TestTarget"
        credentials = {
            "api_key": "test-api-key-123",
            "credential_location": "HEADER",
            "credential_parameter_name": "X-API-Key",
        }

        # Mock create_api_key_credential_provider response
        provider_arn = "arn:aws:agentcredentialprovider:us-west-2:123456789012:provider/test-provider"
        self.mock_acps_client.create_api_key_credential_provider.return_value = {"credentialProviderArn": provider_arn}

        with patch.object(GatewayClient, "generate_random_id", return_value="12345678"):
            result = self.client._GatewayClient__handle_openapi_target_credential_provider_creation(
                name=name, credentials=credentials
            )

            # Verify create_api_key_credential_provider was called
            self.mock_acps_client.create_api_key_credential_provider.assert_called_once_with(
                name=f"{name}-ApiKey-12345678", apiKey="test-api-key-123"
            )

            # Verify return value structure
            expected_result = {
                "credentialProviderConfigurations": [
                    {
                        "credentialProviderType": "API_KEY",
                        "credentialProvider": {
                            "apiKeyCredentialProvider": {
                                "providerArn": provider_arn,
                                "credentialLocation": "HEADER",
                                "credentialParameterName": "X-API-Key",
                            }
                        },
                    }
                ]
            }
            assert result == expected_result

    def test_handle_openapi_target_oauth2_credentials(self):
        """Test __handle_openapi_target_credential_provider_creation with OAuth2."""
        name = "TestTarget"
        oauth_config = {
            "customOauth2ProviderConfig": {
                "oauthDiscovery": {
                    "authorizationServerMetadata": {
                        "issuer": "https://example.com",
                        "tokenEndpoint": "https://example.com/token",
                    }
                },
                "clientId": "test-client-id",
                "clientSecret": "test-client-secret",
            }
        }
        credentials = {"oauth2_provider_config": oauth_config, "scopes": ["read", "write"]}

        # Mock create_oauth2_credential_provider response
        provider_arn = "arn:aws:agentcredentialprovider:us-west-2:123456789012:provider/oauth-provider"
        self.mock_acps_client.create_oauth2_credential_provider.return_value = {"credentialProviderArn": provider_arn}

        with patch.object(GatewayClient, "generate_random_id", return_value="87654321"):
            result = self.client._GatewayClient__handle_openapi_target_credential_provider_creation(
                name=name, credentials=credentials
            )

            # Verify create_oauth2_credential_provider was called
            self.mock_acps_client.create_oauth2_credential_provider.assert_called_once_with(
                name=f"{name}-OAuth-Credentials-87654321",
                credentialProviderVendor="CustomOauth2",
                oauth2ProviderConfigInput=oauth_config,
            )

            # Verify return value structure
            expected_result = {
                "credentialProviderConfigurations": [
                    {
                        "credentialProviderType": "OAUTH",
                        "credentialProvider": {
                            "oauthCredentialProvider": {"providerArn": provider_arn, "scopes": ["read", "write"]}
                        },
                    }
                ]
            }
            assert result == expected_result

    def test_handle_openapi_target_oauth2_credentials_without_scopes(self):
        """Test __handle_openapi_target_credential_provider_creation with OAuth2 but no scopes."""
        name = "TestTarget"
        oauth_config = {"customOauth2ProviderConfig": {"clientId": "test-client"}}
        credentials = {"oauth2_provider_config": oauth_config}

        provider_arn = "arn:aws:agentcredentialprovider:us-west-2:123456789012:provider/oauth-provider"
        self.mock_acps_client.create_oauth2_credential_provider.return_value = {"credentialProviderArn": provider_arn}

        result = self.client._GatewayClient__handle_openapi_target_credential_provider_creation(
            name=name, credentials=credentials
        )

        # Verify scopes defaults to empty list
        expected_scopes = []
        assert (
            result["credentialProviderConfigurations"][0]["credentialProvider"]["oauthCredentialProvider"]["scopes"]
            == expected_scopes
        )

    def test_handle_openapi_target_invalid_credentials_raises_exception(self):
        """Test __handle_openapi_target_credential_provider_creation with invalid credentials."""
        name = "TestTarget"
        credentials = {"invalid_key": "invalid_value"}

        with pytest.raises(Exception) as exc_info:
            self.client._GatewayClient__handle_openapi_target_credential_provider_creation(
                name=name, credentials=credentials
            )

        # Verify the correct exception message is raised
        assert CREATE_OPENAPI_TARGET_INVALID_CREDENTIALS_SHAPE_EXCEPTION_MESSAGE in str(exc_info.value)


class TestCreateOAuthAuthorizerWithCognito:
    """Test create_oauth_authorizer_with_cognito method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient(region_name="us-east-1")
            self.client.session = Mock()
            self.client.logger = Mock()

        # Mock the Cognito client
        self.mock_cognito_client = Mock()
        self.client.session.client.return_value = self.mock_cognito_client

    def test_create_oauth_authorizer_with_cognito_success(self):
        """Test successful creation of OAuth authorizer with Cognito."""
        gateway_name = "TestGateway"

        # Mock Cognito responses
        user_pool_id = "us-east-1_TestPool123"
        client_id = "test-client-id-123"
        client_secret = "test-client-secret-456"

        self.mock_cognito_client.create_user_pool.return_value = {"UserPool": {"Id": user_pool_id}}

        self.mock_cognito_client.create_user_pool_client.return_value = {
            "UserPoolClient": {"ClientId": client_id, "ClientSecret": client_secret}
        }

        # Mock domain status check
        self.mock_cognito_client.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "ACTIVE"}}

        with patch.object(GatewayClient, "generate_random_id", side_effect=["12345678", "87654321", "abcdefgh"]):
            with patch("time.sleep"):  # Mock sleep to speed up test
                result = self.client.create_oauth_authorizer_with_cognito(gateway_name)

                # Verify user pool creation
                self.mock_cognito_client.create_user_pool.assert_called_once_with(PoolName="agentcore-gateway-12345678")

                # Verify domain creation
                self.mock_cognito_client.create_user_pool_domain.assert_called_once_with(
                    Domain="agentcore-87654321", UserPoolId=user_pool_id
                )

                # Verify resource server creation
                self.mock_cognito_client.create_resource_server.assert_called_once_with(
                    UserPoolId=user_pool_id,
                    Identifier=gateway_name,
                    Name=gateway_name,
                    Scopes=[{"ScopeName": "invoke", "ScopeDescription": "Scope for invoking the agentcore gateway"}],
                )

                # Verify client creation
                self.mock_cognito_client.create_user_pool_client.assert_called_once_with(
                    UserPoolId=user_pool_id,
                    ClientName="agentcore-client-abcdefgh",
                    GenerateSecret=True,
                    AllowedOAuthFlows=["client_credentials"],
                    AllowedOAuthScopes=[f"{gateway_name}/invoke"],
                    AllowedOAuthFlowsUserPoolClient=True,
                    SupportedIdentityProviders=["COGNITO"],
                )

                # Verify return value structure
                expected_discovery_url = (
                    f"https://cognito-idp.us-east-1.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
                )
                expected_token_endpoint = "https://agentcore-87654321.auth.us-east-1.amazoncognito.com/oauth2/token"

                assert result["authorizer_config"]["customJWTAuthorizer"]["allowedClients"] == [client_id]
                assert result["authorizer_config"]["customJWTAuthorizer"]["discoveryUrl"] == expected_discovery_url
                assert result["client_info"]["client_id"] == client_id
                assert result["client_info"]["client_secret"] == client_secret
                assert result["client_info"]["user_pool_id"] == user_pool_id
                assert result["client_info"]["token_endpoint"] == expected_token_endpoint
                assert result["client_info"]["scope"] == f"{gateway_name}/invoke"

    def test_create_oauth_authorizer_with_cognito_domain_not_active(self):
        """Test OAuth authorizer creation when domain is not immediately active."""
        gateway_name = "TestGateway"
        user_pool_id = "us-east-1_TestPool123"

        self.mock_cognito_client.create_user_pool.return_value = {"UserPool": {"Id": user_pool_id}}

        self.mock_cognito_client.create_user_pool_client.return_value = {
            "UserPoolClient": {"ClientId": "test-client-id", "ClientSecret": "test-client-secret"}
        }

        # Mock domain status check - first call returns CREATING, second returns ACTIVE
        self.mock_cognito_client.describe_user_pool_domain.side_effect = [
            {"DomainDescription": {"Status": "CREATING"}},
            {"DomainDescription": {"Status": "ACTIVE"}},
        ]

        with patch("time.sleep") as mock_sleep:
            result = self.client.create_oauth_authorizer_with_cognito(gateway_name)

            # Verify domain status was checked multiple times
            assert self.mock_cognito_client.describe_user_pool_domain.call_count == 2

            # Verify sleep was called during domain wait
            mock_sleep.assert_called()

            # Should still return valid result
            assert "authorizer_config" in result
            assert "client_info" in result

    def test_create_oauth_authorizer_with_cognito_domain_timeout(self):
        """Test OAuth authorizer creation when domain never becomes active."""
        gateway_name = "TestGateway"
        user_pool_id = "us-east-1_TestPool123"

        self.mock_cognito_client.create_user_pool.return_value = {"UserPool": {"Id": user_pool_id}}

        self.mock_cognito_client.create_user_pool_client.return_value = {
            "UserPoolClient": {"ClientId": "test-client-id", "ClientSecret": "test-client-secret"}
        }

        # Mock domain status check - always returns CREATING
        self.mock_cognito_client.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "CREATING"}}

        with patch("time.sleep"):
            result = self.client.create_oauth_authorizer_with_cognito(gateway_name)

            # Should still complete but log warning
            self.client.logger.warning.assert_called_with("  ⚠️  Domain may not be fully available yet")

            # Should still return valid result
            assert "authorizer_config" in result
            assert "client_info" in result

    def test_create_oauth_authorizer_with_cognito_exception(self):
        """Test OAuth authorizer creation when Cognito operations fail."""
        gateway_name = "TestGateway"

        # Mock create_user_pool to raise an exception
        cognito_error = ClientError(
            error_response={"Error": {"Code": "LimitExceededException", "Message": "Too many user pools"}},
            operation_name="CreateUserPool",
        )
        self.mock_cognito_client.create_user_pool.side_effect = cognito_error

        with pytest.raises(GatewaySetupException, match="Failed to create Cognito resources"):
            self.client.create_oauth_authorizer_with_cognito(gateway_name)


class TestGetAccessTokenForCognito:
    """Test get_access_token_for_cognito method."""

    def setup_method(self):
        """Setup test fixtures."""
        with patch("boto3.client"), patch("boto3.Session"):
            self.client = GatewayClient()
            self.client.logger = Mock()

        self.client_info = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scope": "TestGateway/invoke",
            "token_endpoint": "https://test-domain.auth.us-west-2.amazoncognito.com/oauth2/token",
        }

    @patch("urllib3.PoolManager")
    def test_get_access_token_for_cognito_success(self, mock_pool_manager):
        """Test successful token retrieval from Cognito."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data.decode.return_value = json.dumps(
            {"access_token": "test-access-token-123", "token_type": "Bearer", "expires_in": 3600}
        )

        mock_http = Mock()
        mock_http.request.return_value = mock_response
        mock_pool_manager.return_value = mock_http

        result = self.client.get_access_token_for_cognito(self.client_info)

        # Verify HTTP request was made correctly
        mock_http.request.assert_called_once_with(
            "POST",
            self.client_info["token_endpoint"],
            body="grant_type=client_credentials&client_id=test-client-id&client_secret=test-client-secret&scope=TestGateway%2Finvoke",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
            retries=False,
        )

        # Verify return value
        assert result == "test-access-token-123"

    @patch("urllib3.PoolManager")
    def test_get_access_token_for_cognito_http_error(self, mock_pool_manager):
        """Test token retrieval when HTTP request fails."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status = 400
        mock_response.data.decode.return_value = '{"error": "invalid_client"}'

        mock_http = Mock()
        mock_http.request.return_value = mock_response
        mock_pool_manager.return_value = mock_http

        with pytest.raises(GatewaySetupException, match="Token request failed"):
            self.client.get_access_token_for_cognito(self.client_info)

    # @patch('urllib3.PoolManager')
    # def test_get_access_token_for_cognito_name_resolution_error_with_retry(self, mock_pool_manager):
    #     """Test token retrieval with name resolution error and successful retry."""
    #     # Mock name resolution error on first attempt, success on second
    #     name_resolution_error = urllib3.exceptions.MaxRetryError(
    #         pool=Mock(),
    #         url="test-url",
    #         reason=urllib3.exceptions.NameResolutionError("Name resolution failed")
    #     )
    #
    #     mock_success_response = Mock()
    #     mock_success_response.status = 200
    #     mock_success_response.data.decode.return_value = json.dumps({
    #         "access_token": "retry-success-token"
    #     })
    #
    #     mock_http = Mock()
    #     mock_http.request.side_effect = [name_resolution_error, mock_success_response]
    #     mock_pool_manager.return_value = mock_http
    #
    #     with patch('time.sleep') as mock_sleep:
    #         result = self.client.get_access_token_for_cognito(self.client_info)
    #
    #         # Verify retry logic
    #         assert mock_http.request.call_count == 2
    #         mock_sleep.assert_called_once_with(10)  # retry delay
    #
    #         # Verify successful result after retry
    #         assert result == "retry-success-token"
    #
    # @patch('urllib3.PoolManager')
    # def test_get_access_token_for_cognito_max_retries_exceeded(self, mock_pool_manager):
    #     """Test token retrieval when max retries are exceeded."""
    #     # Mock persistent name resolution error
    #     name_resolution_error = urllib3.exceptions.MaxRetryError(
    #         pool=Mock(),
    #         url="test-url",
    #         reason=urllib3.exceptions.NameResolutionError("Name resolution failed")
    #     )
    #
    #     mock_http = Mock()
    #     mock_http.request.side_effect = name_resolution_error
    #     mock_pool_manager.return_value = mock_http
    #
    #     with patch('time.sleep'):
    #         with pytest.raises(GatewaySetupException, match="Failed to get test token"):
    #             self.client.get_access_token_for_cognito(self.client_info)
    #
    #         # Verify all retry attempts were made
    #         assert mock_http.request.call_count == 5  # max_retries

    @patch("urllib3.PoolManager")
    def test_get_access_token_for_cognito_general_exception(self, mock_pool_manager):
        """Test token retrieval when general exception occurs."""
        # Mock general exception
        mock_http = Mock()
        mock_http.request.side_effect = Exception("General network error")
        mock_pool_manager.return_value = mock_http

        with pytest.raises(GatewaySetupException, match="Failed to get test token"):
            self.client.get_access_token_for_cognito(self.client_info)
