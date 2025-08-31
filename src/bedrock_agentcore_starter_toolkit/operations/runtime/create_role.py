"""Creates an execution role to use in the Bedrock AgentCore Runtime module."""

import hashlib
import json
import logging
from typing import Optional

from boto3 import Session
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ...utils.runtime.policy_template import (
    render_execution_policy_template,
    render_trust_policy_template,
    validate_rendered_policy,
)


def _generate_deterministic_suffix(agent_name: str, length: int = 10) -> str:
    """Generate a deterministic suffix for role names based on agent name.

    Args:
        agent_name: Name of the agent
        length: Length of the suffix (default: 10)

    Returns:
        Deterministic alphanumeric string in lowercase
    """
    # Create deterministic hash from agent name
    hash_object = hashlib.sha256(agent_name.encode())
    hex_hash = hash_object.hexdigest()

    # Take first N characters for AWS resource names
    return hex_hash[:length].lower()


def get_or_create_runtime_execution_role(
    session: Session,
    logger: logging.Logger,
    region: str,
    account_id: str,
    agent_name: str,
    role_name: Optional[str] = None,
) -> str:
    """Get existing execution role or create a new one (idempotent).

    Args:
        session: Boto3 session
        logger: Logger instance
        region: AWS region
        account_id: AWS account ID
        agent_name: Agent name for resource scoping
        role_name: Optional custom role name

    Returns:
        Role ARN

    Raises:
        RuntimeError: If role creation fails
    """
    if not role_name:
        # Generate deterministic role name based on agent name
        # This ensures the same agent always gets the same role name
        deterministic_suffix = _generate_deterministic_suffix(agent_name)
        role_name = f"AmazonBedrockAgentCoreSDKRuntime-{region}-{deterministic_suffix}"

    logger.info("Getting or creating execution role for agent: %s", agent_name)
    logger.info("Using AWS region: %s, account ID: %s", region, account_id)
    logger.info("Role name: %s", role_name)

    iam = session.client("iam")

    try:
        # Step 1: Check if role already exists
        logger.debug("Checking if role exists: %s", role_name)
        role = iam.get_role(RoleName=role_name)
        existing_role_arn = role["Role"]["Arn"]

        logger.info("✅ Reusing existing execution role: %s", existing_role_arn)
        logger.debug("Role creation date: %s", role["Role"].get("CreateDate", "Unknown"))

        # TODO: In future, we could add validation here to ensure the role has correct policies
        # For now, we trust that if the role exists with our naming pattern, it's compatible

        return existing_role_arn

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            # Step 2: Role doesn't exist, create it
            logger.info("Role doesn't exist, creating new execution role: %s", role_name)

            # Inline role creation logic (previously in create_runtime_execution_role)
            logger.info("Starting execution role creation process for agent: %s", agent_name)
            logger.info("✓ Role creating: %s", role_name)

            try:
                # Render the trust policy template
                trust_policy_json = render_trust_policy_template(region, account_id)
                trust_policy = validate_rendered_policy(trust_policy_json)

                # Render the execution policy template
                execution_policy_json = render_execution_policy_template(region, account_id, agent_name)
                execution_policy = validate_rendered_policy(execution_policy_json)

                logger.info("Creating IAM role: %s", role_name)

                # Create the role with the trust policy
                role = iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description=f"Execution role for BedrockAgentCore Runtime - {agent_name}",
                )

                role_arn = role["Role"]["Arn"]
                logger.info("✓ Role created: %s", role_arn)

                # Create and attach the inline execution policy
                policy_name = f"BedrockAgentCoreRuntimeExecutionPolicy-{agent_name}"

                _attach_inline_policy(
                    iam_client=iam,
                    role_name=role_name,
                    policy_name=policy_name,
                    policy_document=json.dumps(execution_policy),
                    logger=logger,
                )

                logger.info("✓ Execution policy attached: %s", policy_name)
                logger.info("Role creation complete and ready for use with Bedrock AgentCore")

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


def _create_iam_role_with_policies(
    session: Session,
    logger: logging.Logger,
    role_name: str,
    trust_policy: dict,
    inline_policies: dict,  # {policy_name: policy_document}
    description: str,
) -> str:
    """Generic IAM role creation with inline policies.

    Args:
        session: Boto3 session
        logger: Logger instance
        role_name: Name for the IAM role
        trust_policy: Trust policy document (dict)
        inline_policies: Dictionary of {policy_name: policy_document}
        description: Role description

    Returns:
        Role ARN

    Raises:
        RuntimeError: If role creation fails
    """
    iam = session.client("iam")

    try:
        logger.info("Creating IAM role: %s", role_name)

        # Create the role with trust policy
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
        )

        role_arn = role["Role"]["Arn"]
        logger.info("✓ Role created: %s", role_arn)

        # Attach inline policies
        for policy_name, policy_document in inline_policies.items():
            logger.info("Attaching inline policy: %s to role: %s", policy_name, role_name)
            _attach_inline_policy(
                iam_client=iam,
                role_name=role_name,
                policy_name=policy_name,
                policy_document=json.dumps(policy_document) if isinstance(policy_document, dict) else policy_document,
                logger=logger,
            )
            logger.info("✓ Policy attached: %s", policy_name)

        return role_arn

    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            try:
                logger.info("Role %s already exists, retrieving existing role...", role_name)
                role = iam.get_role(RoleName=role_name)
                logger.info("✓ Role already exists: %s", role["Role"]["Arn"])

                # Update existing policies
                for policy_name, policy_document in inline_policies.items():
                    logger.info("Updating inline policy: %s on existing role: %s", policy_name, role_name)
                    _attach_inline_policy(
                        iam_client=iam,
                        role_name=role_name,
                        policy_name=policy_name,
                        policy_document=json.dumps(policy_document)
                        if isinstance(policy_document, dict)
                        else policy_document,
                        logger=logger,
                    )

                return role["Role"]["Arn"]
            except ClientError as get_error:
                logger.error("Error getting existing role: %s", get_error)
                raise RuntimeError(f"Failed to get existing role: {get_error}") from get_error
        else:
            logger.error("Error creating role: %s", e)
            if e.response["Error"]["Code"] == "AccessDenied":
                logger.error(
                    "Access denied. Ensure your AWS credentials have sufficient IAM permissions "
                    "to create roles and policies."
                )
            elif e.response["Error"]["Code"] == "LimitExceeded":
                logger.error(
                    "AWS limit exceeded. You may have reached the maximum number of IAM roles allowed in your account."
                )
            raise RuntimeError(f"Failed to create role: {e}") from e


def _attach_inline_policy(
    iam_client: BaseClient,
    role_name: str,
    policy_name: str,
    policy_document: str,
    logger: logging.Logger,
) -> None:
    """Attach an inline policy to an IAM role.

    Args:
        iam_client: IAM client instance
        role_name: Name of the role
        policy_name: Name of the policy
        policy_document: Policy document JSON string
        logger: Logger instance

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


def get_or_create_codebuild_execution_role(
    session: Session,
    logger: logging.Logger,
    region: str,
    account_id: str,
    agent_name: str,
    ecr_repository_arn: str,
    source_bucket_name: str,
) -> str:
    """Get existing CodeBuild execution role or create a new one (idempotent).

    Args:
        session: Boto3 session
        logger: Logger instance
        region: AWS region
        account_id: AWS account ID
        agent_name: Agent name for resource scoping
        ecr_repository_arn: ECR repository ARN for permissions
        source_bucket_name: S3 source bucket name for permissions

    Returns:
        Role ARN

    Raises:
        RuntimeError: If role creation fails
    """
    # Generate deterministic role name based on agent name
    deterministic_suffix = _generate_deterministic_suffix(agent_name)
    role_name = f"AmazonBedrockAgentCoreSDKCodeBuild-{region}-{deterministic_suffix}"

    logger.info("Getting or creating CodeBuild execution role for agent: %s", agent_name)
    logger.info("Role name: %s", role_name)

    iam = session.client("iam")

    try:
        # Step 1: Check if role already exists
        logger.debug("Checking if CodeBuild role exists: %s", role_name)
        role = iam.get_role(RoleName=role_name)
        existing_role_arn = role["Role"]["Arn"]

        logger.info("Reusing existing CodeBuild execution role: %s", existing_role_arn)
        return existing_role_arn

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            # Step 2: Role doesn't exist, create it
            logger.info("CodeBuild role doesn't exist, creating new role: %s", role_name)

            # Define trust policy for CodeBuild service
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "codebuild.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                        "Condition": {"StringEquals": {"aws:SourceAccount": account_id}},
                    }
                ],
            }

            # Define permissions policy for CodeBuild operations
            permissions_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"},
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:PutImage",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload",
                        ],
                        "Resource": ecr_repository_arn,
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                        "Resource": f"arn:aws:logs:{region}:{account_id}:log-group:/aws/codebuild/bedrock-agentcore-*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject"],
                        "Resource": f"arn:aws:s3:::{source_bucket_name}/*",
                    },
                ],
            }

            # Create role using shared logic
            role_arn = _create_iam_role_with_policies(
                session=session,
                logger=logger,
                role_name=role_name,
                trust_policy=trust_policy,
                inline_policies={"CodeBuildExecutionPolicy": permissions_policy},
                description="CodeBuild execution role for Bedrock AgentCore ARM64 builds",
            )

            # Wait for IAM propagation to prevent CodeBuild authorization errors
            logger.info("Waiting for IAM role propagation...")
            import time

            time.sleep(10)

            logger.info("CodeBuild execution role creation complete: %s", role_arn)
            return role_arn
        else:
            logger.error("Error checking CodeBuild role existence: %s", e)
            raise RuntimeError(f"Failed to check CodeBuild role existence: {e}") from e
