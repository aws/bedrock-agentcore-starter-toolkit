"""CloudWatch delivery configuration for AgentCore resource observability.

This module enables service-provided logs and traces for AgentCore resources
(Memory, Gateway, Runtime, Built-in Tools) by configuring CloudWatch delivery
sources and destinations.

IMPORTANT DISTINCTION:
- ADOT Instrumentation (existing in Runtime): Captures spans from YOUR agent code
- CloudWatch Delivery (this module): Enables AWS SERVICE-PROVIDED logs & traces

Both are needed for complete observability.

Resource-specific notes:
- Runtime: AWS auto-creates log groups, but TRACES delivery must be enabled via this module
- Memory: Both logs AND traces delivery must be enabled via this module
- Gateway: Both logs AND traces delivery must be enabled via this module

Reference: AWS Documentation - "Configure CloudWatch resources using an AWS SDK"
"""

import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ObservabilityDeliveryManager:
    """Manages CloudWatch delivery configuration for AgentCore resources.

    This class configures CloudWatch to receive service-provided logs and traces
    from AgentCore resources like Memory, Gateway, Runtime, and Built-in Tools.

    This is SEPARATE from ADOT instrumentation which captures agent code telemetry.
    This enables the AWS service itself to emit logs and traces.

    Usage:
        manager = ObservabilityDeliveryManager(region_name='us-east-1')

        # Enable observability for a memory resource (logs + traces)
        result = manager.enable_observability_for_resource(
            resource_arn='arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/my-memory-id',
            resource_id='my-memory-id',
            resource_type='memory'
        )

        # Enable only traces for runtime (logs auto-created by AWS)
        result = manager.enable_traces_for_runtime(
            runtime_arn='arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/my-agent-id',
            runtime_id='my-agent-id'
        )

    Reference:
        AWS Documentation: "Enabling observability for AgentCore runtime, memory,
        gateway, built-in tools, and identity resources"
    """

    # Supported resource types and their log group patterns
    SUPPORTED_RESOURCE_TYPES = {"memory", "gateway", "runtime"}

    # Resource types where AWS auto-creates log groups
    AUTO_LOG_RESOURCE_TYPES = {"runtime"}

    def __init__(
        self,
        region_name: Optional[str] = None,
        boto3_session: Optional[boto3.Session] = None,
    ):
        """Initialize the ObservabilityDeliveryManager.

        Args:
            region_name: AWS region name. If not provided, uses session default.
            boto3_session: Optional boto3 Session. Creates new one if not provided.
        """
        self._session = boto3_session or boto3.Session()
        self.region = region_name or self._session.region_name

        if not self.region:
            raise ValueError(
                "AWS region must be specified either via region_name parameter "
                "or configured in boto3 session/environment"
            )

        self._logs_client = self._session.client("logs", region_name=self.region)

        # Get account ID for ARN construction
        sts_client = self._session.client("sts", region_name=self.region)
        self._account_id = sts_client.get_caller_identity()["Account"]

        logger.info(
            "ObservabilityDeliveryManager initialized for region: %s, account: %s", self.region, self._account_id
        )

    @property
    def account_id(self) -> str:
        """Get the AWS account ID."""
        return self._account_id

    def enable_observability_for_resource(
        self,
        resource_arn: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        enable_logs: bool = True,
        enable_traces: bool = True,
        custom_log_group: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enable CloudWatch observability for an AgentCore resource.

        This configures CloudWatch delivery sources and destinations to capture
        service-provided logs and traces for the specified resource.

        Args:
            resource_arn: Full ARN of the AgentCore resource
                Example: 'arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/my-memory-id'
            resource_id: Optional Resource identifier (e.g., memory ID, gateway ID)
            resource_type: Optional Type of resource - one of:
                'memory', 'gateway', 'runtime', 'tools', 'identity'
            enable_logs: Whether to enable APPLICATION_LOGS delivery (default: True)
                Note: For 'runtime', logs are auto-created by AWS, so this creates
                the delivery configuration but log group already exists.
            enable_traces: Whether to enable TRACES delivery to X-Ray (default: True)
            custom_log_group: Optional custom log group name. If not provided,
                uses default pattern: /aws/vendedlogs/bedrock-agentcore/{resource_type}/APPLICATION_LOGS/{resource_id}

        Returns:
            Dict containing:
                - resource_id: The resource identifier
                - resource_type: The resource type
                - status: 'success' or 'error'
                - logs_enabled: Whether logs delivery was enabled
                - traces_enabled: Whether traces delivery was enabled
                - log_group: The log group name used
                - deliveries: Dict with delivery details (logs and/or traces)
                - error: Error message if status is 'error'

        Raises:
            ValueError: If resource_type is not supported
        """
        # Parse resource_type and resource_id from ARN if not provided
        # ARN format: arn:aws:bedrock-agentcore:{region}:{account}:{resource_type}/{resource_id}
        if resource_type is None or resource_id is None:
            try:
                resource_part = resource_arn.split(":")[-1]
                parsed_type, parsed_id = resource_part.split("/", 1)
                resource_type = resource_type or parsed_type
                resource_id = resource_id or parsed_id
            except (IndexError, ValueError) as e:
                raise ValueError(
                    f"Could not parse resource_type/resource_id from ARN: {resource_arn}. "
                    f"Please provide them explicitly. Error: {e}"
                ) from e

        # Validate resource type
        if resource_type not in self.SUPPORTED_RESOURCE_TYPES:
            raise ValueError(
                f"Unsupported resource_type: '{resource_type}'. Must be one of: {self.SUPPORTED_RESOURCE_TYPES}"
            )

        results: Dict[str, Any] = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "resource_arn": resource_arn,
            "logs_enabled": False,
            "traces_enabled": False,
            "log_group": None,
            "deliveries": {},
        }

        # Determine log group name per AWS documentation pattern
        if custom_log_group:
            log_group_name = custom_log_group
        elif resource_type == "runtime":
            # Runtime has different log group pattern
            log_group_name = f"/aws/bedrock-agentcore/runtimes/{resource_id}"
        else:
            # Default pattern from AWS docs:
            # /aws/vendedlogs/bedrock-agentcore/{resource-type}/APPLICATION_LOGS/{resource-id}
            log_group_name = f"/aws/vendedlogs/bedrock-agentcore/{resource_type}/APPLICATION_LOGS/{resource_id}"

        log_group_arn = f"arn:aws:logs:{self.region}:{self._account_id}:log-group:{log_group_name}"
        results["log_group"] = log_group_name

        try:
            # Step 0: Create log group for vended log delivery (skip for runtime - AWS creates it)
            if resource_type not in self.AUTO_LOG_RESOURCE_TYPES:
                self._create_log_group_if_not_exists(log_group_name)

            # Step 1: Enable logs delivery (optional for runtime since AWS handles it)
            if enable_logs and resource_type not in self.AUTO_LOG_RESOURCE_TYPES:
                logs_delivery = self._setup_logs_delivery(
                    resource_arn=resource_arn,
                    resource_id=resource_id,
                    log_group_arn=log_group_arn,
                )
                results["logs_enabled"] = True
                results["deliveries"]["logs"] = logs_delivery
                logger.info("✅ Logs delivery enabled for %s/%s", resource_type, resource_id)
            elif resource_type in self.AUTO_LOG_RESOURCE_TYPES:
                results["logs_enabled"] = True  # AWS auto-creates
                results["deliveries"]["logs"] = {"status": "auto-created by AWS"}
                logger.info("✅ Logs auto-created by AWS for %s/%s", resource_type, resource_id)

            # Step 2: Enable traces delivery
            if enable_traces:
                traces_delivery = self._setup_traces_delivery(
                    resource_arn=resource_arn,
                    resource_id=resource_id,
                )
                results["traces_enabled"] = True
                results["deliveries"]["traces"] = traces_delivery
                logger.info("✅ Traces delivery enabled for %s/%s", resource_type, resource_id)

            results["status"] = "success"
            logger.info(
                "Observability enabled for %s/%s - logs: %s, traces: %s",
                resource_type,
                resource_id,
                results["logs_enabled"],
                results["traces_enabled"],
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            logger.error(
                "Failed to enable observability for %s/%s: %s - %s", resource_type, resource_id, error_code, error_msg
            )
            results["status"] = "error"
            results["error"] = f"{error_code}: {error_msg}"

        except Exception as e:
            logger.error("Unexpected error enabling observability for %s/%s: %s", resource_type, resource_id, str(e))
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def enable_traces_for_runtime(
        self,
        runtime_arn: str,
        runtime_id: str,
    ) -> Dict[str, Any]:
        """Enable TRACES delivery for a Runtime resource.

        This is a convenience method for Runtime resources where:
        - Logs are auto-created by AWS (no action needed)
        - Traces must be explicitly enabled via CloudWatch delivery

        Args:
            runtime_arn: Full ARN of the Runtime resource
            runtime_id: Runtime/Agent identifier

        Returns:
            Dict with traces delivery configuration results
        """
        return self.enable_observability_for_resource(
            resource_arn=runtime_arn,
            resource_id=runtime_id,
            resource_type="runtime",
            enable_logs=False,  # AWS auto-creates
            enable_traces=True,
        )

    def _create_log_group_if_not_exists(self, log_group_name: str) -> None:
        """Create log group if it doesn't already exist.

        Args:
            log_group_name: Name of the log group to create
        """
        try:
            self._logs_client.create_log_group(logGroupName=log_group_name)
            logger.info("Created log group: %s", log_group_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.debug("Log group already exists: %s", log_group_name)
            else:
                raise

    def _setup_logs_delivery(
        self,
        resource_arn: str,
        resource_id: str,
        log_group_arn: str,
    ) -> Dict[str, str]:
        """Set up APPLICATION_LOGS delivery to CloudWatch Logs.

        This creates:
        1. A delivery source for logs from the resource
        2. A delivery destination pointing to CloudWatch Logs
        3. A delivery connecting source to destination

        Args:
            resource_arn: ARN of the AgentCore resource
            resource_id: Resource identifier
            log_group_arn: ARN of the destination log group

        Returns:
            Dict with delivery_id, source_name, destination_name
        """
        source_name = f"{resource_id}-logs-source"
        dest_name = f"{resource_id}-logs-destination"

        # Step 1: Create delivery source for logs
        try:
            logs_source = self._logs_client.put_delivery_source(
                name=source_name, logType="APPLICATION_LOGS", resourceArn=resource_arn
            )
            logger.debug("Created logs delivery source: %s", source_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.debug("Logs delivery source already exists: %s", source_name)
                logs_source = {"deliverySource": {"name": source_name}}
            else:
                raise

        # Step 2: Create delivery destination (CloudWatch Logs)
        try:
            logs_dest = self._logs_client.put_delivery_destination(
                name=dest_name,
                deliveryDestinationType="CWL",
                deliveryDestinationConfiguration={
                    "destinationResourceArn": log_group_arn,
                },
            )
            dest_arn = logs_dest["deliveryDestination"]["arn"]
            logger.debug("Created logs delivery destination: %s", dest_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.debug("Logs delivery destination already exists: %s", dest_name)
                # Construct the ARN for existing destination
                dest_arn = f"arn:aws:logs:{self.region}:{self._account_id}:delivery-destination:{dest_name}"
            else:
                raise

        # Step 3: Create delivery (connect source to destination)
        try:
            delivery = self._logs_client.create_delivery(
                deliverySourceName=logs_source["deliverySource"]["name"], deliveryDestinationArn=dest_arn
            )
            delivery_id = delivery.get("id", "created")
            logger.debug("Created logs delivery: %s", delivery_id)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConflictException":
                logger.debug("Logs delivery already exists for source: %s", source_name)
                delivery_id = "existing"
            else:
                raise

        return {
            "delivery_id": delivery_id,
            "source_name": source_name,
            "destination_name": dest_name,
            "log_group_arn": log_group_arn,
        }

    def _setup_traces_delivery(
        self,
        resource_arn: str,
        resource_id: str,
    ) -> Dict[str, str]:
        """Set up TRACES delivery to X-Ray.

        This creates:
        1. A delivery source for traces from the resource
        2. A delivery destination pointing to X-Ray
        3. A delivery connecting source to destination

        Args:
            resource_arn: ARN of the AgentCore resource
            resource_id: Resource identifier

        Returns:
            Dict with delivery_id, source_name, destination_name
        """
        source_name = f"{resource_id}-traces-source"
        dest_name = f"{resource_id}-traces-destination"

        # Step 1: Create delivery source for traces
        try:
            traces_source = self._logs_client.put_delivery_source(
                name=source_name, logType="TRACES", resourceArn=resource_arn
            )
            logger.debug("Created traces delivery source: %s", source_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.debug("Traces delivery source already exists: %s", source_name)
                traces_source = {"deliverySource": {"name": source_name}}
            else:
                raise

        # Step 2: Create delivery destination (X-Ray)
        try:
            traces_dest = self._logs_client.put_delivery_destination(name=dest_name, deliveryDestinationType="XRAY")
            dest_arn = traces_dest["deliveryDestination"]["arn"]
            logger.debug("Created traces delivery destination: %s", dest_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.debug("Traces delivery destination already exists: %s", dest_name)
                dest_arn = f"arn:aws:logs:{self.region}:{self._account_id}:delivery-destination:{dest_name}"
            else:
                raise

        # Step 3: Create delivery
        try:
            delivery = self._logs_client.create_delivery(
                deliverySourceName=traces_source["deliverySource"]["name"], deliveryDestinationArn=dest_arn
            )
            delivery_id = delivery.get("id", "created")
            logger.debug("Created traces delivery: %s", delivery_id)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConflictException":
                logger.debug("Traces delivery already exists for source: %s", source_name)
                delivery_id = "existing"
            else:
                raise

        return {
            "delivery_id": delivery_id,
            "source_name": source_name,
            "destination_name": dest_name,
        }

    def disable_observability_for_resource(
        self,
        resource_id: str,
        delete_log_group: bool = False,
    ) -> Dict[str, Any]:
        """Disable CloudWatch observability for a resource.

        This removes the delivery sources, destinations, and deliveries.
        Optionally removes the log group (existing logs are preserved unless
        the log group is deleted).

        Args:
            resource_id: Resource identifier
            delete_log_group: Whether to also delete the log group (default: False)

        Returns:
            Dict with status and list of deleted resources
        """
        results: Dict[str, Any] = {
            "resource_id": resource_id,
            "deleted": [],
            "errors": [],
        }

        # Delete delivery sources and destinations for both logs and traces
        for suffix in ["logs", "traces"]:
            source_name = f"{resource_id}-{suffix}-source"
            dest_name = f"{resource_id}-{suffix}-destination"

            # Delete delivery source (this implicitly deletes the delivery)
            try:
                self._logs_client.delete_delivery_source(name=source_name)
                results["deleted"].append(f"source:{source_name}")
                logger.debug("Deleted delivery source: %s", source_name)
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceNotFoundException":
                    results["errors"].append(f"Failed to delete {source_name}: {e}")
                    logger.warning("Failed to delete delivery source %s: %s", source_name, e)

            # Delete delivery destination
            try:
                self._logs_client.delete_delivery_destination(name=dest_name)
                results["deleted"].append(f"destination:{dest_name}")
                logger.debug("Deleted delivery destination: %s", dest_name)
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceNotFoundException":
                    results["errors"].append(f"Failed to delete {dest_name}: {e}")
                    logger.warning("Failed to delete delivery destination %s: %s", dest_name, e)

        # Optionally delete log group
        if delete_log_group:
            for resource_type in self.SUPPORTED_RESOURCE_TYPES:
                if resource_type == "runtime":
                    log_group_name = f"/aws/bedrock-agentcore/runtimes/{resource_id}"
                else:
                    log_group_name = f"/aws/vendedlogs/bedrock-agentcore/{resource_type}/APPLICATION_LOGS/{resource_id}"
                try:
                    self._logs_client.delete_log_group(logGroupName=log_group_name)
                    results["deleted"].append(f"log_group:{log_group_name}")
                    logger.debug("Deleted log group: %s", log_group_name)
                except ClientError as e:
                    if e.response["Error"]["Code"] != "ResourceNotFoundException":
                        results["errors"].append(f"Failed to delete log group {log_group_name}: {e}")

        results["status"] = "success" if not results["errors"] else "partial"
        return results

    def get_observability_status(
        self,
        resource_id: str,
    ) -> Dict[str, Any]:
        """Check the observability configuration status for a resource.

        Args:
            resource_id: Resource identifier

        Returns:
            Dict with status information for logs and traces delivery
        """
        status: Dict[str, Any] = {
            "resource_id": resource_id,
            "logs": {"configured": False},
            "traces": {"configured": False},
        }

        # Check logs delivery source
        logs_source_name = f"{resource_id}-logs-source"
        try:
            self._logs_client.get_delivery_source(name=logs_source_name)
            status["logs"]["configured"] = True
            status["logs"]["source_name"] = logs_source_name
        except ClientError:
            pass

        # Check traces delivery source
        traces_source_name = f"{resource_id}-traces-source"
        try:
            self._logs_client.get_delivery_source(name=traces_source_name)
            status["traces"]["configured"] = True
            status["traces"]["source_name"] = traces_source_name
        except ClientError:
            pass

        return status

    def enable_for_memory(
        self,
        memory_id: str,
        memory_arn: Optional[str] = None,
        enable_logs: bool = True,
        enable_traces: bool = True,
    ) -> Dict[str, Any]:
        """Enable observability for a memory resource.

        Convenience method that handles ARN construction if not provided.
        """
        if not memory_arn:
            memory_arn = f"arn:aws:bedrock-agentcore:{self.region}:{self._account_id}:memory/{memory_id}"

        return self.enable_observability_for_resource(
            resource_arn=memory_arn,
            resource_id=memory_id,
            resource_type="memory",
            enable_logs=enable_logs,
            enable_traces=enable_traces,
        )

    def enable_for_gateway(
        self,
        gateway_id: str,
        gateway_arn: Optional[str] = None,
        enable_logs: bool = True,
        enable_traces: bool = True,
    ) -> Dict[str, Any]:
        """Enable observability for a gateway resource.

        Convenience method that handles ARN construction if not provided.
        """
        if not gateway_arn:
            gateway_arn = f"arn:aws:bedrock-agentcore:{self.region}:{self._account_id}:gateway/{gateway_id}"

        return self.enable_observability_for_resource(
            resource_arn=gateway_arn,
            resource_id=gateway_id,
            resource_type="gateway",
            enable_logs=enable_logs,
            enable_traces=enable_traces,
        )

    def disable_for_memory(
        self,
        memory_id: str,
        delete_log_group: bool = False,
    ) -> Dict[str, Any]:
        """Disable observability for a memory resource."""
        return self.disable_observability_for_resource(
            resource_id=memory_id,
            delete_log_group=delete_log_group,
        )

    def disable_for_gateway(
        self,
        gateway_id: str,
        delete_log_group: bool = False,
    ) -> Dict[str, Any]:
        """Disable observability for a gateway resource."""
        return self.disable_observability_for_resource(
            resource_id=gateway_id,
            delete_log_group=delete_log_group,
        )


# Convenience function matching AWS documentation example signature
def enable_observability_for_resource(
    resource_arn: str,
    resource_id: str,
    account_id: str,
    region: str = "us-east-1",
    enable_logs: bool = True,
    enable_traces: bool = True,
) -> Dict[str, Any]:
    """Enable observability for a Bedrock AgentCore resource.

    This is a convenience function that matches the signature from AWS documentation.
    For more control, use ObservabilityDeliveryManager class directly.

    Args:
        resource_arn: Full ARN of the resource
        resource_id: Resource identifier
        account_id: AWS account ID (used for validation)
        region: AWS region (default: us-east-1)
        enable_logs: Whether to enable logs delivery
        enable_traces: Whether to enable traces delivery

    Returns:
        Dict with delivery configuration results

    Example:
        # From AWS documentation
        resource_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/my-memory-id"
        resource_id = "my-memory-id"
        account_id = "123456789012"

        delivery_ids = enable_observability_for_resource(resource_arn, resource_id, account_id)
    """
    # Determine resource type from ARN
    # ARN format: arn:aws:bedrock-agentcore:{region}:{account}:{resource_type}/{resource_id}
    try:
        arn_parts = resource_arn.split(":")
        resource_part = arn_parts[-1]  # e.g., "memory/my-memory-id" or "runtime/my-agent-id"
        resource_type = resource_part.split("/")[0]
    except (IndexError, ValueError):
        resource_type = "memory"  # Default fallback

    manager = ObservabilityDeliveryManager(region_name=region)

    # Validate account_id matches
    if manager.account_id != account_id:
        logger.warning("Provided account_id (%s) differs from session account (%s)", account_id, manager.account_id)

    result = manager.enable_observability_for_resource(
        resource_arn=resource_arn,
        resource_id=resource_id,
        resource_type=resource_type,
        enable_logs=enable_logs,
        enable_traces=enable_traces,
    )

    # Return in format compatible with AWS documentation example
    if result["status"] == "success":
        return {
            "logs_delivery_id": result["deliveries"].get("logs", {}).get("delivery_id"),
            "traces_delivery_id": result["deliveries"].get("traces", {}).get("delivery_id"),
            "log_group": result["log_group"],
            "status": "success",
        }
    else:
        return {
            "status": "error",
            "error": result.get("error"),
        }
