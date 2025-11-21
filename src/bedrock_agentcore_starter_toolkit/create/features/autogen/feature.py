"""AutoGen Feature."""

from ...constants import ModelProvider, SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class AutogenFeature(Feature):
    """Implements Autogen Code generation."""

    feature_dir_name = SDKProvider.AUTOGEN

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        from ...constants import TemplateDirSelection

        # For monorepo, only Bedrock is supported (templates don't have model provider subdirs)
        if context.template_dir_selection == TemplateDirSelection.MONOREPO:
            self.python_dependencies = [
                "autogen-agentchat>=0.7.5",
                "autogen-ext[bedrock]>=0.7.5",
                "autogen-ext[mcp]>=0.7.5",
                "tiktoken",
            ]
            # model_provider_name not needed for monorepo (no subdirectories)
        else:
            # For runtime_only, set model_provider_name to select correct template subdirectory
            self.model_provider_name = context.model_provider.lower()
            base_python_dependencies = [
                "autogen-agentchat>=0.7.5",
                "autogen-ext[mcp]>=0.7.5",
                "tiktoken==0.11.0",
            ]
            match context.model_provider:
                case ModelProvider.Bedrock:
                    self.python_dependencies = base_python_dependencies + ["autogen-ext[anthropic]>=0.7.5"]
                case ModelProvider.OpenAI:
                    self.python_dependencies = base_python_dependencies + ["autogen-ext[openai]>=0.7.5"]
                case ModelProvider.Anthropic:
                    self.python_dependencies = base_python_dependencies + ["autogen-ext[anthropic]>=0.7.5"]
                case ModelProvider.Gemini:
                    # Gemini uses OpenAI's client
                    # https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/tutorial/models.html
                    self.python_dependencies = base_python_dependencies + ["autogen-ext[openai]>=0.7.5"]

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
