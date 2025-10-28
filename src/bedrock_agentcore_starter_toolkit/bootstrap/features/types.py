from enum import Enum
from typing import TypeAlias

class BootstrapIACProvider(str, Enum):
    CDK = "CDK",
    Terraform = "Terraform"

class BootstrapSDKProvider(str, Enum):
    Strands = "Strands"
    ClaudeAgentsSDK = "ClaudeAgentsSDK"
    OpenAi = "OpenAI"

BootstrapFeature: TypeAlias = BootstrapIACProvider | BootstrapSDKProvider