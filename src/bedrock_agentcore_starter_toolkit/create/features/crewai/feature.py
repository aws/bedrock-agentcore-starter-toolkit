"""CrewAI Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class CrewAIFeature(Feature):
    """Implements CrewAI code generation."""

    feature_dir_name = SDKProvider.CREWAI
    python_dependencies = ["crewai[tools]>=1.3.0", "crewai-tools[mcp]>=1.3.0", "mcp>=1.20.0"]

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        pass

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
