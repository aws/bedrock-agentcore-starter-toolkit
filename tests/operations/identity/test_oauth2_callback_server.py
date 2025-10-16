from unittest.mock import Mock, patch

from bedrock_agentcore.services.identity import UserIdIdentifier
from starlette.testclient import TestClient

from bedrock_agentcore_starter_toolkit.operations.identity.oauth2_callback_server import (
    OAUTH2_CALLBACK_ENDPOINT,
    WORKLOAD_USER_ID,
    BedrockAgentCoreIdentity3loCallback,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    NetworkConfiguration,
    ObservabilityConfig,
)


def create_test_config(tmp_path, *, agent_name="test-agent", user_id="test-user-id", region="us-west-2"):
    config_path = tmp_path / ".bedrock_agentcore.yaml"

    agent_config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint="test_agent.py",
        container_runtime="docker",
        aws=AWSConfig(
            region=region,
            account="123456789012",
            execution_role=None,
            execution_role_auto_create=True,
            ecr_repository=None,
            ecr_auto_create=True,
            network_configuration=NetworkConfiguration(),
            observability=ObservabilityConfig(),
        ),
        oauth_configuration={WORKLOAD_USER_ID: user_id} if user_id else {},
    )

    project_config = BedrockAgentCoreConfigSchema(default_agent=agent_name, agents={agent_name: agent_config})
    save_config(project_config, config_path)

    return config_path


class TestBedrockAgentCoreIdentity3loCallback:
    def test_init(self, tmp_path):
        config_path = create_test_config(tmp_path)
        server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name="test-agent")

        assert server.config_path == config_path
        assert server.agent_name == "test-agent"
        assert len(server.routes) == 1
        assert server.routes[0].path == OAUTH2_CALLBACK_ENDPOINT

    def test_get_callback_endpoint(self):
        endpoint = BedrockAgentCoreIdentity3loCallback.get_oauth2_callback_endpoint()
        assert endpoint == "http://localhost:8081/oauth2/callback"

    def test_handle_3lo_callback_missing_session_id(self, tmp_path):
        config_path = create_test_config(tmp_path)
        server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name="test-agent")
        client = TestClient(server)
        response = client.get(OAUTH2_CALLBACK_ENDPOINT)

        assert response.status_code == 400
        assert response.json().get("message") == "missing session_id query parameter"

    @patch("bedrock_agentcore_starter_toolkit.operations.identity.oauth2_callback_server.IdentityClient")
    def test_handle_3lo_callback_success(self, mock_identity_client, tmp_path):
        config_path = create_test_config(tmp_path)
        server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name="test-agent")

        mock_client_instance = Mock()
        mock_identity_client.return_value = mock_client_instance

        client = TestClient(server)
        response = client.get(f"{OAUTH2_CALLBACK_ENDPOINT}?session_id=test-session-123")

        assert response.status_code == 200
        assert response.json().get("message") == "OAuth2 3LO flow completed successfully"
        mock_identity_client.assert_called_once_with("us-west-2")
        mock_client_instance.complete_resource_token_auth.assert_called_once_with(
            session_uri="test-session-123", user_identifier=UserIdIdentifier(user_id="test-user-id")
        )

    def test_handle_3lo_callback_missing_user_id(self, tmp_path):
        config_path = create_test_config(tmp_path, user_id="")
        server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name="test-agent")
        client = TestClient(server)
        response = client.get(f"{OAUTH2_CALLBACK_ENDPOINT}?session_id=test-session-123")

        assert response.status_code == 500
        assert response.json().get("message") == "Internal Server Error"

    def test_handle_3lo_callback_missing_region(self, tmp_path):
        config_path = create_test_config(tmp_path, region="")
        server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name="test-agent")
        client = TestClient(server)
        response = client.get(f"{OAUTH2_CALLBACK_ENDPOINT}?session_id=test-session-123")

        assert response.status_code == 500
        assert response.json().get("message") == "Internal Server Error"
