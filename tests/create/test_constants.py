"""Unit tests for create constants module."""

import pytest

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    IACProvider,
    ModelProvider,
    RuntimeProtocol,
    SDKProvider,
    TemplateDirSelection,
)


class TestTemplateDirSelection:
    """Tests for TemplateDirSelection constants."""

    def test_monorepo_value(self):
        """Test MONOREPO constant value."""
        assert TemplateDirSelection.MONOREPO == "monorepo"

    def test_common_value(self):
        """Test COMMON constant value."""
        assert TemplateDirSelection.COMMON == "common"

    def test_runtime_only_value(self):
        """Test RUNTIME_ONLY constant value."""
        assert TemplateDirSelection.RUNTIME_ONLY == "runtime_only"


class TestDeploymentType:
    """Tests for DeploymentType constants."""

    def test_container_value(self):
        """Test CONTAINER constant value."""
        assert DeploymentType.CONTAINER == "container"

    def test_direct_code_deploy_value(self):
        """Test DIRECT_CODE_DEPLOY constant value."""
        assert DeploymentType.DIRECT_CODE_DEPLOY == "direct_code_deploy"


class TestRuntimeProtocol:
    """Tests for RuntimeProtocol constants."""

    def test_http_value(self):
        """Test HTTP constant value."""
        assert RuntimeProtocol.HTTP == "HTTP"

    def test_mcp_value(self):
        """Test MCP constant value."""
        assert RuntimeProtocol.MCP == "MCP"

    def test_a2a_value(self):
        """Test A2A constant value."""
        assert RuntimeProtocol.A2A == "A2A"


class TestIACProvider:
    """Tests for IACProvider class."""

    def test_cdk_value(self):
        """Test CDK constant value."""
        assert IACProvider.CDK == "CDK"

    def test_terraform_value(self):
        """Test Terraform constant value."""
        assert IACProvider.TERRAFORM == "Terraform"

    def test_get_iac_as_list_returns_correct_order(self):
        """Test get_iac_as_list returns providers in correct order."""
        result = IACProvider.get_iac_as_list()
        assert result == ["CDK", "Terraform"]

    def test_get_iac_as_list_returns_list(self):
        """Test get_iac_as_list returns a list type."""
        result = IACProvider.get_iac_as_list()
        assert isinstance(result, list)


class TestSDKProvider:
    """Tests for SDKProvider class."""

    def test_strands_value(self):
        """Test STRANDS constant value."""
        assert SDKProvider.STRANDS == "Strands"

    def test_langgraph_value(self):
        """Test LANG_GRAPH constant value."""
        assert SDKProvider.LANG_GRAPH == "LangGraph"

    def test_google_adk_value(self):
        """Test GOOGLE_ADK constant value."""
        assert SDKProvider.GOOGLE_ADK == "GoogleADK"

    def test_openai_agents_value(self):
        """Test OPENAI_AGENTS constant value."""
        assert SDKProvider.OPENAI_AGENTS == "OpenAIAgents"

    def test_autogen_value(self):
        """Test AUTOGEN constant value."""
        assert SDKProvider.AUTOGEN == "AutoGen"

    def test_crewai_value(self):
        """Test CREWAI constant value."""
        assert SDKProvider.CREWAI == "CrewAI"

    def test_get_sdk_display_names_as_list_returns_correct_order(self):
        """Test get_sdk_display_names_as_list returns display names in order."""
        result = SDKProvider.get_sdk_display_names_as_list()
        expected = [
            "Strands Agents SDK",
            "CrewAI",
            "Google Agent Development Kit",
            "LangGraph",
            "Microsoft AutoGen",
            "OpenAI Agents SDK",
        ]
        assert result == expected

    def test_get_sdk_display_names_as_list_length(self):
        """Test get_sdk_display_names_as_list returns all 6 SDKs."""
        result = SDKProvider.get_sdk_display_names_as_list()
        assert len(result) == 6

    def test_get_id_from_display_strands(self):
        """Test converting Strands display name to ID."""
        result = SDKProvider.get_id_from_display("Strands Agents SDK")
        assert result == "Strands"

    def test_get_id_from_display_crewai(self):
        """Test converting CrewAI display name to ID."""
        result = SDKProvider.get_id_from_display("CrewAI")
        assert result == "CrewAI"

    def test_get_id_from_display_google_adk(self):
        """Test converting Google ADK display name to ID."""
        result = SDKProvider.get_id_from_display("Google Agent Development Kit")
        assert result == "GoogleADK"

    def test_get_id_from_display_langgraph(self):
        """Test converting LangGraph display name to ID."""
        result = SDKProvider.get_id_from_display("LangGraph")
        assert result == "LangGraph"

    def test_get_id_from_display_autogen(self):
        """Test converting AutoGen display name to ID."""
        result = SDKProvider.get_id_from_display("Microsoft AutoGen")
        assert result == "AutoGen"

    def test_get_id_from_display_openai(self):
        """Test converting OpenAI Agents display name to ID."""
        result = SDKProvider.get_id_from_display("OpenAI Agents SDK")
        assert result == "OpenAIAgents"

    def test_get_id_from_display_unknown_raises_error(self):
        """Test that unknown display name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown SDK display name"):
            SDKProvider.get_id_from_display("Unknown SDK")

    def test_resolve_to_internal_id_with_internal_id(self):
        """Test resolve_to_internal_id with already valid internal ID."""
        assert SDKProvider.resolve_to_internal_id("Strands") == "Strands"
        assert SDKProvider.resolve_to_internal_id("LangGraph") == "LangGraph"
        assert SDKProvider.resolve_to_internal_id("CrewAI") == "CrewAI"

    def test_resolve_to_internal_id_with_display_name(self):
        """Test resolve_to_internal_id with display name."""
        assert SDKProvider.resolve_to_internal_id("Strands Agents SDK") == "Strands"
        assert SDKProvider.resolve_to_internal_id("Google Agent Development Kit") == "GoogleADK"

    def test_resolve_to_internal_id_unknown_raises_error(self):
        """Test that unknown value raises ValueError."""
        with pytest.raises(ValueError):
            SDKProvider.resolve_to_internal_id("Unknown")


class TestModelProvider:
    """Tests for ModelProvider class."""

    def test_openai_value(self):
        """Test OpenAI constant value."""
        assert ModelProvider.OpenAI == "OpenAI"

    def test_bedrock_value(self):
        """Test Bedrock constant value."""
        assert ModelProvider.Bedrock == "Bedrock"

    def test_anthropic_value(self):
        """Test Anthropic constant value."""
        assert ModelProvider.Anthropic == "Anthropic"

    def test_gemini_value(self):
        """Test Gemini constant value."""
        assert ModelProvider.Gemini == "Gemini"

    def test_requires_api_key_set(self):
        """Test REQUIRES_API_KEY contains correct providers."""
        expected = {"OpenAI", "Anthropic", "Gemini"}
        assert ModelProvider.REQUIRES_API_KEY == expected

    def test_bedrock_not_in_requires_api_key(self):
        """Test Bedrock is not in REQUIRES_API_KEY."""
        assert ModelProvider.Bedrock not in ModelProvider.REQUIRES_API_KEY

    def test_sdk_compatibility_openai_agents(self):
        """Test OpenAI Agents SDK only supports OpenAI."""
        compat = ModelProvider.SDK_COMPATIBILITY[SDKProvider.OPENAI_AGENTS]
        assert compat == {ModelProvider.OpenAI}

    def test_sdk_compatibility_google_adk(self):
        """Test Google ADK only supports Gemini."""
        compat = ModelProvider.SDK_COMPATIBILITY[SDKProvider.GOOGLE_ADK]
        assert compat == {ModelProvider.Gemini}

    def test_sdk_compatibility_strands(self):
        """Test Strands supports all providers."""
        compat = ModelProvider.SDK_COMPATIBILITY[SDKProvider.STRANDS]
        expected = {
            ModelProvider.Bedrock,
            ModelProvider.OpenAI,
            ModelProvider.Anthropic,
            ModelProvider.Gemini,
        }
        assert compat == expected

    def test_sdk_compatibility_crewai(self):
        """Test CrewAI supports all providers."""
        compat = ModelProvider.SDK_COMPATIBILITY[SDKProvider.CREWAI]
        expected = {
            ModelProvider.Bedrock,
            ModelProvider.OpenAI,
            ModelProvider.Anthropic,
            ModelProvider.Gemini,
        }
        assert compat == expected

    def test_get_providers_list_no_filter(self):
        """Test get_providers_list with no SDK filter returns all providers."""
        result = ModelProvider.get_providers_list()
        expected = ["Bedrock", "Anthropic", "Gemini", "OpenAI"]
        assert result == expected

    def test_get_providers_list_strands(self):
        """Test get_providers_list for Strands returns all providers."""
        result = ModelProvider.get_providers_list("Strands")
        expected = ["Bedrock", "Anthropic", "Gemini", "OpenAI"]
        assert result == expected

    def test_get_providers_list_openai_agents(self):
        """Test get_providers_list for OpenAI Agents returns only OpenAI."""
        result = ModelProvider.get_providers_list("OpenAIAgents")
        assert result == ["OpenAI"]

    def test_get_providers_list_google_adk(self):
        """Test get_providers_list for Google ADK returns only Gemini."""
        result = ModelProvider.get_providers_list("GoogleADK")
        assert result == ["Gemini"]

    def test_get_providers_list_with_display_name(self):
        """Test get_providers_list works with display names."""
        result = ModelProvider.get_providers_list("Strands Agents SDK")
        expected = ["Bedrock", "Anthropic", "Gemini", "OpenAI"]
        assert result == expected

    def test_get_providers_list_unknown_sdk_returns_all(self):
        """Test get_providers_list with unknown SDK returns all providers."""
        result = ModelProvider.get_providers_list("UnknownSDK")
        expected = ["Bedrock", "Anthropic", "Gemini", "OpenAI"]
        assert result == expected

    def test_get_provider_display_names_as_list_no_filter(self):
        """Test get_provider_display_names_as_list with no filter."""
        result = ModelProvider.get_provider_display_names_as_list()
        expected = ["Amazon Bedrock", "Anthropic", "Google Gemini", "OpenAI"]
        assert result == expected

    def test_get_provider_display_names_as_list_openai_agents(self):
        """Test get_provider_display_names_as_list for OpenAI Agents."""
        result = ModelProvider.get_provider_display_names_as_list("OpenAIAgents")
        assert result == ["OpenAI"]

    def test_get_provider_display_names_as_list_google_adk(self):
        """Test get_provider_display_names_as_list for Google ADK."""
        result = ModelProvider.get_provider_display_names_as_list("GoogleADK")
        assert result == ["Google Gemini"]

    def test_get_id_from_display_bedrock(self):
        """Test converting Amazon Bedrock display name to ID."""
        result = ModelProvider.get_id_from_display("Amazon Bedrock")
        assert result == "Bedrock"

    def test_get_id_from_display_anthropic(self):
        """Test converting Anthropic display name to ID."""
        result = ModelProvider.get_id_from_display("Anthropic")
        assert result == "Anthropic"

    def test_get_id_from_display_gemini(self):
        """Test converting Google Gemini display name to ID."""
        result = ModelProvider.get_id_from_display("Google Gemini")
        assert result == "Gemini"

    def test_get_id_from_display_openai(self):
        """Test converting OpenAI display name to ID."""
        result = ModelProvider.get_id_from_display("OpenAI")
        assert result == "OpenAI"

    def test_get_id_from_display_unknown_raises_error(self):
        """Test that unknown display name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown Model display name"):
            ModelProvider.get_id_from_display("Unknown Provider")
