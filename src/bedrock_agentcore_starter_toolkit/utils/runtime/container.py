"""Container runtime management for Bedrock AgentCore SDK."""

import logging
import platform
import subprocess  # nosec B404 - Required for container runtime operations
import time
from pathlib import Path
from typing import List, Optional, Tuple

from jinja2 import Template

from ...cli.common import _handle_warn
from .entrypoint import detect_dependencies, get_python_version

log = logging.getLogger(__name__)


class ContainerRuntime:
    """Container runtime for Docker, Finch, and Podman."""

    DEFAULT_RUNTIME = "auto"
    DEFAULT_PLATFORM = "linux/arm64"

    def __init__(self, runtime_type: Optional[str] = None):
        """Initialize container runtime.

        Args:
            runtime_type: Runtime type to use, defaults to auto-detection
        """
        runtime_type = runtime_type or self.DEFAULT_RUNTIME
        self.available_runtimes = ["finch", "docker", "podman"]

        if runtime_type == "auto":
            for runtime in self.available_runtimes:
                if self._is_runtime_installed(runtime):
                    self.runtime = runtime
                    break
            else:
                raise RuntimeError("No container runtime found. Please install Docker, Finch, or Podman.")
        elif runtime_type in self.available_runtimes:
            if self._is_runtime_installed(runtime_type):
                self.runtime = runtime_type
            else:
                raise RuntimeError(f"{runtime_type.capitalize()} is not installed")
        else:
            raise ValueError(f"Unsupported runtime: {runtime_type}")

    def _is_runtime_installed(self, runtime: str) -> bool:
        """Check if runtime is installed."""
        try:
            result = subprocess.run([runtime, "version"], capture_output=True, check=False)  # nosec B603
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def get_name(self) -> str:
        """Get runtime name."""
        return self.runtime.capitalize()

    def image_exists(self, tag: str) -> bool:
        """Check if image exists."""
        try:
            result = subprocess.run([self.runtime, "images", "-q", tag], capture_output=True, text=True, check=False)  # nosec B603
            return bool(result.stdout.strip())
        except (subprocess.SubprocessError, OSError):
            return False

    def generate_dockerfile(
        self,
        agent_path: Path,
        output_dir: Path,
        agent_name: str,
        aws_region: Optional[str] = None,
        enable_observability: bool = True,
        requirements_file: Optional[str] = None,
    ) -> Path:
        """Generate Dockerfile from template."""
        current_platform = self._get_current_platform()
        required_platform = self.DEFAULT_PLATFORM

        if current_platform != required_platform:
            _handle_warn(
                f"[WARNING] Platform mismatch: Current system is '{current_platform}' "
                f"but Bedrock AgentCore requires '{required_platform}'.\n"
                "For deployment options and workarounds, see: "
                "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html\n"
            )

        template_path = Path(__file__).parent / "templates" / "Dockerfile.j2"

        if not template_path.exists():
            log.error("Dockerfile template not found: %s", template_path)
            raise FileNotFoundError(f"Dockerfile template not found: {template_path}")

        with open(template_path) as f:
            template = Template(f.read())

        # Generate .dockerignore if it doesn't exist
        self._ensure_dockerignore(output_dir)

        # Validate module path before generating Dockerfile
        self._validate_module_path(agent_path, output_dir)

        # Calculate module path relative to project root
        agent_module_path = self._get_module_path(agent_path, output_dir)

        wheelhouse_dir = output_dir / "wheelhouse"

        # Detect dependencies using the new DependencyInfo class
        deps = detect_dependencies(output_dir, explicit_file=requirements_file)

        # Add logic to avoid duplicate installation
        has_current_package = False
        if (output_dir / "pyproject.toml").exists():
            # Only install current package if deps isn't already pointing to it
            if not (deps.found and deps.is_root_package):
                has_current_package = True

        context = {
            "python_version": get_python_version(),
            "agent_file": agent_path.name,
            "agent_module": agent_path.stem,
            "agent_module_path": agent_module_path,
            "agent_var": agent_name,
            "has_wheelhouse": wheelhouse_dir.exists() and wheelhouse_dir.is_dir(),
            "has_current_package": has_current_package,
            "dependencies_file": deps.file,
            "dependencies_install_path": deps.install_path,
            "aws_region": aws_region,
            "system_packages": [],
            "observability_enabled": enable_observability,
        }

        dockerfile_path = output_dir / "Dockerfile"
        dockerfile_path.write_text(template.render(**context))
        return dockerfile_path

    def _ensure_dockerignore(self, project_dir: Path) -> None:
        """Create .dockerignore if it doesn't exist."""
        dockerignore_path = project_dir / ".dockerignore"
        if not dockerignore_path.exists():
            template_path = Path(__file__).parent / "templates" / "dockerignore.template"
            if template_path.exists():
                dockerignore_path.write_text(template_path.read_text())
                log.info("Generated .dockerignore")

    def _validate_module_path(self, agent_path: Path, project_root: Path) -> None:
        """Validate that the agent path can be converted to a valid Python module path."""
        try:
            agent_path = agent_path.resolve()
            relative_path = agent_path.relative_to(project_root)
            for part in relative_path.parts[:-1]:  # Check all directory parts
                if "-" in part:
                    raise ValueError(
                        f"Directory name '{part}' contains hyphens which are not valid in Python module paths. "
                        f"Please rename '{part}' to '{part.replace('-', '_')}' or move your agent file to a "
                        f"directory with valid Python identifiers."
                    )
        except ValueError as e:
            if "does not start with" in str(e):
                raise ValueError("Entrypoint file must be within the current project directory") from e
            raise

    def _get_module_path(self, agent_path: Path, project_root: Path) -> str:
        """Get the Python module path for the agent file."""
        try:
            agent_path = agent_path.resolve()
            # Get relative path from project root
            relative_path = agent_path.relative_to(project_root)
            # Convert to module path (e.g., src/agents/my_agent.py -> src.agents.my_agent)
            parts = list(relative_path.parts[:-1]) + [relative_path.stem]
            module_path = ".".join(parts)

            # Handle notebook-generated handlers that start with .bedrock_agentcore
            if module_path.startswith(".bedrock_agentcore"):
                # Remove leading dot to make it a valid Python import
                module_path = module_path[1:]

            return module_path
        except ValueError:
            # If agent is outside project root, just use the filename
            return agent_path.stem

    def _get_current_platform(self) -> str:
        """Get the current system platform in standardized format."""
        machine = platform.machine().lower()
        arch_map = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
        arch = arch_map.get(machine, machine)
        return f"linux/{arch}"

    def build(self, dockerfile_dir: Path, tag: str, platform: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Build container image."""
        if not dockerfile_dir.exists():
            return False, [f"Directory not found: {dockerfile_dir}"]

        dockerfile_path = dockerfile_dir / "Dockerfile"
        if not dockerfile_path.exists():
            return False, [f"Dockerfile not found in {dockerfile_dir}"]

        cmd = [self.runtime, "build", "-t", tag]
        build_platform = platform or self.DEFAULT_PLATFORM
        cmd.extend(["--platform", build_platform])
        cmd.append(str(dockerfile_dir))

        return self._execute_command(cmd)

    def run_local(self, tag: str, port: int = 8080, env_vars: Optional[dict] = None) -> subprocess.CompletedProcess:
        """Run container locally.

        Args:
            tag: Docker image tag to run
            port: Port to expose (default: 8080)
            env_vars: Additional environment variables to pass to container
        """
        container_name = f"{tag.split(':')[0]}-{int(time.time())}"
        cmd = [self.runtime, "run", "-it", "--rm", "-p", f"{port}:8080", "--name", container_name]

        # Use boto3 to get current credentials
        try:
            import boto3

            session = boto3.Session()
            credentials = session.get_credentials()

            if not credentials:
                raise RuntimeError("No AWS credentials found. Please configure AWS credentials.")

            # Get the frozen credentials (resolves temporary credentials too)
            frozen_creds = credentials.get_frozen_credentials()

            cmd.extend(["-e", f"AWS_ACCESS_KEY_ID={frozen_creds.access_key}"])
            cmd.extend(["-e", f"AWS_SECRET_ACCESS_KEY={frozen_creds.secret_key}"])

            if frozen_creds.token:
                cmd.extend(["-e", f"AWS_SESSION_TOKEN={frozen_creds.token}"])

        except ImportError:
            raise RuntimeError("boto3 is required for local mode. Please install it.") from None

        # Add additional environment variables if provided
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(tag)
        return subprocess.run(cmd, check=False)  # nosec B603

    def login(self, registry: str, username: str, password: str) -> bool:
        """Login to registry."""
        log.info("Authenticating with registry...")
        try:
            subprocess.run(  # nosec B603
                [self.runtime, "login", "--username", username, "--password-stdin", registry],
                input=password.encode(),
                capture_output=True,
                check=True,
            )
            log.info("Registry authentication successful")
            return True
        except subprocess.CalledProcessError:
            log.error("Registry authentication failed")
            return False

    def tag(self, source: str, target: str) -> bool:
        """Tag an image."""
        log.info("Tagging image: %s -> %s", source, target)
        try:
            subprocess.run([self.runtime, "tag", source, target], check=True)  # nosec B603
            return True
        except subprocess.CalledProcessError:
            log.error("Failed to tag image")
            return False

    def push(self, tag: str) -> bool:
        """Push image to registry."""
        log.info("Pushing image to registry...")
        try:
            subprocess.run([self.runtime, "push", tag], check=True)  # nosec B603
            log.info("Image pushed successfully")
            return True
        except subprocess.CalledProcessError:
            log.error("Failed to push image")
            return False

    def _execute_command(self, cmd: List[str]) -> Tuple[bool, List[str]]:
        """Execute command and capture output."""
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)  # nosec B603

            output_lines = []
            if process.stdout:
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        # Log output at source as it streams
                        if "error" in line.lower() or "failed" in line.lower():
                            log.error("Build: %s", line)
                        elif "Successfully" in line:
                            log.info("Build: %s", line)
                        else:
                            log.debug("Build: %s", line)

                        output_lines.append(line)

            process.wait()
            return process.returncode == 0, output_lines

        except (subprocess.SubprocessError, OSError) as e:
            log.error("Command execution failed: %s", str(e))
            return False, [str(e)]
