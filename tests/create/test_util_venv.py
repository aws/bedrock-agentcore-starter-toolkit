"""Unit tests for post_generate_venv utility module."""

from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.progress.progress_sink import ProgressSink
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util.post_generate_venv import (
    _has_uv,
    create_and_init_venv,
)


class TestHasUv:
    """Tests for _has_uv function."""

    def test_has_uv_when_installed(self):
        """Test _has_uv returns True when uv is installed."""
        with patch("shutil.which", return_value="/usr/local/bin/uv"):
            assert _has_uv() is True

    def test_has_uv_when_not_installed(self):
        """Test _has_uv returns False when uv is not installed."""
        with patch("shutil.which", return_value=None):
            assert _has_uv() is False


class TestCreateAndInitVenv:
    """Tests for create_and_init_venv function."""

    def _create_context(self, tmp_path):
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
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            template_dir_selection=TemplateDirSelection.RUNTIME_ONLY,
            runtime_protocol=RuntimeProtocol.HTTP,
            deployment_type=DeploymentType.DIRECT_CODE_DEPLOY,
            python_dependencies=[],
            iac_dir=None,
            agent_name="testProject_Agent",
        )

    def test_skips_when_no_pyproject(self, tmp_path):
        """Test that venv creation is skipped when pyproject.toml doesn't exist."""
        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._has_uv", return_value=True):
            with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)
                mock_run.assert_not_called()

    def test_skips_when_no_uv(self, tmp_path):
        """Test that venv creation is skipped when uv is not installed."""
        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        # Create pyproject.toml
        (ctx.output_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._has_uv", return_value=False):
            with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)
                mock_run.assert_not_called()

    def test_creates_venv_and_syncs(self, tmp_path):
        """Test that venv is created and dependencies synced when conditions met."""
        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        # Create pyproject.toml
        (ctx.output_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._has_uv", return_value=True):
            with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)

                # Should have called uv venv and uv sync
                assert mock_run.call_count == 2
                calls = mock_run.call_args_list
                assert calls[0][0][0] == ["uv", "venv", ".venv"]
                assert calls[1][0][0] == ["uv", "sync"]

    def test_passes_correct_cwd(self, tmp_path):
        """Test that commands are run in the correct directory."""
        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        # Create pyproject.toml
        (ctx.output_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._has_uv", return_value=True):
            with patch("bedrock_agentcore_starter_toolkit.create.util.post_generate_venv._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)

                # Both calls should use output_dir as cwd
                for call in mock_run.call_args_list:
                    assert call[1]["cwd"] == ctx.output_dir
