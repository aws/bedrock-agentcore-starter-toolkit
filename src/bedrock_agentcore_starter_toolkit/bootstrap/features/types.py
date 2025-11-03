from enum import Enum
from typing import Union

class BootstrapIACProvider(str, Enum):
    CDK = "CDK"
    Terraform = "Terraform"

class BootstrapSDKProvider(str, Enum):
    Strands = "Strands"
    ClaudeAgentsSDK = "ClaudeAgentsSDK"
    LangGraph = "LangGraph"
    GoogleADK = "GoogleADK"
    OpenAIAgents = "OpenAIAgents"

class BootstrapProtocol(str, Enum):
    HTTP = "http"
    MCP = "mcp"
    A2A = "a2a"

BootstrapFeature = Union[BootstrapIACProvider, BootstrapSDKProvider]