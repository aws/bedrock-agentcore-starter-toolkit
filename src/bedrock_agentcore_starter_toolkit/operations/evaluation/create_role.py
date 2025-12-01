"""Creates an execution role for Bedrock AgentCore Evaluation operations."""

import hashlib
import json
import logging
import time
from typing import Optional

from boto3 import Session
from botocore.client import BaseClient
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _generate_deterministic_suffix(config_name: str, length: int = 10) -> str:
    """Generate a deterministic suffix for role names based on config name.

    Args:
        config_name: Name of the evaluation config
        length: Length of the suffix (default: 10)

    Returns:
        Deterministic alphanumeric string in lowercase
    """
    # Create deterministic hash from config name
    hash_object = hashlib.sha256(config_name.encode())
    hex_hash = hash_object.hexdigest()

    # Take first N characters for AWS resource names
    return hex_hash[:length].lower()


def get_or_create_evaluation_execution_role(
    session: Session,
    region: str,
    account_id: str,
    config_name: str,
    role_name: Optional[str] = None,
) -> str:
    """Get existing evaluation execution role or create a new one (idempotent).

    Args:
        session: Boto3 session
        region: AWS region
        account_id: AWS account ID
        config_name: Evaluation config name for resource scoping
        role_name: Optional custom role name

    Returns:
        Role ARN

    Raises:
        RuntimeError: If role creation fails
    """
    if not role_name:
        # Generate deterministic role name based on config name
        deterministic_suffix = _generate_deterministic_suffix(config_name)
        role_name = f"AgentCoreEvalsSDK-{region}-{deterministic_suffix}"

    logger.info("Getting or creating evaluation execution role for config: %s", config_name)
    logger.info("Using AWS region: %s, account ID: %s", region, account_id)
    logger.info("Role name: %s", role_name)

    iam = session.client("iam")

    try:
        # Step 1: Check if role already exists
        logger.debug("Checking if role exists: %s", role_name)
        role = iam.get_role(RoleName=role_name)
        existing_role_arn = role["Role"]["Arn"]

        logger.info("✅ Reusing existing evaluation execution role: %s", existing_role_arn)
        logger.debug("Role creation date: %s", role["Role"].get("CreateDate", "Unknown"))

        return existing_role_arn

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            # Step 2: Role doesn't exist, create it
            logger.info("Role doesn't exist, creating new evaluation execution role: %s", role_name)

            # Define trust policy for AgentCore Evaluation service
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "TrustPolicyStatement",
                        "Effect": "Allow",
                        "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": account_id,
                                "aws:ResourceAccount": account_id,
                            },
                            "ArnLike": {
                                "aws:SourceArn": [
                                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:evaluator/*",
                                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:online-evaluation-config/*",
                                ]
                            },
                        },
                    }
                ],
            }

            # Define permissions policy for evaluation operations
            permissions_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "CloudWatchLogReadStatement",
                        "Effect": "Allow",
                        "Action": [
                            "logs:DescribeLogGroups",
                            "logs:DescribeLogStreams",
                            "logs:GetQueryResults",
                            "logs:StartQuery",
                            "cloudwatch:GenerateQuery",
                            "cloudwatch:GenerateQueryResultsSummary",
                        ],
                        "Resource": "*",
                    },
                    {
                        "Sid": "CloudWatchLogWriteStatement",
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:GetLogEvents",
                        ],
                        "Resource": (
                            f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/evaluations/*"
                        ),
                    },
                    {
                        "Sid": "CloudWatchIndexPolicyStatement",
                        "Effect": "Allow",
                        "Action": ["logs:DescribeIndexPolicies", "logs:PutIndexPolicy"],
                        "Resource": [
                            f"arn:aws:logs:{region}:{account_id}:log-group:aws/spans",
                            f"arn:aws:logs:{region}:{account_id}:log-group:aws/spans:*",
                        ],
                    },
                    {
                        "Sid": "BedrockInvokeStatement",
                        "Effect": "Allow",
                        "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                        "Resource": "*",
                    },
                ],
            }

            try:
                logger.info("Creating IAM role: %s", role_name)

                # Create the role with trust policy
                role = iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description=f"Execution role for BedrockAgentCore Evaluation - {config_name}",
                )

                role_arn = role["Role"]["Arn"]
                logger.info("✓ Role created: %s", role_arn)

                # Create and attach the inline execution policy
                policy_name = f"AgentCoreEvaluationPolicy-{region}-{_generate_deterministic_suffix(config_name)}"

                _attach_inline_policy(
                    iam_client=iam,
                    role_name=role_name,
                    policy_name=policy_name,
                    policy_document=json.dumps(permissions_policy),
                )

                logger.info("✓ Execution policy attached: %s", policy_name)

                # Wait for IAM propagation
                logger.info("Waiting for IAM role propagation...")
                time.sleep(10)

                logger.info("Role creation complete and ready for use with Bedrock AgentCore Evaluation")

                return role_arn

            except ClientError as create_error:
                if create_error.response["Error"]["Code"] == "EntityAlreadyExists":
                    try:
                        logger.info("Role %s already exists, retrieving existing role...", role_name)
                        role = iam.get_role(RoleName=role_name)
                        logger.info("✓ Role already exists: %s", role["Role"]["Arn"])
                        return role["Role"]["Arn"]
                    except ClientError as get_error:
                        logger.error("Error getting existing role: %s", get_error)
                        raise RuntimeError(f"Failed to get existing role: {get_error}") from get_error
                else:
                    logger.error("Error creating role: %s", create_error)
                    if create_error.response["Error"]["Code"] == "AccessDenied":
                        logger.error(
                            "Access denied. Ensure your AWS credentials have sufficient IAM permissions "
                            "to create roles and policies."
                        )
                    elif create_error.response["Error"]["Code"] == "LimitExceeded":
                        logger.error(
                            "AWS limit exceeded. You may have reached the maximum number of IAM roles "
                            "allowed in your account."
                        )
                    raise RuntimeError(f"Failed to create role: {create_error}") from create_error
        else:
            logger.error("Error checking role existence: %s", e)
            raise RuntimeError(f"Failed to check role existence: {e}") from e


def _attach_inline_policy(
    iam_client: BaseClient,
    role_name: str,
    policy_name: str,
    policy_document: str,
) -> None:
    """Attach an inline policy to an IAM role.

    Args:
        iam_client: IAM client instance
        role_name: Name of the role
        policy_name: Name of the policy
        policy_document: Policy document JSON string

    Raises:
        RuntimeError: If policy attachment fails
    """
    try:
        logger.debug("Attaching inline policy %s to role %s", policy_name, role_name)
        logger.debug("Policy document size: %d bytes", len(policy_document))

        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document,
        )

        logger.debug("Successfully attached policy %s to role %s", policy_name, role_name)
    except ClientError as e:
        logger.error("Error attaching policy %s to role %s: %s", policy_name, role_name, e)
        if e.response["Error"]["Code"] == "MalformedPolicyDocument":
            logger.error("Policy document is malformed. Check the JSON syntax.")
        elif e.response["Error"]["Code"] == "LimitExceeded":
            logger.error("Policy size limit exceeded or too many policies attached to the role.")
        raise RuntimeError(f"Failed to attach policy {policy_name}: {e}") from e
