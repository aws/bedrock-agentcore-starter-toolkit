from pathlib import Path
from ...features.base_feature import Feature
from ...features.types import BootstrapIACProvider
from ...types import ProjectContext

class TerraformFeature(Feature):
    name = BootstrapIACProvider.Terraform.value

    def before_apply(self, context: ProjectContext):

        # create output dir
        iac_dir = Path(context.output_dir / "terraform")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

    def execute(self, context):
        return self.render_dir(context.iac_dir, context)