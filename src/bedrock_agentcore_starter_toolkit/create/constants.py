"""Classes used to reference str constants throughout the code.

Define class members in all caps so pylance treats them as literals
This structure is chosen because StrEnum is available in 3.11+ and we need to support 3.10
"""

from .types import CreateIACProvider, CreateModelProvider, CreateSDKProvider


class TemplateDisplay:
    """This is how we describe the templates in the UI."""

    BASIC = "basic"
    PRODUCTION = "production"


class TemplateDirSelection:
    """Used to keep track of which directories within templates/ to render."""

    MONOREPO = "monorepo"
    COMMON = "common"
    RUNTIME_ONLY = "runtime_only"


class DeploymentType:
    """Deploy with docker or s3 zip."""

    CONTAINER = "container"
    DIRECT_CODE_DEPLOY = "direct_code_deploy"


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

    _ORDER = [CDK, TERRAFORM]

    @classmethod
    def get_iac_as_list(cls) -> list[CreateIACProvider]:
        """Get IAC in intended order for display."""
        return cls._ORDER


class SDKProvider:
    """Supported Agent SDKs for agentcore create."""

    STRANDS = "Strands"
    LANG_CHAIN_LANG_GRAPH = "LangChain_LangGraph"
    GOOGLE_ADK = "GoogleADK"
    OPENAI_AGENTS = "OpenAIAgents"
    AUTOGEN = "AutoGen"
    CREWAI = "CrewAI"

    _DISPLAY_MAP = {
        STRANDS: "Strands Agents SDK",
        LANG_CHAIN_LANG_GRAPH: "LangChain + LangGraph",
        GOOGLE_ADK: "Google Agent Development Kit",
        OPENAI_AGENTS: "OpenAI Agents SDK",
        AUTOGEN: "Microsoft AutoGen",
        CREWAI: "CrewAI",
    }
    _REVERSE_DISPLAY_MAP = {v: k for k, v in _DISPLAY_MAP.items()}

    _ORDER = [
        STRANDS,
        CREWAI,
        GOOGLE_ADK,
        LANG_CHAIN_LANG_GRAPH,
        AUTOGEN,
        OPENAI_AGENTS,
    ]

    @classmethod
    def get_sdk_display_names_as_list(cls) -> list[str]:
        """Returns a list of DISPLAY names."""
        return [cls._DISPLAY_MAP[k] for k in cls._ORDER]

    @classmethod
    def get_id_from_display(cls, display_name: str) -> CreateSDKProvider:
        """Converts 'Strands Agents SDK' -> 'Strands'."""
        try:
            return cls._REVERSE_DISPLAY_MAP[display_name]
        except KeyError as e:
            raise ValueError(f"Unknown SDK display name: {display_name}") from e

    @classmethod
    def resolve_to_internal_id(cls, input_val: str) -> str:
        """Smart resolver.

        1. If input is a valid Internal ID (e.g. 'Strands'), return it.
        2. If input is a valid Display Name (e.g. 'Strands Agents SDK'), return the ID.
        3. Otherwise raise ValueError.
        """
        # Check if it is already an internal ID
        if input_val in cls._ORDER:
            return input_val

        # Try to resolve from display name
        return cls.get_id_from_display(input_val)


class ModelProvider:
    """Supported Model Providers with context-aware availability."""

    OpenAI = "OpenAI"
    Bedrock = "Bedrock"
    Anthropic = "Anthropic"
    Gemini = "Gemini"

    _DISPLAY_MAP = {
        OpenAI: "OpenAI",
        Bedrock: "Amazon Bedrock",
        Anthropic: "Anthropic",
        Gemini: "Google Gemini",
    }
    _REVERSE_DISPLAY_MAP = {v: k for k, v in _DISPLAY_MAP.items()}

    _ORDER = [
        Bedrock,
        Anthropic,
        Gemini,
        OpenAI,
    ]

    REQUIRES_API_KEY = {OpenAI, Anthropic, Gemini}

    SDK_COMPATIBILITY = {
        SDKProvider.OPENAI_AGENTS: {OpenAI},
        SDKProvider.GOOGLE_ADK: {Gemini},
        SDKProvider.CREWAI: {Bedrock, OpenAI, Anthropic, Gemini},
        SDKProvider.AUTOGEN: {Bedrock, OpenAI, Anthropic, Gemini},
        SDKProvider.STRANDS: {Bedrock, OpenAI, Anthropic, Gemini},
        SDKProvider.LANG_CHAIN_LANG_GRAPH: {Bedrock, OpenAI, Anthropic, Gemini},
    }

    @classmethod
    def _get_filtered_ids(cls, sdk_provider: str | None = None) -> list[CreateModelProvider]:
        """Shared logic: Returns sorted list of INTERNAL IDs based on SDK compatibility.

        Args:
            sdk_provider: Can be Internal ID ('Strands') OR Display Name ('Strands Agents SDK').
        """
        available_ids = set(cls._ORDER)

        if sdk_provider:
            try:
                # Use the smart resolver here
                sdk_internal = SDKProvider.resolve_to_internal_id(sdk_provider)

                sdk_support = cls.SDK_COMPATIBILITY.get(sdk_internal)
                if sdk_support:
                    available_ids = available_ids & sdk_support
            except ValueError:
                # swallow and return all. Shouldn't happen
                pass

        # Return sorted internal IDs
        return [p for p in cls._ORDER if p in available_ids]

    @classmethod
    def get_provider_display_names_as_list(cls, sdk_provider: str | None = None) -> list[str]:
        """Returns list of DISPLAY names (for UI)."""
        internal_ids = cls._get_filtered_ids(sdk_provider)
        return [cls._DISPLAY_MAP[p] for p in internal_ids]

    @classmethod
    def get_providers_list(cls, sdk_provider: str | None = None) -> list[CreateModelProvider]:
        """Returns list of INTERNAL IDs (for Logic) SDK can be display or internal."""
        return cls._get_filtered_ids(sdk_provider)

    @classmethod
    def get_id_from_display(cls, display_name: str) -> str:
        """Converts 'Amazon Bedrock' -> 'Bedrock'."""
        try:
            return cls._REVERSE_DISPLAY_MAP[display_name]
        except KeyError as e:
            raise ValueError(f"Unknown Model display name: {display_name}") from e
