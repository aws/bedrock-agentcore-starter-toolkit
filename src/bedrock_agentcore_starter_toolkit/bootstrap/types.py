from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Literal

BootstrapSDKProvider = Literal[
    "Strands",
    "LangGraph",
    "GoogleADK",
    "OpenAIAgents",
    "AutoGen",
    "CrewAI"
]

BootstrapIACProvider = Literal[
    "CDK",
    "Terraform"
]

BootstrapTemplateDirSelection = Literal[
    "default",
    "common",
    "mcp_runtime"
]

BootstrapRuntimeProtocol = Literal[
    "HTTP",
    "MCP",
    "A2A"
]

@dataclass
class ProjectContext:
    """
    This class is instantiated once in the ./generate.py file at project creation
    Then other components in the logic update its properties during execution.
    No defaults here so its clear what is the default behavior in generate.
    """
    name: str
    output_dir: Path
    src_dir: Path
    entrypoint_path: Path
    sdk_provider: Optional[BootstrapSDKProvider]
    iac_provider: BootstrapIACProvider
    template_dir_selection: BootstrapTemplateDirSelection
    runtime_protocol: BootstrapRuntimeProtocol
    python_dependencies: List[str]
    iac_dir: Optional[Path]
    src_implementation_provided: bool
    # below properties are related to consuming the yaml from configure
    agent_name: Optional[str]
    # memory
    memory_enabled: bool
    memory_name: Optional[str]
    memory_event_expiry_days: Optional[int]
    memory_is_long_term: Optional[bool]
    # custom jwt
    custom_authorizer_enabled: bool
    custom_authorizer_url: Optional[str]
    custom_authorizer_allowed_clients: Optional[list[str]]
    custom_authorizer_allowed_audience: Optional[list[str]]
    # vpc
    vpc_enabled: bool
    vpc_subnets: Optional[list[str]]
    vpc_security_groups: Optional[list[str]]
    # request headers
    request_header_allowlist: Optional[list[str]]
    # observability (use opentelemetry-instrument at Docker entry CMD)
    observability_enabled: bool
    
    def dict(self):
        return asdict(self)