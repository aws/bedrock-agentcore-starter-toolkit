#!/usr/bin/env python3
"""Prepare pyproject.toml for release by removing local dependencies."""

import re

print("Preparing pyproject.toml for release...")

with open("pyproject.toml", "r") as f:
    content = f.read()

# Remove [tool.uv.sources] section
original_length = len(content)
content = re.sub(r"\[tool\.uv\.sources\].*?(?=\[|$)", "", content, flags=re.DOTALL)

# Clean up extra newlines
content = re.sub(r"\n{3,}", "\n\n", content)

if len(content) < original_length:
    print("✓ Removed tool.uv.sources section")
else:
    print("ℹ No tool.uv.sources section found")

with open("pyproject.toml", "w") as f:
    f.write(content)

print("✓ Release preparation complete")
