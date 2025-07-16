"""Creates an execution role to use in the Bedrock AgentCore Gateway module."""

import json
import logging
from typing import Optional

from boto3 import Session
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ...operations.gateway.constants import (
    BEDROCK_AGENTCORE_TRUST_POLICY,
    POLICIES,
    POLICIES_TO_CREATE,
)


def create_gateway_execution_role(
    session: Session, logger: logging.Logger, role_name: str = "AgentCoreGatewayExecutionRole"
) -> str:
    """Create the Gateway execution role.

    :param logger: the logger to use.
    :return: the role ARN.
    """
    iam = session.client("iam")
    # Create the role
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(BEDROCK_AGENTCORE_TRUST_POLICY),
            Description="Execution role for AgentCore Gateway",
        )
        for policy_name, policy in POLICIES_TO_CREATE:
            _attach_policy(
                iam_client=iam,
                role_name=role_name,
                policy_name=policy_name,
                policy_document=json.dumps(policy),
            )
        for policy_arn in POLICIES:
            _attach_policy(iam_client=iam, role_name=role_name, policy_arn=policy_arn)

        return role["Role"]["Arn"]

    except iam.exceptions.EntityAlreadyExistsException:
        try:
            role = iam.get_role(RoleName=role_name)
            logger.info("✓ Role already exists: %s", role["Role"]["Arn"])
            return role["Role"]["Arn"]
        except ClientError as e:
            logger.error("Error getting existing role: %s", e)
            raise
    except ClientError as e:
        logger.error("Error creating role: %s", e)
        raise


def _attach_policy(
    iam_client: BaseClient,
    role_name: str,
    policy_arn: Optional[str] = None,
    policy_document: Optional[str] = None,
    policy_name: Optional[str] = None,
) -> None:
    """Attach a policy to an IAM role.

    :param iam_client: the IAM client to use.
    :param role_name: name of the role.
    :param policy_arn: the arn of the policy to attach.
    :param policy_document: the policy document (if not using a policy_arn).
    :param policy_name: the policy name (if not using a policy_arn).
    :return:
    """
    if policy_arn and policy_document:
        raise Exception("Cannot specify both policy arn and policy document.")
    try:
        if policy_arn:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        elif policy_document and policy_name:
            policy = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=policy_document,
            )
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy["Policy"]["Arn"])
        else:
            raise Exception("Must specify both policy document and policy name or just a policy arn")
    except ClientError as e:
        raise RuntimeError(f"Failed to attach AgentCore policy: {e}") from e
