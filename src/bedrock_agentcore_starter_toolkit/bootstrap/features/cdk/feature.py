from pathlib import Path

from ...features.base_feature import Feature
from ...types import ProjectContext
from ...constants import IACProvider

class CDKFeature(Feature):
    feature_dir_name = IACProvider.CDK
    render_common_dir = True

    def before_apply(self, context: ProjectContext):
        # create output dir
        iac_dir = Path(context.output_dir / "cdk")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

    def execute(self, context: ProjectContext) -> None:
        self.render_dir(context.iac_dir, context)