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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
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

    def test_configure_with_request_header_configuration(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with request_header_configuration parameter."""
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                # Test with request header configuration
                request_header_config = {
                    "requestHeaderAllowlist": ["Authorization", "X-Custom-Header", "X-Test-Header"]
                }

                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    container_runtime="docker",
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
                    "Authorization", "X-Custom-Header", "X-Test-Header"
                ]

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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                # Mock the logger to capture verbose logging
                with patch("bedrock_agentcore_starter_toolkit.operations.runtime.configure.log") as mock_log:
                    request_header_config = {
                        "requestHeaderAllowlist": ["Authorization", "X-Verbose-Test-Header"]
                    }

                    result = configure_bedrock_agentcore(
                        agent_name="test_agent",
                        entrypoint_path=agent_file,
                        execution_role="TestRole",
                        request_header_configuration=request_header_config,
                        verbose=True,  # Enable verbose mode
                    )

                    # Verify result structure is correct
                    assert result.runtime == "Docker"

                    # Verify that verbose logging was enabled
                    mock_log.setLevel.assert_called_with(10)  # logging.DEBUG = 10

                    # Verify that request header configuration was logged
                    debug_calls = [call for call in mock_log.debug.call_args_list]
                    assert len(debug_calls) > 0, "Expected debug log calls when verbose=True"
                    
                    # Check that request header configuration appears in one of the debug calls
                    request_header_logged = any(
                        "Request header configuration" in str(call) for call in debug_calls
                    )
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                # Test with complex nested request header configuration
                request_header_config = {
                    "requestHeaderAllowlist": [
                        "Authorization",
                        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*",
                        "Content-Type",
                        "User-Agent"
                    ],
                    "additionalSettings": {
                        "maxHeaderSize": 8192,
                        "caseSensitive": False,
                        "allowWildcards": True
                    }
                }

                result = configure_bedrock_agentcore(
                    agent_name="test_agent",
                    entrypoint_path=agent_file,
                    execution_role="TestRole",
                    request_header_configuration=request_header_config,
                )

                # Verify config file was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Load and verify the complex configuration is preserved
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config
                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")
                
                assert agent_config.request_header_configuration is not None
                assert "requestHeaderAllowlist" in agent_config.request_header_configuration
                assert len(agent_config.request_header_configuration["requestHeaderAllowlist"]) == 4
                assert "Authorization" in agent_config.request_header_configuration["requestHeaderAllowlist"]
                assert "X-Amzn-Bedrock-AgentCore-Runtime-Custom-*" in agent_config.request_header_configuration["requestHeaderAllowlist"]
                
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

            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                MockContainerRuntimeClass,
            ):
                # Test with both OAuth authorizer and request headers
                oauth_config = {
                    "customJWTAuthorizer": {
                        "discoveryUrl": "https://example.com/.well-known/openid_configuration",
                        "allowedClients": ["client1", "client2"],
                        "allowedAudience": ["aud1", "aud2"]
                    }
                }
                
                request_header_config = {
                    "requestHeaderAllowlist": ["Authorization", "X-OAuth-Token", "X-Client-ID"]
                }

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

                # Load and verify both configurations are preserved
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config
                loaded_config = load_config(config_path)
                agent_config = loaded_config.get_agent_config("test_agent")
                
                # Verify OAuth configuration
                assert agent_config.authorizer_configuration is not None
                assert "customJWTAuthorizer" in agent_config.authorizer_configuration
                assert agent_config.authorizer_configuration["customJWTAuthorizer"]["discoveryUrl"] == "https://example.com/.well-known/openid_configuration"
                
                # Verify request header configuration
                assert agent_config.request_header_configuration is not None
                assert agent_config.request_header_configuration["requestHeaderAllowlist"] == [
                    "Authorization", "X-OAuth-Token", "X-Client-ID"
                ]

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
