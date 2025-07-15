"""Tests for Bedrock AgentCore ECR service integration."""

import pytest

from bedrock_agentcore_starter_toolkit.services.ecr import (
    create_ecr_repository,
    deploy_to_ecr,
    get_account_id,
    get_region,
)


class TestECRService:
    """Test ECR service functionality."""

    def test_create_ecr_repository(self, mock_boto3_clients):
        """Test ECR repository creation (new and existing)."""
        # Test creating new repository
        repo_uri = create_ecr_repository("test-repo", "us-west-2")
        assert repo_uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo"
        mock_boto3_clients["ecr"].create_repository.assert_called_once_with(repositoryName="test-repo")

        # Test existing repository
        mock_boto3_clients["ecr"].create_repository.side_effect = mock_boto3_clients[
            "ecr"
        ].exceptions.RepositoryAlreadyExistsException()
        mock_boto3_clients["ecr"].describe_repositories.return_value = {
            "repositories": [{"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/existing-repo"}]
        }

        repo_uri = create_ecr_repository("existing-repo", "us-west-2")
        assert repo_uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/existing-repo"
        mock_boto3_clients["ecr"].describe_repositories.assert_called_once_with(repositoryNames=["existing-repo"])

    def test_deploy_to_ecr_full_flow(self, mock_boto3_clients, mock_container_runtime):
        """Test complete ECR deployment flow."""
        # Mock successful deployment
        mock_container_runtime.login.return_value = True
        mock_container_runtime.tag.return_value = True
        mock_container_runtime.push.return_value = True

        ecr_tag = deploy_to_ecr("local-image:latest", "test-repo", "us-west-2", mock_container_runtime)

        # Verify ECR operations
        assert ecr_tag == "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo:latest"
        mock_boto3_clients["ecr"].get_authorization_token.assert_called_once()

        # Verify container runtime operations
        mock_container_runtime.login.assert_called_once()
        mock_container_runtime.tag.assert_called_once_with(
            "local-image:latest", "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo:latest"
        )
        mock_container_runtime.push.assert_called_once_with(
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo:latest"
        )

    def test_ecr_auth_failure(self, mock_boto3_clients, mock_container_runtime):
        """Test ECR authentication error handling."""
        # Mock login failure
        mock_container_runtime.login.return_value = False

        with pytest.raises(RuntimeError, match="Failed to login to ECR"):
            deploy_to_ecr("local-image:latest", "test-repo", "us-west-2", mock_container_runtime)

        # Mock tag failure
        mock_container_runtime.login.return_value = True
        mock_container_runtime.tag.return_value = False

        with pytest.raises(RuntimeError, match="Failed to tag image"):
            deploy_to_ecr("local-image:latest", "test-repo", "us-west-2", mock_container_runtime)

        # Mock push failure
        mock_container_runtime.tag.return_value = True
        mock_container_runtime.push.return_value = False

        with pytest.raises(RuntimeError, match="Failed to push image to ECR"):
            deploy_to_ecr("local-image:latest", "test-repo", "us-west-2", mock_container_runtime)

    def test_get_account_id(self, mock_boto3_clients):
        """Test AWS account ID retrieval."""
        account_id = get_account_id()
        assert account_id == "123456789012"
        mock_boto3_clients["sts"].get_caller_identity.assert_called_once()

    def test_get_region(self, mock_boto3_clients):
        """Test AWS region detection."""
        region = get_region()
        assert region == "us-west-2"

        # Test default fallback
        mock_boto3_clients["session"].region_name = None
        region = get_region()
        assert region == "us-west-2"  # Default fallback
