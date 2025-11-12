"""AutoGen Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class AutogenFeature(Feature):
    """Implements Autogen Code generation."""

    feature_dir_name = SDKProvider.AUTOGEN
    python_dependencies = [
        "autogen-agentchat>=0.7.5",
        "autogen-ext[anthropic]>=0.7.5",
        "autogen-ext[mcp]>=0.7.5",
        "tiktoken",
    ]

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        pass

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)

    def before_apply(self, context):
        pass
    
    def after_apply(self, context):
        pass
