"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
