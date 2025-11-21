"""Tests for aws utilties."""

from bedrock_agentcore_starter_toolkit.utils.aws import get_account_id, get_region


class TestAws:
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
