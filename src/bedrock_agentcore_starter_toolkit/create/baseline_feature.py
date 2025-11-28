"""Base feature implementation for rendering create templates."""

from pathlib import Path

from .constants import TemplateDirSelection
from .features import Feature
from .types import ProjectContext


class BaselineFeature(Feature):
    """Generic feature for rendering any of the create/* templates.

    Pass in the directory you want to read in. i.e. default/common/mcp.
    """

    def __init__(self, ctx: ProjectContext):
        """Initialise the template directory and minimum dependencies required for a Create project."""
        self.template_override_dir = Path(__file__).parent / "templates" / ctx.template_dir_selection
        match ctx.template_dir_selection:
            case TemplateDirSelection.MONOREPO:
                self.python_dependencies = [
                    "bedrock-agentcore >= 1.0.3",
                    "requests >= 2.32.5",
                    "pytest >= 7.0.0",
                    "pytest-asyncio >= 0.21.0",
                ]
            case TemplateDirSelection.RUNTIME_ONLY:
                self.python_dependencies = [
                    "bedrock-agentcore >= 1.0.3",
                    "python-dotenv >= 1.2.1",
                    "pytest >= 7.0.0",
                    "pytest-asyncio >= 0.21.0",
                    "aws-opentelemetry-distro >= 0.10.0",
                ]
        super().__init__()

    def before_apply(self, context):
        """Implement anything that needs to happen before template rendering."""
        pass

    def after_apply(self, context):
        """Implement anything that needs to happen after template rendering."""
        pass

    def execute(self, context: ProjectContext) -> None:
        """Renders the directory structure for a Create project."""
        self.render_dir(context.output_dir, context)
