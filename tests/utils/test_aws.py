"""Tests for aws utilties."""

from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

# Assuming ensure_valid_aws_creds is also in this module based on context
from bedrock_agentcore_starter_toolkit.utils.aws import ensure_valid_aws_creds, get_account_id, get_region


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

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    def test_ensure_valid_aws_creds_success(self, mock_get_account_id):
        """Test validation when credentials are valid."""
        mock_get_account_id.return_value = "123456789012"

        is_valid, message = ensure_valid_aws_creds()

        assert is_valid is True
        assert message is None

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    def test_ensure_valid_aws_creds_no_creds(self, mock_get_account_id):
        """Test validation when NoCredentialsError is raised."""
        mock_get_account_id.side_effect = NoCredentialsError()

        is_valid, message = ensure_valid_aws_creds()

        assert is_valid is False
        assert message == "No AWS credentials found."

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    def test_ensure_valid_aws_creds_partial_creds(self, mock_get_account_id):
        """Test validation when PartialCredentialsError is raised."""
        mock_get_account_id.side_effect = PartialCredentialsError(provider="aws", cred_var="foo")

        is_valid, message = ensure_valid_aws_creds()

        assert is_valid is False
        assert message == "AWS credentials are incomplete or misconfigured."

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    @pytest.mark.parametrize("error_code", ["ExpiredToken", "ExpiredTokenException", "RequestExpired"])
    def test_ensure_valid_aws_creds_expired(self, mock_get_account_id, error_code):
        """Test validation when token has expired."""
        error_response = {"Error": {"Code": error_code, "Message": "Token expired"}}
        mock_get_account_id.side_effect = ClientError(error_response, "GetCallerIdentity")

        is_valid, message = ensure_valid_aws_creds()

        assert is_valid is False
        assert message == "AWS credentials have expired. Please refresh or re-authenticate."

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    @pytest.mark.parametrize("error_code", ["InvalidClientTokenId", "UnrecognizedClientException"])
    def test_ensure_valid_aws_creds_invalid(self, mock_get_account_id, error_code):
        """Test validation when token is invalid."""
        error_response = {"Error": {"Code": error_code, "Message": "Invalid token"}}
        mock_get_account_id.side_effect = ClientError(error_response, "GetCallerIdentity")

        is_valid, message = ensure_valid_aws_creds()

        assert is_valid is False
        assert message == "AWS credentials are invalid."

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    def test_ensure_valid_aws_creds_generic_client_error(self, mock_get_account_id):
        """Test validation when a generic ClientError occurs."""
        error_code = "AccessDenied"
        msg = "User not authorized"
        error_response = {"Error": {"Code": error_code, "Message": msg}}
        mock_get_account_id.side_effect = ClientError(error_response, "GetCallerIdentity")

        is_valid, message = ensure_valid_aws_creds()

        assert is_valid is False
        assert message == f"AWS credential validation failed: {msg}"

    @patch("bedrock_agentcore_starter_toolkit.utils.aws.get_account_id")
    def test_ensure_valid_aws_creds_unknown_exception(self, mock_get_account_id):
        """Test that unknown exceptions do not block the user (return True)."""
        mock_get_account_id.side_effect = Exception("Unexpected network blip")

        is_valid, message = ensure_valid_aws_creds()

        # Function spec says: "Don't block the user — a non-credential error occured"
        assert is_valid is True
        assert message is None
