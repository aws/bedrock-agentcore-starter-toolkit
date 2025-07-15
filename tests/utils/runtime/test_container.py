"""Tests for Bedrock AgentCore container runtime management."""

from pathlib import Path
from unittest.mock import patch

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.container import ContainerRuntime


class TestContainerRuntime:
    """Test ContainerRuntime functionality."""

    def test_runtime_auto_detection(self, mock_subprocess):
        """Test auto-detection of Docker/Finch/Podman."""
        # Test basic runtime functionality using mocked runtime
        # Since we have a mock fixture, we'll test the interface
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")
            assert runtime.runtime == "docker"
            assert runtime.get_name() == "Docker"

            runtime = ContainerRuntime("finch")
            assert runtime.runtime == "finch"
            assert runtime.get_name() == "Finch"

    def test_generate_dockerfile(self, tmp_path, mock_subprocess):
        """Test Dockerfile generation with dependencies."""
        # Create mock template
        template_dir = tmp_path / "src" / "bedrock_agentcore" / "templates"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "Dockerfile.j2"
        template_file.write_text("""
FROM python:{{ python_version }}
COPY {{ dependencies_file }} /app/
RUN pip install -r /app/{{ dependencies_file }}
COPY {{ agent_file }} /app/
CMD ["python", "/app/{{ agent_file }}"]
""")

        # Create agent file and requirements
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("bedrock_agentcore\nrequests")

        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock the template path resolution and platform validation
            with (
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.Path") as mock_path,
                patch.object(runtime, "_get_current_platform", return_value="linux/arm64"),
            ):
                mock_path.return_value.parent.parent = tmp_path
                mock_path.side_effect = lambda x: Path(x) if isinstance(x, str) else x

                dockerfile_path = runtime.generate_dockerfile(
                    agent_path=agent_file, output_dir=tmp_path, agent_name="test_agent", aws_region="us-west-2"
                )

                assert dockerfile_path == tmp_path / "Dockerfile"

    def test_build_image(self, mock_subprocess, tmp_path):
        """Test Docker build success and failure scenarios."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create a temporary Dockerfile for testing
            dockerfile = tmp_path / "Dockerfile"
            dockerfile.write_text("FROM python:3.10\nCMD echo 'test'")

            # Test successful build
            mock_subprocess["popen"].stdout = ["Step 1/5", "Successfully built abc123"]
            mock_subprocess["popen"].returncode = 0
            mock_subprocess["popen"].wait.return_value = 0

            success, output = runtime.build(tmp_path, "test:latest")
            assert success is True
            assert len(output) == 2

            # Test failed build
            mock_subprocess["popen"].returncode = 1
            mock_subprocess["popen"].wait.return_value = 1
            mock_subprocess["popen"].stdout = ["Error: build failed"]

            success, output = runtime.build(tmp_path, "test:latest")
            assert success is False
            assert "Error: build failed" in output

    def test_run_local_with_credentials(self, mock_boto3_clients, mock_subprocess):
        """Test local run with AWS credentials."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock successful credential retrieval
            mock_subprocess["run"].returncode = 0

            result = runtime.run_local("test:latest", 8080)
            assert result.returncode == 0

            # Test missing credentials
            mock_boto3_clients["session"].get_credentials.return_value = None
            with pytest.raises(RuntimeError, match="No AWS credentials found"):
                runtime.run_local("test:latest", 8080)

    def test_auto_runtime_detection_success(self, mock_subprocess):
        """Test successful auto-detection of available runtime."""

        def mock_is_installed(runtime_name):
            return runtime_name == "docker"  # Only docker is "installed"

        with patch.object(ContainerRuntime, "_is_runtime_installed", side_effect=mock_is_installed):
            runtime = ContainerRuntime("auto")
            assert runtime.runtime == "docker"
            assert runtime.get_name() == "Docker"

    def test_get_module_path_success(self, tmp_path):
        """Test successful module path generation."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create test structure: project/src/agents/my_agent.py
            src_dir = tmp_path / "src" / "agents"
            src_dir.mkdir(parents=True)
            agent_file = src_dir / "my_agent.py"
            agent_file.touch()

            module_path = runtime._get_module_path(agent_file, tmp_path)
            assert module_path == "src.agents.my_agent"

    def test_get_module_path_root_level(self, tmp_path):
        """Test module path generation for root level file."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create test agent at root level
            agent_file = tmp_path / "my_agent.py"
            agent_file.touch()

            module_path = runtime._get_module_path(agent_file, tmp_path)
            assert module_path == "my_agent"

    def test_get_module_path_bedrock_agentcore_prefix(self, tmp_path):
        """Test module path generation with .bedrock_agentcore prefix handling."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create test structure with .bedrock_agentcore prefix
            bedrock_dir = tmp_path / ".bedrock_agentcore"
            bedrock_dir.mkdir()
            agent_file = bedrock_dir / "handler.py"
            agent_file.touch()

            module_path = runtime._get_module_path(agent_file, tmp_path)
            assert module_path == "bedrock_agentcore.handler"

    def test_validate_module_path_success(self, tmp_path):
        """Test successful module path validation."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create valid directory structure
            src_dir = tmp_path / "src" / "valid_name"
            src_dir.mkdir(parents=True)
            agent_file = src_dir / "agent.py"
            agent_file.touch()

            # Should not raise any exception
            runtime._validate_module_path(agent_file, tmp_path)

    def test_registry_login_success(self, mock_subprocess):
        """Test successful registry login."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock successful login
            mock_subprocess["run"].returncode = 0

            success = runtime.login("registry.example.com", "username", "password")
            assert success is True

    def test_tag_image_success(self, mock_subprocess):
        """Test successful image tagging."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock successful tagging
            mock_subprocess["run"].returncode = 0

            success = runtime.tag("source:latest", "target:v1.0")
            assert success is True

    def test_push_image_success(self, mock_subprocess):
        """Test successful image push."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock successful push
            mock_subprocess["run"].returncode = 0

            success = runtime.push("registry.example.com/image:latest")
            assert success is True

    def test_ensure_dockerignore_creation(self, tmp_path):
        """Test .dockerignore file creation."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create mock template
            template_dir = tmp_path / "templates"
            template_dir.mkdir()
            template_file = template_dir / "dockerignore.template"
            template_file.write_text("__pycache__/\n*.pyc\n.git/")

            # Mock the Path(__file__).parent resolution to point to our test template
            mock_container_file = tmp_path / "container.py"
            with patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.container.Path",
                side_effect=lambda x: mock_container_file if str(x).endswith("__file__") else Path(x),
            ):
                runtime._ensure_dockerignore(tmp_path)

            dockerignore_path = tmp_path / ".dockerignore"
            assert dockerignore_path.exists()

    def test_run_local_with_env_vars(self, mock_boto3_clients, mock_subprocess):
        """Test local run with additional environment variables."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock successful credential retrieval and run
            mock_subprocess["run"].returncode = 0

            env_vars = {"DEBUG": "true", "LOG_LEVEL": "info"}
            result = runtime.run_local("test:latest", 8080, env_vars)
            assert result.returncode == 0

    def test_dockerfile_generation_with_wheelhouse(self, tmp_path):
        """Test Dockerfile generation when wheelhouse directory exists."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create wheelhouse directory
            wheelhouse_dir = tmp_path / "wheelhouse"
            wheelhouse_dir.mkdir()

            # Create agent file
            agent_file = tmp_path / "test_agent.py"
            agent_file.write_text("# test agent")

            # Create requirements file
            req_file = tmp_path / "requirements.txt"
            req_file.write_text("requests==2.25.1")

            # Mock template, dependencies, and platform validation
            with (
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.detect_dependencies") as mock_deps,
                patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.container.get_python_version", return_value="3.10"
                ),
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.Template") as mock_template,
                patch.object(runtime, "_get_current_platform", return_value="linux/arm64"),
            ):
                from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

                mock_deps.return_value = DependencyInfo(file="requirements.txt", type="requirements")

                mock_template_instance = mock_template.return_value
                mock_template_instance.render.return_value = "# Generated Dockerfile"

                dockerfile_path = runtime.generate_dockerfile(
                    agent_path=agent_file,
                    output_dir=tmp_path,
                    agent_name="test_agent",
                    requirements_file="requirements.txt",
                )

                assert dockerfile_path == tmp_path / "Dockerfile"
                mock_template_instance.render.assert_called_once()

    def test_dockerfile_generation_with_pyproject(self, tmp_path):
        """Test Dockerfile generation with pyproject.toml."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create pyproject.toml
            pyproject_file = tmp_path / "pyproject.toml"
            pyproject_file.write_text("[build-system]\nrequires = ['setuptools']")

            # Create agent file
            agent_file = tmp_path / "test_agent.py"
            agent_file.write_text("# test agent")

            # Mock template, dependencies, and platform validation
            with (
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.detect_dependencies") as mock_deps,
                patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.container.get_python_version", return_value="3.10"
                ),
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.Template") as mock_template,
                patch.object(runtime, "_get_current_platform", return_value="linux/arm64"),
            ):
                from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

                mock_deps.return_value = DependencyInfo(file="pyproject.toml", type="pyproject")

                mock_template_instance = mock_template.return_value
                mock_template_instance.render.return_value = "# Generated Dockerfile"

                dockerfile_path = runtime.generate_dockerfile(
                    agent_path=agent_file, output_dir=tmp_path, agent_name="test_agent"
                )

                assert dockerfile_path == tmp_path / "Dockerfile"
                # Verify context passed to template
                call_args = mock_template_instance.render.call_args
                context = call_args[1] if call_args[1] else call_args[0][0] if call_args[0] else {}
                assert context.get("has_current_package") is True

    def test_is_runtime_installed_success(self):
        """Test _is_runtime_installed with successful runtime detection."""
        runtime = ContainerRuntime.__new__(ContainerRuntime)  # Create instance without __init__

        with patch("subprocess.run") as mock_run:
            # Mock successful subprocess call
            mock_run.return_value.returncode = 0

            result = runtime._is_runtime_installed("docker")
            assert result is True
            mock_run.assert_called_once_with(["docker", "version"], capture_output=True, check=False)

    def test_is_runtime_installed_not_found(self):
        """Test _is_runtime_installed with runtime not found."""
        runtime = ContainerRuntime.__new__(ContainerRuntime)  # Create instance without __init__

        with patch("subprocess.run") as mock_run:
            # Mock FileNotFoundError (runtime not installed)
            mock_run.side_effect = FileNotFoundError("docker: command not found")

            result = runtime._is_runtime_installed("docker")
            assert result is False

    def test_image_exists_true(self, mock_subprocess):
        """Test image_exists when image exists."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock successful image check with output
            mock_subprocess["run"].returncode = 0
            mock_subprocess["run"].stdout = "abc123def456\n"

            result = runtime.image_exists("test:latest")
            assert result is True

    def test_image_exists_false(self, mock_subprocess):
        """Test image_exists when image does not exist."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Mock image check with no output (image doesn't exist)
            mock_subprocess["run"].returncode = 0
            mock_subprocess["run"].stdout = ""

            result = runtime.image_exists("nonexistent:latest")
            assert result is False

    def test_image_exists_subprocess_error(self):
        """Test image_exists when subprocess fails."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("subprocess.run") as mock_run:
                # Mock subprocess error
                mock_run.side_effect = OSError("Command failed")

                result = runtime.image_exists("test:latest")
                assert result is False

    def test_registry_login_failure(self):
        """Test registry login failure."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("subprocess.run") as mock_run:
                # Mock subprocess.CalledProcessError for failed login
                from subprocess import CalledProcessError

                mock_run.side_effect = CalledProcessError(1, ["docker", "login"])

                success = runtime.login("registry.example.com", "username", "wrong_password")
                assert success is False

    def test_registry_login_subprocess_error(self):
        """Test registry login with subprocess error."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("subprocess.run") as mock_run:
                # Mock subprocess.CalledProcessError
                from subprocess import CalledProcessError

                mock_run.side_effect = CalledProcessError(1, ["docker", "login"])

                success = runtime.login("registry.example.com", "username", "password")
                assert success is False

    def test_tag_image_failure(self):
        """Test image tagging failure."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("subprocess.run") as mock_run:
                # Mock failed tagging
                from subprocess import CalledProcessError

                mock_run.side_effect = CalledProcessError(1, ["docker", "tag"])

                success = runtime.tag("source:latest", "target:v1.0")
                assert success is False

    def test_push_image_failure(self):
        """Test image push failure."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("subprocess.run") as mock_run:
                # Mock failed push
                from subprocess import CalledProcessError

                mock_run.side_effect = CalledProcessError(1, ["docker", "push"])

                success = runtime.push("registry.example.com/image:latest")
                assert success is False

    def test_get_current_platform_amd64(self):
        """Test _get_current_platform for x86_64/amd64 systems."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("platform.machine", return_value="x86_64"):
                platform_str = runtime._get_current_platform()
                assert platform_str == "linux/amd64"

            with patch("platform.machine", return_value="amd64"):
                platform_str = runtime._get_current_platform()
                assert platform_str == "linux/amd64"

    def test_get_current_platform_arm64(self):
        """Test _get_current_platform for ARM64 systems."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("platform.machine", return_value="aarch64"):
                platform_str = runtime._get_current_platform()
                assert platform_str == "linux/arm64"

            with patch("platform.machine", return_value="arm64"):
                platform_str = runtime._get_current_platform()
                assert platform_str == "linux/arm64"

    def test_get_current_platform_unknown(self):
        """Test _get_current_platform for unknown architecture."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            with patch("platform.machine", return_value="unknown_arch"):
                platform_str = runtime._get_current_platform()
                assert platform_str == "linux/unknown_arch"

    def test_generate_dockerfile_platform_validation_success(self, tmp_path):
        """Test generate_dockerfile platform validation when platforms match."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create agent file
            agent_file = tmp_path / "test_agent.py"
            agent_file.write_text("# test agent")

            # Mock platform methods to return matching platforms
            with (
                patch.object(runtime, "_get_current_platform", return_value="linux/arm64"),
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.detect_dependencies") as mock_deps,
                patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.container.get_python_version", return_value="3.10"
                ),
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.Template") as mock_template,
            ):
                from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

                mock_deps.return_value = DependencyInfo(file="requirements.txt", type="requirements")
                mock_template_instance = mock_template.return_value
                mock_template_instance.render.return_value = "# Generated Dockerfile"

                # Should not raise any exception
                dockerfile_path = runtime.generate_dockerfile(
                    agent_path=agent_file, output_dir=tmp_path, agent_name="test_agent"
                )
                assert dockerfile_path == tmp_path / "Dockerfile"

    def test_generate_dockerfile_platform_validation_failure(self, tmp_path):
        """Test generate_dockerfile platform validation when platforms don't match."""
        with patch.object(ContainerRuntime, "_is_runtime_installed", return_value=True):
            runtime = ContainerRuntime("docker")

            # Create agent file
            agent_file = tmp_path / "test_agent.py"
            agent_file.write_text("# test agent")

            # Mock platform methods to return mismatched platforms and dependencies
            with (
                patch.object(runtime, "_get_current_platform", return_value="linux/amd64"),
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.detect_dependencies") as mock_deps,
                patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.container.get_python_version", return_value="3.10"
                ),
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.Template") as mock_template,
                patch("bedrock_agentcore_starter_toolkit.utils.runtime.container._handle_warn") as mock_handle_warn,
            ):
                from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

                mock_deps.return_value = DependencyInfo(file="requirements.txt", type="requirements")
                mock_template_instance = mock_template.return_value
                mock_template_instance.render.return_value = "# Generated Dockerfile"

                # Should not raise any exception, but should call _handle_warn
                dockerfile_path = runtime.generate_dockerfile(
                    agent_path=agent_file, output_dir=tmp_path, agent_name="test_agent"
                )

                # Verify the dockerfile was still generated
                assert dockerfile_path == tmp_path / "Dockerfile"

                # Check that _handle_warn was called with the expected message
                mock_handle_warn.assert_called_once()
                warning_message = mock_handle_warn.call_args[0][0]
                assert "Platform mismatch" in warning_message
                assert "linux/amd64" in warning_message
                assert "linux/arm64" in warning_message
                assert (
                    "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html"
                    in warning_message
                )
