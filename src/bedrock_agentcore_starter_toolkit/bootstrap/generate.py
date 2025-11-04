from pathlib import Path
import time

from .features.types import BootstrapSDKProvider, BootstrapIACProvider
from typing import Optional
from .types import ProjectContext, RuntimeProtocol, TemplateDirSelection
from .features import sdk_feature_registry, iac_feature_registry
from ..utils.runtime.container import ContainerRuntime
from ..utils.runtime.schema import AWSConfig, BedrockAgentCoreAgentSchema, MemoryConfig, NetworkConfiguration, NetworkModeConfig, ObservabilityConfig, ProtocolConfiguration
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema
from .baseline_feature import BaselineFeature
from ..cli.common import console
from rich.pretty import Pretty
from ..cli.common import _handle_warn


def generate_project(name: str, sdk_provider: BootstrapSDKProvider, iac_provider: BootstrapIACProvider, agent_config: BedrockAgentCoreAgentSchema | None):

    # create directory structure
    output_path = (Path.cwd() / name)
    output_path.mkdir(exist_ok=False)
    src_path = Path(output_path / "src")
    src_path.mkdir(exist_ok=False)

    ctx = ProjectContext(
        name=name,
        output_dir=output_path,
        src_dir=src_path,
        iac_dir=None, # updated when iac is generated
        sdk_provider=sdk_provider,
        iac_provider=iac_provider,
        template_dir_selection=TemplateDirSelection.Default,
        runtime_protocol=RuntimeProtocol.HTTP,
        python_dependencies=[],
        src_implementation_provided=False,
        agent_name=name + "-Agent",
        # memory
        memory_enabled=True,
        memory_name=name + "_Memory",
        memory_event_expiry_days=30,
        memory_is_long_term=False,
        # custom authorizer
        custom_authorizer_enabled=False,
        custom_authorizer_url=None,
        custom_authorizer_allowed_audience=None,
        custom_authorizer_allowed_clients=None,
        # vpc
        vpc_enabled=False,
        vpc_security_groups=None,
        vpc_subnets=None,
        # observability
        observability_enabled=True
    )

    # resolve above defaults with the configure context if present
    if agent_config:
        resolve_agent_config_with_project_context(ctx, agent_config)

    # ctx is resolved, ready to start generating
    console.print(f"[cyan] Bootstrap generating with the following configuration: [/cyan]")
    console.print(Pretty(ctx))
    time.sleep(5) # give the user a few seconds to read the output before continuing

    if ctx.src_implementation_provided:
        iac_feature_registry[iac_provider]().apply(ctx)
    else:
        baseline_feature = BaselineFeature(ctx.template_dir_selection)
        # source code python dependencies
        deps = set(baseline_feature.python_dependencies)
        if ctx.sdk_provider:
            deps.update(sdk_feature_registry[sdk_provider]().python_dependencies)
        ctx.python_dependencies = sorted(deps)
        
        # render baseline feature
        baseline_feature.apply(ctx)

        # Render sdk/iac templates
        if ctx.sdk_provider:
            sdk_feature_registry[sdk_provider]().apply(ctx)
        iac_feature_registry[iac_provider]().apply(ctx)
        # create dockerfile
        ContainerRuntime().generate_dockerfile(
            agent_path=Path(ctx.src_dir / "main.py"),
            output_dir=ctx.src_dir,
            agent_name=ctx.agent_name, 
            enable_observability=ctx.observability_enabled
        )

def resolve_agent_config_with_project_context(ctx: ProjectContext, agent_config: BedrockAgentCoreAgentSchema):
    """
    Overwrite the default values for functionality that was configured in the configure YAML
    We re-map these configurations from the original BedrockAgentCoreAgentSchema to generate a simple ProjectContext that is easily consumed by Jinja
    """
    ctx.agent_name = agent_config.name
    if agent_config.entrypoint != ".": # bootstrap sets entrypoint to . to indicate that source code should be provided by bootstrap
        ctx.src_implementation_provided = True
        ctx.sdk_provider = None

    aws_config: AWSConfig = agent_config.aws

    # protocol configuration will determine which templates we render
    # mcp_runtime is different enough from default that it gets its own templates
    protocol_configuration: ProtocolConfiguration = aws_config.protocol_configuration
    ctx.runtime_protocol = protocol_configuration.server_protocol
    if protocol_configuration.server_protocol == RuntimeProtocol.MCP:
        ctx.template_dir_selection = TemplateDirSelection.McpRuntime
        if ctx.sdk_provider is not None:
            _handle_warn("In MCP mode, SDK code is not generated")
        ctx.sdk_provider = None
    # no src code support for A2A for now
    if protocol_configuration.server_protocol == RuntimeProtocol.A2A:
        ctx.template_dir_selection = TemplateDirSelection.Default
        if ctx.sdk_provider is not None:
            _handle_warn("In A2A mode, source code is not generated")
        ctx.sdk_provider = None
        ctx.src_implementation_provided = True

    # memory
    memory_config: MemoryConfig = agent_config.memory
    ctx.memory_enabled = memory_config.is_enabled
    ctx.memory_event_expiry_days = memory_config.event_expiry_days
    ctx.memory_is_long_term = memory_config.has_ltm

    # custom authorizer
    authorizer_config: Optional[dict[str, any]] = agent_config.authorizer_configuration
    if authorizer_config:
        ctx.custom_authorizer_enabled = True
        authorizer_config_values = authorizer_config["customJWTAuthorizer"]
        ctx.custom_authorizer_url = authorizer_config_values["discoveryUrl"]
        ctx.custom_authorizer_allowed_clients = authorizer_config_values["allowedClients"]
        ctx.custom_authorizer_allowed_audience = authorizer_config_values["allowedAudience"]

    # vpc
    network_config: NetworkConfiguration = aws_config.network_configuration
    if network_config.network_mode == "VPC":
        ctx.vpc_enabled = True
        network_mode_config: NetworkModeConfig = network_config.network_mode_config
        ctx.vpc_security_groups = network_mode_config.security_groups
        ctx.vpc_subnets = network_mode_config.subnets
    
    # observability
    observability_config: ObservabilityConfig = aws_config.observability
    ctx.observability_enabled = observability_config.enabled