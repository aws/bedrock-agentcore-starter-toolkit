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
                custom_headers=None,
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
                custom_headers=None,
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
            mock_identity_client.get_workload_identity.return_value = {
                "name": "test-workload-identity",
                "allowedResourceOauth2ReturnUrls": [],
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
            mock_local_client_class.assert_called_once_with("http://127.0.0.1:8080")

            # Verify local client invoke_endpoint was called correctly
            mock_local_client.invoke_endpoint.assert_called_once_with(
                result.session_id,
                '{"message": "Hello local mode!"}',
                "test-workload-token-123",
                "http://localhost:8081/oauth2/callback",
                None,
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
            mock_identity_client.get_workload_identity.return_value = {
                "name": "test-workload-identity",
                "allowedResourceOauth2ReturnUrls": [],
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
            mock_local_client_class.assert_called_once_with("http://127.0.0.1:8080")

            # Verify local client invoke was called with workload token
            mock_local_client.invoke_endpoint.assert_called_once_with(
                result.session_id,
                '{"message": "Hello with bearer token"}',
                "workload-token-with-user-context",
                "http://localhost:8081/oauth2/callback",
                None,
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
            mock_identity_client.get_workload_identity.return_value = {
                "name": "test-workload-identity",
                "allowedResourceOauth2ReturnUrls": [],
            }
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
                result.session_id,
                '{"message": "Test workload creation"}',
                "new-workload-token",
                "http://localhost:8081/oauth2/callback",
                None,
            )

            # Verify config was updated with the new workload name
            from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

            updated_config = load_config(config_path)
            updated_agent = updated_config.get_agent_config("test-agent")
            assert updated_agent.oauth_configuration == {"workload_name": "auto-created-workload-123", "userId": None}

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

    def test_invoke_with_custom_headers_boto3_client(self, mock_boto3_clients, tmp_path):
        """Test invocation with custom headers using boto3 client."""
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

        payload = {"message": "Hello with headers"}
        custom_headers = {
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Context": "production",
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-ID": "123",
        }

        result = invoke_bedrock_agentcore(config_path, payload, custom_headers=custom_headers)

        # Verify result structure
        assert result.response == {"response": [{"data": "test response"}]}
        assert isinstance(result.session_id, str)
        assert result.agent_arn == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"

        # Verify boto3 client was called correctly (custom headers are handled
        # via event system, not as direct parameters)
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args

        # Verify basic call parameters (custom_headers are injected via
        # boto3 event system, not as direct params)
        assert (
            call_args[1]["agentRuntimeArn"]
            == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        )
        assert call_args[1]["payload"] == '{"message": "Hello with headers"}'
        assert call_args[1]["qualifier"] == "DEFAULT"
        assert "runtimeSessionId" in call_args[1]

    def test_invoke_with_custom_headers_http_client(self, tmp_path):
        """Test invocation with custom headers using HTTP client (bearer token)."""
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

        payload = {"message": "Hello with headers and bearer token"}
        bearer_token = "test-bearer-token-123"
        custom_headers = {
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Context": "production",
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Session": "abc123",
        }

        with patch(
            "bedrock_agentcore_starter_toolkit.services.runtime.HttpBedrockAgentCoreClient"
        ) as mock_http_client_class:
            mock_http_client = Mock()
            mock_http_client.invoke_endpoint.return_value = {"response": "http client response with headers"}
            mock_http_client_class.return_value = mock_http_client

            result = invoke_bedrock_agentcore(
                config_path, payload, bearer_token=bearer_token, custom_headers=custom_headers
            )

            # Verify HTTP client was used
            mock_http_client_class.assert_called_once_with("us-west-2")
            mock_http_client.invoke_endpoint.assert_called_once_with(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
                payload='{"message": "Hello with headers and bearer token"}',
                session_id=result.session_id,
                bearer_token=bearer_token,
                custom_headers=custom_headers,
            )

            # Verify response
            assert result.response == {"response": "http client response with headers"}

    def test_invoke_with_custom_headers_local_client(self, tmp_path):
        """Test invocation with custom headers using local client."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            oauth_configuration={"workload_name": "test-workload-456"},
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        payload = {"message": "Hello local mode with headers"}
        custom_headers = {
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Environment": "local",
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Debug": "true",
        }

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
                "workloadAccessToken": "test-workload-token-456"
            }
            mock_identity_client.get_workload_identity.return_value = {
                "name": "test-workload-identity",
                "allowedResourceOauth2ReturnUrls": [],
            }
            mock_identity_client_class.return_value = mock_identity_client

            # Mock LocalBedrockAgentCoreClient
            mock_local_client = Mock()
            mock_local_client.invoke_endpoint.return_value = {"response": "local client response with headers"}
            mock_local_client_class.return_value = mock_local_client

            # Call with local_mode=True and custom_headers
            result = invoke_bedrock_agentcore(config_path, payload, local_mode=True, custom_headers=custom_headers)

            # Verify LocalBedrockAgentCoreClient was used with headers
            mock_local_client_class.assert_called_once_with("http://127.0.0.1:8080")
            mock_local_client.invoke_endpoint.assert_called_once_with(
                result.session_id,
                '{"message": "Hello local mode with headers"}',
                "test-workload-token-456",
                "http://localhost:8081/oauth2/callback",
                custom_headers,
            )

            # Verify result
            assert result.response == {"response": "local client response with headers"}

    def test_invoke_with_empty_custom_headers(self, mock_boto3_clients, tmp_path):
        """Test invocation with empty custom headers dict."""
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

        payload = {"message": "Hello without headers"}
        empty_headers = {}

        result = invoke_bedrock_agentcore(config_path, payload, custom_headers=empty_headers)

        # Verify boto3 client was called correctly (empty custom headers handled via event system)
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args
        assert result.response is not None

        # Verify basic call parameters (custom_headers are injected via boto3 event system, not as direct params)
        assert (
            call_args[1]["agentRuntimeArn"]
            == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        )
        assert call_args[1]["payload"] == '{"message": "Hello without headers"}'
        assert call_args[1]["qualifier"] == "DEFAULT"

    def test_invoke_with_none_custom_headers(self, mock_boto3_clients, tmp_path):
        """Test invocation with None custom headers."""
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

        payload = {"message": "Hello without headers"}

        result = invoke_bedrock_agentcore(config_path, payload, custom_headers=None)

        # Verify boto3 client was called correctly (None custom headers handled via event system)
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args
        assert result.response is not None

        # Verify basic call parameters (custom_headers are injected via boto3 event system, not as direct params)
        assert (
            call_args[1]["agentRuntimeArn"]
            == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        )
        assert call_args[1]["payload"] == '{"message": "Hello without headers"}'
        assert call_args[1]["qualifier"] == "DEFAULT"

    def test_invoke_custom_headers_with_session_id(self, mock_boto3_clients, tmp_path):
        """Test invocation with both custom headers and custom session ID."""
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

        payload = {"message": "Hello with headers and session"}
        custom_headers = {"X-Amzn-Bedrock-AgentCore-Runtime-Custom-Context": "test"}
        custom_session_id = "custom-session-789"

        result = invoke_bedrock_agentcore(
            config_path, payload, session_id=custom_session_id, custom_headers=custom_headers
        )

        # Verify both session ID and headers were used
        assert result.session_id == custom_session_id

        # Verify boto3 client was called correctly (custom headers are handled
        # via event system, not as direct parameters)
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()
        call_args = mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.call_args
        assert call_args[1]["runtimeSessionId"] == custom_session_id

        # Verify basic call parameters (custom_headers are injected via boto3 event system, not as direct params)
        assert (
            call_args[1]["agentRuntimeArn"]
            == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        )
        assert call_args[1]["payload"] == '{"message": "Hello with headers and session"}'
        assert call_args[1]["qualifier"] == "DEFAULT"

    def test_invoke_sync_with_streaming(self, mock_boto3_clients, tmp_path):
        """Test sync invocation with streaming response (covers lines 40-76)."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                network_configuration=NetworkConfiguration(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock streaming response
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.return_value = {
            "response": [{"chunk": {"text": "Part 1 "}}, {"chunk": {"text": "Part 2"}}, {"data": "final response"}]
        }

        result = invoke_bedrock_agentcore(config_path, {"message": "Test streaming"})

        assert result.response is not None
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once()

    def test_invoke_with_invalid_json_response(self, mock_boto3_clients, tmp_path):
        """Test handling of invalid JSON in response (covers line 122)."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                network_configuration=NetworkConfiguration(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Return response that might contain invalid JSON
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.return_value = {
            "response": [{"data": "{invalid json"}]
        }

        result = invoke_bedrock_agentcore(config_path, {"message": "Test invalid json"})

        # Should handle gracefully
        assert result.response is not None

    def test_invoke_api_exception(self, mock_boto3_clients, tmp_path):
        """Test API exception handling (covers line 127)."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                network_configuration=NetworkConfiguration(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock API error
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            invoke_bedrock_agentcore(config_path, {"message": "Test error"})

    def test_invoke_memory_import_error(self, mock_boto3_clients, tmp_path):
        """Test invoke when MemoryManager import fails (covers lines 68-70)."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                network_configuration=NetworkConfiguration(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
            ),
            memory=MemoryConfig(
                mode="STM_AND_LTM",
                memory_id="mem-12345",
                first_invoke_memory_check_done=False,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        with patch.dict("sys.modules", {"bedrock_agentcore_starter_toolkit.operations.memory.manager": None}):
            # Should continue despite import error
            result = invoke_bedrock_agentcore(config_path, {"message": "test"})
            assert result is not None


class TestUpdateWorkloadIdentityWithCallbackUrl:
    def test_update_workload_identity_callback_url_already_exists(self):
        from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import (
            _update_workload_identity_with_oauth2_callback_url,
        )

        mock_identity_client = Mock()
        mock_identity_client.get_workload_identity.return_value = {
            "allowedResourceOauth2ReturnUrls": ["http://localhost:8081/oauth2/callback", "https://example.com/callback"]
        }

        _update_workload_identity_with_oauth2_callback_url(
            mock_identity_client, "test-workload", "http://localhost:8081/oauth2/callback"
        )

        mock_identity_client.get_workload_identity.assert_called_once_with(name="test-workload")
        mock_identity_client.update_workload_identity.assert_not_called()

    def test_update_workload_identity_callback_url_new(self):
        from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import (
            _update_workload_identity_with_oauth2_callback_url,
        )

        mock_identity_client = Mock()
        mock_identity_client.get_workload_identity.return_value = {
            "allowedResourceOauth2ReturnUrls": ["https://example.com/callback"]
        }

        _update_workload_identity_with_oauth2_callback_url(
            mock_identity_client, "test-workload", "http://localhost:8081/oauth2/callback"
        )

        mock_identity_client.get_workload_identity.assert_called_once_with(name="test-workload")
        mock_identity_client.update_workload_identity.assert_called_once_with(
            name="test-workload",
            allowed_resource_oauth_2_return_urls=[
                "https://example.com/callback",
                "http://localhost:8081/oauth2/callback",
            ],
        )

    def test_update_workload_identity_callback_url_empty_list(self):
        from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import (
            _update_workload_identity_with_oauth2_callback_url,
        )

        mock_identity_client = Mock()
        mock_identity_client.get_workload_identity.return_value = {"allowedResourceOauth2ReturnUrls": []}

        _update_workload_identity_with_oauth2_callback_url(
            mock_identity_client, "test-workload", "http://localhost:8081/oauth2/callback"
        )

        mock_identity_client.get_workload_identity.assert_called_once_with(name="test-workload")
        mock_identity_client.update_workload_identity.assert_called_once_with(
            name="test-workload", allowed_resource_oauth_2_return_urls=["http://localhost:8081/oauth2/callback"]
        )

    def test_update_workload_identity_callback_url_missing_from_response(self):
        from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import (
            _update_workload_identity_with_oauth2_callback_url,
        )

        mock_identity_client = Mock()
        mock_identity_client.get_workload_identity.return_value = {}

        _update_workload_identity_with_oauth2_callback_url(
            mock_identity_client, "test-workload", "http://localhost:8081/oauth2/callback"
        )

        mock_identity_client.get_workload_identity.assert_called_once_with(name="test-workload")
        mock_identity_client.update_workload_identity.assert_called_once_with(
            name="test-workload", allowed_resource_oauth_2_return_urls=["http://localhost:8081/oauth2/callback"]
        )
