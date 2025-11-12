"""Unit tests for bootstrap configuration resolution."""

from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.bootstrap.configure.resolve import (
    copy_src_implementation_and_docker_config_into_monorepo,
    resolve_agent_config_with_project_context,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    MemoryConfig,
    NetworkConfiguration,
    NetworkModeConfig,
    ObservabilityConfig,
    ProtocolConfiguration,
)


class TestConfigurationResolution:
    """Tests for resolve_agent_config_with_project_context function."""

    def test_memory_config_enabled(self, sample_project_context, sample_agent_config):
        """Test that memory_enabled is applied from agent config."""
        # Arrange
        sample_agent_config.memory = MemoryConfig(
            mode="STM_ONLY",
            event_expiry_days=30,
        )

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.memory_enabled is True

    def test_memory_config_with_ltm(self, sample_project_context, sample_agent_config):
        """Test that memory with LTM enabled is applied correctly."""
        # Arrange
        sample_agent_config.memory = MemoryConfig(
            mode="STM_AND_LTM",
            event_expiry_days=60,
        )

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.memory_enabled is True
        assert sample_project_context.memory_is_long_term is True
        assert sample_project_context.memory_event_expiry_days == 60

    def test_memory_event_expiry_days(self, sample_project_context, sample_agent_config):
        """Test that memory_event_expiry_days is applied from agent config."""
        # Arrange
        sample_agent_config.memory = MemoryConfig(
            mode="STM_ONLY",
            event_expiry_days=45,
        )

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.memory_event_expiry_days == 45

    def test_memory_name_applied(self, sample_project_context, sample_agent_config):
        """Test that memory_name is applied when provided."""
        # Arrange
        sample_agent_config.memory = MemoryConfig(
            mode="STM_ONLY",
            memory_name="my-custom-memory",
            event_expiry_days=30,
        )

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.memory_name == "my-custom-memory"

    def test_observability_disabled(self, sample_project_context, sample_agent_config):
        """Test that observability_enabled is set to False when disabled in config."""
        # Arrange
        sample_agent_config.aws.observability = ObservabilityConfig(enabled=False)

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.observability_enabled is False

    def test_custom_authorizer_config_applied(self, sample_project_context, sample_agent_config):
        """Test that custom_authorizer_enabled is applied from agent config."""
        # Arrange
        sample_agent_config.authorizer_configuration = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://auth.example.com/.well-known/jwks.json",
                "allowedClients": ["client1", "client2"],
                "allowedAudience": ["audience1"],
            }
        }

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.custom_authorizer_enabled is True

    def test_custom_authorizer_fields(self, sample_project_context, sample_agent_config):
        """Test that authorizer URL, clients, and audience are applied correctly."""
        # Arrange
        sample_agent_config.authorizer_configuration = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://auth.example.com/.well-known/jwks.json",
                "allowedClients": ["client1", "client2"],
                "allowedAudience": ["audience1", "audience2"],
            }
        }

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.custom_authorizer_url == "https://auth.example.com/.well-known/jwks.json"
        assert sample_project_context.custom_authorizer_allowed_clients == ["client1", "client2"]
        assert sample_project_context.custom_authorizer_allowed_audience == ["audience1", "audience2"]

    def test_vpc_config_applied(self, sample_project_context, sample_agent_config):
        """Test that vpc_enabled is applied from agent config."""
        # Arrange
        sample_agent_config.aws.network_configuration = NetworkConfiguration(
            network_mode="VPC",
            network_mode_config=NetworkModeConfig(
                security_groups=["sg-12345"],
                subnets=["subnet-12345"],
            ),
        )

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.vpc_enabled is True

    def test_vpc_fields_applied(self, sample_project_context, sample_agent_config):
        """Test that vpc_subnets and vpc_security_groups are applied correctly."""
        # Arrange
        sample_agent_config.aws.network_configuration = NetworkConfiguration(
            network_mode="VPC",
            network_mode_config=NetworkModeConfig(
                security_groups=["sg-12345", "sg-67890"],
                subnets=["subnet-12345", "subnet-67890", "subnet-abcde"],
            ),
        )

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.vpc_subnets == ["subnet-12345", "subnet-67890", "subnet-abcde"]
        assert sample_project_context.vpc_security_groups == ["sg-12345", "sg-67890"]

    def test_mcp_protocol_sets_template_dir(self, sample_project_context, sample_agent_config):
        """Test that MCP protocol sets template_dir_selection to MCP_RUNTIME."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="MCP")

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.template_dir_selection == "mcp_runtime"

    def test_mcp_protocol_clears_sdk(self, sample_project_context, sample_agent_config):
        """Test that MCP protocol sets sdk_provider to None."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="MCP")
        sample_agent_config.entrypoint = "."  # Set to "." so sdk_provider isn't cleared by entrypoint check
        sample_project_context.sdk_provider = "Strands"  # Start with an SDK provider

        # Act
        with patch("bedrock_agentcore_starter_toolkit.bootstrap.configure.resolve._handle_warn") as mock_warn:
            resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.sdk_provider is None
        mock_warn.assert_called_once_with("In MCP mode, SDK code is not generated")

    def test_a2a_protocol_sets_src_provided(self, sample_project_context, sample_agent_config):
        """Test that A2A protocol sets src_implementation_provided to True."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="A2A")
        sample_agent_config.entrypoint = "."  # Set to "." so src_implementation_provided isn't set by entrypoint check
        sample_project_context.src_implementation_provided = False

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.src_implementation_provided is True

    def test_a2a_protocol_clears_sdk(self, sample_project_context, sample_agent_config):
        """Test that A2A protocol sets sdk_provider to None."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="A2A")
        sample_agent_config.entrypoint = "."  # Set to "." so sdk_provider isn't cleared by entrypoint check
        sample_project_context.sdk_provider = "Strands"  # Start with an SDK provider

        # Act
        with patch("bedrock_agentcore_starter_toolkit.bootstrap.configure.resolve._handle_warn") as mock_warn:
            resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.sdk_provider is None
        mock_warn.assert_called_once_with("In A2A mode, source code is not generated")

    def test_a2a_protocol_template_dir(self, sample_project_context, sample_agent_config):
        """Test that A2A protocol sets template_dir_selection to DEFAULT."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="A2A")

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.template_dir_selection == "default"

    def test_http_protocol_keeps_defaults(self, sample_project_context, sample_agent_config):
        """Test that HTTP protocol keeps default template_dir_selection."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="HTTP")
        initial_template_dir = sample_project_context.template_dir_selection

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        # HTTP protocol should not change template_dir_selection or sdk_provider (unless entrypoint changes them)
        # Since entrypoint is "src/main.py" (not "."), sdk_provider will be None due to entrypoint check
        assert sample_project_context.template_dir_selection == initial_template_dir
        # sdk_provider is None because entrypoint != "."
        assert sample_project_context.sdk_provider is None

    def test_mcp_protocol_with_no_sdk(self, sample_project_context, sample_agent_config):
        """Test that MCP protocol doesn't warn when sdk_provider is already None."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="MCP")
        sample_agent_config.entrypoint = "."  # Set to "." so sdk_provider isn't cleared by entrypoint check
        sample_project_context.sdk_provider = None  # Already None

        # Act
        with patch("bedrock_agentcore_starter_toolkit.bootstrap.configure.resolve._handle_warn") as mock_warn:
            resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.template_dir_selection == "mcp_runtime"
        assert sample_project_context.sdk_provider is None
        # Should not warn when sdk_provider is already None
        mock_warn.assert_not_called()

    def test_a2a_protocol_with_no_sdk(self, sample_project_context, sample_agent_config):
        """Test that A2A protocol doesn't warn when sdk_provider is already None."""
        # Arrange
        sample_agent_config.aws.protocol_configuration = ProtocolConfiguration(server_protocol="A2A")
        sample_agent_config.entrypoint = "."  # Set to "." so sdk_provider isn't cleared by entrypoint check
        sample_project_context.sdk_provider = None  # Already None

        # Act
        with patch("bedrock_agentcore_starter_toolkit.bootstrap.configure.resolve._handle_warn") as mock_warn:
            resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.template_dir_selection == "default"
        assert sample_project_context.sdk_provider is None
        assert sample_project_context.src_implementation_provided is True
        # Should not warn when sdk_provider is already None
        mock_warn.assert_not_called()

    def test_vpc_not_enabled_when_public(self, sample_project_context, sample_agent_config):
        """Test that vpc_enabled remains False when network_mode is PUBLIC."""
        # Arrange
        sample_agent_config.aws.network_configuration = NetworkConfiguration(
            network_mode="PUBLIC",
        )
        sample_project_context.vpc_enabled = False

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.vpc_enabled is False
        assert sample_project_context.vpc_subnets is None
        assert sample_project_context.vpc_security_groups is None

    def test_request_header_allowlist_terraform(self, sample_project_context, sample_agent_config):
        """Test that request header allowlist is applied for Terraform."""
        # Arrange
        sample_project_context.iac_provider = "Terraform"
        sample_agent_config.request_header_configuration = {
            "requestHeaderAllowlist": ["X-Custom-Header", "X-Another-Header"]
        }

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.request_header_allowlist == ["X-Custom-Header", "X-Another-Header"]

    def test_request_header_allowlist_cdk_warning(self, sample_project_context, sample_agent_config):
        """Test that request header allowlist triggers warning for CDK."""
        # Arrange
        sample_project_context.iac_provider = "CDK"
        sample_agent_config.request_header_configuration = {"requestHeaderAllowlist": ["X-Custom-Header"]}

        # Act
        with patch("bedrock_agentcore_starter_toolkit.bootstrap.configure.resolve._handle_warn") as mock_warn:
            resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        mock_warn.assert_called_once_with(
            "Request header allowlist is not supported by CDK so it won't be included in the generated code"
        )
        # request_header_allowlist should remain None for CDK
        assert sample_project_context.request_header_allowlist is None

    def test_entrypoint_not_dot_sets_src_provided(self, sample_project_context, sample_agent_config):
        """Test that entrypoint not equal to '.' sets src_implementation_provided to True."""
        # Arrange
        sample_project_context.src_implementation_provided = False
        sample_project_context.sdk_provider = "Strands"
        sample_agent_config.entrypoint = "src/main.py"  # Not "."

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.src_implementation_provided is True
        assert sample_project_context.sdk_provider is None
        assert sample_project_context.entrypoint_path == "src/main.py"

    def test_entrypoint_dot_keeps_default(self, sample_project_context, sample_agent_config):
        """Test that entrypoint equal to '.' keeps src_implementation_provided as False."""
        # Arrange
        sample_project_context.src_implementation_provided = False
        sample_project_context.sdk_provider = "Strands"
        sample_agent_config.entrypoint = "."  # Indicates bootstrap should provide source

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        # src_implementation_provided should remain False when entrypoint is "."
        assert sample_project_context.src_implementation_provided is False
        # sdk_provider should remain as is (not cleared by entrypoint check)
        assert sample_project_context.sdk_provider == "Strands"

    def test_memory_name_not_set_when_none(self, sample_project_context, sample_agent_config):
        """Test that memory_name is not set when None in config."""
        # Arrange
        sample_agent_config.memory = MemoryConfig(
            mode="STM_ONLY",
            memory_name=None,
            event_expiry_days=30,
        )
        sample_project_context.memory_name = "existing-name"

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        # memory_name should remain unchanged when config has None
        assert sample_project_context.memory_name == "existing-name"

    def test_custom_authorizer_without_audience(self, sample_project_context, sample_agent_config):
        """Test that custom authorizer works without allowedAudience field."""
        # Arrange
        sample_agent_config.authorizer_configuration = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://auth.example.com/.well-known/jwks.json",
                "allowedClients": ["client1"],
                # No allowedAudience field
            }
        }

        # Act
        resolve_agent_config_with_project_context(sample_project_context, sample_agent_config)

        # Assert
        assert sample_project_context.custom_authorizer_enabled is True
        assert sample_project_context.custom_authorizer_allowed_audience == []


class TestSourceCodeCopying:
    """Tests for copy_src_implementation_and_docker_config_into_monorepo function."""

    def test_absolute_source_path(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that absolute source_path is handled correctly."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create .dockerignore in source directory
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Create Dockerfile in .bedrock_agentcore/agent_name
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")

        # Set up context with absolute path
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir.resolve())  # Absolute path

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        dockerignore_dst = src_dir / ".dockerignore"
        assert dockerignore_dst.exists()
        assert dockerignore_dst.read_text() == "*.pyc"

    def test_skips_reserved_directories(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that reserved directories (.bedrock_agentcore, project_name) are skipped."""
        # Arrange - create source structure with reserved directories
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create regular directory that should be copied
        regular_dir = source_dir / "lib"
        regular_dir.mkdir()
        (regular_dir / "helper.py").write_text("# helper")

        # Create reserved directories that should be skipped
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        (bedrock_dir / "config.yaml").write_text("# config")

        project_dir = source_dir / "test-project"
        project_dir.mkdir()
        (project_dir / "file.py").write_text("# file")

        # Create Dockerfile in .bedrock_agentcore/agent_name
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")

        # Create .dockerignore
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        # Regular directory should be copied
        assert (src_dir / "lib" / "helper.py").exists()

        # Reserved directories should NOT be copied
        assert not (src_dir / ".bedrock_agentcore").exists()
        assert not (src_dir / "test-project").exists()

        # Dockerfile and .dockerignore should be copied
        assert (src_dir / "Dockerfile").exists()
        assert (src_dir / ".dockerignore").exists()

    def test_skips_reserved_files(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that reserved files (.bedrock_agentcore.yaml, .bedrock_agentcore.YAML) are skipped."""
        # Arrange - create source structure with reserved files
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create regular files that should be copied
        (source_dir / "main.py").write_text("# main")
        (source_dir / "utils.py").write_text("# utils")

        # Create reserved files that should be skipped
        (source_dir / ".bedrock_agentcore.yaml").write_text("# reserved yaml")
        (source_dir / ".bedrock_agentcore.YAML").write_text("# reserved YAML")

        # Create Dockerfile in .bedrock_agentcore/agent_name
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")

        # Create .dockerignore
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        # Regular files should be copied
        assert (src_dir / "main.py").exists()
        assert (src_dir / "utils.py").exists()

        # Reserved files should NOT be copied
        assert not (src_dir / ".bedrock_agentcore.yaml").exists()
        assert not (src_dir / ".bedrock_agentcore.YAML").exists()

        # Dockerfile and .dockerignore should be copied
        assert (src_dir / "Dockerfile").exists()
        assert (src_dir / ".dockerignore").exists()

    def test_copies_dockerfile_from_bedrock_dir(
        self, sample_project_context, sample_agent_config, tmp_path, monkeypatch
    ):
        """Test that Dockerfile is copied from .bedrock_agentcore/agent_name directory."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create Dockerfile in .bedrock_agentcore/agent_name
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        dockerfile_content = "FROM python:3.11\nRUN pip install boto3"
        (agent_dir / "Dockerfile").write_text(dockerfile_content)

        # Create .dockerignore
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        dockerfile_dst = src_dir / "Dockerfile"
        assert dockerfile_dst.exists()
        assert dockerfile_dst.read_text() == dockerfile_content

    def test_copies_dockerignore_from_source(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that .dockerignore is copied from source_path directory."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create .dockerignore in source directory
        dockerignore_content = "*.pyc\n__pycache__/\n.git/"
        (source_dir / ".dockerignore").write_text(dockerignore_content)

        # Create Dockerfile in .bedrock_agentcore/agent_name
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        dockerignore_dst = src_dir / ".dockerignore"
        assert dockerignore_dst.exists()
        assert dockerignore_dst.read_text() == dockerignore_content

    def test_preserves_directory_structure(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that directory structure is preserved when copying."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create directory structure
        lib_dir = source_dir / "lib"
        lib_dir.mkdir()
        (lib_dir / "helper.py").write_text("# helper")

        utils_dir = source_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "logger.py").write_text("# logger")

        # Create Dockerfile and .dockerignore
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        assert (src_dir / "lib" / "helper.py").exists()
        assert (src_dir / "utils" / "logger.py").exists()
        assert (src_dir / "lib" / "helper.py").read_text() == "# helper"
        assert (src_dir / "utils" / "logger.py").read_text() == "# logger"

    def test_handles_nested_directories(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that nested directories are handled correctly."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create nested directory structure
        nested_dir = source_dir / "lib" / "core" / "models"
        nested_dir.mkdir(parents=True)
        (nested_dir / "user.py").write_text("# user model")

        # Create Dockerfile and .dockerignore
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        nested_file = src_dir / "lib" / "core" / "models" / "user.py"
        assert nested_file.exists()
        assert nested_file.read_text() == "# user model"

    def test_copies_regular_files(self, sample_project_context, sample_agent_config, tmp_path, monkeypatch):
        """Test that regular files are copied correctly."""
        # Arrange
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create regular files
        (source_dir / "main.py").write_text("# main file")
        (source_dir / "config.json").write_text('{"key": "value"}')
        (source_dir / "README.md").write_text("# README")

        # Create Dockerfile and .dockerignore
        bedrock_dir = source_dir / ".bedrock_agentcore"
        bedrock_dir.mkdir()
        agent_dir = bedrock_dir / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "Dockerfile").write_text("FROM python:3.11")
        (source_dir / ".dockerignore").write_text("*.pyc")

        # Set up context
        output_dir = tmp_path / "output" / "test-project"
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True)
        sample_project_context.output_dir = output_dir
        sample_project_context.src_dir = src_dir
        sample_agent_config.source_path = str(source_dir)

        # Change to source directory
        monkeypatch.chdir(source_dir)

        # Act
        copy_src_implementation_and_docker_config_into_monorepo(sample_agent_config, sample_project_context)

        # Assert
        assert (src_dir / "main.py").exists()
        assert (src_dir / "config.json").exists()
        assert (src_dir / "README.md").exists()
        assert (src_dir / "main.py").read_text() == "# main file"
        assert (src_dir / "config.json").read_text() == '{"key": "value"}'
        assert (src_dir / "README.md").read_text() == "# README"
