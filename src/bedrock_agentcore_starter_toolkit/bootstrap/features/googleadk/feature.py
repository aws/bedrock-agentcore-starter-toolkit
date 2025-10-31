from ...types import ProjectContext
from ..types import BootstrapSDKProvider
from ..base_feature import Feature

class GoogleADKFeature(Feature):
    name = BootstrapSDKProvider.GoogleADK.value
    python_dependencies = ["google-adk>=1.17.0"]

    def execute(self, context: ProjectContext):
        self.render_dir(context.src_dir, context)