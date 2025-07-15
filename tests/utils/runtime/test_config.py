"""Tests for BedrockAgentCore configuration management."""

import logging
from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.utils.runtime.config import (
    is_project_config_format,
    load_config,
    merge_agent_config,
    save_config,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
    ProtocolConfiguration,
)


class TestProjectConfiguration:
    """Test project configuration functionality."""

    def test_load_project_config_single_agent(self):
        """Test loading project config with single agent."""
        from pathlib import Path

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
        from pathlib import Path

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
        from pathlib import Path

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "project_config_multiple.yaml"
        project_config = load_config(fixture_path)

        # Get specific agent
        code_config = project_config.get_agent_config("code-assistant")
        assert code_config.name == "code-assistant"
        assert code_config.entrypoint == "code.py"
        assert code_config.aws.region == "us-west-2"

    def test_get_default_agent_config(self):
        """Test getting default agent config."""
        from pathlib import Path

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
        from pathlib import Path

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
        from pathlib import Path

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
        from pathlib import Path

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
