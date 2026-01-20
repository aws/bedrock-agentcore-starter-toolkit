"""Bedrock AgentCore utility functions for parsing and importing Bedrock AgentCore applications."""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, Tuple

log = logging.getLogger(__name__)

# Entrypoint candidates by language
PYTHON_ENTRYPOINT_CANDIDATES = ["agent.py", "app.py", "main.py", "__main__.py"]
TYPESCRIPT_ENTRYPOINT_CANDIDATES = [
    "src/index.ts",
    "index.ts",
    "src/agent.ts",
    "agent.ts",
    "src/main.ts",
    "main.ts",
    "src/app.ts",
    "app.ts",
]


def detect_entrypoint_by_language(source_dir: Path, language: str) -> List[Path]:
    """Detect entrypoint files based on project language.

    Args:
        source_dir: Directory to search for entrypoint
        language: Project language ("python" or "typescript")

    Returns:
        List of detected entrypoint files (empty list if none found)
    """
    if language == "typescript":
        candidates = TYPESCRIPT_ENTRYPOINT_CANDIDATES
    else:
        candidates = PYTHON_ENTRYPOINT_CANDIDATES

    found_files = []
    for candidate in candidates:
        candidate_path = source_dir / candidate
        if candidate_path.exists():
            found_files.append(candidate_path)
            log.debug("Detected entrypoint: %s", candidate_path)
            if language == "typescript":
                break  # TypeScript uses first match only

    if not found_files:
        log.debug("No entrypoint found in %s", source_dir)

    return found_files


def detect_language(project_dir: Path) -> Literal["python", "typescript"]:
    """Auto-detect project language based on dependency files.

    Args:
        project_dir: Path to the project directory

    Returns:
        "typescript" if package.json and tsconfig.json exist, otherwise "python"
    """
    # Check for both package.json and tsconfig.json to distinguish TypeScript from vanilla JS
    has_package_json = (project_dir / "package.json").exists()
    has_tsconfig = (project_dir / "tsconfig.json").exists()
    
    if has_package_json and has_tsconfig:
        return "typescript"
    return "python"


def detect_typescript_project(project_dir: Path) -> Optional["TypeScriptProjectInfo"]:
    """Parse package.json and extract TypeScript project information.

    Args:
        project_dir: Path to the project directory

    Returns:
        TypeScriptProjectInfo if package.json exists, None otherwise
    """
    package_json_path = project_dir / "package.json"
    if not package_json_path.exists():
        return None

    try:
        with open(package_json_path) as f:
            pkg = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to parse package.json: %s", e)
        return None

    # Parse Node.js version from engines.node (e.g., ">=20.0.0" -> "20")
    node_constraint = pkg.get("engines", {}).get("node", "")
    match = re.search(r"(\d+)", node_constraint)
    node_version = match.group(1) if match else "20"

    # Check for build script
    has_build_script = "build" in pkg.get("scripts", {})

    return TypeScriptProjectInfo(
        package_json_path=str(package_json_path),
        node_version=node_version,
        has_build_script=has_build_script,
    )


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


@dataclass
class TypeScriptProjectInfo:
    """Information about a TypeScript project extracted from package.json."""

    package_json_path: Optional[str] = None
    node_version: str = "20"
    has_build_script: bool = False

    @property
    def found(self) -> bool:
        """Whether package.json was found."""
        return self.package_json_path is not None


def detect_dependencies(package_dir: Path, explicit_file: Optional[str] = None) -> DependencyInfo:
    """Detect dependency file, with optional explicit override."""
    if explicit_file:
        return _handle_explicit_file(package_dir, explicit_file)

    project_root = Path.cwd().resolve()
    package_dir = package_dir.resolve()

    # Priority 1: Check entrypoint directory first (agent-specific requirements)
    for filename in ["requirements.txt", "pyproject.toml"]:
        file_path = package_dir / filename
        if file_path.exists():
            try:
                relative_path = file_path.relative_to(project_root)
                file_type = "requirements" if filename.endswith(".txt") else "pyproject"
                install_path = "." if file_type == "pyproject" and len(relative_path.parts) == 1 else None
                return DependencyInfo(
                    file=relative_path.as_posix(),
                    type=file_type,
                    resolved_path=str(file_path),
                    install_path=install_path,
                )
            except ValueError:
                continue  # Skip files outside project root

    # Priority 2: Check project root (shared requirements for multi-agent projects)
    for filename in ["requirements.txt", "pyproject.toml"]:
        file_path = project_root / filename
        if file_path.exists():
            file_type = "requirements" if filename.endswith(".txt") else "pyproject"
            install_path = "." if file_type == "pyproject" else None
            return DependencyInfo(
                file=filename, type=file_type, resolved_path=str(file_path), install_path=install_path
            )

    return DependencyInfo(file=None, type="notfound")


def _handle_explicit_file(package_dir: Path, explicit_file: str) -> DependencyInfo:
    """Handle explicitly provided dependency file."""
    project_root = Path.cwd().resolve()

    # Handle both absolute and relative paths
    explicit_path = Path(explicit_file)
    if not explicit_path.is_absolute():
        explicit_path = project_root / explicit_path

    # Resolve the path to handle .. and . components
    explicit_path = explicit_path.resolve()

    if not explicit_path.exists():
        raise FileNotFoundError(f"Specified requirements file not found: {explicit_path}")

    # Ensure file is within project directory for Docker context
    try:
        relative_path = explicit_path.relative_to(project_root)
    except ValueError:
        raise ValueError(
            f"Requirements file must be within project directory. File: {explicit_path}, Project: {project_root}"
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


@dataclass
class RuntimeEntrypointInfo:
    """Runtime entrypoint information for codeConfiguration API."""

    file_path: Path  # Absolute path to entrypoint file
    module_name: str  # Python module name (e.g., "agent" or "src.agent")
    handler_name: str  # Handler function name (e.g., "app")


def parse_entrypoint_for_runtime(entrypoint: str, source_dir: Optional[Path] = None) -> RuntimeEntrypointInfo:
    """Parse entrypoint for Runtime codeConfiguration API.

    Supported formats:
        "agent.py" → module="agent", handler="app" (default)
        "agent.py:handler" → module="agent", handler="handler"
        "src/agent.py:my_app" → module="src.agent", handler="my_app"

    Args:
        entrypoint: Entrypoint specification
        source_dir: Source directory for relative path resolution

    Returns:
        RuntimeEntrypointInfo with module and handler

    Raises:
        ValueError: If entrypoint format is invalid or file doesn't exist
    """
    # Split on ":" to separate file and handler
    if ":" in entrypoint:
        file_part, handler = entrypoint.split(":", 1)
    else:
        file_part = entrypoint
        handler = "app"  # Default handler name

    # Parse file path
    file_path = Path(file_part)

    # Resolve to absolute path
    if not file_path.is_absolute():
        if source_dir:
            file_path = source_dir / file_path
        file_path = file_path.resolve()

    if not file_path.exists():
        raise ValueError(f"Entrypoint file not found: {file_path}")

    # Convert file path to module name
    # Example: "src/agent.py" → "src.agent"
    if source_dir:
        try:
            relative = file_path.relative_to(source_dir.resolve())
        except ValueError:
            # File is not under source_dir, use just the filename
            relative = file_path
    else:
        relative = file_path

    # Convert to module name: remove .py and replace path separators with dots
    module = str(relative.with_suffix("")).replace(os.sep, ".")

    log.info("Parsed entrypoint: module=%s, handler=%s", module, handler)

    return RuntimeEntrypointInfo(file_path=file_path, module_name=module, handler_name=handler)


def build_entrypoint_array(entrypoint_path: str, has_otel_distro: bool, observability_enabled: bool) -> List[str]:
    """Build entrypoint array for Runtime codeConfiguration API.

    Args:
        entrypoint_path: Path to entrypoint file (e.g., "agent.py")
        has_otel_distro: Whether aws-opentelemetry-distro is installed
        observability_enabled: Whether observability is enabled in config

    Returns:
        List of entrypoint arguments for Runtime API
        - With OpenTelemetry: ["opentelemetry-instrument", "agent.py"]
        - Without: ["agent.py"]
    """
    if has_otel_distro and observability_enabled:
        return ["opentelemetry-instrument", entrypoint_path]
    return [entrypoint_path]
