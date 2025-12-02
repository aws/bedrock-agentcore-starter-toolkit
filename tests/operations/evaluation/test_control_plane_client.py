"""Comprehensive unit tests for control plane client.

Tests all control plane API calls with data-driven approach.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.evaluation.control_plane_client import (
    EvaluationControlPlaneClient,
)

# Apply mock_boto3_clients fixture to prevent real AWS calls
pytestmark = pytest.mark.usefixtures("mock_boto3_clients")

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def mock_boto_client():
    """Mock boto3 client."""
    return MagicMock()


@pytest.fixture
def valid_config():
    """Valid evaluator configuration."""
    return {
        "llmAsAJudge": {"instructions": "Evaluate the response", "modelId": "anthropic.claude-3-sonnet-20240229-v1:0"}
    }


@pytest.fixture
def evaluator_list_response():
    """Sample list evaluators API response."""
    return {
        "evaluators": [
            {
                "evaluatorId": "Builtin.Helpfulness",
                "evaluatorName": "Helpfulness",
                "evaluatorLevel": "TRACE",
                "description": "Evaluates helpfulness",
                "evaluatorArn": "arn:aws:bedrock:::evaluator/Builtin.Helpfulness",
            },
            {
                "evaluatorId": "Custom.MyEval",
                "evaluatorName": "My Evaluator",
                "evaluatorLevel": "SESSION",
                "description": "Custom evaluator",
                "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.MyEval",
            },
        ]
    }


@pytest.fixture
def evaluator_details_response():
    """Sample get evaluator API response."""
    return {
        "evaluatorId": "Custom.MyEval",
        "evaluatorName": "My Evaluator",
        "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.MyEval",
        "level": "TRACE",
        "description": "A custom evaluator",
        "evaluatorConfig": {
            "llmAsAJudge": {"instructions": "Evaluate carefully", "modelId": "anthropic.claude-3-sonnet-20240229-v1:0"}
        },
    }


# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Test client initialization."""

    @patch("boto3.client")
    def test_init_basic(self, mock_boto3_client):
        """Test basic initialization with region."""
        # Mock STS get_caller_identity
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        # Return appropriate mocks for STS and control plane client
        def client_side_effect(service_name, **kwargs):
            if service_name == "sts":
                return mock_sts
            return MagicMock()

        mock_boto3_client.side_effect = client_side_effect

        client = EvaluationControlPlaneClient(region_name="us-west-2")

        assert client.region == "us-west-2"
        assert client.endpoint_url is not None  # Should have default endpoint
        assert client.account_id == "123456789012"
        # Should be called twice: once for STS, twice for control plane, once for iam
        assert mock_boto3_client.call_count == 4

    @patch("boto3.client")
    def test_init_with_custom_endpoint(self, mock_boto3_client):
        """Test initialization with custom endpoint."""
        custom_endpoint = "https://custom-eval-endpoint.com"

        client = EvaluationControlPlaneClient(region_name="us-east-1", endpoint_url=custom_endpoint)

        assert client.endpoint_url == custom_endpoint
        call_args = mock_boto3_client.call_args
        assert call_args.kwargs["endpoint_url"] == custom_endpoint

    @patch("boto3.client")
    @patch.dict(os.environ, {"AGENTCORE_EVAL_CP_ENDPOINT": "https://env-endpoint.com"})
    def test_init_with_env_var(self, mock_boto3_client):
        """Test initialization uses environment variable if no endpoint provided."""
        client = EvaluationControlPlaneClient(region_name="us-west-2")

        assert client.endpoint_url == "https://env-endpoint.com"

    def test_init_with_mock_client(self, mock_boto_client):
        """Test initialization with pre-configured client (for testing)."""
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        assert client.client == mock_boto_client

    @pytest.mark.parametrize(
        "region",
        [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-northeast-1",
        ],
    )
    @patch("boto3.client")
    def test_init_various_regions(self, mock_boto3_client, region):
        """Test initialization with various AWS regions."""
        client = EvaluationControlPlaneClient(region_name=region)

        assert client.region == region
        call_args = mock_boto3_client.call_args
        assert call_args.kwargs["region_name"] == region


# =============================================================================
# List Evaluators Tests
# =============================================================================


class TestListEvaluators:
    """Test list_evaluators operation."""

    def test_list_evaluators_default(self, mock_boto_client, evaluator_list_response):
        """Test listing evaluators with default max results."""
        mock_boto_client.list_evaluators.return_value = evaluator_list_response
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.list_evaluators()

        assert "evaluators" in result
        assert len(result["evaluators"]) == 2
        mock_boto_client.list_evaluators.assert_called_once_with(maxResults=50)

    @pytest.mark.parametrize("max_results", [10, 25, 50, 100, 500])
    def test_list_evaluators_custom_max(self, mock_boto_client, max_results):
        """Test listing with various max results values."""
        mock_boto_client.list_evaluators.return_value = {"evaluators": []}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.list_evaluators(max_results=max_results)

        mock_boto_client.list_evaluators.assert_called_once_with(maxResults=max_results)

    def test_list_evaluators_empty_result(self, mock_boto_client):
        """Test handling empty evaluators list."""
        mock_boto_client.list_evaluators.return_value = {"evaluators": []}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.list_evaluators()

        assert result["evaluators"] == []

    def test_list_evaluators_with_builtin_and_custom(self, mock_boto_client, evaluator_list_response):
        """Test result includes both builtin and custom evaluators."""
        mock_boto_client.list_evaluators.return_value = evaluator_list_response
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.list_evaluators()
        evaluators = result["evaluators"]

        # Check builtin
        builtin = [e for e in evaluators if e["evaluatorId"].startswith("Builtin.")]
        assert len(builtin) == 1
        assert builtin[0]["evaluatorId"] == "Builtin.Helpfulness"

        # Check custom
        custom = [e for e in evaluators if not e["evaluatorId"].startswith("Builtin.")]
        assert len(custom) == 1
        assert custom[0]["evaluatorId"] == "Custom.MyEval"


# =============================================================================
# Get Evaluator Tests
# =============================================================================


class TestGetEvaluator:
    """Test get_evaluator operation."""

    def test_get_evaluator_success(self, mock_boto_client, evaluator_details_response):
        """Test getting evaluator details."""
        mock_boto_client.get_evaluator.return_value = evaluator_details_response
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.get_evaluator(evaluator_id="Custom.MyEval")

        assert result["evaluatorId"] == "Custom.MyEval"
        assert result["level"] == "TRACE"
        assert "evaluatorConfig" in result
        mock_boto_client.get_evaluator.assert_called_once_with(evaluatorId="Custom.MyEval")

    @pytest.mark.parametrize(
        "evaluator_id",
        [
            "Builtin.Helpfulness",
            "Builtin.Accuracy",
            "Custom.MyEval",
            "Custom.AnotherEval",
            "arn:aws:bedrock:::evaluator/Test",
        ],
    )
    def test_get_evaluator_various_ids(self, mock_boto_client, evaluator_id):
        """Test getting evaluators with various ID formats."""
        mock_boto_client.get_evaluator.return_value = {"evaluatorId": evaluator_id}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.get_evaluator(evaluator_id=evaluator_id)

        assert result["evaluatorId"] == evaluator_id
        mock_boto_client.get_evaluator.assert_called_once_with(evaluatorId=evaluator_id)

    def test_get_evaluator_includes_config(self, mock_boto_client, evaluator_details_response):
        """Test response includes evaluator configuration."""
        mock_boto_client.get_evaluator.return_value = evaluator_details_response
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.get_evaluator(evaluator_id="Custom.MyEval")

        assert "evaluatorConfig" in result
        config = result["evaluatorConfig"]
        assert "llmAsAJudge" in config
        assert "instructions" in config["llmAsAJudge"]


# =============================================================================
# Create Evaluator Tests
# =============================================================================


class TestCreateEvaluator:
    """Test create_evaluator operation."""

    def test_create_evaluator_minimal(self, mock_boto_client, valid_config):
        """Test creating evaluator with minimal parameters."""
        mock_boto_client.create_evaluator.return_value = {
            "evaluatorId": "Custom.NewEval",
            "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.NewEval",
        }
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.create_evaluator(name="NewEval", config=valid_config)

        assert result["evaluatorId"] == "Custom.NewEval"
        assert "evaluatorArn" in result
        mock_boto_client.create_evaluator.assert_called_once()
        call_args = mock_boto_client.create_evaluator.call_args
        assert call_args.kwargs["evaluatorName"] == "NewEval"
        assert call_args.kwargs["evaluatorConfig"] == valid_config
        assert call_args.kwargs["level"] == "TRACE"  # Default
        assert "description" not in call_args.kwargs

    @pytest.mark.parametrize("level", ["SESSION", "TRACE", "TOOL_CALL"])
    def test_create_evaluator_with_levels(self, mock_boto_client, valid_config, level):
        """Test creating evaluators with different levels."""
        mock_boto_client.create_evaluator.return_value = {"evaluatorId": "Test"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.create_evaluator(name="TestEval", config=valid_config, level=level)

        call_args = mock_boto_client.create_evaluator.call_args
        assert call_args.kwargs["level"] == level

    def test_create_evaluator_with_description(self, mock_boto_client, valid_config):
        """Test creating evaluator with description."""
        mock_boto_client.create_evaluator.return_value = {"evaluatorId": "Test"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        description = "This evaluates responses for helpfulness"
        client.create_evaluator(name="TestEval", config=valid_config, description=description)

        call_args = mock_boto_client.create_evaluator.call_args
        assert call_args.kwargs["description"] == description

    def test_create_evaluator_without_description(self, mock_boto_client, valid_config):
        """Test description is not included when None."""
        mock_boto_client.create_evaluator.return_value = {"evaluatorId": "Test"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.create_evaluator(name="TestEval", config=valid_config)

        call_args = mock_boto_client.create_evaluator.call_args
        assert "description" not in call_args.kwargs

    def test_create_evaluator_empty_string_description(self, mock_boto_client, valid_config):
        """Test empty string description is not included."""
        mock_boto_client.create_evaluator.return_value = {"evaluatorId": "Test"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.create_evaluator(name="TestEval", config=valid_config, description="")

        call_args = mock_boto_client.create_evaluator.call_args
        # Empty string is falsy, so should not be included
        assert "description" not in call_args.kwargs


# =============================================================================
# Update Evaluator Tests
# =============================================================================


class TestUpdateEvaluator:
    """Test update_evaluator operation."""

    def test_update_evaluator_description_only(self, mock_boto_client, evaluator_details_response):
        """Test updating only description (fetches existing config)."""
        mock_boto_client.get_evaluator.return_value = evaluator_details_response
        mock_boto_client.update_evaluator.return_value = {"status": "success"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.update_evaluator(evaluator_id="Custom.MyEval", description="Updated description")

        assert result["status"] == "success"
        # Should fetch existing config
        mock_boto_client.get_evaluator.assert_called_once_with(evaluatorId="Custom.MyEval")
        # Should call update with description and existing config
        call_args = mock_boto_client.update_evaluator.call_args
        assert call_args.kwargs["description"] == "Updated description"
        assert call_args.kwargs["evaluatorConfig"] == evaluator_details_response["evaluatorConfig"]

    def test_update_evaluator_config_only(self, mock_boto_client, valid_config):
        """Test updating only config (no description fetch needed)."""
        mock_boto_client.update_evaluator.return_value = {"status": "success"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.update_evaluator(evaluator_id="Custom.MyEval", config=valid_config)

        # Should NOT fetch existing config
        mock_boto_client.get_evaluator.assert_not_called()
        # Should call update with config only
        call_args = mock_boto_client.update_evaluator.call_args
        assert call_args.kwargs["evaluatorConfig"] == valid_config
        assert "description" not in call_args.kwargs

    def test_update_evaluator_both_fields(self, mock_boto_client, valid_config):
        """Test updating both description and config."""
        mock_boto_client.update_evaluator.return_value = {"status": "success"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.update_evaluator(evaluator_id="Custom.MyEval", description="New description", config=valid_config)

        # Should NOT fetch existing config (new config provided)
        mock_boto_client.get_evaluator.assert_not_called()
        # Should call update with both
        call_args = mock_boto_client.update_evaluator.call_args
        assert call_args.kwargs["description"] == "New description"
        assert call_args.kwargs["evaluatorConfig"] == valid_config

    def test_update_evaluator_description_no_existing_config(self, mock_boto_client):
        """Test updating description when get_evaluator returns no config."""
        mock_boto_client.get_evaluator.return_value = {
            "evaluatorId": "Custom.MyEval",
            # No evaluatorConfig key
        }
        mock_boto_client.update_evaluator.return_value = {"status": "success"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        # Should still call update (let API handle the error if needed)
        client.update_evaluator(evaluator_id="Custom.MyEval", description="Updated")

        call_args = mock_boto_client.update_evaluator.call_args
        assert call_args.kwargs["description"] == "Updated"
        # Config should not be included if it wasn't found
        assert "evaluatorConfig" not in call_args.kwargs

    def test_update_evaluator_neither_field(self, mock_boto_client):
        """Test updating with neither description nor config."""
        mock_boto_client.update_evaluator.return_value = {"status": "success"}
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        # Call with no updates - should still work (API will handle validation)
        client.update_evaluator(evaluator_id="Custom.MyEval")

        # Should call API with just evaluator ID
        call_args = mock_boto_client.update_evaluator.call_args
        assert call_args.kwargs["evaluatorId"] == "Custom.MyEval"
        assert "description" not in call_args.kwargs
        assert "evaluatorConfig" not in call_args.kwargs


# =============================================================================
# Delete Evaluator Tests
# =============================================================================


class TestDeleteEvaluator:
    """Test delete_evaluator operation."""

    def test_delete_evaluator_success(self, mock_boto_client):
        """Test successful deletion."""
        mock_boto_client.delete_evaluator.return_value = None
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.delete_evaluator(evaluator_id="Custom.MyEval")

        assert result is None
        mock_boto_client.delete_evaluator.assert_called_once_with(evaluatorId="Custom.MyEval")

    @pytest.mark.parametrize(
        "evaluator_id",
        [
            "Custom.MyEval",
            "Custom.ToDelete",
            "arn:aws:bedrock:::evaluator/Custom.Test",
        ],
    )
    def test_delete_evaluator_various_ids(self, mock_boto_client, evaluator_id):
        """Test deleting evaluators with various ID formats."""
        mock_boto_client.delete_evaluator.return_value = None
        client = EvaluationControlPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.delete_evaluator(evaluator_id=evaluator_id)

        mock_boto_client.delete_evaluator.assert_called_once_with(evaluatorId=evaluator_id)
