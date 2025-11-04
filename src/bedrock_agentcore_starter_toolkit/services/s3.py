"""S3 service integration."""

import logging
import re

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


def sanitize_s3_bucket_name(name: str, account_id: str, region: str) -> str:
    """Sanitize agent name for S3 bucket naming requirements."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-.]", "-", name)
    name = re.sub(r"[-\.]{2,}", "-", name)
    name = name.strip("-.")

    if name and not name[0].isalnum():
        name = "a" + name
    if name and not name[-1].isalnum():
        name = name + "a"

    bucket_name = f"bedrock-agentcore-{name}-{account_id}-{region}"

    if len(bucket_name) < 3:
        bucket_name = f"bedrock-agentcore-agent-{account_id}-{region}"

    if len(bucket_name) > 63:
        suffix = f"-{account_id}-{region}"
        max_name_length = 63 - len("bedrock-agentcore-") - len(suffix)
        truncated_name = name[:max_name_length].rstrip("-.")
        bucket_name = f"bedrock-agentcore-{truncated_name}{suffix}"

    return bucket_name


def get_or_create_s3_bucket(agent_name: str, account_id: str, region: str) -> str:
    """Get existing S3 bucket or create a new one (idempotent).

    Uses the same bucket naming pattern as CodeBuild for consistency.
    """
    bucket_name = f"bedrock-agentcore-codebuild-sources-{account_id}-{region}"
    s3 = boto3.client("s3", region_name=region)

    try:
        s3.head_bucket(Bucket=bucket_name, ExpectedBucketOwner=account_id)
        print(f"✅ Reusing existing S3 bucket: {bucket_name}")
        return bucket_name
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "403":
            raise RuntimeError(
                f"Access Error: Unable to access S3 bucket '{bucket_name}' due to permission constraints."
            ) from e
        elif error_code == "404":
            print(f"Bucket doesn't exist, creating new S3 bucket: {bucket_name}")
            return create_s3_bucket(bucket_name, region, account_id)
        else:
            raise RuntimeError(f"Unexpected error checking S3 bucket: {e}") from e


def create_s3_bucket(bucket_name: str, region: str, account_id: str) -> str:
    """Create S3 bucket with appropriate configuration."""
    s3 = boto3.client("s3", region_name=region)

    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name, ExpectedBucketOwner=account_id)
        else:
            s3.create_bucket(
                Bucket=bucket_name, 
                CreateBucketConfiguration={"LocationConstraint": region},
                ExpectedBucketOwner=account_id
            )

        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            ExpectedBucketOwner=account_id,
            LifecycleConfiguration={
                "Rules": [{"ID": "DeleteOldBuilds", "Status": "Enabled", "Filter": {}, "Expiration": {"Days": 7}}]
            },
        )

        print(f"✅ Created S3 bucket: {bucket_name}")
        return bucket_name

    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            print(f"✅ S3 bucket already exists: {bucket_name}")
            return bucket_name
        else:
            raise RuntimeError(f"Failed to create S3 bucket: {e}") from e
