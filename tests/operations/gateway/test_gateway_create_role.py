"""Tests for Bedrock AgentCore Gateway create_role functionality."""

import json
import logging
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.gateway.constants import (
    AGENTCORE_FULL_ACCESS,
    BEDROCK_AGENTCORE_TRUST_POLICY,
    POLICIES,
    POLICIES_TO_CREATE,
)
from bedrock_agentcore_starter_toolkit.operations.gateway.create_role import (
    _attach_policy,
    create_gateway_execution_role,
)


class TestCreateGatewayExecutionRole:
    """Test create_gateway_execution_role function."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = Mock()
        self.mock_iam_client = Mock()
        self.mock_session.client.return_value = self.mock_iam_client
        self.logger = logging.getLogger(__name__)
        self.role_name = "TestGatewayRole"
        self.role_arn = f"arn:aws:iam::123456789012:role/{self.role_name}"

    def test_create_gateway_execution_role_success(self):
        """Test successful role creation."""
        # Mock successful role creation
        self.mock_iam_client.create_role.return_value = {
            "Role": {
                "Arn": self.role_arn,
                "RoleName": self.role_name,
                "Path": "/",
                "RoleId": "AROAI23HZ27SI6FQMGNQ2",
            }
        }

        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.create_role._attach_policy") as mock_attach:
            result = create_gateway_execution_role(self.mock_session, self.logger, self.role_name)

        # Verify role creation
        self.mock_iam_client.create_role.assert_called_once_with(
            RoleName=self.role_name,
            AssumeRolePolicyDocument=json.dumps(BEDROCK_AGENTCORE_TRUST_POLICY),
            Description="Execution role for AgentCore Gateway",
        )

        # Verify policies were attached
        expected_calls = len(POLICIES_TO_CREATE) + len(POLICIES)
        assert mock_attach.call_count == expected_calls

        # Verify return value
        assert result == self.role_arn

    def test_create_gateway_execution_role_default_name(self):
        """Test role creation with default role name."""
        default_role_name = "AgentCoreGatewayExecutionRole"
        default_role_arn = f"arn:aws:iam::123456789012:role/{default_role_name}"

        self.mock_iam_client.create_role.return_value = {
            "Role": {"Arn": default_role_arn, "RoleName": default_role_name}
        }

        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.create_role._attach_policy"):
            result = create_gateway_execution_role(self.mock_session, self.logger)

        # Verify default role name was used
        self.mock_iam_client.create_role.assert_called_once_with(
            RoleName=default_role_name,
            AssumeRolePolicyDocument=json.dumps(BEDROCK_AGENTCORE_TRUST_POLICY),
            Description="Execution role for AgentCore Gateway",
        )

        assert result == default_role_arn

    def test_create_gateway_execution_role_already_exists(self):
        """Test handling when role already exists."""
        # Mock EntityAlreadyExistsException using proper ClientError
        already_exists_error = ClientError(
            error_response={"Error": {"Code": "EntityAlreadyExists", "Message": "Role already exists"}},
            operation_name="CreateRole",
        )
        self.mock_iam_client.create_role.side_effect = already_exists_error

        # Mock successful get_role
        self.mock_iam_client.get_role.return_value = {"Role": {"Arn": self.role_arn, "RoleName": self.role_name}}

        result = create_gateway_execution_role(self.mock_session, self.logger, self.role_name)

        # Verify create_role was attempted
        self.mock_iam_client.create_role.assert_called_once()

        # Verify get_role was called
        self.mock_iam_client.get_role.assert_called_once_with(RoleName=self.role_name)

        # Verify return value
        assert result == self.role_arn

    def test_create_gateway_execution_role_exists_but_get_fails(self):
        """Test handling when role exists but get_role fails."""
        # Mock EntityAlreadyExistsException using proper ClientError
        already_exists_error = ClientError(
            error_response={"Error": {"Code": "EntityAlreadyExists", "Message": "Role already exists"}},
            operation_name="CreateRole",
        )
        self.mock_iam_client.create_role.side_effect = already_exists_error

        # Mock ClientError on get_role
        get_role_error = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            operation_name="GetRole",
        )
        self.mock_iam_client.get_role.side_effect = get_role_error

        with pytest.raises(ClientError) as exc_info:
            create_gateway_execution_role(self.mock_session, self.logger, self.role_name)

        # Verify the original exception is raised
        assert exc_info.value == get_role_error

    def test_create_gateway_execution_role_create_fails(self):
        """Test handling when role creation fails."""
        # Mock ClientError on create_role
        create_role_error = ClientError(
            error_response={"Error": {"Code": "MalformedPolicyDocument", "Message": "Invalid trust policy"}},
            operation_name="CreateRole",
        )
        self.mock_iam_client.create_role.side_effect = create_role_error

        with pytest.raises(ClientError) as exc_info:
            create_gateway_execution_role(self.mock_session, self.logger, self.role_name)

        # Verify the original exception is raised
        assert exc_info.value == create_role_error

    def test_create_gateway_execution_role_policy_attachment_patterns(self):
        """Test that correct policy attachment patterns are used."""
        self.mock_iam_client.create_role.return_value = {"Role": {"Arn": self.role_arn, "RoleName": self.role_name}}

        with patch("bedrock_agentcore_starter_toolkit.operations.gateway.create_role._attach_policy") as mock_attach:
            create_gateway_execution_role(self.mock_session, self.logger, self.role_name)

            # Verify policy creation calls (POLICIES_TO_CREATE)
            policy_creation_calls = [
                call for call in mock_attach.call_args_list if call.kwargs.get("policy_document") is not None
            ]
            assert len(policy_creation_calls) == len(POLICIES_TO_CREATE)

            # Verify policy ARN attachment calls (POLICIES)
            policy_arn_calls = [
                call for call in mock_attach.call_args_list if call.kwargs.get("policy_arn") is not None
            ]
            assert len(policy_arn_calls) == len(POLICIES)

    def test_create_gateway_execution_role_attach_policy_integration(self):
        """Test actual policy attachment without mocking _attach_policy."""
        self.mock_iam_client.create_role.return_value = {"Role": {"Arn": self.role_arn, "RoleName": self.role_name}}

        # Mock successful policy operations
        self.mock_iam_client.create_policy.return_value = {
            "Policy": {"Arn": "arn:aws:iam::123456789012:policy/TestPolicy"}
        }
        self.mock_iam_client.attach_role_policy.return_value = {}

        result = create_gateway_execution_role(self.mock_session, self.logger, self.role_name)

        # Verify role was created successfully
        assert result == self.role_arn

        # Verify policies were created and attached
        assert self.mock_iam_client.create_policy.call_count == len(POLICIES_TO_CREATE)
        assert self.mock_iam_client.attach_role_policy.call_count == len(POLICIES_TO_CREATE) + len(POLICIES)


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

        with pytest.raises(Exception, match="Must specify both policy document and policy name, or just a policy arn"):
            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_document=policy_document)

        # Verify no AWS calls were made
        self.mock_iam_client.attach_role_policy.assert_not_called()
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_name_without_document_raises_exception(self):
        """Test that providing policy name without document raises exception."""
        policy_name = "TestPolicy"

        with pytest.raises(Exception, match="Must specify both policy document and policy name, or just a policy arn"):
            _attach_policy(iam_client=self.mock_iam_client, role_name=self.role_name, policy_name=policy_name)

        # Verify no AWS calls were made
        self.mock_iam_client.attach_role_policy.assert_not_called()
        self.mock_iam_client.create_policy.assert_not_called()

    def test_attach_policy_no_parameters_raises_exception(self):
        """Test that providing no policy parameters raises exception."""
        with pytest.raises(Exception, match="Must specify both policy document and policy name, or just a policy arn"):
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

    def test_attach_policy_with_existing_full_access_policy(self):
        """Test attaching a preexisting full access policy."""
        policy_name = "BedrockAgentCoreGatewayStarterFullAccess"
        existing_policy_arn = "arn:aws:iam::123456789012:policy/BedrockAgentCoreGatewayStarterFullAccess"

        # Mock ClientError on create_policy
        client_error = ClientError(
            error_response={"Error": {
                "Code": "EntityAlreadyExists", 
                "Message": f"Policy {policy_name} already exists"
            }},
            operation_name="CreatePolicy",
        )
        self.mock_iam_client.create_policy.side_effect = client_error

        # Mock paginator
        self.mock_iam_client.get_paginator.return_value.paginate.return_value = [
            {"Policies": [{"Arn": existing_policy_arn, "PolicyName": policy_name}]}
        ]

        _attach_policy(
            iam_client=self.mock_iam_client,
            role_name=self.role_name,
            policy_document=AGENTCORE_FULL_ACCESS,
            policy_name=policy_name,
        )

        # Verify paginator was called
        self.mock_iam_client.get_paginator.assert_called_once_with("list_policies")
        self.mock_iam_client.get_paginator().paginate.assert_called_once_with(Scope="Local")
    
        # Verify attach_role_policy was called
        self.mock_iam_client.attach_role_policy.assert_called_once_with(
            RoleName=self.role_name, PolicyArn=existing_policy_arn
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
