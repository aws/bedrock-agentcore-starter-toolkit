"""Create CLI Commands."""

import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple

import typer

from ...cli.common import _handle_error, _handle_warn
from ...create.constants import ModelProvider, TemplateDisplay
from ...create.generate import generate_project
from ...create.types import (
    CreateIACProvider,
    CreateModelProvider,
    CreateSDKProvider,
    CreateTemplateDisplay,
    SupportedIACProivders,
)
from ...utils.runtime.config import load_config
from ...utils.runtime.schema import BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from ..cli_ui import (
    _pause_and_new_line_on_finish,
    ask_text,
    ask_text_with_validation,
    intro_animate_once,
    show_create_welcome_ascii,
)
from ..runtime.commands import configure_impl
from .prompt_util import (
    get_auto_generated_project_name,
    prompt_configure,
    prompt_git_init,
    prompt_iac_provider,
    prompt_model_provider,
    prompt_runtime_or_monorepo,
    prompt_sdk_provider,
)

create_app = typer.Typer(
    name="create", help="create an agent core project", invoke_without_command=True, no_args_is_help=False
)

# create arn friendly names on the shorter side (used for prefix in infra ids) no - or _ for now
VALID_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,35}$")

project_name_option = typer.Option(
    None, "--project-name", "-p", help="Project name to create (assumes current folder for creation)"
)
template_option = typer.Option(
    None,
    "--template",
    "-t",
    help="The template to use. `basic creates just runtime code. `production` includes an MCP setup and IaC.",
)
sdk_option = typer.Option(None, "--agent-framework", help="Agent SDK provider (Strands, ClaudeAgents, OpenAI, etc.)")
model_provider_option = typer.Option(None, "--model-provider", "-mp", help="Model provider to use with the Agent SDK")
model_provider_api_key_option = typer.Option(None, "--provider-api-key", "-key", help="API key for the model provider")
iac_option = typer.Option(None, "--iac", help="Infrastructure as code provider (CDK or Terraform)")
non_interactive_flag_opt = typer.Option(False, "--non-interactive", help="Run in non-interactive mode")
venv_option = typer.Option(True, "--venv/--no-venv", help="Automatically create a venv and install dependencies")


@create_app.callback(invoke_without_command=True)
def create(
    ctx: typer.Context,
    project_name: Optional[str] = project_name_option,
    template: Optional[CreateTemplateDisplay] = template_option,
    sdk: CreateSDKProvider = sdk_option,
    model_provider: CreateModelProvider = model_provider_option,
    provider_api_key: Optional[str] = model_provider_api_key_option,
    iac: Optional[CreateIACProvider] = iac_option,
    non_interactive_flag: Optional[bool] = non_interactive_flag_opt,
    venv_option: bool = venv_option,
):
    """CLI Implementation for Create Command."""
    if ctx.invoked_subcommand:
        return

    # Auto-set non-interactive mode
    if not non_interactive_flag and (project_name or sdk or model_provider):
        _handle_warn(
            "Automatically using interactive mode because project_name sdk or model_provider"
            " were given directly as flags. "
            "Use agentcore create without arguments to enter interactive mode."
        )
        non_interactive_flag = True

    if non_interactive_flag:
        _validate_non_interactive_input(
            project_name=project_name, iac=iac, sdk=sdk, template=template, model_provider=model_provider
        )
    else:
        show_create_welcome_ascii()

    agent_config: BedrockAgentCoreAgentSchema | None = None

    # Start the safe execution block
    with handle_keyboard_interrupt():
        # 1. Project Name Input & Validation
        if not project_name:
            project_name = ask_text_with_validation(
                title="Where should we create your new agent?",
                regex=VALID_PROJECT_NAME_PATTERN,
                error_message="Prjoect directory names need to be alphanumeric.",
                default=get_auto_generated_project_name(),
                starting_chars="./",
                erase_prompt_on_submit=False,
            )

        if not VALID_PROJECT_NAME_PATTERN.fullmatch(project_name):
            raise typer.BadParameter(
                "Project must only contain alphanumeric characters (no '-' or '_') up to 36 chars."
            )
        if Path(project_name).exists():
            raise typer.BadParameter(f"A directory already exists with name {project_name}!")

        # 2. Determine Mode (Runtime vs Monorepo)
        if template is None:
            if non_interactive_flag:
                template = TemplateDisplay.BASIC
            else:
                basic_opt_text = "A basic starter project (recommended)"
                is_basic = prompt_runtime_or_monorepo(runtime_only_text=basic_opt_text) == basic_opt_text
                template = TemplateDisplay.BASIC if is_basic else TemplateDisplay.PROODUCTION

        # 3. Run specific flows (Pass args IN, get results OUT)
        if template == TemplateDisplay.BASIC:
            sdk, model_provider, provider_api_key = _handle_basic_runtime_flow(
                sdk, model_provider, provider_api_key, non_interactive_flag
            )
        else:
            sdk, model_provider, iac, agent_config = _handle_monorepo_flow(
                sdk, model_provider, iac, non_interactive_flag
            )

        git_init = False
        if not non_interactive_flag:
            git_init = prompt_git_init() == "Yes"
        intro_animate_once()
        generate_project(
            name=project_name,
            sdk_provider=sdk,
            model_provider=model_provider,
            provider_api_key=provider_api_key,
            iac_provider=iac,
            agent_config=agent_config,
            use_venv=venv_option,
            git_init=git_init,
        )


# ------------------------------------------------------------------------------
# Helper Functions & Utilities
# ------------------------------------------------------------------------------


def _handle_basic_runtime_flow(
    sdk: CreateSDKProvider,
    model_provider: CreateModelProvider,
    provider_api_key: Optional[str],
    non_interactive_flag: bool,
) -> Tuple[CreateSDKProvider, CreateModelProvider, Optional[str]]:
    """Handles prompt logic for Runtime-only mode."""
    if not sdk:
        sdk = prompt_sdk_provider()

    supported_providers = ModelProvider.get_providers_list(sdk_provider=sdk)

    if not model_provider:
        model_provider = prompt_model_provider(sdk_provider=sdk)

    if model_provider not in supported_providers:
        raise typer.BadParameter(f"Model provider '{model_provider}' is not supported for SDK '{sdk}'.")

    if model_provider in ModelProvider.REQUIRES_API_KEY and not provider_api_key:
        if non_interactive_flag:
            typer.echo(
                typer.style(
                    f"\n⚠️  Warning: No API key provided for {model_provider}. "
                    f"Please set {model_provider.upper()}_API_KEY in your .env file later.\n",
                    fg=typer.colors.YELLOW,
                ),
                err=True,
            )
        else:
            provider_api_key = ask_text(
                title=f"Add your API key now for {model_provider} (optional)",
                default="",
                redact=True,
            )

    return sdk, model_provider, provider_api_key


def _handle_monorepo_flow(
    sdk: CreateSDKProvider,
    model_provider: CreateModelProvider,
    iac: Optional[CreateIACProvider],
    non_interactive_flag: bool,
) -> Tuple[CreateSDKProvider, CreateModelProvider, Optional[CreateIACProvider], Optional[BedrockAgentCoreAgentSchema]]:
    """Handles prompt logic for Monorepo mode."""
    agent_config = None
    configure_yaml = Path.cwd() / ".bedrock_agentcore.yaml"

    if configure_yaml.exists():
        configure_schema: BedrockAgentCoreConfigSchema = load_config(configure_yaml)
        if len(configure_schema.agents.keys()) > 1:
            _handle_error("agentcore create does not currently support multi agent configurations.")

        agent_config = next(iter(configure_schema.agents.values()))
        if agent_config.deployment_type != "container":
            _handle_error("agentcore create currently only supports deployment_type: container")

    # Interactively accept IAC/SDK if not provided
    if not sdk and (not agent_config or agent_config.entrypoint == "."):
        sdk = prompt_sdk_provider()
        model_provider = prompt_model_provider()

    if model_provider and model_provider in ModelProvider.REQUIRES_API_KEY:
        _handle_warn(
            "In runtime + IaC mode: Securely providing the API key to AgentCore Runtime is your responsibility."
        )

    if not iac:
        if non_interactive_flag:
            raise typer.BadParameter("--iac is required for monorepo mode in non-interactive mode")
        iac = prompt_iac_provider()

    if not configure_yaml.exists() and not non_interactive_flag:
        no_title = "No, use default settings"
        if prompt_configure(no_title) != no_title:
            configure_impl(create=True)
            _pause_and_new_line_on_finish(sleep_override=1.0)
            # load new config in
            agent_config = load_config(configure_yaml)

    return sdk, model_provider, iac, agent_config


def _validate_non_interactive_input(
    project_name: str,
    iac: Optional[CreateIACProvider],
    sdk: CreateSDKProvider,
    template: CreateTemplateDisplay,
    model_provider: CreateModelProvider,
):
    # Make it easy for LLMs to understand what went wrong
    REQUIRED_OPTS = """
    Required options for non-interactive mode are: --project-name, --agent-framework and --model-provider
    If --template production is specified, --iac is also a required parameter.
    Run agentcore create --help for more information
    """

    if not project_name:
        raise typer.BadParameter(f"--project-name is required in non-interactive mode.{REQUIRED_OPTS}")
    if not sdk:
        raise typer.BadParameter(
            f"--agent-framework is required in non-interactive mode. "
            "Supported SDK providers: {', '.join(SupportedSDKProviders)}."
            f"{REQUIRED_OPTS}"
        )
    if not model_provider:
        supported_providers = ModelProvider.get_providers_list(sdk_provider=sdk)
        raise typer.BadParameter(
            f"--model-provider is required in non-interactive mode. "
            f"Supported providers for the chosen SDK '{sdk}' are: {', '.join(supported_providers)}"
            f"{REQUIRED_OPTS}"
        )
    if template == TemplateDisplay.PROODUCTION and not iac:
        raise typer.BadParameter(
            f"--iac is required for --template production in non-interactive mode. "
            f"Supported providers for IAC: {', '.join(SupportedIACProivders)}"
            f"{REQUIRED_OPTS}"
        )


@contextmanager
def handle_keyboard_interrupt():
    """Context manager to catch Ctrl+C and exit cleanly."""
    try:
        yield
    except KeyboardInterrupt:
        typer.echo("\n\nOperation cancelled by user.", err=True)
        raise typer.Exit(code=1) from None
