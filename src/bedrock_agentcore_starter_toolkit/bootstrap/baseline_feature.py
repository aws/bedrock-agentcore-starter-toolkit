from pathlib import Path
from .features import Feature
from .types import ProjectContext, TemplateDirSelection

class BaselineFeature(Feature):
    """
    Generic feature for rendering any of the bootstrap/* templates.
    Pass in the direcotry you want to read in. i.e. default/common/mcp
    """
    def __init__(self, template_dir_name: TemplateDirSelection):
        self.template_override_dir = Path(__file__).parent / "templates" / template_dir_name.value
        super().__init__()

    def execute(self, context: ProjectContext) -> None:
        self.render_dir(context.output_dir, context)