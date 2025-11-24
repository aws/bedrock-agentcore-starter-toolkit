"""Utility functions for interactive CLI prompts with validation and confirmation."""

import random

from ...create.constants import IACProvider, ModelProvider, SDKProvider
from ...create.types import CreateModelProvider, CreateSDKProvider
from ..cli_ui import ask_text, select_one


def ask_text_required(title: str, redact: bool = False) -> str:
    """Prompt user for required text input, looping until non-empty value is provided."""
    while True:
        result = ask_text(title, default=None, redact=redact)
        if result and result.strip():
            return result.strip()
        # Empty input, loop and ask again


def prompt_runtime_or_monorepo(runtime_only_text: str):
    """Prompt user to choose between Runtime or Monorepo project type."""
    choice = select_one(title="How would you like to start?", options=[runtime_only_text, "A production-ready agent"])
    return choice


def prompt_iac_provider() -> IACProvider:
    """Prompt user to choose CDK or Terraform as the IaC provider."""
    choice = select_one(
        title="Which IaC proivder will define your AgentCore resources?", options=IACProvider.get_iac_as_list()
    )
    return choice


def prompt_sdk_provider() -> CreateSDKProvider:
    """Prompt user to choose agent SDK."""
    choice = select_one(
        title="What agent framework should we use?", options=SDKProvider.get_sdk_display_names_as_list()
    )
    return SDKProvider.get_id_from_display(choice)


def prompt_model_provider(sdk_provider: str | None = None) -> CreateModelProvider:
    """Prompt user to choose an LLM model provider."""
    choice = select_one(
        title="Which model provider will power your agent?",
        options=ModelProvider.get_provider_display_names_as_list(sdk_provider=sdk_provider),
    )
    return ModelProvider.get_id_from_display(choice)


def prompt_configure():
    """Prompt user to decide if they want to run agentcore configure."""
    choice = select_one(
        title="Run agentcore configure first? "
        "(Further define configuration and reference exisiting resources like a JWT authorizer in the generated IaC?",
        options=["No", "Yes"],
    )
    return choice


def prompt_memory_enabled() -> bool:
    """Prompt user to enable memory (default configuration: STM + LTM)."""
    choice = select_one(title="Do you want to enable memory?", options=["No", "Yes, use default memory configuration"])
    return choice == "Yes, use default memory configuration"


def prompt_git_init():
    """Prompt user to decide if they want to run git init."""
    choice = select_one(title="Initialize a new git repository? (optional)", options=["Yes", "No"])
    return choice


def get_auto_generated_project_name() -> str:
    """Auto gen a valid project name."""
    adjectives = [
        "echo",
        "bravo",
        "delta",
        "astro",
        "atomic",
        "rapid",
        "hyper",
        "neo",
        "ultra",
        "nova",
    ]

    colors = [
        "red",
        "blue",
        "cyan",
        "lime",
        "teal",
        "gray",
        "navy",
        "aqua",
        "ivory",
        "amber",
    ]

    a = random.choice(adjectives)  # nosec B311 - not used for security/crypto, just friendly name generation
    c = random.choice(colors)  # nosec B311 - not used for security/crypto, just friendly name generation

    # camelCase: adjective + CapitalizedColor
    return f"{a}{c.capitalize()}"
