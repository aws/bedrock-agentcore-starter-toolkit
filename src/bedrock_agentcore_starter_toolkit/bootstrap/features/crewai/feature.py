from ...types import ProjectContext
from ..types import BootstrapSDKProvider
from ..base_feature import Feature

class CrewAIFeature(Feature):
    feature_dir_name = BootstrapSDKProvider.CrewAI.value
    python_dependencies = ["crewai[tools]>=1.3.0"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)