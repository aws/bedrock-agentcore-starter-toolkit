"""Implementation for create command to be compatible with the outputs from the configure command."""

from typing import Optional

from ...cli.common import _handle_error, _handle_warn
from ...utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    MemoryConfig,
    NetworkConfiguration,
    NetworkModeConfig,
    ObservabilityConfig,
    ProtocolConfiguration,
)
from ..constants import IACProvider, RuntimeProtocol
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
        _handle_error("agentcore create cannot support existing source code with a bedrock_agentcore.yaml")

    aws_config: AWSConfig = agent_config.aws

    # protocol configuration will determine which templates we render
    # mcp_runtime is different enough from default that it gets its own templates
    protocol_configuration: ProtocolConfiguration = aws_config.protocol_configuration
    ctx.runtime_protocol = protocol_configuration.server_protocol
    if protocol_configuration.server_protocol != RuntimeProtocol.HTTP:
        _handle_error("Only HTTP Protocol is supported by agentcore create --iac")

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
