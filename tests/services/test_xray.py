"""Tests for XRay Transaction Search service."""

import json
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.services.xray import (
    _configure_indexing_rule,
    _configure_trace_segment_destination,
    _create_cloudwatch_logs_resource_policy,
    _need_indexing_rule,
    _need_resource_policy,
    _need_trace_destination,
    enable_transaction_search_if_needed,
)


class TestEnableTransactionSearchIfNeeded:
    """Test cases for the main enable_transaction_search_if_needed function."""

    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_resource_policy")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_trace_destination")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_indexing_rule")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._create_cloudwatch_logs_resource_policy")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._configure_trace_segment_destination")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._configure_indexing_rule")
    def test_all_components_need_configuration(
        self,
        mock_configure_indexing,
        mock_configure_trace,
        mock_create_policy,
        mock_need_indexing,
        mock_need_trace,
        mock_need_policy,
        mock_session,
    ):
        """Test when all components need configuration."""
        # Setup mocks
        mock_logs_client = Mock()
        mock_xray_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: {"logs": mock_logs_client, "xray": mock_xray_client}[
            service
        ]
        mock_session.return_value = mock_session_instance

        # All components need configuration
        mock_need_policy.return_value = True
        mock_need_trace.return_value = True
        mock_need_indexing.return_value = True

        # Execute
        result = enable_transaction_search_if_needed("us-east-1", "123456789012")

        # Verify
        assert result is True
        mock_session.assert_called_once_with(region_name="us-east-1")
        mock_session_instance.client.assert_any_call("logs")
        mock_session_instance.client.assert_any_call("xray")

        # Verify all steps were executed
        mock_create_policy.assert_called_once_with(mock_logs_client, "123456789012", "us-east-1")
        mock_configure_trace.assert_called_once_with(mock_xray_client)
        mock_configure_indexing.assert_called_once_with(mock_xray_client)

    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_resource_policy")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_trace_destination")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_indexing_rule")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._create_cloudwatch_logs_resource_policy")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._configure_trace_segment_destination")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._configure_indexing_rule")
    def test_partial_configuration_needed(
        self,
        mock_configure_indexing,
        mock_configure_trace,
        mock_create_policy,
        mock_need_indexing,
        mock_need_trace,
        mock_need_policy,
        mock_session,
    ):
        """Test when only some components need configuration."""
        # Setup mocks
        mock_logs_client = Mock()
        mock_xray_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: {"logs": mock_logs_client, "xray": mock_xray_client}[
            service
        ]
        mock_session.return_value = mock_session_instance

        # Only resource policy needs configuration
        mock_need_policy.return_value = True
        mock_need_trace.return_value = False
        mock_need_indexing.return_value = False

        # Execute
        result = enable_transaction_search_if_needed("us-west-2", "987654321098")

        # Verify
        assert result is True

        # Verify only needed step was executed
        mock_create_policy.assert_called_once_with(mock_logs_client, "987654321098", "us-west-2")
        mock_configure_trace.assert_not_called()
        mock_configure_indexing.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_resource_policy")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_trace_destination")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_indexing_rule")
    def test_all_components_already_configured(
        self, mock_need_indexing, mock_need_trace, mock_need_policy, mock_session
    ):
        """Test when all components are already configured."""
        # Setup mocks
        mock_logs_client = Mock()
        mock_xray_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: {"logs": mock_logs_client, "xray": mock_xray_client}[
            service
        ]
        mock_session.return_value = mock_session_instance

        # All components already configured
        mock_need_policy.return_value = False
        mock_need_trace.return_value = False
        mock_need_indexing.return_value = False

        # Execute
        result = enable_transaction_search_if_needed("eu-west-1", "111222333444")

        # Verify
        assert result is True

    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    def test_session_creation_failure(self, mock_session):
        """Test handling of session creation failure."""
        mock_session.side_effect = Exception("AWS credentials not found")

        result = enable_transaction_search_if_needed("us-east-1", "123456789012")

        assert result is False

    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_resource_policy")
    def test_configuration_step_failure(self, mock_need_policy, mock_session):
        """Test handling of configuration step failure."""
        # Setup mocks
        mock_logs_client = Mock()
        mock_xray_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: {"logs": mock_logs_client, "xray": mock_xray_client}[
            service
        ]
        mock_session.return_value = mock_session_instance

        # Resource policy check fails
        mock_need_policy.side_effect = Exception("Permission denied")

        result = enable_transaction_search_if_needed("us-east-1", "123456789012")

        assert result is False


class TestNeedResourcePolicy:
    """Test cases for _need_resource_policy function."""

    def test_policy_exists(self):
        """Test when policy already exists."""
        mock_logs_client = Mock()
        mock_logs_client.describe_resource_policies.return_value = {
            "resourcePolicies": [{"policyName": "TransactionSearchXRayAccess", "policyDocument": "{}"}]
        }

        result = _need_resource_policy(mock_logs_client)

        assert result is False

    def test_policy_does_not_exist(self):
        """Test when policy does not exist."""
        mock_logs_client = Mock()
        mock_logs_client.describe_resource_policies.return_value = {
            "resourcePolicies": [{"policyName": "SomeOtherPolicy", "policyDocument": "{}"}]
        }

        result = _need_resource_policy(mock_logs_client)

        assert result is True

    def test_no_policies_exist(self):
        """Test when no policies exist."""
        mock_logs_client = Mock()
        mock_logs_client.describe_resource_policies.return_value = {"resourcePolicies": []}

        result = _need_resource_policy(mock_logs_client)

        assert result is True

    def test_api_exception(self):
        """Test when API call fails."""
        mock_logs_client = Mock()
        mock_logs_client.describe_resource_policies.side_effect = Exception("API error")

        result = _need_resource_policy(mock_logs_client)

        assert result is True  # Fail-safe: assume we need it

    def test_custom_policy_name(self):
        """Test with custom policy name."""
        mock_logs_client = Mock()
        mock_logs_client.describe_resource_policies.return_value = {
            "resourcePolicies": [{"policyName": "CustomPolicyName", "policyDocument": "{}"}]
        }

        result = _need_resource_policy(mock_logs_client, policy_name="CustomPolicyName")

        assert result is False


class TestNeedTraceDestination:
    """Test cases for _need_trace_destination function."""

    def test_destination_is_cloudwatch_logs(self):
        """Test when destination is already CloudWatch Logs."""
        mock_xray_client = Mock()
        mock_xray_client.get_trace_segment_destination.return_value = {"Destination": "CloudWatchLogs"}

        result = _need_trace_destination(mock_xray_client)

        assert result is False

    def test_destination_is_not_cloudwatch_logs(self):
        """Test when destination is not CloudWatch Logs."""
        mock_xray_client = Mock()
        mock_xray_client.get_trace_segment_destination.return_value = {"Destination": "XRay"}

        result = _need_trace_destination(mock_xray_client)

        assert result is True

    def test_no_destination_set(self):
        """Test when no destination is set."""
        mock_xray_client = Mock()
        mock_xray_client.get_trace_segment_destination.return_value = {}

        result = _need_trace_destination(mock_xray_client)

        assert result is True

    def test_api_exception(self):
        """Test when API call fails."""
        mock_xray_client = Mock()
        mock_xray_client.get_trace_segment_destination.side_effect = Exception("API error")

        result = _need_trace_destination(mock_xray_client)

        assert result is True  # Fail-safe: assume we need it


class TestNeedIndexingRule:
    """Test cases for _need_indexing_rule function."""

    def test_default_rule_exists(self):
        """Test when Default indexing rule exists."""
        mock_xray_client = Mock()
        mock_xray_client.get_indexing_rules.return_value = {
            "IndexingRules": [{"Name": "Default", "Rule": {"Probabilistic": {"DesiredSamplingPercentage": 1}}}]
        }

        result = _need_indexing_rule(mock_xray_client)

        assert result is False

    def test_no_default_rule(self):
        """Test when Default rule does not exist."""
        mock_xray_client = Mock()
        mock_xray_client.get_indexing_rules.return_value = {"IndexingRules": [{"Name": "SomeOtherRule", "Rule": {}}]}

        result = _need_indexing_rule(mock_xray_client)

        assert result is True

    def test_no_rules_exist(self):
        """Test when no indexing rules exist."""
        mock_xray_client = Mock()
        mock_xray_client.get_indexing_rules.return_value = {"IndexingRules": []}

        result = _need_indexing_rule(mock_xray_client)

        assert result is True

    def test_api_exception(self):
        """Test when API call fails."""
        mock_xray_client = Mock()
        mock_xray_client.get_indexing_rules.side_effect = Exception("API error")

        result = _need_indexing_rule(mock_xray_client)

        assert result is True  # Fail-safe: assume we need it


class TestCreateCloudWatchLogsResourcePolicy:
    """Test cases for _create_cloudwatch_logs_resource_policy function."""

    def test_successful_policy_creation(self):
        """Test successful policy creation."""
        mock_logs_client = Mock()

        _create_cloudwatch_logs_resource_policy(mock_logs_client, "123456789012", "us-east-1")

        # Verify the policy was created with correct parameters
        mock_logs_client.put_resource_policy.assert_called_once()
        call_args = mock_logs_client.put_resource_policy.call_args

        assert call_args[1]["policyName"] == "TransactionSearchXRayAccess"

        # Parse and verify policy document
        policy_doc = json.loads(call_args[1]["policyDocument"])
        assert policy_doc["Version"] == "2012-10-17"
        assert len(policy_doc["Statement"]) == 1

        statement = policy_doc["Statement"][0]
        assert statement["Sid"] == "TransactionSearchXRayAccess"
        assert statement["Effect"] == "Allow"
        assert statement["Principal"] == {"Service": "xray.amazonaws.com"}
        assert statement["Action"] == "logs:PutLogEvents"

        expected_resources = [
            "arn:aws:logs:us-east-1:123456789012:log-group:aws/spans:*",
            "arn:aws:logs:us-east-1:123456789012:log-group:/aws/application-signals/data:*",
        ]
        assert statement["Resource"] == expected_resources

        expected_condition = {
            "ArnLike": {"aws:SourceArn": "arn:aws:xray:us-east-1:123456789012:*"},
            "StringEquals": {"aws:SourceAccount": "123456789012"},
        }
        assert statement["Condition"] == expected_condition

    def test_policy_already_exists(self):
        """Test when policy already exists (InvalidParameterException)."""
        mock_logs_client = Mock()
        error_response = {"Error": {"Code": "InvalidParameterException", "Message": "Policy already exists"}}
        mock_logs_client.put_resource_policy.side_effect = ClientError(error_response, "PutResourcePolicy")

        # Should not raise exception
        _create_cloudwatch_logs_resource_policy(mock_logs_client, "123456789012", "us-east-1")

    def test_other_client_error(self):
        """Test handling of other ClientError exceptions."""
        mock_logs_client = Mock()
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_logs_client.put_resource_policy.side_effect = ClientError(error_response, "PutResourcePolicy")

        with pytest.raises(ClientError):
            _create_cloudwatch_logs_resource_policy(mock_logs_client, "123456789012", "us-east-1")


class TestConfigureTraceSegmentDestination:
    """Test cases for _configure_trace_segment_destination function."""

    def test_successful_configuration(self):
        """Test successful trace destination configuration."""
        mock_xray_client = Mock()

        _configure_trace_segment_destination(mock_xray_client)

        mock_xray_client.update_trace_segment_destination.assert_called_once_with(Destination="CloudWatchLogs")

    def test_destination_already_configured(self):
        """Test when destination is already configured (InvalidRequestException)."""
        mock_xray_client = Mock()
        error_response = {"Error": {"Code": "InvalidRequestException", "Message": "Already configured"}}
        mock_xray_client.update_trace_segment_destination.side_effect = ClientError(
            error_response, "UpdateTraceSegmentDestination"
        )

        # Should not raise exception
        _configure_trace_segment_destination(mock_xray_client)

    def test_other_client_error(self):
        """Test handling of other ClientError exceptions."""
        mock_xray_client = Mock()
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_xray_client.update_trace_segment_destination.side_effect = ClientError(
            error_response, "UpdateTraceSegmentDestination"
        )

        with pytest.raises(ClientError):
            _configure_trace_segment_destination(mock_xray_client)


class TestConfigureIndexingRule:
    """Test cases for _configure_indexing_rule function."""

    def test_successful_configuration(self):
        """Test successful indexing rule configuration."""
        mock_xray_client = Mock()

        _configure_indexing_rule(mock_xray_client)

        mock_xray_client.update_indexing_rule.assert_called_once_with(
            Name="Default", Rule={"Probabilistic": {"DesiredSamplingPercentage": 1}}
        )

    def test_rule_already_configured(self):
        """Test when rule is already configured (InvalidRequestException)."""
        mock_xray_client = Mock()
        error_response = {"Error": {"Code": "InvalidRequestException", "Message": "Already configured"}}
        mock_xray_client.update_indexing_rule.side_effect = ClientError(error_response, "UpdateIndexingRule")

        # Should not raise exception
        _configure_indexing_rule(mock_xray_client)

    def test_other_client_error(self):
        """Test handling of other ClientError exceptions."""
        mock_xray_client = Mock()
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_xray_client.update_indexing_rule.side_effect = ClientError(error_response, "UpdateIndexingRule")

        with pytest.raises(ClientError):
            _configure_indexing_rule(mock_xray_client)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    @pytest.mark.parametrize(
        "region,account_id",
        [
            ("", "123456789012"),
            ("us-east-1", ""),
            ("", ""),
            (None, "123456789012"),
            ("us-east-1", None),
        ],
    )
    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    def test_invalid_parameters(self, mock_session, region, account_id):
        """Test handling of invalid region/account parameters."""
        # Session creation should still work, but configuration might fail
        mock_logs_client = Mock()
        mock_xray_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: {"logs": mock_logs_client, "xray": mock_xray_client}[
            service
        ]
        mock_session.return_value = mock_session_instance

        # The function should handle these gracefully and return False
        result = enable_transaction_search_if_needed(region, account_id)

        # Should not crash, should return False due to likely configuration errors
        assert isinstance(result, bool)

    @patch("bedrock_agentcore_starter_toolkit.services.xray.boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._need_resource_policy")
    @patch("bedrock_agentcore_starter_toolkit.services.xray._create_cloudwatch_logs_resource_policy")
    def test_partial_failure_scenario(self, mock_create_policy, mock_need_policy, mock_session):
        """Test partial failure where some steps succeed and others fail."""
        # Setup mocks
        mock_logs_client = Mock()
        mock_xray_client = Mock()
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = lambda service: {"logs": mock_logs_client, "xray": mock_xray_client}[
            service
        ]
        mock_session.return_value = mock_session_instance

        mock_need_policy.return_value = True
        mock_create_policy.side_effect = Exception("Unexpected error")

        result = enable_transaction_search_if_needed("us-east-1", "123456789012")

        assert result is False
