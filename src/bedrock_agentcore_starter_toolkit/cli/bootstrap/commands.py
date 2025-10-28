from pathlib import Path
import shutil
import typer
import re
from ...bootstrap.generate import generate_project
from ...bootstrap.features.types import BootstrapFeature, BootstrapIACProvider, BootstrapSDKProvider

bootstrap_app = typer.Typer(help="bootstrap an agent core project")
VALID_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9-_]{0,35}$") # create arn friendly names on the shorter side (used for prefix in infra ids)

@bootstrap_app.command()
def generate(
    project_name: str,
    iac: BootstrapIACProvider = typer.Option(..., help="Infrastructure as code provider"),
    sdk: BootstrapSDKProvider = typer.Option(..., help="SDK provider"),
):
    # Input Validation
    if not VALID_PROJECT_NAME_PATTERN.fullmatch(project_name):
        raise typer.BadParameter(
            "To ensure friendly ARN creation, project must start with a letter and then only contain alphanumeric or - or _ characters up to 36 chars in total length"
        )
    if Path(project_name).exists():
        raise typer.BadParameter(f"A directory already exists with name {project_name}! Either delete that directory or choose a new project name.")
    if iac == BootstrapIACProvider.CDK and not shutil.which("npx"):
        raise typer.BadParameter("Need to install npx to bootstrap with cdk. Npx comes installed with any npm >= 5.2.0. Npm is bundled with node install.")
    
    active_features: list[BootstrapFeature] = [iac, sdk]
    
    # Create template project
    generate_project(project_name, active_features)
    

