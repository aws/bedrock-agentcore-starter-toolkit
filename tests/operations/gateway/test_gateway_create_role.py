"""Tests for Bedrock AgentCore Gateway create_role functionality."""

import json
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.gateway.constants import (
    AGENTCORE_FULL_ACCESS,
    POLICIES,
)
from bedrock_agentcore_starter_toolkit.operations.gateway.create_role import (
    _attach_policy,
)


class TestAttachPolicy:
    """Test _attach_policy function."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_iam_client = Mock()
        self.role_name = "TestRole"

    def test_attach_policy_with_policy_arn(self):
        """Test attaching policy using policy ARN."""
        policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

        _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_arn=policy_arn)

        # Verify attach_role_policy was called correctly
        self.mock_iam_client.attach_role_policy.assert_called_once_with(RoleName=self.role_name, PolicyArn=policy_arn)

        # Verify create_policy was not called
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_with_policy_document_and_name(self):
        """Test attaching policy using policy document and name."""
        policy_name = "TestPolicy"
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}],
        }
        created_policy_arn = "arn:aws:iam::123456789012:policy/TestPolicy"

        # Mock create_policy response
        self.mock_iam_client.create_policy.return_value = {
            "Policy": {"Arn": created_policy_arn, "PolicyName": policy_name, "PolicyId": "ANPAI23HZ27SI6FQMGNQ2"}
        }

        _attach_policy(
            iam_client=self.mock_iam_client,
            role_name=self.role_name,
            policy_document=policy_document,
            policy_name=policy_name,
        )

        # Verify create_policy was called
        self.mock_iam_client.create_policy.assert_called_once_with(
            PolicyName=policy_name, PolicyDocument=policy_document
        )

        # Verify attach_role_policy was called with created policy ARN
        self.mock_iam_client.attach_role_policy.assert_called_once_with(
            RoleName=self.role_name, PolicyArn=created_policy_arn
        )

    def test_attach_policy_both_arn_and_document_raises_exception(self):
        """Test that providing both policy ARN and document raises exception."""
        policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
        policy_document = {"Version": "2012-10-17"}
        policy_name = "TestPolicy"

        with pytest.raises(Exception, match="Cannot specify both policy arn and policy document"):
            _attach_policy(
                iam_client=self.mock_iam_client,
                role_name=self.role_name,
                policy_arn=policy_arn,
                policy_document=policy_document,
                policy_name=policy_name,
            )

        # Verify no AWS calls were made
        self.mock_iam_client.attach_role_policy.assert_not_called()
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_document_without_name_raises_exception(self):
        """Test that providing policy document without name raises exception."""
        policy_document = {"Version": "2012-10-17"}

        with pytest.raises(Exception, match="Must specify both policy document and policy name or just a policy arn"):
            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_document=policy_document)

        # Verify no AWS calls were made
        self.mock_iam_client.attach_role_policy.assert_not_called()
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_name_without_document_raises_exception(self):
        """Test that providing policy name without document raises exception."""
        policy_name = "TestPolicy"

        with pytest.raises(Exception, match="Must specify both policy document and policy name or just a policy arn"):
            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_name=policy_name)

        # Verify no AWS calls were made
        self.mock_iam_client.attach_role_policy.assert_not_called()
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_no_parameters_raises_exception(self):
        """Test that providing no policy parameters raises exception."""
        with pytest.raises(Exception, match="Must specify both policy document and policy name or just a policy arn"):
            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name)

        # Verify no AWS calls were made
        self.mock_iam_client.attach_role_policy.assert_not_called()
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_arn_client_error(self):
        """Test handling ClientError when attaching policy by ARN."""
        policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

        # Mock ClientError
        client_error = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            operation_name="AttachRolePolicy",
        )
        self.mock_iam_client.attach_role_policy.side_effect = client_error

        with pytest.raises(RuntimeError, match="Failed to attach AgentCore policy") as exc_info:
            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_arn=policy_arn)

        # Verify the original exception is chained
        assert exc_info.value.__cause__ == client_error

    def test_attach_policy_document_create_policy_client_error(self):
        """Test handling ClientError when creating policy from document."""
        policy_name = "TestPolicy"
        policy_document = {"Version": "2012-10-17"}

        # Mock ClientError on create_policy
        client_error = ClientError(
            error_response={"Error": {"Code": "MalformedPolicyDocument", "Message": "Invalid policy"}},
            operation_name="CreatePolicy",
        )
        self.mock_iam_client.create_policy.side_effect = client_error

        with pytest.raises(RuntimeError, match="Failed to attach AgentCore policy") as exc_info:
            _attach_policy(
                iam_client=self.mock_iam_client,
                role_name=self.role_name,
                policy_document=policy_document,
                policy_name=policy_name,
            )

        # Verify the original exception is chained
        assert exc_info.value.__cause__ == client_error

    def test_attach_policy_document_attach_role_policy_client_error(self):
        """Test handling ClientError when attaching created policy to role."""
        policy_name = "TestPolicy"
        policy_document = {"Version": "2012-10-17"}
        created_policy_arn = "arn:aws:iam::123456789012:policy/TestPolicy"

        # Mock successful create_policy
        self.mock_iam_client.create_policy.return_value = {
            "Policy": {"Arn": created_policy_arn, "PolicyName": policy_name}
        }

        # Mock ClientError on attach_role_policy
        client_error = ClientError(
            error_response={"Error": {"Code": "NoSuchEntity", "Message": "Role not found"}},
            operation_name="AttachRolePolicy",
        )
        self.mock_iam_client.attach_role_policy.side_effect = client_error

        with pytest.raises(RuntimeError, match="Failed to attach AgentCore policy") as exc_info:
            _attach_policy(
                iam_client=self.mock_iam_client,
                role_name=self.role_name,
                policy_document=policy_document,
                policy_name=policy_name,
            )

        # Verify create_policy was called successfully
        self.mock_iam_client.create_policy.assert_called_once()

        # Verify the original exception is chained
        assert exc_info.value.__cause__ == client_error

    def test_attach_policy_with_json_string_policy_document(self):
        """Test attaching policy with JSON string policy document."""
        policy_name = "TestPolicy"
        policy_document_dict = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}],
        }
        policy_document_json = json.dumps(policy_document_dict)
        created_policy_arn = "arn:aws:iam::123456789012:policy/TestPolicy"

        # Mock create_policy response
        self.mock_iam_client.create_policy.return_value = {
            "Policy": {"Arn": created_policy_arn, "PolicyName": policy_name}
        }

        _attach_policy(
            iam_client=self.mock_iam_client,
            role_name=self.role_name,
            policy_document=policy_document_json,
            policy_name=policy_name,
        )

        # Verify create_policy was called with JSON string
        self.mock_iam_client.create_policy.assert_called_once_with(
            PolicyName=policy_name, PolicyDocument=policy_document_json
        )

        # Verify attach_role_policy was called
        self.mock_iam_client.attach_role_policy.assert_called_once_with(
            RoleName=self.role_name, PolicyArn=created_policy_arn
        )

    def test_attach_policy_with_agentcore_full_access_policy(self):
        """Test attaching the actual AGENTCORE_FULL_ACCESS policy from constants."""
        policy_name = "BedrockAgentCoreGatewayStarterFullAccess"
        created_policy_arn = "arn:aws:iam::123456789012:policy/BedrockAgentCoreGatewayStarterFullAccess"

        # Mock create_policy response
        self.mock_iam_client.create_policy.return_value = {
            "Policy": {"Arn": created_policy_arn, "PolicyName": policy_name}
        }

        _attach_policy(
            iam_client=self.mock_iam_client,
            role_name=self.role_name,
            policy_document=AGENTCORE_FULL_ACCESS,
            policy_name=policy_name,
        )

        # Verify create_policy was called with the actual policy document
        self.mock_iam_client.create_policy.assert_called_once_with(
            PolicyName=policy_name, PolicyDocument=AGENTCORE_FULL_ACCESS
        )

        # Verify attach_role_policy was called
        self.mock_iam_client.attach_role_policy.assert_called_once_with(
            RoleName=self.role_name, PolicyArn=created_policy_arn
        )

    def test_attach_policy_with_aws_managed_policies(self):
        """Test attaching AWS managed policies from POLICIES constant."""
        for policy_arn in POLICIES:
            # Reset mock for each iteration
            self.mock_iam_client.reset_mock()

            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_arn=policy_arn)

            # Verify attach_role_policy was called correctly
            self.mock_iam_client.attach_role_policy.assert_called_once_with(
                RoleName=self.role_name, PolicyArn=policy_arn
            )

            # Verify create_policy was not called for managed policies
            self.mock_iam_client.create_policy.assert_not_called()
