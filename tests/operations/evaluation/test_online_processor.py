"""Tests for online evaluation processor."""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor import (
    create_online_evaluation_config,
    delete_online_evaluation_config,
    get_online_evaluation_config,
    list_online_evaluation_configs,
    update_online_evaluation_config,
)

# =============================================================================
# create_online_evaluation_config Tests
# =============================================================================


class TestCreateOnlineEvaluationConfig:
    """Test create_online_evaluation_config function."""

    def test_create_with_minimal_params(self):
        """Test create with only required parameters."""
        mock_client = Mock()
        mock_client.create_online_evaluation_config.return_value = {
            "onlineEvaluationConfigId": "config-123",
            "status": "ENABLED",
        }

        result = create_online_evaluation_config(client=mock_client, config_name="my-config", agent_id="agent-456")

        assert result["onlineEvaluationConfigId"] == "config-123"
        mock_client.create_online_evaluation_config.assert_called_once()

    def test_create_with_all_params(self):
        """Test create with all optional parameters."""
        mock_client = Mock()
        mock_client.create_online_evaluation_config.return_value = {
            "onlineEvaluationConfigId": "config-123",
            "status": "DISABLED",
        }

        result = create_online_evaluation_config(
            client=mock_client,
            config_name="my-config",
            agent_id="agent-456",
            agent_endpoint="DRAFT",
            config_description="Test config",
            sampling_rate=50.0,
            evaluator_list=["Builtin.Helpfulness"],
            execution_role="arn:aws:iam::123:role/test",
            auto_create_execution_role=False,
            enable_on_create=False,
        )

        assert result["onlineEvaluationConfigId"] == "config-123"
        assert result["status"] == "DISABLED"
        call_kwargs = mock_client.create_online_evaluation_config.call_args[1]
        assert call_kwargs["sampling_rate"] == 50.0
        assert call_kwargs["enable_on_create"] is False

    def test_create_requires_config_name(self):
        """Test create fails without config_name."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="config_name is required"):
            create_online_evaluation_config(client=mock_client, config_name="", agent_id="agent-456")

    def test_create_requires_agent_id(self):
        """Test create fails without agent_id."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="agent_id is required"):
            create_online_evaluation_config(client=mock_client, config_name="my-config", agent_id="")

    def test_create_validates_sampling_rate_low(self):
        """Test create validates sampling_rate is not below 0."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="sampling_rate must be between 0 and 100"):
            create_online_evaluation_config(
                client=mock_client, config_name="my-config", agent_id="agent-456", sampling_rate=-1.0
            )

    def test_create_validates_sampling_rate_high(self):
        """Test create validates sampling_rate is not above 100."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="sampling_rate must be between 0 and 100"):
            create_online_evaluation_config(
                client=mock_client, config_name="my-config", agent_id="agent-456", sampling_rate=101.0
            )

    def test_create_with_default_evaluators(self):
        """Test create uses default evaluators when none provided."""
        mock_client = Mock()
        mock_client.create_online_evaluation_config.return_value = {
            "onlineEvaluationConfigId": "config-123",
            "status": "ENABLED",
        }

        result = create_online_evaluation_config(
            client=mock_client, config_name="my-config", agent_id="agent-456", evaluator_list=None
        )

        # Should pass None to client (client will use defaults)
        call_kwargs = mock_client.create_online_evaluation_config.call_args[1]
        assert call_kwargs["evaluator_list"] is None
        assert result["onlineEvaluationConfigId"] == "config-123"


# =============================================================================
# get_online_evaluation_config Tests
# =============================================================================


class TestGetOnlineEvaluationConfig:
    """Test get_online_evaluation_config function."""

    def test_get_config_success(self):
        """Test successful config retrieval."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "onlineEvaluationConfigId": "config-123",
            "configName": "my-config",
            "status": "ENABLED",
        }

        result = get_online_evaluation_config(client=mock_client, config_id="config-123")

        assert result["onlineEvaluationConfigId"] == "config-123"
        assert result["configName"] == "my-config"
        mock_client.get_online_evaluation_config.assert_called_once_with(config_id="config-123")

    def test_get_config_requires_config_id(self):
        """Test get fails without config_id."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="config_id is required"):
            get_online_evaluation_config(client=mock_client, config_id="")

    def test_get_config_whitespace_config_id(self):
        """Test get fails with whitespace-only config_id."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="config_id is required"):
            get_online_evaluation_config(client=mock_client, config_id="   ")


# =============================================================================
# list_online_evaluation_configs Tests
# =============================================================================


class TestListOnlineEvaluationConfigs:
    """Test list_online_evaluation_configs function."""

    def test_list_all_configs(self):
        """Test list all configs without filter."""
        mock_client = Mock()
        mock_client.list_online_evaluation_configs.return_value = {
            "onlineEvaluationConfigs": [
                {"onlineEvaluationConfigId": "config-1"},
                {"onlineEvaluationConfigId": "config-2"},
            ]
        }

        result = list_online_evaluation_configs(client=mock_client)

        assert len(result["onlineEvaluationConfigs"]) == 2
        mock_client.list_online_evaluation_configs.assert_called_once_with(agent_id=None, max_results=50)

    def test_list_configs_filtered_by_agent(self):
        """Test list configs filtered by agent_id."""
        mock_client = Mock()
        mock_client.list_online_evaluation_configs.return_value = {
            "onlineEvaluationConfigs": [{"onlineEvaluationConfigId": "config-1"}]
        }

        result = list_online_evaluation_configs(client=mock_client, agent_id="agent-456")

        assert len(result["onlineEvaluationConfigs"]) == 1
        mock_client.list_online_evaluation_configs.assert_called_once_with(agent_id="agent-456", max_results=50)

    def test_list_configs_with_max_results(self):
        """Test list configs with custom max_results."""
        mock_client = Mock()
        mock_client.list_online_evaluation_configs.return_value = {"onlineEvaluationConfigs": []}

        result = list_online_evaluation_configs(client=mock_client, max_results=100)

        assert result["onlineEvaluationConfigs"] == []
        mock_client.list_online_evaluation_configs.assert_called_once_with(agent_id=None, max_results=100)

    def test_list_configs_empty_result(self):
        """Test list configs when no configs exist."""
        mock_client = Mock()
        mock_client.list_online_evaluation_configs.return_value = {"onlineEvaluationConfigs": []}

        result = list_online_evaluation_configs(client=mock_client)

        assert result["onlineEvaluationConfigs"] == []


# =============================================================================
# update_online_evaluation_config Tests
# =============================================================================


class TestUpdateOnlineEvaluationConfig:
    """Test update_online_evaluation_config function."""

    def test_update_status(self):
        """Test update config status."""
        mock_client = Mock()
        mock_client.update_online_evaluation_config.return_value = {
            "onlineEvaluationConfigId": "config-123",
            "status": "DISABLED",
        }

        result = update_online_evaluation_config(client=mock_client, config_id="config-123", status="DISABLED")

        assert result["status"] == "DISABLED"
        mock_client.update_online_evaluation_config.assert_called_once()

    def test_update_sampling_rate(self):
        """Test update config sampling_rate."""
        mock_client = Mock()
        mock_client.update_online_evaluation_config.return_value = {"onlineEvaluationConfigId": "config-123"}

        update_online_evaluation_config(client=mock_client, config_id="config-123", sampling_rate=75.0)

        call_kwargs = mock_client.update_online_evaluation_config.call_args[1]
        assert call_kwargs["sampling_rate"] == 75.0

    def test_update_evaluator_list(self):
        """Test update config evaluator list."""
        mock_client = Mock()
        mock_client.update_online_evaluation_config.return_value = {"onlineEvaluationConfigId": "config-123"}

        update_online_evaluation_config(
            client=mock_client, config_id="config-123", evaluator_list=["Builtin.Helpfulness", "Builtin.Accuracy"]
        )

        call_kwargs = mock_client.update_online_evaluation_config.call_args[1]
        assert len(call_kwargs["evaluator_list"]) == 2

    def test_update_description(self):
        """Test update config description."""
        mock_client = Mock()
        mock_client.update_online_evaluation_config.return_value = {"onlineEvaluationConfigId": "config-123"}

        update_online_evaluation_config(client=mock_client, config_id="config-123", description="New description")

        call_kwargs = mock_client.update_online_evaluation_config.call_args[1]
        assert call_kwargs["description"] == "New description"

    def test_update_requires_config_id(self):
        """Test update fails without config_id."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="config_id is required"):
            update_online_evaluation_config(client=mock_client, config_id="", status="ENABLED")

    def test_update_validates_sampling_rate_low(self):
        """Test update validates sampling_rate is not below 0."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="sampling_rate must be between 0 and 100"):
            update_online_evaluation_config(client=mock_client, config_id="config-123", sampling_rate=-5.0)

    def test_update_validates_sampling_rate_high(self):
        """Test update validates sampling_rate is not above 100."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="sampling_rate must be between 0 and 100"):
            update_online_evaluation_config(client=mock_client, config_id="config-123", sampling_rate=150.0)

    def test_update_validates_status(self):
        """Test update validates status value."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="status must be ENABLED or DISABLED"):
            update_online_evaluation_config(client=mock_client, config_id="config-123", status="INVALID")

    def test_update_all_fields(self):
        """Test update with all fields at once."""
        mock_client = Mock()
        mock_client.update_online_evaluation_config.return_value = {"onlineEvaluationConfigId": "config-123"}

        update_online_evaluation_config(
            client=mock_client,
            config_id="config-123",
            status="ENABLED",
            sampling_rate=25.0,
            evaluator_list=["Builtin.GoalSuccessRate"],
            description="Updated config",
        )

        call_kwargs = mock_client.update_online_evaluation_config.call_args[1]
        assert call_kwargs["status"] == "ENABLED"
        assert call_kwargs["sampling_rate"] == 25.0
        assert call_kwargs["description"] == "Updated config"


# =============================================================================
# delete_online_evaluation_config Tests
# =============================================================================


class TestDeleteOnlineEvaluationConfig:
    """Test delete_online_evaluation_config function."""

    def test_delete_without_role(self):
        """Test delete config without deleting role."""
        mock_client = Mock()
        mock_client.delete_online_evaluation_config.return_value = None

        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=False)

        mock_client.delete_online_evaluation_config.assert_called_once_with(config_id="config-123")
        # Should not try to get config details
        mock_client.get_online_evaluation_config.assert_not_called()

    def test_delete_requires_config_id(self):
        """Test delete fails without config_id."""
        mock_client = Mock()

        with pytest.raises(ValueError, match="config_id is required"):
            delete_online_evaluation_config(client=mock_client, config_id="")

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_with_role(self, mock_boto3):
        """Test delete config with role deletion."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        mock_iam.list_role_policies.return_value = {"PolicyNames": ["policy-1"]}
        mock_boto3.client.return_value = mock_iam

        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        # Should get config to extract role ARN
        mock_client.get_online_evaluation_config.assert_called_once_with(config_id="config-123")
        # Should delete config
        mock_client.delete_online_evaluation_config.assert_called_once_with(config_id="config-123")
        # Should delete role policies and role
        mock_iam.list_role_policies.assert_called_once_with(RoleName="test-role")
        mock_iam.delete_role_policy.assert_called_once_with(RoleName="test-role", PolicyName="policy-1")
        mock_iam.delete_role.assert_called_once_with(RoleName="test-role")

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_with_role_no_policies(self, mock_boto3):
        """Test delete config with role that has no inline policies."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        mock_iam.list_role_policies.return_value = {"PolicyNames": []}
        mock_boto3.client.return_value = mock_iam

        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        # Should delete role without deleting policies
        mock_iam.list_role_policies.assert_called_once()
        mock_iam.delete_role_policy.assert_not_called()
        mock_iam.delete_role.assert_called_once_with(RoleName="test-role")

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_with_role_get_config_fails(self, mock_boto3):
        """Test delete config when getting config details fails."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.side_effect = RuntimeError("API error")
        mock_client.delete_online_evaluation_config.return_value = None

        # Should still delete config even if getting role ARN fails
        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        mock_client.delete_online_evaluation_config.assert_called_once_with(config_id="config-123")
        # Should not try to delete role
        mock_boto3.client.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_with_role_no_role_arn_in_response(self, mock_boto3):
        """Test delete config when response doesn't contain role ARN."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {"onlineEvaluationConfigId": "config-123"}
        mock_client.delete_online_evaluation_config.return_value = None

        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        # Should delete config but not try to delete role
        mock_client.delete_online_evaluation_config.assert_called_once()
        mock_boto3.client.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_role_nosuchentity_error(self, mock_boto3):
        """Test delete role when role doesn't exist."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        mock_iam.list_role_policies.return_value = {"PolicyNames": []}
        error_response = {"Error": {"Code": "NoSuchEntity"}}
        mock_iam.delete_role.side_effect = ClientError(error_response, "DeleteRole")
        mock_boto3.client.return_value = mock_iam

        # Should not raise error when role doesn't exist
        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        mock_iam.delete_role.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_role_deleteconflict_error(self, mock_boto3):
        """Test delete role when role has conflicts."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        mock_iam.list_role_policies.return_value = {"PolicyNames": []}
        error_response = {"Error": {"Code": "DeleteConflict"}}
        mock_iam.delete_role.side_effect = ClientError(error_response, "DeleteRole")
        mock_boto3.client.return_value = mock_iam

        # Should raise RuntimeError for DeleteConflict
        with pytest.raises(RuntimeError, match="Cannot delete role"):
            delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_role_other_error(self, mock_boto3):
        """Test delete role when other error occurs."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        mock_iam.list_role_policies.return_value = {"PolicyNames": []}
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_iam.delete_role.side_effect = ClientError(error_response, "DeleteRole")
        mock_boto3.client.return_value = mock_iam

        # Should raise RuntimeError for other errors
        with pytest.raises(RuntimeError, match="Failed to delete role"):
            delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_role_policy_error(self, mock_boto3):
        """Test delete role when deleting policies fails."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_iam.list_role_policies.side_effect = ClientError(error_response, "ListRolePolicies")
        mock_boto3.client.return_value = mock_iam

        # Should still try to delete role even if policy deletion fails
        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        mock_iam.delete_role.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.online_processor.boto3")
    def test_delete_role_multiple_policies(self, mock_boto3):
        """Test delete role with multiple inline policies."""
        mock_client = Mock()
        mock_client.get_online_evaluation_config.return_value = {
            "evaluationExecutionRoleArn": "arn:aws:iam::123:role/test-role"
        }
        mock_client.delete_online_evaluation_config.return_value = None

        mock_iam = Mock()
        mock_iam.list_role_policies.return_value = {"PolicyNames": ["policy-1", "policy-2", "policy-3"]}
        mock_boto3.client.return_value = mock_iam

        delete_online_evaluation_config(client=mock_client, config_id="config-123", delete_execution_role=True)

        # Should delete all three policies
        assert mock_iam.delete_role_policy.call_count == 3
        mock_iam.delete_role.assert_called_once()
