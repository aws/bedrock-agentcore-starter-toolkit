from pathlib import Path
from ...features.base_feature import Feature
from ...features.types import BootstrapIACProvider
from ...types import ProjectContext

class TerraformFeature(Feature):
    name = BootstrapIACProvider.Terraform.value

    def before_apply(self, context: ProjectContext):
        context.iac_dir = context.output_dir

    def execute(self, context: ProjectContext) -> None:
        self.render_dir(context.iac_dir, context)

    def after_apply(self, context: ProjectContext):
        pass