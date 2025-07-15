"""Tests for Bedrock AgentCore configure operation."""

from pathlib import Path
from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.operations.runtime.configure import (
    AGENT_NAME_ERROR,
    configure_bedrock_agentcore,
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                # Mock the logger to capture verbose logging
                with patch("bedrock_agentcore_starter_toolkit.operations.runtime.configure.log") as mock_log:
                    result = configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        container_runtime="docker",
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
