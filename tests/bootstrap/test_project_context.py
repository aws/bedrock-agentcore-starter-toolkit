"""Unit tests for ProjectContext dataclass."""

from pathlib import Path

from bedrock_agentcore_starter_toolkit.bootstrap.types import ProjectContext


class TestProjectContext:
    """Tests for ProjectContext dataclass validation and methods."""

    def test_project_context_initialization(self, tmp_path):
        """Test ProjectContext initialization with all required fields."""
        # Arrange
        output_dir = tmp_path / "test-project"
        src_dir = output_dir / "src"
        entrypoint_path = src_dir / "main.py"

        # Act
        context = ProjectContext(
            name="test-project",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=entrypoint_path,
            sdk_provider="Strands",
            iac_provider="CDK",
            template_dir_selection="default",
            runtime_protocol="HTTP",
            deployment_type="container",
            python_dependencies=["bedrock-agentcore", "requests"],
            iac_dir=output_dir / "cdk",
            src_implementation_provided=False,
            agent_name="test_agent",
            memory_enabled=True,
            memory_name="test-memory",
            memory_event_expiry_days=30,
            memory_is_long_term=True,
            custom_authorizer_enabled=True,
            custom_authorizer_url="https://auth.example.com",
            custom_authorizer_allowed_clients=["client1", "client2"],
            custom_authorizer_allowed_audience=["audience1"],
            vpc_enabled=True,
            vpc_subnets=["subnet-123", "subnet-456"],
            vpc_security_groups=["sg-123"],
            request_header_allowlist=["X-Custom-Header"],
            observability_enabled=True,
        )

        # Assert
        assert context.name == "test-project"
        assert context.output_dir == output_dir
        assert context.src_dir == src_dir
        assert context.entrypoint_path == entrypoint_path
        assert context.sdk_provider == "Strands"
        assert context.iac_provider == "CDK"
        assert context.template_dir_selection == "default"
        assert context.runtime_protocol == "HTTP"
        assert context.deployment_type == "container"
        assert context.python_dependencies == ["bedrock-agentcore", "requests"]
        assert context.iac_dir == output_dir / "cdk"
        assert context.src_implementation_provided is False
        assert context.agent_name == "test_agent"
        assert context.memory_enabled is True
        assert context.memory_name == "test-memory"
        assert context.memory_event_expiry_days == 30
        assert context.memory_is_long_term is True
        assert context.custom_authorizer_enabled is True
        assert context.custom_authorizer_url == "https://auth.example.com"
        assert context.custom_authorizer_allowed_clients == ["client1", "client2"]
        assert context.custom_authorizer_allowed_audience == ["audience1"]
        assert context.vpc_enabled is True
        assert context.vpc_subnets == ["subnet-123", "subnet-456"]
        assert context.vpc_security_groups == ["sg-123"]
        assert context.request_header_allowlist == ["X-Custom-Header"]
        assert context.observability_enabled is True

    def test_project_context_dict_method(self, tmp_path):
        """Test that dict() method returns correct dictionary representation."""
        # Arrange
        output_dir = tmp_path / "test-project"
        src_dir = output_dir / "src"
        entrypoint_path = src_dir / "main.py"

        context = ProjectContext(
            name="test-project",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=entrypoint_path,
            sdk_provider="LangGraph",
            iac_provider="Terraform",
            template_dir_selection="default",
            runtime_protocol="HTTP",
            deployment_type="container",
            python_dependencies=["langgraph"],
            iac_dir=output_dir / "terraform",
            src_implementation_provided=False,
            agent_name="test_agent",
            memory_enabled=False,
            memory_name=None,
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

        # Act
        result = context.dict()

        # Assert
        assert isinstance(result, dict)
        assert result["name"] == "test-project"
        assert result["output_dir"] == output_dir
        assert result["src_dir"] == src_dir
        assert result["entrypoint_path"] == entrypoint_path
        assert result["sdk_provider"] == "LangGraph"
        assert result["iac_provider"] == "Terraform"
        assert result["template_dir_selection"] == "default"
        assert result["runtime_protocol"] == "HTTP"
        assert result["deployment_type"] == "container"
        assert result["python_dependencies"] == ["langgraph"]
        assert result["iac_dir"] == output_dir / "terraform"
        assert result["src_implementation_provided"] is False
        assert result["agent_name"] == "test_agent"
        assert result["memory_enabled"] is False
        assert result["memory_name"] is None
        assert result["memory_event_expiry_days"] == 30
        assert result["memory_is_long_term"] is False
        assert result["custom_authorizer_enabled"] is False
        assert result["custom_authorizer_url"] is None
        assert result["custom_authorizer_allowed_clients"] is None
        assert result["custom_authorizer_allowed_audience"] is None
        assert result["vpc_enabled"] is False
        assert result["vpc_subnets"] is None
        assert result["vpc_security_groups"] is None
        assert result["request_header_allowlist"] is None
        assert result["observability_enabled"] is True

    def test_project_context_with_optional_fields(self, tmp_path):
        """Test ProjectContext with optional fields set to None."""
        # Arrange
        output_dir = tmp_path / "minimal-project"
        src_dir = output_dir / "src"
        entrypoint_path = src_dir / "app.py"

        # Act
        context = ProjectContext(
            name="minimal-project",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=entrypoint_path,
            sdk_provider=None,  # Optional SDK provider
            iac_provider="CDK",
            template_dir_selection="mcp_runtime",
            runtime_protocol="MCP",
            deployment_type="container",
            python_dependencies=[],
            iac_dir=None,  # Optional IaC directory
            src_implementation_provided=True,
            agent_name=None,  # Optional agent name
            memory_enabled=False,
            memory_name=None,
            memory_event_expiry_days=None,
            memory_is_long_term=None,
            custom_authorizer_enabled=False,
            custom_authorizer_url=None,
            custom_authorizer_allowed_clients=None,
            custom_authorizer_allowed_audience=None,
            vpc_enabled=False,
            vpc_subnets=None,
            vpc_security_groups=None,
            request_header_allowlist=None,
            observability_enabled=False,
        )

        # Assert
        assert context.name == "minimal-project"
        assert context.sdk_provider is None
        assert context.iac_dir is None
        assert context.agent_name is None
        assert context.memory_name is None
        assert context.memory_event_expiry_days is None
        assert context.memory_is_long_term is None
        assert context.template_dir_selection == "mcp_runtime"
        assert context.runtime_protocol == "MCP"
        assert context.src_implementation_provided is True

    def test_project_context_path_handling(self, tmp_path):
        """Test ProjectContext correctly handles Path objects."""
        # Arrange
        output_dir = tmp_path / "path-test"
        src_dir = output_dir / "src"
        entrypoint_path = src_dir / "handler.py"
        iac_dir = output_dir / "infrastructure"

        # Act
        context = ProjectContext(
            name="path-test",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=entrypoint_path,
            sdk_provider="GoogleADK",
            iac_provider="CDK",
            template_dir_selection="default",
            runtime_protocol="A2A",
            deployment_type="container",
            python_dependencies=[],
            iac_dir=iac_dir,
            src_implementation_provided=False,
            agent_name="path_agent",
            memory_enabled=False,
            memory_name=None,
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

        # Assert - verify Path objects are preserved
        assert isinstance(context.output_dir, Path)
        assert isinstance(context.src_dir, Path)
        assert isinstance(context.entrypoint_path, Path)
        assert isinstance(context.iac_dir, Path)

        # Assert - verify path relationships
        assert context.src_dir.parent == context.output_dir
        assert context.entrypoint_path.parent == context.src_dir
        assert context.iac_dir.parent == context.output_dir

        # Assert - verify path string representations
        assert str(context.output_dir).endswith("path-test")
        assert str(context.src_dir).endswith("src")
        assert str(context.entrypoint_path).endswith("handler.py")
        assert str(context.iac_dir).endswith("infrastructure")
