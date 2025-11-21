"""Project generation orchestration for Bedrock Agent Core starter projects."""

from pathlib import Path

from ..cli.common import _handle_warn
from ..utils.python_env import is_recommended_python_version
from ..utils.runtime.container import ContainerRuntime
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema
from .baseline_feature import BaselineFeature
from .configure.resolve import (
    resolve_agent_config_with_project_context,
)
from .constants import DeploymentType, ModelProvider, RuntimeProtocol, TemplateDirSelection
from .features import iac_feature_registry, sdk_feature_registry
from .progress.progress_sink import ProgressSink
from .types import CreateIACProvider, CreateModelProvider, CreateSDKProvider, ProjectContext
from .util.console_print import emit_create_completed_message
from .util.create_agentcore_yaml import write_minimal_create_runtime_yaml, write_minimal_create_with_iac_project_yaml
from .util.dotenv import _write_env_file_directly
from .util.post_generate_venv import create_and_init_venv


def generate_project(
    name: str,
    sdk_provider: CreateSDKProvider,
    iac_provider: CreateIACProvider | None,
    model_provider: CreateModelProvider | None,
    provider_api_key: str | None,
    agent_config: BedrockAgentCoreAgentSchema | None,
    use_venv: bool,
):
    """Generate a new Bedrock Agent Core project with specified SDK and IaC providers."""
    sink = ProgressSink()

    # create directory structure
    output_path = Path.cwd() / name
    output_path.mkdir(exist_ok=False)
    src_path = Path(output_path / "src")
    src_path.mkdir(exist_ok=False)

    # the ProjectContext defines what is generated. It is passed into the jinja templates that are rendered.
    # start with common settings. The rest will auto populate
    template_dir: TemplateDirSelection = (
        TemplateDirSelection.MONOREPO if iac_provider else TemplateDirSelection.RUNTIME_ONLY
    )
    deployment_type: DeploymentType = DeploymentType.CONTAINER if iac_provider else DeploymentType.DIRECT_CODE_DEPLOY
    api_key_name = (
        f"{model_provider.upper()}_API_KEY" if model_provider and model_provider != ModelProvider.Bedrock else None
    )
    ctx = ProjectContext(
        # high level project config
        name=name,
        output_dir=output_path,
        src_dir=src_path,
        entrypoint_path=Path(src_path / "main.py"),
        iac_dir=None,  # updated when iac is generated
        sdk_provider=sdk_provider,
        iac_provider=iac_provider,
        model_provider=model_provider,
        deployment_type=deployment_type,
        template_dir_selection=template_dir,
        runtime_protocol=RuntimeProtocol.HTTP,
        python_dependencies=[],
        agent_name=name + "_Agent",
        api_key_env_var_name=api_key_name,
    )
    # override IAC specific settings
    if iac_provider:
        ctx.memory_enabled = True
        ctx.memory_name = name + "_Memory"
        ctx.memory_event_expiry_days = 30
        ctx.memory_is_long_term = False
        # custom authorizer
        ctx.custom_authorizer_enabled = False
        ctx.custom_authorizer_url = None
        ctx.custom_authorizer_allowed_audience = None
        ctx.custom_authorizer_allowed_clients = None
        # vpc
        ctx.vpc_enabled = False
        ctx.vpc_security_groups = None
        ctx.vpc_subnets = None
        # request header
        ctx.request_header_allowlist = None
        # observability
        ctx.observability_enabled = True

    with sink.step("Template copying", "Template copied"):
        _apply_baseline_and_sdk_features(ctx)

        if not ctx.iac_provider:
            ctx.memory_enabled = False
            write_minimal_create_runtime_yaml(ctx)
            # Write .env file for non-Bedrock providers (outside template system for security)
            # Always write if model provider requires API key, even if empty (user can fill in later)
            if ctx.model_provider and ctx.model_provider != ModelProvider.Bedrock:
                _write_env_file_directly(ctx.output_dir, ctx.model_provider, provider_api_key)
        else:
            _apply_iac_generation(ctx, agent_config)
            write_minimal_create_with_iac_project_yaml(ctx)
    # we have a project... create a venv install deps
    if use_venv:
        create_and_init_venv(ctx, sink=sink)
    _emit_python_version_warning_if_applicable(ctx)
    # everything is done emit the blue success panel
    emit_create_completed_message(ctx)


def _apply_baseline_and_sdk_features(ctx: ProjectContext) -> None:
    """Apply baseline and SDK features, collecting dependencies from both.

    This common method handles:
    1. Creating baseline feature for the template directory
    2. Collecting python dependencies from baseline and SDK features
    3. Applying baseline feature (renders pyproject.toml, etc.)
    4. Applying SDK feature (renders SDK-specific templates)
    """
    baseline_feature = BaselineFeature(ctx)

    # Collect python dependencies from baseline and SDK
    deps = set(baseline_feature.python_dependencies)
    sdk_feature = None
    if ctx.sdk_provider:
        # Get SDK feature instance to access its dependencies
        sdk_feature = sdk_feature_registry[ctx.sdk_provider]()
        # Call before_apply to ensure dependencies are set correctly based on model provider
        sdk_feature.before_apply(ctx)
        deps.update(sdk_feature.python_dependencies)

    ctx.python_dependencies = sorted(deps)

    # Apply baseline feature (renders common templates like pyproject.toml)
    baseline_feature.apply(ctx)

    # Apply SDK feature (renders SDK-specific templates)
    if sdk_feature:
        sdk_feature.apply(ctx)


def _apply_iac_generation(ctx: ProjectContext, agent_config) -> None:
    if agent_config:
        resolve_agent_config_with_project_context(ctx, agent_config)
    iac_feature_registry[ctx.iac_provider]().apply(ctx)
    # create dockerfile
    ContainerRuntime().generate_dockerfile(
        agent_path=ctx.entrypoint_path,
        output_dir=ctx.output_dir,
        explicit_requirements_file=ctx.output_dir / "pyproject.toml",
        agent_name=ctx.agent_name,
        enable_observability=ctx.observability_enabled,
    )


def _emit_python_version_warning_if_applicable(ctx: ProjectContext):
    """With direct code deploy, there are platform/library compatibility concerns."""
    if ctx.deployment_type == DeploymentType.DIRECT_CODE_DEPLOY:
        deployment_string = "agentcore launch" if not ctx.iac_provider else "deploying"
        recommended, version = is_recommended_python_version()
        if not recommended:
            _handle_warn(
                f"Detected python version: {version}. For AgentCore runtime "
                f"platform compatibility switch to Python 3.10 before running {deployment_string}"
            )
