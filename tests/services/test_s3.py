"""Tests for S3 service integration."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.services.s3 import (
    create_s3_bucket,
    get_or_create_s3_bucket,
    sanitize_s3_bucket_name,
)


class TestSanitizeS3BucketName:
    """Test S3 bucket name sanitization."""

    def test_basic_sanitization(self):
        """Test basic name sanitization."""
        result = sanitize_s3_bucket_name("MyAgent", "123456789012", "us-east-1")
        assert result == "bedrock-agentcore-myagent-123456789012-us-east-1"

    def test_special_characters(self):
        """Test sanitization of special characters."""
        result = sanitize_s3_bucket_name("My_Agent@Test!", "123456789012", "us-east-1")
        assert result == "bedrock-agentcore-my-agent-test-123456789012-us-east-1"

    def test_consecutive_separators(self):
        """Test handling of consecutive separators."""
        result = sanitize_s3_bucket_name("My--Agent..Test", "123456789012", "us-east-1")
        assert result == "bedrock-agentcore-my-agent-test-123456789012-us-east-1"

    def test_leading_non_alphanumeric(self):
        """Test handling of leading non-alphanumeric characters."""
        result = sanitize_s3_bucket_name("-agent", "123456789012", "us-east-1")
        assert result == "bedrock-agentcore-agent-123456789012-us-east-1"

    def test_trailing_non_alphanumeric(self):
        """Test handling of trailing non-alphanumeric characters."""
        result = sanitize_s3_bucket_name("agent-", "123456789012", "us-east-1")
        assert result == "bedrock-agentcore-agent-123456789012-us-east-1"

    def test_short_name_fallback(self):
        """Test fallback for very short names."""
        result = sanitize_s3_bucket_name("", "123456789012", "us-east-1")
        assert result == "bedrock-agentcore--123456789012-us-east-1"

    def test_long_name_truncation(self):
        """Test truncation of very long names."""
        long_name = "a" * 100
        result = sanitize_s3_bucket_name(long_name, "123456789012", "us-east-1")
        assert len(result) <= 63
        assert result.startswith("bedrock-agentcore-")
        assert result.endswith("-123456789012-us-east-1")


class TestGetOrCreateS3Bucket:
    """Test S3 bucket creation and retrieval."""

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_existing_bucket(self, mock_boto3_client):
        """Test using existing bucket."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = None

        result = get_or_create_s3_bucket("test-agent", "123456789012", "us-east-1")

        expected_bucket = "bedrock-agentcore-codebuild-sources-123456789012-us-east-1"
        assert result == expected_bucket
        mock_s3.head_bucket.assert_called_once_with(Bucket=expected_bucket, ExpectedBucketOwner="123456789012")

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_permission_error(self, mock_boto3_client):
        """Test handling of permission errors."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        error = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket")
        mock_s3.head_bucket.side_effect = error

        with pytest.raises(RuntimeError, match="Access Error"):
            get_or_create_s3_bucket("test-agent", "123456789012", "us-east-1")

    @patch("bedrock_agentcore_starter_toolkit.services.s3.create_s3_bucket")
    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_bucket_not_found_creates_new(self, mock_boto3_client, mock_create_bucket):
        """Test creating new bucket when not found."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        error = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")
        mock_s3.head_bucket.side_effect = error
        mock_create_bucket.return_value = "test-bucket"

        result = get_or_create_s3_bucket("test-agent", "123456789012", "us-east-1")

        assert result == "test-bucket"
        expected_bucket = "bedrock-agentcore-codebuild-sources-123456789012-us-east-1"
        mock_create_bucket.assert_called_once_with(expected_bucket, "us-east-1", "123456789012")

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_unexpected_error(self, mock_boto3_client):
        """Test handling of unexpected errors."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        error = ClientError({"Error": {"Code": "500", "Message": "Internal Error"}}, "HeadBucket")
        mock_s3.head_bucket.side_effect = error

        with pytest.raises(RuntimeError, match="Unexpected error checking S3 bucket"):
            get_or_create_s3_bucket("test-agent", "123456789012", "us-east-1")


class TestCreateS3Bucket:
    """Test S3 bucket creation."""

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_create_bucket_us_east_1(self, mock_boto3_client):
        """Test bucket creation in us-east-1."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        result = create_s3_bucket("test-bucket", "us-east-1", "123456789012")

        assert result == "test-bucket"
        mock_s3.create_bucket.assert_called_once_with(Bucket="test-bucket", ExpectedBucketOwner="123456789012")
        mock_s3.put_bucket_lifecycle_configuration.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_create_bucket_other_region(self, mock_boto3_client):
        """Test bucket creation in non-us-east-1 region."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        result = create_s3_bucket("test-bucket", "us-west-2", "123456789012")

        assert result == "test-bucket"
        mock_s3.create_bucket.assert_called_once_with(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            ExpectedBucketOwner="123456789012",
        )
        mock_s3.put_bucket_lifecycle_configuration.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_bucket_already_exists(self, mock_boto3_client):
        """Test handling when bucket already exists."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        error = ClientError({"Error": {"Code": "BucketAlreadyOwnedByYou", "Message": "Already exists"}}, "CreateBucket")
        mock_s3.create_bucket.side_effect = error

        result = create_s3_bucket("test-bucket", "us-east-1", "123456789012")

        assert result == "test-bucket"

    @patch("bedrock_agentcore_starter_toolkit.services.s3.boto3.client")
    def test_create_bucket_error(self, mock_boto3_client):
        """Test handling of bucket creation errors."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        error = ClientError({"Error": {"Code": "InvalidBucketName", "Message": "Invalid name"}}, "CreateBucket")
        mock_s3.create_bucket.side_effect = error

        with pytest.raises(RuntimeError, match="Failed to create S3 bucket"):
            create_s3_bucket("test-bucket", "us-east-1", "123456789012")
