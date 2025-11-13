"""LangGraph Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class LangGraphFeature(Feature):
    """Implements Langgraph code generation."""

    feature_dir_name = SDKProvider.LANG_GRAPH
    python_dependencies = [
        "langgraph >= 1.0.2",
        "langchain_aws >= 1.0.0",
        "mcp >= 1.19.0",
        "langchain-mcp-adapters >= 0.1.11",
        "langchain >= 1.0.3",
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
