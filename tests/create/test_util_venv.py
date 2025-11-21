"""Unit tests for post_generate_venv utility module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.progress.progress_sink import ProgressSink
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util.subprocess import (
    _has_uv,
    _run,
    _run_quiet,
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


class TestRun:
    """Tests for _run function."""

    def test_run_calls_subprocess(self, tmp_path):
        """Test that _run calls subprocess.run with correct arguments."""
        with patch("subprocess.run") as mock_run:
            _run(["echo", "test"], tmp_path)
            mock_run.assert_called_once_with(["echo", "test"], cwd=str(tmp_path), check=True)

    def test_run_raises_on_failure(self, tmp_path):
        """Test that _run raises CalledProcessError on command failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["false"])
            with pytest.raises(subprocess.CalledProcessError):
                _run(["false"], tmp_path)


class TestRunQuiet:
    """Tests for _run_quiet function."""

    def test_run_quiet_success(self, tmp_path):
        """Test _run_quiet completes silently on success."""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["output line\n"])
            mock_proc.returncode = 0
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            # Should not raise
            _run_quiet(["echo", "test"], tmp_path)

    def test_run_quiet_failure_prints_output(self, tmp_path, capsys):
        """Test _run_quiet prints captured output on failure."""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["error: something went wrong\n"])
            mock_proc.returncode = 1
            mock_proc.wait.return_value = 1
            mock_popen.return_value = mock_proc

            with pytest.raises(subprocess.CalledProcessError):
                _run_quiet(["failing-cmd"], tmp_path)

            captured = capsys.readouterr()
            assert "command failed" in captured.out
            assert "failing-cmd" in captured.out
            assert "error: something went wrong" in captured.out

    def test_run_quiet_captures_multiple_lines(self, tmp_path, capsys):
        """Test _run_quiet captures all output lines on failure."""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout = iter(["line 1\n", "line 2\n", "line 3\n"])
            mock_proc.returncode = 1
            mock_proc.wait.return_value = 1
            mock_popen.return_value = mock_proc

            with pytest.raises(subprocess.CalledProcessError):
                _run_quiet(["cmd"], tmp_path)

            captured = capsys.readouterr()
            assert "line 1" in captured.out
            assert "line 2" in captured.out
            assert "line 3" in captured.out
