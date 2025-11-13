"""Implementation for create command to be compatible with the outputs from the configure command."""

import shutil
from pathlib import Path
from typing import Optional

from ...cli.common import _handle_warn
from ...utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    MemoryConfig,
    NetworkConfiguration,
    NetworkModeConfig,
    ObservabilityConfig,
    ProtocolConfiguration,
)
from ..constants import IACProvider, RuntimeProtocol, TemplateDirSelection
from ..types import ProjectContext


def resolve_agent_config_with_project_context(ctx: ProjectContext, agent_config: BedrockAgentCoreAgentSchema):
    """Overwrite the default values for functionality that was configured in the configuration YAML.

    We re-map these configurations from the original BedrockAgentCoreAgentSchema to generate a simple
    ProjectContext that is easily consumed by Jinja
    """
    ctx.agent_name = agent_config.name
    if (
        agent_config.entrypoint != "."
    ):  # create sets entrypoint to . to indicate that source code should be provided by create
        ctx.src_implementation_provided = True
        ctx.sdk_provider = None
        ctx.entrypoint_path = agent_config.entrypoint

    aws_config: AWSConfig = agent_config.aws

    # protocol configuration will determine which templates we render
    # mcp_runtime is different enough from default that it gets its own templates
    protocol_configuration: ProtocolConfiguration = aws_config.protocol_configuration
    ctx.runtime_protocol = protocol_configuration.server_protocol
    if protocol_configuration.server_protocol == RuntimeProtocol.MCP:
        ctx.template_dir_selection = TemplateDirSelection.MCP_RUNTIME
        if ctx.sdk_provider is not None:
            _handle_warn("In MCP mode, SDK code is not generated")
        ctx.sdk_provider = None
    # no src code support for A2A for now
    if protocol_configuration.server_protocol == RuntimeProtocol.A2A:
        ctx.template_dir_selection = TemplateDirSelection.DEFAULT
        if ctx.sdk_provider is not None:
            _handle_warn("In A2A mode, source code is not generated")
        ctx.sdk_provider = None
        ctx.src_implementation_provided = True

    # memory
    memory_config: MemoryConfig = agent_config.memory
    ctx.memory_enabled = memory_config.is_enabled
    ctx.memory_event_expiry_days = memory_config.event_expiry_days
    ctx.memory_is_long_term = memory_config.has_ltm
    if memory_config.memory_name:
        ctx.memory_name = memory_config.memory_name

    # custom authorizer
    authorizer_config: Optional[dict[str, any]] = agent_config.authorizer_configuration
    if authorizer_config:
        ctx.custom_authorizer_enabled = True
        authorizer_config_values = authorizer_config["customJWTAuthorizer"]
        ctx.custom_authorizer_url = authorizer_config_values["discoveryUrl"]
        ctx.custom_authorizer_allowed_clients = authorizer_config_values["allowedClients"]
        ctx.custom_authorizer_allowed_audience = authorizer_config_values.get("allowedAudience", [])

    # vpc
    network_config: NetworkConfiguration = aws_config.network_configuration
    if network_config.network_mode == "VPC":
        ctx.vpc_enabled = True
        network_mode_config: NetworkModeConfig = network_config.network_mode_config
        ctx.vpc_security_groups = network_mode_config.security_groups
        ctx.vpc_subnets = network_mode_config.subnets

    # request header
    if agent_config.request_header_configuration:
        if ctx.iac_provider == IACProvider.CDK:
            _handle_warn(
                "Request header allowlist is not supported by CDK so it won't be included in the generated code"
            )
        else:
            ctx.request_header_allowlist = agent_config.request_header_configuration["requestHeaderAllowlist"]

    # observability
    observability_config: ObservabilityConfig = aws_config.observability
    ctx.observability_enabled = observability_config.enabled


def copy_src_implementation_and_docker_config_into_monorepo(
    agent_config: BedrockAgentCoreAgentSchema, ctx: ProjectContext
):
    """Handles:.

    1. copying over the contents of the provided src code into the monorepo
    2. copying the Dockerfile and .dockerignore into the root of the monorepo because configure assumes this structure
    when Dockerfile is generated

    """
    # copy over everything in the current working directory except reserved directories
    skip_dir = {".bedrock_agentcore", ctx.name}
    skip_file = {".bedrock_agentcore.yaml", ".bedrock_agentcore.YAML"}
    cwd = Path.cwd()

    # take snapshot first — avoids seeing newly copied files
    entries = list(cwd.iterdir())
    for item in entries:
        if item.is_file() and item.name in skip_file:
            continue
        if item.is_dir() and item.name in skip_dir:
            continue
        target = ctx.src_dir / item.name
        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
                ignore=lambda src, names: [n for n in names if n.lower() == ".dockerignore"],
            )
        else:
            shutil.copy2(item, target)

    # Move Dockerfile and .dockerignore from configure’s output
    agentcore_dir = cwd / ".bedrock_agentcore" / agent_config.name

    src_root = Path(agent_config.source_path)
    if not src_root.is_absolute():
        src_root = (Path.cwd() / src_root).resolve()

    dockerfile_src = agentcore_dir / "Dockerfile"
    dockerignore_src = src_root / ".dockerignore"  # original path

    dockerfile_dst = ctx.src_dir / "Dockerfile"
    dockerignore_dst = ctx.src_dir / ".dockerignore"

    shutil.copy2(dockerfile_src, dockerfile_dst)
    shutil.copy2(dockerignore_src, dockerignore_dst)
