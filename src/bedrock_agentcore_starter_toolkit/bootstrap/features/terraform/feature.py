"""Terraform IaC."""

from pathlib import Path

from ...constants import IACProvider
from ...features.base_feature import Feature
from ...types import ProjectContext


class TerraformFeature(Feature):
    """Implements Terraform code generation."""

    feature_dir_name = IACProvider.TERRAFORM

    def before_apply(self, context: ProjectContext):
        """Create Terraform IaC dir if it doesnt exist."""
        iac_dir = Path(context.output_dir / "terraform")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

    def execute(self, context: ProjectContext) -> None:
        """Call render_dir."""
        self.render_dir(context.iac_dir, context)

    def after_apply(self, context):
        pass