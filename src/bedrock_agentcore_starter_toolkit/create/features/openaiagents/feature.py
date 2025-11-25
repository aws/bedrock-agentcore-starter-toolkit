"""OpenAI Agents Feature."""

from ...constants import SDKProvider
from ...types import ProjectContext
from ..base_feature import Feature


class OpenAIAgentsFeature(Feature):
    """Implements OpenAI Agents SDK code generation."""

    feature_dir_name = SDKProvider.OPENAI_AGENTS
    python_dependencies = ["openai-agents>=0.4.2"]

    def before_apply(self, context: ProjectContext) -> None:
        """Hook called before template rendering and code generation."""

        # Note: model_provider_name is no longer set here as model_provider templates
        # have been moved to create/templates/model_provider/ and are rendered separately

    def after_apply(self, context: ProjectContext) -> None:
        """Hook called after template rendering and code generation."""
        pass

    def execute(self, context: ProjectContext):
        """Call render_dir."""
        self.render_dir(context.src_dir, context)
