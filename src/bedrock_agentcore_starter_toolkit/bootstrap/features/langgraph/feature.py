from ...types import ProjectContext
from ...constants import SDKProvider
from ..base_feature import Feature

class LangGraphFeature(Feature):
    feature_dir_name = SDKProvider.LANG_GRAPH
    python_dependencies = ["langgraph >= 1.0.2", "langchain_aws >= 1.0.0", "mcp >= 1.19.0",
                           "langchain-mcp-adapters >= 0.1.11", "langchain >= 1.0.3"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)