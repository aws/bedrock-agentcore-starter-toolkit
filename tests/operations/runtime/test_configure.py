"""Tests for Bedrock AgentCore configure operation."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.configure import (
    AGENT_NAME_ERROR,
    configure_bedrock_agentcore,
    detect_entrypoint,
    get_relative_path,
    infer_agent_name,
    validate_agent_name,
)


class TestConfigureBedrockAgentCore:
    """Test configure_bedrock_agentcore functionality."""

    def test_configure_bedrock_agentcore_basic(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test basic configuration flow."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
bedrock_agentcore = BedrockAgentCoreApp()
""")

        # Change to temp directory for config creation
        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager to bypass interactive prompts
            mock_config_manager = Mock()

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
                    deployment_type="container",
                    memory_mode="STM_ONLY",
                    non_interactive=True,
                )

                # Verify result structure - now using attribute access
                assert hasattr(result, "config_path")
                assert hasattr(result, "dockerfile_path")
                assert hasattr(result, "runtime")
                assert hasattr(result, "region")
                assert hasattr(result, "account_id")
                assert hasattr(result, "execution_role")

                # Verify values
                assert result.runtime == "Docker"
                assert result.region == "us-west-2"
                assert result.account_id == "123456789012"
                assert result.execution_role == "arn:aws:iam::123456789012:role/TestRole"

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Verify memory configuration in saved config
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["test_agent"]
                assert agent_config.memory.mode == "STM_ONLY"
        finally:
            os.chdir(original_cwd)

    def test_configure_with_memory_options(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with memory options."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    memory_mode="STM_AND_LTM",
                    non_interactive=True,
                )

                # Verify configuration was created
                assert result.config_path.exists()

                # Load config and verify memory settings
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.agents["test_agent"]

                assert agent_config.memory.mode == "STM_AND_LTM"
                assert agent_config.memory.event_expiry_days == 30
                assert agent_config.memory.memory_name == "test_agent_memory"

        finally:
            os.chdir(original_cwd)

    def test_configure_with_non_python_file(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with non-Python entrypoint file."""
        # Create non-python file
        agent_file = tmp_path / "test_agent.txt"
        agent_file.write_text("# not python")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
                    deployment_type="container",
                )

                # Should still work but skip the Python module inspection
                assert result.runtime == "Docker"

        finally:
            os.chdir(original_cwd)

    def test_configure_with_ecr_options(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test ECR auto-create vs custom ECR."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # Test auto-create ECR (default)
                result1 = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="arn:aws:iam::123456789012:role/TestRole",
                )
                assert result1.auto_create_ecr is True
                assert result1.ecr_repository is None

                # Test custom ECR repository
                result2 = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="arn:aws:iam::123456789012:role/TestRole",
                    ecr_repository="my-custom-repo",
                )
                assert result2.auto_create_ecr is False
                assert result2.ecr_repository == "my-custom-repo"

        finally:
            os.chdir(original_cwd)

    def test_configure_role_arn_formatting(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test execution role ARN handling."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # Test role name (should be converted to full ARN)
                result1 = configure_bedrock_agentcore(
                    agent_name="test_agent", entrypoint_path=agent_file, execution_role="MyRole"
                )
                assert result1.execution_role == "arn:aws:iam::123456789012:role/MyRole"

                # Test full ARN (should be kept as-is)
                full_arn = "arn:aws:iam::123456789012:role/MyCustomRole"
                result2 = configure_bedrock_agentcore(
                    agent_name="test_agent", entrypoint_path=agent_file, execution_role=full_arn
                )
                assert result2.execution_role == full_arn

        finally:
            os.chdir(original_cwd)

    def test_configure_bedrock_agentcore(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with verbose option enabled."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
bedrock_agentcore = BedrockAgentCoreApp()
""")

        # Change to temp directory for config creation
        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
                patch("bedrock_agentcore_starter_toolkit.operations.runtime.configure.log") as mock_log,
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
                    deployment_type="container",
                    verbose=True,  # Enable verbose mode
                    enable_observability=True,
                    requirements_file="requirements.txt",
                )

                # Verify result structure is correct
                assert hasattr(result, "config_path")
                assert hasattr(result, "dockerfile_path")
                assert hasattr(result, "runtime")
                assert hasattr(result, "region")
                assert hasattr(result, "account_id")
                assert hasattr(result, "execution_role")

                # Verify values
                assert result.runtime == "Docker"
                assert result.region == "us-west-2"
                assert result.account_id == "123456789012"
                assert result.execution_role == "arn:aws:iam::123456789012:role/TestRole"

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Verify that verbose logging was enabled (log.setLevel called with DEBUG)
                mock_log.setLevel.assert_called_with(10)  # logging.DEBUG = 10

                # Verify that debug messages were logged
                debug_calls = [call for call in mock_log.debug.call_args_list]
                assert len(debug_calls) > 0, "Expected debug log calls when verbose=True"
        finally:
            os.chdir(original_cwd)

    def test_configure_with_minimal_defaults(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configure operation with minimal parameters (non-interactive mode defaults)."""
        # Create minimal test agent file
        agent_file = tmp_path / "minimal_agent.py"
        agent_file.write_text("""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
bedrock_agentcore = BedrockAgentCoreApp()

@bedrock_agentcore.entrypoint
def handler(payload):
    return {"status": "success", "message": "Hello from minimal agent"}
""")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # Test with minimal parameters - only required ones, rest use defaults
                result = configure_bedrock_agentcore(
                    agent_name="minimal_agent",
                    entrypoint_path=agent_file,
                    # All other parameters should use their defaults
                    execution_role=None,  # Should auto-create
                    ecr_repository=None,  # Should auto-create
                    auto_create_ecr=True,  # Default for non-interactive
                    container_runtime="docker",  # Default runtime
                    enable_observability=True,  # Default enabled
                    authorizer_configuration=None,  # Default IAM
                    verbose=False,  # Default non-verbose
                    deployment_type="container",
                )

                # Verify result structure
                assert hasattr(result, "config_path")
                assert hasattr(result, "dockerfile_path")
                assert hasattr(result, "runtime")
                assert hasattr(result, "region")
                assert hasattr(result, "account_id")
                assert hasattr(result, "execution_role")

                # Verify all defaults are applied correctly
                assert result.runtime == "Docker"
                assert result.region == "us-west-2"  # Default region from mock
                assert result.account_id == "123456789012"  # Default account from mock

                # Verify auto-creation defaults
                assert result.auto_create_ecr is True
                assert result.ecr_repository is None  # Will be auto-created

                # Verify execution role is None (will be auto-created during launch, not configure)
                assert result.execution_role is None  # Auto-create during launch

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Verify Dockerfile path was returned (file creation is mocked in tests)
                assert result.dockerfile_path is not None

        finally:
            os.chdir(original_cwd)

    def test_configure_with_code_build_execution_role(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with separate CodeBuild execution role."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="ExecutionRole",
                    code_build_execution_role="CodeBuildRole",
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.execution_role == "arn:aws:iam::123456789012:role/ExecutionRole"
                assert agent_config.codebuild.execution_role == "arn:aws:iam::123456789012:role/CodeBuildRole"

        finally:
            os.chdir(original_cwd)

    def test_configure_with_request_header_allowlist(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with request header allowlist."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_config_manager_class,
            ):
                # Test with request header configuration
                request_header_config = {
                    "requestHeaderAllowlist": ["Authorization", "X-Custom-Header", "X-Test-Header"]
                }

                # Configure mock
                mock_config_manager = Mock()
                mock_config_manager.prompt_memory_selection.return_value = (
                    "CREATE_NEW",
                    "STM_ONLY",
                )  # Default to STM only
                mock_config_manager_class.return_value = mock_config_manager

                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
                    deployment_type="container",
                    request_header_configuration=request_header_config,
                )

                # Verify result structure
                assert hasattr(result, "config_path")
                assert result.runtime == "Docker"

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Load and verify the configuration contains request headers
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")

                assert agent_config.request_header_configuration is not None
                assert "requestHeaderAllowlist" in agent_config.request_header_configuration
                assert agent_config.request_header_configuration["requestHeaderAllowlist"] == [
                    "Authorization",
                    "X-Custom-Header",
                    "X-Test-Header",
                ]

        finally:
            os.chdir(original_cwd)

    def test_configure_without_code_build_execution_role(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration without CodeBuild execution role uses main execution role."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock the ConfigurationManager
            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="arn:aws:iam::123456789012:role/ExecutionRole",
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.execution_role == "arn:aws:iam::123456789012:role/ExecutionRole"
                assert agent_config.codebuild.execution_role is None

        finally:
            os.chdir(original_cwd)

    def test_configure_with_none_request_header_configuration(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with None request_header_configuration parameter."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_config_manager_class,
            ):
                # Configure mock
                mock_config_manager = Mock()
                mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")
                mock_config_manager_class.return_value = mock_config_manager

                # Test with None request header configuration
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    request_header_configuration=None,
                )

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()
                assert result.config_path is not None

                # Load and verify the configuration has None for request headers
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")

                assert agent_config.request_header_configuration is None

        finally:
            os.chdir(original_cwd)

    def test_configure_with_empty_request_header_configuration(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with empty dict request_header_configuration parameter."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_config_manager_class,
            ):
                # Test with empty dict request header configuration

                # Configure mock
                mock_config_manager = Mock()
                mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")
                mock_config_manager_class.return_value = mock_config_manager

                # Test with empty dict request header configuration
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    request_header_configuration={},
                )

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()
                assert result.config_path is not None

                # Load and verify the configuration has empty dict for request headers
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")

                assert agent_config.request_header_configuration == {}

        finally:
            os.chdir(original_cwd)

    def test_configure_verbose_logs_request_header_configuration(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that verbose mode logs request header configuration details."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_config_manager_class,
            ):
                # Mock the logger to capture verbose logging
                with patch("bedrock_agentcore_starter_toolkit.operations.runtime.configure.log") as mock_log:
                    request_header_config = {"requestHeaderAllowlist": ["Authorization", "X-Verbose-Test-Header"]}

                    # Configure mock
                    mock_config_manager = Mock()
                    mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")
                    mock_config_manager_class.return_value = mock_config_manager

                    # Mock container runtime
                    mock_container_runtime.runtime = "Docker"
                    mock_container_runtime.get_name.return_value = "Docker"

                    result = configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        request_header_configuration=request_header_config,
                        verbose=True,  # Enable verbose mode
                        deployment_type="container",  # Required for runtime to be initialized
                    )

                    # Verify result structure is correct
                    assert result.runtime == "Docker"

                    # Verify that verbose logging was enabled
                    mock_log.setLevel.assert_called_with(10)  # logging.DEBUG = 10

                    # Verify that request header configuration was logged
                    debug_calls = [call for call in mock_log.debug.call_args_list]
                    assert len(debug_calls) > 0, "Expected debug log calls when verbose=True"

                    # Check that request header configuration appears in one of the debug calls
                    request_header_logged = any("Request header configuration" in str(call) for call in debug_calls)
                    assert request_header_logged, "Expected request header configuration to be logged in verbose mode"

        finally:
            os.chdir(original_cwd)

    def test_configure_complex_request_header_configuration(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with complex request_header_configuration structure."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_config_manager_class,
            ):
                # Test with complex nested request header configuration
                request_header_config = {
                    "requestHeaderAllowlist": [
                        "Authorization",
                        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*",
                        "Content-Type",
                        "User-Agent",
                    ],
                    "additionalSettings": {"maxHeaderSize": 8192, "caseSensitive": False, "allowWildcards": True},
                }

                # Configure mock
                mock_config_manager = Mock()
                mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")
                mock_config_manager_class.return_value = mock_config_manager

                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    request_header_configuration=request_header_config,
                )

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()
                assert result.config_path is not None

                # Load and verify the complex configuration is preserved
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")

                assert agent_config.request_header_configuration is not None
                assert "requestHeaderAllowlist" in agent_config.request_header_configuration
                assert len(agent_config.request_header_configuration["requestHeaderAllowlist"]) == 4
                assert "Authorization" in agent_config.request_header_configuration["requestHeaderAllowlist"]
                assert (
                    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*"
                    in agent_config.request_header_configuration["requestHeaderAllowlist"]
                )

                # Verify additional settings are preserved
                assert "additionalSettings" in agent_config.request_header_configuration
                assert agent_config.request_header_configuration["additionalSettings"]["maxHeaderSize"] == 8192
                assert agent_config.request_header_configuration["additionalSettings"]["caseSensitive"] is False

        finally:
            os.chdir(original_cwd)

    def test_configure_with_all_authorization_options(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with both authorizer_configuration and request_header_configuration."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # Create a mock class that preserves class attributes
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_config_manager_class,
            ):
                # Test with both OAuth authorizer and request headers
                oauth_config = {
                    "customJWTAuthorizer": {
                        "discoveryUrl": "https://example.com/.well-known/openid_configuration",
                        "allowedClients": ["client1", "client2"],
                        "allowedAudience": ["aud1", "aud2"],
                    }
                }

                request_header_config = {"requestHeaderAllowlist": ["Authorization", "X-OAuth-Token", "X-Client-ID"]}

                # Configure mock
                mock_config_manager = Mock()
                mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")
                mock_config_manager_class.return_value = mock_config_manager

                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    authorizer_configuration=oauth_config,
                    request_header_configuration=request_header_config,
                )

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()
                assert result.config_path is not None

                # Load and verify both configurations are preserved
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")

                # Verify OAuth configuration
                assert agent_config.authorizer_configuration is not None
                assert "customJWTAuthorizer" in agent_config.authorizer_configuration
                assert (
                    agent_config.authorizer_configuration["customJWTAuthorizer"]["discoveryUrl"]
                    == "https://example.com/.well-known/openid_configuration"
                )

                # Verify request header configuration
                assert agent_config.request_header_configuration is not None
                assert agent_config.request_header_configuration["requestHeaderAllowlist"] == [
                    "Authorization",
                    "X-OAuth-Token",
                    "X-Client-ID",
                ]

        finally:
            os.chdir(original_cwd)

    def test_configure_with_vpc_enabled_valid_resources(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with valid VPC resources."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    vpc_enabled=True,
                    vpc_subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                    vpc_security_groups=["sg-abc123xyz789"],
                    non_interactive=True,
                )

                print("VPC enabled: True")
                print(f"Result network_mode: {result.network_mode}")
                print(f"Result subnets: {result.network_subnets}")
                print(f"Result security_groups: {result.network_security_groups}")

                # Verify VPC configuration in result
                assert result.network_mode == "VPC"
                assert result.network_subnets == ["subnet-abc123def456", "subnet-xyz789ghi012"]
                assert result.network_security_groups == ["sg-abc123xyz789"]

                # Load config and verify VPC settings
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.agents["test_agent"]

                assert agent_config.aws.network_configuration.network_mode == "VPC"
                assert agent_config.aws.network_configuration.network_mode_config.subnets == [
                    "subnet-abc123def456",
                    "subnet-xyz789ghi012",
                ]
                assert agent_config.aws.network_configuration.network_mode_config.security_groups == ["sg-abc123xyz789"]

        finally:
            os.chdir(original_cwd)

    def test_configure_with_source_path_parameter(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with source_path parameter."""
        # Create source directory structure
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        agent_file = source_dir / "agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    source_path=str(source_dir),  # Add source_path parameter
                    non_interactive=True,
                    deployment_type="container",  # Required for runtime to be initialized
                )

                assert result.runtime == "Docker"
                assert result.config_path.exists()

        finally:
            os.chdir(original_cwd)

    def test_configure_with_protocol_parameter(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with protocol parameter."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    vpc_enabled=True,
                    vpc_subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                    vpc_security_groups=["sg-abc123xyz789"],
                    protocol="MCP",  # Test different protocol
                    non_interactive=True,
                )

                # Verify VPC configuration in result
                assert result.network_mode == "VPC"
                assert result.network_subnets == ["subnet-abc123def456", "subnet-xyz789ghi012"]
                assert result.network_security_groups == ["sg-abc123xyz789"]

                # Verify protocol was set
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.agents["test_agent"]

                assert agent_config.aws.network_configuration.network_mode == "VPC"
                assert agent_config.aws.network_configuration.network_mode_config.subnets == [
                    "subnet-abc123def456",
                    "subnet-xyz789ghi012",
                ]
                assert agent_config.aws.network_configuration.network_mode_config.security_groups == ["sg-abc123xyz789"]
                assert agent_config.aws.protocol_configuration.server_protocol == "MCP"

        finally:
            os.chdir(original_cwd)

    def test_configure_vpc_requires_both_subnets_and_security_groups(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that VPC mode requires both subnets and security groups."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # ADD THIS MOCK SETUP:
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # Test with subnets but no security groups
                with pytest.raises(ValueError, match="VPC mode requires both subnets and security groups"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=["subnet-abc123"],
                        vpc_security_groups=None,
                        non_interactive=True,  # ADD THIS
                    )

                # Test with security groups but no subnets
                with pytest.raises(ValueError, match="VPC mode requires both subnets and security groups"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=None,
                        vpc_security_groups=["sg-xyz789"],
                        non_interactive=True,  # ADD THIS
                    )

        finally:
            os.chdir(original_cwd)

    def test_configure_vpc_subnet_format_validation(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test subnet ID format validation."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # ADD THIS MOCK SETUP:
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # Test invalid subnet prefix
                with pytest.raises(ValueError, match="Invalid subnet ID format"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=["invalid-abc123"],  # Wrong prefix
                        vpc_security_groups=["sg-xyz789"],
                        non_interactive=True,  # ADD THIS
                    )

                # Test subnet too short
                with pytest.raises(ValueError, match="Invalid subnet ID format"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=["subnet-abc"],  # Too short (< 15 chars)
                        vpc_security_groups=["sg-xyz789abc123"],
                        non_interactive=True,  # ADD THIS
                    )

        finally:
            os.chdir(original_cwd)

    def test_configure_vpc_security_group_format_validation(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test security group ID format validation."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:
            # ADD THIS MOCK SETUP:
            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # Test invalid SG prefix
                with pytest.raises(ValueError, match="Invalid security group ID format"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=["subnet-abc123def456"],
                        vpc_security_groups=["invalid-xyz789"],  # Wrong prefix
                        non_interactive=True,  # ADD THIS
                    )

                # Test SG too short
                with pytest.raises(ValueError, match="Invalid security group ID format"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=["subnet-abc123def456"],
                        vpc_security_groups=["sg-xyz"],  # Too short (< 11 chars)
                        non_interactive=True,  # ADD THIS
                    )

        finally:
            os.chdir(original_cwd)

    def test_configure_vpc_immutability_check(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that VPC configuration cannot be changed after agent creation."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                # First configure with VPC
                _ = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    vpc_enabled=True,
                    vpc_subnets=["subnet-abc123def456"],
                    vpc_security_groups=["sg-xyz789abc123"],
                    non_interactive=True,
                )

                # Try to reconfigure with PUBLIC mode - should fail
                with pytest.raises(ValueError, match="Cannot change network mode"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=False,  # Trying to change to PUBLIC
                        non_interactive=True,
                    )

                # Try to reconfigure with different subnets - should fail
                with pytest.raises(ValueError, match="Cannot change VPC subnets"):
                    configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        vpc_enabled=True,
                        vpc_subnets=["subnet-different123"],  # Different subnets
                        vpc_security_groups=["sg-xyz789abc123"],
                        non_interactive=True,
                    )

        finally:
            os.chdir(original_cwd)

    def test_configure_default_public_mode(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that default network mode is PUBLIC when VPC not specified."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")
            # Simulate user choosing existing memory
            mock_config_manager.prompt_memory_selection.return_value = ("USE_EXISTING", "mem-existing-123")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    # vpc_enabled not specified - should default to PUBLIC
                    memory_mode="STM_ONLY",  # This should be overridden by interactive choice
                    non_interactive=False,  # Interactive mode
                )

                # Verify PUBLIC mode is default
                assert result.network_mode == "PUBLIC"
                assert result.network_subnets is None
                assert result.network_security_groups is None

                # Verify existing memory was used
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.agents["test_agent"]

                assert agent_config.aws.network_configuration.network_mode == "PUBLIC"
                assert agent_config.aws.network_configuration.network_mode_config is None
                assert agent_config.memory.memory_id == "mem-existing-123"

        finally:
            os.chdir(original_cwd)

    def test_configure_interactive_memory_selection_skip(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test interactive memory selection choosing to skip memory."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            # Simulate user choosing to skip memory
            mock_config_manager.prompt_memory_selection.return_value = ("SKIP", None)

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    memory_mode="STM_ONLY",  # This should be overridden by interactive choice
                    non_interactive=False,  # Interactive mode
                )

                # Verify memory was disabled
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.agents["test_agent"]
                assert agent_config.memory.mode == "NO_MEMORY"

        finally:
            os.chdir(original_cwd)


class TestValidateAgentName:
    """Test class for validate_agent_name function."""

    def test_valid_agent_names(self):
        """Test that valid agent names pass validation."""
        valid_names = [
            "a",  # Single letter (minimum valid)
            "A",  # Single uppercase letter
            "agent",  # Simple lowercase name
            "Agent",  # Simple mixed case name
            "AGENT_123",  # Simple uppercase name
            "a" * 48,  # Maximum length (48 characters)
            "A" + "b" * 47,  # Max length with mixed case
            "z" + "1" * 47,  # Max length with numbers
            "x" + "_" * 47,  # Max length with underscores
        ]

        for name in valid_names:
            is_valid, error_msg = validate_agent_name(name)
            assert is_valid is True, f"Expected '{name}' to be valid but got error: {error_msg}"
            assert error_msg == "", f"Expected no error message for valid name '{name}' but got: {error_msg}"

    def test_invalid_agent_names_with_special_characters(self):
        """Test that agent names with invalid characters are rejected."""
        invalid_names = [
            "agent-name",  # Hyphen not allowed
            "agent.name",  # Dot not allowed
            "agent name",  # Space not allowed
            "agent@name",  # @ symbol not allowed
            "agent#name",  # # symbol not allowed
        ]

        for name in invalid_names:
            is_valid, error_msg = validate_agent_name(name)
            assert is_valid is False, f"Expected '{name}' to be invalid"
            assert error_msg == AGENT_NAME_ERROR, f"Expected standard error message for '{name}'"

    def test_agent_names_too_long(self):
        """Test that agent names longer than 48 characters are invalid."""
        invalid_names = [
            "a" * 49,  # 49 characters (1 over limit)
            "a" * 50,  # 50 characters
            "a" * 100,  # 100 characters
            "A" + "b" * 48,  # 49 characters with mixed case
        ]

        for name in invalid_names:
            is_valid, error_msg = validate_agent_name(name)
            assert is_valid is False, f"Expected '{name}' (length {len(name)}) to be invalid"
            assert error_msg == AGENT_NAME_ERROR, "Expected standard error message for long name"

    def test_empty_and_none_agent_names(self):
        """Test that empty strings and None values are handled properly."""
        invalid_names = [
            "",  # Empty string
        ]

        for name in invalid_names:
            is_valid, error_msg = validate_agent_name(name)
            assert is_valid is False, f"Expected '{name}' to be invalid"
            assert error_msg == AGENT_NAME_ERROR, f"Expected standard error message for '{name}'"

    def test_validate_agent_name_additional_patterns(self):
        """Test validate_agent_name with various name patterns."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.configure import validate_agent_name

        # Test valid names
        valid_names = ["agent123", "Agent_123", "A_1"]
        for name in valid_names:
            is_valid, _ = validate_agent_name(name)
            assert is_valid is True, f"Expected '{name}' to be valid"

        # Test invalid names
        invalid_names = ["1agent", "agent-123", "agent.name"]
        for name in invalid_names:
            is_valid, _ = validate_agent_name(name)
            assert is_valid is False, f"Expected '{name}' to be invalid"


class TestLifecycleConfiguration:
    """Test lifecycle configuration parameters (idle timeout and max lifetime)."""

    def test_configure_with_idle_timeout(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with idle timeout parameter."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    idle_timeout=300,  # 5 minutes
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.lifecycle_configuration.idle_runtime_session_timeout == 300
                assert agent_config.aws.lifecycle_configuration.has_custom_settings is True

        finally:
            os.chdir(original_cwd)

    def test_configure_with_max_lifetime(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with max lifetime parameter."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    max_lifetime=3600,  # 1 hour
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.lifecycle_configuration.max_lifetime == 3600
                assert agent_config.aws.lifecycle_configuration.has_custom_settings is True

        finally:
            os.chdir(original_cwd)

    def test_configure_with_both_lifecycle_parameters(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with both idle timeout and max lifetime."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    idle_timeout=600,  # 10 minutes
                    max_lifetime=7200,  # 2 hours
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.lifecycle_configuration.idle_runtime_session_timeout == 600
                assert agent_config.aws.lifecycle_configuration.max_lifetime == 7200
                assert agent_config.aws.lifecycle_configuration.has_custom_settings is True

        finally:
            os.chdir(original_cwd)

    def test_configure_verbose_logs_lifecycle_configuration(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that verbose mode logs lifecycle configuration details."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
                patch("bedrock_agentcore_starter_toolkit.operations.runtime.configure.log") as mock_log,
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    idle_timeout=1800,  # 30 minutes
                    max_lifetime=10800,  # 3 hours
                    verbose=True,
                )

                # Verify result was created successfully
                assert result.config_path.exists()

                # Verify verbose logging was enabled
                mock_log.setLevel.assert_called_with(10)  # logging.DEBUG = 10

                # Verify that lifecycle configuration was logged
                debug_calls = [str(call) for call in mock_log.debug.call_args_list]
                assert any("Lifecycle configuration" in call or "Idle timeout" in call for call in debug_calls)

        finally:
            os.chdir(original_cwd)


class TestMemoryModeConfiguration:
    """Test different memory mode configurations."""

    def test_configure_with_no_memory_mode(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with memory explicitly disabled."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            # Mock should not be called when memory is disabled
            mock_config_manager = Mock()

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    memory_mode="NO_MEMORY",
                    non_interactive=True,
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.memory.mode == "NO_MEMORY"
                # Memory prompt should not be called when NO_MEMORY is explicitly set
                mock_config_manager.prompt_memory_selection.assert_not_called()

        finally:
            os.chdir(original_cwd)

    def test_configure_non_interactive_stm_and_ltm(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test non-interactive mode with STM_AND_LTM memory mode."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    memory_mode="STM_AND_LTM",
                    non_interactive=True,
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.memory.mode == "STM_AND_LTM"
                assert agent_config.memory.event_expiry_days == 30
                assert agent_config.memory.memory_name == "test_agent_memory"

        finally:
            os.chdir(original_cwd)

    def test_configure_interactive_use_existing_memory(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test interactive mode selecting existing memory."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            # User selects existing memory
            mock_config_manager.prompt_memory_selection.return_value = ("USE_EXISTING", "existing-memory-123")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    memory_mode="STM_ONLY",
                    non_interactive=False,  # Interactive mode
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.memory.memory_id == "existing-memory-123"
                assert agent_config.memory.mode == "STM_AND_LTM"

        finally:
            os.chdir(original_cwd)

    def test_configure_interactive_skip_memory(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test interactive mode where user skips memory setup."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            # User skips memory setup
            mock_config_manager.prompt_memory_selection.return_value = ("SKIP", None)

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    non_interactive=False,
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.memory.mode == "NO_MEMORY"

        finally:
            os.chdir(original_cwd)


class TestSourcePathConfiguration:
    """Test configuration with source_path parameter."""

    def test_configure_with_source_path(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with custom source path."""
        # Create source directory structure
        source_dir = tmp_path / "custom_source"
        source_dir.mkdir()
        agent_file = source_dir / "agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    source_path=str(source_dir),
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.source_path == str(source_dir.resolve())

        finally:
            os.chdir(original_cwd)


class TestHelperFunctions:
    """Test helper functions like get_relative_path, detect_entrypoint, infer_agent_name."""

    def test_get_relative_path_with_whitespace_path(self):
        """Test get_relative_path with whitespace-only path raises ValueError."""

        # Create a mock Path object that returns whitespace when converted to string
        class WhitespacePath:
            def __str__(self):
                return "   "

        with pytest.raises(ValueError, match="Path cannot be empty"):
            get_relative_path(WhitespacePath())

    def test_get_relative_path_outside_base(self, tmp_path):
        """Test get_relative_path with path outside base directory."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        outside_path = tmp_path / "outside" / "file.py"
        outside_path.parent.mkdir()
        outside_path.write_text("# test")

        # Should return full path when outside base
        result = get_relative_path(outside_path, base_dir)
        assert str(outside_path) in result

    def test_get_relative_path_normal_case(self, tmp_path):
        """Test get_relative_path with normal relative path."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        sub_dir = base_dir / "subdir"
        sub_dir.mkdir()
        file_path = sub_dir / "file.py"
        file_path.write_text("# test")

        result = get_relative_path(file_path, base_dir)
        # Should return relative path from base
        assert "subdir" in result
        assert "file.py" in result
        assert str(base_dir) not in result  # Should not contain base path

    def test_detect_entrypoint_not_found(self, tmp_path):
        """Test detect_entrypoint when no entrypoint file exists."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = detect_entrypoint(empty_dir)
        assert result == []

    def test_detect_entrypoint_finds_agent_py(self, tmp_path):
        """Test detect_entrypoint finds agent.py."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        agent_file = test_dir / "agent.py"
        agent_file.write_text("# agent")

        result = detect_entrypoint(test_dir)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == agent_file

    def test_detect_entrypoint_finds_app_py(self, tmp_path):
        """Test detect_entrypoint finds app.py when agent.py doesn't exist."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        app_file = test_dir / "app.py"
        app_file.write_text("# app")

        result = detect_entrypoint(test_dir)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == app_file

    def test_detect_entrypoint_finds_main_py(self, tmp_path):
        """Test detect_entrypoint finds main.py when agent.py and app.py don't exist."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        main_file = test_dir / "main.py"
        main_file.write_text("# main")

        result = detect_entrypoint(test_dir)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == main_file

    def test_detect_entrypoint_priority_order(self, tmp_path):
        """Test detect_entrypoint returns all matching files in priority order."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create all three files
        agent_file = test_dir / "agent.py"
        agent_file.write_text("# agent")
        app_file = test_dir / "app.py"
        app_file.write_text("# app")
        main_file = test_dir / "main.py"
        main_file.write_text("# main")

        result = detect_entrypoint(test_dir)
        # Should return all three files in priority order
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == agent_file  # First in priority
        assert result[1] == app_file  # Second in priority
        assert result[2] == main_file  # Third in priority

    def test_infer_agent_name_with_py_extension(self, tmp_path):
        """Test infer_agent_name removes .py extension."""
        test_file = tmp_path / "my_agent.py"
        test_file.write_text("# test")

        name = infer_agent_name(test_file, tmp_path)
        assert name == "my_agent"
        assert ".py" not in name

    def test_infer_agent_name_with_nested_path(self, tmp_path):
        """Test infer_agent_name with nested directory structure."""
        nested_dir = tmp_path / "agents" / "writer"
        nested_dir.mkdir(parents=True)
        agent_file = nested_dir / "main.py"
        agent_file.write_text("# test")

        name = infer_agent_name(agent_file, tmp_path)
        assert "agents" in name
        assert "writer" in name
        assert "main" in name
        assert name == "agents_writer_main"

    def test_infer_agent_name_with_spaces(self, tmp_path):
        """Test infer_agent_name replaces spaces with underscores."""
        test_dir = tmp_path / "my agent"
        test_dir.mkdir()
        agent_file = test_dir / "handler.py"
        agent_file.write_text("# test")

        name = infer_agent_name(agent_file, tmp_path)
        assert " " not in name
        assert "_" in name


class TestProtocolConfiguration:
    """Test protocol configuration options."""

    def test_configure_with_mcp_protocol(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with MCP protocol."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    protocol="MCP",
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.protocol_configuration.server_protocol == "MCP"

        finally:
            os.chdir(original_cwd)

    def test_configure_with_a2a_protocol(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with A2A protocol."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            mock_config_manager = Mock()
            mock_config_manager.prompt_memory_selection.return_value = ("CREATE_NEW", "STM_ONLY")

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager",
                    return_value=mock_config_manager,
                ),
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    protocol="A2A",
                )

                # Load and verify the configuration
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(result.config_path)
                agent_config = config.get_agent_config("test_agent")

                assert agent_config.aws.protocol_configuration.server_protocol == "A2A"

        finally:
            os.chdir(original_cwd)
