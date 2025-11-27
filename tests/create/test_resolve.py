"""Unit tests for create configuration resolution."""

from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.create.configure.resolve import (
    resolve_agent_config_with_project_context,
)
from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    IACProvider,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    MemoryConfig,
    NetworkConfiguration,
    NetworkModeConfig,
    ObservabilityConfig,
    ProtocolConfiguration,
)


def create_project_context(tmp_path, iac_provider=IACProvider.CDK):
    """Helper to create a ProjectContext for testing."""
    output_dir = tmp_path / "test-project"
    src_dir = output_dir / "src"

    return ProjectContext(
        name="testProject",
        output_dir=output_dir,
        src_dir=src_dir,
        entrypoint_path=src_dir / "main.py",
        sdk_provider="Strands",
        iac_provider=iac_provider,
        model_provider=ModelProvider.Bedrock,
        template_dir_selection=TemplateDirSelection.MONOREPO,
        runtime_protocol=RuntimeProtocol.HTTP,
        deployment_type=DeploymentType.CONTAINER,
        python_dependencies=[],
        iac_dir=None,
        agent_name="testProject_Agent",
        memory_enabled=True,
        memory_name="testProject_Memory",
        memory_event_expiry_days=30,
        memory_is_long_term=False,
        custom_authorizer_enabled=False,
        custom_authorizer_url=None,
        custom_authorizer_allowed_clients=None,
        custom_authorizer_allowed_audience=None,
        vpc_enabled=False,
        vpc_subnets=None,
        vpc_security_groups=None,
        request_header_allowlist=None,
        observability_enabled=True,
    )


def create_agent_config(
    entrypoint=".",
    protocol="HTTP",
    memory_enabled=True,
    memory_event_expiry_days=30,
    has_ltm=False,
    memory_name=None,
    authorizer_config=None,
    network_mode="PUBLIC",
    network_mode_config=None,
    request_header_config=None,
    observability_enabled=True,
):
    """Helper to create a BedrockAgentCoreAgentSchema for testing."""
    # Determine memory mode based on enabled and LTM settings
    if not memory_enabled:
        memory_mode = "NO_MEMORY"
    elif has_ltm:
        memory_mode = "STM_AND_LTM"
    else:
        memory_mode = "STM_ONLY"

    return BedrockAgentCoreAgentSchema(
        name="test-agent",
        entrypoint=entrypoint,
        source_path=".",
        deployment_type="container",
        aws=AWSConfig(
            region="us-west-2",
            account="123456789012",
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            network_configuration=NetworkConfiguration(
                network_mode=network_mode,
                network_mode_config=network_mode_config,
            ),
            observability=ObservabilityConfig(enabled=observability_enabled),
            protocol_configuration=ProtocolConfiguration(server_protocol=protocol),
        ),
        memory=MemoryConfig(
            mode=memory_mode,
            event_expiry_days=memory_event_expiry_days,
            memory_name=memory_name,
        ),
        authorizer_configuration=authorizer_config,
        request_header_configuration=request_header_config,
    )


class TestResolveAgentConfigWithProjectContext:
    """Tests for resolve_agent_config_with_project_context function."""

    def test_sets_agent_name(self, tmp_path):
        """Test that agent_name is set from config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config()

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.agent_name == "test-agent"

    def test_sets_runtime_protocol(self, tmp_path):
        """Test that runtime_protocol is set from config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(protocol="HTTP")

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.runtime_protocol == "HTTP"

    def test_memory_enabled(self, tmp_path):
        """Test that memory_enabled is set from config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(memory_enabled=True)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.memory_enabled is True

    def test_memory_event_expiry_days(self, tmp_path):
        """Test that memory_event_expiry_days is set from config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(memory_event_expiry_days=60)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.memory_event_expiry_days == 60

    def test_memory_is_long_term(self, tmp_path):
        """Test that memory_is_long_term is set from config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(has_ltm=True)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.memory_is_long_term is True

    def test_memory_name_set_when_provided(self, tmp_path):
        """Test that memory_name is set when provided in config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(memory_name="custom-memory")

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.memory_name == "custom-memory"

    def test_memory_name_not_set_when_none(self, tmp_path):
        """Test that memory_name is not overwritten when not in config."""
        ctx = create_project_context(tmp_path)
        original_name = ctx.memory_name
        config = create_agent_config(memory_name=None)

        resolve_agent_config_with_project_context(ctx, config)

        # Should keep the original name since config has None
        assert ctx.memory_name == original_name

    def test_custom_authorizer_enabled(self, tmp_path):
        """Test that custom authorizer is enabled when config provided."""
        ctx = create_project_context(tmp_path)
        authorizer_config = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://auth.example.com/.well-known/openid-configuration",
                "allowedClients": ["client1", "client2"],
                "allowedAudience": ["audience1"],
            }
        }
        config = create_agent_config(authorizer_config=authorizer_config)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.custom_authorizer_enabled is True
        assert ctx.custom_authorizer_url == "https://auth.example.com/.well-known/openid-configuration"
        assert ctx.custom_authorizer_allowed_clients == ["client1", "client2"]
        assert ctx.custom_authorizer_allowed_audience == ["audience1"]

    def test_custom_authorizer_without_audience(self, tmp_path):
        """Test that custom authorizer works without allowedAudience."""
        ctx = create_project_context(tmp_path)
        authorizer_config = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://auth.example.com/.well-known/openid-configuration",
                "allowedClients": ["client1"],
            }
        }
        config = create_agent_config(authorizer_config=authorizer_config)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.custom_authorizer_enabled is True
        assert ctx.custom_authorizer_allowed_audience == []

    def test_vpc_enabled_when_vpc_mode(self, tmp_path):
        """Test that VPC is enabled when network_mode is VPC."""
        ctx = create_project_context(tmp_path)
        network_mode_config = NetworkModeConfig(
            subnets=["subnet-1", "subnet-2"],
            security_groups=["sg-1", "sg-2"],
        )
        config = create_agent_config(
            network_mode="VPC",
            network_mode_config=network_mode_config,
        )

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.vpc_enabled is True
        assert ctx.vpc_subnets == ["subnet-1", "subnet-2"]
        assert ctx.vpc_security_groups == ["sg-1", "sg-2"]

    def test_vpc_not_enabled_when_public(self, tmp_path):
        """Test that VPC is not enabled when network_mode is PUBLIC."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(network_mode="PUBLIC")

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.vpc_enabled is False

    def test_request_header_allowlist_for_terraform(self, tmp_path):
        """Test that request header allowlist is set for Terraform."""
        ctx = create_project_context(tmp_path, iac_provider=IACProvider.TERRAFORM)
        request_header_config = {"requestHeaderAllowlist": ["X-Custom-Header", "Authorization"]}
        config = create_agent_config(request_header_config=request_header_config)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.request_header_allowlist == ["X-Custom-Header", "Authorization"]

    def test_request_header_allowlist_warns_for_cdk(self, tmp_path):
        """Test that request header allowlist triggers warning for CDK."""
        ctx = create_project_context(tmp_path, iac_provider=IACProvider.CDK)
        request_header_config = {"requestHeaderAllowlist": ["X-Custom-Header"]}
        config = create_agent_config(request_header_config=request_header_config)

        with patch("bedrock_agentcore_starter_toolkit.create.configure.resolve._handle_warn") as mock_warn:
            resolve_agent_config_with_project_context(ctx, config)
            mock_warn.assert_called_once()
            assert "CDK" in mock_warn.call_args[0][0]

    def test_observability_enabled(self, tmp_path):
        """Test that observability_enabled is set from config."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(observability_enabled=True)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.observability_enabled is True

    def test_observability_disabled(self, tmp_path):
        """Test that observability_enabled can be disabled."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(observability_enabled=False)

        resolve_agent_config_with_project_context(ctx, config)

        assert ctx.observability_enabled is False

    def test_invalid_entrypoint_errors(self, tmp_path):
        """Test that non-'.' entrypoint triggers error."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(entrypoint="src/main.py")

        with patch("bedrock_agentcore_starter_toolkit.create.configure.resolve._handle_error") as mock_error:
            resolve_agent_config_with_project_context(ctx, config)
            mock_error.assert_called_once()
            assert "existing source code" in mock_error.call_args[0][0]

    def test_non_http_protocol_errors(self, tmp_path):
        """Test that non-HTTP protocol triggers error."""
        ctx = create_project_context(tmp_path)
        config = create_agent_config(protocol="MCP")

        with patch("bedrock_agentcore_starter_toolkit.create.configure.resolve._handle_error") as mock_error:
            resolve_agent_config_with_project_context(ctx, config)
            mock_error.assert_called_once()
            assert "HTTP" in mock_error.call_args[0][0]
