"""X-Ray Transaction Search service for enabling observability."""

import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _need_resource_policy(logs_client, policy_name="TransactionSearchXRayAccess"):
    """Check if resource policy needs to be created (fail-safe)."""
    try:
        response = logs_client.describe_resource_policies()
        for policy in response.get("resourcePolicies", []):
            if policy.get("policyName") == policy_name:
                return False  # Already exists
        return True  # Needs creation
    except Exception:
        return True  # If check fails, assume we need it (safe)


def _need_trace_destination(xray_client):
    """Check if trace destination needs to be set (fail-safe)."""
    try:
        response = xray_client.get_trace_segment_destination()
        return response.get("Destination") != "CloudWatchLogs"
    except Exception:
        return True  # If check fails, assume we need it (safe)


def _need_indexing_rule(xray_client):
    """Check if indexing rule needs to be configured (fail-safe)."""
    try:
        response = xray_client.get_indexing_rules()
        for rule in response.get("IndexingRules", []):
            if rule.get("Name") == "Default":
                return False  # Already configured
        return True  # Needs configuration
    except Exception:
        return True  # If check fails, assume we need it (safe)


def enable_transaction_search_if_needed(region: str, account_id: str) -> bool:
    """Enable X-Ray Transaction Search components that are not already configured.

    This function checks what's already configured and only runs needed steps.
    It's fail-safe - if checks fail, it assumes configuration is needed.

    Args:
        region: AWS region
        account_id: AWS account ID

    Returns:
        bool: True if Transaction Search was configured successfully, False if failed
    """
    try:
        session = boto3.Session(region_name=region)
        logs_client = session.client("logs")
        xray_client = session.client("xray")

        steps_run = []

        # Step 1: Resource policy (only if needed)
        if _need_resource_policy(logs_client):
            _create_cloudwatch_logs_resource_policy(logs_client, account_id, region)
            steps_run.append("resource_policy")
        else:
            logger.info("CloudWatch Logs resource policy already configured")

        # Step 2: Trace destination (only if needed)
        if _need_trace_destination(xray_client):
            _configure_trace_segment_destination(xray_client)
            steps_run.append("trace_destination")
        else:
            logger.info("X-Ray trace destination already configured")

        # Step 3: Indexing rule (only if needed)
        if _need_indexing_rule(xray_client):
            _configure_indexing_rule(xray_client)
            steps_run.append("indexing_rule")
        else:
            logger.info("X-Ray indexing rule already configured")

        if steps_run:
            logger.info("Transaction Search configured: %s", ", ".join(steps_run))
        else:
            logger.info("Transaction Search already fully configured")

        return True

    except Exception as e:
        logger.warning("Transaction Search configuration failed: %s", str(e))
        logger.info("Agent launch will continue without Transaction Search")
        return False  # Don't fail launch


def _create_cloudwatch_logs_resource_policy(logs_client, account_id: str, region: str) -> None:
    """Create CloudWatch Logs resource policy for X-Ray access (idempotent)."""
    policy_name = "TransactionSearchXRayAccess"

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "TransactionSearchXRayAccess",
                "Effect": "Allow",
                "Principal": {"Service": "xray.amazonaws.com"},
                "Action": "logs:PutLogEvents",
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:aws/spans:*",
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/application-signals/data:*",
                ],
                "Condition": {
                    "ArnLike": {"aws:SourceArn": f"arn:aws:xray:{region}:{account_id}:*"},
                    "StringEquals": {"aws:SourceAccount": account_id},
                },
            }
        ],
    }

    try:
        logs_client.put_resource_policy(policyName=policy_name, policyDocument=json.dumps(policy_document))
        logger.info("Created/updated CloudWatch Logs resource policy")
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidParameterException":
            # Policy might already exist with same content
            logger.info("CloudWatch Logs resource policy already configured")
        else:
            raise


def _configure_trace_segment_destination(xray_client) -> None:
    """Configure X-Ray trace segment destination to CloudWatch Logs (idempotent)."""
    try:
        # Configure trace segments to be sent to CloudWatch Logs
        # This enables Transaction Search functionality
        xray_client.update_trace_segment_destination(Destination="CloudWatchLogs")
        logger.info("Configured X-Ray trace segment destination to CloudWatch Logs")
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidRequestException":
            # Destination might already be configured
            logger.info("X-Ray trace segment destination already configured")
        else:
            raise


def _configure_indexing_rule(xray_client) -> None:
    """Configure X-Ray indexing rule for transaction search (idempotent)."""
    try:
        # Update the default indexing rule with probabilistic sampling
        # This is idempotent - it will update the existing rule
        xray_client.update_indexing_rule(Name="Default", Rule={"Probabilistic": {"DesiredSamplingPercentage": 1}})
        logger.info("Updated X-Ray indexing rule for Transaction Search")
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidRequestException":
            # Rule might already be configured
            logger.info("X-Ray indexing rule already configured")
        else:
            raise
