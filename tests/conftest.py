"""Shared test fixtures for Bedrock AgentCore Starter Toolkit tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from bedrock_agentcore import BedrockAgentCoreApp


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
