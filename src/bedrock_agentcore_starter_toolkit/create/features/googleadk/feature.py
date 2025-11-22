"""Google ADK Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class GoogleADKFeature(Feature):
    """Implements Google ADK code generation."""

    feature_dir_name = SDKProvider.GOOGLE_ADK
    python_dependencies = ["google-adk>=1.17.0"]

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        from ...constants import TemplateDirSelection

        if context.template_dir_selection == TemplateDirSelection.RUNTIME_ONLY:
            self.model_provider_name = context.model_provider.lower()

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
