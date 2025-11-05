from ...types import ProjectContext
from ...constants import SDKProvider
from ..base_feature import Feature

class OpenAIAgentsFeature(Feature):
    feature_dir_name = SDKProvider.OPENAI_AGENTS
    python_dependencies = ["openai-agents>=0.4.2"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)