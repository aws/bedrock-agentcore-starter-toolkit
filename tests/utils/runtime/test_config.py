"""Tests for BedrockAgentCore configuration management."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from bedrock_agentcore_starter_toolkit.operations.runtime.exceptions import RuntimeToolkitException
from bedrock_agentcore_starter_toolkit.utils.runtime.config import (
    get_agentcore_directory,
    is_project_config_format,
    load_config,
    merge_agent_config,
    save_config,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
    ProtocolConfiguration,
)


class TestProjectConfiguration:
    """Test project configuration functionality."""

    def test_load_project_config_single_agent(self):
        """Test loading project config with single agent."""

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_single.yaml"
        project_config = load_config(fixture_path)

        assert project_config.default_agent == "test-agent"
        assert len(project_config.agents) == 1
        assert "test-agent" in project_config.agents

        agent_config = project_config.agents["test-agent"]
        assert agent_config.name == "test-agent"
        assert agent_config.entrypoint == "test.py"
        assert agent_config.aws.region == "us-west-2"
        assert agent_config.aws.account == "123456789012"

    def test_load_project_config_multiple_agents(self):
        """Test loading project config with multiple agents."""

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_multiple.yaml"
        project_config = load_config(fixture_path)

        assert project_config.default_agent == "chat-agent"
        assert len(project_config.agents) == 2
        assert "chat-agent" in project_config.agents
        assert "code-assistant" in project_config.agents

        # Test chat agent
        chat_agent = project_config.agents["chat-agent"]
        assert chat_agent.name == "chat-agent"
        assert chat_agent.aws.region == "us-east-1"
        assert chat_agent.bedrock_agentcore.agent_id == "CHAT123"

        # Test code assistant
        code_agent = project_config.agents["code-assistant"]
        assert code_agent.name == "code-assistant"
        assert code_agent.aws.region == "us-west-2"
        assert code_agent.bedrock_agentcore.agent_id == "CODE456"

    def test_get_agent_config_by_name(self):
        """Test getting specific agent config."""

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_multiple.yaml"
        project_config = load_config(fixture_path)

        # Get specific agent
        code_config = project_config.get_agent_config("code-assistant")
        assert code_config.name == "code-assistant"
        assert code_config.entrypoint == "code.py"
        assert code_config.aws.region == "us-west-2"

    def test_get_default_agent_config(self):
        """Test getting default agent config."""

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_multiple.yaml"
        project_config = load_config(fixture_path)

        # Get default agent (no name specified)
        default_config = project_config.get_agent_config()
        assert default_config.name == "chat-agent"
        assert default_config.entrypoint == "chat.py"
        assert default_config.aws.region == "us-east-1"

    def test_get_agent_config_no_target_name_single_agent(self):
        """Test get_agent_config when no agent name and no default, but exactly 1 agent configured."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import BedrockAgentCoreConfigSchema

        # Create config with single agent and no default
        agent_config = BedrockAgentCoreAgentSchema(
            name="only-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(
            default_agent=None,  # No default set
            agents={"only-agent": agent_config},
        )

        # Should auto-select the single agent and set it as default
        result = project_config.get_agent_config()

        assert result.name == "only-agent"
        assert result.entrypoint == "test.py"
        # Should have auto-set as default
        assert project_config.default_agent == "only-agent"

    def test_get_agent_config_error_handling(self):
        """Test error handling for agent config retrieval."""

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_single.yaml"
        project_config = load_config(fixture_path)

        # Test non-existent agent
        try:
            project_config.get_agent_config("non-existent")
            raise AssertionError("Should raise ValueError")
        except ValueError as e:
            assert "Agent 'non-existent' not found" in str(e)

    def test_project_config_save_load_cycle(self, tmp_path):
        """Test saving and loading project configuration."""

        # Load original config
        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_multiple.yaml"
        original_config = load_config(fixture_path)

        # Save to temp path
        temp_config_path = tmp_path / "test_project.yaml"
        save_config(original_config, temp_config_path)

        # Load saved config
        loaded_config = load_config(temp_config_path)

        # Verify configs match
        assert loaded_config.default_agent == original_config.default_agent
        assert len(loaded_config.agents) == len(original_config.agents)
        assert loaded_config.agents["chat-agent"].name == "chat-agent"
        assert loaded_config.agents["code-assistant"].name == "code-assistant"

    def test_is_project_config_format_detection(self):
        """Test project config format detection."""

        # Test project format files
        single_fixture = Path(__file__).parent.parent.parent / "fixtures" / "project_config_single.yaml"
        multiple_fixture = Path(__file__).parent.parent.parent / "fixtures" / "project_config_multiple.yaml"

        assert is_project_config_format(single_fixture)
        assert is_project_config_format(multiple_fixture)

        # Test non-existent file
        nonexistent_path = Path(__file__).parent / "nonexistent.yaml"
        assert not is_project_config_format(nonexistent_path)


class TestMergeAgentConfig:
    """Test merge_agent_config functionality, especially default agent behavior."""

    def _create_test_agent_config(self, name: str, entrypoint: str = "test.py") -> BedrockAgentCoreAgentSchema:
        """Helper to create a test agent configuration."""
        return BedrockAgentCoreAgentSchema(
            name=name,
            entrypoint=entrypoint,
            platform="linux/arm64",
            container_runtime="finch",
            aws=AWSConfig(
                execution_role=f"arn:aws:iam::123456789012:role/{name}Role",
                account="123456789012",
                region="us-west-2",
                ecr_repository=f"123456789012.dkr.ecr.us-west-2.amazonaws.com/{name}",
                ecr_auto_create=False,
                network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
                protocol_configuration=ProtocolConfiguration(server_protocol="HTTP"),
                observability=ObservabilityConfig(enabled=True),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

    def test_merge_agent_config_first_agent_sets_default(self, tmp_path, caplog):
        """Test that first agent is set as default with proper logging."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "first-agent"
        agent_config = self._create_test_agent_config(agent_name)

        with caplog.at_level(logging.INFO):
            result_config = merge_agent_config(config_path, agent_name, agent_config)

        # Verify default agent is set
        assert result_config.default_agent == agent_name
        assert agent_name in result_config.agents
        assert result_config.agents[agent_name].name == agent_name

        # Verify logging
        assert f"Setting '{agent_name}' as default agent" in caplog.text

    def test_merge_agent_config_changes_default_agent(self, tmp_path, caplog):
        """Test that configuring a new agent changes the default with proper logging."""
        config_path = tmp_path / "test_config.yaml"

        # First, configure initial agent
        first_agent = "first-agent"
        first_config = self._create_test_agent_config(first_agent)
        result1 = merge_agent_config(config_path, first_agent, first_config)
        save_config(result1, config_path)  # Save after first agent

        # Now configure second agent - this should become the new default
        second_agent = "second-agent"
        second_config = self._create_test_agent_config(second_agent, "second.py")

        with caplog.at_level(logging.INFO):
            result_config = merge_agent_config(config_path, second_agent, second_config)

        # Verify default agent changed
        assert result_config.default_agent == second_agent
        assert len(result_config.agents) == 2
        assert first_agent in result_config.agents
        assert second_agent in result_config.agents

        # Verify logging shows the change
        assert f"Changing default agent from '{first_agent}' to '{second_agent}'" in caplog.text

    def test_merge_agent_config_keeps_same_default(self, tmp_path, caplog):
        """Test that reconfiguring the same agent keeps it as default with proper logging."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "test-agent"

        # First configuration
        first_config = self._create_test_agent_config(agent_name)
        result1 = merge_agent_config(config_path, agent_name, first_config)
        save_config(result1, config_path)  # Save after first config

        # Reconfigure the same agent (e.g., updating settings)
        updated_config = self._create_test_agent_config(agent_name)
        updated_config.aws.region = "us-east-1"  # Change a setting

        with caplog.at_level(logging.INFO):
            result_config = merge_agent_config(config_path, agent_name, updated_config)

        # Verify agent remains default
        assert result_config.default_agent == agent_name
        assert len(result_config.agents) == 1
        assert result_config.agents[agent_name].aws.region == "us-east-1"

        # Verify logging shows keeping the same agent
        assert f"Keeping '{agent_name}' as default agent" in caplog.text

    def test_merge_agent_config_preserves_deployment_info(self, tmp_path):
        """Test that existing deployment info is preserved when updating agent config."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "test-agent"

        # First configuration with deployment info
        first_config = self._create_test_agent_config(agent_name)
        first_config.bedrock_agentcore.agent_id = "test-agent-123"
        first_config.bedrock_agentcore.agent_arn = (
            "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent-123"
        )
        result1 = merge_agent_config(config_path, agent_name, first_config)
        save_config(result1, config_path)  # Save after first config

        # Update configuration (without deployment info)
        updated_config = self._create_test_agent_config(agent_name)
        updated_config.aws.region = "us-east-1"

        result_config = merge_agent_config(config_path, agent_name, updated_config)

        # Verify deployment info is preserved
        assert result_config.agents[agent_name].bedrock_agentcore.agent_id == "test-agent-123"
        assert (
            result_config.agents[agent_name].bedrock_agentcore.agent_arn
            == "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent-123"
        )
        # Verify update was applied
        assert result_config.agents[agent_name].aws.region == "us-east-1"

    def test_merge_agent_config_multiple_agents_scenario(self, tmp_path, caplog):
        """Test complete scenario with multiple agents and default changes."""
        config_path = tmp_path / "test_config.yaml"

        # Configure first agent
        agent1 = self._create_test_agent_config("agent1", "agent1.py")
        config1 = merge_agent_config(config_path, "agent1", agent1)
        save_config(config1, config_path)  # Save after first agent
        assert config1.default_agent == "agent1"

        # Configure second agent - should become new default
        agent2 = self._create_test_agent_config("agent2", "agent2.py")
        with caplog.at_level(logging.INFO):
            config2 = merge_agent_config(config_path, "agent2", agent2)
        save_config(config2, config_path)  # Save after second agent

        assert config2.default_agent == "agent2"
        assert "Changing default agent from 'agent1' to 'agent2'" in caplog.text
        caplog.clear()

        # Configure third agent - should become new default
        agent3 = self._create_test_agent_config("agent3", "agent3.py")
        with caplog.at_level(logging.INFO):
            config3 = merge_agent_config(config_path, "agent3", agent3)
        save_config(config3, config_path)  # Save after third agent

        assert config3.default_agent == "agent3"
        assert "Changing default agent from 'agent2' to 'agent3'" in caplog.text
        caplog.clear()

        # Reconfigure agent1 - should become default again
        with caplog.at_level(logging.INFO):
            config4 = merge_agent_config(config_path, "agent1", agent1)

        assert config4.default_agent == "agent1"
        assert "Changing default agent from 'agent3' to 'agent1'" in caplog.text

        # Verify all agents still exist
        assert len(config4.agents) == 3
        assert "agent1" in config4.agents
        assert "agent2" in config4.agents
        assert "agent3" in config4.agents

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.log")
    def test_merge_agent_config_logging_calls(self, mock_log, tmp_path):
        """Test that logging calls are made correctly."""
        config_path = tmp_path / "test_config.yaml"

        # Test first agent
        agent1 = self._create_test_agent_config("agent1")
        result1 = merge_agent_config(config_path, "agent1", agent1)
        save_config(result1, config_path)  # Save after first agent
        mock_log.info.assert_called_with("Setting '%s' as default agent", "agent1")

        # Test changing agent
        mock_log.reset_mock()
        agent2 = self._create_test_agent_config("agent2")
        result2 = merge_agent_config(config_path, "agent2", agent2)
        save_config(result2, config_path)  # Save after second agent
        mock_log.info.assert_called_with("Changing default agent from '%s' to '%s'", "agent1", "agent2")

        # Test keeping same agent
        mock_log.reset_mock()
        merge_agent_config(config_path, "agent2", agent2)
        mock_log.info.assert_called_with("Keeping '%s' as default agent", "agent2")


class TestRequestHeaderConfigurationSchema:
    """Test request_header_configuration schema validation and handling."""

    def _create_base_agent_config(self, name: str = "test-agent") -> BedrockAgentCoreAgentSchema:
        """Helper to create a base agent configuration for testing."""
        return BedrockAgentCoreAgentSchema(
            name=name,
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

    def test_agent_schema_request_header_configuration_none_default(self):
        """Test that request_header_configuration defaults to None."""
        agent_config = self._create_base_agent_config()
        assert agent_config.request_header_configuration is None

    def test_agent_schema_request_header_configuration_valid_dict(self):
        """Test that valid request_header_configuration dict is accepted."""
        agent_config = self._create_base_agent_config()
        agent_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header"]}

        assert agent_config.request_header_configuration is not None
        assert "requestHeaderAllowlist" in agent_config.request_header_configuration
        assert agent_config.request_header_configuration["requestHeaderAllowlist"] == [
            "Authorization",
            "X-Custom-Header",
        ]

    def test_agent_schema_request_header_configuration_empty_dict(self):
        """Test that empty dict is valid for request_header_configuration."""
        agent_config = self._create_base_agent_config()
        agent_config.request_header_configuration = {}

        assert agent_config.request_header_configuration == {}

    def test_agent_schema_request_header_configuration_complex_structure(self):
        """Test that complex nested structure is accepted."""
        agent_config = self._create_base_agent_config()
        agent_config.request_header_configuration = {
            "requestHeaderAllowlist": [
                "Authorization",
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*",
                "Content-Type",
                "User-Agent",
            ],
            "additionalConfig": {"maxHeaderSize": 8192, "caseSensitive": False},
        }

        assert len(agent_config.request_header_configuration["requestHeaderAllowlist"]) == 4
        assert "Authorization" in agent_config.request_header_configuration["requestHeaderAllowlist"]
        assert agent_config.request_header_configuration["additionalConfig"]["maxHeaderSize"] == 8192

    def test_project_config_with_request_headers_save_load_cycle(self, tmp_path):
        """Test saving and loading project config with request header configuration."""
        # Create config with request header configuration
        agent_config = self._create_base_agent_config()
        agent_config.request_header_configuration = {
            "requestHeaderAllowlist": ["Authorization", "X-Custom-Header", "X-Another-Header"]
        }

        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        # Save to temp file
        config_path = tmp_path / "test_request_headers.yaml"
        save_config(project_config, config_path)

        # Load config back
        loaded_config = load_config(config_path)

        # Verify request header configuration is preserved
        loaded_agent = loaded_config.get_agent_config("test-agent")
        assert loaded_agent.request_header_configuration is not None
        assert "requestHeaderAllowlist" in loaded_agent.request_header_configuration
        assert loaded_agent.request_header_configuration["requestHeaderAllowlist"] == [
            "Authorization",
            "X-Custom-Header",
            "X-Another-Header",
        ]

    def test_merge_agent_config_replaces_request_header_config(self, tmp_path):
        """Test that merge_agent_config replaces request header configuration when not specified."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "test-agent"

        # First configuration with request headers
        first_config = self._create_base_agent_config(agent_name)
        first_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization", "X-Original-Header"]}
        result1 = merge_agent_config(config_path, agent_name, first_config)
        save_config(result1, config_path)

        # Update configuration (without request header config)
        updated_config = self._create_base_agent_config(agent_name)
        updated_config.aws.region = "us-east-1"  # Change something else

        result_config = merge_agent_config(config_path, agent_name, updated_config)

        # Verify request header config is reset to None when not specified
        assert result_config.agents[agent_name].request_header_configuration is None
        # Verify update was applied
        assert result_config.agents[agent_name].aws.region == "us-east-1"

    def test_merge_agent_config_preserves_with_explicit_config(self, tmp_path):
        """Test that request header config can be preserved by explicitly providing it in updates."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "test-agent"

        # First configuration with request headers
        first_config = self._create_base_agent_config(agent_name)
        first_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization", "X-Original-Header"]}
        result1 = merge_agent_config(config_path, agent_name, first_config)
        save_config(result1, config_path)

        # Update configuration with explicit request header config to preserve it
        updated_config = self._create_base_agent_config(agent_name)
        updated_config.aws.region = "us-east-1"  # Change region
        updated_config.request_header_configuration = {  # Explicitly include headers
            "requestHeaderAllowlist": ["Authorization", "X-Original-Header"]
        }

        result_config = merge_agent_config(config_path, agent_name, updated_config)

        # Verify both changes are applied
        assert result_config.agents[agent_name].request_header_configuration is not None
        assert result_config.agents[agent_name].request_header_configuration["requestHeaderAllowlist"] == [
            "Authorization",
            "X-Original-Header",
        ]
        assert result_config.agents[agent_name].aws.region == "us-east-1"

    def test_merge_agent_config_updates_request_header_config(self, tmp_path):
        """Test that merge_agent_config updates request header configuration when provided."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "test-agent"

        # First configuration with request headers
        first_config = self._create_base_agent_config(agent_name)
        first_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization"]}
        result1 = merge_agent_config(config_path, agent_name, first_config)
        save_config(result1, config_path)

        # Update configuration with new request header config
        updated_config = self._create_base_agent_config(agent_name)
        updated_config.request_header_configuration = {
            "requestHeaderAllowlist": ["Authorization", "X-New-Header", "X-Updated-Header"]
        }

        result_config = merge_agent_config(config_path, agent_name, updated_config)

        # Verify request header config was updated
        assert result_config.agents[agent_name].request_header_configuration["requestHeaderAllowlist"] == [
            "Authorization",
            "X-New-Header",
            "X-Updated-Header",
        ]

    def test_merge_agent_config_clears_request_header_config_when_none(self, tmp_path):
        """Test that merge_agent_config can clear request header configuration."""
        config_path = tmp_path / "test_config.yaml"
        agent_name = "test-agent"

        # First configuration with request headers
        first_config = self._create_base_agent_config(agent_name)
        first_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization", "X-Original-Header"]}
        result1 = merge_agent_config(config_path, agent_name, first_config)
        save_config(result1, config_path)

        # Update configuration with None request header config (explicit clearing)
        updated_config = self._create_base_agent_config(agent_name)
        updated_config.request_header_configuration = None

        result_config = merge_agent_config(config_path, agent_name, updated_config)

        # Verify request header config was cleared
        assert result_config.agents[agent_name].request_header_configuration is None

    def test_agent_schema_serialization_with_request_headers(self, tmp_path):
        """Test that BedrockAgentCoreAgentSchema serializes request headers correctly."""
        agent_config = self._create_base_agent_config()
        agent_config.request_header_configuration = {
            "requestHeaderAllowlist": [
                "Authorization",
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-SessionId",
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*",
            ]
        }

        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        # Save and verify the file content has proper structure
        config_path = tmp_path / "serialization_test.yaml"
        save_config(project_config, config_path)

        # Read raw content to verify serialization format
        raw_content = config_path.read_text()

        # Should contain the request_header_configuration section
        assert "request_header_configuration:" in raw_content
        assert "requestHeaderAllowlist:" in raw_content
        assert "Authorization" in raw_content
        assert "X-Amzn-Bedrock-AgentCore-Runtime-Custom-SessionId" in raw_content

    def test_config_schema_validation_with_request_headers(self):
        """Test BedrockAgentCoreConfigSchema validation includes request headers."""
        agent_config = self._create_base_agent_config()
        agent_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header"]}

        # Test valid configuration
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        # Should validate without errors
        retrieved_config = project_config.get_agent_config("test-agent")
        assert retrieved_config.request_header_configuration is not None
        assert len(retrieved_config.request_header_configuration["requestHeaderAllowlist"]) == 2

    def test_multiple_agents_different_request_headers(self, tmp_path):
        """Test configuration with multiple agents having different request header configs."""
        config_path = tmp_path / "multi_agent_headers.yaml"

        # Agent 1 with basic headers
        agent1_config = self._create_base_agent_config("agent1")
        agent1_config.request_header_configuration = {"requestHeaderAllowlist": ["Authorization"]}

        # Agent 2 with more headers
        agent2_config = self._create_base_agent_config("agent2")
        agent2_config.request_header_configuration = {
            "requestHeaderAllowlist": ["Authorization", "X-Custom-Header", "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*"]
        }

        # Agent 3 with no header config (None)
        agent3_config = self._create_base_agent_config("agent3")
        # Explicitly keep request_header_configuration as None (default)

        # Create project config
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="agent1", agents={"agent1": agent1_config, "agent2": agent2_config, "agent3": agent3_config}
        )

        # Save and reload
        save_config(project_config, config_path)
        loaded_config = load_config(config_path)

        # Verify each agent has correct configuration
        loaded_agent1 = loaded_config.get_agent_config("agent1")
        assert len(loaded_agent1.request_header_configuration["requestHeaderAllowlist"]) == 1

        loaded_agent2 = loaded_config.get_agent_config("agent2")
        assert len(loaded_agent2.request_header_configuration["requestHeaderAllowlist"]) == 3

        loaded_agent3 = loaded_config.get_agent_config("agent3")
        assert loaded_agent3.request_header_configuration is None


class TestLegacyFormatTransformation:
    """Test legacy format transformation functionality."""

    def test_load_legacy_format(self, tmp_path):
        """Test loading and transforming legacy single-agent format."""
        # Lines 44-45, 58: Test legacy format transformation
        config_path = tmp_path / "legacy_config.yaml"

        # Create legacy format config (single agent, no 'agents' key)
        legacy_config = {
            "name": "legacy-agent",
            "entrypoint": "agent.py",
            "platform": "linux/arm64",
            "container_runtime": "docker",
            "aws": {
                "region": "us-west-2",
                "account": "123456789012",
                "network_configuration": {"network_mode": "PUBLIC"},
                "observability": {"enabled": True},
            },
            "bedrock_agentcore": {},
        }

        with open(config_path, "w") as f:
            yaml.dump(legacy_config, f)

        # Load the config - should auto-transform to multi-agent format
        loaded_config = load_config(config_path)

        # Verify transformation
        assert isinstance(loaded_config, BedrockAgentCoreConfigSchema)
        assert loaded_config.default_agent == "legacy-agent"
        assert "legacy-agent" in loaded_config.agents
        assert loaded_config.agents["legacy-agent"].name == "legacy-agent"
        assert loaded_config.agents["legacy-agent"].entrypoint == "agent.py"


class TestConfigValidationErrors:
    """Test configuration validation error handling."""

    def test_validation_error_field_required(self, tmp_path):
        """Test validation error handling for required fields."""
        # Lines 73: Test 'field required' error handling
        config_path = tmp_path / "missing_field_config.yaml"

        # Create config missing required field (entrypoint)
        invalid_config = {
            "default_agent": "test-agent",
            "agents": {
                "test-agent": {
                    "name": "test-agent",
                    # Missing 'entrypoint' field
                    "aws": {
                        "region": "us-west-2",
                        "network_configuration": {"network_mode": "PUBLIC"},
                        "observability": {"enabled": True},
                    },
                    "bedrock_agentcore": {},
                }
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)

        # Should raise RuntimeToolkitException with friendly error message
        with pytest.raises(RuntimeToolkitException) as exc_info:
            load_config(config_path)

        assert "Configuration validation failed" in str(exc_info.value)
        # Check for the friendly error message about required field
        assert "Field required" in str(exc_info.value)

    def test_validation_error_input_type(self, tmp_path):
        """Test validation error handling for input type errors."""
        # Lines 75: Test 'Input should be' error handling
        config_path = tmp_path / "invalid_type_config.yaml"

        # Create config with invalid type (region as integer instead of string)
        invalid_config = {
            "default_agent": "test-agent",
            "agents": {
                "test-agent": {
                    "name": "test-agent",
                    "entrypoint": "agent.py",
                    "aws": {
                        "region": 123,  # Invalid: should be string
                        "network_configuration": {"network_mode": "PUBLIC"},
                        "observability": {"enabled": True},
                    },
                    "bedrock_agentcore": {},
                }
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)

        # Should raise RuntimeToolkitException with friendly error message
        with pytest.raises(RuntimeToolkitException) as exc_info:
            load_config(config_path)

        assert "Configuration validation failed" in str(exc_info.value)

    def test_general_exception_handling(self, tmp_path):
        """Test general exception handling for non-ValidationError exceptions."""
        # Lines 80-81: Test general exception handling
        config_path = tmp_path / "corrupt_config.yaml"

        # Create corrupt YAML that will raise a general exception
        with open(config_path, "w") as f:
            f.write("{corrupt yaml content that doesn't parse properly")

        # Should raise RuntimeToolkitException for general errors
        with pytest.raises((RuntimeToolkitException, yaml.YAMLError)):
            load_config(config_path)


class TestGetAgentcoreDirectory:
    """Test get_agentcore_directory functionality."""

    def test_get_agentcore_directory_with_source_path(self, tmp_path):
        """Test agentcore directory when source_path is provided."""
        # Lines 166-168: Test multi-agent path creation
        project_root = tmp_path / "project"
        project_root.mkdir()
        agent_name = "test-agent"
        source_path = "/some/source/path"

        result = get_agentcore_directory(project_root, agent_name, source_path)

        # Should create .bedrock_agentcore/{agent_name}/ directory
        expected_path = project_root / ".bedrock_agentcore" / agent_name
        assert result == expected_path
        assert result.exists()
        assert result.is_dir()

    def test_get_agentcore_directory_without_source_path(self, tmp_path):
        """Test agentcore directory when source_path is None (legacy)."""
        # Lines 170-171: Test legacy single-agent behavior
        project_root = tmp_path / "project"
        project_root.mkdir()
        agent_name = "test-agent"

        result = get_agentcore_directory(project_root, agent_name, None)

        # Should return project root (legacy behavior)
        assert result == project_root

    def test_get_agentcore_directory_creates_nested_dirs(self, tmp_path):
        """Test that nested directories are created properly."""
        # Test mkdir with parents=True functionality
        project_root = tmp_path / "deep" / "nested" / "project"
        # Don't create project_root manually - let the function do it
        agent_name = "test-agent"
        source_path = "/some/source"

        result = get_agentcore_directory(project_root, agent_name, source_path)

        # Should create all parent directories
        expected_path = tmp_path / "deep" / "nested" / "project" / ".bedrock_agentcore" / "test-agent"
        assert result.exists()
        assert result == expected_path
