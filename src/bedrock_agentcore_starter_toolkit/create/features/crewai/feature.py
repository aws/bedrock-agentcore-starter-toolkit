"""CrewAI Feature."""

from ...constants import ModelProvider, SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class CrewAIFeature(Feature):
    """Implements CrewAI code generation."""

    feature_dir_name = SDKProvider.CREWAI

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        base_python_dependencies = [
            "crewai-tools[mcp]>=1.3.0",
            "mcp>=1.20.0",
        ]

        # Note: model_provider_name is no longer set here as model_provider templates
        # have been moved to create/templates/model_provider/ and are rendered separately

        match context.model_provider:
            case ModelProvider.Bedrock:
                self.python_dependencies = base_python_dependencies + ["crewai[tools,bedrock]>=1.3.0"]
            case ModelProvider.OpenAI:
                self.python_dependencies = base_python_dependencies + ["crewai[tools,openai]>=1.3.0"]
            case ModelProvider.Anthropic:
                self.python_dependencies = base_python_dependencies + ["crewai[tools,anthropic]>=1.3.0"]
            case ModelProvider.Gemini:
                self.python_dependencies = base_python_dependencies + ["crewai[tools,google-genai]>=1.3.0"]

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
