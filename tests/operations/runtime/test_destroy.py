"""Tests for Bedrock AgentCore destroy operation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.runtime.destroy import destroy_bedrock_agentcore
from bedrock_agentcore_starter_toolkit.operations.runtime.models import DestroyResult
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
)


# Test Helper Functions
def create_test_config(
    tmp_path,
    agent_name="test-agent",
    entrypoint="test_agent.py",
    region="us-west-2",
    account="123456789012",
    execution_role="arn:aws:iam::123456789012:role/test-role",
    ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-agent",
    agent_id="test-agent-id",
    agent_arn="arn:aws:bedrock:us-west-2:123456789012:agent-runtime/test-agent-id",
):
    """Create a test configuration with deployment info."""
    config_path = tmp_path / ".bedrock_agentcore.yaml"
    
    deployment_info = BedrockAgentCoreDeploymentInfo(
        agent_id=agent_id,
        agent_arn=agent_arn,
    ) if agent_id else None
    
    agent_config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint=entrypoint,
        container_runtime="docker",
        aws=AWSConfig(
            region=region,
            account=account,
            execution_role=execution_role,
            execution_role_auto_create=False,
            ecr_repository=ecr_repository,
            ecr_auto_create=False,
            network_configuration=NetworkConfiguration(),
            observability=ObservabilityConfig(),
        ),
        bedrock_agentcore=deployment_info,
    )
    
    project_config = BedrockAgentCoreConfigSchema(
        default_agent=agent_name,
        agents={agent_name: agent_config}
    )
    
    save_config(project_config, config_path)
    return config_path


def create_undeployed_config(tmp_path, agent_name="test-agent"):
    """Create a test configuration without deployment info."""
    config_path = tmp_path / ".bedrock_agentcore.yaml"
    
    agent_config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint="test_agent.py",
        container_runtime="docker",
        aws=AWSConfig(
            region="us-west-2",
            account="123456789012",
            execution_role=None,
            execution_role_auto_create=True,
            ecr_repository=None,
            ecr_auto_create=True,
            network_configuration=NetworkConfiguration(),  
            observability=ObservabilityConfig(),
        ),
        bedrock_agentcore=None,  # Not deployed
    )
    
    project_config = BedrockAgentCoreConfigSchema(
        default_agent=agent_name,
        agents={agent_name: agent_config}
    )
    
    save_config(project_config, config_path)
    return config_path


class TestDestroyBedrockAgentCore:
    """Test destroy_bedrock_agentcore function."""

    def test_destroy_nonexistent_config(self, tmp_path):
        """Test destroy with nonexistent configuration file."""
        config_path = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            destroy_bedrock_agentcore(config_path)

    def test_destroy_nonexistent_agent(self, tmp_path):
        """Test destroy with nonexistent agent."""
        config_path = create_test_config(tmp_path)
        
        with pytest.raises(ValueError, match="Agent 'nonexistent' not found"):
            destroy_bedrock_agentcore(config_path, agent_name="nonexistent")

    def test_destroy_undeployed_agent(self, tmp_path):
        """Test destroy with undeployed agent."""
        config_path = create_undeployed_config(tmp_path)
        
        result = destroy_bedrock_agentcore(config_path, dry_run=True)
        
        assert isinstance(result, DestroyResult)
        assert result.agent_name == "test-agent"
        assert len(result.warnings) == 1
        assert "not deployed" in result.warnings[0]
        assert len(result.resources_removed) == 0

    def test_destroy_dry_run(self, tmp_path):
        """Test dry run mode."""
        config_path = create_test_config(tmp_path)
        
        with patch("boto3.Session") as mock_session:
            result = destroy_bedrock_agentcore(config_path, dry_run=True)
        
        assert isinstance(result, DestroyResult)
        assert result.agent_name == "test-agent"
        assert result.dry_run is True
        assert len(result.resources_removed) > 0
        assert all("DRY RUN" in resource for resource in result.resources_removed)
        mock_session.assert_not_called()  # No AWS calls in dry run

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.destroy.BedrockAgentCoreClient")
    @patch("boto3.Session")
    def test_destroy_success(self, mock_session, mock_client_class, tmp_path):
        """Test successful destroy operation."""
        config_path = create_test_config(tmp_path)
        
        # Mock AWS clients
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_agentcore_client = MagicMock()
        mock_client_class.return_value = mock_agentcore_client
        
        mock_ecr_client = MagicMock()
        mock_codebuild_client = MagicMock()
        mock_iam_client = MagicMock()
        
        mock_session_instance.client.side_effect = lambda service: {
            "ecr": mock_ecr_client,
            "codebuild": mock_codebuild_client,
            "iam": mock_iam_client,
        }[service]
        
        # Mock successful API calls
        mock_agentcore_client.list_agent_runtime_endpoints.return_value = {
            "agentRuntimeEndpointSummaries": [
                {"agentRuntimeEndpointArn": "arn:aws:bedrock:us-west-2:123456789012:agent-runtime-endpoint/test"}
            ]
        }
        mock_ecr_client.list_images.return_value = {
            "imageDetails": [{"imageTags": ["latest"]}]
        }
        mock_ecr_client.batch_delete_image.return_value = {}
        mock_codebuild_client.delete_project.return_value = {}
        mock_iam_client.list_attached_role_policies.return_value = {"AttachedPolicies": []}
        mock_iam_client.list_role_policies.return_value = {"PolicyNames": []}
        mock_iam_client.delete_role.return_value = {}
        
        result = destroy_bedrock_agentcore(config_path, dry_run=False)
        
        assert isinstance(result, DestroyResult)
        assert result.agent_name == "test-agent"
        assert result.dry_run is False
        assert len(result.resources_removed) > 0
        assert len(result.errors) == 0
        
        # Verify AWS API calls were made
        mock_agentcore_client.delete_agent_runtime_endpoint.assert_called()
        mock_agentcore_client.delete_agent_runtime.assert_called()
        mock_ecr_client.batch_delete_image.assert_called()
        mock_codebuild_client.delete_project.assert_called()

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.destroy.BedrockAgentCoreClient")
    @patch("boto3.Session")
    def test_destroy_with_errors(self, mock_session, mock_client_class, tmp_path):
        """Test destroy operation with errors."""
        config_path = create_test_config(tmp_path)
        
        # Mock AWS clients
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_agentcore_client = MagicMock()
        mock_client_class.return_value = mock_agentcore_client
        
        mock_ecr_client = MagicMock()
        mock_codebuild_client = MagicMock()
        mock_iam_client = MagicMock()
        
        mock_session_instance.client.side_effect = lambda service: {
            "ecr": mock_ecr_client,
            "codebuild": mock_codebuild_client,
            "iam": mock_iam_client,
        }[service]
        
        # Mock API errors
        mock_agentcore_client.delete_agent_runtime.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "Server error"}},
            "DeleteAgentRuntime"
        )
        
        result = destroy_bedrock_agentcore(config_path, dry_run=False)
        
        assert isinstance(result, DestroyResult)
        assert len(result.errors) > 0
        assert "InternalServerError" in str(result.errors)

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.destroy.BedrockAgentCoreClient")
    @patch("boto3.Session")
    def test_destroy_resource_not_found(self, mock_session, mock_client_class, tmp_path):
        """Test destroy operation when resources are not found."""
        config_path = create_test_config(tmp_path)
        
        # Mock AWS clients
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_agentcore_client = MagicMock()
        mock_client_class.return_value = mock_agentcore_client
        
        mock_ecr_client = MagicMock()
        mock_codebuild_client = MagicMock()
        mock_iam_client = MagicMock()
        
        mock_session_instance.client.side_effect = lambda service: {
            "ecr": mock_ecr_client,
            "codebuild": mock_codebuild_client,
            "iam": mock_iam_client,
        }[service]
        
        # Mock ResourceNotFound errors (should be treated as warnings, not errors)
        mock_agentcore_client.delete_agent_runtime.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}},
            "DeleteAgentRuntime"
        )
        mock_ecr_client.list_images.side_effect = ClientError(
            {"Error": {"Code": "RepositoryNotFoundException", "Message": "Repository not found"}},
            "ListImages"
        )
        mock_codebuild_client.delete_project.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Project not found"}},
            "DeleteProject"
        )
        mock_iam_client.delete_role.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity", "Message": "Role not found"}},
            "DeleteRole"
        )
        
        result = destroy_bedrock_agentcore(config_path, dry_run=False)
        
        assert isinstance(result, DestroyResult)
        assert len(result.errors) == 0  # ResourceNotFound should be warnings, not errors
        assert len(result.warnings) > 0

    def test_destroy_multiple_agents_same_role(self, tmp_path):
        """Test destroy when multiple agents use the same IAM role."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        
        shared_role = "arn:aws:iam::123456789012:role/shared-role"
        
        # Create config with two agents sharing the same role
        agent1 = BedrockAgentCoreAgentSchema(
            name="agent1",
            entrypoint="agent1.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role=shared_role,
                execution_role_auto_create=False,
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/agent1",
                ecr_auto_create=False,
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="agent1-id",
                agent_arn="arn:aws:bedrock:us-west-2:123456789012:agent-runtime/agent1-id",
            ),
        )
        
        agent2 = BedrockAgentCoreAgentSchema(
            name="agent2",
            entrypoint="agent2.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role=shared_role,  # Same role as agent1
                execution_role_auto_create=False,
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/agent2",
                ecr_auto_create=False,
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="agent2-id",
                agent_arn="arn:aws:bedrock:us-west-2:123456789012:agent-runtime/agent2-id",
            ),
        )
        
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="agent1",
            agents={"agent1": agent1, "agent2": agent2}
        )
        
        save_config(project_config, config_path)
        
        with patch("boto3.Session") as mock_session:
            result = destroy_bedrock_agentcore(config_path, agent_name="agent1", dry_run=True)
        
        assert isinstance(result, DestroyResult)
        # Should warn that role is shared and not destroy it
        role_warnings = [w for w in result.warnings if "shared-role" in w and "other agents" in w]
        assert len(role_warnings) > 0

    def test_config_cleanup_after_destroy(self, tmp_path):
        """Test that agent configuration is cleaned up after successful destroy."""
        config_path = create_test_config(tmp_path)
        
        with patch("boto3.Session"), \
             patch("bedrock_agentcore_starter_toolkit.operations.runtime.destroy.BedrockAgentCoreClient"):
            
            result = destroy_bedrock_agentcore(config_path, dry_run=False)
        
        # Verify configuration was updated
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config
        updated_config = load_config(config_path)
        agent_config = updated_config.get_agent_config("test-agent")
        
        assert agent_config.bedrock_agentcore is None  # Deployment info should be cleared
        assert "Agent deployment configuration: test-agent" in result.resources_removed


class TestDestroyHelpers:
    """Test helper functions in destroy module."""

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.destroy.BedrockAgentCoreClient")
    @patch("boto3.Session")
    def test_destroy_agentcore_endpoint_no_agent_id(self, mock_session, mock_client_class, tmp_path):
        """Test endpoint destruction when agent has no ID."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.destroy import _destroy_agentcore_endpoint
        from bedrock_agentcore_starter_toolkit.operations.runtime.models import DestroyResult
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import BedrockAgentCoreAgentSchema, AWSConfig
        
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # Agent config without deployment info
        agent_config = MagicMock()
        agent_config.bedrock_agentcore = None
        
        result = DestroyResult(agent_name="test", dry_run=False)
        
        _destroy_agentcore_endpoint(mock_session_instance, agent_config, result, False)
        
        # Should not make any API calls
        mock_client_class.assert_not_called()
        assert len(result.warnings) == 0  # No warnings expected for undeployed agent

    def test_destroy_result_model(self):
        """Test DestroyResult model."""
        result = DestroyResult(
            agent_name="test-agent",
            resources_removed=["resource1", "resource2"],
            warnings=["warning1"],
            errors=["error1"],
            dry_run=True
        )
        
        assert result.agent_name == "test-agent"
        assert len(result.resources_removed) == 2
        assert len(result.warnings) == 1
        assert len(result.errors) == 1
        assert result.dry_run is True
        
        # Test default values
        result_defaults = DestroyResult(agent_name="test")
        assert result_defaults.resources_removed == []
        assert result_defaults.warnings == []
        assert result_defaults.errors == []
        assert result_defaults.dry_run is False