"""Tests for get_agent_card operation."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.get_agent_card import get_agent_card
from bedrock_agentcore_starter_toolkit.operations.runtime.models import GetAgentCardResult


class TestGetAgentCard:
    """Test get_agent_card functionality."""


    def test_get_agent_card_with_oauth(self, tmp_path):
        """Test retrieving agent card using OAuth bearer token."""
        config_content = """
default_agent: test_agent
agents:
  test_agent:
    name: test_agent
    entrypoint: test_agent.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      region: us-west-2
      account: '123456789012'
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: test-repo
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: A2A
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: test-agent-id
      agent_arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent
      agent_session_id: null
    codebuild:
      project_name: null
      execution_role: null
      source_bucket: null
    memory:
      mode: STM_ONLY
      memory_id: null
      memory_arn: null
      memory_name: null
      event_expiry_days: 30
      first_invoke_memory_check_done: false
    authorizer_configuration:
      customJWTAuthorizer:
        discoveryUrl: https://example.com/.well-known/openid-configuration
        allowedClients:
          - test-client-id
    request_header_configuration: null
    oauth_configuration: null
"""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text(config_content)

        mock_agent_card = {"name": "OAuth Agent", "url": "https://example.com/oauth-agent"}

        # Patch the dynamically imported HttpBedrockAgentCoreClient
        with patch(
            "bedrock_agentcore_starter_toolkit.services.runtime.HttpBedrockAgentCoreClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.get_agent_card.return_value = mock_agent_card
            mock_client_class.return_value = mock_client

            result = get_agent_card(config_path=config_path, agent_name="test_agent", bearer_token="test-token")

            assert isinstance(result, GetAgentCardResult)
            assert result.agent_name == "test_agent"
            assert result.agent_card == mock_agent_card

    def test_get_agent_card_agent_not_deployed(self, tmp_path):
        """Test error when agent is not deployed."""
        config_content = """
default_agent: test_agent
agents:
  test_agent:
    name: test_agent
    entrypoint: test_agent.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      region: us-west-2
      account: '123456789012'
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: test-repo
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: A2A
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: null
      agent_arn: null
      agent_session_id: null
    codebuild:
      project_name: null
      execution_role: null
      source_bucket: null
    memory:
      mode: STM_ONLY
      memory_id: null
      memory_arn: null
      memory_name: null
      event_expiry_days: 30
      first_invoke_memory_check_done: false
    authorizer_configuration: null
    request_header_configuration: null
    oauth_configuration: null
"""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            get_agent_card(config_path=config_path, agent_name="test_agent")

        assert "not deployed" in str(exc_info.value)

    def test_get_agent_card_config_not_found(self, tmp_path):
        """Test error when configuration file doesn't exist."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        with pytest.raises(FileNotFoundError):
            get_agent_card(config_path=config_path, agent_name="test_agent")

    def test_get_agent_card_agent_not_in_config(self, tmp_path):
        """Test error when specified agent doesn't exist in config."""
        config_content = """
default_agent: test_agent
agents:
  test_agent:
    name: test_agent
    entrypoint: test_agent.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      region: us-west-2
      account: '123456789012'
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: test-repo
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: A2A
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: test-agent-id
      agent_arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent
      agent_session_id: null
    codebuild:
      project_name: null
      execution_role: null
      source_bucket: null
    memory:
      mode: STM_ONLY
      memory_id: null
      memory_arn: null
      memory_name: null
      event_expiry_days: 30
      first_invoke_memory_check_done: false
    authorizer_configuration: null
    request_header_configuration: null
    oauth_configuration: null
"""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            get_agent_card(config_path=config_path, agent_name="nonexistent_agent")

        assert "not found" in str(exc_info.value)

    def test_get_agent_card_missing_region(self, tmp_path):
        """Test error when region is missing from configuration."""
        config_content = """
default_agent: test_agent
agents:
  test_agent:
    name: test_agent
    entrypoint: test_agent.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      region: null
      account: '123456789012'
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: test-repo
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC
      protocol_configuration:
        server_protocol: A2A
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: test-agent-id
      agent_arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent
      agent_session_id: null
    codebuild:
      project_name: null
      execution_role: null
      source_bucket: null
    memory:
      mode: STM_ONLY
      memory_id: null
      memory_arn: null
      memory_name: null
      event_expiry_days: 30
      first_invoke_memory_check_done: false
    authorizer_configuration: null
    request_header_configuration: null
    oauth_configuration: null
"""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            get_agent_card(config_path=config_path, agent_name="test_agent")

        assert "Region not found" in str(exc_info.value)