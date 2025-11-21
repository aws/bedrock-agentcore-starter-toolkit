"""Unit tests for YAML output generation utilities."""

import yaml

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util.create_agentcore_yaml import (
    write_minimal_create_runtime_yaml,
    write_minimal_create_with_iac_project_yaml,
)


class TestWriteMinimalCreateWithIacProjectYaml:
    """Tests for write_minimal_create_with_iac_project_yaml function."""

    def _create_iac_context(self, tmp_path):
        """Helper to create a ProjectContext for IaC testing."""
        output_dir = tmp_path / "test-project"
        output_dir.mkdir(parents=True, exist_ok=True)
        src_dir = output_dir / "src"
        src_dir.mkdir(exist_ok=True)

        return ProjectContext(
            name="testProject",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=src_dir / "main.py",
            sdk_provider="Strands",
            iac_provider="CDK",
            model_provider=ModelProvider.Bedrock,
            template_dir_selection=TemplateDirSelection.MONOREPO,
            runtime_protocol=RuntimeProtocol.HTTP,
            deployment_type=DeploymentType.CONTAINER,
            python_dependencies=[],
            iac_dir=None,
            agent_name="testProject_Agent",
        )

    def test_yaml_file_created(self, tmp_path):
        """Test that YAML file is created in the output directory."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        assert yaml_path.exists()
        assert yaml_path.name == ".bedrock_agentcore.yaml"
        assert yaml_path.parent == ctx.output_dir

    def test_yaml_includes_agent_name(self, tmp_path):
        """Test that YAML includes the agent name from ProjectContext."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert "agents" in data
        assert ctx.agent_name in data["agents"]
        assert data["agents"][ctx.agent_name]["name"] == ctx.agent_name
        assert data["default_agent"] == ctx.agent_name

    def test_yaml_includes_entrypoint(self, tmp_path):
        """Test that YAML includes the entrypoint path."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        assert "entrypoint" in agent_config
        assert agent_config["entrypoint"] == str(ctx.entrypoint_path)

    def test_yaml_includes_deployment_type(self, tmp_path):
        """Test that YAML includes the deployment type."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        assert "deployment_type" in agent_config
        assert agent_config["deployment_type"] == ctx.deployment_type

    def test_yaml_sets_create_flag(self, tmp_path):
        """Test that YAML sets is_agentcore_create_with_iac flag to True."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert "is_agentcore_create_with_iac" in data
        assert data["is_agentcore_create_with_iac"] is True

    def test_yaml_includes_source_path(self, tmp_path):
        """Test that YAML includes source_path."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        assert "source_path" in agent_config
        assert agent_config["source_path"] == str(ctx.src_dir)

    def test_yaml_includes_aws_section(self, tmp_path):
        """Test that YAML includes AWS configuration section."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        assert "aws" in agent_config
        assert agent_config["aws"]["account"] is None
        assert agent_config["aws"]["region"] is None

    def test_yaml_includes_bedrock_agentcore_section(self, tmp_path):
        """Test that YAML includes bedrock_agentcore section with null IDs."""
        ctx = self._create_iac_context(tmp_path)
        yaml_path = write_minimal_create_with_iac_project_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        assert "bedrock_agentcore" in agent_config
        assert agent_config["bedrock_agentcore"]["agent_id"] is None
        assert agent_config["bedrock_agentcore"]["agent_arn"] is None
        assert agent_config["bedrock_agentcore"]["agent_session_id"] is None


class TestWriteMinimalCreateRuntimeYaml:
    """Tests for write_minimal_create_runtime_yaml function."""

    def _create_runtime_context(self, tmp_path, model_provider=ModelProvider.Bedrock):
        """Helper to create a ProjectContext for runtime testing."""
        output_dir = tmp_path / "test-project"
        output_dir.mkdir(parents=True, exist_ok=True)
        src_dir = output_dir / "src"
        src_dir.mkdir(exist_ok=True)

        api_key_name = f"{model_provider.upper()}_API_KEY" if model_provider != ModelProvider.Bedrock else None

        return ProjectContext(
            name="testProject",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=src_dir / "main.py",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=model_provider,
            template_dir_selection=TemplateDirSelection.RUNTIME_ONLY,
            runtime_protocol=RuntimeProtocol.HTTP,
            deployment_type=DeploymentType.DIRECT_CODE_DEPLOY,
            python_dependencies=[],
            iac_dir=None,
            agent_name="testProject_Agent",
            api_key_env_var_name=api_key_name,
        )

    def test_yaml_file_created(self, tmp_path):
        """Test that YAML file is created for runtime projects."""
        ctx = self._create_runtime_context(tmp_path)
        write_minimal_create_runtime_yaml(ctx)

        yaml_path = ctx.output_dir / ".bedrock_agentcore.yaml"
        assert yaml_path.exists()
        assert yaml_path.name == ".bedrock_agentcore.yaml"

    def test_yaml_includes_agent_name(self, tmp_path):
        """Test that runtime YAML includes agent name."""
        ctx = self._create_runtime_context(tmp_path)
        write_minimal_create_runtime_yaml(ctx)

        yaml_path = ctx.output_dir / ".bedrock_agentcore.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert data["default_agent"] == ctx.agent_name
        assert ctx.agent_name in data["agents"]

    def test_yaml_includes_api_key_env_var_for_openai(self, tmp_path):
        """Test that runtime YAML includes api_key_env_var_name for OpenAI."""
        ctx = self._create_runtime_context(tmp_path, ModelProvider.OpenAI)
        write_minimal_create_runtime_yaml(ctx)

        yaml_path = ctx.output_dir / ".bedrock_agentcore.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        assert agent_config.get("api_key_env_var_name") == "OPENAI_API_KEY"

    def test_yaml_no_api_key_env_var_for_bedrock(self, tmp_path):
        """Test that runtime YAML has no api_key_env_var_name for Bedrock."""
        ctx = self._create_runtime_context(tmp_path, ModelProvider.Bedrock)
        write_minimal_create_runtime_yaml(ctx)

        yaml_path = ctx.output_dir / ".bedrock_agentcore.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        # Should be None or not present
        assert agent_config.get("api_key_env_var_name") is None

    def test_yaml_includes_aws_auto_create_settings(self, tmp_path):
        """Test that runtime YAML includes AWS auto-create settings."""
        ctx = self._create_runtime_context(tmp_path)
        write_minimal_create_runtime_yaml(ctx)

        yaml_path = ctx.output_dir / ".bedrock_agentcore.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_config = data["agents"][ctx.agent_name]
        aws_config = agent_config.get("aws", {})
        assert aws_config.get("execution_role_auto_create") is True
        assert aws_config.get("s3_auto_create") is True
