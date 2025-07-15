"""Tests for Bedrock AgentCore invoke operation."""

from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import invoke_bedrock_agentcore
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
)


class TestInvokeBedrockAgentCore:
    """Test invoke_bedrock_agentcore functionality."""

    def test_invoke_success(self, mock_boto3_clients, tmp_path):
        """Test successful invocation with session handling."""
        # Create config file with deployed agent
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello, Bedrock AgentCore!"}

        result = invoke_bedrock_agentcore(config_path, payload)

        # Verify result structure
        assert hasattr(result, "response")
        assert hasattr(result, "session_id")
        assert hasattr(result, "agent_arn")

        # Verify values
        assert result.agent_arn == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        assert result.response == {"response": [{"data": "test response"}]}
        assert isinstance(result.session_id, str)

        # Verify Bedrock AgentCore client was called correctly
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args
        assert (
            call_args[1]["agentRuntimeArn"]
            == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        )
        assert '"message": "Hello, Bedrock AgentCore!"' in call_args[1]["payload"]

    def test_invoke_missing_config(self, tmp_path):
        """Test error when config file not found."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            invoke_bedrock_agentcore(nonexistent_config, {"test": "payload"})

    def test_invoke_with_custom_session_id(self, mock_boto3_clients, tmp_path):
        """Test invocation with custom session ID."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        custom_session_id = "custom-session-123"
        payload = {"message": "Hello"}

        result = invoke_bedrock_agentcore(config_path, payload, session_id=custom_session_id)

        # Verify custom session ID was used
        assert result.session_id == custom_session_id

        # Verify it was passed to the client
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args
        assert call_args[1]["runtimeSessionId"] == custom_session_id

    def test_invoke_string_payload(self, mock_boto3_clients, tmp_path):
        """Test invocation with string payload."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        string_payload = "Hello, Bedrock AgentCore!"

        invoke_bedrock_agentcore(config_path, string_payload)

        # Verify string payload was handled correctly
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args
        assert call_args[1]["payload"] == "Hello, Bedrock AgentCore!"

    def test_invoke_with_bearer_token(self, tmp_path):
        """Test invocation with bearer token uses HTTP client."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello with bearer token"}
        bearer_token = "test-bearer-token-123"

        with patch(
            "bedrock_agentcore_starter_toolkit.services.runtime.HttpBedrockAgentCoreClient"
        ) as mock_http_client_class:
            mock_http_client = Mock()
            mock_http_client.invoke_endpoint.return_value = {"response": "http client response"}
            mock_http_client_class.return_value = mock_http_client

            result = invoke_bedrock_agentcore(config_path, payload, bearer_token=bearer_token)

            # Verify HTTP client was used instead of boto3 client
            mock_http_client_class.assert_called_once_with("us-west-2")
            mock_http_client.invoke_endpoint.assert_called_once_with(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
                payload='{"message": "Hello with bearer token"}',  # Payload is converted to JSON string
                session_id=result.session_id,
                bearer_token=bearer_token,
            )

            # Verify response
            assert result.response == {"response": "http client response"}

    def test_invoke_bearer_token_with_session_id(self, tmp_path):
        """Test bearer token invocation with custom session ID."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello"}
        bearer_token = "bearer-token-456"
        custom_session_id = "custom-session-789"

        with patch(
            "bedrock_agentcore_starter_toolkit.services.runtime.HttpBedrockAgentCoreClient"
        ) as mock_http_client_class:
            mock_http_client = Mock()
            mock_http_client.invoke_endpoint.return_value = {"response": "success"}
            mock_http_client_class.return_value = mock_http_client

            result = invoke_bedrock_agentcore(
                config_path, payload, session_id=custom_session_id, bearer_token=bearer_token
            )

            # Verify custom session ID was used
            assert result.session_id == custom_session_id
            mock_http_client.invoke_endpoint.assert_called_once_with(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
                payload='{"message": "Hello"}',  # Payload is converted to JSON string
                session_id=custom_session_id,
                bearer_token=bearer_token,
            )

    def test_invoke_without_bearer_token_uses_boto3(self, mock_boto3_clients, tmp_path):
        """Test invocation without bearer token uses boto3 client."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello without bearer token"}

        with patch(
            "bedrock_agentcore_starter_toolkit.services.runtime.HttpBedrockAgentCoreClient"
        ) as mock_http_client_class:
            result = invoke_bedrock_agentcore(config_path, payload)

            # Verify HTTP client was NOT used
            mock_http_client_class.assert_not_called()

            # Verify boto3 client was used
            mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()
            assert result.response == {"response": [{"data": "test response"}]}

    def test_invoke_local_mode_success(self, tmp_path):
        """Test invoke_bedrock_agentcore with local_mode=True."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            oauth_configuration={"workload_name": "existing-workload-456"},
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello local mode!"}

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.invoke.IdentityClient"
            ) as mock_identity_client_class,
            patch(
                "bedrock_agentcore_starter_toolkit.services.runtime.LocalBedrockAgentCoreClient"
            ) as mock_local_client_class,
        ):
            # Mock IdentityClient
            mock_identity_client = Mock()
            mock_identity_client.get_workload_access_token.return_value = {
                "workloadAccessToken": "test-workload-token-123"
            }
            mock_identity_client_class.return_value = mock_identity_client

            # Mock LocalBedrockAgentCoreClient
            mock_local_client = Mock()
            mock_local_client.invoke_endpoint.return_value = {"response": "local client response"}
            mock_local_client_class.return_value = mock_local_client

            # Call with local_mode=True
            result = invoke_bedrock_agentcore(config_path, payload, local_mode=True)

            # Verify IdentityClient was created with correct region
            mock_identity_client_class.assert_called_once_with("us-west-2")

            # Verify get_workload_access_token was called correctly
            mock_identity_client.get_workload_access_token.assert_called_once_with(
                workload_name="existing-workload-456", user_token=None, user_id=None
            )

            # Verify LocalBedrockAgentCoreClient was created with correct URL
            mock_local_client_class.assert_called_once_with("http://0.0.0.0:8080")

            # Verify local client invoke_endpoint was called correctly
            mock_local_client.invoke_endpoint.assert_called_once_with(
                result.session_id, '{"message": "Hello local mode!"}', "test-workload-token-123"
            )

            # Verify result
            assert result.response == {"response": "local client response"}
            assert result.agent_arn is None  # Local mode doesn't have agent_arn
            assert isinstance(result.session_id, str)

    def test_invoke_local_mode_with_bearer_token(self, tmp_path):
        """Test invoke_bedrock_agentcore with local_mode=True and bearer token."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-east-1", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            oauth_configuration={"workload_name": "test-workload-789"},
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello with bearer token"}
        bearer_token = "user-bearer-token-456"
        user_id = "test-user-123"

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.invoke.IdentityClient"
            ) as mock_identity_client_class,
            patch(
                "bedrock_agentcore_starter_toolkit.services.runtime.LocalBedrockAgentCoreClient"
            ) as mock_local_client_class,
        ):
            # Mock IdentityClient
            mock_identity_client = Mock()
            mock_identity_client.get_workload_access_token.return_value = {
                "workloadAccessToken": "workload-token-with-user-context"
            }
            mock_identity_client_class.return_value = mock_identity_client

            # Mock LocalBedrockAgentCoreClient
            mock_local_client = Mock()
            mock_local_client.invoke_endpoint.return_value = {"response": "authenticated local response"}
            mock_local_client_class.return_value = mock_local_client

            # Call with local_mode=True, bearer_token, and user_id
            result = invoke_bedrock_agentcore(
                config_path, payload, local_mode=True, bearer_token=bearer_token, user_id=user_id
            )

            # Verify IdentityClient was created with correct region
            mock_identity_client_class.assert_called_once_with("us-east-1")

            # Verify get_workload_access_token was called with bearer token and user_id
            mock_identity_client.get_workload_access_token.assert_called_once_with(
                workload_name="test-workload-789", user_token=bearer_token, user_id=user_id
            )

            # Verify LocalBedrockAgentCoreClient was used
            mock_local_client_class.assert_called_once_with("http://0.0.0.0:8080")

            # Verify local client invoke was called with workload token
            mock_local_client.invoke_endpoint.assert_called_once_with(
                result.session_id, '{"message": "Hello with bearer token"}', "workload-token-with-user-context"
            )

            # Verify result
            assert result.response == {"response": "authenticated local response"}

    def test_invoke_local_mode_creates_workload_if_missing(self, tmp_path):
        """Test invoke_bedrock_agentcore local mode creates workload if not configured."""
        # Create config file without oauth_configuration
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            # No oauth_configuration - should trigger workload creation
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Test workload creation"}

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.invoke.IdentityClient"
            ) as mock_identity_client_class,
            patch(
                "bedrock_agentcore_starter_toolkit.services.runtime.LocalBedrockAgentCoreClient"
            ) as mock_local_client_class,
        ):
            # Mock IdentityClient
            mock_identity_client = Mock()
            mock_identity_client.create_workload_identity.return_value = {"name": "auto-created-workload-123"}
            mock_identity_client.get_workload_access_token.return_value = {"workloadAccessToken": "new-workload-token"}
            mock_identity_client_class.return_value = mock_identity_client

            # Mock LocalBedrockAgentCoreClient
            mock_local_client = Mock()
            mock_local_client.invoke_endpoint.return_value = {"response": "workload creation test"}
            mock_local_client_class.return_value = mock_local_client

            # Call with local_mode=True
            result = invoke_bedrock_agentcore(config_path, payload, local_mode=True)

            # Verify workload was created
            mock_identity_client.create_workload_identity.assert_called_once()

            # Verify get_workload_access_token was called with the created workload name
            mock_identity_client.get_workload_access_token.assert_called_once_with(
                workload_name="auto-created-workload-123", user_token=None, user_id=None
            )

            # Verify local client was called with the new workload token
            mock_local_client.invoke_endpoint.assert_called_once_with(
                result.session_id, '{"message": "Test workload creation"}', "new-workload-token"
            )

            # Verify config was updated with the new workload name
            from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

            updated_config = load_config(config_path)
            updated_agent = updated_config.get_agent_config("test-agent")
            assert updated_agent.oauth_configuration == {"workload_name": "auto-created-workload-123"}

            # Verify result
            assert result.response == {"response": "workload creation test"}


class TestGetWorkloadName:
    """Test _get_workload_name functionality."""

    def test_get_workload_name_existing(self, tmp_path):
        """Test _get_workload_name when workload_name already exists."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import _get_workload_name

        # Create config with existing workload_name
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            oauth_configuration={"workload_name": "existing-workload-123"},
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock identity client
        mock_identity_client = Mock()

        # Call function
        result = _get_workload_name(project_config, config_path, "test-agent", mock_identity_client)

        # Should return existing workload name without creating new one
        assert result == "existing-workload-123"
        mock_identity_client.create_workload_identity.assert_not_called()

    def test_get_workload_name_no_oauth_config(self, tmp_path):
        """Test _get_workload_name when oauth_configuration doesn't exist."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import _get_workload_name

        # Create config without oauth_configuration
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            # No oauth_configuration
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock identity client
        mock_identity_client = Mock()
        mock_identity_client.create_workload_identity.return_value = {"name": "created-workload-789"}

        # Call function
        result = _get_workload_name(project_config, config_path, "test-agent", mock_identity_client)

        # Should create new workload and return its name
        assert result == "created-workload-789"
        mock_identity_client.create_workload_identity.assert_called_once()

        # Verify oauth_configuration was created and config was saved
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        updated_config = load_config(config_path)
        updated_agent = updated_config.get_agent_config("test-agent")
        assert updated_agent.oauth_configuration == {"workload_name": "created-workload-789"}
