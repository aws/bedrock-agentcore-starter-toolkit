"""LangGraph Feature."""

from ...constants import ModelProvider, SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class LangChainLangGraphFeature(Feature):
    """Implements Langgraph code generation."""

    feature_dir_name = SDKProvider.LANG_CHAIN_LANG_GRAPH

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""
        self.model_provider_name = context.model_provider.lower()
        base_python_dependencies = [
            "langgraph >= 1.0.2",
            "mcp >= 1.19.0",
            "langchain-mcp-adapters >= 0.1.11",
            "langchain >= 1.0.3",
            "tiktoken==0.11.0",
        ]
        match context.model_provider:
            case ModelProvider.Bedrock:
                self.python_dependencies = base_python_dependencies + ["langchain_aws >= 1.0.0"]
            case ModelProvider.OpenAI:
                self.python_dependencies = base_python_dependencies + ["langchain-openai >= 1.0.3"]
            case ModelProvider.Anthropic:
                self.python_dependencies = base_python_dependencies + ["langchain-anthropic >= 1.1.0"]
            case ModelProvider.Gemini:
                self.python_dependencies = base_python_dependencies + ["langchain-google-genai >= 3.0.3"]

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
