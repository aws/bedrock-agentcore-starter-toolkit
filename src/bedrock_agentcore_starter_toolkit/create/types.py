"""Type definitions and data classes for create project configuration."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Literal, Optional, get_args

CreateSDKProvider = Literal["Strands", "LangChain", "GoogleADK", "OpenAIAgents", "AutoGen", "CrewAI"]
SupportedSDKProviders = list(get_args(CreateSDKProvider))

CreateIACProvider = Literal["CDK", "Terraform"]

CreateTemplateDirSelection = Literal["monorepo", "common", "runtime_only"]
CreateTemplateDisplay = Literal["basic", "production"]

CreateRuntimeProtocol = Literal["HTTP", "MCP", "A2A"]

# until we have direct code deployment constructs, only support container deploy
CreateDeploymentType = Literal["container", "direct_code_deploy"]

CreateModelProvider = Literal["Bedrock", "OpenAI", "Anthropic", "Gemini"]


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
    sdk_provider: Optional[CreateSDKProvider]
    iac_provider: CreateIACProvider
    model_provider: CreateModelProvider
    template_dir_selection: CreateTemplateDirSelection
    runtime_protocol: CreateRuntimeProtocol
    deployment_type: CreateDeploymentType
    python_dependencies: List[str]
    iac_dir: Optional[Path] = None
    # below properties are related to consuming the yaml from configure
    agent_name: Optional[str] = None
    # memory
    memory_enabled: bool = False
    memory_name: Optional[str] = None
    memory_event_expiry_days: Optional[int] = None
    memory_is_long_term: Optional[bool] = None
    # custom jwt
    custom_authorizer_enabled: bool = False
    custom_authorizer_url: Optional[str] = None
    custom_authorizer_allowed_clients: Optional[list[str]] = None
    custom_authorizer_allowed_audience: Optional[list[str]] = None
    # vpc
    vpc_enabled: bool = False
    vpc_subnets: Optional[list[str]] = None
    vpc_security_groups: Optional[list[str]] = None
    # request headers
    request_header_allowlist: Optional[list[str]] = None
    # observability (use opentelemetry-instrument at Docker entry CMD)
    observability_enabled: bool = True
    # api key authentication
    api_key_env_var_name: Optional[str] = False

    def dict(self):
        """Return dataclass as dictionary."""
        return asdict(self)
