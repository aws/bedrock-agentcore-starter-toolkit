"""Pydantic models for operation requests and responses."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ...utils.runtime.container import ContainerRuntime


# Configure operation models
class ConfigureResult(BaseModel):
    """Result of configure operation."""

    config_path: Path = Field(..., description="Path to configuration file")
    dockerfile_path: Optional[Path] = Field(None, description="Path to generated Dockerfile")
    dockerignore_path: Optional[Path] = Field(None, description="Path to generated .dockerignore")
    runtime: Optional[str] = Field(None, description="Container runtime name")
    runtime_type: Optional[str] = Field(None, description="Python runtime version for direct_code_deploy")
    region: str = Field(..., description="AWS region")
    account_id: str = Field(..., description="AWS account ID")
    execution_role: Optional[str] = Field(None, description="AWS execution role ARN")
    ecr_repository: Optional[str] = Field(None, description="ECR repository URI")
    auto_create_ecr: bool = Field(False, description="Whether ECR will be auto-created")
    s3_path: Optional[str] = Field(None, description="S3 URI")
    auto_create_s3: bool = Field(False, description="Whether S3 bucket will be auto-created")
    memory_id: Optional[str] = Field(default=None, description="Memory resource ID if created")
    network_mode: Optional[str] = Field(None, description="Network mode (PUBLIC or VPC)")
    network_subnets: Optional[List[str]] = Field(None, description="VPC subnet IDs")
    network_security_groups: Optional[List[str]] = Field(None, description="VPC security group IDs")
    network_vpc_id: Optional[str] = Field(None, description="VPC ID")


# Launch operation models
class LaunchResult(BaseModel):
    """Result of launch operation."""

    mode: str = Field(..., description="Launch mode: local, cloud, or codebuild")
    tag: Optional[str] = Field(default=None, description="Docker image tag (container deployments only)")
    env_vars: Optional[Dict[str, str]] = Field(default=None, description="Environment variables for local deployment")

    # Local mode fields
    port: Optional[int] = Field(default=None, description="Port for local deployment")
    runtime: Optional[ContainerRuntime] = Field(default=None, description="Container runtime instance")

    # Cloud mode fields
    ecr_uri: Optional[str] = Field(default=None, description="ECR repository URI")
    agent_id: Optional[str] = Field(default=None, description="BedrockAgentCore agent ID")
    agent_arn: Optional[str] = Field(default=None, description="BedrockAgentCore agent ARN")

    # CodeBuild mode fields
    codebuild_id: Optional[str] = Field(default=None, description="CodeBuild build ID for ARM64 builds")

    # Build output (optional)
    build_output: Optional[List[str]] = Field(default=None, description="Docker build output")

    model_config = ConfigDict(arbitrary_types_allowed=True)  # For runtime field


class InvokeResult(BaseModel):
    """Result of invoke operation."""

    response: Dict[str, Any] = Field(..., description="Response from Bedrock AgentCore endpoint")
    session_id: str = Field(..., description="Session ID used for invocation")
    agent_arn: Optional[str] = Field(default=None, description="BedrockAgentCore agent ARN")


# Status operation models
class StatusConfigInfo(BaseModel):
    """Configuration information for status."""

    name: str = Field(..., description="Bedrock AgentCore application name")
    entrypoint: str = Field(..., description="Entrypoint file path")
    region: Optional[str] = Field(None, description="AWS region")
    account: Optional[str] = Field(None, description="AWS account ID")
    execution_role: Optional[str] = Field(None, description="AWS execution role ARN")
    ecr_repository: Optional[str] = Field(None, description="ECR repository URI")
    agent_id: Optional[str] = Field(None, description="BedrockAgentCore agent ID")
    agent_arn: Optional[str] = Field(None, description="BedrockAgentCore agent ARN")
    network_mode: Optional[str] = None
    network_subnets: Optional[List[str]] = None
    network_security_groups: Optional[List[str]] = None
    network_vpc_id: Optional[str] = None
    memory_id: Optional[str] = Field(None, description="Memory resource ID")
    memory_status: Optional[str] = Field(None, description="Memory provisioning status (CREATING/ACTIVE/FAILED)")
    memory_type: Optional[str] = Field(None, description="Memory type (STM or STM+LTM)")
    memory_enabled: Optional[bool] = Field(None, description="Whether memory is enabled")
    memory_strategies: Optional[List[str]] = Field(None, description="Active memory strategies")
    memory_details: Optional[Dict[str, Any]] = Field(None, description="Detailed memory resource information")
    idle_timeout: Optional[int] = Field(None, description="Idle runtime session timeout in seconds")
    max_lifetime: Optional[int] = Field(None, description="Maximum instance lifetime in seconds")


class StatusResult(BaseModel):
    """Result of status operation."""

    config: StatusConfigInfo = Field(..., description="Configuration information")
    agent: Optional[Dict[str, Any]] = Field(None, description="Agent runtime details or error")
    endpoint: Optional[Dict[str, Any]] = Field(None, description="Endpoint details or error")


class DestroyResult(BaseModel):
    """Result of destroy operation."""

    agent_name: str = Field(..., description="Name of the destroyed agent")
    resources_removed: List[str] = Field(default_factory=list, description="List of removed AWS resources")
    warnings: List[str] = Field(default_factory=list, description="List of warnings during destruction")
    errors: List[str] = Field(default_factory=list, description="List of errors during destruction")
    dry_run: bool = Field(default=False, description="Whether this was a dry run")


class StopSessionResult(BaseModel):
    """Result of stop session operation."""

    session_id: str = Field(..., description="Session ID that was stopped")
    agent_name: str = Field(..., description="Name of the agent")
    status_code: int = Field(..., description="HTTP status code of the operation")
    message: str = Field(default="Session stopped successfully", description="Result message")
