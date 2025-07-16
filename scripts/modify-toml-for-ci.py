#!/usr/bin/env python3
"""Safely modify pyproject.toml for CI without breaking TOML syntax."""

try:
    import tomllib
except ImportError:
    import tomli as tomllib
import toml


def clean_dependencies_for_ci():
    """Remove private dependencies while maintaining valid TOML."""
    # Read the original file
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    # Remove tool.uv.sources if it exists
    if "tool" in data and "uv" in data["tool"] and "sources" in data["tool"]["uv"]:
        del data["tool"]["uv"]["sources"]
        # If uv section is now empty, remove it
        if not data["tool"]["uv"]:
            del data["tool"]["uv"]

    # Filter out private dependencies
    if "project" in data and "dependencies" in data["project"]:
        original_deps = data["project"]["dependencies"]
        filtered_deps = []

        for dep in original_deps:
            dep_lower = dep.lower()
            # Skip private dependencies
            if any(pkg in dep_lower for pkg in ["boto3", "botocore", "bedrock-agentcore"]):
                print(f"Removing: {dep}")
                continue
            filtered_deps.append(dep)

        data["project"]["dependencies"] = filtered_deps
        print(f"Kept {len(filtered_deps)} of {len(original_deps)} dependencies")

    # Write the modified TOML
    with open("pyproject.toml", "w") as f:
        toml.dump(data, f)

    print("✓ Successfully modified pyproject.toml for CI")


if __name__ == "__main__":
    clean_dependencies_for_ci()
