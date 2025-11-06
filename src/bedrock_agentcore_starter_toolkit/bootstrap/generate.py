from pathlib import Path
import time

from .types import ProjectContext, BootstrapSDKProvider, BootstrapIACProvider
from .constants import RuntimeProtocol, TemplateDirSelection
from .features import sdk_feature_registry, iac_feature_registry
from ..utils.runtime.container import ContainerRuntime
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema
from .baseline_feature import BaselineFeature
from ..cli.common import console
from rich.pretty import Pretty
from .configure.configure_utils import copy_src_implementation_and_docker_config_into_monorepo, resolve_agent_config_with_project_context

def generate_project(name: str, sdk_provider: BootstrapSDKProvider, iac_provider: BootstrapIACProvider, agent_config: BedrockAgentCoreAgentSchema | None):

    # create directory structure
    output_path = (Path.cwd() / name)
    output_path.mkdir(exist_ok=False)
    src_path = Path(output_path / "src")
    src_path.mkdir(exist_ok=False)

    ctx = ProjectContext(
        # high level project config
        name=name,
        output_dir=output_path,
        src_dir=src_path,
        entrypoint_path=Path(src_path / "main.py"),
        iac_dir=None, # updated when iac is generated
        sdk_provider=sdk_provider,
        iac_provider=iac_provider,
        template_dir_selection=TemplateDirSelection.DEFAULT,
        runtime_protocol=RuntimeProtocol.HTTP,
        python_dependencies=[],
        src_implementation_provided=False,
        agent_name=name + "_Agent",
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
        # request header
        request_header_allowlist=None,
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
        # copy over runtime code and just apply the IAC feature
        copy_src_implementation_and_docker_config_into_monorepo(agent_config, ctx)
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
            agent_path=ctx.entrypoint_path,
            output_dir=ctx.src_dir,
            explicit_requirements_file=ctx.src_dir / "pyproject.toml",
            agent_name=ctx.agent_name,
            enable_observability=ctx.observability_enabled
        )
