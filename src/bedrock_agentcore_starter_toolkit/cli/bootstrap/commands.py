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
    use_cdk: bool = typer.Option(False, "--iac-cdk", help="Use AWS CDK as the IAC provider for the generated project"),
    use_terraform: bool = typer.Option(False, "--iac-terraform", help="Use Terraform as the IAC provider for the generated project"),
    use_strands: bool = typer.Option(False, "--use-strands", help="Use Strands as the agent SDK for the generated project"),
    use_claude_agents: bool = typer.Option(False, "--use-claude-agents", help="Use claude-agents-sdk as the agent SDK for the generated project"),
    use_open_ai_agents: bool = typer.Option(False, "--use-open-ai-agents", help="Use open-ai-agents-sdk as the agent SDK for the generated project")
):
    # Input Validation
    if not VALID_PROJECT_NAME_PATTERN.fullmatch(project_name):
        raise typer.BadParameter(
            "To ensure friendly ARN creation, project must start with a letter and then only contain alphanumeric or - or _ characters up to 36 chars in total length"
        )
    if use_cdk and use_terraform:
        raise typer.BadParameter("Can't enable both CDK and terraform generation for the same project!")
    if use_strands + use_claude_agents + use_open_ai_agents > 1: # boolean math so "if more than one is true"
        raise typer.BadParameter("Can only enable one agent SDK for the generated project")
    if Path(project_name).exists():
        raise typer.BadParameter(f"A directory already exists with name {project_name}! Either delete that directory or choose a new project name.")
    if use_cdk and not shutil.which("npx"):
        raise typer.BadParameter("Need to install npx to bootstrap with cdk. Npx comes installed with any npm >= 5.2.0. Npm is bundled with node install.")
    
    # Build feature configuration list
    active_features: list[BootstrapFeature] = []
    if use_cdk:
        active_features.append(BootstrapIACProvider.CDK)
    if use_terraform:
        active_features.append(BootstrapIACProvider.Terraform)
    if use_strands:
        active_features.append(BootstrapSDKProvider.Strands)
    if use_claude_agents:
        active_features.append(BootstrapSDKProvider.ClaudeAgentsSDK)
    if use_open_ai_agents:
        active_features.append(BootstrapSDKProvider.OpenAi)
    
    # Create template project
    generate_project(project_name, active_features)
    

