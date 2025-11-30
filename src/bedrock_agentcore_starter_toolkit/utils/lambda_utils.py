"""Utility functions for creating AWS Lambda functions."""

import io
import json
import logging
import time
import zipfile
from typing import Optional

from boto3 import Session


def create_lambda_function(
    session: Session,
    logger: logging.Logger,
    function_name: str,
    lambda_code: str,
    runtime: str,
    handler: str,
    gateway_role_arn: str,
    description: Optional[str] = None,
) -> str:
    """Create a Lambda function with the specified code.

    Args:
        session: boto3 Session instance
        logger: Logger instance for output
        function_name: Name for the Lambda function
        lambda_code: Python code as a string to deploy
        runtime: Lambda runtime (e.g., 'python3.13')
        handler: Handler path (e.g., 'lambda_function.lambda_handler')
        gateway_role_arn: ARN of the gateway role that will invoke this Lambda
        description: Optional description for the Lambda function

    Returns:
        Lambda function ARN
    """
    lambda_client = session.client("lambda")
    iam = session.client("iam")
    role_name = f"{function_name}Role"

    # Create zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("lambda_function.py", lambda_code)
    zip_buffer.seek(0)

    # Define Lambda trust policy
    lambda_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    # Create Lambda execution role
    try:
        role_response = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(lambda_trust_policy))

        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )

        role_arn = role_response["Role"]["Arn"]
        logger.info("✓ Created Lambda execution role: %s", role_arn)

        # Wait for role to propagate
        time.sleep(10)

    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        role_arn = role["Role"]["Arn"]
        logger.info("✓ Lambda execution role already exists: %s", role_arn)

    # Create Lambda function
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role_arn,
            Handler=handler,
            Code={"ZipFile": zip_buffer.read()},
            Description=description or f"Lambda function for {function_name}",
        )

        lambda_arn = response["FunctionArn"]
        logger.info("✓ Created Lambda function: %s", lambda_arn)

        # Add permission for Gateway to invoke
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
        logger.info("✓ Lambda function already exists: %s", lambda_arn)

    return lambda_arn
