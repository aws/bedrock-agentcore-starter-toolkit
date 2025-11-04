"""Typed configuration schema for Bedrock AgentCore SDK."""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class NetworkModeConfig(BaseModel):
    """Network mode configuration for VPC deployments."""

    security_groups: List[str] = Field(default_factory=list, description="List of security group IDs")
    subnets: List[str] = Field(default_factory=list, description="List of subnet IDs")


class MemoryConfig(BaseModel):
    """Memory configuration for BedrockAgentCore."""

    mode: Literal["STM_ONLY", "STM_AND_LTM", "NO_MEMORY"] = Field(
        default="NO_MEMORY", description="Memory mode - opt-in feature"
    )
    memory_id: Optional[str] = Field(default=None, description="Memory resource ID")
    memory_arn: Optional[str] = Field(default=None, description="Memory resource ARN")
    memory_name: Optional[str] = Field(default=None, description="Memory name")
    event_expiry_days: int = Field(default=30, description="Event expiry duration in days")
    first_invoke_memory_check_done: bool = Field(
        default=False, description="Whether first invoke memory check has been performed"
    )
    was_created_by_toolkit: bool = Field(
        default=False, description="Whether memory was created by toolkit (vs reused existing)"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if memory is enabled."""
        return self.mode != "NO_MEMORY"

    @property
    def has_ltm(self) -> bool:
        """Check if LTM is enabled."""
        return self.mode == "STM_AND_LTM"


class NetworkConfiguration(BaseModel):
    """Network configuration for BedrockAgentCore deployment."""

    network_mode: str = Field(default="PUBLIC", description="Network mode for deployment")
    network_mode_config: Optional[NetworkModeConfig] = Field(
        default=None, description="Network mode configuration (required for VPC mode)"
    )

    @field_validator("network_mode")
    @classmethod
    def validate_network_mode(cls, v: str) -> str:
        """Validate network mode and ensure VPC config is provided when needed."""
        valid_modes = ["PUBLIC", "VPC"]
        if v not in valid_modes:
            raise ValueError(f"Invalid network_mode: {v}. Must be one of {valid_modes}")
        return v

    @field_validator("network_mode_config")
    @classmethod
    def validate_network_mode_config(cls, v: Optional[NetworkModeConfig], info) -> Optional[NetworkModeConfig]:
        """Validate that network_mode_config is provided when network_mode is VPC."""
        if info.data.get("network_mode") == "VPC" and v is None:
            raise ValueError("network_mode_config is required when network_mode is VPC")
        return v

    def to_aws_dict(self) -> dict:
        """Convert to AWS API format with camelCase keys."""
        result = {"networkMode": self.network_mode}

        if self.network_mode_config:
            result["networkModeConfig"] = {
                "securityGroups": self.network_mode_config.security_groups,
                "subnets": self.network_mode_config.subnets,
            }

        return result


class ProtocolConfiguration(BaseModel):
    """Protocol configuration for BedrockAgentCore deployment."""

    server_protocol: str = Field(
        default="HTTP", description="Server protocol for deployment, either HTTP or MCP or A2A"
    )

    @field_validator("server_protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Validate protocol is one of the supported types."""
        allowed = ["HTTP", "MCP", "A2A"]
        if v.upper() not in allowed:
            raise ValueError(f"Protocol must be one of {allowed}, got: {v}")
        return v.upper()

    def to_aws_dict(self) -> dict:
        """Convert to AWS API format with camelCase keys."""
        return {"serverProtocol": self.server_protocol}


class LifecycleConfiguration(BaseModel):
    """Lifecycle configuration for runtime sessions."""

    idle_runtime_session_timeout: Optional[int] = Field(
        default=None,
        description="Timeout in seconds for idle runtime sessions (60-28800)",
        ge=60,
        le=28800,
    )
    max_lifetime: Optional[int] = Field(
        default=None, description="Maximum lifetime for the instance in seconds (60-28800)", ge=60, le=28800
    )

    @field_validator("max_lifetime")
    @classmethod
    def validate_lifecycle_relationship(cls, v: Optional[int], info) -> Optional[int]:
        """Validate that max_lifetime >= idle_timeout if both are set."""
        if v is None:
            return v

        idle = info.data.get("idle_runtime_session_timeout")
        if idle is not None and v < idle:
            raise ValueError(
                f"max_lifetime ({v}s) must be greater than or equal to idle_runtime_session_timeout ({idle}s)"
            )
        return v

    def to_aws_dict(self) -> dict:
        """Convert to AWS API format with camelCase keys."""
        result = {}
        if self.idle_runtime_session_timeout is not None:
            result["idleRuntimeSessionTimeout"] = self.idle_runtime_session_timeout
        if self.max_lifetime is not None:
            result["maxLifetime"] = self.max_lifetime
        return result

    @property
    def has_custom_settings(self) -> bool:
        """Check if any custom lifecycle settings are configured."""
        return self.idle_runtime_session_timeout is not None or self.max_lifetime is not None


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    enabled: bool = Field(default=True, description="Whether observability is enabled")


class AWSConfig(BaseModel):
    """AWS-specific configuration."""

    execution_role: Optional[str] = Field(default=None, description="AWS IAM execution role ARN")
    execution_role_auto_create: bool = Field(default=False, description="Whether to auto-create execution role")
    account: Optional[str] = Field(default=None, description="AWS account ID")
    region: Optional[str] = Field(default=None, description="AWS region")
    ecr_repository: Optional[str] = Field(default=None, description="ECR repository URI")
    ecr_auto_create: bool = Field(default=False, description="Whether to auto-create ECR repository")
    s3_path: Optional[str] = Field(default=None, description="S3 URI for code deployment")
    s3_auto_create: bool = Field(default=False, description="Whether to auto-create S3 bucket")
    network_configuration: NetworkConfiguration = Field(default_factory=NetworkConfiguration)
    protocol_configuration: ProtocolConfiguration = Field(default_factory=ProtocolConfiguration)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    lifecycle_configuration: LifecycleConfiguration = Field(default_factory=LifecycleConfiguration)

    @field_validator("account")
    @classmethod
    def validate_account(cls, v: Optional[str]) -> Optional[str]:
        """Validate AWS account ID."""
        if v is not None:
            if not v.isdigit() or len(v) != 12:
                raise ValueError("Invalid AWS account ID")
        return v


class CodeBuildConfig(BaseModel):
    """CodeBuild deployment information."""

    project_name: Optional[str] = Field(default=None, description="CodeBuild project name")
    execution_role: Optional[str] = Field(default=None, description="CodeBuild execution role ARN")
    source_bucket: Optional[str] = Field(default=None, description="S3 source bucket name")


class BedrockAgentCoreDeploymentInfo(BaseModel):
    """BedrockAgentCore deployment information."""

    agent_id: Optional[str] = Field(default=None, description="BedrockAgentCore agent ID")
    agent_arn: Optional[str] = Field(default=None, description="BedrockAgentCore agent ARN")
    agent_session_id: Optional[str] = Field(default=None, description="Session ID for invocations")


class BedrockAgentCoreAgentSchema(BaseModel):
    """Type-safe schema for BedrockAgentCore configuration."""

    name: str = Field(..., description="Name of the Bedrock AgentCore application")
    entrypoint: str = Field(..., description="Entrypoint file path (e.g., 'agent.py' or 'agent.py:handler')")
    deployment_type: Literal["container", "direct_code_deploy"] = Field(
        default="container", description="Deployment artifact type: container (Docker) or direct_code_deploy"
    )
    runtime_type: Optional[str] = Field(
        default=None, description="Managed runtime version for direct_code_deploy (e.g., 'PYTHON_3_10', 'PYTHON_3_11')"
    )
    platform: str = Field(default="linux/amd64", description="Target platform (for container deployments)")
    container_runtime: Optional[str] = Field(
        default=None, description="Container runtime to use (for container deployments)"
    )
    source_path: Optional[str] = Field(default=None, description="Directory containing agent source code")
    aws: AWSConfig = Field(default_factory=AWSConfig)
    bedrock_agentcore: BedrockAgentCoreDeploymentInfo = Field(default_factory=BedrockAgentCoreDeploymentInfo)
    codebuild: CodeBuildConfig = Field(default_factory=CodeBuildConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    authorizer_configuration: Optional[dict] = Field(default=None, description="JWT authorizer configuration")
    request_header_configuration: Optional[dict] = Field(default=None, description="Request header configuration")
    oauth_configuration: Optional[dict] = Field(default=None, description="Oauth configuration")

    def get_authorizer_configuration(self) -> Optional[dict]:
        """Get the authorizer configuration."""
        return self.authorizer_configuration

    def validate(self, for_local: bool = False) -> List[str]:
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

            # Code zip specific validation (runtime_type is optional, will default to PYTHON_3_11)

        return errors


class BedrockAgentCoreConfigSchema(BaseModel):
    """Project configuration supporting multiple named agents.

    Operations use --agent parameter to select which agent to work with.
    """

    default_agent: Optional[str] = Field(default=None, description="Default agent name for operations")
    agents: Dict[str, BedrockAgentCoreAgentSchema] = Field(
        default_factory=dict, description="Named agent configurations"
    )

    def get_agent_config(self, agent_name: Optional[str] = None) -> BedrockAgentCoreAgentSchema:
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
