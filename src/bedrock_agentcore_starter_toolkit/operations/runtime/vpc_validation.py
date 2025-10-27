"""VPC networking validation utilities for AgentCore Runtime."""

import logging
from typing import List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


def validate_vpc_configuration(
    region: str,
    subnets: List[str],
    security_groups: List[str],
    session: Optional[boto3.Session] = None,
) -> Tuple[str, List[str]]:
    """Validate VPC configuration and return VPC ID and any warnings.

    Args:
        region: AWS region
        subnets: List of subnet IDs
        security_groups: List of security group IDs
        session: Optional boto3 session (creates new if not provided)

    Returns:
        Tuple of (vpc_id, warnings_list)

    Raises:
        ValueError: If validation fails
    """
    if not session:
        session = boto3.Session(region_name=region)

    ec2_client = session.client("ec2", region_name=region)
    warnings = []

    # Validate subnets
    vpc_id = _validate_subnets(ec2_client, subnets, warnings)

    # Validate security groups
    _validate_security_groups(ec2_client, security_groups, vpc_id, warnings)

    return vpc_id, warnings


def _validate_subnets(ec2_client, subnets: List[str], warnings: List[str]) -> str:
    """Validate subnets and return VPC ID."""
    try:
        response = ec2_client.describe_subnets(SubnetIds=subnets)

        if len(response["Subnets"]) != len(subnets):
            found_ids = {s["SubnetId"] for s in response["Subnets"]}
            missing = set(subnets) - found_ids
            raise ValueError(f"Subnet IDs not found: {missing}")

        # Check all subnets are in same VPC
        vpc_ids = {subnet["VpcId"] for subnet in response["Subnets"]}

        if len(vpc_ids) > 1:
            raise ValueError(
                f"All subnets must be in the same VPC. Found subnets in {len(vpc_ids)} different VPCs: {vpc_ids}"
            )

        vpc_id = vpc_ids.pop()
        log.info("✓ Validated %d subnets in VPC %s", len(subnets), vpc_id)

        # Check subnet availability zones
        azs = {subnet["AvailabilityZone"] for subnet in response["Subnets"]}
        if len(azs) < 2:
            warnings.append(
                f"Subnets are in only {len(azs)} availability zone(s). "
                "For high availability, use subnets in multiple AZs."
            )

        return vpc_id

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "InvalidSubnetID.NotFound":
            raise ValueError(f"One or more subnet IDs not found: {subnets}") from e
        raise ValueError(f"Failed to validate subnets: {e}") from e


def _validate_security_groups(
    ec2_client, security_groups: List[str], expected_vpc_id: str, warnings: List[str]
) -> None:
    """Validate security groups are in the expected VPC."""
    try:
        response = ec2_client.describe_security_groups(GroupIds=security_groups)

        if len(response["SecurityGroups"]) != len(security_groups):
            found_ids = {sg["GroupId"] for sg in response["SecurityGroups"]}
            missing = set(security_groups) - found_ids
            raise ValueError(f"Security group IDs not found: {missing}")

        # Check all SGs are in same VPC
        sg_vpcs = {sg["VpcId"] for sg in response["SecurityGroups"]}

        if len(sg_vpcs) > 1:
            raise ValueError(
                f"All security groups must be in the same VPC. "
                f"Found security groups in {len(sg_vpcs)} different VPCs: {sg_vpcs}"
            )

        sg_vpc_id = sg_vpcs.pop()

        # Check SGs are in same VPC as subnets
        if sg_vpc_id != expected_vpc_id:
            raise ValueError(
                f"Security groups must be in the same VPC as subnets. "
                f"Subnets are in VPC {expected_vpc_id}, "
                f"but security groups are in VPC {sg_vpc_id}"
            )

        log.info("✓ Validated %d security groups in VPC %s", len(security_groups), sg_vpc_id)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "InvalidGroup.NotFound":
            raise ValueError(f"One or more security group IDs not found: {security_groups}") from e
        raise ValueError(f"Failed to validate security groups: {e}") from e


def check_network_immutability(
    existing_network_mode: str,
    existing_subnets: Optional[List[str]],
    existing_security_groups: Optional[List[str]],
    new_network_mode: str,
    new_subnets: Optional[List[str]],
    new_security_groups: Optional[List[str]],
) -> Optional[str]:
    """Check if network configuration is being changed (not allowed).

    Returns:
        Error message if change detected, None if no change
    """
    # Check mode change
    if existing_network_mode != new_network_mode:
        return (
            f"Cannot change network mode from {existing_network_mode} to {new_network_mode}. "
            f"Network configuration is immutable after agent creation. "
            f"Create a new agent for different network settings."
        )

    # If both PUBLIC, no further checks needed
    if existing_network_mode == "PUBLIC":
        return None

    # Check VPC resource changes
    if set(existing_subnets or []) != set(new_subnets or []):
        return (
            "Cannot change VPC subnets after agent creation. "
            "Network configuration is immutable. "
            "Create a new agent for different network settings."
        )

    if set(existing_security_groups or []) != set(new_security_groups or []):
        return (
            "Cannot change VPC security groups after agent creation. "
            "Network configuration is immutable. "
            "Create a new agent for different network settings."
        )

    return None


def verify_subnet_azs(ec2_client, subnets: List[str], region: str) -> List[str]:
    """Verify subnets are in supported AZs and return any issues."""
    # Supported AZ IDs for us-west-2
    SUPPORTED_AZS = {
        "us-west-2": ["usw2-az1", "usw2-az2", "usw2-az3"],
        "us-east-1": ["use1-az1", "use1-az2", "use1-az4"],
        # Add other regions as needed
    }

    supported = SUPPORTED_AZS.get(region, [])

    response = ec2_client.describe_subnets(SubnetIds=subnets)
    issues = []

    for subnet in response["Subnets"]:
        subnet_id = subnet["SubnetId"]
        az_id = subnet["AvailabilityZoneId"]
        az_name = subnet["AvailabilityZone"]

        if supported and az_id not in supported:
            issues.append(
                f"Subnet {subnet_id} is in AZ {az_name} (ID: {az_id}) "
                f"which is NOT supported by AgentCore in {region}. "
                f"Supported AZ IDs: {supported}"
            )
        else:
            log.info("✓ Subnet %s is in supported AZ: %s (%s)", subnet_id, az_name, az_id)

    return issues
