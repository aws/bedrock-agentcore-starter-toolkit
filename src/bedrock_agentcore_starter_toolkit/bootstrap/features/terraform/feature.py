from pathlib import Path
from ...features.base_feature import Feature
from ...constants import IACProvider
from ...types import ProjectContext

class TerraformFeature(Feature):
    feature_dir_name = IACProvider.TERRAFORM

    def before_apply(self, context: ProjectContext):
        iac_dir = Path(context.output_dir / "terraform")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

    def execute(self, context: ProjectContext) -> None:
        self.render_dir(context.iac_dir, context)

    def after_apply(self, context: ProjectContext):
        pass