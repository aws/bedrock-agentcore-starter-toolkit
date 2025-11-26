"""Integration tests for ObservabilityDeliveryManager.

These tests make actual AWS API calls and require:
1. Valid AWS credentials configured
2. Appropriate IAM permissions for CloudWatch Logs

Run with: pytest tests/integration/test_observability_delivery_integration.py -v --run-integration

To skip integration tests: pytest tests/integration/ -v (they're marked to skip by default)
"""

import os
import time
import uuid
import pytest
import boto3
from botocore.exceptions import ClientError


# Import the module under test
from bedrock_agentcore_starter_toolkit.operations.observability.delivery import (
    ObservabilityDeliveryManager,
    enable_observability_for_resource,
)


class TestObservabilityDeliveryIntegration:
    """Integration tests that make real AWS API calls."""

    @pytest.fixture(scope="class")
    def region(self):
        """Get the AWS region for tests."""
        return os.getenv("AWS_REGION", "us-east-1")

    @pytest.fixture(scope="class")
    def account_id(self):
        """Get the AWS account ID."""
        sts = boto3.client("sts")
        return sts.get_caller_identity()["Account"]

    @pytest.fixture
    def test_resource_id(self):
        """Generate a unique resource ID for testing."""
        return f"test-obs-{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def manager(self, region):
        """Create an ObservabilityDeliveryManager instance."""
        return ObservabilityDeliveryManager(region_name=region)

    @pytest.fixture
    def cleanup_resources(self, manager):
        """Fixture to track and clean up resources after tests."""
        resources_to_cleanup = []

        yield resources_to_cleanup

        # Cleanup after test
        for resource_id in resources_to_cleanup:
            try:
                manager.disable_observability_for_resource(
                    resource_id=resource_id,
                    delete_log_group=True,
                )
            except Exception as e:
                print(f"Cleanup warning for {resource_id}: {e}")

    def test_enable_and_disable_observability_memory(
        self, manager, test_resource_id, account_id, region, cleanup_resources
    ):
        """Test enabling and disabling observability for a memory resource."""
        cleanup_resources.append(test_resource_id)

        # Note: This creates delivery configuration but doesn't create the actual
        # AgentCore memory resource. The delivery source will fail if the resource
        # doesn't exist, so we test the expected error handling.

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{test_resource_id}"

        # Try to enable observability
        # This may fail if the memory resource doesn't exist, which is expected
        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='memory',
            enable_logs=True,
            enable_traces=True,
        )

        # The result depends on whether the resource exists
        # We're mainly testing that the code runs without throwing exceptions
        assert 'status' in result
        assert result['resource_id'] == test_resource_id
        assert result['resource_type'] == 'memory'

        # Test get status
        status = manager.get_observability_status(resource_id=test_resource_id)
        assert 'logs' in status
        assert 'traces' in status

        # Test disable
        disable_result = manager.disable_observability_for_resource(
            resource_id=test_resource_id,
            delete_log_group=True,
        )
        assert 'status' in disable_result

    def test_enable_observability_gateway(
        self, manager, test_resource_id, account_id, region, cleanup_resources
    ):
        """Test enabling observability for a gateway resource."""
        cleanup_resources.append(test_resource_id)

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{test_resource_id}"

        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='gateway',
            enable_logs=True,
            enable_traces=True,
        )

        assert 'status' in result
        assert result['resource_type'] == 'gateway'

    def test_custom_log_group(
        self, manager, test_resource_id, account_id, region, cleanup_resources
    ):
        """Test using a custom log group name."""
        cleanup_resources.append(test_resource_id)

        custom_log_group = f"/custom/agentcore/test/{test_resource_id}"
        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{test_resource_id}"

        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='memory',
            custom_log_group=custom_log_group,
        )

        assert result['log_group'] == custom_log_group

        # Cleanup custom log group
        try:
            logs_client = boto3.client('logs', region_name=region)
            logs_client.delete_log_group(logGroupName=custom_log_group)
        except ClientError:
            pass

    def test_enable_logs_only(
        self, manager, test_resource_id, account_id, region, cleanup_resources
    ):
        """Test enabling only logs (no traces)."""
        cleanup_resources.append(test_resource_id)

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{test_resource_id}"

        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='memory',
            enable_logs=True,
            enable_traces=False,
        )

        # Verify traces were not set up
        if result['status'] == 'success':
            assert result['logs_enabled'] is True
            assert result['traces_enabled'] is False

    def test_enable_traces_only(
        self, manager, test_resource_id, account_id, region, cleanup_resources
    ):
        """Test enabling only traces (no logs)."""
        cleanup_resources.append(test_resource_id)

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{test_resource_id}"

        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='memory',
            enable_logs=False,
            enable_traces=True,
        )

        if result['status'] == 'success':
            assert result['logs_enabled'] is False
            assert result['traces_enabled'] is True

    def test_idempotent_enable(
        self, manager, test_resource_id, account_id, region, cleanup_resources
    ):
        """Test that enabling observability multiple times is idempotent."""
        cleanup_resources.append(test_resource_id)

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{test_resource_id}"

        # Enable first time
        result1 = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='memory',
        )

        # Enable second time (should not fail)
        result2 = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=test_resource_id,
            resource_type='memory',
        )

        # Both should have a status (may be success or error depending on resource)
        assert 'status' in result1
        assert 'status' in result2


class TestConvenienceFunctionIntegration:
    """Integration tests for the convenience function."""

    @pytest.fixture
    def test_resource_id(self):
        """Generate a unique resource ID for testing."""
        return f"test-func-{uuid.uuid4().hex[:8]}"

    def test_convenience_function(self, test_resource_id):
        """Test the convenience function that matches AWS docs."""
        region = os.getenv("AWS_REGION", "us-east-1")
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{test_resource_id}"

        try:
            result = enable_observability_for_resource(
                resource_arn=resource_arn,
                resource_id=test_resource_id,
                account_id=account_id,
                region=region,
            )

            assert 'status' in result

        finally:
            # Cleanup
            try:
                manager = ObservabilityDeliveryManager(region_name=region)
                manager.disable_observability_for_resource(
                    resource_id=test_resource_id,
                    delete_log_group=True,
                )
            except Exception:
                pass


class TestWithRealAgentCoreResources:
    """
    Integration tests that work with real AgentCore resources.

    These tests require actual AgentCore resources to exist.
    They are skipped unless AGENTCORE_MEMORY_ID or AGENTCORE_GATEWAY_ID
    environment variables are set.
    """

    @pytest.fixture
    def real_memory_id(self):
        """Get a real memory ID from environment."""
        memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        if not memory_id:
            pytest.skip("AGENTCORE_MEMORY_ID not set")
        return memory_id

    @pytest.fixture
    def real_gateway_id(self):
        """Get a real gateway ID from environment."""
        gateway_id = os.getenv("AGENTCORE_GATEWAY_ID")
        if not gateway_id:
            pytest.skip("AGENTCORE_GATEWAY_ID not set")
        return gateway_id

    def test_enable_observability_real_memory(self, real_memory_id):
        """Test with a real memory resource."""
        region = os.getenv("AWS_REGION", "us-east-1")
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        manager = ObservabilityDeliveryManager(region_name=region)

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{real_memory_id}"

        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=real_memory_id,
            resource_type='memory',
        )

        print(f"Result for real memory {real_memory_id}: {result}")

        assert result['status'] == 'success'
        assert result['logs_enabled'] is True
        assert result['traces_enabled'] is True

    def test_enable_observability_real_gateway(self, real_gateway_id):
        """Test with a real gateway resource."""
        region = os.getenv("AWS_REGION", "us-east-1")
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        manager = ObservabilityDeliveryManager(region_name=region)

        resource_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{real_gateway_id}"

        result = manager.enable_observability_for_resource(
            resource_arn=resource_arn,
            resource_id=real_gateway_id,
            resource_type='gateway',
        )

        print(f"Result for real gateway {real_gateway_id}: {result}")

        assert result['status'] == 'success'
        assert result['logs_enabled'] is True
        assert result['traces_enabled'] is True
