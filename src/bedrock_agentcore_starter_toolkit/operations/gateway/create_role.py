"""Creates an execution role to use in the Bedrock AgentCore Gateway module."""

import json
import logging
from typing import Optional

from boto3 import Session
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from ...operations.gateway.constants import (
    GATEWAY_EXECUTION_POLICY_NAME,
    POLICIES,
    POLICIES_TO_CREATE,
    build_gateway_access_policy,
    build_gateway_credential_provider_policy,
    build_gateway_lambda_invoke_policy,
)
from ...utils.aws import get_partition
from ...utils.runtime.policy_template import render_trust_policy_template


def create_gateway_execution_role(
    session: Session,
    logger: logging.Logger,
    role_name: str = "AgentCoreGatewayExecutionRole",
    region: Optional[str] = None,
    gateway_name: str = "*",
) -> str:
    """Create the Gateway execution role.

    :param session: the boto3 session to use.
    :param logger: the logger to use.
    :param role_name: the name of the role to create.
    :param region: the AWS region for the SourceArn condition. Defaults to the session region.
    :param gateway_name: the gateway name used to scope the gateway ARN in the base policy.
    :return: the role ARN.
    """
    iam = session.client("iam")
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    region = region or session.region_name
    partition = get_partition(region)
    trust_policy = render_trust_policy_template(region=region, account_id=account_id)
    # Create the role
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=trust_policy,
            Description="Execution role for AgentCore Gateway",
        )

        base_policy = build_gateway_access_policy(
            region=region, account_id=account_id, gateway_name=gateway_name, partition=partition
        )
        _attach_policy(
            iam_client=iam,
            role_name=role_name,
            policy_name=GATEWAY_EXECUTION_POLICY_NAME,
            policy_document=json.dumps(base_policy),
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

    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            try:
                role = iam.get_role(RoleName=role_name)
                logger.info("✓ Role already exists: %s", role["Role"]["Arn"])
                return role["Role"]["Arn"]
            except ClientError as get_error:
                logger.error("Error getting existing role: %s", get_error)
                raise
        else:
            logger.error("Error creating role: %s", e)
            raise


def _role_name_from_arn(role_arn: str) -> str:
    """Extract the role name from a role ARN (``.../role/<name>`` -> ``<name>``)."""
    return role_arn.split("/")[-1]


def append_credential_provider_permissions(
    session: Session,
    logger: logging.Logger,
    role_arn: str,
    provider_name: str,
    provider_kind: str,
    region: Optional[str] = None,
) -> None:
    """Attach token and secret access for a single credential provider to the gateway role.

    Failures are logged and do not raise, so target creation proceeds.

    :param session: the boto3 session to use.
    :param logger: the logger to use.
    :param role_arn: the gateway execution role ARN.
    :param provider_name: the credential provider name (scopes the secret/token-vault ARNs).
    :param provider_kind: ``oauth2`` or ``apikey``.
    :param region: AWS region; defaults to the session region.
    """
    region = region or session.region_name
    account_id = session.client("sts").get_caller_identity()["Account"]
    partition = get_partition(region)
    role_name = _role_name_from_arn(role_arn)
    policy = build_gateway_credential_provider_policy(
        region=region,
        account_id=account_id,
        provider_name=provider_name,
        provider_kind=provider_kind,
        partition=partition,
    )
    policy_name = f"GatewayCredentialProvider-{provider_kind}-{provider_name}"[:128]
    try:
        session.client("iam").put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy),
        )
        logger.info("✓ Scoped credential-provider permissions added to %s for provider %s", role_name, provider_name)
    except ClientError as e:
        logger.warning(
            "⚠️ Could not add scoped credential-provider permissions to %s for provider %s: %s. "
            "The gateway may lack access to this provider's secret; continuing (best effort).",
            role_name,
            provider_name,
            e,
        )


def append_lambda_target_permission(
    session: Session,
    logger: logging.Logger,
    role_arn: str,
    function_arn: str,
    region: Optional[str] = None,
) -> None:
    """Attach ``lambda:InvokeFunction`` for a single function ARN to the gateway role.

    Failures are logged and do not raise, so target creation proceeds.

    :param session: the boto3 session to use.
    :param logger: the logger to use.
    :param role_arn: the gateway execution role ARN.
    :param function_arn: the exact Lambda function ARN the target invokes.
    :param region: AWS region; defaults to the session region.
    """
    region = region or session.region_name
    account_id = session.client("sts").get_caller_identity()["Account"]
    partition = get_partition(region)
    role_name = _role_name_from_arn(role_arn)
    policy = build_gateway_lambda_invoke_policy(
        region=region, account_id=account_id, function_arn=function_arn, partition=partition
    )
    function_name = function_arn.split(":function:")[-1].split(":")[0]
    policy_name = f"GatewayLambdaTarget-{function_name}"[:128]
    try:
        session.client("iam").put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy),
        )
        logger.info("✓ Scoped Lambda invoke permission added to %s for %s", role_name, function_arn)
    except ClientError as e:
        logger.warning(
            "⚠️ Could not add scoped Lambda invoke permission to %s for %s: %s. "
            "The gateway may lack invoke access to this target; continuing (best effort).",
            role_name,
            function_arn,
            e,
        )


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
    # Check for invalid combinations of parameters
    if policy_arn:
        if policy_document or policy_name:
            raise Exception("Cannot specify both policy arn and policy document/name")
    elif not (policy_document and policy_name):
        raise Exception("Must specify both policy document and policy name, or just a policy arn")

    try:
        if policy_document and policy_name:
            policy_arn = _try_create_policy(iam_client, policy_name, policy_document)
        iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except ClientError as e:
        raise RuntimeError(f"Failed to attach AgentCore policy: {e}") from e


def _try_create_policy(iam_client: BaseClient, policy_name: str, policy_document: str) -> str:
    """Try to create a new policy, or return the arn if the policy already exists.

    :param iam_client: the IAM client to use.
    :param policy_name: the name of the policy to create.
    :param policy_document: the policy document to create.
    :return: the arn of the policy.
    """
    try:
        policy = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy_document,
        )
        return policy["Policy"]["Arn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            return _get_existing_policy_arn(iam_client, policy_name)
        else:
            raise e


def _get_existing_policy_arn(iam_client: BaseClient, policy_name: str) -> str:
    """Get the arn of an existing policy.

    :param iam_client: the IAM client to use.
    :param policy_name: the name of the policy to get.
    :return: the arn of the policy.
    """
    paginator = iam_client.get_paginator("list_policies")
    try:
        for page in paginator.paginate(Scope="Local"):
            for policy in page["Policies"]:
                if policy["PolicyName"] == policy_name:
                    return policy["Arn"]
    except ClientError as e:
        raise RuntimeError(f"Failed to get existing policy arn: {e}") from e
