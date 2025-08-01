import logging
import uuid

import boto3

from bedrock_agentcore_starter_toolkit.operations.gateway.create_role import create_gateway_execution_role


def test_create_role():
    uid = str(uuid.uuid4())[:8]
    role_arn = create_gateway_execution_role(
        boto3.Session(), logging.getLogger("TestCreateRole"), role_name=f"SomeRandomName-{uid}"
    )
    assert isinstance(role_arn, str)
