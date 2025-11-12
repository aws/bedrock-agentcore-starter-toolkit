"""Strands SDK Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class StrandsFeature(Feature):
    """Implements Strands code generation."""

    feature_dir_name = SDKProvider.STRANDS
    python_dependencies = ["strands-agents >= 1.13.0", "mcp >= 1.19.0"]

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        pass

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
