"""Create CLI Commands."""

import re
from pathlib import Path
from time import sleep

import typer

from ...cli.common import _handle_error
from ...create.generate import generate_project
from ...create.types import CreateIACProvider, CreateSDKProvider
from ...utils.runtime.config import load_config
from ...utils.runtime.schema import BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from ..common import _handle_warn
from .prompt_util import prompt_choice_until_valid_input

create_app = typer.Typer(
    name="create", help="create an agent core project", invoke_without_command=True, no_args_is_help=False
)
# create arn friendly names on the shorter side (used for prefix in infra ids) no - or _ for now to deal
# with inconsistent agentcore validations
VALID_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,35}$")

iac_option = typer.Option(
    None,
    "--iac",
    help="Infrastructure as code provider (CDK or Terraform)",
)

sdk_option = typer.Option(
    None,
    "--sdk",
    help="SDK provider (Strands, ClaudeAgents, OpenAI, etc.)",
)


@create_app.callback(invoke_without_command=True)
def create(
    ctx: typer.Context,
    project_name: str = typer.Option(
        None, "--project-name", "-p", prompt="Project name (alphanumeric)", help="Project name to create"
    ),
    iac: CreateIACProvider = iac_option,
    sdk: CreateSDKProvider = sdk_option,
):
    """CLI Implementation for Create Command."""
    if ctx.invoked_subcommand:
        return

    # Input Validation
    if not VALID_PROJECT_NAME_PATTERN.fullmatch(project_name):
        raise typer.BadParameter(
            "To ensure friendly ARN creation, project must only contain alphanumeric charcters (no '-' or '_') up to "
            "36 chars in total length"
        )
    if Path(project_name).exists():
        raise typer.BadParameter(
            f"A directory already exists with name {project_name}! Either delete that directory or choose a new "
            f"project name."
        )

    # consume config from configure command and perform validations
    configure_yaml = Path.cwd() / ".bedrock_agentcore.yaml"
    agent_config: BedrockAgentCoreAgentSchema | None = None

    if configure_yaml.exists():
        configure_schema: BedrockAgentCoreConfigSchema = load_config(configure_yaml)
        if len(configure_schema.agents.keys()) > 1:
            _handle_error(
                message="agentcore create does not currently support multi agent configurations. "
                "Try again with a single agent configured. Exiting."
            )
        # now assume we have just one agent configured and build the project context
        agent_config = next(iter(configure_schema.agents.values()))
        # until there are IAC constructs for direct code deployment, fail configs that aren't configured for container
        if agent_config.deployment_type != "container":
            _handle_error(
                message="agentcore create does not currently support direct code deployment. "
                "Try again with deployment_type: container"
            )

    # Interactively accept IAC/SDK if not provided
    valid_iac = list(CreateIACProvider.__args__)
    valid_sdk = list(CreateSDKProvider.__args__)
    if not iac:
        iac = prompt_choice_until_valid_input(label="IAC provider", choices=valid_iac)
    # entrypoint provided != . means src is provided and we don't need sdk
    if not sdk and (not agent_config or agent_config.entrypoint == "."):
        sdk = prompt_choice_until_valid_input(label="SDK provider", choices=valid_sdk)

    if not configure_yaml.exists():
        _handle_warn(
            "No .bedrock_agentcore.yaml file detected, using create configuration defaults. "
            "To specifiy project configuration, first run agentcore configure."
        )
        sleep(2)  # so above message can be seen clearly

    # Create template project
    generate_project(project_name, sdk, iac, agent_config)
