from ...types import ProjectContext
from ..types import BootstrapSDKProvider
from ..base_feature import Feature

class StrandsFeature(Feature):
    name = BootstrapSDKProvider.Strands.value
    python_dependencies = ["strands-agents >= 1.13.0", "mcp >= 1.19.0"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)