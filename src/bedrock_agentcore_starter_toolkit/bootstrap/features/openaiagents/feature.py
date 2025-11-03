from ...types import ProjectContext
from ..types import BootstrapSDKProvider
from ..base_feature import Feature

class OpenAIAgentsFeature(Feature):
    feature_dir_name = BootstrapSDKProvider.OpenAIAgents.value
    python_dependencies = ["openai-agents>=0.4.2"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)