"""Simple tests for cross-account launch functionality."""

from unittest.mock import Mock, patch
import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _execute_codebuild_workflow
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    NetworkConfiguration,
    ObservabilityConfig,
    BedrockAgentCoreDeploymentInfo,
    CodeBuildConfig,
)


class TestLaunchCrossAccount:
    """Test cross-account functionality in launch operations."""

    def test_codebuild_service_initialization_cross_account(self, tmp_path):
        """Test CodeBuildService is initialized with cross-account role."""
        # Create agent config with cross-account CodeBuild role
        aws_config = AWSConfig(
            account="123456789012",
            region="us-west-2",
            execution_role="arn:aws:iam::123456789012:role/ExecutionRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            network_configuration=NetworkConfiguration(),
            observability=ObservabilityConfig(),
        )
        
        codebuild_config = CodeBuildConfig()
        codebuild_config.execution_role = "arn:aws:iam::987654321098:role/BuildRole"
        
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=aws_config,
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            codebuild=codebuild_config,
        )
        
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="test-agent",
            agents={"test-agent": agent_config}
        )
        
        config_path = tmp_path / "config.yaml"
        
        with patch('bedrock_agentcore_starter_toolkit.operations.runtime.launch.CodeBuildService') as mock_cb_service, \
             patch('bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_ecr_repository') as mock_ecr, \
             patch('bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role') as mock_role, \
             patch("boto3.Session") as mock_session:
            
            # Setup mocks
            mock_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo"
            mock_role.return_value = "arn:aws:iam::123456789012:role/ExecutionRole"
            
            mock_service_instance = Mock()
            mock_service_instance.upload_source.return_value = "s3://bucket/source.zip"
            mock_service_instance.create_or_update_project.return_value = "test-project"
            mock_service_instance.start_build.return_value = "build-123"
            mock_service_instance.wait_for_completion.return_value = None
            mock_service_instance.source_bucket = "test-bucket"
            mock_cb_service.return_value = mock_service_instance
            
            deployment_session = Mock()
            # Mock STS client for account detection
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
            deployment_session.client.return_value = mock_sts
            mock_session.return_value = deployment_session
            
            # Execute
            _execute_codebuild_workflow(
                config_path=config_path,
                agent_name="test-agent",
                agent_config=agent_config,
                project_config=project_config,
                ecr_only=False
            )
            
            # Verify CodeBuildService was called with cross-account role
            mock_cb_service.assert_called_once_with(
                deployment_session,
                "arn:aws:iam::987654321098:role/BuildRole"
            )

    def test_codebuild_service_initialization_same_account(self, tmp_path):
        """Test CodeBuildService is initialized without cross-account role."""
        # Create agent config without cross-account CodeBuild role
        aws_config = AWSConfig(
            account="123456789012",
            region="us-west-2",
            execution_role="arn:aws:iam::123456789012:role/ExecutionRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            network_configuration=NetworkConfiguration(),
            observability=ObservabilityConfig(),
        )
        
        codebuild_config = CodeBuildConfig()
        # No execution_role set - same account scenario
        
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=aws_config,
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            codebuild=codebuild_config,
        )
        
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="test-agent",
            agents={"test-agent": agent_config}
        )
        
        config_path = tmp_path / "config.yaml"
        
        with patch('bedrock_agentcore_starter_toolkit.operations.runtime.launch.CodeBuildService') as mock_cb_service, \
             patch('bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_ecr_repository') as mock_ecr, \
             patch('bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role') as mock_role, \
             patch("boto3.Session") as mock_session:
            
            # Setup mocks
            mock_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo"
            mock_role.return_value = "arn:aws:iam::123456789012:role/ExecutionRole"
            
            mock_service_instance = Mock()
            mock_service_instance.create_codebuild_execution_role.return_value = "arn:aws:iam::123456789012:role/CodeBuildRole"
            mock_service_instance.upload_source.return_value = "s3://bucket/source.zip"
            mock_service_instance.create_or_update_project.return_value = "test-project"
            mock_service_instance.start_build.return_value = "build-123"
            mock_service_instance.wait_for_completion.return_value = None
            mock_service_instance.source_bucket = "test-bucket"
            mock_cb_service.return_value = mock_service_instance
            
            deployment_session = Mock()
            # Mock STS client for account detection
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
            deployment_session.client.return_value = mock_sts
            mock_session.return_value = deployment_session
            
            # Execute
            _execute_codebuild_workflow(
                config_path=config_path,
                agent_name="test-agent",
                agent_config=agent_config,
                project_config=project_config,
                ecr_only=False
            )
            
            # Verify CodeBuildService was called without cross-account role
            mock_cb_service.assert_called_once_with(deployment_session, None)
