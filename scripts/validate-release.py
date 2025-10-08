#!/usr/bin/env python3
"""
Pre-release validation script for BedrockAgentCore Starter Toolkit.
Configured for staging repository.
"""

import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_status(message: str, status: str = "info"):
    """Print colored status message."""
    if status == "success":
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
    elif status == "error":
        print(f"{Colors.RED}✗{Colors.RESET} {message}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠{Colors.RESET}  {message}")
    elif status == "info":
        print(f"{Colors.BLUE}ℹ{Colors.RESET}  {message}")
    else:
        print(f"  {message}")


def run_command(cmd: List[str], capture=True) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr."""
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result.returncode, result.stdout, result.stderr


def check_version() -> str:
    """Check and return the package version."""
    print(f"\n{Colors.BOLD}Checking package version...{Colors.RESET}")

    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print_status("pyproject.toml not found", "error")
        sys.exit(1)

    content = pyproject_path.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        print_status("Version not found in pyproject.toml", "error")
        sys.exit(1)

    version = match.group(1)
    print_status(f"Package version: {version}", "success")

    # Check for development markers
    if any(marker in version for marker in ["dev", "alpha", "beta", "rc"]):
        print_status(f"Version contains pre-release marker: {version}", "warning")

    return version


def check_dependencies():
    """Check that dependencies are properly configured for staging."""
    print(f"\n{Colors.BOLD}Checking dependencies...{Colors.RESET}")

    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Check for staging SDK dependency
    if "bedrock-agentcore-sdk-staging-py" in content:
        print_status("Staging SDK dependency found", "success")
    else:
        print_status("Missing staging SDK dependency (bedrock-agentcore-sdk-staging-py)", "error")
        print_status("Please update pyproject.toml dependencies", "info")

    # Check that wheelhouse dependencies are only in tool.uv.sources
    main_deps_section = re.search(r"\[project\].*?dependencies = \[(.*?)\]", content, re.DOTALL)
    if main_deps_section:
        deps_content = main_deps_section.group(1)
        if "wheelhouse" in deps_content:
            print_status("Wheelhouse references found in main dependencies!", "error")
            sys.exit(1)

    print_status("No wheelhouse references in main dependencies", "success")

    # Check tool.uv.sources exists for development
    if "[tool.uv.sources]" in content:
        print_status("Development sources properly configured in [tool.uv.sources]", "success")
    else:
        print_status("No [tool.uv.sources] section found", "warning")


def check_security_files():
    """Verify all security-related files are in place."""
    print(f"\n{Colors.BOLD}Checking security compliance...{Colors.RESET}")

    required_files = {
        ".github/workflows/security-scanning.yml": "Security scanning workflow",
        ".github/workflows/ci.yml": "CI workflow",
        ".github/workflows/release.yml": "Release workflow",
        ".github/dependabot.yml": "Dependabot configuration",
        ".github/CODEOWNERS": "Code ownership file",
        "SECURITY.md": "Security policy",
    }

    all_present = True
    for file_path, description in required_files.items():
        if Path(file_path).exists():
            print_status(f"{description} present", "success")
        else:
            print_status(f"{description} missing: {file_path}", "error")
            all_present = False

    return all_present


def validate_package_contents(wheel_path: Path):
    """Validate the contents of the built wheel."""
    print(f"\n{Colors.BOLD}Validating package contents...{Colors.RESET}")

    with zipfile.ZipFile(wheel_path, "r") as zf:
        files = zf.namelist()

        # Check for wheelhouse
        wheelhouse_files = [f for f in files if "wheelhouse" in f]
        if wheelhouse_files:
            print_status(f"Found wheelhouse files in package: {wheelhouse_files[:5]}...", "error")
            sys.exit(1)
        else:
            print_status("No wheelhouse files in package", "success")

        # Check for required files
        required_patterns = [
            "bedrock_agentcore_starter_toolkit/__init__.py",
            "bedrock_agentcore_starter_toolkit/cli/cli.py",
            "*.dist-info/METADATA",
            "*.dist-info/WHEEL",
        ]

        for pattern in required_patterns:
            if pattern.startswith("*"):
                found = any(f.endswith(pattern[1:]) for f in files)
            else:
                found = pattern in files

            if found:
                print_status(f"Found required: {pattern}", "success")
            else:
                print_status(f"Missing required: {pattern}", "error")
                sys.exit(1)


def main():
    """Run all validation checks."""
    print(f"{Colors.BOLD}=== BedrockAgentCore Starter Toolkit - Release Validation ==={Colors.RESET}")
    print("Repository: bedrock-agentcore-starter-toolkit-staging")

    # Check we're in the right directory
    if not Path("pyproject.toml").exists():
        print_status("This script must be run from the repository root", "error")
        sys.exit(1)

    # Run all checks
    version = check_version()
    check_dependencies()

    if not check_security_files():
        print_status("Security compliance check failed", "error")
        print_status("Run scripts/setup-release.sh to create required files", "info")

    # Build the package
    print(f"\n{Colors.BOLD}Building package...{Colors.RESET}")
    code, stdout, stderr = run_command(["uv", "build"])
    if code != 0:
        print_status(f"Build failed: {stderr}", "error")
        sys.exit(1)
    print_status("Package built successfully", "success")

    # Find the wheel
    wheel_files = list(Path("dist").glob("*.whl"))
    if not wheel_files:
        print_status("No wheel file found in dist/", "error")
        sys.exit(1)

    wheel_path = wheel_files[0]
    print_status(f"Found wheel: {wheel_path.name}", "info")

    # Validate wheel
    validate_package_contents(wheel_path)

    # Final summary
    print(f"\n{Colors.BOLD}=== Validation Summary ==={Colors.RESET}")
    print_status(f"Package version: {version}", "info")
    print_status(f"Wheel file: {wheel_path.name}", "info")
    print_status(f"Size: {wheel_path.stat().st_size / 1024 / 1024:.2f} MB", "info")

    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Package validation complete!{Colors.RESET}")
    print("\nNext steps:")
    print("1. Update pyproject.toml to use staging dependencies")
    print("2. Test on Test PyPI: Follow instructions in MCM document")
    print(f"3. Create git tag: git tag -a v{version} -m 'Release {version}'")
    print(f"4. Push tag to trigger release: git push origin v{version}")


if __name__ == "__main__":
    main()
