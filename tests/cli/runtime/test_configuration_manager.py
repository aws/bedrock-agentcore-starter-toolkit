"""Tests for ConfigurationManager."""

from unittest.mock import Mock, patch

from bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager import ConfigurationManager


class TestConfigurationManager:
    """Test ConfigurationManager functionality."""

    def test_prompt_execution_role_with_user_input(self, tmp_path):
        """Test prompt_execution_role with user providing a role."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user input
            mock_prompt.return_value = "arn:aws:iam::123456789012:role/TestExecutionRole"

            result = config_manager.prompt_execution_role()

            assert result == "arn:aws:iam::123456789012:role/TestExecutionRole"
            mock_prompt.assert_called_once_with("Enter execution role ARN or name", "")
            mock_success.assert_called_once_with(
                "Using execution role: [dim]arn:aws:iam::123456789012:role/TestExecutionRole[/dim]"
            )

    def test_prompt_execution_role_with_existing_config(self, tmp_path):
        """Test prompt_execution_role with existing configuration as default."""
        # Mock existing config
        mock_project_config = Mock()
        mock_agent_config = Mock()
        mock_agent_config.aws.execution_role = "arn:aws:iam::123456789012:role/ExistingRole"
        mock_project_config.get_agent_config.return_value = mock_agent_config

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists",
                return_value=mock_project_config,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user accepting default (returning existing role)
            mock_prompt.return_value = "arn:aws:iam::123456789012:role/ExistingRole"

            result = config_manager.prompt_execution_role()

            assert result == "arn:aws:iam::123456789012:role/ExistingRole"
            # Should use existing role as default
            mock_prompt.assert_called_once_with(
                "Enter execution role ARN or name", "arn:aws:iam::123456789012:role/ExistingRole"
            )
            mock_success.assert_called_once_with(
                "Using execution role: [dim]arn:aws:iam::123456789012:role/ExistingRole[/dim]"
            )

    def test_prompt_execution_role_existing_config_overridden(self, tmp_path):
        """Test prompt_execution_role when user overrides existing config."""
        # Mock existing config
        mock_project_config = Mock()
        mock_agent_config = Mock()
        mock_agent_config.aws.execution_role = "arn:aws:iam::123456789012:role/OldRole"
        mock_project_config.get_agent_config.return_value = mock_agent_config

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists",
                return_value=mock_project_config,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user providing new role (overriding existing)
            mock_prompt.return_value = "arn:aws:iam::123456789012:role/NewRole"

            result = config_manager.prompt_execution_role()

            assert result == "arn:aws:iam::123456789012:role/NewRole"
            # Should use existing role as default but return new role
            mock_prompt.assert_called_once_with(
                "Enter execution role ARN or name", "arn:aws:iam::123456789012:role/OldRole"
            )
            mock_success.assert_called_once_with(
                "Using execution role: [dim]arn:aws:iam::123456789012:role/NewRole[/dim]"
            )
