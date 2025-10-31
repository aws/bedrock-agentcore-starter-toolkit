from enum import Enum
from typing import Union

class BootstrapIACProvider(str, Enum):
    CDK = "CDK"
    Terraform = "Terraform"

class BootstrapSDKProvider(str, Enum):
    Strands = "Strands"
    ClaudeAgentsSDK = "ClaudeAgentsSDK"
    OpenAi = "OpenAI"
    LangGraph = "LangGraph"
    GoogleADK = "GoogleADK"

BootstrapFeature = Union[BootstrapIACProvider, BootstrapSDKProvider]

class TemplateMode(str, Enum):
    Default = "default"