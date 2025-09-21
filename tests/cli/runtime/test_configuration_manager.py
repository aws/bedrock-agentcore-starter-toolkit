"""Tests for ConfigurationManager."""

from unittest.mock import Mock, patch
import pytest

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
            mock_prompt.assert_called_once_with("Execution role ARN/name (or press Enter to auto-create)", "")
            mock_success.assert_called_once_with(
                "Using existing execution role: [dim]arn:aws:iam::123456789012:role/TestExecutionRole[/dim]"
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
            # Should use empty default since we're showing the existing config separately
            mock_prompt.assert_called_once_with("Execution role ARN/name (or press Enter to auto-create)", "")
            mock_success.assert_called_once_with(
                "Using existing execution role: [dim]arn:aws:iam::123456789012:role/ExistingRole[/dim]"
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
            # Should use empty default since we're showing the existing config separately
            mock_prompt.assert_called_once_with("Execution role ARN/name (or press Enter to auto-create)", "")
            mock_success.assert_called_once_with(
                "Using existing execution role: [dim]arn:aws:iam::123456789012:role/NewRole[/dim]"
            )

    def test_prompt_request_header_allowlist_no_configuration(self, tmp_path):
        """Test prompt_request_header_allowlist when user declines configuration."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user declining configuration
            mock_prompt.return_value = "no"

            result = config_manager.prompt_request_header_allowlist()

            assert result is None
            mock_prompt.assert_called_once_with("Configure request header allowlist? (yes/no)", "no")
            mock_success.assert_called_once_with("Using default request header configuration")

    def test_prompt_request_header_allowlist_with_configuration(self, tmp_path):
        """Test prompt_request_header_allowlist when user configures headers."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user accepting configuration, then configuring headers
            mock_prompt.side_effect = [
                "yes",  # First call: "Configure request header allowlist?"
                "Authorization,X-Custom-Header"  # Second call: "Enter allowed request headers"
            ]

            result = config_manager.prompt_request_header_allowlist()

            assert result == {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header"]}
            assert mock_prompt.call_count == 2
            mock_success.assert_called_once_with("Request header allowlist configured with 2 headers")

    def test_prompt_request_header_allowlist_with_existing_config(self, tmp_path):
        """Test prompt_request_header_allowlist with existing configuration."""
        # Mock existing config
        mock_project_config = Mock()
        mock_agent_config = Mock()
        mock_agent_config.request_header_configuration = {
            "requestHeaderAllowlist": ["Authorization", "X-Existing-Header"]
        }
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

            # Mock user accepting existing configuration
            mock_prompt.side_effect = [
                "yes",  # First call: "Configure request header allowlist?"
                "Authorization,X-Existing-Header"  # Second call: headers (using existing)
            ]

            result = config_manager.prompt_request_header_allowlist()

            assert result == {"requestHeaderAllowlist": ["Authorization", "X-Existing-Header"]}
            # Should use "yes" default since existing headers are present
            first_call_args = mock_prompt.call_args_list[0]
            assert first_call_args[0][1] == "yes"  # Default should be "yes"

    def test_prompt_request_header_allowlist_non_interactive(self, tmp_path):
        """Test prompt_request_header_allowlist in non-interactive mode."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml", non_interactive=True)

            result = config_manager.prompt_request_header_allowlist()

            assert result is None
            mock_success.assert_called_once_with("Using default request header configuration")

    def test_configure_request_header_allowlist_basic(self, tmp_path):
        """Test _configure_request_header_allowlist with basic input."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user input with headers
            mock_prompt.return_value = "Authorization,X-Custom-Header,X-Another-Header"

            result = config_manager._configure_request_header_allowlist()

            expected = {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header", "X-Another-Header"]}
            assert result == expected
            mock_success.assert_called_once_with("Request header allowlist configured with 3 headers")

    def test_configure_request_header_allowlist_with_existing_headers(self, tmp_path):
        """Test _configure_request_header_allowlist with existing headers passed in."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            existing_headers = "Authorization,X-Existing-Header"
            # Mock user accepting existing headers
            mock_prompt.return_value = existing_headers

            result = config_manager._configure_request_header_allowlist(existing_headers)

            expected = {"requestHeaderAllowlist": ["Authorization", "X-Existing-Header"]}
            assert result == expected
            # Should use existing headers as default
            mock_prompt.assert_called_once_with(
                "Enter allowed request headers (comma-separated)", 
                existing_headers
            )

    def test_configure_request_header_allowlist_with_whitespace(self, tmp_path):
        """Test _configure_request_header_allowlist handles whitespace properly."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock input with various whitespace patterns
            mock_prompt.return_value = " Authorization , X-Custom-Header ,  X-Another-Header  "

            result = config_manager._configure_request_header_allowlist()

            expected = {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header", "X-Another-Header"]}
            assert result == expected

    def test_configure_request_header_allowlist_empty_input_error(self, tmp_path):
        """Test _configure_request_header_allowlist handles empty input properly."""
        import typer
        
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._handle_error") as mock_error,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock empty input
            mock_prompt.return_value = ""
            # Mock _handle_error to raise typer.Exit to simulate real behavior
            mock_error.side_effect = typer.Exit(1)

            # Should raise typer.Exit when empty input is provided
            with pytest.raises(typer.Exit):
                config_manager._configure_request_header_allowlist()

            mock_error.assert_called_once_with("At least one request header must be specified for allowlist configuration")

    def test_configure_request_header_allowlist_only_commas_error(self, tmp_path):
        """Test _configure_request_header_allowlist handles input with only commas."""
        import typer
        
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._handle_error") as mock_error,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock input with only commas and whitespace
            mock_prompt.return_value = " , , , "
            # Mock _handle_error to raise typer.Exit to simulate real behavior
            mock_error.side_effect = typer.Exit(1)

            # Should raise typer.Exit when only commas are provided
            with pytest.raises(typer.Exit):
                config_manager._configure_request_header_allowlist()

            mock_error.assert_called_once_with("Empty request header allowlist provided")

    def test_configure_request_header_allowlist_default_headers(self, tmp_path):
        """Test _configure_request_header_allowlist uses default headers when no existing ones."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user accepting defaults
            default_headers = "Authorization,X-Amzn-Bedrock-AgentCore-Runtime-Custom-*"
            mock_prompt.return_value = default_headers

            result = config_manager._configure_request_header_allowlist()

            expected = {"requestHeaderAllowlist": ["Authorization", "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*"]}
            assert result == expected
            # Should use default headers when no existing ones provided
            mock_prompt.assert_called_once_with(
                "Enter allowed request headers (comma-separated)", 
                default_headers
            )
