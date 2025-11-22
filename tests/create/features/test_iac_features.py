"""Unit tests for IaC feature modules."""

import pytest

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    IACProvider,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.features.cdk.feature import CDKFeature
from bedrock_agentcore_starter_toolkit.create.features.terraform.feature import TerraformFeature
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext


def create_monorepo_context(tmp_path, iac_provider):
    """Helper to create a monorepo ProjectContext for testing."""
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


class TestCDKFeature:
    """Tests for CDKFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert CDKFeature.feature_dir_name == IACProvider.CDK

    def test_render_common_dir_enabled(self):
        """Test that render_common_dir is True for CDK."""
        assert CDKFeature.render_common_dir is True

    def test_before_apply_creates_cdk_directory(self, tmp_path):
        """Test that before_apply creates cdk directory."""
        ctx = create_monorepo_context(tmp_path, IACProvider.CDK)
        feature = CDKFeature()
        feature.before_apply(ctx)

        expected_iac_dir = ctx.output_dir / "cdk"
        assert expected_iac_dir.exists()
        assert expected_iac_dir.is_dir()
        assert ctx.iac_dir == expected_iac_dir

    def test_before_apply_sets_iac_dir_on_context(self, tmp_path):
        """Test that before_apply sets iac_dir on context."""
        ctx = create_monorepo_context(tmp_path, IACProvider.CDK)
        assert ctx.iac_dir is None

        feature = CDKFeature()
        feature.before_apply(ctx)

        assert ctx.iac_dir is not None
        assert ctx.iac_dir.name == "cdk"

    def test_before_apply_fails_if_dir_exists(self, tmp_path):
        """Test that before_apply fails if cdk directory already exists."""
        ctx = create_monorepo_context(tmp_path, IACProvider.CDK)

        # Pre-create the directory
        (ctx.output_dir / "cdk").mkdir()

        feature = CDKFeature()
        with pytest.raises(FileExistsError):
            feature.before_apply(ctx)


class TestTerraformFeature:
    """Tests for TerraformFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert TerraformFeature.feature_dir_name == IACProvider.TERRAFORM

    def test_before_apply_creates_terraform_directory(self, tmp_path):
        """Test that before_apply creates terraform directory."""
        ctx = create_monorepo_context(tmp_path, IACProvider.TERRAFORM)
        feature = TerraformFeature()
        feature.before_apply(ctx)

        expected_iac_dir = ctx.output_dir / "terraform"
        assert expected_iac_dir.exists()
        assert expected_iac_dir.is_dir()
        assert ctx.iac_dir == expected_iac_dir

    def test_before_apply_sets_iac_dir_on_context(self, tmp_path):
        """Test that before_apply sets iac_dir on context."""
        ctx = create_monorepo_context(tmp_path, IACProvider.TERRAFORM)
        assert ctx.iac_dir is None

        feature = TerraformFeature()
        feature.before_apply(ctx)

        assert ctx.iac_dir is not None
        assert ctx.iac_dir.name == "terraform"

    def test_before_apply_fails_if_dir_exists(self, tmp_path):
        """Test that before_apply fails if terraform directory already exists."""
        ctx = create_monorepo_context(tmp_path, IACProvider.TERRAFORM)

        # Pre-create the directory
        (ctx.output_dir / "terraform").mkdir()

        feature = TerraformFeature()
        with pytest.raises(FileExistsError):
            feature.before_apply(ctx)
