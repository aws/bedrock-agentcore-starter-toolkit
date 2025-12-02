"""Tests for Bedrock AgentCore configuration schema."""

import pytest
from pydantic import ValidationError

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    NetworkModeConfig,
    ObservabilityConfig,
    ProtocolConfiguration,
)


class TestNetworkConfiguration:
    """Test NetworkConfiguration schema validation."""

    def test_network_mode_validation_invalid(self):
        """Test network mode validation with invalid value."""
        # Line 65: Test invalid network_mode
        with pytest.raises(ValidationError) as exc_info:
            NetworkConfiguration(network_mode="INVALID_MODE")

        error_msg = str(exc_info.value)
        assert "Invalid network_mode" in error_msg
        assert "Must be one of" in error_msg

    def test_network_mode_config_required_for_vpc(self):
        """Test that network_mode_config is required when network_mode is VPC."""
        # Line 65: Test missing network_mode_config for VPC
        with pytest.raises(ValidationError) as exc_info:
            NetworkConfiguration(network_mode="VPC", network_mode_config=None)

        error_msg = str(exc_info.value)
        assert "network_mode_config is required when network_mode is VPC" in error_msg

    def test_network_mode_config_to_aws_dict_with_config(self):
        """Test to_aws_dict conversion with network_mode_config."""
        # Line 73: Test network_mode_config conversion to AWS format
        network_config = NetworkConfiguration(
            network_mode="VPC",
            network_mode_config=NetworkModeConfig(
                security_groups=["sg-123", "sg-456"], subnets=["subnet-abc", "subnet-def"]
            ),
        )

        result = network_config.to_aws_dict()

        assert result["networkMode"] == "VPC"
        assert "networkModeConfig" in result
        assert result["networkModeConfig"]["securityGroups"] == ["sg-123", "sg-456"]
        assert result["networkModeConfig"]["subnets"] == ["subnet-abc", "subnet-def"]

    def test_network_mode_config_to_aws_dict_without_config(self):
        """Test to_aws_dict conversion without network_mode_config."""
        network_config = NetworkConfiguration(network_mode="PUBLIC")

        result = network_config.to_aws_dict()

        assert result["networkMode"] == "PUBLIC"
        assert "networkModeConfig" not in result


class TestProtocolConfiguration:
    """Test ProtocolConfiguration schema validation."""

    def test_protocol_validation_invalid(self):
        """Test protocol validation with invalid value."""
        # Line 94: Test invalid server_protocol
        with pytest.raises(ValidationError) as exc_info:
            ProtocolConfiguration(server_protocol="INVALID_PROTOCOL")

        error_msg = str(exc_info.value)
        assert "Protocol must be one of" in error_msg

    def test_protocol_validation_case_insensitive(self):
        """Test protocol validation is case-insensitive."""
        # Test that lowercase protocol is converted to uppercase
        config1 = ProtocolConfiguration(server_protocol="http")
        assert config1.server_protocol == "HTTP"

        config2 = ProtocolConfiguration(server_protocol="mcp")
        assert config2.server_protocol == "MCP"

        config3 = ProtocolConfiguration(server_protocol="a2a")
        assert config3.server_protocol == "A2A"

    def test_protocol_to_aws_dict(self):
        """Test to_aws_dict conversion."""
        config = ProtocolConfiguration(server_protocol="MCP")
        result = config.to_aws_dict()

        assert result["serverProtocol"] == "MCP"


class TestAWSConfig:
    """Test AWSConfig schema validation."""

    def test_account_validation_invalid_length(self):
        """Test AWS account ID validation with invalid length."""
        # Line 127: Test invalid AWS account ID (wrong length)
        with pytest.raises(ValidationError) as exc_info:
            AWSConfig(account="12345", network_configuration=NetworkConfiguration())

        error_msg = str(exc_info.value)
        assert "Invalid AWS account ID" in error_msg

    def test_account_validation_non_numeric(self):
        """Test AWS account ID validation with non-numeric value."""
        # Line 127: Test invalid AWS account ID (non-numeric)
        with pytest.raises(ValidationError) as exc_info:
            AWSConfig(account="12345abcd123", network_configuration=NetworkConfiguration())

        error_msg = str(exc_info.value)
        assert "Invalid AWS account ID" in error_msg

    def test_account_validation_valid(self):
        """Test AWS account ID validation with valid value."""
        config = AWSConfig(account="123456789012", network_configuration=NetworkConfiguration())

        assert config.account == "123456789012"

    def test_account_validation_none_allowed(self):
        """Test that None is allowed for account field."""
        config = AWSConfig(account=None, network_configuration=NetworkConfiguration())

        assert config.account is None


class TestBedrockAgentCoreAgentSchema:
    """Test BedrockAgentCoreAgentSchema validation."""

    def _create_valid_agent_config(self) -> BedrockAgentCoreAgentSchema:
        """Helper to create a valid agent config."""
        return BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="agent.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/test-role",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

    def test_validate_missing_name(self):
        """Test validation error for missing name."""
        # Line 180: Test missing name validation
        agent_config = self._create_valid_agent_config()
        agent_config.name = ""  # Empty name

        errors = agent_config.validate()

        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)

    def test_validate_missing_entrypoint(self):
        """Test validation error for missing entrypoint."""
        # Line 180: Test missing entrypoint validation (though checked at line 182)
        agent_config = self._create_valid_agent_config()
        agent_config.entrypoint = ""  # Empty entrypoint

        errors = agent_config.validate()

        assert len(errors) > 0
        assert any("entrypoint" in error.lower() for error in errors)

    def test_validate_missing_aws_region_for_cloud(self):
        """Test validation error for missing AWS region in cloud deployment."""
        # Line 189: Test missing aws.region for cloud deployment
        agent_config = self._create_valid_agent_config()
        agent_config.aws.region = None

        errors = agent_config.validate(for_local=False)

        assert len(errors) > 0
        assert any("region" in error.lower() for error in errors)

    def test_validate_missing_aws_account_for_cloud(self):
        """Test validation error for missing AWS account in cloud deployment."""
        # Line 191: Test missing aws.account for cloud deployment
        agent_config = self._create_valid_agent_config()
        agent_config.aws.account = None

        errors = agent_config.validate(for_local=False)

        assert len(errors) > 0
        assert any("account" in error.lower() for error in errors)

    def test_validate_missing_execution_role_for_cloud(self):
        """Test validation error for missing execution role in cloud deployment."""
        agent_config = self._create_valid_agent_config()
        agent_config.aws.execution_role = None
        agent_config.aws.execution_role_auto_create = False

        errors = agent_config.validate(for_local=False)

        assert len(errors) > 0
        assert any("execution_role" in error.lower() for error in errors)

    def test_validate_for_local_skips_aws_checks(self):
        """Test that local validation skips AWS field requirements."""
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="agent.py",
            aws=AWSConfig(network_configuration=NetworkConfiguration()),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

        # No AWS fields set, but for_local=True should pass
        errors = agent_config.validate(for_local=True)

        # Should only fail on truly required fields, not AWS fields
        assert len(errors) == 0 or not any("aws" in error.lower() for error in errors)

    def test_validate_returns_empty_for_valid_config(self):
        """Test that validation returns empty list for valid config."""
        agent_config = self._create_valid_agent_config()

        errors = agent_config.validate(for_local=False)

        assert len(errors) == 0


class TestBedrockAgentCoreConfigSchema:
    """Test BedrockAgentCoreConfigSchema functionality."""

    def _create_test_agent(self, name: str) -> BedrockAgentCoreAgentSchema:
        """Helper to create a test agent config."""
        return BedrockAgentCoreAgentSchema(
            name=name,
            entrypoint="agent.py",
            aws=AWSConfig(
                region="us-west-2", network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

    def test_get_agent_config_no_agents_configured(self):
        """Test get_agent_config when no agents are configured."""
        # Line 226: Test error when no agents configured
        config = BedrockAgentCoreConfigSchema(agents={})

        with pytest.raises(ValueError) as exc_info:
            config.get_agent_config("some-agent")

        # Should raise error indicating no agents configured
        error_msg = str(exc_info.value)
        assert "No agents configured" in error_msg or "not found" in error_msg

    def test_get_agent_config_no_default_and_multiple_agents(self):
        """Test get_agent_config when no default is set and multiple agents exist."""
        # Line 219: Test error when no agent specified and no default set
        agent1 = self._create_test_agent("agent1")
        agent2 = self._create_test_agent("agent2")
        config = BedrockAgentCoreConfigSchema(default_agent=None, agents={"agent1": agent1, "agent2": agent2})

        with pytest.raises(ValueError) as exc_info:
            config.get_agent_config()

        assert "No agent specified and no default set" in str(exc_info.value)

    def test_get_agent_config_agent_not_found(self):
        """Test get_agent_config when specified agent doesn't exist."""
        # Line 224-226: Test error when agent not found
        agent1 = self._create_test_agent("agent1")
        config = BedrockAgentCoreConfigSchema(default_agent="agent1", agents={"agent1": agent1})

        with pytest.raises(ValueError) as exc_info:
            config.get_agent_config("non-existent")

        error_msg = str(exc_info.value)
        assert "Agent 'non-existent' not found" in error_msg
        assert "Available agents:" in error_msg

    def test_get_agent_config_single_agent_auto_default(self):
        """Test get_agent_config auto-selects single agent as default."""
        # Test that single agent is auto-selected
        agent = self._create_test_agent("only-agent")
        config = BedrockAgentCoreConfigSchema(default_agent=None, agents={"only-agent": agent})

        result = config.get_agent_config()

        assert result.name == "only-agent"
        # Should have set as default
        assert config.default_agent == "only-agent"

    def test_get_agent_config_by_name(self):
        """Test get_agent_config with specific agent name."""
        agent1 = self._create_test_agent("agent1")
        agent2 = self._create_test_agent("agent2")
        config = BedrockAgentCoreConfigSchema(default_agent="agent1", agents={"agent1": agent1, "agent2": agent2})

        result = config.get_agent_config("agent2")

        assert result.name == "agent2"

    def test_get_agent_config_uses_default(self):
        """Test get_agent_config uses default when no name specified."""
        agent1 = self._create_test_agent("agent1")
        agent2 = self._create_test_agent("agent2")
        config = BedrockAgentCoreConfigSchema(default_agent="agent2", agents={"agent1": agent1, "agent2": agent2})

        result = config.get_agent_config()

        assert result.name == "agent2"


class TestAwsJwtConfig:
    """Test AwsJwtConfig schema validation."""

    def test_default_values(self):
        """Test default values for AwsJwtConfig."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig()

        assert config.enabled is False
        assert config.audiences == []
        assert config.signing_algorithm == "ES384"
        assert config.issuer_url is None
        assert config.duration_seconds == 300

    def test_valid_es384_algorithm(self):
        """Test valid ES384 signing algorithm."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig(signing_algorithm="ES384")
        assert config.signing_algorithm == "ES384"

        # Test lowercase conversion
        config_lower = AwsJwtConfig(signing_algorithm="es384")
        assert config_lower.signing_algorithm == "ES384"

    def test_valid_rs256_algorithm(self):
        """Test valid RS256 signing algorithm."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig(signing_algorithm="RS256")
        assert config.signing_algorithm == "RS256"

        # Test lowercase conversion
        config_lower = AwsJwtConfig(signing_algorithm="rs256")
        assert config_lower.signing_algorithm == "RS256"

    def test_invalid_signing_algorithm(self):
        """Test invalid signing algorithm validation."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        with pytest.raises(ValidationError) as exc_info:
            AwsJwtConfig(signing_algorithm="INVALID")

        error_msg = str(exc_info.value)
        assert "Invalid signing_algorithm" in error_msg or "ES384" in error_msg

    def test_valid_duration_min(self):
        """Test minimum valid duration (60 seconds)."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig(duration_seconds=60)
        assert config.duration_seconds == 60

    def test_valid_duration_max(self):
        """Test maximum valid duration (3600 seconds)."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig(duration_seconds=3600)
        assert config.duration_seconds == 3600

    def test_invalid_duration_too_short(self):
        """Test duration below minimum."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        with pytest.raises(ValidationError) as exc_info:
            AwsJwtConfig(duration_seconds=59)

        error_msg = str(exc_info.value)
        assert "60" in error_msg or "greater than" in error_msg.lower()

    def test_invalid_duration_too_long(self):
        """Test duration above maximum."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        with pytest.raises(ValidationError) as exc_info:
            AwsJwtConfig(duration_seconds=3601)

        error_msg = str(exc_info.value)
        assert "3600" in error_msg or "less than" in error_msg.lower()

    def test_with_audiences(self):
        """Test AwsJwtConfig with audiences list."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        audiences = ["https://api1.example.com", "https://api2.example.com"]
        config = AwsJwtConfig(enabled=True, audiences=audiences)

        assert config.enabled is True
        assert config.audiences == audiences
        assert len(config.audiences) == 2

    def test_with_issuer_url(self):
        """Test AwsJwtConfig with issuer URL."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig(
            enabled=True,
            issuer_url="https://sts.us-west-2.amazonaws.com",
        )

        assert config.issuer_url == "https://sts.us-west-2.amazonaws.com"

    def test_full_configuration(self):
        """Test AwsJwtConfig with all fields."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import AwsJwtConfig

        config = AwsJwtConfig(
            enabled=True,
            audiences=["https://api.example.com"],
            signing_algorithm="RS256",
            issuer_url="https://sts.us-west-2.amazonaws.com",
            duration_seconds=900,
        )

        assert config.enabled is True
        assert config.audiences == ["https://api.example.com"]
        assert config.signing_algorithm == "RS256"
        assert config.issuer_url == "https://sts.us-west-2.amazonaws.com"
        assert config.duration_seconds == 900


class TestIdentityConfigAwsJwt:
    """Test IdentityConfig - aws_jwt is now at agent level, not identity level."""

    def test_identity_config_is_enabled_with_oauth_only(self):
        """Test is_enabled property with OAuth providers only."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
            CredentialProviderInfo,
            IdentityConfig,
        )

        config = IdentityConfig()
        config.credential_providers = [
            CredentialProviderInfo(
                name="TestProvider",
                arn="arn:aws:identity:us-west-2:123456789012:provider/TestProvider",
                type="cognito",
                callback_url="https://example.com/callback",
            )
        ]

        assert config.is_enabled is True
        assert config.has_oauth_providers is True

    def test_identity_config_is_not_enabled(self):
        """Test is_enabled property when nothing is configured."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import IdentityConfig

        config = IdentityConfig()

        assert config.is_enabled is False
        assert config.has_oauth_providers is False

    def test_identity_config_provider_names(self):
        """Test provider_names property."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
            CredentialProviderInfo,
            IdentityConfig,
        )

        config = IdentityConfig()
        config.credential_providers = [
            CredentialProviderInfo(
                name="Provider1",
                arn="arn:aws:identity:us-west-2:123456789012:provider/Provider1",
                type="cognito",
                callback_url="https://example.com/callback",
            ),
            CredentialProviderInfo(
                name="Provider2",
                arn="arn:aws:identity:us-west-2:123456789012:provider/Provider2",
                type="github",
                callback_url="https://example.com/callback",
            ),
        ]

        assert config.provider_names == ["Provider1", "Provider2"]


class TestAwsJwtConfigAtAgentLevel:
    """Test AwsJwtConfig at agent schema level (moved from IdentityConfig)."""

    def test_agent_schema_has_aws_jwt(self):
        """Test that aws_jwt is at agent level."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
            AWSConfig,
            AwsJwtConfig,
            BedrockAgentCoreAgentSchema,
            BedrockAgentCoreDeploymentInfo,
            NetworkConfiguration,
        )

        agent = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="agent.py",
            aws=AWSConfig(network_configuration=NetworkConfiguration()),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
            aws_jwt=AwsJwtConfig(enabled=True, audiences=["https://api.example.com"]),
        )

        assert agent.aws_jwt is not None
        assert agent.aws_jwt.enabled is True
        assert agent.aws_jwt.audiences == ["https://api.example.com"]

    def test_agent_schema_default_aws_jwt(self):
        """Test default aws_jwt config at agent level."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
            AWSConfig,
            BedrockAgentCoreAgentSchema,
            BedrockAgentCoreDeploymentInfo,
            NetworkConfiguration,
        )

        agent = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="agent.py",
            aws=AWSConfig(network_configuration=NetworkConfiguration()),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

        assert agent.aws_jwt is not None
        assert agent.aws_jwt.enabled is False
        assert agent.aws_jwt.audiences == []
