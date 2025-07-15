"""Creates a Lambda function to use as a Bedrock AgentCore Gateway Target."""

import io
import json
import logging
import zipfile

from boto3 import Session

from ...operations.gateway.constants import (
    LAMBDA_FUNCTION_CODE,
    LAMBDA_TRUST_POLICY,
)


def create_test_lambda(session: Session, logger: logging.Logger, gateway_role_arn: str) -> str:
    """Create a test Lambda function.

    :param region_name: the name of the region to create in.
    :param logger: instance of a logger.
    :param gateway_role_arn: the execution role arn of the gateway this lambda is going to be used with.
    :return: the lambda arn
    """
    lambda_client = session.client("lambda")
    iam = session.client("iam")
    function_name = "AgentCoreLambdaTestFunction"
    role_name = "AgentCoreTestLambdaRole"

    # Create zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("lambda_function.py", LAMBDA_FUNCTION_CODE)
    zip_buffer.seek(0)

    # Create Lambda execution role

    try:
        role_response = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(LAMBDA_TRUST_POLICY))

        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )

        role_arn = role_response["Role"]["Arn"]
        logger.info("✓ Created Lambda execution role: %s", role_arn)

        # Wait a bit for role to propagate
        import time

        time.sleep(10)

    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]

    # Create Lambda function
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.9",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_buffer.read()},
            Description="Test Lambda for AgentCore Gateway",
        )

        lambda_arn = response["FunctionArn"]
        logger.info("✓ Created Lambda function: %s", lambda_arn)
        logger.info("✓ Attaching access policy to: %s for %s", lambda_arn, gateway_role_arn)

        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId="AllowAgentCoreInvoke",
            Action="lambda:InvokeFunction",
            Principal=gateway_role_arn,
        )
        logger.info("✓ Attached permissions for role invocation: %s", lambda_arn)

    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.get_function(FunctionName=function_name)
        lambda_arn = response["Configuration"]["FunctionArn"]
        logger.info("✓ Lambda already exists: %s", lambda_arn)

    return lambda_arn
