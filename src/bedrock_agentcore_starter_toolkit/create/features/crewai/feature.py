"""CrewAI Feature."""

from ...constants import ModelProvider, SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class CrewAIFeature(Feature):
    """Implements CrewAI code generation."""

    feature_dir_name = SDKProvider.CREWAI

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        from ...constants import TemplateDirSelection

        # For monorepo, only Bedrock is supported (templates don't have model provider subdirs)
        if context.template_dir_selection == TemplateDirSelection.MONOREPO:
            self.python_dependencies = [
                "crewai[tools]>=1.3.0",
                "crewai-tools[mcp]>=1.3.0",
                "mcp>=1.20.0",
            ]
            # model_provider_name not needed for monorepo (no subdirectories)
        else:
            # For runtime_only, set model_provider_name to select correct template subdirectory
            self.model_provider_name = context.model_provider.lower()
            base_python_dependencies = [
                "crewai-tools[mcp]>=1.3.0",
                "mcp>=1.20.0",
            ]
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
