"""Google ADK Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class GoogleADKFeature(Feature):
    """Implements Google ADK code generation."""

    feature_dir_name = SDKProvider.GOOGLE_ADK
    python_dependencies = ["google-adk>=1.17.0"]

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)

    def before_apply(self, context):
        pass
    
    def after_apply(self, context):
        pass