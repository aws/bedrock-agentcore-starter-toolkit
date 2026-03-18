"""Type definitions and data classes for create project configuration."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, get_args

CreateSDKProvider = Literal["Strands", "LangChain_LangGraph", "GoogleADK", "OpenAIAgents", "AutoGen", "CrewAI"]
SupportedSDKProviders = list(get_args(CreateSDKProvider))

CreateIACProvider = Literal["CDK", "Terraform"]

CreateTemplateDirSelection = Literal["monorepo", "common", "runtime_only"]
CreateTemplateDisplay = Literal["basic", "production"]

CreateRuntimeProtocol = Literal["HTTP", "MCP", "A2A", "AGUI"]

# until we have direct code deployment constructs, only support container deploy
CreateDeploymentType = Literal["container", "direct_code_deploy"]

CreateModelProvider = Literal["Bedrock", "OpenAI", "Anthropic", "Gemini"]

CreateMemoryType = Literal["STM_ONLY", "STM_AND_LTM", "NO_MEMORY"]


@dataclass
class ProjectContext:
    """This class is instantiated once in the ./generate.py file at project creation.

    Then other components in the logic update its properties during execution.
    No defaults here so its clear what is the default behavior in generate.
    """

    name: str
    output_dir: Path
    src_dir: Path
    entrypoint_path: Path
    sdk_provider: CreateSDKProvider | None
    iac_provider: CreateIACProvider | None
    model_provider: CreateModelProvider
    template_dir_selection: CreateTemplateDirSelection
    runtime_protocol: CreateRuntimeProtocol
    deployment_type: CreateDeploymentType
    python_dependencies: list[str]
    iac_dir: Path | None = None
    # below properties are related to consuming the yaml from configure
    agent_name: str | None = None
    # memory
    memory_enabled: bool = False
    memory_name: str | None = None
    memory_event_expiry_days: int | None = None
    memory_is_long_term: bool | None = None
    # custom jwt
    custom_authorizer_enabled: bool = False
    custom_authorizer_url: str | None = None
    custom_authorizer_allowed_clients: list[str] | None = None
    custom_authorizer_allowed_audience: list[str] | None = None
    # vpc
    vpc_enabled: bool = False
    vpc_subnets: list[str] | None = None
    vpc_security_groups: list[str] | None = None
    # request headers
    request_header_allowlist: list[str] | None = None
    # observability (use opentelemetry-instrument at Docker entry CMD)
    observability_enabled: bool = True
    # api key authentication
    api_key_env_var_name: str | None = False

    def dict(self):
        """Return dataclass as dictionary."""
        return asdict(self)
