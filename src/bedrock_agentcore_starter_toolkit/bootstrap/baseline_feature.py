"""Base feature implementation for rendering bootstrap templates."""

from pathlib import Path

from .constants import TemplateDirSelection
from .features import Feature
from .types import BootstrapTemplateDirSelection, ProjectContext


class BaselineFeature(Feature):
    """Generic feature for rendering any of the bootstrap/* templates.

    Pass in the directory you want to read in. i.e. default/common/mcp.
    """

    def __init__(self, template_dir_name: BootstrapTemplateDirSelection):
        """Initialise the template directory and minimum dependencies required for a Bootstrap project."""
        self.template_override_dir = Path(__file__).parent / "templates" / template_dir_name
        self.python_dependencies = (
            ["bedrock-agentcore >= 1.0.3", "requests >= 2.32.5"]
            if template_dir_name == TemplateDirSelection.DEFAULT
            else ["mcp >= 1.19.0"]
        )
        super().__init__()
    
    def before_apply(self, context):
        pass
    
    def after_apply(self, context):
        pass

    def execute(self, context: ProjectContext) -> None:
        """Renders the directory structure for a Bootstrap project."""
        self.render_dir(context.output_dir, context)
