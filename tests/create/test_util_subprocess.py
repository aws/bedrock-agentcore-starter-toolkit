"""Unit tests for subprocess utility module."""

from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.progress.progress_sink import ProgressSink
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util.subprocess import _has_git, _has_uv, create_and_init_venv


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


class TestHasGit:
    """Tests for _has_git function."""

    def test_has_git_when_installed(self):
        """Test _has_git returns True when git is installed."""
        with patch("shutil.which", return_value="/usr/local/bin/git"):
            assert _has_git() is True

    def test_has_git_when_not_installed(self):
        """Test _has_git returns False when git is not installed."""
        with patch("shutil.which", return_value=None):
            assert _has_git() is False


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

        with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_uv", return_value=True):
            with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)
                mock_run.assert_not_called()

    def test_skips_when_no_uv(self, tmp_path):
        """Test that venv creation is skipped when uv is not installed."""
        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        # Create pyproject.toml
        (ctx.output_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_uv", return_value=False):
            with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)
                mock_run.assert_not_called()

    def test_creates_venv_and_syncs(self, tmp_path):
        """Test that venv is created and dependencies synced when conditions met."""
        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        # Create pyproject.toml
        (ctx.output_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_uv", return_value=True):
            with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet") as mock_run:
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

        with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_uv", return_value=True):
            with patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet") as mock_run:
                create_and_init_venv(ctx, sink)

                # Both calls should use output_dir as cwd
                for call in mock_run.call_args_list:
                    assert call[1]["cwd"] == ctx.output_dir


class TestInitGitProject:
    """Tests for init_git_project function."""

    def _create_context(self, tmp_path):
        output_dir = tmp_path / "test-project"
        output_dir.mkdir(parents=True, exist_ok=True)
        src_dir = output_dir / "src"
        src_dir.mkdir()

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

    @patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_git", return_value=True)
    @patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet")
    def test_initializes_git_repo(self, mock_run, mock_has_git, tmp_path):
        """Test that git init/add/commit are called when git is present."""
        from bedrock_agentcore_starter_toolkit.create.util.subprocess import init_git_project

        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        init_git_project(ctx, sink)

        # Should run exactly 3 git commands
        assert mock_run.call_count == 3

        expected_calls = [
            (["git", "init"],),
            (["git", "add", "."],),
            (["git", "commit", "-m", "feat: initialze agentcore create project"],),
        ]

        for call, expected in zip(mock_run.call_args_list, expected_calls, strict=False):
            assert call[0][0] == expected[0]
            assert call[1]["cwd"] == ctx.output_dir

    @patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_git", return_value=True)
    @patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet")
    def test_skips_if_git_dir_exists(self, mock_run, mock_has_git, tmp_path):
        """Test that initialization is skipped if .git directory already exists."""
        from bedrock_agentcore_starter_toolkit.create.util.subprocess import init_git_project

        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        # Fake an existing .git directory
        (ctx.output_dir / ".git").mkdir()

        init_git_project(ctx, sink)

        mock_run.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._has_git", return_value=False)
    @patch("bedrock_agentcore_starter_toolkit.create.util.subprocess._run_quiet")
    def test_skips_if_git_not_installed(self, mock_run, mock_has_git, tmp_path):
        """Test that initialization is skipped when git is not installed."""
        from bedrock_agentcore_starter_toolkit.create.util.subprocess import init_git_project

        ctx = self._create_context(tmp_path)
        sink = ProgressSink()

        init_git_project(ctx, sink)

        mock_run.assert_not_called()
