from ...types import ProjectContext
from ...constants import SDKProvider
from ..base_feature import Feature

class CrewAIFeature(Feature):
    feature_dir_name = SDKProvider.CREWAI
    python_dependencies = ["crewai[tools]>=1.3.0","crewai-tools[mcp]>=1.3.0","mcp>=1.20.0"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)