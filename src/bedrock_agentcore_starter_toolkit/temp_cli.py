"""Wrapper script for dev. Will delete."""

import sys
from pathlib import Path

# resolve the package src directory and insert into sys.path
repo_root = Path(__file__).resolve().parent
src_dir = repo_root / "src"
sys.path.insert(0, str(src_dir))

# now safely import your CLI entrypoint
from bedrock_agentcore_starter_toolkit.cli.cli import main  # noqa

if __name__ == "__main__":
    main()
