"""Path related utilities for build commands."""

import os
from pathlib import Path

from .runtime.entrypoint import DependencyInfo


def is_sub_path(path: Path, parent: Path) -> bool:
    """Return True if path is within parent directory."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def expand_source_path_for_dependencies(source_dir: Path, dependency_info: DependencyInfo) -> Path:
    """Expand build context to include dependency file/directory when needed."""
    if not dependency_info or not dependency_info.resolved_path:
        return source_dir

    dependency_path = Path(dependency_info.resolved_path)
    # For pyproject installs we need the containing directory; for requirements just ensure file parent is included
    if dependency_path.is_file():
        dependency_root = dependency_path.parent
    else:
        dependency_root = dependency_path

    if is_sub_path(dependency_root, source_dir):
        return source_dir

    common_root = Path(os.path.commonpath([source_dir.resolve(), dependency_root.resolve()]))
    return common_root


def _relative_to_build_context(context_root: Path, path: Path, description: str) -> str:
    """Convert an absolute dependency path to Docker context-relative form."""
    try:
        relative = path.resolve().relative_to(context_root)
    except ValueError as exc:
        raise ValueError(f"{description} '{path}' is outside the Docker build context '{context_root}'.") from exc

    relative_str = relative.as_posix()
    return relative_str if relative_str else "."
