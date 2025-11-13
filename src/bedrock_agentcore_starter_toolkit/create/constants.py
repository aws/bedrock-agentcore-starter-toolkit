"""Classes used to reference str constants throughout the code.

Define class members in all caps so pylance treats them as literals
This structure is chosen because StrEnum is available in 3.11+ and we need to support 3.10
"""


class TemplateDirSelection:
    """Used to keep track of which directories within templates/ to render."""

    DEFAULT = "default"
    COMMON = "common"
    MCP_RUNTIME = "mcp_runtime"
    RUNTIME_ONLY = "runtime_only"


class RuntimeProtocol:
    """The protocols that runtime supports.

    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html#protocol-comparison
    """

    HTTP = "HTTP"
    MCP = "MCP"
    A2A = "A2A"


class IACProvider:
    """Supported IaC Frameworks for agentcore create."""

    CDK = "CDK"
    TERRAFORM = "Terraform"


class SDKProvider:
    """Supported Agent SDKs for agentcore create."""

    STRANDS = "Strands"
    LANG_GRAPH = "LangGraph"
    GOOGLE_ADK = "GoogleADK"
    OPENAI_AGENTS = "OpenAIAgents"
    AUTOGEN = "AutoGen"
    CREWAI = "CrewAI"
