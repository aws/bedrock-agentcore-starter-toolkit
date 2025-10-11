"""Container runtime management for Bedrock AgentCore SDK."""

import logging
import platform
import subprocess  # nosec B404 - Required for container runtime operations
import time
from pathlib import Path
from typing import List, Optional, Tuple

from jinja2 import Template
from rich.console import Console

from ...cli.common import _handle_warn, _print_success
from .entrypoint import detect_dependencies, get_python_version

console = Console()

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
        self.runtime = None
        self.has_local_runtime = False

        if runtime_type == "auto":
            for runtime in self.available_runtimes:
                if self._is_runtime_installed(runtime):
                    self.runtime = runtime
                    self.has_local_runtime = True
                    break
            else:
                # Informational message - default CodeBuild deployment works fine
                console.print("\n💡 [cyan]No container engine found (Docker/Finch/Podman not installed)[/cyan]")
                _print_success(
                    "Default deployment uses CodeBuild (no container engine needed), "
                    "For local builds, install Docker, Finch, or Podman"
                )
                self.runtime = "none"
                self.has_local_runtime = False
        elif runtime_type in self.available_runtimes:
            if self._is_runtime_installed(runtime_type):
                self.runtime = runtime_type
                self.has_local_runtime = True
            else:
                # Convert hard error to warning - suggest CodeBuild instead
                _handle_warn(
                    f"{runtime_type.capitalize()} is not installed\n"
                    "Recommendation: Use CodeBuild for building containers in the cloud\n"
                    f"For local builds, please install {runtime_type.capitalize()}"
                )
                self.runtime = "none"
                self.has_local_runtime = False
        else:
            if runtime_type == "none":
                raise ValueError(
                    "No supported container engine found.\n\n"
                    "AgentCore requires one of the following container engines for local builds:\n"
                    "• Docker (any recent version, including Docker Desktop)\n"
                    "• Finch (Amazon's open-source container engine)\n"
                    "• Podman (compatible alternative to Docker)\n\n"
                    "To install:\n"
                    "• Docker: https://docs.docker.com/get-docker/\n"
                    "• Finch: https://github.com/runfinch/finch\n"
                    "• Podman: https://podman.io/getting-started/installation\n\n"
                    "Alternative: Use CodeBuild for cloud-based building (no container engine needed):\n"
                    "  agentcore launch  # Uses CodeBuild (default)"
                )
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
        memory_id: Optional[str] = None,
        memory_name: Optional[str] = None,
        source_path: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> Path:
        """Generate Dockerfile from template.

        Args:
            agent_path: Path to agent entrypoint file
            output_dir: Output directory for Dockerfile (project root)
            agent_name: Name of the agent
            aws_region: AWS region
            enable_observability: Whether to enable observability
            requirements_file: Optional explicit requirements file path
            memory_id: Optional memory ID
            memory_name: Optional memory name
            source_path: Optional source code directory (for dependency detection)
            protocol: Optional protocol configuration (HTTP or HTTPS)
        """
        current_platform = self._get_current_platform()
        required_platform = self.DEFAULT_PLATFORM

        if current_platform != required_platform:
            _handle_warn(
                f"Platform mismatch: Current system is '{current_platform}' "
                f"but Bedrock AgentCore requires '{required_platform}', so local builds won't work.\n"
                "Please use default launch command which will do a remote cross-platform build using code build."
                "For deployment other options and workarounds, see: "
                "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html\n"
            )

        template_path = Path(__file__).parent / "templates" / "Dockerfile.j2"

        if not template_path.exists():
            log.error("Dockerfile template not found: %s", template_path)
            raise FileNotFoundError(f"Dockerfile template not found: {template_path}")

        with open(template_path) as f:
            template = Template(f.read())

        # Calculate build context root first (needed for validation)
        # If source_path provided: module path relative to source_path (Docker build context)
        # Otherwise: module path relative to project root
        build_context_root = Path(source_path) if source_path else output_dir
        # Generate .dockerignore if it doesn't exist
        self._ensure_dockerignore(build_context_root)

        # Validate module path against build context root
        self._validate_module_path(agent_path, build_context_root)

        # Calculate module path relative to Docker build context
        agent_module_path = self._get_module_path(agent_path, build_context_root)

        wheelhouse_dir = output_dir / "wheelhouse"

        # Detect dependencies:
        # - If source_path provided: check source_path only
        # - Otherwise: check project root (output_dir)
        # - If explicit requirements_file provided: use that regardless
        if source_path and not requirements_file:
            source_dir = Path(source_path)
            deps = detect_dependencies(source_dir, explicit_file=None)
        if source_path:
            source_dir = Path(source_path)
            deps = detect_dependencies(source_dir, explicit_file=requirements_file)
        else:
            deps = detect_dependencies(output_dir, explicit_file=requirements_file)

        # Add logic to avoid duplicate installation
        # Check for pyproject.toml in the appropriate directory
        has_current_package = False
        check_dir = Path(source_path) if source_path else output_dir
        if (check_dir / "pyproject.toml").exists():
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
            "memory_id": memory_id,
            "memory_name": memory_name,
            "protocol": protocol or "HTTP",
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
            project_root = project_root.resolve()
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
            project_root = project_root.resolve()
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

    def build(
        self,
        build_context: Path,
        tag: str,
        dockerfile_path: Optional[Path] = None,
        platform: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Build container image.

        Args:
            build_context: Directory to use as build context
            tag: Tag for the built image
            dockerfile_path: Optional path to Dockerfile (if not in build_context)
            platform: Optional platform override
        """
        if not self.has_local_runtime:
            return False, [
                "No container runtime available for local build",
                "💡 Recommendation: Use CodeBuild for building containers in the cloud",
                "💡 Run 'agentcore launch' (default) for CodeBuild deployment",
                "💡 For local builds, please install Docker, Finch, or Podman",
            ]

        if not build_context.exists():
            return False, [f"Build context directory not found: {build_context}"]

        # Determine Dockerfile location
        if dockerfile_path:
            # Use provided Dockerfile path
            if not dockerfile_path.exists():
                return False, [f"Dockerfile not found: {dockerfile_path}"]
        else:
            # Look for Dockerfile in build context
            dockerfile_path = build_context / "Dockerfile"
            if not dockerfile_path.exists():
                return False, [f"Dockerfile not found in {build_context}"]

        cmd = [self.runtime, "build", "-t", tag]

        # Use -f flag if Dockerfile is not in the build context
        if dockerfile_path.parent != build_context:
            cmd.extend(["-f", str(dockerfile_path)])

        build_platform = platform or self.DEFAULT_PLATFORM
        cmd.extend(["--platform", build_platform])
        cmd.append(str(build_context))

        return self._execute_command(cmd)

    def run_local(self, tag: str, port: int = 8080, env_vars: Optional[dict] = None) -> subprocess.CompletedProcess:
        """Run container locally.

        Args:
            tag: Docker image tag to run
            port: Port to expose (default: 8080)
            env_vars: Additional environment variables to pass to container
        """
        if not self.has_local_runtime:
            raise RuntimeError(
                "No container runtime available for local run\n"
                "💡 Recommendation: Use CodeBuild for building containers in the cloud\n"
                "💡 Run 'agentcore launch' (default) for CodeBuild deployment\n"
                "💡 For local runs, please install Docker, Finch, or Podman"
            )

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
