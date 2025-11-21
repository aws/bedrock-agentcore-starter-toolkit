"""Utility to create a venv and install dependencies after generate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..progress.progress_sink import ProgressSink
from ..types import ProjectContext


def create_and_init_venv(ctx: ProjectContext, sink: ProgressSink) -> None:
    """Create a venv and install dependencies if uv is present."""
    project_root = ctx.output_dir
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return

    if not _has_uv():
        return

    # Use the new quiet runner here
    with sink.step("Venv dependencies installing", "Venv created and installed."):
        _run_quiet(["uv", "venv", ".venv"], cwd=project_root)
        _run_quiet(["uv", "sync"], cwd=project_root)


# ---------------------------------------------------------------------------
# Helpers live *after* the main function
# ---------------------------------------------------------------------------


def _has_uv() -> bool:
    return shutil.which("uv") is not None


def _run(cmd: list[str], cwd: Path) -> None:
    """Original run method preserved as-is."""
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _run_quiet(cmd: list[str], cwd: Path) -> None:
    """Run a command quietly; show the full output only if it fails."""
    proc = subprocess.Popen(
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
        print("\n----- command failed ---------------------------------\n")
        print(f"Command: {' '.join(cmd)}\n")
        print("Output:\n")
        print("".join(captured))
        print("\n-------------------------------------------------------\n")
        raise subprocess.CalledProcessError(proc.returncode, cmd)
