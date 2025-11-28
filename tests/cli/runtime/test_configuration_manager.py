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
                "Authorization,X-Custom-Header",  # Second call: "Enter allowed request headers"
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
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success"),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user accepting existing configuration
            mock_prompt.side_effect = [
                "yes",  # First call: "Configure request header allowlist?"
                "Authorization,X-Existing-Header",  # Second call: headers (using existing)
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
        """Test _configure_request_header_allowlist uses hardcoded default (no longer accepts parameters)."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success"),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user providing custom headers
            custom_headers = "Authorization,X-Custom-Header"
            mock_prompt.return_value = custom_headers

            result = config_manager._configure_request_header_allowlist()

            expected = {"requestHeaderAllowlist": ["Authorization", "X-Custom-Header"]}
            assert result == expected
            # Should use hardcoded default (no longer auto-populates from config)
            default_headers = "Authorization,X-Amzn-Bedrock-AgentCore-Runtime-Custom-*"
            mock_prompt.assert_called_once_with("Enter allowed request headers (comma-separated)", default_headers)

    def test_configure_request_header_allowlist_with_whitespace(self, tmp_path):
        """Test _configure_request_header_allowlist handles whitespace properly."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success"),
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

            mock_error.assert_called_once_with(
                "At least one request header must be specified for allowlist configuration"
            )

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
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success"),
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
            mock_prompt.assert_called_once_with("Enter allowed request headers (comma-separated)", default_headers)

    def test_prompt_memory_selection_create_new_stm_only(self, tmp_path):
        """Test prompt_memory_selection when creating new memory with STM only."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user choosing to create new memory with STM only
            mock_prompt.side_effect = [
                "",  # Press Enter to create new
                "no",  # No to LTM
            ]

            action, value = config_manager.prompt_memory_selection()

            assert action == "CREATE_NEW"
            assert value == "STM_ONLY"
            mock_success.assert_called_with("Using short-term memory only")

    def test_prompt_memory_selection_create_new_stm_and_ltm(self, tmp_path):
        """Test prompt_memory_selection when creating new memory with STM+LTM."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
            # Mock the MemoryManager import to skip the existing memory check
            patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager") as mock_mm_class,
        ):
            # Make MemoryManager raise an exception to skip to new memory creation
            mock_mm_class.side_effect = Exception("No memory manager available")

            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            mock_prompt.return_value = "yes"  # Enable LTM

            action, value = config_manager.prompt_memory_selection()

            assert action == "CREATE_NEW"
            assert value == "STM_AND_LTM"
            mock_success.assert_called_with("Configuring short-term + long-term memory")

    def test_init_with_non_interactive_mode(self, tmp_path):
        """Test initialization with non_interactive=True."""
        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml", non_interactive=True)
            assert config_manager.non_interactive is True
            assert config_manager.existing_config is None

    def test_prompt_execution_role_non_interactive(self, tmp_path):
        """Test prompt_execution_role in non-interactive mode."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml", non_interactive=True)
            result = config_manager.prompt_execution_role()

            assert result is None
            mock_success.assert_called_once_with("Will auto-create execution role")

    def test_prompt_ecr_repository_non_interactive(self, tmp_path):
        """Test prompt_ecr_repository in non-interactive mode."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml", non_interactive=True)
            repo, auto_create = config_manager.prompt_ecr_repository()

            assert repo is None
            assert auto_create is True
            mock_success.assert_called_once_with("Will auto-create ECR repository")

    def test_prompt_ecr_repository_with_user_input(self, tmp_path):
        """Test prompt_ecr_repository with user providing a repository."""
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
            mock_prompt.return_value = "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo"

            repo, auto_create = config_manager.prompt_ecr_repository()

            assert repo == "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo"
            assert auto_create is False
            mock_prompt.assert_called_once_with("ECR Repository URI (or press Enter to auto-create)", "")
            mock_success.assert_called_once_with(
                "Using existing ECR repository: [dim]123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo[/dim]"
            )

    def test_prompt_oauth_config_non_interactive(self, tmp_path):
        """Test prompt_oauth_config in non-interactive mode."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml", non_interactive=True)
            result = config_manager.prompt_oauth_config()

            assert result is None
            mock_success.assert_called_once_with("Using default IAM authorization")

    def test_prompt_oauth_config_with_no(self, tmp_path):
        """Test prompt_oauth_config when user declines OAuth."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user declining OAuth
            mock_prompt.return_value = "no"

            result = config_manager.prompt_oauth_config()

            assert result is None
            mock_prompt.assert_called_once_with("Configure OAuth authorizer instead? (yes/no)", "no")
            mock_success.assert_called_once_with("Using default IAM authorization")

    def test_configure_oauth_basic(self, tmp_path):
        """Test _configure_oauth with basic configuration."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user input for OAuth configuration
            mock_prompt.side_effect = [
                "https://cognito-idp.us-east-1.amazonaws.com/my-user-pool",  # discovery URL
                "client1,client2",  # client IDs
                "api://default",  # audience
            ]

            result = config_manager._configure_oauth()

            expected = {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/my-user-pool",
                    "allowedClients": ["client1", "client2"],
                    "allowedAudience": ["api://default"],
                }
            }
            assert result == expected
            assert mock_prompt.call_count == 3
            mock_success.assert_called_once_with("OAuth authorizer configuration created")

    def test_prompt_memory_type_yes_both(self, tmp_path):
        """Test prompt_memory_type with user enabling both STM and LTM."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user enabling both memory types
            mock_prompt.side_effect = ["yes", "yes"]

            enable_memory, enable_ltm = config_manager.prompt_memory_type()

            assert enable_memory is True
            assert enable_ltm is True
            assert mock_prompt.call_count == 2
            mock_success.assert_called_once_with("Long-term memory will be configured")

    def test_prompt_memory_type_yes_stm_only(self, tmp_path):
        """Test prompt_memory_type with user enabling only STM."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user enabling STM but not LTM
            mock_prompt.side_effect = ["yes", "no"]

            enable_memory, enable_ltm = config_manager.prompt_memory_type()

            assert enable_memory is True
            assert enable_ltm is False
            assert mock_prompt.call_count == 2
            mock_success.assert_called_once_with("Using short-term memory only")

    def test_prompt_memory_type_no(self, tmp_path):
        """Test prompt_memory_type with user disabling memory."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

            # Mock user disabling all memory
            mock_prompt.return_value = "no"

            enable_memory, enable_ltm = config_manager.prompt_memory_type()

            assert enable_memory is False
            assert enable_ltm is False
            mock_prompt.assert_called_once_with("Enable memory for your agent? (yes/no)", "yes")
            mock_success.assert_called_once_with("Memory disabled")

    def test_prompt_memory_selection_with_existing_memories(self, tmp_path):
        """Test memory selection with existing memories found (covers lines 264-303)."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
            patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager") as mock_mm,
        ):
            # Mock existing config with region
            mock_config = Mock()
            mock_config.aws.region = "us-west-2"

            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")
            config_manager.existing_config = mock_config

            # Mock memory manager to return existing memories
            mock_manager = Mock()
            mock_manager.list_memories.return_value = [
                {"id": "mem-123", "name": "existing-memory", "description": "Test memory"},
                {"id": "mem-456", "name": "another-memory", "description": "Another test"},
            ]
            mock_mm.return_value = mock_manager

            # User selects first memory
            mock_prompt.return_value = "1"

            action, value = config_manager.prompt_memory_selection()

            assert action == "USE_EXISTING"
            assert value == "mem-123"
            mock_success.assert_called_with("Using existing memory: existing-memory")

    def test_prompt_memory_selection_skip_option(self, tmp_path):
        """Test memory selection skip option (covers response == 's' branch)."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager.console.print"),
            patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager") as mock_mm,
        ):
            mock_config = Mock()
            mock_config.aws.region = "us-west-2"

            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")
            config_manager.existing_config = mock_config

            mock_manager = Mock()
            mock_manager.list_memories.return_value = [{"id": "mem-123", "name": "memory"}]
            mock_mm.return_value = mock_manager

            # User types 's' to skip memory configuration
            mock_prompt.return_value = "s"

            action, value = config_manager.prompt_memory_selection()

            assert action == "SKIP"
            assert value is None
            mock_success.assert_called_with("Skipping memory configuration")
