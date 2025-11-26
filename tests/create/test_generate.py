"""Unit tests for generate module."""

from unittest.mock import MagicMock, patch

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.generate import (
    _apply_baseline_and_sdk_features,
    generate_project,
)
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext


class TestGenerateProject:
    """Tests for generate_project function."""

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_runtime_only_mode_creates_directories(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that runtime_only mode creates output and src directories."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        output_dir = tmp_path / "testProject"
        assert output_dir.exists()
        assert (output_dir / "src").exists()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_runtime_only_calls_write_yaml(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that runtime_only mode calls write_minimal_create_runtime_yaml."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        mock_yaml.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_runtime_only_writes_env_for_non_bedrock(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that runtime_only mode writes .env for non-Bedrock providers."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.OpenAI,
            provider_api_key="test-key",
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        mock_env.assert_called_once()
        call_args = mock_env.call_args
        assert call_args[0][1] == ModelProvider.OpenAI
        assert call_args[0][2] == "test-key"

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_runtime_only_skips_env_for_bedrock(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that runtime_only mode skips .env for Bedrock provider."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        mock_env.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_iac_generation")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_with_iac_project_yaml")
    def test_monorepo_mode_creates_directories(
        self, mock_iac_yaml, mock_iac_gen, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that monorepo mode creates output and src directories."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider="CDK",
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        output_dir = tmp_path / "testProject"
        assert output_dir.exists()
        assert (output_dir / "src").exists()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_iac_generation")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_with_iac_project_yaml")
    def test_monorepo_mode_calls_iac_generation(
        self, mock_iac_yaml, mock_iac_gen, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that monorepo mode calls _apply_iac_generation."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider="CDK",
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        mock_iac_gen.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_venv_creation_called_when_enabled(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that venv creation is called when use_venv=True."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=True,
            git_init=False,
            memory=None,
        )

        mock_venv.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_venv_creation_skipped_when_disabled(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that venv creation is skipped when use_venv=False."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        mock_venv.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._write_env_file_directly")
    def test_emit_success_message_called(
        self, mock_env, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that emit_create_completed_message is always called."""
        monkeypatch.chdir(tmp_path)

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=None,
        )

        mock_emit.assert_called_once()


class TestApplyBaselineAndSdkFeatures:
    """Tests for _apply_baseline_and_sdk_features function."""

    def _create_context(self, tmp_path, sdk_provider="Strands", model_provider=ModelProvider.Bedrock):
        """Helper to create a ProjectContext for testing."""
        output_dir = tmp_path / "test-project"
        output_dir.mkdir(parents=True, exist_ok=True)
        src_dir = output_dir / "src"
        src_dir.mkdir(exist_ok=True)

        return ProjectContext(
            name="testProject",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=src_dir / "main.py",
            sdk_provider=sdk_provider,
            iac_provider=None,
            model_provider=model_provider,
            template_dir_selection=TemplateDirSelection.RUNTIME_ONLY,
            runtime_protocol=RuntimeProtocol.HTTP,
            deployment_type=DeploymentType.DIRECT_CODE_DEPLOY,
            python_dependencies=[],
            iac_dir=None,
            agent_name="testProject_Agent",
        )

    def test_collects_baseline_dependencies(self, tmp_path):
        """Test that baseline dependencies are collected."""
        ctx = self._create_context(tmp_path, sdk_provider=None)

        with patch("bedrock_agentcore_starter_toolkit.create.generate.BaselineFeature") as MockBaseline:
            mock_instance = MagicMock()
            mock_instance.python_dependencies = ["dep1", "dep2"]
            MockBaseline.return_value = mock_instance

            _apply_baseline_and_sdk_features(ctx)

            assert "dep1" in ctx.python_dependencies
            assert "dep2" in ctx.python_dependencies

    def test_collects_sdk_dependencies(self, tmp_path):
        """Test that SDK dependencies are collected."""
        ctx = self._create_context(tmp_path)

        with patch("bedrock_agentcore_starter_toolkit.create.generate.BaselineFeature") as MockBaseline:
            mock_baseline = MagicMock()
            mock_baseline.python_dependencies = ["baseline-dep"]
            MockBaseline.return_value = mock_baseline

            mock_sdk_feature = MagicMock()
            mock_sdk_feature.python_dependencies = ["sdk-dep"]

            with patch(
                "bedrock_agentcore_starter_toolkit.create.generate.sdk_feature_registry",
                {"Strands": lambda: mock_sdk_feature},
            ):
                _apply_baseline_and_sdk_features(ctx)

            assert "baseline-dep" in ctx.python_dependencies
            assert "sdk-dep" in ctx.python_dependencies

    def test_dependencies_are_sorted(self, tmp_path):
        """Test that collected dependencies are sorted."""
        ctx = self._create_context(tmp_path, sdk_provider=None)

        with patch("bedrock_agentcore_starter_toolkit.create.generate.BaselineFeature") as MockBaseline:
            mock_baseline = MagicMock()
            mock_baseline.python_dependencies = ["zebra", "alpha"]
            MockBaseline.return_value = mock_baseline

            _apply_baseline_and_sdk_features(ctx)

            # Dependencies should be sorted
            assert ctx.python_dependencies == sorted(ctx.python_dependencies)

    def test_applies_baseline_feature(self, tmp_path):
        """Test that baseline feature apply is called."""
        ctx = self._create_context(tmp_path, sdk_provider=None)

        with patch("bedrock_agentcore_starter_toolkit.create.generate.BaselineFeature") as MockBaseline:
            mock_instance = MagicMock()
            mock_instance.python_dependencies = []
            MockBaseline.return_value = mock_instance

            _apply_baseline_and_sdk_features(ctx)

            mock_instance.apply.assert_called_once_with(ctx)

    def test_applies_sdk_feature_when_present(self, tmp_path):
        """Test that SDK feature apply is called when sdk_provider is set."""
        ctx = self._create_context(tmp_path)

        with patch("bedrock_agentcore_starter_toolkit.create.generate.BaselineFeature") as MockBaseline:
            mock_baseline = MagicMock()
            mock_baseline.python_dependencies = []
            MockBaseline.return_value = mock_baseline

            mock_sdk_feature = MagicMock()
            mock_sdk_feature.python_dependencies = []

            with patch(
                "bedrock_agentcore_starter_toolkit.create.generate.sdk_feature_registry",
                {"Strands": lambda: mock_sdk_feature},
            ):
                _apply_baseline_and_sdk_features(ctx)

            mock_sdk_feature.apply.assert_called_once_with(ctx)

    def test_no_sdk_feature_when_none(self, tmp_path):
        """Test that no SDK feature is applied when sdk_provider is None."""
        ctx = self._create_context(tmp_path, sdk_provider=None)

        with patch("bedrock_agentcore_starter_toolkit.create.generate.BaselineFeature") as MockBaseline:
            mock_baseline = MagicMock()
            mock_baseline.python_dependencies = []
            MockBaseline.return_value = mock_baseline

            mock_sdk_feature = MagicMock()

            with patch(
                "bedrock_agentcore_starter_toolkit.create.generate.sdk_feature_registry",
                {"Strands": lambda: mock_sdk_feature},
            ):
                _apply_baseline_and_sdk_features(ctx)

            mock_sdk_feature.apply.assert_not_called()
