"""Typed configuration schema for Bedrock AgentCore SDK."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MemoryConfig(BaseModel):
    """Memory configuration for BedrockAgentCore."""

    mode: Literal["STM_ONLY", "STM_AND_LTM"] = Field(
        default="STM_ONLY", description="Memory mode - always has STM, optionally adds LTM"
    )
    memory_id: str | None = Field(default=None, description="Memory resource ID")
    memory_arn: str | None = Field(default=None, description="Memory resource ARN")
    memory_name: str | None = Field(default=None, description="Memory name")
    event_expiry_days: int = Field(default=30, description="Event expiry duration in days")
    first_invoke_memory_check_done: bool = Field(
        default=False, description="Whether first invoke memory check has been performed"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if memory is enabled (always true now)."""
        return True

    @property
    def has_ltm(self) -> bool:
        """Check if LTM is enabled."""
        return self.mode == "STM_AND_LTM"


class NetworkConfiguration(BaseModel):
    """Network configuration for BedrockAgentCore deployment."""

    network_mode: str = Field(default="PUBLIC", description="Network mode for deployment")

    def to_aws_dict(self) -> dict:
        """Convert to AWS API format with camelCase keys."""
        return {"networkMode": self.network_mode}


class ProtocolConfiguration(BaseModel):
    """Protocol configuration for BedrockAgentCore deployment."""

    server_protocol: str = Field(default="HTTP", description="Server protocol for deployment, either HTTP or MCP")

    def to_aws_dict(self) -> dict:
        """Convert to AWS API format with camelCase keys."""
        return {"serverProtocol": self.server_protocol}


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    enabled: bool = Field(default=True, description="Whether observability is enabled")


class AWSConfig(BaseModel):
    """AWS-specific configuration."""

    execution_role: str | None = Field(default=None, description="AWS IAM execution role ARN")
    execution_role_auto_create: bool = Field(default=False, description="Whether to auto-create execution role")
    account: str | None = Field(default=None, description="AWS account ID")
    region: str | None = Field(default=None, description="AWS region")
    ecr_repository: str | None = Field(default=None, description="ECR repository URI")
    ecr_auto_create: bool = Field(default=False, description="Whether to auto-create ECR repository")
    network_configuration: NetworkConfiguration = Field(default_factory=NetworkConfiguration)
    protocol_configuration: ProtocolConfiguration = Field(default_factory=ProtocolConfiguration)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @field_validator("account")
    @classmethod
    def validate_account(cls, v: str | None) -> str | None:
        """Validate AWS account ID."""
        if v is not None and (not v.isdigit() or len(v) != 12):
            raise ValueError("Invalid AWS account ID")
        return v


class CodeBuildConfig(BaseModel):
    """CodeBuild deployment information."""

    project_name: str | None = Field(default=None, description="CodeBuild project name")
    execution_role: str | None = Field(default=None, description="CodeBuild execution role ARN")
    source_bucket: str | None = Field(default=None, description="S3 source bucket name")


class BedrockAgentCoreDeploymentInfo(BaseModel):
    """BedrockAgentCore deployment information."""

    agent_id: str | None = Field(default=None, description="BedrockAgentCore agent ID")
    agent_arn: str | None = Field(default=None, description="BedrockAgentCore agent ARN")
    agent_session_id: str | None = Field(default=None, description="Session ID for invocations")


class BuildArtifactInfo(BaseModel):
    """Build artifact organization information for enhanced configuration management."""

    base_directory: str | None = Field(default=None, description="Root directory for agent's build artifacts")
    source_copy_path: str | None = Field(default=None, description="Path to copied source code")
    dockerfile_path: str | None = Field(default=None, description="Path to generated Dockerfile")
    build_timestamp: datetime | None = Field(default=None, description="When artifacts were created")
    organized: bool = Field(default=False, description="Whether artifacts are properly organized")

    def get_artifact_directory(self, agent_name: str) -> str:
        """Get the artifact directory path for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Path to the artifact directory
        """
        return f".packages/{agent_name}"

    def is_valid(self) -> bool:
        """Check if artifact info represents a valid organization.

        Returns:
            True if artifacts are properly organized
        """
        if not self.organized:
            return False

        # For basic validity, we only need the fields to be present
        # Directory existence will be checked at build time
        return bool(self.base_directory)

    def cleanup(self) -> None:
        """Clean up build artifacts directory."""
        if self.base_directory:
            try:
                base_path = Path(self.base_directory)
                if base_path.exists():
                    import shutil

                    shutil.rmtree(base_path)
                    self.organized = False
                    self.build_timestamp = None
            except Exception:
                # Cleanup failures are non-critical
                pass


class BedrockAgentCoreAgentSchema(BaseModel):
    """Type-safe schema for BedrockAgentCore configuration."""

    name: str = Field(..., description="Name of the Bedrock AgentCore application")
    entrypoint: str = Field(..., description="Entrypoint file path")
    platform: str = Field(default="linux/amd64", description="Target platform")
    container_runtime: str = Field(default="docker", description="Container runtime to use")
    aws: AWSConfig = Field(default_factory=AWSConfig)
    bedrock_agentcore: BedrockAgentCoreDeploymentInfo = Field(default_factory=BedrockAgentCoreDeploymentInfo)
    codebuild: CodeBuildConfig = Field(default_factory=CodeBuildConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    authorizer_configuration: dict | None = Field(default=None, description="JWT authorizer configuration")
    request_header_configuration: dict | None = Field(default=None, description="Request header configuration")
    oauth_configuration: dict | None = Field(default=None, description="Oauth configuration")

    # Enhanced configuration management fields (backward compatible)
    source_path: str | None = Field(default=None, description="Directory containing agent source code")
    build_artifacts: BuildArtifactInfo | None = Field(
        default=None, description="Build artifact organization information"
    )

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, v: str | None) -> str | None:
        """Validate source path if provided.

        Args:
            v: Source path value

        Returns:
            Validated source path or None

        Raises:
            ValueError: If source path is invalid
        """
        if v is None:
            return v

        # Convert to Path for validation
        source_path = Path(v)

        # Check if path exists
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {v}")

        # Check if it's a directory
        if not source_path.is_dir():
            raise ValueError(f"Source path must be a directory: {v}")

        # Return absolute path string
        return str(source_path.resolve())

    def get_authorizer_configuration(self) -> dict | None:
        """Get the authorizer configuration."""
        return self.authorizer_configuration

    def validate(self, for_local: bool = False) -> list[str]:
        """Validate configuration and return list of errors.

        Args:
            for_local: Whether validating for local deployment

        Returns:
            List of validation error messages
        """
        errors = []

        # Required fields for all deployments
        if not self.name:
            errors.append("Missing 'name' field")
        if not self.entrypoint:
            errors.append("Missing 'entrypoint' field")

        # AWS fields required for cloud deployment
        if not for_local:
            if not self.aws.execution_role and not self.aws.execution_role_auto_create:
                errors.append("Missing 'aws.execution_role' for cloud deployment (or enable auto-creation)")
            if not self.aws.region:
                errors.append("Missing 'aws.region' for cloud deployment")
            if not self.aws.account:
                errors.append("Missing 'aws.account' for cloud deployment")

        # Enhanced field validation (optional)
        if self.source_path:
            try:
                # Validate entrypoint exists within source path
                source_dir = Path(self.source_path)
                entrypoint_path = source_dir / self.entrypoint

                if not entrypoint_path.exists():
                    errors.append(f"Entrypoint file not found in source path: {entrypoint_path}")
            except Exception as e:
                errors.append(f"Error validating source path: {e}")

        return errors


class BedrockAgentCoreConfigSchema(BaseModel):
    """Project configuration supporting multiple named agents.

    Operations use --agent parameter to select which agent to work with.
    """

    default_agent: str | None = Field(default=None, description="Default agent name for operations")
    agents: dict[str, BedrockAgentCoreAgentSchema] = Field(
        default_factory=dict, description="Named agent configurations"
    )

    def get_agent_config(self, agent_name: str | None = None) -> BedrockAgentCoreAgentSchema:
        """Get agent config by name or default.

        Args:
            agent_name: Agent name from --agent parameter, or None for default
        """
        target_name = agent_name or self.default_agent
        if not target_name:
            if len(self.agents) == 1:
                agent = list(self.agents.values())[0]
                self.default_agent = agent.name
                return agent
            raise ValueError("No agent specified and no default set")

        if target_name not in self.agents:
            available = list(self.agents.keys())
            if available:
                raise ValueError(f"Agent '{target_name}' not found. Available agents: {available}")
            else:
                raise ValueError("No agents configured")

        return self.agents[target_name]
