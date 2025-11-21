"""Shared test fixtures for Bedrock AgentCore Starter Toolkit tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from bedrock_agentcore import BedrockAgentCoreApp

from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    MemoryConfig,
    NetworkConfiguration,
    ObservabilityConfig,
    ProtocolConfiguration,
)


@pytest.fixture
def mock_boto3_clients(monkeypatch):
    """Mock AWS clients (STS, ECR, BedrockAgentCore)."""
    # Mock STS client
    mock_sts = Mock()
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

    # Mock ECR client
    mock_ecr = Mock()
    mock_ecr.create_repository.return_value = {
        "repository": {"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo"}
    }
    mock_ecr.get_authorization_token.return_value = {
        "authorizationData": [
            {
                "authorizationToken": "dXNlcjpwYXNz",  # base64 encoded "user:pass"
                "proxyEndpoint": "https://123456789012.dkr.ecr.us-west-2.amazonaws.com",
            }
        ]
    }
    mock_ecr.describe_repositories.return_value = {
        "repositories": [{"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/existing-repo"}]
    }

    # Mock exceptions - create proper exception classes
    class RepositoryAlreadyExistsException(Exception):
        """Mock exception for repository already exists."""

        pass

    class RepositoryNotFoundException(Exception):
        """Mock exception for repository not found."""

        pass

    mock_ecr.exceptions = Mock()
    mock_ecr.exceptions.RepositoryAlreadyExistsException = RepositoryAlreadyExistsException
    mock_ecr.exceptions.RepositoryNotFoundException = RepositoryNotFoundException

    # Mock BedrockAgentCore client
    mock_bedrock_agentcore = Mock()
    mock_bedrock_agentcore.create_agent_runtime.return_value = {
        "agentRuntimeId": "test-agent-id",
        "agentRuntimeArn": "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
    }
    mock_bedrock_agentcore.update_agent_runtime.return_value = {
        "agentRuntimeArn": "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
    }
    mock_bedrock_agentcore.get_agent_runtime_endpoint.return_value = {
        "status": "READY",
        "agentRuntimeEndpointArn": (
            "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
        ),
    }
    mock_bedrock_agentcore.invoke_agent_runtime.return_value = {"response": [{"data": "test response"}]}
    # Mock exceptions
    mock_bedrock_agentcore.exceptions = Mock()
    mock_bedrock_agentcore.exceptions.ResourceNotFoundException = Exception

    # Mock boto3.client calls
    def mock_client(service_name, **kwargs):
        if service_name == "sts":
            return mock_sts
        elif service_name == "ecr":
            return mock_ecr
        elif service_name in ["bedrock_agentcore-test", "bedrock-agentcore-control", "bedrock-agentcore"]:
            return mock_bedrock_agentcore
        return Mock()

    # Mock boto3.Session
    mock_session = Mock()
    mock_session.region_name = "us-west-2"
    mock_session.get_credentials.return_value.get_frozen_credentials.return_value = Mock(
        access_key="test-key", secret_key="test-secret", token="test-token"
    )

    monkeypatch.setattr("boto3.client", mock_client)
    monkeypatch.setattr("boto3.Session", lambda *args, **kwargs: mock_session)

    return {"sts": mock_sts, "ecr": mock_ecr, "bedrock_agentcore": mock_bedrock_agentcore, "session": mock_session}


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess operations for container runtime."""
    mock_run = Mock()
    mock_run.returncode = 0
    mock_run.stdout = "Docker version 20.10.0"

    mock_popen = Mock()
    mock_popen.stdout = ["Step 1/5 : FROM python:3.10", "Successfully built abc123"]
    mock_popen.wait.return_value = 0
    mock_popen.returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: mock_run)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: mock_popen)

    return {"run": mock_run, "popen": mock_popen}


@pytest.fixture
def mock_bedrock_agentcore_app():
    """Mock BedrockAgentCoreApp instance for testing."""
    app = BedrockAgentCoreApp()

    @app.entrypoint
    def test_handler(payload):
        return {"result": "test"}

    return app


@pytest.fixture
def mock_container_runtime(monkeypatch):
    """Mock container runtime operations."""
    from bedrock_agentcore_starter_toolkit.utils.runtime.container import ContainerRuntime

    # Create a mock runtime object with all required attributes and methods
    mock_runtime = Mock(spec=ContainerRuntime)
    mock_runtime.runtime = "docker"
    mock_runtime.has_local_runtime = True  # Add the new attribute
    mock_runtime.get_name.return_value = "Docker"
    mock_runtime.build.return_value = (True, ["Successfully built test-image"])
    mock_runtime.login.return_value = True
    mock_runtime.tag.return_value = True
    mock_runtime.push.return_value = True
    mock_runtime.generate_dockerfile.return_value = Path("/tmp/Dockerfile")

    # Set class attributes for compatibility
    mock_runtime.DEFAULT_RUNTIME = "auto"
    mock_runtime.DEFAULT_PLATFORM = "linux/arm64"

    # Mock the ContainerRuntime class constructor
    def mock_constructor(*args, **kwargs):
        return mock_runtime

    monkeypatch.setattr("bedrock_agentcore_starter_toolkit.utils.runtime.container.ContainerRuntime", mock_constructor)

    return mock_runtime


@pytest.fixture
def sample_project_context(tmp_path):
    """Returns a ProjectContext with typical values for testing."""
    output_dir = tmp_path / "test-project"
    src_dir = output_dir / "src"

    return ProjectContext(
        name="test-project",
        output_dir=output_dir,
        src_dir=src_dir,
        entrypoint_path=src_dir / "main.py",
        sdk_provider="Strands",
        iac_provider="CDK",
        model_provider="Bedrock",
        template_dir_selection="default",
        runtime_protocol="HTTP",
        deployment_type="container",
        python_dependencies=[],
        iac_dir=None,
        agent_name="test_agent",
        memory_enabled=False,
        memory_name=None,
        memory_event_expiry_days=30,
        memory_is_long_term=False,
        custom_authorizer_enabled=False,
        custom_authorizer_url=None,
        custom_authorizer_allowed_clients=None,
        custom_authorizer_allowed_audience=None,
        vpc_enabled=False,
        vpc_subnets=None,
        vpc_security_groups=None,
        request_header_allowlist=None,
        observability_enabled=True,
    )


@pytest.fixture
def sample_agent_config():
    """Returns a BedrockAgentCoreAgentSchema with typical values for testing."""
    return BedrockAgentCoreAgentSchema(
        name="test-agent",
        entrypoint="src/main.py",
        source_path=".",
        deployment_type="container",
        aws=AWSConfig(
            region="us-west-2",
            account="123456789012",
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
            observability=ObservabilityConfig(enabled=True),
            protocol_configuration=ProtocolConfiguration(server_protocol="HTTP"),
        ),
        memory=MemoryConfig(
            mode="NO_MEMORY",
            event_expiry_days=30,
        ),
        authorizer_configuration=None,
        request_header_configuration=None,
    )


@pytest.fixture
def temp_source_structure(tmp_path):
    """Creates a temporary source directory structure for copying tests."""
    # Create source files
    (tmp_path / "main.py").write_text("# main file")
    (tmp_path / "utils.py").write_text("# utils file")
    (tmp_path / ".dockerignore").write_text("*.pyc\n__pycache__/")

    # Create subdirectory
    subdir = tmp_path / "lib"
    subdir.mkdir()
    (subdir / "helper.py").write_text("# helper file")

    # Create reserved directory (should be skipped)
    reserved = tmp_path / ".bedrock_agentcore"
    reserved.mkdir()
    (reserved / "config.yaml").write_text("# config")

    # Create reserved file (should be skipped)
    (tmp_path / ".bedrock_agentcore.yaml").write_text("# reserved")

    # Create .bedrock_agentcore/agent_name/Dockerfile
    agent_dir = reserved / "test-agent"
    agent_dir.mkdir()
    (agent_dir / "Dockerfile").write_text("FROM python:3.11")

    return tmp_path
