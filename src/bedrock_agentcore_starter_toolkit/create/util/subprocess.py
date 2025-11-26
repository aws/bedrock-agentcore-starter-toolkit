"""Utility to create a venv and install dependencies after generate."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - subprocess required for running uv venv setup commands
from pathlib import Path

from ...cli.common import console
from ..progress.progress_sink import ProgressSink
from ..types import ProjectContext


def create_and_init_venv(ctx: ProjectContext, sink: ProgressSink) -> None:
    """Create a venv and install dependencies if uv is present."""
    project_root = ctx.output_dir
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return

    if not _has_uv():
        sink.notification("Venv setup skipped because uv not found")
        return

    try:
        with sink.step(
            "Venv dependencies installing",
            "Venv created and installed",
        ):
            _run_quiet(["uv", "venv", ".venv"], cwd=project_root)
            _run_quiet(["uv", "sync"], cwd=project_root)
    except subprocess.CalledProcessError:
        sink.notification("Venv setup failed. Continuing")
        console.print(
            "      • Your project and venv were created successfully but dependency installation failed.\n"
            "        Run uv sync in the project directory to troubleshoot\n"
            "        More information: https://docs.astral.sh/uv/concepts/resolution/"
        )


def init_git_project(ctx: ProjectContext, sink: ProgressSink) -> None:
    """Initialize a git repo and stage files if git is present."""
    project_root = ctx.output_dir

    # Check if git is installed
    if not _has_git():
        sink.notification("Git setup skipped because git not found")
        return

    # Avoid re-initializing if .git already exists
    if (project_root / ".git").exists():
        sink.notification("Git setup skipped because .git already exists")
        return

    with sink.step(
        "Git initializing", "Git initialized", error_message="Git initialization failed. Continuing", swallow_fail=True
    ):
        _run_quiet(["git", "init"], cwd=project_root)
        _run_quiet(["git", "add", "."], cwd=project_root)
        _run_quiet(["git", "commit", "-m", "feat: initialze agentcore create project"], cwd=project_root)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_uv() -> bool:
    return shutil.which("uv") is not None


def _has_git() -> bool:
    return shutil.which("git") is not None


def _run(cmd: list[str], cwd: Path) -> None:
    """Original run method preserved as-is."""
    subprocess.run(cmd, cwd=str(cwd), check=True)  # nosec B603 - cmd args are hardcoded uv commands, not user input


def _run_quiet(cmd: list[str], cwd: Path) -> None:
    """Run a command quietly; show the full output only if it fails."""
    proc = subprocess.Popen(  # nosec B603 - cmd args are hardcoded uv commands, not user input
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )

    captured = []

    # Capture all output silently
    for line in proc.stdout:
        captured.append(line)

    proc.wait()

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)
