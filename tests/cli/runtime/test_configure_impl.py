"""Tests for configure_impl CLI implementation."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl import configure_impl
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
)


class TestConfigureImplExistingCreateAgent:
    """Test configure_impl behavior when detecting existing create-flow agents."""

    def test_detects_existing_create_flow_agent(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that configure_impl detects and uses existing create-flow agent config."""
        # Create existing config with is_created_via_create_flow=True
        agent_schema = BedrockAgentCoreAgentSchema(
            name="my_created_agent",
            entrypoint="src/main.py",
            deployment_type="direct_code_deploy",
            runtime_type="PYTHON_3_10",
            source_path="src",
            aws=AWSConfig(
                execution_role_auto_create=True,
                s3_auto_create=True,
                region=None,
                account=None,
            ),
            is_created_via_create_flow=True,
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="my_created_agent",
            agents={"my_created_agent": agent_schema},
        )

        # Save config to tmp_path
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create the entrypoint file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "my_created_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_s3_bucket.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = agent_schema
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                # Run configure_impl - it should detect existing agent and skip prompts
                configure_impl(
                    non_interactive=True,
                    deployment_type="direct_code_deploy",
                    runtime="PYTHON_3_10",
                )

                # The agent name should be used from existing config
                # No entrypoint prompts should be triggered since is_created_via_create_flow=True

        finally:
            os.chdir(original_cwd)

    def test_existing_create_agent_skips_entrypoint_prompt(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that entrypoint prompt is skipped for create-flow agents."""
        # Create existing config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="direct_code_deploy",
            runtime_type="PYTHON_3_10",
            source_path="src",
            aws=AWSConfig(
                execution_role_auto_create=True,
                s3_auto_create=True,
            ),
            is_created_via_create_flow=True,
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
                patch("bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.prompt") as mock_prompt,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_s3_bucket.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = agent_schema
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    non_interactive=True,
                    deployment_type="direct_code_deploy",
                    runtime="PYTHON_3_10",
                )

                # Prompt should NOT be called for entrypoint since agent was created via create flow
                for call in mock_prompt.call_args_list:
                    assert "Entrypoint" not in str(call)

        finally:
            os.chdir(original_cwd)

    def test_existing_create_agent_blocks_deployment_type_change(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that deployment type cannot be changed for existing agents (requires destroy first)."""
        # Create config with direct_code_deploy
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="direct_code_deploy",
            runtime_type="PYTHON_3_10",
            source_path="src",
            aws=AWSConfig(
                execution_role_auto_create=True,
                s3_auto_create=True,
            ),
            is_created_via_create_flow=True,
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = agent_schema
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                # Change to container deployment - should be blocked
                with pytest.raises(typer.Exit):
                    configure_impl(
                        non_interactive=True,
                        deployment_type="container",
                    )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplVPCValidation:
    """Test VPC validation in configure_impl."""

    def test_vpc_requires_subnets_and_security_groups(self, tmp_path):
        """Test that VPC mode requires both subnets and security groups."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    vpc=True,
                    subnets="subnet-abc123def456",
                    security_groups=None,  # Missing security groups
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)

    def test_vpc_validates_subnet_format(self, tmp_path):
        """Test that subnet IDs are validated for proper format."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    vpc=True,
                    subnets="invalid-subnet",  # Invalid format
                    security_groups="sg-abc123xyz789",
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)

    def test_vpc_validates_security_group_format(self, tmp_path):
        """Test that security group IDs are validated for proper format."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    vpc=True,
                    subnets="subnet-abc123def456",
                    security_groups="invalid-sg",  # Invalid format
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplProtocolValidation:
    """Test protocol validation in configure_impl."""

    def test_invalid_protocol_rejected(self, tmp_path):
        """Test that invalid protocols are rejected."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    protocol="INVALID",  # Invalid protocol
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplLifecycleValidation:
    """Test lifecycle configuration validation in configure_impl."""

    def test_idle_timeout_must_be_less_than_max_lifetime(self, tmp_path):
        """Test that idle_timeout must be less than or equal to max_lifetime."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    idle_timeout=3600,  # 1 hour
                    max_lifetime=1800,  # 30 minutes - less than idle_timeout
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplAuthorizerConfig:
    """Test authorizer configuration in configure_impl."""

    def test_invalid_authorizer_json_rejected(self, tmp_path, mock_boto3_clients):
        """Test that invalid JSON in authorizer config is rejected."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    authorizer_config="not valid json",  # Invalid JSON
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplRequestHeaderAllowlist:
    """Test request header allowlist configuration in configure_impl."""

    def test_empty_request_header_allowlist_uses_default(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that empty request header allowlist uses default configuration."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_s3_bucket.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                # Empty string should use default (no allowlist)
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    request_header_allowlist="",  # Empty - uses default
                    non_interactive=True,
                )

                # Verify config was created without custom allowlist
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["test_agent"]
                # Empty string means no custom allowlist configured
                assert agent_config.request_header_configuration is None

        finally:
            os.chdir(original_cwd)


class TestConfigureImplIACProjectBlocking:
    """Test that configure is blocked for IAC-created projects."""

    def test_blocks_iac_created_projects(self, tmp_path, mock_boto3_clients):
        """Test that configure is blocked for projects created with agentcore create monorepo mode."""
        # Create config with is_agentcore_create_with_iac=True
        agent_schema = BedrockAgentCoreAgentSchema(
            name="iac_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path="src",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="iac_agent",
            is_agentcore_create_with_iac=True,
            agents={"iac_agent": agent_schema},
        )

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create the source directory and file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplBasicFlow:
    """Test basic configure_impl flow."""

    def test_configure_with_basic_options(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test basic configuration flow with minimal options."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    execution_role="TestRole",
                    non_interactive=True,
                    deployment_type="container",
                )

                # Config file should be created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

        finally:
            os.chdir(original_cwd)

    def test_configure_with_memory_disabled(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with memory explicitly disabled."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    execution_role="TestRole",
                    disable_memory=True,
                    non_interactive=True,
                    deployment_type="container",
                )

                # Verify config was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Load and verify memory is disabled
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["test_agent"]
                assert agent_config.memory.mode == "NO_MEMORY"

        finally:
            os.chdir(original_cwd)

    def test_configure_with_request_headers(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with request header allowlist."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    execution_role="TestRole",
                    request_header_allowlist="Authorization,X-Custom-Header",
                    non_interactive=True,
                    deployment_type="container",
                )

                # Verify config was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Load and verify request headers
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["test_agent"]
                assert agent_config.request_header_configuration is not None
                assert "Authorization" in agent_config.request_header_configuration["requestHeaderAllowlist"]
                assert "X-Custom-Header" in agent_config.request_header_configuration["requestHeaderAllowlist"]

        finally:
            os.chdir(original_cwd)

    def test_configure_with_oauth_authorizer(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with OAuth authorizer."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            oauth_config = {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://example.com/.well-known/openid_configuration",
                    "allowedClients": ["client1"],
                    "allowedAudience": ["aud1"],
                }
            }

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    execution_role="TestRole",
                    authorizer_config=json.dumps(oauth_config),
                    non_interactive=True,
                    deployment_type="container",
                )

                # Verify config was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Load and verify authorizer config
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["test_agent"]
                assert agent_config.authorizer_configuration is not None
                assert "customJWTAuthorizer" in agent_config.authorizer_configuration

        finally:
            os.chdir(original_cwd)


class TestConfigureImplDeploymentType:
    """Test deployment type handling in configure_impl."""

    def test_configure_with_direct_code_deploy(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test configuration with direct_code_deploy deployment type."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
                patch("shutil.which", return_value="/usr/bin/uv"),  # Mock uv availability
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "test_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_s3_bucket.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    execution_role="TestRole",
                    deployment_type="direct_code_deploy",
                    runtime="PYTHON_3_11",
                    non_interactive=True,
                )

                # Verify config was created
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                # Load and verify deployment type
                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["test_agent"]
                assert agent_config.deployment_type == "direct_code_deploy"
                assert agent_config.runtime_type == "PYTHON_3_11"

        finally:
            os.chdir(original_cwd)

    def test_configure_with_invalid_deployment_type(self, tmp_path, mock_boto3_clients):
        """Test that invalid deployment types are rejected."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        # Create requirements file
        (tmp_path / "requirements.txt").write_text("boto3>=1.0.0")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                configure_impl(
                    entrypoint=str(agent_file),
                    agent_name="test_agent",
                    deployment_type="invalid_type",
                    non_interactive=True,
                )

        finally:
            os.chdir(original_cwd)


class TestConfigureImplCreateMode:
    """Test create mode in configure_impl."""

    def test_create_mode_uses_container_deployment(
        self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that create mode uses container deployment."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:

            class MockContainerRuntimeClass:
                DEFAULT_RUNTIME = "auto"
                DEFAULT_PLATFORM = "linux/arm64"

                def __init__(self, *args, **kwargs):
                    pass

                def __new__(cls, *args, **kwargs):
                    return mock_container_runtime

            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime._configure_impl.ConfigurationManager"
                ) as mock_config_manager_class,
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ContainerRuntime",
                    MockContainerRuntimeClass,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.configure.ConfigurationManager"
                ) as mock_ops_config_manager,
            ):
                mock_config_manager = Mock()
                mock_config_manager.prompt_agent_name.return_value = "create_agent"
                mock_config_manager.prompt_execution_role.return_value = None
                mock_config_manager.prompt_ecr_repository.return_value = (None, True)
                mock_config_manager.prompt_oauth_config.return_value = None
                mock_config_manager.prompt_request_header_allowlist.return_value = None
                mock_config_manager.existing_config = None
                mock_config_manager_class.return_value = mock_config_manager
                mock_ops_config_manager.return_value = Mock()

                configure_impl(
                    create=True,  # Create mode
                    non_interactive=True,
                )

                # In create mode, deployment type should be container
                config_path = tmp_path / ".bedrock_agentcore.yaml"
                assert config_path.exists()

                from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

                config = load_config(config_path)
                agent_config = config.agents["create_agent"]
                assert agent_config.deployment_type == "container"

        finally:
            os.chdir(original_cwd)
