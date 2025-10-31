from ...types import ProjectContext
from ..types import BootstrapSDKProvider
from ..base_feature import Feature

class LangGraphFeature(Feature):
    feature_dir_name = BootstrapSDKProvider.LangGraph
    python_dependencies = ["langgraph >= 1.0.2", "langchain_aws >= 1.0.0", "mcp >= 1.19.0",
                           "langchain-mcp-adapters >= 0.1.11"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)