from __future__ import annotations
import tempfile
from pathlib import Path

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
}

EXCLUDED_FILES = {
    ".DS_Store",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


TEMP_DIR = Path(tempfile.gettempdir()).resolve()


def snapshot_dir_tree(path: Path) -> dict:
    """
    Produce a deterministic, sanitized snapshot representation of the directory.
    """
    path = path.resolve()
    snapshot = {}

    for p in sorted(path.rglob("*")):
        rel = p.relative_to(path)

        # Skip junk dirs/files
        if set(rel.parts) & EXCLUDED_DIRS:
            continue
        if p.name in EXCLUDED_FILES or p.suffix in EXCLUDED_SUFFIXES:
            continue

        key = rel.as_posix()

        if p.is_dir():
            snapshot[key] = None
        else:
            content = p.read_text(encoding="utf-8", errors="replace")
            snapshot[key] = _sanitize(content, project_root=path)

    return snapshot


def _sanitize(text: str, project_root: Path) -> str:
    """
    Sanitize absolute paths for repeatable snapshots.
    """
    if not isinstance(text, str):
        return text

    # Replace project root path
    text = text.replace(str(project_root), "<PROJECT_ROOT>")

    # Replace OS-specific temp directories
    text = text.replace(str(TEMP_DIR), "<TEMP_DIR>")

    # Also sanitize Windows-specific temp forms like "C:\\Users\\...\\AppData\\Local\\Temp"
    text = text.replace(str(TEMP_DIR).replace("\\", "/"), "<TEMP_DIR>")

    return text
