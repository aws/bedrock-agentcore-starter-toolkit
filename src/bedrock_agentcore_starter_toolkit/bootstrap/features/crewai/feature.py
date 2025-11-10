"""CrewAI Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class CrewAIFeature(Feature):
    """Implements CrewAI code generation."""

    feature_dir_name = SDKProvider.CREWAI
    python_dependencies = ["crewai[tools]>=1.3.0", "crewai-tools[mcp]>=1.3.0", "mcp>=1.20.0"]

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
