"""Tests for Bedrock AgentCore import agent functionality."""

import json
import os
from unittest.mock import Mock, patch

from bedrock_agentcore_starter_toolkit.services.import_agent.scripts import (
    bedrock_to_langchain,
    bedrock_to_strands,
)


class TestImportAgent:
    """Test Import Agent functionality."""

    def test_bedrock_to_strands(self, mock_boto3_clients):
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

    def test_bedrock_to_langchain(self, mock_boto3_clients):
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
        mock_boto3_clients,
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
                return mock_boto3_clients["sts"]
            elif service_name == "iam":
                return mock_boto3_clients["iam"]
            elif service_name == "lambda":
                return mock_boto3_clients["lambda"]
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
        mock_boto3_clients,
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
                return mock_boto3_clients["sts"]
            elif service_name == "iam":
                return mock_boto3_clients["iam"]
            elif service_name == "lambda":
                return mock_boto3_clients["lambda"]
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

    def test_bedrock_to_langchain_with_function_schema_no_gateway(self, mock_boto3_clients):
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

    def test_bedrock_to_strands_with_function_schema_no_gateway(self, mock_boto3_clients):
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

    def test_bedrock_to_langchain_with_no_schema_action_group(self, mock_boto3_clients):
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
