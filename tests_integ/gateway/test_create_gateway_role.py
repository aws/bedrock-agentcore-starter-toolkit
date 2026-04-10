import logging
import os
import uuid

import boto3

from bedrock_agentcore_starter_toolkit.operations.gateway.create_role import create_gateway_execution_role


def test_create_role():
    region = os.environ.get("AWS_REGION", "us-east-1")
    session = boto3.Session(region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]

    uid = str(uuid.uuid4())[:8]
    role_name = f"SomeRandomName-{uid}"

    role_arn = create_gateway_execution_role(
        session, logging.getLogger("TestCreateRole"), role_name=role_name, region=region
    )
    assert isinstance(role_arn, str)

    # Verify the trust policy has the required confused-deputy conditions
    trust_doc = session.client("iam").get_role(RoleName=role_name)["Role"]["AssumeRolePolicyDocument"]
    stmt = trust_doc["Statement"][0]
    assert "Condition" in stmt, "Trust policy is missing Condition block"
    cond = stmt["Condition"]
    assert cond["StringEquals"]["aws:SourceAccount"] == account_id
    assert cond["ArnLike"]["aws:SourceArn"] == f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
