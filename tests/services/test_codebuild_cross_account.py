"""Simple tests for cross-account CodeBuild functionality."""

from unittest.mock import Mock, patch
import pytest

from bedrock_agentcore_starter_toolkit.services.codebuild import CodeBuildService


class TestCodeBuildCrossAccount:
    """Test cross-account CodeBuild functionality."""

    def test_init_same_account(self):
        """Test initialization for same-account scenario."""
        mock_session = Mock()
        mock_session.region_name = "us-west-2"
        
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session.client.return_value = mock_sts
        
        service = CodeBuildService(mock_session)
        
        assert service.deployment_account == "123456789012"
        assert service.build_account is None
        assert service.is_cross_account_codebuild is False

    def test_init_cross_account(self):
        """Test initialization for cross-account scenario."""
        mock_session = Mock()
        mock_session.region_name = "us-west-2"
        
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        
        mock_build_session = Mock()
        mock_build_session.region_name = "us-west-2"
        
        def client_factory(service_name):
            if service_name == "sts":
                return mock_sts
            return Mock()
        
        mock_session.client = client_factory
        
        with patch.object(CodeBuildService, '_create_build_session', return_value=mock_build_session):
            service = CodeBuildService(mock_session, "arn:aws:iam::987654321098:role/BuildRole")
        
        assert service.deployment_account == "123456789012"
        assert service.build_account == "987654321098"
        assert service.is_cross_account_codebuild is True

    def test_extract_build_account(self):
        """Test build account extraction from role ARN."""
        mock_session = Mock()
        mock_session.region_name = "us-west-2"
        
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session.client.return_value = mock_sts
        
        # Test valid ARN
        with patch.object(CodeBuildService, '_create_build_session'):
            service = CodeBuildService(mock_session, "arn:aws:iam::987654321098:role/BuildRole")
            assert service._extract_build_account() == "987654321098"
        
        # Test invalid ARN
        with patch.object(CodeBuildService, '_create_build_session'):
            service = CodeBuildService(mock_session, "invalid-arn")
            assert service._extract_build_account() is None
        
        # Test no ARN
        service = CodeBuildService(mock_session)
        assert service._extract_build_account() is None

    def test_upload_source_account_selection(self):
        """Test that upload_source uses correct account."""
        mock_session = Mock()
        mock_session.region_name = "us-west-2"
        
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        
        mock_s3 = Mock()
        mock_s3.head_bucket.return_value = {}
        
        def client_factory(service_name):
            if service_name == "sts":
                return mock_sts
            elif service_name == "s3":
                return mock_s3
            return Mock()
        
        mock_session.client = client_factory
        
        # Same account scenario
        service = CodeBuildService(mock_session)
        
        with patch('os.walk', return_value=[(".", [], ["test.py"])]), \
             patch('zipfile.ZipFile'), \
             patch('tempfile.NamedTemporaryFile'), \
             patch('os.unlink'):
            
            service.upload_source("test-agent")
            
            # Should use deployment account
            expected_bucket = "bedrock-agentcore-codebuild-sources-123456789012-us-west-2"
            mock_s3.head_bucket.assert_called_with(
                Bucket=expected_bucket,
                ExpectedBucketOwner="123456789012"
            )
