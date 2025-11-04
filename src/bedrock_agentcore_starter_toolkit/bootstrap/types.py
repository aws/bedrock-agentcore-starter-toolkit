from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional
from .features.types import BootstrapIACProvider, BootstrapSDKProvider

class TemplateDirSelection(str, Enum):
    """
    Used to keep track of which directories within templates/ to render
    """
    Default = "default"
    McpRuntime = "mcp_runtime"
    Common = "common"

class RuntimeProtocol(str, Enum):
    """
    The protocols that runtime supports: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html#protocol-comparison
    """
    HTTP = "HTTP"
    MCP = "MCP"
    A2A = "A2A"

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
    sdk_provider: Optional[BootstrapSDKProvider]
    iac_provider: BootstrapIACProvider
    template_dir_selection: TemplateDirSelection
    runtime_protocol: RuntimeProtocol
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
    # observability (use opentelemetry-instrument at Docker entry CMD)
    observability_enabled: bool
    
    def dict(self):
        return asdict(self)