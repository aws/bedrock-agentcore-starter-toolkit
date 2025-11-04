from pathlib import Path

from ...features.base_feature import Feature
from ...features.types import BootstrapIACProvider
from ...types import ProjectContext

class CDKFeature(Feature):
    feature_dir_name = BootstrapIACProvider.CDK.value
    render_common_dir = True

    def before_apply(self, context: ProjectContext):
        # create output dir
        iac_dir = Path(context.output_dir / "cdk")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

    def execute(self, context: ProjectContext) -> None:
        self.render_dir(context.iac_dir, context)

    def after_apply(self, context: ProjectContext):
        pass