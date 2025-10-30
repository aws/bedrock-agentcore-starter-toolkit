from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from .features.types import BootstrapFeature

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
    features: List[BootstrapFeature]
    python_dependencies: List[str]
    iac_dir: Optional[Path]
    # below properties are related to consuming the yaml from configure
    agent_name: Optional[str]
    # memory
    memory_enabled: bool
    memory_name: Optional[str]
    memory_event_expiry_days: Optional[int]
    memory_short_and_long_term: Optional[bool]
    memory_short_term_only: Optional[bool]
    # custom jwt
    custom_authorizer_enabled: bool
    custom_authorizer_url: Optional[str]
    custom_authorizer_allowed_clients: Optional[list[str]]
    custom_authorizer_allowed_audience: Optional[list[str]]
    # vpc
    vpc_enabled: bool
    vpc_subnets: Optional[list[str]]
    vpc_security_groups: Optional[list[str]]
    
    def dict(self):
        return asdict(self)