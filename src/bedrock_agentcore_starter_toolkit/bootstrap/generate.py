from pathlib import Path
import time

from .features.types import BootstrapFeature
from typing import List, Optional
from .types import ProjectContext
from .features import feature_registry
from .constants import COMMON_PYTHON_DEPENDENCIES
from ..utils.runtime.container import ContainerRuntime
from ..utils.runtime.schema import AWSConfig, BedrockAgentCoreAgentSchema, MemoryConfig, NetworkConfiguration, NetworkModeConfig, ObservabilityConfig
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema
from .common_features import CommonFeatures
from ..cli.common import console
from rich.pretty import Pretty


def generate_project(name: str, features: List[BootstrapFeature], agent_config: BedrockAgentCoreAgentSchema | None):

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
        features=features,
        python_dependencies=[],
        agent_name=name + "-Agent",
        # memory
        memory_enabled=True,
        memory_name=name + "_Memory",
        memory_event_expiry_days=30,
        memory_short_term_only=False,
        memory_short_and_long_term=False,
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

    # Collect dependencies from features, starting with common deps
    deps = set(COMMON_PYTHON_DEPENDENCIES)
    for feature in ctx.features:
        feature_cls = feature_registry[feature]
        deps.update(feature_cls().python_dependencies)
    ctx.python_dependencies = sorted(deps)

    # Render common templates
    CommonFeatures().apply(ctx)

    # Render feature templates
    for feature in ctx.features:
        instance = feature_registry[feature]()
        instance.apply(ctx)   

    # create docker file with settings from ctx
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

    # memory
    memory_config: MemoryConfig = agent_config.memory
    ctx.memory_enabled = memory_config.is_enabled
    ctx.memory_event_expiry_days = memory_config.event_expiry_days
    ctx.memory_short_and_long_term = memory_config.has_ltm
    ctx.memory_short_term_only = memory_config.mode == "STM_ONLY"

    # custom authorizer
    authorizer_config: Optional[dict[str, any]] = agent_config.authorizer_configuration
    if authorizer_config:
        ctx.custom_authorizer_enabled = True
        authorizer_config_values = authorizer_config["customJWTAuthorizer"]
        ctx.custom_authorizer_url = authorizer_config_values["discoveryUrl"]
        ctx.custom_authorizer_allowed_clients = authorizer_config_values["allowedClients"]
        ctx.custom_authorizer_allowed_audience = authorizer_config_values["allowedAudience"]

    # vpc
    aws_config: AWSConfig = agent_config.aws
    network_config: NetworkConfiguration = aws_config.network_configuration
    if network_config.network_mode == "VPC":
        ctx.vpc_enabled = True
        network_mode_config: NetworkModeConfig = network_config.network_mode_config
        ctx.vpc_security_groups = network_mode_config.security_groups
        ctx.vpc_subnets = network_mode_config.subnets
    
    # observability
    observability_config: ObservabilityConfig = aws_config.observability
    ctx.observability_enabled = observability_config.enabled