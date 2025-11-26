"""Unit tests for ObservabilityDeliveryManager.

These tests use mocking to test the CloudWatch delivery configuration logic
without making actual AWS API calls.

Run with: pytest tests/unit/test_observability_delivery.py -v
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# Import the module under test
from bedrock_agentcore_starter_toolkit.operations.observability.delivery import (
    ObservabilityDeliveryManager,
    enable_observability_for_resource,
)


class TestObservabilityDeliveryManagerInit:
    """Tests for ObservabilityDeliveryManager initialization."""

    @patch("boto3.Session")
    def test_init_with_region(self, mock_session_class):
        """Test initialization with explicit region."""
        mock_session = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_session.client.return_value.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_session_class.return_value = mock_session

        manager = ObservabilityDeliveryManager(region_name="us-west-2")

        assert manager.region == "us-west-2"
        assert manager.account_id == "123456789012"

    @patch("boto3.Session")
    def test_init_with_session(self, mock_session_class):
        """Test initialization with boto3 session."""
        mock_session = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_session.client.return_value.get_caller_identity.return_value = {"Account": "123456789012"}

        manager = ObservabilityDeliveryManager(boto3_session=mock_session)

        assert manager.region == "us-east-1"
        assert manager.account_id == "123456789012"

    @patch("boto3.Session")
    def test_init_without_region_raises(self, mock_session_class):
        """Test that init raises ValueError if no region available."""
        mock_session = MagicMock()
        mock_session.region_name = None
        mock_session_class.return_value = mock_session

        with pytest.raises(ValueError, match="AWS region must be specified"):
            ObservabilityDeliveryManager()


class TestEnableObservabilityForResource:
    """Tests for enable_observability_for_resource method."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager with mocked AWS clients."""
        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.region_name = "us-east-1"
            mock_session.client.return_value.get_caller_identity.return_value = {"Account": "123456789012"}
            mock_session_class.return_value = mock_session

            manager = ObservabilityDeliveryManager(region_name="us-east-1")

            # Mock the logs client
            manager._logs_client = MagicMock()

            return manager

    def test_enable_observability_success(self, mock_manager):
        """Test successful observability enablement."""
        # Configure mocks for success
        mock_manager._logs_client.create_log_group.return_value = {}
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-logs-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-logs-destination",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-logs-destination",
            }
        }
        mock_manager._logs_client.create_delivery.return_value = {"id": "delivery-123"}

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory",
            resource_id="test-memory",
            resource_type="memory",
        )

        assert result["status"] == "success"
        assert result["logs_enabled"] is True
        assert result["traces_enabled"] is True
        assert result["log_group"] == "/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/test-memory"

    def test_enable_observability_logs_only(self, mock_manager):
        """Test enabling only logs (no traces)."""
        mock_manager._logs_client.create_log_group.return_value = {}
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-logs-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-logs-destination",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-logs-destination",
            }
        }
        mock_manager._logs_client.create_delivery.return_value = {"id": "delivery-123"}

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory",
            resource_id="test-memory",
            resource_type="memory",
            enable_logs=True,
            enable_traces=False,
        )

        assert result["status"] == "success"
        assert result["logs_enabled"] is True
        assert result["traces_enabled"] is False

    def test_enable_observability_traces_only(self, mock_manager):
        """Test enabling only traces (no logs)."""
        mock_manager._logs_client.create_log_group.return_value = {}
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-traces-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-traces-destination",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-traces-destination",
            }
        }
        mock_manager._logs_client.create_delivery.return_value = {"id": "delivery-123"}

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory",
            resource_id="test-memory",
            resource_type="memory",
            enable_logs=False,
            enable_traces=True,
        )

        assert result["status"] == "success"
        assert result["logs_enabled"] is False
        assert result["traces_enabled"] is True

    def test_enable_observability_custom_log_group(self, mock_manager):
        """Test with custom log group name."""
        mock_manager._logs_client.create_log_group.return_value = {}
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-logs-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-logs-destination",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-logs-destination",
            }
        }
        mock_manager._logs_client.create_delivery.return_value = {"id": "delivery-123"}

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test-memory",
            resource_id="test-memory",
            resource_type="memory",
            custom_log_group="/my/custom/log-group",
        )

        assert result["status"] == "success"
        assert result["log_group"] == "/my/custom/log-group"

    def test_enable_observability_invalid_resource_type(self, mock_manager):
        """Test that invalid resource type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported resource_type"):
            mock_manager.enable_observability_for_resource(
                resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:invalid/test",
                resource_id="test",
                resource_type="invalid",
            )

    def test_enable_observability_all_resource_types(self, mock_manager):
        """Test that all supported resource types work."""
        mock_manager._logs_client.create_log_group.return_value = {}
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-dest",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-dest",
            }
        }
        mock_manager._logs_client.create_delivery.return_value = {"id": "delivery-123"}

        for resource_type in ["memory", "gateway", "runtime", "tools", "identity"]:
            result = mock_manager.enable_observability_for_resource(
                resource_arn=f"arn:aws:bedrock-agentcore:us-east-1:123456789012:{resource_type}/test",
                resource_id="test",
                resource_type=resource_type,
            )
            assert result["status"] == "success"
            assert result["resource_type"] == resource_type

    def test_enable_observability_log_group_already_exists(self, mock_manager):
        """Test handling when log group already exists."""
        error_response = {"Error": {"Code": "ResourceAlreadyExistsException", "Message": "Log group already exists"}}
        mock_manager._logs_client.create_log_group.side_effect = ClientError(error_response, "CreateLogGroup")
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-dest",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-dest",
            }
        }
        mock_manager._logs_client.create_delivery.return_value = {"id": "delivery-123"}

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test",
            resource_id="test",
            resource_type="memory",
        )

        # Should succeed even if log group exists
        assert result["status"] == "success"

    def test_enable_observability_delivery_already_exists(self, mock_manager):
        """Test handling when delivery already exists."""
        mock_manager._logs_client.create_log_group.return_value = {}
        mock_manager._logs_client.put_delivery_source.return_value = {"deliverySource": {"name": "test-source"}}
        mock_manager._logs_client.put_delivery_destination.return_value = {
            "deliveryDestination": {
                "name": "test-dest",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:test-dest",
            }
        }

        error_response = {"Error": {"Code": "ConflictException", "Message": "Delivery already exists"}}
        mock_manager._logs_client.create_delivery.side_effect = ClientError(error_response, "CreateDelivery")

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test",
            resource_id="test",
            resource_type="memory",
        )

        # Should succeed with existing delivery
        assert result["status"] == "success"
        assert result["deliveries"]["logs"]["delivery_id"] == "existing"

    def test_enable_observability_api_error(self, mock_manager):
        """Test handling of AWS API errors."""
        error_response = {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}}
        mock_manager._logs_client.create_log_group.side_effect = ClientError(error_response, "CreateLogGroup")

        result = mock_manager.enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/test",
            resource_id="test",
            resource_type="memory",
        )

        assert result["status"] == "error"
        assert "AccessDeniedException" in result["error"]


class TestDisableObservabilityForResource:
    """Tests for disable_observability_for_resource method."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager."""
        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.region_name = "us-east-1"
            mock_session.client.return_value.get_caller_identity.return_value = {"Account": "123456789012"}
            mock_session_class.return_value = mock_session

            manager = ObservabilityDeliveryManager(region_name="us-east-1")
            manager._logs_client = MagicMock()

            return manager

    def test_disable_observability_success(self, mock_manager):
        """Test successful observability disablement."""
        mock_manager._logs_client.delete_delivery_source.return_value = {}
        mock_manager._logs_client.delete_delivery_destination.return_value = {}

        result = mock_manager.disable_observability_for_resource(
            resource_id="test-memory",
        )

        assert result["status"] == "success"
        assert len(result["deleted"]) == 4  # 2 sources + 2 destinations

    def test_disable_observability_with_log_group_deletion(self, mock_manager):
        """Test disabling with log group deletion."""
        mock_manager._logs_client.delete_delivery_source.return_value = {}
        mock_manager._logs_client.delete_delivery_destination.return_value = {}
        mock_manager._logs_client.delete_log_group.return_value = {}

        result = mock_manager.disable_observability_for_resource(
            resource_id="test-memory",
            delete_log_group=True,
        )

        assert result["status"] == "success"
        # Should have attempted to delete log groups for all resource types
        assert mock_manager._logs_client.delete_log_group.called

    def test_disable_observability_resource_not_found(self, mock_manager):
        """Test handling when resources don't exist."""
        error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}}
        mock_manager._logs_client.delete_delivery_source.side_effect = ClientError(
            error_response, "DeleteDeliverySource"
        )
        mock_manager._logs_client.delete_delivery_destination.side_effect = ClientError(
            error_response, "DeleteDeliveryDestination"
        )

        result = mock_manager.disable_observability_for_resource(
            resource_id="nonexistent",
        )

        # Should succeed (resources just don't exist)
        assert result["status"] == "success"


class TestGetObservabilityStatus:
    """Tests for get_observability_status method."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager."""
        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.region_name = "us-east-1"
            mock_session.client.return_value.get_caller_identity.return_value = {"Account": "123456789012"}
            mock_session_class.return_value = mock_session

            manager = ObservabilityDeliveryManager(region_name="us-east-1")
            manager._logs_client = MagicMock()

            return manager

    def test_get_status_both_configured(self, mock_manager):
        """Test status when both logs and traces are configured."""
        mock_manager._logs_client.get_delivery_source.return_value = {"deliverySource": {"name": "test-source"}}

        result = mock_manager.get_observability_status(resource_id="test-memory")

        assert result["logs"]["configured"] is True
        assert result["traces"]["configured"] is True

    def test_get_status_not_configured(self, mock_manager):
        """Test status when nothing is configured."""
        error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}}
        mock_manager._logs_client.get_delivery_source.side_effect = ClientError(error_response, "GetDeliverySource")

        result = mock_manager.get_observability_status(resource_id="test-memory")

        assert result["logs"]["configured"] is False
        assert result["traces"]["configured"] is False


class TestConvenienceFunction:
    """Tests for the convenience function matching AWS docs."""

    @patch("bedrock_agentcore_starter_toolkit.operations.observability.delivery.ObservabilityDeliveryManager")
    def test_enable_observability_for_resource_function(self, mock_manager_class):
        """Test the convenience function."""
        mock_manager = MagicMock()
        mock_manager.account_id = "123456789012"
        mock_manager.enable_observability_for_resource.return_value = {
            "status": "success",
            "log_group": "/aws/vendedlogs/bedrock-agentcore/memory/APPLICATION_LOGS/my-memory",
            "deliveries": {
                "logs": {"delivery_id": "logs-123"},
                "traces": {"delivery_id": "traces-123"},
            },
        }
        mock_manager_class.return_value = mock_manager

        result = enable_observability_for_resource(
            resource_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/my-memory",
            resource_id="my-memory",
            account_id="123456789012",
            region="us-east-1",
        )

        assert result["status"] == "success"
        assert result["logs_delivery_id"] == "logs-123"
        assert result["traces_delivery_id"] == "traces-123"
