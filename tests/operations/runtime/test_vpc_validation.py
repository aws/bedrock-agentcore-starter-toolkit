"""Tests for VPC validation utilities."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.runtime.vpc_validation import (
    check_network_immutability,
    validate_vpc_configuration,
    verify_subnet_azs,
)


class TestValidateVPCConfiguration:
    """Test validate_vpc_configuration functionality."""

    def test_validate_vpc_configuration_success(self):
        """Test successful VPC configuration validation."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"},
                {"SubnetId": "subnet-xyz789ghi012", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2b"},
            ]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "sg-abc123xyz789", "VpcId": "vpc-test123"},
                {"GroupId": "sg-def456ghi012", "VpcId": "vpc-test123"},
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        vpc_id, warnings = validate_vpc_configuration(
            region="us-west-2",
            subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
            security_groups=["sg-abc123xyz789", "sg-def456ghi012"],
            session=mock_session,
        )

        assert vpc_id == "vpc-test123"
        assert len(warnings) == 0

    def test_validate_vpc_configuration_single_az_warning(self):
        """Test warning when subnets are in single availability zone."""
        # Mock EC2 client - both subnets in same AZ
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"},
                {
                    "SubnetId": "subnet-xyz789ghi012",
                    "VpcId": "vpc-test123",
                    "AvailabilityZone": "us-west-2a",
                },  # Same AZ
            ]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-test123"}]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        vpc_id, warnings = validate_vpc_configuration(
            region="us-west-2",
            subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
            security_groups=["sg-abc123xyz789"],
            session=mock_session,
        )

        assert vpc_id == "vpc-test123"
        assert len(warnings) == 1
        assert "only 1 availability zone" in warnings[0]
        assert "For high availability" in warnings[0]

    def test_validate_vpc_configuration_subnets_in_different_vpcs(self):
        """Test error when subnets are in different VPCs."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": "subnet-abc123def456", "VpcId": "vpc-111", "AvailabilityZone": "us-west-2a"},
                {"SubnetId": "subnet-xyz789ghi012", "VpcId": "vpc-222", "AvailabilityZone": "us-west-2b"},
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with pytest.raises(ValueError, match="All subnets must be in the same VPC"):
            validate_vpc_configuration(
                region="us-west-2",
                subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                security_groups=["sg-abc123xyz789"],
                session=mock_session,
            )

    def test_validate_vpc_configuration_subnet_not_found(self):
        """Test error when subnet ID doesn't exist."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.side_effect = ClientError(
            {"Error": {"Code": "InvalidSubnetID.NotFound", "Message": "Subnet not found"}}, "DescribeSubnets"
        )

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with pytest.raises(ValueError, match="One or more subnet IDs not found"):
            validate_vpc_configuration(
                region="us-west-2",
                subnets=["subnet-nonexistent"],
                security_groups=["sg-abc123xyz789"],
                session=mock_session,
            )

    def test_validate_vpc_configuration_security_groups_in_different_vpcs(self):
        """Test error when security groups are in different VPCs."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [
                {"GroupId": "sg-abc123xyz789", "VpcId": "vpc-111"},
                {"GroupId": "sg-def456ghi012", "VpcId": "vpc-222"},  # Different VPC
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with pytest.raises(ValueError, match="All security groups must be in the same VPC"):
            validate_vpc_configuration(
                region="us-west-2",
                subnets=["subnet-abc123def456"],
                security_groups=["sg-abc123xyz789", "sg-def456ghi012"],
                session=mock_session,
            )

    def test_validate_vpc_configuration_security_groups_mismatch_subnet_vpc(self):
        """Test error when security groups are in different VPC than subnets."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-111", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-222"}]  # Different VPC
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with pytest.raises(ValueError, match="Security groups must be in the same VPC as subnets"):
            validate_vpc_configuration(
                region="us-west-2",
                subnets=["subnet-abc123def456"],
                security_groups=["sg-abc123xyz789"],
                session=mock_session,
            )

    def test_validate_vpc_configuration_security_group_not_found(self):
        """Test error when security group ID doesn't exist."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.side_effect = ClientError(
            {"Error": {"Code": "InvalidGroup.NotFound", "Message": "Security group not found"}},
            "DescribeSecurityGroups",
        )

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with pytest.raises(ValueError, match="One or more security group IDs not found"):
            validate_vpc_configuration(
                region="us-west-2",
                subnets=["subnet-abc123def456"],
                security_groups=["sg-nonexistent"],
                session=mock_session,
            )

    def test_validate_vpc_configuration_creates_session_when_none_provided(self):
        """Test that function creates boto3 session when none provided."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-test123"}]
        }

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.vpc_validation.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_ec2
            mock_session_class.return_value = mock_session

            vpc_id, warnings = validate_vpc_configuration(
                region="us-west-2",
                subnets=["subnet-abc123def456"],
                security_groups=["sg-abc123xyz789"],
                session=None,  # No session provided
            )

            # Verify session was created
            mock_session_class.assert_called_once_with(region_name="us-west-2")
            assert vpc_id == "vpc-test123"


class TestCheckNetworkImmutability:
    """Test check_network_immutability functionality."""

    def test_check_network_immutability_no_change_public(self):
        """Test no error when both modes are PUBLIC."""
        error = check_network_immutability(
            existing_network_mode="PUBLIC",
            existing_subnets=None,
            existing_security_groups=None,
            new_network_mode="PUBLIC",
            new_subnets=None,
            new_security_groups=None,
        )

        assert error is None

    def test_check_network_immutability_no_change_vpc(self):
        """Test no error when VPC config unchanged."""
        error = check_network_immutability(
            existing_network_mode="VPC",
            existing_subnets=["subnet-abc123", "subnet-xyz789"],
            existing_security_groups=["sg-abc123"],
            new_network_mode="VPC",
            new_subnets=["subnet-abc123", "subnet-xyz789"],  # Same subnets (order doesn't matter)
            new_security_groups=["sg-abc123"],
        )

        assert error is None

    def test_check_network_immutability_mode_change_error(self):
        """Test error when changing network mode."""
        error = check_network_immutability(
            existing_network_mode="PUBLIC",
            existing_subnets=None,
            existing_security_groups=None,
            new_network_mode="VPC",
            new_subnets=["subnet-abc123"],
            new_security_groups=["sg-abc123"],
        )

        assert error is not None
        assert "Cannot change network mode" in error
        assert "PUBLIC" in error
        assert "VPC" in error
        assert "immutable" in error.lower()

    def test_check_network_immutability_subnet_change_error(self):
        """Test error when changing VPC subnets."""
        error = check_network_immutability(
            existing_network_mode="VPC",
            existing_subnets=["subnet-abc123"],
            existing_security_groups=["sg-abc123"],
            new_network_mode="VPC",
            new_subnets=["subnet-different"],  # Changed subnets
            new_security_groups=["sg-abc123"],
        )

        assert error is not None
        assert "Cannot change VPC subnets" in error
        assert "immutable" in error.lower()

    def test_check_network_immutability_security_group_change_error(self):
        """Test error when changing VPC security groups."""
        error = check_network_immutability(
            existing_network_mode="VPC",
            existing_subnets=["subnet-abc123"],
            existing_security_groups=["sg-abc123"],
            new_network_mode="VPC",
            new_subnets=["subnet-abc123"],
            new_security_groups=["sg-different"],  # Changed SGs
        )

        assert error is not None
        assert "Cannot change VPC security groups" in error
        assert "immutable" in error.lower()

    def test_check_network_immutability_handles_none_values(self):
        """Test immutability check handles None values properly."""
        # PUBLIC mode with None values
        error = check_network_immutability(
            existing_network_mode="PUBLIC",
            existing_subnets=None,
            existing_security_groups=None,
            new_network_mode="PUBLIC",
            new_subnets=None,
            new_security_groups=None,
        )

        assert error is None

    def test_check_network_immutability_subnet_order_independent(self):
        """Test that subnet order doesn't matter for immutability check."""
        # Same subnets, different order
        error = check_network_immutability(
            existing_network_mode="VPC",
            existing_subnets=["subnet-abc123", "subnet-xyz789"],
            existing_security_groups=["sg-abc123"],
            new_network_mode="VPC",
            new_subnets=["subnet-xyz789", "subnet-abc123"],  # Different order
            new_security_groups=["sg-abc123"],
        )

        assert error is None  # Order shouldn't matter


class TestVerifySubnetAZs:
    """Test verify_subnet_azs functionality."""

    def test_verify_subnet_azs_all_supported_us_west_2(self):
        """Test subnets in supported AZs for us-west-2."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "subnet-abc123",
                    "AvailabilityZone": "us-west-2a",
                    "AvailabilityZoneId": "usw2-az1",
                },
                {
                    "SubnetId": "subnet-xyz789",
                    "AvailabilityZone": "us-west-2b",
                    "AvailabilityZoneId": "usw2-az2",
                },
            ]
        }

        issues = verify_subnet_azs(mock_ec2, ["subnet-abc123", "subnet-xyz789"], "us-west-2")

        assert len(issues) == 0

    def test_verify_subnet_azs_unsupported_az(self):
        """Test detection of unsupported availability zone."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "subnet-abc123",
                    "AvailabilityZone": "us-west-2d",
                    "AvailabilityZoneId": "usw2-az4",  # Not in supported list
                }
            ]
        }

        issues = verify_subnet_azs(mock_ec2, ["subnet-abc123"], "us-west-2")

        assert len(issues) == 1
        assert "NOT supported by AgentCore" in issues[0]
        assert "usw2-az4" in issues[0]
        assert "Supported AZ IDs" in issues[0]

    def test_verify_subnet_azs_unknown_region(self):
        """Test behavior with unsupported region (no validation)."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "subnet-abc123",
                    "AvailabilityZone": "ap-south-1a",
                    "AvailabilityZoneId": "aps1-az1",
                }
            ]
        }

        # For unknown regions, no validation is performed (returns empty issues)
        issues = verify_subnet_azs(mock_ec2, ["subnet-abc123"], "ap-south-1")

        assert len(issues) == 0  # No issues for unknown region

    def test_verify_subnet_azs_all_supported_us_east_1(self):
        """Test subnets in supported AZs for us-east-1."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "subnet-abc123",
                    "AvailabilityZone": "us-east-1a",
                    "AvailabilityZoneId": "use1-az1",
                },
                {
                    "SubnetId": "subnet-xyz789",
                    "AvailabilityZone": "us-east-1b",
                    "AvailabilityZoneId": "use1-az2",
                },
            ]
        }

        issues = verify_subnet_azs(mock_ec2, ["subnet-abc123", "subnet-xyz789"], "us-east-1")

        assert len(issues) == 0

    def test_verify_subnet_azs_mixed_supported_unsupported(self):
        """Test mix of supported and unsupported AZs."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "subnet-abc123",
                    "AvailabilityZone": "us-west-2a",
                    "AvailabilityZoneId": "usw2-az1",  # Supported
                },
                {
                    "SubnetId": "subnet-xyz789",
                    "AvailabilityZone": "us-west-2d",
                    "AvailabilityZoneId": "usw2-az4",  # NOT supported
                },
            ]
        }

        issues = verify_subnet_azs(mock_ec2, ["subnet-abc123", "subnet-xyz789"], "us-west-2")

        assert len(issues) == 1
        assert "subnet-xyz789" in issues[0]
        assert "usw2-az4" in issues[0]
        assert "NOT supported" in issues[0]
