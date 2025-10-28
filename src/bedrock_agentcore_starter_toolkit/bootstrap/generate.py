from pathlib import Path

from .features.types import BootstrapFeature
from typing import List
from .types import ProjectContext
from .features import feature_registry
from .constants import COMMON_PYTHON_DEPENDENCIES
from ..utils.runtime.container import ContainerRuntime
from .features.base_feature import Feature

def generate_project(name: str, features: List[BootstrapFeature]):

    # create directory structure
    output_path = (Path.cwd() / name)
    output_path.mkdir(exist_ok=False)
    src_path = Path(output_path / "src")
    src_path.mkdir(exist_ok=False)

    ctx = ProjectContext(
        name=name,
        output_dir=output_path,
        src_dir=src_path,
        features=features,
        python_dependencies=[],
    )

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

    ContainerRuntime().generate_dockerfile(agent_path=Path(ctx.src_dir / "main.py"), output_dir=ctx.output_dir, agent_name=f"{ctx.name}-agent")
    
# small class to extract the common templates under the bootstrap/ dir and write them to the output dir
class CommonFeatures(Feature):
    name = "bootstrap"
    template_override_dir = Path(__file__).parent / "templates"
    def execute(self, context):
        self.render_dir(context.output_dir, context)
    