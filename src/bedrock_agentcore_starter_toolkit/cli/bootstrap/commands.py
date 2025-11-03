from pathlib import Path
import shutil
from time import sleep
import typer
import re
from ...bootstrap.generate import generate_project
from ...utils.runtime.schema import BedrockAgentCoreConfigSchema, BedrockAgentCoreAgentSchema
from ...utils.runtime.config import load_config
from ...cli.common import console, _handle_error
from ...bootstrap.features.types import BootstrapIACProvider, BootstrapSDKProvider
from ..common import _handle_warn

bootstrap_app = typer.Typer(help="bootstrap an agent core project")
# create arn friendly names on the shorter side (used for prefix in infra ids) no - or _ for now to deal with inconsistent agentcore validations
VALID_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,35}$") 

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

    # consume config from configure command and perform validations
    configure_yaml = Path.cwd() / ".bedrock_agentcore.yaml"
    agent_config: BedrockAgentCoreAgentSchema | None = None

    if not configure_yaml.exists():
        _handle_warn("No .bedrock_agentcore.yaml file detected, using bootstrap configuration defaults. To specifiy project configuration, first run agentcore configure.")
        sleep(2) # so above message can be seen clearly
  
    if configure_yaml.exists():
        configure_schema: BedrockAgentCoreConfigSchema = load_config(configure_yaml)
        if len(configure_schema.agents.keys()) > 1:
            _handle_error(message="agentcore bootstrap generate does not currently support multi agent configurations. Try again with a single agent configured. Exiting.")
        # now assume we have just one agent configured and build the project context
        agent_config = next(iter(configure_schema.agents.values()))

    # Create template project
    generate_project(project_name, sdk, iac, agent_config)

