"""Pydantic models for operation requests and responses."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ...utils.runtime.container import ContainerRuntime


# Configure operation models
class ConfigureResult(BaseModel):
    """Result of configure operation."""

    config_path: Path = Field(..., description="Path to configuration file")
    dockerfile_path: Path = Field(..., description="Path to generated Dockerfile")
    dockerignore_path: Optional[Path] = Field(None, description="Path to generated .dockerignore")
    runtime: str = Field(..., description="Container runtime name")
    region: str = Field(..., description="AWS region")
    account_id: str = Field(..., description="AWS account ID")
    execution_role: Optional[str] = Field(None, description="AWS execution role ARN")
    ecr_repository: Optional[str] = Field(None, description="ECR repository URI")
    auto_create_ecr: bool = Field(False, description="Whether ECR will be auto-created")


# Launch operation models
class LaunchResult(BaseModel):
    """Result of launch operation."""

    mode: str = Field(..., description="Launch mode: local, cloud, or codebuild")
    tag: str = Field(..., description="Docker image tag")
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
