"""Tests for create_role module."""

import json
import logging
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.runtime.create_role import (
    _attach_inline_policy,
    _create_iam_role_with_policies,
    _generate_deterministic_suffix,
    get_or_create_codebuild_execution_role,
    get_or_create_runtime_execution_role,
)


class TestCreateRole:
    """Test create_role functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock boto3 session."""
        session = MagicMock(spec=boto3.Session)
        mock_iam = MagicMock()
        session.client.return_value = mock_iam
        return session, mock_iam

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock(spec=logging.Logger)

    def test_get_or_create_runtime_execution_role_success(self, mock_session, mock_logger):
        """Test successful role creation."""
        session, mock_iam = mock_session

        # First call (check if exists) - role doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        # Second call (create role) - successful creation
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestRole"}}

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_trust_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_execution_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.validate_rendered_policy",
                return_value={"Version": "2012-10-17", "Statement": []},
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role._attach_inline_policy"
            ) as mock_attach,
        ):
            result = get_or_create_runtime_execution_role(
                session=session,
                logger=mock_logger,
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
            )

            assert result == "arn:aws:iam::123456789012:role/TestRole"
            mock_iam.create_role.assert_called_once()
            mock_attach.assert_called_once()
            mock_logger.info.assert_called()

    def test_get_or_create_runtime_execution_role_with_custom_name(self, mock_session, mock_logger):
        """Test role creation with custom name."""
        session, mock_iam = mock_session

        # First call (check if exists) - role doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        # Second call (create role) - successful creation
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/CustomRoleName"}}

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_trust_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_execution_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.validate_rendered_policy",
                return_value={"Version": "2012-10-17", "Statement": []},
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.create_role._attach_inline_policy"),
        ):
            result = get_or_create_runtime_execution_role(
                session=session,
                logger=mock_logger,
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                role_name="CustomRoleName",
            )

            assert result == "arn:aws:iam::123456789012:role/CustomRoleName"
            mock_iam.create_role.assert_called_once_with(
                RoleName="CustomRoleName",
                AssumeRolePolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": []}),
                Description="Execution role for BedrockAgentCore Runtime - test-agent",
            )

    def test_get_or_create_runtime_execution_role_already_exists(self, mock_session, mock_logger):
        """Test getting existing role when role already exists."""
        session, mock_iam = mock_session

        # Mock the get_role response (role exists)
        mock_iam.get_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/ExistingRole"}}

        result = get_or_create_runtime_execution_role(
            session=session,
            logger=mock_logger,
            region="us-east-1",
            account_id="123456789012",
            agent_name="test-agent",
            role_name="ExistingRole",
        )

        assert result == "arn:aws:iam::123456789012:role/ExistingRole"
        mock_iam.get_role.assert_called_once_with(RoleName="ExistingRole")
        # create_role should not be called since role already exists
        mock_iam.create_role.assert_not_called()
        mock_logger.info.assert_called()

    def test_get_or_create_runtime_execution_role_check_error(self, mock_session, mock_logger):
        """Test error when checking role existence (other than NoSuchEntity)."""
        session, mock_iam = mock_session

        # Mock the get_role to raise a different error (not NoSuchEntity)
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        with pytest.raises(RuntimeError, match="Failed to check role existence"):
            get_or_create_runtime_execution_role(
                session=session,
                logger=mock_logger,
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                role_name="TestRole",
            )

        mock_iam.get_role.assert_called_once_with(RoleName="TestRole")
        mock_iam.create_role.assert_not_called()
        mock_logger.error.assert_called()

    def test_get_or_create_runtime_execution_role_create_error(self, mock_session, mock_logger):
        """Test error during role creation."""
        session, mock_iam = mock_session

        # First call (check if exists) - role doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        # Second call (create role) - raise AccessDenied error
        error_response_create = {"Error": {"Code": "AccessDenied"}}
        mock_iam.create_role.side_effect = ClientError(error_response_create, "CreateRole")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_trust_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_execution_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.validate_rendered_policy",
                return_value={"Version": "2012-10-17", "Statement": []},
            ),
        ):
            with pytest.raises(RuntimeError, match="Failed to create role"):
                get_or_create_runtime_execution_role(
                    session=session,
                    logger=mock_logger,
                    region="us-east-1",
                    account_id="123456789012",
                    agent_name="test-agent",
                )

            mock_iam.create_role.assert_called_once()
            mock_logger.error.assert_called()

    def test_attach_inline_policy_success(self, mock_session, mock_logger):
        """Test successful policy attachment."""
        _, mock_iam = mock_session

        _attach_inline_policy(
            iam_client=mock_iam,
            role_name="TestRole",
            policy_name="TestPolicy",
            policy_document='{"Version": "2012-10-17", "Statement": []}',
            logger=mock_logger,
        )

        mock_iam.put_role_policy.assert_called_once_with(
            RoleName="TestRole",
            PolicyName="TestPolicy",
            PolicyDocument='{"Version": "2012-10-17", "Statement": []}',
        )

    def test_attach_inline_policy_error(self, mock_session, mock_logger):
        """Test error during policy attachment."""
        _, mock_iam = mock_session

        # Mock the put_role_policy to raise an error
        error_response = {"Error": {"Code": "MalformedPolicyDocument"}}
        mock_iam.put_role_policy.side_effect = ClientError(error_response, "PutRolePolicy")

        with pytest.raises(RuntimeError, match="Failed to attach policy"):
            _attach_inline_policy(
                iam_client=mock_iam,
                role_name="TestRole",
                policy_name="TestPolicy",
                policy_document='{"Version": "2012-10-17", "Statement": []}',
                logger=mock_logger,
            )

        mock_iam.put_role_policy.assert_called_once()
        mock_logger.error.assert_called()

    def test_generate_deterministic_suffix(self):
        """Test deterministic suffix generation."""
        # Test deterministic behavior - same input should produce same output
        suffix1 = _generate_deterministic_suffix("test-agent")
        suffix2 = _generate_deterministic_suffix("test-agent")
        assert suffix1 == suffix2
        assert len(suffix1) == 10
        assert suffix1.islower()
        assert suffix1.isalnum()

        # Test different inputs produce different outputs
        suffix_a = _generate_deterministic_suffix("agent-a")
        suffix_b = _generate_deterministic_suffix("agent-b")
        assert suffix_a != suffix_b

        # Test custom length
        suffix_short = _generate_deterministic_suffix("test", length=5)
        assert len(suffix_short) == 5

        # Test empty string
        suffix_empty = _generate_deterministic_suffix("")
        assert len(suffix_empty) == 10

    def test_create_iam_role_with_policies_success(self, mock_session, mock_logger):
        """Test successful role creation with policies."""
        session, mock_iam = mock_session

        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestRole"}}

        trust_policy = {"Version": "2012-10-17", "Statement": []}
        inline_policies = {
            "Policy1": {"Version": "2012-10-17", "Statement": []},
            "Policy2": '{"Version": "2012-10-17", "Statement": []}',
        }

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.create_role._attach_inline_policy"
        ) as mock_attach:
            result = _create_iam_role_with_policies(
                session=session,
                logger=mock_logger,
                role_name="TestRole",
                trust_policy=trust_policy,
                inline_policies=inline_policies,
                description="Test role description",
            )

            assert result == "arn:aws:iam::123456789012:role/TestRole"
            mock_iam.create_role.assert_called_once_with(
                RoleName="TestRole",
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Test role description",
            )
            assert mock_attach.call_count == 2

    def test_create_iam_role_with_policies_already_exists(self, mock_session, mock_logger):
        """Test role creation when role already exists."""
        session, mock_iam = mock_session

        # Mock role creation failure (already exists)
        error_response = {"Error": {"Code": "EntityAlreadyExists"}}
        mock_iam.create_role.side_effect = ClientError(error_response, "CreateRole")

        # Mock get_role success
        mock_iam.get_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/ExistingRole"}}

        trust_policy = {"Version": "2012-10-17", "Statement": []}
        inline_policies = {"Policy1": {"Version": "2012-10-17", "Statement": []}}

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.create_role._attach_inline_policy"
        ) as mock_attach:
            result = _create_iam_role_with_policies(
                session=session,
                logger=mock_logger,
                role_name="ExistingRole",
                trust_policy=trust_policy,
                inline_policies=inline_policies,
                description="Test role description",
            )

            assert result == "arn:aws:iam::123456789012:role/ExistingRole"
            mock_iam.create_role.assert_called_once()
            mock_iam.get_role.assert_called_once_with(RoleName="ExistingRole")
            mock_attach.assert_called_once()  # Should update existing policies

    def test_create_iam_role_with_policies_get_existing_error(self, mock_session, mock_logger):
        """Test error when getting existing role after EntityAlreadyExists."""
        session, mock_iam = mock_session

        # Mock role creation failure (already exists)
        error_response = {"Error": {"Code": "EntityAlreadyExists"}}
        mock_iam.create_role.side_effect = ClientError(error_response, "CreateRole")

        # Mock get_role failure
        error_response_get = {"Error": {"Code": "AccessDenied"}}
        mock_iam.get_role.side_effect = ClientError(error_response_get, "GetRole")

        trust_policy = {"Version": "2012-10-17", "Statement": []}
        inline_policies = {"Policy1": {"Version": "2012-10-17", "Statement": []}}

        with pytest.raises(RuntimeError, match="Failed to get existing role"):
            _create_iam_role_with_policies(
                session=session,
                logger=mock_logger,
                role_name="TestRole",
                trust_policy=trust_policy,
                inline_policies=inline_policies,
                description="Test role description",
            )

    def test_create_iam_role_with_policies_access_denied(self, mock_session, mock_logger):
        """Test AccessDenied error during role creation."""
        session, mock_iam = mock_session

        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_iam.create_role.side_effect = ClientError(error_response, "CreateRole")

        trust_policy = {"Version": "2012-10-17", "Statement": []}
        inline_policies = {"Policy1": {"Version": "2012-10-17", "Statement": []}}

        with pytest.raises(RuntimeError, match="Failed to create role"):
            _create_iam_role_with_policies(
                session=session,
                logger=mock_logger,
                role_name="TestRole",
                trust_policy=trust_policy,
                inline_policies=inline_policies,
                description="Test role description",
            )

        mock_logger.error.assert_called()

    def test_create_iam_role_with_policies_limit_exceeded(self, mock_session, mock_logger):
        """Test LimitExceeded error during role creation."""
        session, mock_iam = mock_session

        error_response = {"Error": {"Code": "LimitExceeded"}}
        mock_iam.create_role.side_effect = ClientError(error_response, "CreateRole")

        trust_policy = {"Version": "2012-10-17", "Statement": []}
        inline_policies = {"Policy1": {"Version": "2012-10-17", "Statement": []}}

        with pytest.raises(RuntimeError, match="Failed to create role"):
            _create_iam_role_with_policies(
                session=session,
                logger=mock_logger,
                role_name="TestRole",
                trust_policy=trust_policy,
                inline_policies=inline_policies,
                description="Test role description",
            )

        mock_logger.error.assert_called()

    def test_get_or_create_codebuild_execution_role_success(self, mock_session, mock_logger):
        """Test successful CodeBuild role creation."""
        session, mock_iam = mock_session

        # First call (check if exists) - role doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.create_role._create_iam_role_with_policies"
        ) as mock_create:
            mock_create.return_value = "arn:aws:iam::123456789012:role/CodeBuildRole"

            with patch("time.sleep"):  # Mock sleep for IAM propagation
                result = get_or_create_codebuild_execution_role(
                    session=session,
                    logger=mock_logger,
                    region="us-west-2",
                    account_id="123456789012",
                    agent_name="test-agent",
                    ecr_repository_arn="arn:aws:ecr:us-west-2:123456789012:repository/test-repo",
                    source_bucket_name="test-bucket",
                )

            assert result == "arn:aws:iam::123456789012:role/CodeBuildRole"
            mock_iam.get_role.assert_called_once()
            mock_create.assert_called_once()

            # Verify correct trust policy and permissions were passed
            call_args = mock_create.call_args
            trust_policy = call_args[1]["trust_policy"]
            assert trust_policy["Statement"][0]["Principal"]["Service"] == "codebuild.amazonaws.com"

            inline_policies = call_args[1]["inline_policies"]
            permissions_policy = inline_policies["CodeBuildExecutionPolicy"]
            assert "ecr:GetAuthorizationToken" in str(permissions_policy)
            assert "arn:aws:ecr:us-west-2:123456789012:repository/test-repo" in str(permissions_policy)

    def test_get_or_create_codebuild_execution_role_already_exists(self, mock_session, mock_logger):
        """Test getting existing CodeBuild role."""
        session, mock_iam = mock_session

        mock_iam.get_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/ExistingCodeBuildRole"}}

        result = get_or_create_codebuild_execution_role(
            session=session,
            logger=mock_logger,
            region="us-west-2",
            account_id="123456789012",
            agent_name="test-agent",
            ecr_repository_arn="arn:aws:ecr:us-west-2:123456789012:repository/test-repo",
            source_bucket_name="test-bucket",
        )

        assert result == "arn:aws:iam::123456789012:role/ExistingCodeBuildRole"
        mock_iam.get_role.assert_called_once()

    def test_get_or_create_codebuild_execution_role_check_error(self, mock_session, mock_logger):
        """Test error when checking CodeBuild role existence."""
        session, mock_iam = mock_session

        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        with pytest.raises(RuntimeError, match="Failed to check CodeBuild role existence"):
            get_or_create_codebuild_execution_role(
                session=session,
                logger=mock_logger,
                region="us-west-2",
                account_id="123456789012",
                agent_name="test-agent",
                ecr_repository_arn="arn:aws:ecr:us-west-2:123456789012:repository/test-repo",
                source_bucket_name="test-bucket",
            )

    def test_attach_inline_policy_limit_exceeded_error(self, mock_session, mock_logger):
        """Test LimitExceeded error during policy attachment."""
        _, mock_iam = mock_session

        error_response = {"Error": {"Code": "LimitExceeded"}}
        mock_iam.put_role_policy.side_effect = ClientError(error_response, "PutRolePolicy")

        with pytest.raises(RuntimeError, match="Failed to attach policy"):
            _attach_inline_policy(
                iam_client=mock_iam,
                role_name="TestRole",
                policy_name="TestPolicy",
                policy_document='{"Version": "2012-10-17", "Statement": []}',
                logger=mock_logger,
            )

        mock_logger.error.assert_called()

    def test_get_or_create_runtime_execution_role_entity_already_exists_during_creation(
        self, mock_session, mock_logger
    ):
        """Test EntityAlreadyExists during runtime role creation."""
        session, mock_iam = mock_session

        # First call (check if exists) - role doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = [
            ClientError(error_response, "GetRole"),  # First call fails
            {"Role": {"Arn": "arn:aws:iam::123456789012:role/ExistingRole"}},  # Second call succeeds
        ]

        # Role creation fails with EntityAlreadyExists
        error_response_create = {"Error": {"Code": "EntityAlreadyExists"}}
        mock_iam.create_role.side_effect = ClientError(error_response_create, "CreateRole")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_trust_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_execution_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.validate_rendered_policy",
                return_value={"Version": "2012-10-17", "Statement": []},
            ),
        ):
            result = get_or_create_runtime_execution_role(
                session=session,
                logger=mock_logger,
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
            )

            assert result == "arn:aws:iam::123456789012:role/ExistingRole"
            mock_iam.create_role.assert_called_once()
            assert mock_iam.get_role.call_count == 2

    def test_get_or_create_runtime_execution_role_limit_exceeded_error(self, mock_session, mock_logger):
        """Test LimitExceeded error during runtime role creation."""
        session, mock_iam = mock_session

        # First call (check if exists) - role doesn't exist
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")

        # Role creation fails with LimitExceeded
        error_response_create = {"Error": {"Code": "LimitExceeded"}}
        mock_iam.create_role.side_effect = ClientError(error_response_create, "CreateRole")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_trust_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_execution_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.validate_rendered_policy",
                return_value={"Version": "2012-10-17", "Statement": []},
            ),
        ):
            with pytest.raises(RuntimeError, match="Failed to create role"):
                get_or_create_runtime_execution_role(
                    session=session,
                    logger=mock_logger,
                    region="us-east-1",
                    account_id="123456789012",
                    agent_name="test-agent",
                )

            mock_logger.error.assert_called()

    def test_execution_policy_not_double_encoded(self, mock_session, mock_logger):
        """Test that execution policy passed to put_role_policy is valid JSON, not double-encoded."""
        session, mock_iam = mock_session

        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.get_role.side_effect = ClientError(error_response, "GetRole")
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestRole"}}

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.render_trust_policy_template",
                return_value='{"Version": "2012-10-17", "Statement": []}',
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.create_role.validate_rendered_policy",
                return_value={"Version": "2012-10-17", "Statement": []},
            ),
        ):
            get_or_create_runtime_execution_role(
                session=session,
                logger=mock_logger,
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
            )

        mock_iam.put_role_policy.assert_called_once()
        call_kwargs = mock_iam.put_role_policy.call_args[1]
        policy_document = call_kwargs["PolicyDocument"]

        parsed = json.loads(policy_document)
        assert isinstance(parsed, dict), "Policy document is double-encoded"
        assert parsed.get("Version") == "2012-10-17"
        assert "Statement" in parsed
