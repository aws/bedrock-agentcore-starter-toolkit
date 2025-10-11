"""Tests for Bedrock AgentCore ECR service integration."""

import pytest

from bedrock_agentcore_starter_toolkit.services.ecr import (
    create_ecr_repository,
    deploy_to_ecr,
    get_account_id,
    get_or_create_ecr_repository,
    get_region,
    sanitize_ecr_repo_name,
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


class TestSanitizeECRRepoName:
    """Test sanitize_ecr_repo_name functionality."""

    def test_sanitize_basic_name(self):
        """Test sanitization of basic agent names."""
        # Normal names should be lowercased
        assert sanitize_ecr_repo_name("TestAgent") == "testagent"
        assert sanitize_ecr_repo_name("my-agent") == "my-agent"
        # Underscores are valid ECR characters and are kept
        assert sanitize_ecr_repo_name("agent_123") == "agent_123"

    def test_sanitize_name_starting_with_non_alphanumeric(self):
        """Test names starting with non-alphanumeric characters."""
        # Line 33: Prefix with 'a' if starts with non-alphanumeric
        assert sanitize_ecr_repo_name("-agent") == "a-agent"
        # Underscore is kept in ECR names, not replaced
        assert sanitize_ecr_repo_name("_test") == "a_test"
        # Multiple hyphens collapsed then prefixed
        assert sanitize_ecr_repo_name("---test") == "a-test"

    def test_sanitize_short_name(self):
        """Test names shorter than 2 characters."""
        # Line 43: Append "-agent" if too short
        assert sanitize_ecr_repo_name("a") == "a-agent"
        assert sanitize_ecr_repo_name("x") == "x-agent"
        assert sanitize_ecr_repo_name("1") == "1-agent"

    def test_sanitize_long_name(self):
        """Test names longer than 200 characters."""
        # Line 47: Truncate if too long
        long_name = "a" * 250
        result = sanitize_ecr_repo_name(long_name)
        assert len(result) == 200
        assert result == "a" * 200

        # Test truncation with trailing hyphens
        long_name_with_hyphens = "a" * 195 + "-----"  # 200 chars ending in hyphens
        result = sanitize_ecr_repo_name(long_name_with_hyphens)
        assert len(result) <= 200
        # Should strip trailing hyphens after truncation
        assert not result.endswith("-")

    def test_sanitize_name_with_invalid_chars(self):
        """Test names with invalid characters."""
        # Replace invalid characters with hyphens
        assert sanitize_ecr_repo_name("my@agent") == "my-agent"
        assert sanitize_ecr_repo_name("agent#123") == "agent-123"
        assert sanitize_ecr_repo_name("test$agent%") == "test-agent"

    def test_sanitize_complex_name(self):
        """Test complex names with multiple sanitization rules."""
        # Multiple hyphens should be collapsed
        assert sanitize_ecr_repo_name("my---agent") == "my-agent"
        # Trailing hyphens should be stripped
        assert sanitize_ecr_repo_name("my-agent---") == "my-agent"
        # Underscores consecutive with hyphens
        assert sanitize_ecr_repo_name("my__agent") == "my-agent"


class TestGetOrCreateECRRepository:
    """Test get_or_create_ecr_repository functionality."""

    def test_get_existing_repository(self, mock_boto3_clients, capsys):
        """Test getting an existing ECR repository."""
        # Line 96-99: Test the RepositoryNotFoundException path
        # Mock repository already exists
        mock_boto3_clients["ecr"].describe_repositories.return_value = {
            "repositories": [{"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-test"}]
        }

        result = get_or_create_ecr_repository("test", "us-west-2")

        assert result == "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-test"
        mock_boto3_clients["ecr"].describe_repositories.assert_called_once_with(
            repositoryNames=["bedrock-agentcore-test"]
        )

        # Verify success message printed
        captured = capsys.readouterr()
        assert "Reusing existing ECR repository" in captured.out

    def test_create_new_repository(self, mock_boto3_clients, capsys):
        """Test creating a new ECR repository when it doesn't exist."""
        # Line 96-99: Test the RepositoryNotFoundException path
        # Mock repository doesn't exist
        mock_boto3_clients["ecr"].describe_repositories.side_effect = mock_boto3_clients[
            "ecr"
        ].exceptions.RepositoryNotFoundException()

        # Mock create_repository success
        mock_boto3_clients["ecr"].create_repository.return_value = {
            "repository": {"repositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-newagent"}
        }

        result = get_or_create_ecr_repository("newagent", "us-west-2")

        assert result == "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock-agentcore-newagent"
        mock_boto3_clients["ecr"].create_repository.assert_called_once_with(repositoryName="bedrock-agentcore-newagent")

        # Verify creation message printed
        captured = capsys.readouterr()
        assert "Repository doesn't exist, creating new ECR repository" in captured.out
