from ...types import ProjectContext
from ..types import BootstrapSDKProvider
from ..base_feature import Feature

class AutogenFeature(Feature):
    feature_dir_name = BootstrapSDKProvider.Autogen.value
    python_dependencies = ["autogen-agentchat>=0.7.5","autogen-ext[openai]>=0.7.5","autogen-ext[mcp]>=0.7.5"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)