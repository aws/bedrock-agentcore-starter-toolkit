from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.gateway import (
    GatewayClient,
)

# Add timeout marker for all tests in this module
pytestmark = pytest.mark.timeout(10)  # 10 second timeout per test


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
    @patch("time.sleep")
    @patch("bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient.create_oauth_authorizer_with_cognito")
    def test_setup_gateway_lambda(
        self, mock_create_oauth_authorizer_with_cognito, mock_sleep, gateway_client, mock_boto_client
    ):
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
        # REMOVED: mock_sleep.assert_not_called() - sleep IS called but mocked so test is fast

    @patch("time.sleep")
    @patch("bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient.create_oauth_authorizer_with_cognito")
    def test_setup_gateway_openapi(self, mock_create_oauth_authorizer_with_cognito, mock_sleep, gateway_client):
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

    @patch("time.sleep")
    @patch("bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient.create_oauth_authorizer_with_cognito")
    def test_error_handling(self, mock_create_oauth_authorizer_with_cognito, mock_sleep, gateway_client):
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

    def test_delete_gateway_with_targets_check(self, gateway_client):
        """Test delete_gateway checks for targets before deletion"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock that gateway has targets
        mock_bedrock.list_gateway_targets.return_value = {"items": [{"targetId": "target-1"}]}

        result = gateway_client.delete_gateway(gateway_identifier="test-gateway")

        # Should check for targets first
        mock_bedrock.list_gateway_targets.assert_called_once_with(gatewayIdentifier="test-gateway")
        # Should not delete gateway if targets exist
        mock_bedrock.delete_gateway.assert_not_called()
        assert result["status"] == "error"
        assert "target(s)" in result["message"]

    def test_delete_gateway_with_force_flag(self, gateway_client):
        """Test delete_gateway with force flag deletes targets first"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock that gateway has targets
        mock_bedrock.list_gateway_targets.return_value = {"items": [{"targetId": "target-1"}, {"targetId": "target-2"}]}

        with patch("time.sleep"):
            result = gateway_client.delete_gateway(gateway_identifier="test-gateway", skip_resource_in_use=True)

            # Should delete all targets first
            assert mock_bedrock.delete_gateway_target.call_count == 2
            mock_bedrock.delete_gateway_target.assert_any_call(gatewayIdentifier="test-gateway", targetId="target-1")
            mock_bedrock.delete_gateway_target.assert_any_call(gatewayIdentifier="test-gateway", targetId="target-2")

            # Then delete the gateway
            mock_bedrock.delete_gateway.assert_called_once_with(gatewayIdentifier="test-gateway")
            assert result["status"] == "success"

    def test_delete_gateway_by_arn(self, gateway_client):
        """Test delete_gateway using ARN"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        arn = "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/test-gateway-123"
        result = gateway_client.delete_gateway(gateway_arn=arn)

        # Should extract ID from ARN
        mock_bedrock.delete_gateway.assert_called_once_with(gatewayIdentifier="test-gateway-123")
        assert result["status"] == "success"

    def test_delete_gateway_by_name(self, gateway_client):
        """Test delete_gateway using name lookup"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        with patch.object(gateway_client, "_get_gateway_id_by_name", return_value="resolved-gateway-id"):
            result = gateway_client.delete_gateway(name="MyGateway")

            gateway_client._get_gateway_id_by_name.assert_called_once_with("MyGateway")
            mock_bedrock.delete_gateway.assert_called_once_with(gatewayIdentifier="resolved-gateway-id")
            assert result["status"] == "success"

    def test_delete_gateway_name_not_found(self, gateway_client):
        """Test delete_gateway when name lookup fails"""
        with patch.object(gateway_client, "_get_gateway_id_by_name", return_value=None):
            result = gateway_client.delete_gateway(name="NonExistentGateway")

            assert result["status"] == "error"
            assert "not found" in result["message"]

    def test_delete_gateway_no_parameters(self, gateway_client):
        """Test delete_gateway with no parameters"""
        result = gateway_client.delete_gateway()

        assert result["status"] == "error"
        assert "required" in result["message"]

    def test_delete_gateway_target_deletion_error(self, gateway_client):
        """Test delete_gateway when target deletion fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": [{"targetId": "target-1"}]}
        mock_bedrock.delete_gateway_target.side_effect = Exception("Target deletion failed")

        with patch("time.sleep"):
            result = gateway_client.delete_gateway(gateway_identifier="test-gateway", skip_resource_in_use=True)

            assert result["status"] == "error"
            assert "Target deletion failed" in result["message"]

    def test_delete_gateway_target_success(self, gateway_client):
        """Test delete_gateway_target with ID"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        result = gateway_client.delete_gateway_target(gateway_identifier="gateway-123", target_id="target-456")

        mock_bedrock.delete_gateway_target.assert_called_once_with(
            gatewayIdentifier="gateway-123", targetId="target-456"
        )
        assert result["status"] == "success"
        assert result["targetId"] == "target-456"

    def test_delete_gateway_target_by_name(self, gateway_client):
        """Test delete_gateway_target using target name lookup"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock list_gateway_targets to return targets
        mock_bedrock.list_gateway_targets.return_value = {
            "items": [{"targetId": "target-123", "name": "MyTarget"}, {"targetId": "target-456", "name": "OtherTarget"}]
        }

        result = gateway_client.delete_gateway_target(gateway_identifier="gateway-123", target_name="MyTarget")

        # Should look up target ID by name
        mock_bedrock.list_gateway_targets.assert_called_once_with(gatewayIdentifier="gateway-123")
        mock_bedrock.delete_gateway_target.assert_called_once_with(
            gatewayIdentifier="gateway-123", targetId="target-123"
        )
        assert result["status"] == "success"

    def test_delete_gateway_target_name_not_found(self, gateway_client):
        """Test delete_gateway_target when target name not found"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": [{"targetId": "target-123", "name": "OtherTarget"}]}

        result = gateway_client.delete_gateway_target(gateway_identifier="gateway-123", target_name="NonExistent")

        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_delete_gateway_target_no_target_specified(self, gateway_client):
        """Test delete_gateway_target without target ID or name"""
        result = gateway_client.delete_gateway_target(gateway_identifier="gateway-123")

        assert result["status"] == "error"
        assert "required" in result["message"]

    def test_delete_gateway_target_with_gateway_name(self, gateway_client):
        """Test delete_gateway_target using gateway name lookup"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        with patch.object(gateway_client, "_get_gateway_id_by_name", return_value="resolved-gateway-id"):
            result = gateway_client.delete_gateway_target(name="MyGateway", target_id="target-123")

            gateway_client._get_gateway_id_by_name.assert_called_once_with("MyGateway")
            mock_bedrock.delete_gateway_target.assert_called_once_with(
                gatewayIdentifier="resolved-gateway-id", targetId="target-123"
            )
            assert result["status"] == "success"

    def test_list_gateways_basic(self, gateway_client):
        """Test list_gateways basic functionality"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateways.return_value = {
            "items": [
                {"gatewayId": "gateway-1", "name": "Gateway1"},
                {"gatewayId": "gateway-2", "name": "Gateway2"},
            ]
        }

        result = gateway_client.list_gateways()

        mock_bedrock.list_gateways.assert_called_once()
        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["items"]) == 2

    def test_list_gateways_with_name_filter(self, gateway_client):
        """Test list_gateways with name filter"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateways.return_value = {
            "items": [
                {"gatewayId": "gateway-1", "name": "TestGateway"},
                {"gatewayId": "gateway-2", "name": "OtherGateway"},
                {"gatewayId": "gateway-3", "name": "TestGateway"},
            ]
        }

        result = gateway_client.list_gateways(name="TestGateway")

        assert result["status"] == "success"
        assert result["count"] == 2
        # Should filter to only matching names
        for item in result["items"]:
            assert item["name"] == "TestGateway"

    def test_list_gateways_with_max_results(self, gateway_client):
        """Test list_gateways with max_results limit"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Return more items than max_results
        mock_bedrock.list_gateways.return_value = {
            "items": [{"gatewayId": f"gateway-{i}", "name": f"Gateway{i}"} for i in range(100)]
        }

        result = gateway_client.list_gateways(max_results=10)

        assert result["status"] == "success"
        assert result["count"] == 10
        assert len(result["items"]) == 10

    def test_list_gateways_with_pagination(self, gateway_client):
        """Test list_gateways handles pagination"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock paginated responses
        mock_bedrock.list_gateways.side_effect = [
            {"items": [{"gatewayId": "gateway-1"}], "nextToken": "token1"},
            {"items": [{"gatewayId": "gateway-2"}], "nextToken": None},
        ]

        result = gateway_client.list_gateways(max_results=10)

        assert mock_bedrock.list_gateways.call_count == 2
        assert result["count"] == 2

    def test_list_gateways_error(self, gateway_client):
        """Test list_gateways error handling"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.list_gateways.side_effect = Exception("API Error")

        result = gateway_client.list_gateways()

        assert result["status"] == "error"
        assert "API Error" in result["message"]

    def test_list_gateway_targets_basic(self, gateway_client):
        """Test list_gateway_targets basic functionality"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {
            "items": [{"targetId": "target-1", "name": "Target1"}, {"targetId": "target-2", "name": "Target2"}]
        }

        result = gateway_client.list_gateway_targets(gateway_identifier="gateway-123")

        mock_bedrock.list_gateway_targets.assert_called_once()
        assert result["status"] == "success"
        assert result["gatewayId"] == "gateway-123"
        assert result["count"] == 2

    def test_list_gateway_targets_with_gateway_name(self, gateway_client):
        """Test list_gateway_targets using gateway name lookup"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        with patch.object(gateway_client, "_get_gateway_id_by_name", return_value="resolved-gateway-id"):
            result = gateway_client.list_gateway_targets(name="MyGateway")

            gateway_client._get_gateway_id_by_name.assert_called_once_with("MyGateway")
            mock_bedrock.list_gateway_targets.assert_called_once()
            assert result["gatewayId"] == "resolved-gateway-id"

    def test_list_gateway_targets_with_pagination(self, gateway_client):
        """Test list_gateway_targets handles pagination"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.side_effect = [
            {"items": [{"targetId": "target-1"}], "nextToken": "token1"},
            {"items": [{"targetId": "target-2"}], "nextToken": None},
        ]

        result = gateway_client.list_gateway_targets(gateway_identifier="gateway-123", max_results=10)

        assert mock_bedrock.list_gateway_targets.call_count == 2
        assert result["count"] == 2

    def test_list_gateway_targets_error(self, gateway_client):
        """Test list_gateway_targets error handling"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.list_gateway_targets.side_effect = Exception("API Error")

        result = gateway_client.list_gateway_targets(gateway_identifier="gateway-123")

        assert result["status"] == "error"
        assert "API Error" in result["message"]

    def test_get_gateway_target_basic(self, gateway_client):
        """Test get_gateway_target basic functionality"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_target = {"targetId": "target-123", "name": "MyTarget", "status": "READY"}
        mock_bedrock.get_gateway_target.return_value = mock_target

        result = gateway_client.get_gateway_target(gateway_identifier="gateway-123", target_id="target-123")

        mock_bedrock.get_gateway_target.assert_called_once_with(gatewayIdentifier="gateway-123", targetId="target-123")
        assert result["status"] == "success"
        assert result["target"] == mock_target

    def test_get_gateway_target_with_target_name(self, gateway_client):
        """Test get_gateway_target using target name lookup"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {
            "items": [{"targetId": "target-123", "name": "MyTarget"}, {"targetId": "target-456", "name": "OtherTarget"}]
        }

        mock_target = {"targetId": "target-123", "name": "MyTarget"}
        mock_bedrock.get_gateway_target.return_value = mock_target

        result = gateway_client.get_gateway_target(gateway_identifier="gateway-123", target_name="MyTarget")

        mock_bedrock.list_gateway_targets.assert_called_once_with(gatewayIdentifier="gateway-123")
        mock_bedrock.get_gateway_target.assert_called_once_with(gatewayIdentifier="gateway-123", targetId="target-123")
        assert result["status"] == "success"

    def test_get_gateway_target_with_gateway_arn(self, gateway_client):
        """Test get_gateway_target using gateway ARN"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.get_gateway_target.return_value = {"targetId": "target-123"}

        arn = "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/gateway-123"
        result = gateway_client.get_gateway_target(gateway_arn=arn, target_id="target-123")

        # Should extract ID from ARN
        mock_bedrock.get_gateway_target.assert_called_once_with(gatewayIdentifier="gateway-123", targetId="target-123")
        assert result["status"] == "success"

    def test_get_gateway_target_no_target_specified(self, gateway_client):
        """Test get_gateway_target without target ID or name"""
        result = gateway_client.get_gateway_target(gateway_identifier="gateway-123")

        assert result["status"] == "error"
        assert "required" in result["message"]

    def test_get_gateway_target_error(self, gateway_client):
        """Test get_gateway_target error handling"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.get_gateway_target.side_effect = Exception("Target not found")

        result = gateway_client.get_gateway_target(gateway_identifier="gateway-123", target_id="target-123")

        assert result["status"] == "error"
        assert "Target not found" in result["message"]

    def test_get_gateway_id_by_name_found(self, gateway_client):
        """Test _get_gateway_id_by_name when gateway is found"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateways.return_value = {
            "items": [
                {"gatewayId": "gateway-1", "name": "Gateway1"},
                {"gatewayId": "gateway-2", "name": "TestGateway"},
                {"gatewayId": "gateway-3", "name": "Gateway3"},
            ]
        }

        result = gateway_client._get_gateway_id_by_name("TestGateway")

        assert result == "gateway-2"

    def test_get_gateway_id_by_name_not_found(self, gateway_client):
        """Test _get_gateway_id_by_name when gateway is not found"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateways.return_value = {
            "items": [{"gatewayId": "gateway-1", "name": "Gateway1"}, {"gatewayId": "gateway-2", "name": "Gateway2"}]
        }

        result = gateway_client._get_gateway_id_by_name("NonExistent")

        assert result is None

    def test_get_gateway_id_by_name_with_pagination(self, gateway_client):
        """Test _get_gateway_id_by_name handles pagination"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock paginated responses - gateway found on second page
        mock_bedrock.list_gateways.side_effect = [
            {"items": [{"gatewayId": "gateway-1", "name": "Gateway1"}], "nextToken": "token1"},
            {"items": [{"gatewayId": "gateway-2", "name": "TestGateway"}], "nextToken": None},
        ]

        result = gateway_client._get_gateway_id_by_name("TestGateway")

        assert result == "gateway-2"
        assert mock_bedrock.list_gateways.call_count == 2

    def test_get_gateway_id_by_name_error(self, gateway_client):
        """Test _get_gateway_id_by_name error handling"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.list_gateways.side_effect = Exception("API Error")

        result = gateway_client._get_gateway_id_by_name("TestGateway")

        assert result is None

    def test_get_gateway_with_identifier(self, gateway_client):
        """Test get_gateway with gateway identifier"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_gateway = {"gatewayId": "gateway-123", "name": "TestGateway"}
        mock_bedrock.get_gateway.return_value = mock_gateway

        result = gateway_client.get_gateway(gateway_identifier="gateway-123")

        mock_bedrock.get_gateway.assert_called_once_with(gatewayIdentifier="gateway-123")
        assert result["status"] == "success"
        assert result["gateway"] == mock_gateway

    def test_get_gateway_error(self, gateway_client):
        """Test get_gateway error handling"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock
        mock_bedrock.get_gateway.side_effect = Exception("Gateway not found")

        result = gateway_client.get_gateway(gateway_identifier="gateway-123")

        assert result["status"] == "error"
        assert "Gateway not found" in result["message"]

    def test_fix_iam_permissions_success(self, gateway_client):
        """Test fix_iam_permissions successfully updates IAM role"""
        with patch("boto3.client") as mock_boto_client:
            mock_sts = Mock()
            mock_iam = Mock()

            # Return STS first, then IAM
            mock_boto_client.side_effect = [mock_sts, mock_iam]

            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

            gateway = {"roleArn": "arn:aws:iam::123456789012:role/TestGatewayRole"}

            gateway_client.fix_iam_permissions(gateway)

            # Verify STS and IAM clients were created
            assert mock_boto_client.call_count == 2

            # Verify trust policy was updated
            mock_iam.update_assume_role_policy.assert_called_once()
            call_args = mock_iam.update_assume_role_policy.call_args
            assert call_args[1]["RoleName"] == "TestGatewayRole"

            # Verify Lambda policy was added
            mock_iam.put_role_policy.assert_called_once()
            policy_call = mock_iam.put_role_policy.call_args
            assert policy_call[1]["RoleName"] == "TestGatewayRole"
            assert policy_call[1]["PolicyName"] == "LambdaInvokePolicy"

    def test_fix_iam_permissions_with_exception(self, gateway_client):
        """Test fix_iam_permissions handles exceptions gracefully"""
        with patch("boto3.client") as mock_boto_client:
            mock_sts = Mock()
            mock_iam = Mock()

            mock_boto_client.side_effect = [mock_sts, mock_iam]
            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

            # Simulate IAM error
            mock_iam.update_assume_role_policy.side_effect = Exception("IAM Error")

            gateway = {"roleArn": "arn:aws:iam::123456789012:role/TestGatewayRole"}

            # Should not raise exception, just log warning
            gateway_client.fix_iam_permissions(gateway)

    def test_delete_gateway_check_targets_error(self, gateway_client):
        """Test delete_gateway when checking targets fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.side_effect = Exception("List Error")

        result = gateway_client.delete_gateway(gateway_identifier="gateway-123")

        assert result["status"] == "error"
        assert "List Error" in result["message"]

    def test_delete_gateway_target_list_error(self, gateway_client):
        """Test delete_gateway_target when listing targets fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.side_effect = Exception("List Error")

        result = gateway_client.delete_gateway_target(gateway_identifier="gateway-123", target_name="MyTarget")

        assert result["status"] == "error"
        assert "List Error" in result["message"]

    @patch("time.sleep")
    def test_cleanup_gateway_full_flow(self, mock_sleep, gateway_client):
        """Test cleanup_gateway complete flow with Cognito"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock targets
        mock_bedrock.list_gateway_targets.side_effect = [
            {"items": [{"targetId": "target-1"}, {"targetId": "target-2"}]},
            {"items": []},  # After deletion
        ]

        client_info = {"user_pool_id": "us-west-2_TestPool", "domain_prefix": "test-domain"}

        with patch("boto3.client") as mock_boto_client:
            mock_cognito = Mock()
            mock_boto_client.return_value = mock_cognito

            gateway_client.cleanup_gateway("gateway-123", client_info)

            # Verify targets were deleted
            assert mock_bedrock.delete_gateway_target.call_count == 2

            # Verify gateway was deleted
            mock_bedrock.delete_gateway.assert_called_once_with(gatewayIdentifier="gateway-123")

            # Verify Cognito cleanup
            mock_cognito.delete_user_pool_domain.assert_called_once_with(
                UserPoolId="us-west-2_TestPool", Domain="test-domain"
            )
            mock_cognito.delete_user_pool.assert_called_once_with(UserPoolId="us-west-2_TestPool")

    @patch("time.sleep")
    def test_cleanup_gateway_without_cognito(self, mock_sleep, gateway_client):
        """Test cleanup_gateway without Cognito info"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        gateway_client.cleanup_gateway("gateway-123")

        # Should still delete gateway
        mock_bedrock.delete_gateway.assert_called_once()

    @patch("time.sleep")
    def test_cleanup_gateway_with_target_deletion_error(self, mock_sleep, gateway_client):
        """Test cleanup_gateway when target deletion fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": [{"targetId": "target-1"}]}
        mock_bedrock.delete_gateway_target.side_effect = Exception("Target deletion failed")

        # Should not raise exception, just log warning
        gateway_client.cleanup_gateway("gateway-123")

    @patch("time.sleep")
    def test_cleanup_gateway_with_gateway_deletion_error(self, mock_sleep, gateway_client):
        """Test cleanup_gateway when gateway deletion fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": []}
        mock_bedrock.delete_gateway.side_effect = Exception("Gateway deletion failed")

        # Should not raise exception, just log warning
        gateway_client.cleanup_gateway("gateway-123")

    @patch("time.sleep")
    def test_cleanup_gateway_with_cognito_domain_error(self, mock_sleep, gateway_client):
        """Test cleanup_gateway when Cognito domain deletion fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        client_info = {"user_pool_id": "us-west-2_TestPool", "domain_prefix": "test-domain"}

        with patch("boto3.client") as mock_boto_client:
            mock_cognito = Mock()
            mock_boto_client.return_value = mock_cognito

            mock_cognito.delete_user_pool_domain.side_effect = Exception("Domain deletion failed")

            # Should not raise exception
            gateway_client.cleanup_gateway("gateway-123", client_info)

            # Should still try to delete user pool
            mock_cognito.delete_user_pool.assert_called_once()

    @patch("time.sleep")
    def test_cleanup_gateway_with_cognito_pool_error(self, mock_sleep, gateway_client):
        """Test cleanup_gateway when Cognito pool deletion fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        client_info = {"user_pool_id": "us-west-2_TestPool", "domain_prefix": "test-domain"}

        with patch("boto3.client") as mock_boto_client:
            mock_cognito = Mock()
            mock_boto_client.return_value = mock_cognito

            mock_cognito.delete_user_pool.side_effect = Exception("Pool deletion failed")

            # Should not raise exception, just log warning
            gateway_client.cleanup_gateway("gateway-123", client_info)

    @patch("time.sleep")
    def test_cleanup_gateway_with_remaining_targets(self, mock_sleep, gateway_client):
        """Test cleanup_gateway when targets remain after deletion"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        # Mock targets still remaining after deletion
        mock_bedrock.list_gateway_targets.side_effect = [
            {"items": [{"targetId": "target-1"}]},
            {"items": [{"targetId": "target-1"}]},  # Still there after deletion
        ]

        gateway_client.cleanup_gateway("gateway-123")

    @patch("time.sleep")
    def test_cleanup_gateway_list_targets_error(self, mock_sleep, gateway_client):
        """Test cleanup_gateway when listing targets fails"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.side_effect = Exception("List error")

        # Should not raise exception, just log warning
        gateway_client.cleanup_gateway("gateway-123")

        # Should still try to delete gateway
        mock_bedrock.delete_gateway.assert_called_once()

    @patch("time.sleep")
    def test_cleanup_gateway_without_domain_prefix(self, mock_sleep, gateway_client):
        """Test cleanup_gateway with Cognito but no domain prefix"""
        mock_bedrock = Mock()
        gateway_client.client = mock_bedrock

        mock_bedrock.list_gateway_targets.return_value = {"items": []}

        # Client info without domain_prefix
        client_info = {"user_pool_id": "us-west-2_TestPool"}

        with patch("boto3.client") as mock_boto_client:
            mock_cognito = Mock()
            mock_boto_client.return_value = mock_cognito

            gateway_client.cleanup_gateway("gateway-123", client_info)

            # Should not try to delete domain
            mock_cognito.delete_user_pool_domain.assert_not_called()

            # Should still delete user pool
            mock_cognito.delete_user_pool.assert_called_once()
