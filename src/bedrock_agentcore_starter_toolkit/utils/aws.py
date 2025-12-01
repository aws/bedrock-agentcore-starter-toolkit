"""Generic aws utilities."""

from typing import Optional

import boto3
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

# Default AWS region
DEFAULT_REGION = "us-west-2"


def extract_id_from_arn(arn_or_id: str) -> str:
    """Extract resource ID from ARN or return ID as-is.

    Args:
        arn_or_id: Either a resource ID or an ARN

    Returns:
        The resource ID (last segment after '/' if ARN, otherwise the identifier itself)

    Examples:
        >>> extract_id_from_arn("gateway-123")
        "gateway-123"
        >>> extract_id_from_arn("arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/gateway-123")
        "gateway-123"
        >>> extract_id_from_arn("arn:aws:iam::123456789012:role/MyRole")
        "MyRole"
    """
    return arn_or_id.split("/")[-1] if "/" in arn_or_id else arn_or_id


def get_account_id() -> str:
    """Get AWS account ID."""
    return boto3.client("sts").get_caller_identity()["Account"]


def get_region() -> str:
    """Get AWS region."""
    return boto3.Session().region_name or DEFAULT_REGION


def ensure_valid_aws_creds() -> tuple[bool, Optional[str]]:
    """Try to make an sts call and return a resourceful message if it fails."""
    try:
        get_account_id()
        return True, None

    except NoCredentialsError:
        return False, "No AWS credentials found."

    except PartialCredentialsError:
        return False, "AWS credentials are incomplete or misconfigured."

    except ClientError as e:
        code = e.response["Error"]["Code"]

        if code in ("ExpiredToken", "ExpiredTokenException", "RequestExpired"):
            return False, "AWS credentials have expired. Please refresh or re-authenticate."

        if code in ("InvalidClientTokenId", "UnrecognizedClientException"):
            return False, "AWS credentials are invalid."

        return False, f"AWS credential validation failed: {e.response['Error'].get('Message', code)}"

    except Exception:
        # Don't block the user — a non-credential error occurred
        return True, None
