"""
Tests for setup_gateway.py using mocks to avoid AWS calls.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, call

import pytest

from bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway import QuickGateway


def test_quickgateway_init():
    """Test that QuickGateway can be initialized."""
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
        gateway = QuickGateway(region="us-east-1")
        assert gateway.region == "us-east-1"
        assert gateway.config_file.name == "gateway_config.json"
        assert gateway.gateway is None
        assert isinstance(gateway.config, dict)


@patch("time.sleep")  # Skip sleep calls
@patch("json.dump")   # Mock writing to config file
def test_create_gateway(mock_json_dump, mock_sleep):
    """Test creating a gateway."""
    mock_client = Mock()
    mock_client.create_oauth_authorizer_with_cognito.return_value = {
        "authorizer_config": {"customJWTAuthorizer": {"allowedClients": ["test-client"]}},
        "client_info": {
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "user_pool_id": "us-east-1_testpool",
            "token_endpoint": "https://test-endpoint/oauth2/token",
            "scope": "test-scope",
            "domain_prefix": "test-domain"
        }
    }
    mock_client.create_mcp_gateway.return_value = {
        "gatewayId": "test-gateway-id",
        "gatewayUrl": "https://test-gateway-url.com/mcp",
        "roleArn": "arn:aws:iam::123456789012:role/TestRole",
    }
    mock_client.get_access_token_for_cognito.return_value = "test-access-token"
    
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient", 
              return_value=mock_client):
        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.QuickGateway._fix_iam_permissions"):
            gateway = QuickGateway(region="us-east-1")
            result_url = gateway.create()
            
            # Verify calls
            mock_client.create_oauth_authorizer_with_cognito.assert_called_once()
            mock_client.create_mcp_gateway.assert_called_once()
            mock_client.create_mcp_gateway_target.assert_called_once()
            mock_client.get_access_token_for_cognito.assert_called_once()
            mock_json_dump.assert_called_once()
            
            # Verify result
            assert result_url == "https://test-gateway-url.com/mcp"
            assert gateway.gateway["gatewayUrl"] == "https://test-gateway-url.com/mcp"
            assert "gateway_url" in gateway.config
            assert gateway.config["access_token"] == "test-access-token"


@patch("pathlib.Path.exists")
@patch("pathlib.Path.unlink")
def test_cleanup_no_config_file(mock_unlink, mock_exists):
    """Test cleanup when no config file exists."""
    mock_exists.return_value = False
    
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
        gateway = QuickGateway(region="us-east-1")
        
        # Should return early without error
        gateway.cleanup()
        
        # No file operations should happen
        mock_unlink.assert_not_called()


@patch("pathlib.Path.exists")
@patch("pathlib.Path.unlink")
def test_cleanup_success(mock_unlink, mock_exists):
    """Test successful cleanup."""
    mock_exists.return_value = True
    
    # Setup mock file handling
    mock_file_data = '{"gateway_id": "test-id", "region": "us-east-1", "client_info": {"user_pool_id": "test-pool", "domain_prefix": "test-domain"}}'
    
    mock_boto3 = Mock()
    mock_gateway_client = Mock()
    mock_cognito_client = Mock()
    
    # Configure list_gateway_targets to return targets first, then empty list
    mock_gateway_client.list_gateway_targets.side_effect = [
        {"items": [{"targetId": "test-target-id", "name": "TestTarget", "status": "READY"}]},
        {"items": []}  # Empty list for verification
    ]
    
    # Configure boto3.client to return our mocks
    def get_mock_client(service_name, **kwargs):
        if service_name == "bedrock-agentcore-control":
            return mock_gateway_client
        elif service_name == "cognito-idp":
            return mock_cognito_client
        return Mock()
    
    mock_boto3.client.side_effect = get_mock_client
    
    with patch("builtins.open", mock_open(read_data=mock_file_data)):
        with patch("json.load", return_value=json.loads(mock_file_data)):
            with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.boto3", mock_boto3):
                with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
                    gateway = QuickGateway(region="us-east-1")
                    gateway.cleanup()
                    
                    # Verify file operations
                    mock_unlink.assert_called_once()
                    
                    # Verify AWS calls - Check call count instead of using assert_called_once
                    assert mock_gateway_client.list_gateway_targets.call_count == 2
                    mock_gateway_client.list_gateway_targets.assert_has_calls([
                        call(gatewayIdentifier="test-id"),
                        call(gatewayIdentifier="test-id")
                    ])
                    mock_gateway_client.delete_gateway_target.assert_called_once()
                    mock_gateway_client.delete_gateway.assert_called_once()
                    mock_cognito_client.delete_user_pool_domain.assert_called_once()
                    mock_cognito_client.delete_user_pool.assert_called_once()


def test_fix_iam_permissions():
    """Test _fix_iam_permissions method."""
    mock_boto3 = Mock()
    mock_sts = Mock()
    mock_iam = Mock()
    
    # Configure mock
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
    
    # Configure boto3.client to return our mocks
    def get_mock_client(service_name, **kwargs):
        if service_name == "sts":
            return mock_sts
        elif service_name == "iam":
            return mock_iam
        return Mock()
    
    mock_boto3.client.side_effect = get_mock_client
    
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.boto3", mock_boto3):
        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
            gateway = QuickGateway(region="us-east-1")
            gateway.gateway = {"roleArn": "arn:aws:iam::123456789012:role/TestRole"}
            
            gateway._fix_iam_permissions()
            
            # Verify AWS calls
            mock_sts.get_caller_identity.assert_called_once()
            mock_iam.update_assume_role_policy.assert_called_once()
            mock_iam.put_role_policy.assert_called_once()


def test_fix_iam_permissions_with_none_gateway():
    """Test _fix_iam_permissions with None gateway."""
    mock_boto3 = Mock()
    
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.boto3", mock_boto3):
        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
            gateway = QuickGateway(region="us-east-1")
            # gateway.gateway is None by default
            
            # Call the method - should handle None gateway
            gateway._fix_iam_permissions()
            
            # Should exit early without error
            mock_boto3.client.assert_not_called()


def test_fix_iam_permissions_with_no_role_arn():
    """Test _fix_iam_permissions with no roleArn in gateway."""
    mock_boto3 = Mock()
    
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.boto3", mock_boto3):
        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
            gateway = QuickGateway(region="us-east-1")
            gateway.gateway = {"gatewayId": "test-id"}  # No roleArn
            
            # Should handle missing roleArn
            gateway._fix_iam_permissions()
            
            # Should exit early without error
            mock_boto3.client.assert_not_called()


def test_fix_iam_permissions_exception_handling():
    """Test exception handling in _fix_iam_permissions."""
    mock_boto3 = Mock()
    mock_sts = Mock()
    mock_iam = Mock()
    
    # Configure mock
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
    mock_iam.update_assume_role_policy.side_effect = Exception("Test exception")
    
    # Configure boto3.client to return our mocks
    def get_mock_client(service_name, **kwargs):
        if service_name == "sts":
            return mock_sts
        elif service_name == "iam":
            return mock_iam
        return Mock()
    
    mock_boto3.client.side_effect = get_mock_client
    
    with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.boto3", mock_boto3):
        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.setup_gateway.GatewayClient"):
            with patch("builtins.print") as mock_print:
                gateway = QuickGateway(region="us-east-1")
                gateway.gateway = {"roleArn": "arn:aws:iam::123456789012:role/TestRole"}
                
                # Should handle exception
                gateway._fix_iam_permissions()
                
                # Verify AWS calls
                mock_sts.get_caller_identity.assert_called_once()
                mock_iam.update_assume_role_policy.assert_called_once()
                mock_print.assert_called_once()