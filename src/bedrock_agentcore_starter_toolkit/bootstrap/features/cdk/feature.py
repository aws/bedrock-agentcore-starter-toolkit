"""CDK Feature."""

from pathlib import Path

from ...constants import IACProvider
from ...features.base_feature import Feature
from ...types import ProjectContext


class CDKFeature(Feature):
    """Implements CDK code generation."""

    feature_dir_name = IACProvider.CDK
    render_common_dir = True

    def before_apply(self, context: ProjectContext):
        """Create CDK directory before code gen."""
        iac_dir = Path(context.output_dir / "cdk")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

    def execute(self, context: ProjectContext) -> None:
        """Call render_dir."""
        self.render_dir(context.iac_dir, context)
