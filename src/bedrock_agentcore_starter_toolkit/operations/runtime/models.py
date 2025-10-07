"""Pydantic models for operation requests and responses."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ...utils.runtime.container import ContainerRuntime


# Configure operation models
class ConfigureResult(BaseModel):
    """Result of configure operation."""

    config_path: Path = Field(..., description="Path to configuration file")
    dockerfile_path: Path = Field(..., description="Path to generated Dockerfile")
    dockerignore_path: Path | None = Field(None, description="Path to generated .dockerignore")
    runtime: str = Field(..., description="Container runtime name")
    region: str = Field(..., description="AWS region")
    account_id: str = Field(..., description="AWS account ID")
    execution_role: str | None = Field(None, description="AWS execution role ARN")
    ecr_repository: str | None = Field(None, description="ECR repository URI")
    auto_create_ecr: bool = Field(False, description="Whether ECR will be auto-created")
    memory_id: str | None = Field(default=None, description="Memory resource ID if created")


# Launch operation models
class LaunchResult(BaseModel):
    """Result of launch operation."""

    mode: str = Field(..., description="Launch mode: local, cloud, or codebuild")
    tag: str = Field(..., description="Docker image tag")
    env_vars: dict[str, str] | None = Field(default=None, description="Environment variables for local deployment")

    # Local mode fields
    port: int | None = Field(default=None, description="Port for local deployment")
    runtime: ContainerRuntime | None = Field(default=None, description="Container runtime instance")

    # Cloud mode fields
    ecr_uri: str | None = Field(default=None, description="ECR repository URI")
    agent_id: str | None = Field(default=None, description="BedrockAgentCore agent ID")
    agent_arn: str | None = Field(default=None, description="BedrockAgentCore agent ARN")

    # CodeBuild mode fields
    codebuild_id: str | None = Field(default=None, description="CodeBuild build ID for ARM64 builds")

    # Build output (optional)
    build_output: list[str] | None = Field(default=None, description="Docker build output")

    model_config = ConfigDict(arbitrary_types_allowed=True)  # For runtime field


class InvokeResult(BaseModel):
    """Result of invoke operation."""

    response: dict[str, Any] = Field(..., description="Response from Bedrock AgentCore endpoint")
    session_id: str = Field(..., description="Session ID used for invocation")
    agent_arn: str | None = Field(default=None, description="BedrockAgentCore agent ARN")


# Status operation models
class StatusConfigInfo(BaseModel):
    """Configuration information for status."""

    name: str = Field(..., description="Bedrock AgentCore application name")
    entrypoint: str = Field(..., description="Entrypoint file path")
    region: str | None = Field(None, description="AWS region")
    account: str | None = Field(None, description="AWS account ID")
    execution_role: str | None = Field(None, description="AWS execution role ARN")
    ecr_repository: str | None = Field(None, description="ECR repository URI")
    agent_id: str | None = Field(None, description="BedrockAgentCore agent ID")
    agent_arn: str | None = Field(None, description="BedrockAgentCore agent ARN")
    memory_id: str | None = Field(None, description="Memory resource ID")
    memory_status: str | None = Field(None, description="Memory provisioning status (CREATING/ACTIVE/FAILED)")
    memory_type: str | None = Field(None, description="Memory type (STM or STM+LTM)")
    memory_enabled: bool | None = Field(None, description="Whether memory is enabled")
    memory_strategies: list[str] | None = Field(None, description="Active memory strategies")
    memory_details: dict[str, Any] | None = Field(None, description="Detailed memory resource information")


class StatusResult(BaseModel):
    """Result of status operation."""

    config: StatusConfigInfo = Field(..., description="Configuration information")
    agent: dict[str, Any] | None = Field(None, description="Agent runtime details or error")
    endpoint: dict[str, Any] | None = Field(None, description="Endpoint details or error")


class DestroyResult(BaseModel):
    """Result of destroy operation."""

    agent_name: str = Field(..., description="Name of the destroyed agent")
    resources_removed: list[str] = Field(default_factory=list, description="List of removed AWS resources")
    warnings: list[str] = Field(default_factory=list, description="List of warnings during destruction")
    errors: list[str] = Field(default_factory=list, description="List of errors during destruction")
    dry_run: bool = Field(default=False, description="Whether this was a dry run")
