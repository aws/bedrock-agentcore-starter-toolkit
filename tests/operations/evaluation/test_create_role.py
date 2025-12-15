"""Tests for IAM role creation for evaluation."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.evaluation.create_role import (
    _attach_inline_policy,
    _generate_deterministic_suffix,
    get_or_create_evaluation_execution_role,
)

# =============================================================================
# _generate_deterministic_suffix Tests
# =============================================================================


class TestGenerateDeterministicSuffix:
    """Test _generate_deterministic_suffix helper function."""

    def test_generates_consistent_suffix(self):
        """Test that same input generates same output."""
        suffix1 = _generate_deterministic_suffix("my-config")
        suffix2 = _generate_deterministic_suffix("my-config")

        assert suffix1 == suffix2
        assert len(suffix1) == 10

    def test_different_inputs_generate_different_suffixes(self):
        """Test that different inputs generate different outputs."""
        suffix1 = _generate_deterministic_suffix("config-a")
        suffix2 = _generate_deterministic_suffix("config-b")

        assert suffix1 != suffix2

    def test_generates_lowercase(self):
        """Test that output is lowercase."""
        suffix = _generate_deterministic_suffix("MY-CONFIG")

        assert suffix.islower()

    def test_custom_length(self):
        """Test custom suffix length."""
        suffix = _generate_deterministic_suffix("my-config", length=20)

        assert len(suffix) == 20


# =============================================================================
# get_or_create_evaluation_execution_role Tests
# =============================================================================


class TestGetOrCreateEvaluationExecutionRole:
    """Test get_or_create_evaluation_execution_role function."""

    @patch("time.sleep")
    def test_creates_new_role_when_not_exists(self, mock_sleep):
        """Test creates new role when it doesn't exist."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        # First call to get_role fails with NoSuchEntity
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        # Create role succeeds
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123:role/test-role"}}

        result = get_or_create_evaluation_execution_role(
            session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
        )

        assert result == "arn:aws:iam::123:role/test-role"
        mock_iam.create_role.assert_called_once()
        mock_iam.put_role_policy.assert_called_once()
        mock_sleep.assert_called_once_with(10)  # IAM propagation wait

    def test_reuses_existing_role(self):
        """Test reuses existing role when it exists."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        # Role already exists
        mock_iam.get_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123:role/existing-role", "CreateDate": "2024-01-01"}
        }

        result = get_or_create_evaluation_execution_role(
            session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
        )

        assert result == "arn:aws:iam::123:role/existing-role"
        mock_iam.create_role.assert_not_called()
        mock_iam.put_role_policy.assert_not_called()

    @patch("time.sleep")
    def test_uses_custom_role_name(self, mock_sleep):
        """Test uses custom role name when provided."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123:role/custom-role"}}

        result = get_or_create_evaluation_execution_role(
            session=mock_session,
            region="us-east-1",
            account_id="123456789012",
            config_name="my-config",
            role_name="custom-role",
        )

        assert result == "arn:aws:iam::123:role/custom-role"
        # Verify custom role name was used
        call_kwargs = mock_iam.create_role.call_args[1]
        assert call_kwargs["RoleName"] == "custom-role"

    @patch("time.sleep")
    def test_generates_role_name_from_config(self, mock_sleep):
        """Test generates deterministic role name from config name."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123:role/generated-role"}}

        get_or_create_evaluation_execution_role(
            session=mock_session, region="us-west-2", account_id="123456789012", config_name="my-config"
        )

        # Verify role name includes region and deterministic suffix
        call_kwargs = mock_iam.create_role.call_args[1]
        role_name = call_kwargs["RoleName"]
        assert role_name.startswith("AgentCoreEvalsSDK-us-west-2-")
        assert len(role_name) > len("AgentCoreEvalsSDK-us-west-2-")

    @patch("time.sleep")
    def test_attaches_trust_policy_with_correct_principals(self, mock_sleep):
        """Test role creation includes correct trust policy."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123:role/test-role"}}

        get_or_create_evaluation_execution_role(
            session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
        )

        # Verify trust policy
        call_kwargs = mock_iam.create_role.call_args[1]
        import json

        trust_policy = json.loads(call_kwargs["AssumeRolePolicyDocument"])
        assert trust_policy["Statement"][0]["Principal"]["Service"] == "bedrock-agentcore.amazonaws.com"
        assert trust_policy["Statement"][0]["Action"] == "sts:AssumeRole"

    @patch("time.sleep")
    def test_attaches_execution_permissions(self, mock_sleep):
        """Test role creation attaches execution permissions policy."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123:role/test-role"}}

        get_or_create_evaluation_execution_role(
            session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
        )

        # Verify put_role_policy was called
        mock_iam.put_role_policy.assert_called_once()
        call_kwargs = mock_iam.put_role_policy.call_args[1]
        import json

        policy = json.loads(call_kwargs["PolicyDocument"])
        # Verify key permissions are included
        actions = []
        for statement in policy["Statement"]:
            actions.extend(statement["Action"])
        assert "logs:StartQuery" in actions
        assert "bedrock:InvokeModel" in actions

    @patch("time.sleep")
    def test_handles_entity_already_exists_race_condition(self, mock_sleep):
        """Test handles race condition when role is created between checks."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        # First get_role fails (doesn't exist)
        # Then create_role fails (race condition - someone else created it)
        # Then second get_role succeeds
        error_response_nosuch = {"Error": {"Code": "NoSuchEntity"}}
        error_response_exists = {"Error": {"Code": "EntityAlreadyExists"}}

        mock_iam.get_role.side_effect = [
            ClientError(error_response_nosuch, "GetRole"),
            {"Role": {"Arn": "arn:aws:iam::123:role/test-role"}},
        ]
        mock_iam.create_role.side_effect = ClientError(error_response_exists, "CreateRole")

        result = get_or_create_evaluation_execution_role(
            session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
        )

        assert result == "arn:aws:iam::123:role/test-role"
        assert mock_iam.get_role.call_count == 2

    def test_handles_entity_already_exists_but_get_fails(self):
        """Test handles when role creation says exists but get still fails."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response_nosuch = {"Error": {"Code": "NoSuchEntity"}}
        error_response_exists = {"Error": {"Code": "EntityAlreadyExists"}}

        # First get_role fails, create_role says exists, second get_role also fails
        mock_iam.get_role.side_effect = [
            ClientError(error_response_nosuch, "GetRole"),
            ClientError(error_response_nosuch, "GetRole"),
        ]
        mock_iam.create_role.side_effect = ClientError(error_response_exists, "CreateRole")

        with pytest.raises(RuntimeError, match="Failed to get existing role"):
            get_or_create_evaluation_execution_role(
                session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
            )

    def test_handles_access_denied_error(self):
        """Test handles AccessDenied error during creation."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response_nosuch = {"Error": {"Code": "NoSuchEntity"}}
        error_response_denied = {"Error": {"Code": "AccessDenied"}}

        mock_iam.get_role.side_effect = ClientError(error_response_nosuch, "GetRole")
        mock_iam.create_role.side_effect = ClientError(error_response_denied, "CreateRole")

        with pytest.raises(RuntimeError, match="Failed to create role"):
            get_or_create_evaluation_execution_role(
                session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
            )

    def test_handles_limit_exceeded_error(self):
        """Test handles LimitExceeded error during creation."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response_nosuch = {"Error": {"Code": "NoSuchEntity"}}
        error_response_limit = {"Error": {"Code": "LimitExceeded"}}

        mock_iam.get_role.side_effect = ClientError(error_response_nosuch, "GetRole")
        mock_iam.create_role.side_effect = ClientError(error_response_limit, "CreateRole")

        with pytest.raises(RuntimeError, match="Failed to create role"):
            get_or_create_evaluation_execution_role(
                session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
            )

    def test_handles_other_create_error(self):
        """Test handles other errors during creation."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response_nosuch = {"Error": {"Code": "NoSuchEntity"}}
        error_response_other = {"Error": {"Code": "ServiceUnavailable"}}

        mock_iam.get_role.side_effect = ClientError(error_response_nosuch, "GetRole")
        mock_iam.create_role.side_effect = ClientError(error_response_other, "CreateRole")

        with pytest.raises(RuntimeError, match="Failed to create role"):
            get_or_create_evaluation_execution_role(
                session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
            )

    def test_handles_other_get_role_error(self):
        """Test handles non-NoSuchEntity errors when checking role existence."""
        mock_session = Mock()
        mock_iam = Mock()
        mock_session.client.return_value = mock_iam

        error_response = {"Error": {"Code": "ServiceUnavailable"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        with pytest.raises(RuntimeError, match="Failed to check role existence"):
            get_or_create_evaluation_execution_role(
                session=mock_session, region="us-east-1", account_id="123456789012", config_name="my-config"
            )


# =============================================================================
# _attach_inline_policy Tests
# =============================================================================


class TestAttachInlinePolicy:
    """Test _attach_inline_policy helper function."""

    def test_attaches_policy_successfully(self):
        """Test successful policy attachment."""
        mock_iam = Mock()
        policy_doc = '{"Version": "2012-10-17", "Statement": []}'

        _attach_inline_policy(
            iam_client=mock_iam, role_name="test-role", policy_name="test-policy", policy_document=policy_doc
        )

        mock_iam.put_role_policy.assert_called_once_with(
            RoleName="test-role", PolicyName="test-policy", PolicyDocument=policy_doc
        )

    def test_handles_malformed_policy_error(self):
        """Test handles MalformedPolicyDocument error."""
        mock_iam = Mock()
        error_response = {"Error": {"Code": "MalformedPolicyDocument"}}
        mock_iam.put_role_policy.side_effect = ClientError(error_response, "PutRolePolicy")

        policy_doc = '{"Version": "2012-10-17"}'  # Missing Statement

        with pytest.raises(RuntimeError, match="Failed to attach policy"):
            _attach_inline_policy(
                iam_client=mock_iam, role_name="test-role", policy_name="test-policy", policy_document=policy_doc
            )

    def test_handles_limit_exceeded_error(self):
        """Test handles LimitExceeded error."""
        mock_iam = Mock()
        error_response = {"Error": {"Code": "LimitExceeded"}}
        mock_iam.put_role_policy.side_effect = ClientError(error_response, "PutRolePolicy")

        policy_doc = '{"Version": "2012-10-17", "Statement": []}'

        with pytest.raises(RuntimeError, match="Failed to attach policy"):
            _attach_inline_policy(
                iam_client=mock_iam, role_name="test-role", policy_name="test-policy", policy_document=policy_doc
            )

    def test_handles_other_error(self):
        """Test handles other errors."""
        mock_iam = Mock()
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_iam.put_role_policy.side_effect = ClientError(error_response, "PutRolePolicy")

        policy_doc = '{"Version": "2012-10-17", "Statement": []}'

        with pytest.raises(RuntimeError, match="Failed to attach policy"):
            _attach_inline_policy(
                iam_client=mock_iam, role_name="test-role", policy_name="test-policy", policy_document=policy_doc
            )
