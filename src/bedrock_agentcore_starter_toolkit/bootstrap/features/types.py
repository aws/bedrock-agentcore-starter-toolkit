from enum import Enum

class BootstrapIACProvider(str, Enum):
    CDK = "CDK"
    Terraform = "Terraform"

class BootstrapSDKProvider(str, Enum):
    Strands = "Strands"
    ClaudeAgentsSDK = "ClaudeAgentsSDK"
    LangGraph = "LangGraph"
    GoogleADK = "GoogleADK"
    OpenAIAgents = "OpenAIAgents"
    Autogen = "AutoGen"
    CrewAI = "CrewAI"

class BootstrapProtocol(str, Enum):
    HTTP = "http"
    MCP = "mcp"
    A2A = "a2a"
