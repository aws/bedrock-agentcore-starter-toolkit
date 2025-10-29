from pathlib import Path

from .features.types import BootstrapFeature
from typing import List, Optional
from .types import ProjectContext
from .features import feature_registry
from .constants import COMMON_PYTHON_DEPENDENCIES
from ..utils.runtime.container import ContainerRuntime
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema, MemoryConfig
from .features.base_feature import Feature
from ..utils.runtime.schema import BedrockAgentCoreAgentSchema

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
        memory_name=name + "-Memory",
        memory_enabled=True,
        memory_event_expiry_days=30,
        memory_short_term_only=False,
        memory_short_and_long_term=False,
        # custom authorizer
        custom_authorizer_enabled=False,
        custom_authorizer_url=None,
        custom_authorizer_allowed_audience=None,
        custom_authorizer_allowed_clients=None,
    )

    # resolve above defaults with the configure context if present
    if agent_config:
        resolve_agent_config_with_project_context(ctx, agent_config)

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

    ContainerRuntime().generate_dockerfile(agent_path=Path(ctx.src_dir / "main.py"), output_dir=ctx.src_dir, agent_name=ctx.agent_name)


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

# small class to extract the common templates under the bootstrap/ dir and write them to the output dir
class CommonFeatures(Feature):
    name = "bootstrap"
    template_override_dir = Path(__file__).parent / "templates"
    def execute(self, context):
        self.render_dir(context.output_dir, context)
    