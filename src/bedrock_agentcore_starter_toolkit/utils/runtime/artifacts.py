"""Build artifact organization utilities for enhanced configuration management."""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .schema import BuildArtifactInfo

log = logging.getLogger(__name__)


def create_build_artifact_organization(agent_name: str, source_path: Optional[str] = None) -> BuildArtifactInfo:
    """Create organized build artifact structure for an agent.

    Args:
        agent_name: Name of the agent
        source_path: Optional source path to copy

    Returns:
        BuildArtifactInfo with organized structure details
    """
    base_dir = Path(f".bedrock-agentcore/{agent_name}")
    base_dir.mkdir(parents=True, exist_ok=True)

    # Copy source files if source_path provided (flat structure, no src/ subdirectory)
    source_copy_path = None
    if source_path:
        source_path_obj = Path(source_path)
        if source_path_obj.exists() and source_path_obj.is_dir():
            # Copy source directory contents directly to base_dir
            shutil.copytree(source_path_obj, base_dir, dirs_exist_ok=True)
            source_copy_path = str(base_dir)

    # Create Dockerfile path (will be generated later)
    dockerfile_path = str(base_dir / "Dockerfile")

    return BuildArtifactInfo(
        base_directory=str(base_dir),
        source_copy_path=source_copy_path,
        dockerfile_path=dockerfile_path,
        build_timestamp=datetime.now(),
        organized=True,
    )


def cleanup_build_artifacts(agent_name: str) -> None:
    """Clean up build artifacts for an agent.

    Args:
        agent_name: Name of the agent whose artifacts to clean
    """
    base_dir = Path(f".bedrock-agentcore/{agent_name}")
    if base_dir.exists():
        try:
            shutil.rmtree(base_dir)
            log.info("Cleaned up build artifacts for agent: %s", agent_name)
        except Exception as e:
            log.warning("Failed to clean up build artifacts for %s: %s", agent_name, e)


def ensure_build_artifact_directory(agent_name: str) -> Path:
    """Ensure build artifact directory exists for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Path to the agent's build artifact directory
    """
    base_dir = Path(f".bedrock-agentcore/{agent_name}")
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_build_artifact_info(agent_name: str) -> Optional[BuildArtifactInfo]:
    """Get build artifact information for an agent if it exists.

    Args:
        agent_name: Name of the agent

    Returns:
        BuildArtifactInfo if artifacts exist, None otherwise
    """
    base_dir = Path(f".bedrock-agentcore/{agent_name}")
    if not base_dir.exists():
        return None

    dockerfile_path = base_dir / "Dockerfile"

    return BuildArtifactInfo(
        base_directory=str(base_dir),
        source_copy_path=str(base_dir),  # Flat structure: source copied directly to base_dir
        dockerfile_path=str(dockerfile_path) if dockerfile_path.exists() else None,
        build_timestamp=datetime.fromtimestamp(base_dir.stat().st_mtime),
        organized=True,
    )
