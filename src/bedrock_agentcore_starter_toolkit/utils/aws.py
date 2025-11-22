"""Generic aws utilities."""

import boto3


def get_account_id() -> str:
    """Get AWS account ID."""
    return boto3.client("sts").get_caller_identity()["Account"]


def get_region() -> str:
    """Get AWS region."""
    return boto3.Session().region_name or "us-west-2"
