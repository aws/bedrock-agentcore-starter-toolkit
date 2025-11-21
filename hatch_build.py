import os
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Custom build hook that builds the UI/frontend before packaging."""

    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        """Initialize the build hook and build the frontend."""
        if self.target_name not in ["wheel", "sdist"]:
            return

        # Get the frontend directory path
        frontend_dir = (
            Path(self.root)
            / "src"
            / "bedrock_agentcore_starter_toolkit"
            / "ui"
            / "frontend"
        )

        if not frontend_dir.exists():
            print(
                f"Warning: Frontend directory not found at {frontend_dir}",
                file=sys.stderr,
            )
            return

        print(f"Building frontend at {frontend_dir}...")

        try:
            # Clean any existing node_modules to ensure fresh install
            node_modules = frontend_dir / "node_modules"
            if node_modules.exists():
                print("Cleaning existing node_modules...")
                import shutil

                shutil.rmtree(node_modules)

            # Install dependencies
            print("Installing frontend dependencies with npm...")
            self._run_command(
                [
                    "npm",
                    (
                        "ci"
                        if (frontend_dir / "package-lock.json").exists()
                        else "install"
                    ),
                ],
                cwd=frontend_dir,
            )

            # Build the frontend
            print("Building frontend assets...")
            self._run_command(["npm", "run", "build"], cwd=frontend_dir)

            # Verify the build output exists
            dist_dir = frontend_dir / "dist"
            if dist_dir.exists():
                print(f"Frontend build successful! Output at {dist_dir}")
            else:
                print(
                    "Warning: Frontend build completed but dist directory not found",
                    file=sys.stderr,
                )

        except subprocess.CalledProcessError as e:
            print(f"Error building frontend: {e}", file=sys.stderr)
            print(
                "Continuing with build, but frontend assets may be missing",
                file=sys.stderr,
            )
        except FileNotFoundError:
            print(
                "Error: npm not found. Please install Node.js and npm",
                file=sys.stderr,
            )
            print(
                "Continuing with build, but frontend assets may be missing",
                file=sys.stderr,
            )

    def _run_command(self, cmd, cwd):
        """Run a shell command in the specified directory."""
        subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            env={
                **os.environ,
                "CI": "true",
            },  # Set CI=true to avoid interactive prompts
        )
