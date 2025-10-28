from pathlib import Path
import subprocess

from ...features.base_feature import Feature
from ...features.types import BootstrapIACProvider
from ...types import ProjectContext

class CDKFeature(Feature):
    name = BootstrapIACProvider.CDK.value

    def before_apply(self, context: ProjectContext):

        # create output dir
        iac_dir = Path(context.output_dir / "cdk")
        iac_dir.mkdir(exist_ok=False)
        context.iac_dir = iac_dir

        # initiate the cdk project via npx
        subprocess.run(
            ["npx", "--yes", "aws-cdk", "init", "app", "--language", "typescript", "--generate-only"],
            cwd=context.iac_dir,
            check=True,
        )

        # aws-cdk doesn't give the newest aws-cdk, so need to run upgrade with npm. We already confirmed use has npx which implies that they have npm
        subprocess.run(
            ["npm", "install", "aws-cdk-lib@latest", "constructs@latest"],
            cwd=context.iac_dir,
            check=True,
        )

        # compatible developer dependency with newer libraries from above
        subprocess.run(
            ["npm", "install", "--save-dev", "aws-cdk@latest"],
            cwd=context.iac_dir,
            check=True,
        )

    def execute(self, context: ProjectContext) -> None:
        #clean out files we don't want
        generated_stack_file: Path = context.iac_dir / "lib" / "cdk-stack.ts"
        if generated_stack_file.exists():
            generated_stack_file.unlink()

        # updated file structure
        stacks_dir: Path = context.iac_dir / "lib" / "stacks"
        stacks_dir.mkdir(parents=True, exist_ok=True)

        self.render_dir(context.iac_dir, context)

    def after_apply(self, context: ProjectContext):
        pass