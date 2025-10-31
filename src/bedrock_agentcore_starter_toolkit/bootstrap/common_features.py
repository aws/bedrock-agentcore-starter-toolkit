from pathlib import Path
from .features import Feature

class CommonFeatures(Feature):
    """
    Small class to extract the common templates under the bootstrap/ dir and write them to the output dir
    """
    name = "bootstrap" # required by Feature class but not used since we specify override_dir in next line
    template_override_parent_dir = Path(__file__).parent
    def execute(self, context):
        self.render_dir(context.output_dir, context)