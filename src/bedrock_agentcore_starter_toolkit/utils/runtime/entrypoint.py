"""Bedrock AgentCore utility functions for parsing and importing Bedrock AgentCore applications."""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger(__name__)


def parse_entrypoint(entrypoint: str) -> Tuple[Path, str]:
    """Parse entrypoint into file path and name.

    Args:
        entrypoint: Entrypoint specification (e.g., "app.py")

    Returns:
        Tuple of (file_path, bedrock_agentcore_name)

    Raises:
        ValueError: If entrypoint cannot be parsed or file doesn't exist
    """
    file_path = Path(entrypoint).resolve()
    if not file_path.exists():
        log.error("Entrypoint file not found: %s", file_path)
        raise ValueError(f"File not found: {file_path}")

    file_name = file_path.stem

    log.info("Entrypoint parsed: file=%s, bedrock_agentcore_name=%s", file_path, file_name)
    return file_path, file_name


@dataclass
class DependencyInfo:
    """Information about project dependencies."""

    file: Optional[str]  # Relative path for Docker context
    type: str  # "requirements", "pyproject", or "notfound"
    resolved_path: Optional[str] = None  # Absolute path for validation
    install_path: Optional[str] = None  # Path for pip install command

    @property
    def found(self) -> bool:
        """Whether a dependency file was found."""
        return self.file is not None

    @property
    def is_pyproject(self) -> bool:
        """Whether this is a pyproject.toml file."""
        return self.type == "pyproject"

    @property
    def is_requirements(self) -> bool:
        """Whether this is a requirements file."""
        return self.type == "requirements"

    @property
    def is_root_package(self) -> bool:
        """Whether this dependency points to the root package."""
        return self.is_pyproject and self.install_path == "."


def detect_dependencies(package_dir: Path, explicit_file: Optional[str] = None) -> DependencyInfo:
    """Detect dependency file, with optional explicit override."""
    if explicit_file:
        return _handle_explicit_file(package_dir, explicit_file)

    # Check for requirements.txt first (prioritized for notebook workflows)
    requirements_path = package_dir / "requirements.txt"
    if requirements_path.exists():
        return DependencyInfo(
            file="requirements.txt", type="requirements", resolved_path=str(requirements_path.resolve())
        )

    # Check for pyproject.toml
    pyproject_path = package_dir / "pyproject.toml"
    if pyproject_path.exists():
        return DependencyInfo(
            file="pyproject.toml",
            type="pyproject",
            resolved_path=str(pyproject_path.resolve()),
            install_path=".",  # Install from current directory
        )

    return DependencyInfo(file=None, type="notfound")


def _handle_explicit_file(package_dir: Path, explicit_file: str) -> DependencyInfo:
    """Handle explicitly provided dependency file."""
    # Handle both absolute and relative paths
    explicit_path = Path(explicit_file)
    if not explicit_path.is_absolute():
        explicit_path = package_dir / explicit_path

    # Resolve the path to handle .. and . components
    explicit_path = explicit_path.resolve()

    if not explicit_path.exists():
        raise FileNotFoundError(f"Specified requirements file not found: {explicit_path}")

    # Ensure file is within project directory for Docker context
    try:
        relative_path = explicit_path.relative_to(package_dir.resolve())
    except ValueError:
        raise ValueError(
            f"Requirements file must be within project directory. File: {explicit_path}, Project: {package_dir}"
        ) from None

    # Determine type and install path
    file_type = "requirements" if explicit_file.endswith((".txt", ".in")) else "pyproject"
    install_path = None

    if file_type == "pyproject":
        if len(relative_path.parts) > 1:
            # pyproject.toml in subdirectory - install from that directory
            install_path = Path(relative_path).parent
        else:
            # pyproject.toml in root - install from current directory
            install_path = Path(".")

    # Get POSIX strings for file and install path
    file_path = relative_path.as_posix()
    install_path = install_path and install_path.as_posix()

    # Maintain local format for explicit path
    explicit_path = str(explicit_path)

    return DependencyInfo(file=file_path, type=file_type, resolved_path=explicit_path, install_path=install_path)


def validate_requirements_file(build_dir: Path, requirements_file: str) -> DependencyInfo:
    """Validate the provided requirements file path and return DependencyInfo."""
    # Check if the provided path exists and is a file
    file_path = Path(requirements_file)
    if not file_path.is_absolute():
        file_path = build_dir / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.is_dir():
        raise ValueError(
            f"Path is a directory, not a file: {file_path}. "
            f"Please specify a requirements file (requirements.txt, pyproject.toml, etc.)"
        )

    # Validate that it's a recognized dependency file type (flexible validation)
    if not (file_path.suffix in [".txt", ".in"] or file_path.name == "pyproject.toml"):
        raise ValueError(
            f"'{file_path.name}' is not a supported dependency file. "
            f"Supported formats: *.txt, *.in (pip requirements), or pyproject.toml"
        )

    # Use the existing detect_dependencies function to process the file
    return detect_dependencies(build_dir, explicit_file=requirements_file)


def get_python_version() -> str:
    """Get Python version for Docker image."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"
