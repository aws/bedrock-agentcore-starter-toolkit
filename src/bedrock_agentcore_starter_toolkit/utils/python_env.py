"""Generic local python utilities."""

import sys

RECOMMENDED_MINOR_VERSIONS = {10}


def is_recommended_python_version() -> tuple[bool, str]:
    """Return whether the running Python version is recommended, and the version string."""
    v = sys.version_info
    return (v.major == 3 and v.minor in RECOMMENDED_MINOR_VERSIONS, f"{v.major}.{v.minor}")
