"""Unit tests for baseline_feature module."""

from bedrock_agentcore_starter_toolkit.create.baseline_feature import BaselineFeature
from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext


class TestBaselineFeature:
    """Tests for BaselineFeature class."""

    def _create_context(self, tmp_path, template_dir_selection, model_provider=ModelProvider.Bedrock):
        """Helper to create a ProjectContext for testing."""
        output_dir = tmp_path / "test-project"
        src_dir = output_dir / "src"
        return ProjectContext(
            name="testProject",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=src_dir / "main.py",
            sdk_provider="Strands",
            iac_provider="CDK" if template_dir_selection == TemplateDirSelection.MONOREPO else None,
            model_provider=model_provider,
            template_dir_selection=template_dir_selection,
            runtime_protocol=RuntimeProtocol.HTTP,
            deployment_type=DeploymentType.CONTAINER
            if template_dir_selection == TemplateDirSelection.MONOREPO
            else DeploymentType.DIRECT_CODE_DEPLOY,
            python_dependencies=[],
            iac_dir=None,
            agent_name="testProject_Agent",
        )

    def test_monorepo_dependencies(self, tmp_path):
        """Test that monorepo mode sets correct dependencies."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO)
        feature = BaselineFeature(ctx)

        expected_deps = [
            "bedrock-agentcore >= 1.0.3",
            "requests >= 2.32.5",
            "pytest >= 7.0.0",
            "pytest-asyncio >= 0.21.0",
        ]
        assert feature.python_dependencies == expected_deps

    def test_runtime_only_dependencies(self, tmp_path):
        """Test that runtime_only mode sets correct dependencies."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.RUNTIME_ONLY)
        feature = BaselineFeature(ctx)

        expected_deps = [
            "bedrock-agentcore >= 1.0.3",
            "python-dotenv >= 1.2.1",
            "pytest >= 7.0.0",
            "pytest-asyncio >= 0.21.0",
        ]
        assert feature.python_dependencies == expected_deps

    def test_before_apply_adds_dotenv_for_non_bedrock(self, tmp_path):
        """Test that before_apply adds python-dotenv for non-Bedrock providers."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO, ModelProvider.OpenAI)
        feature = BaselineFeature(ctx)

        # Initially should not have dotenv (monorepo mode)
        initial_deps = feature.python_dependencies.copy()
        assert "python-dotenv >= 1.2.1" not in initial_deps

        # After before_apply, should have dotenv
        feature.before_apply(ctx)
        assert "python-dotenv >= 1.2.1" in feature.python_dependencies

    def test_before_apply_no_dotenv_for_bedrock(self, tmp_path):
        """Test that before_apply does not add python-dotenv for Bedrock."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO, ModelProvider.Bedrock)
        feature = BaselineFeature(ctx)

        initial_count = len(feature.python_dependencies)
        feature.before_apply(ctx)

        # Should not have added any dependencies
        assert len(feature.python_dependencies) == initial_count
        # Verify dotenv not duplicated
        dotenv_count = sum(1 for d in feature.python_dependencies if "python-dotenv" in d)
        assert dotenv_count == 0

    def test_before_apply_adds_dotenv_for_anthropic(self, tmp_path):
        """Test that before_apply adds python-dotenv for Anthropic provider."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO, ModelProvider.Anthropic)
        feature = BaselineFeature(ctx)
        feature.before_apply(ctx)
        assert "python-dotenv >= 1.2.1" in feature.python_dependencies

    def test_before_apply_adds_dotenv_for_gemini(self, tmp_path):
        """Test that before_apply adds python-dotenv for Gemini provider."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO, ModelProvider.Gemini)
        feature = BaselineFeature(ctx)
        feature.before_apply(ctx)
        assert "python-dotenv >= 1.2.1" in feature.python_dependencies

    def test_template_override_dir_is_set(self, tmp_path):
        """Test that template_override_dir is set correctly."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO)
        feature = BaselineFeature(ctx)

        assert feature.template_override_dir is not None
        assert feature.template_override_dir.name == TemplateDirSelection.MONOREPO

    def test_after_apply_does_nothing(self, tmp_path):
        """Test that after_apply is a no-op."""
        ctx = self._create_context(tmp_path, TemplateDirSelection.MONOREPO)
        feature = BaselineFeature(ctx)

        # Should not raise any errors
        feature.after_apply(ctx)
