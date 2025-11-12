from pathlib import Path

ALLOWED_DIR_PREFIXES = {
    "src",
    "cdk",
    "terraform",
    "mcp",
}

ALLOWED_SUFFIXES = {
    ".py",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".toml",
}


def _is_allowed(p: Path, root: Path) -> bool:
    """Only accept files/dirs the project generator is responsible for."""
    rel_parts = p.relative_to(root).parts
    top = rel_parts[0]

    if top not in ALLOWED_DIR_PREFIXES:
        return False

    if p.is_dir():
        return True

    return p.suffix.lower() in ALLOWED_SUFFIXES


def snapshot_dir_tree(path: Path) -> dict:
    path = path.resolve()
    snapshot = {}

    for p in sorted(path.rglob("*")):
        if not _is_allowed(p, path):
            continue

        rel = p.relative_to(path).as_posix()

        if p.is_dir():
            snapshot[rel] = None
            continue

        content = p.read_text(encoding="utf-8", errors="replace")
        snapshot[rel] = _sanitize(content, project_root=path)

    return snapshot


def _sanitize(text: str, project_root: Path) -> str:
    return text.replace(str(project_root), "<PROJECT_ROOT>")
