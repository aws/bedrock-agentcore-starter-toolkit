"""Strands SDK Feature."""

from ...constants import ModelProvider, SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class StrandsFeature(Feature):
    """Implements Strands code generation."""

    feature_dir_name = SDKProvider.STRANDS

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        base_python_dependencies = ["mcp >= 1.19.0", "strands-agents-tools >= 0.2.16"]

        match context.model_provider:
            case ModelProvider.Bedrock:
                self.python_dependencies = base_python_dependencies + ["strands-agents >= 1.13.0"]
            case ModelProvider.OpenAI:
                self.python_dependencies = base_python_dependencies + ["strands-agents[openai] >= 1.13.0"]
            case ModelProvider.Anthropic:
                self.python_dependencies = base_python_dependencies + ["strands-agents[anthropic] >= 1.13.0"]
            case ModelProvider.Gemini:
                self.python_dependencies = base_python_dependencies + ["strands-agents[gemini] >= 1.13.0"]

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
