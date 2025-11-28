"""Tests for Bedrock AgentCore Gateway CLI functionality."""

import json
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.gateway.commands import gateway_app


class TestBedrockAgentCoreGatewayCLI:
    """Test Bedrock AgentCore Gateway CLI commands."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    def test_create_mcp_gateway_command_basic(self):
        """Test basic create_mcp_gateway command."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            # Mock the GatewayClient instance and its methods
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            # Mock the create_mcp_gateway method return value
            mock_gateway_response = {
                "gatewayId": "test-gateway-123",
                "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123",
                "gatewayUrl": "https://test-gateway.us-west-2.amazonaws.com",
                "status": "CREATING",
                "name": "TestGateway",
                "roleArn": "arn:aws:iam::123456789012:role/TestGatewayRole",
            }
            mock_client_instance.create_mcp_gateway.return_value = mock_gateway_response

            # Test the command with basic parameters
            result = self.runner.invoke(
                gateway_app,
                [
                    "create-mcp-gateway",
                    "--region",
                    "us-west-2",
                    "--name",
                    "TestGateway",
                    "--role-arn",
                    "arn:aws:iam::123456789012:role/TestGatewayRole",
                ],
            )

            # Verify the command executed successfully
            assert result.exit_code == 0

            # Verify GatewayClient was initialized with correct region
            mock_gateway_client.assert_called_once_with(region_name="us-west-2")

            # Verify create_mcp_gateway was called with correct parameters
            mock_client_instance.create_mcp_gateway.assert_called_once_with(
                "TestGateway",
                "arn:aws:iam::123456789012:role/TestGatewayRole",
                "",  # empty authorizer config
                True,  # enable_semantic_search default
            )

    def test_create_mcp_gateway_with_defaults(self):
        """Test create_mcp_gateway command with default values."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            mock_gateway_response = {"gatewayId": "default-gateway"}
            mock_client_instance.create_mcp_gateway.return_value = mock_gateway_response

            # Test with minimal parameters (using defaults)
            result = self.runner.invoke(gateway_app, ["create-mcp-gateway"])

            assert result.exit_code == 0

            # Verify GatewayClient was initialized with default region (None)
            mock_gateway_client.assert_called_once_with(region_name=None)

            # Verify create_mcp_gateway was called with default values
            mock_client_instance.create_mcp_gateway.assert_called_once_with(
                None,  # name default
                None,  # role_arn default
                "",  # empty authorizer config
                True,  # enable_semantic_search default
            )

    def test_create_mcp_gateway_target_command_basic(self):
        """Test basic create_mcp_gateway_target command."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            mock_target_response = {
                "targetId": "test-target-123",
                "targetArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway-target/test-target-123",
                "status": "CREATING",
                "name": "TestTarget",
                "targetType": "lambda",
            }
            mock_client_instance.create_mcp_gateway_target.return_value = mock_target_response

            # Test the command with required parameters
            result = self.runner.invoke(
                gateway_app,
                [
                    "create-mcp-gateway-target",
                    "--gateway-arn",
                    "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway",
                    "--gateway-url",
                    "https://test-gateway.us-west-2.amazonaws.com",
                    "--role-arn",
                    "arn:aws:iam::123456789012:role/TestRole",
                    "--region",
                    "us-west-2",
                    "--name",
                    "TestTarget",
                    "--target-type",
                    "lambda",
                ],
            )

            assert result.exit_code == 0

            # Verify GatewayClient was initialized with correct region
            mock_gateway_client.assert_called_once_with(region_name="us-west-2")

            # Verify create_mcp_gateway_target was called with correct parameters
            expected_gateway = {
                "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway",
                "gatewayUrl": "https://test-gateway.us-west-2.amazonaws.com",
                "gatewayId": "test-gateway",  # extracted from ARN
                "roleArn": "arn:aws:iam::123456789012:role/TestRole",
            }

            mock_client_instance.create_mcp_gateway_target.assert_called_once_with(
                gateway=expected_gateway,
                name="TestTarget",
                target_type="lambda",
                target_payload="",
                credentials="",  # empty credentials
            )

    def test_create_mcp_gateway_target_with_openapi_schema(self):
        """Test create_mcp_gateway_target command with OpenAPI schema target."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            mock_target_response = {"targetId": "openapi-target-456", "targetType": "openApiSchema"}
            mock_client_instance.create_mcp_gateway_target.return_value = mock_target_response

            # Test OpenAPI schema payload and credentials
            openapi_payload = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {"/test": {"get": {"responses": {"200": {"description": "Success"}}}}},
            }

            credentials = {"type": "apiKey", "apiKey": {"name": "X-API-Key", "in": "header"}}

            result = self.runner.invoke(
                gateway_app,
                [
                    "create-mcp-gateway-target",
                    "--gateway-arn",
                    "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/openapi-gateway",
                    "--gateway-url",
                    "https://openapi-gateway.us-west-2.amazonaws.com",
                    "--role-arn",
                    "arn:aws:iam::123456789012:role/OpenAPIRole",
                    "--target-type",
                    "openApiSchema",
                    "--target-payload",
                    json.dumps(openapi_payload),
                    "--credentials",
                    json.dumps(credentials),
                ],
            )

            assert result.exit_code == 0

            # Verify create_mcp_gateway_target was called with OpenAPI parameters
            expected_gateway = {
                "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/openapi-gateway",
                "gatewayUrl": "https://openapi-gateway.us-west-2.amazonaws.com",
                "gatewayId": "openapi-gateway",
                "roleArn": "arn:aws:iam::123456789012:role/OpenAPIRole",
            }

            mock_client_instance.create_mcp_gateway_target.assert_called_once_with(
                gateway=expected_gateway,
                name=None,  # name not provided
                target_type="openApiSchema",
                target_payload=openapi_payload,
                credentials=credentials,  # parsed JSON
            )

    def test_create_mcp_gateway_target_with_defaults(self):
        """Test create_mcp_gateway_target command with default values."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            mock_target_response = {"targetId": "default-target"}
            mock_client_instance.create_mcp_gateway_target.return_value = mock_target_response

            # Test with minimal required parameters
            result = self.runner.invoke(
                gateway_app,
                [
                    "create-mcp-gateway-target",
                    "--gateway-arn",
                    "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/minimal-gateway",
                    "--gateway-url",
                    "https://minimal-gateway.us-west-2.amazonaws.com",
                    "--role-arn",
                    "arn:aws:iam::123456789012:role/MinimalRole",
                ],
            )

            assert result.exit_code == 0

            # Verify GatewayClient was initialized with default region
            mock_gateway_client.assert_called_once_with(region_name=None)

            # Verify create_mcp_gateway_target was called with default values
            expected_gateway = {
                "gatewayArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/minimal-gateway",
                "gatewayUrl": "https://minimal-gateway.us-west-2.amazonaws.com",
                "gatewayId": "minimal-gateway",
                "roleArn": "arn:aws:iam::123456789012:role/MinimalRole",
            }

            mock_client_instance.create_mcp_gateway_target.assert_called_once_with(
                gateway=expected_gateway,
                name=None,  # default
                target_type=None,  # default
                target_payload="",  # default
                credentials="",  # empty credentials
            )

    def test_create_mcp_gateway_invalid_json_authorizer_config(self):
        """Test create_mcp_gateway command with invalid JSON in authorizer config."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            # Test with invalid JSON
            result = self.runner.invoke(
                gateway_app, ["create-mcp-gateway", "--authorizer-config", "invalid-json-string"]
            )

            # Should fail due to JSON parsing error
            assert result.exit_code != 0
            assert "json" in result.stdout.lower() or isinstance(result.exception, json.JSONDecodeError)

    def test_create_mcp_gateway_target_invalid_json_credentials(self):
        """Test create_mcp_gateway_target command with invalid JSON in credentials."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance

            # Test with invalid JSON credentials
            result = self.runner.invoke(
                gateway_app,
                [
                    "create-mcp-gateway-target",
                    "--gateway-arn",
                    "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test",
                    "--gateway-url",
                    "https://test.amazonaws.com",
                    "--role-arn",
                    "arn:aws:iam::123456789012:role/TestRole",
                    "--credentials",
                    "invalid-json-credentials",
                ],
            )

            # Should fail due to JSON parsing error
            assert result.exit_code != 0
            assert "json" in result.stdout.lower() or isinstance(result.exception, json.JSONDecodeError)

    def test_list_mcp_gateways_command_parameters(self):
        """Test list-mcp-gateways command parameter parsing."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_client:
            mock_client.return_value.list_gateways.return_value = {"status": "success"}

            result = self.runner.invoke(
                gateway_app, ["list-mcp-gateways", "--region", "us-west-2", "--max-results", "10"]
            )

            assert result.exit_code == 0
            mock_client.assert_called_once_with(region_name="us-west-2")
            mock_client.return_value.list_gateways.assert_called_once_with(name=None, max_results=10)

    def test_get_mcp_gateway_command_flag_parsing(self):
        """Test get-mcp-gateway command uses updated --id and --arn flags."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_client:
            mock_client.return_value.get_gateway.return_value = {"status": "success"}

            # Test --id flag
            result = self.runner.invoke(gateway_app, ["get-mcp-gateway", "--id", "test-123"])
            assert result.exit_code == 0
            mock_client.return_value.get_gateway.assert_called_with(
                gateway_identifier="test-123", name=None, gateway_arn=None
            )

    def test_delete_mcp_gateway_command_flag_parsing(self):
        """Test delete-mcp-gateway command uses updated --arn flag."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_client:
            mock_client.return_value.delete_gateway.return_value = {"status": "success"}

            arn = "arn:aws:bedrock-agentcore:us-west-2:123:gateway/test"
            result = self.runner.invoke(gateway_app, ["delete-mcp-gateway", "--arn", arn])

            assert result.exit_code == 0
            mock_client.return_value.delete_gateway.assert_called_with(
                gateway_identifier=None, name=None, gateway_arn=arn, skip_resource_in_use=False
            )

    def test_delete_mcp_gateway_target_command_parameter_parsing(self):
        """Test delete-mcp-gateway-target command parses gateway and target parameters correctly."""
        with patch("bedrock_agentcore_starter_toolkit.cli.gateway.commands.GatewayClient") as mock_client:
            mock_client.return_value.delete_gateway_target.return_value = {"status": "success"}

            result = self.runner.invoke(
                gateway_app, ["delete-mcp-gateway-target", "--id", "gateway-123", "--target-id", "target-456"]
            )

            assert result.exit_code == 0
            mock_client.return_value.delete_gateway_target.assert_called_with(
                gateway_identifier="gateway-123", name=None, gateway_arn=None, target_id="target-456", target_name=None
            )
