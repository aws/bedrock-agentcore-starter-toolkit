"""Unit tests for SDK feature modules."""

from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    SDKProvider,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.features.autogen.feature import AutogenFeature
from bedrock_agentcore_starter_toolkit.create.features.crewai.feature import CrewAIFeature
from bedrock_agentcore_starter_toolkit.create.features.googleadk.feature import GoogleADKFeature
from bedrock_agentcore_starter_toolkit.create.features.langchain_langgraph.feature import LangChainLangGraphFeature
from bedrock_agentcore_starter_toolkit.create.features.openaiagents.feature import OpenAIAgentsFeature
from bedrock_agentcore_starter_toolkit.create.features.strands.feature import StrandsFeature
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext


def create_context(tmp_path, sdk_provider, model_provider, template_dir_selection):
    """Helper to create a ProjectContext for testing."""
    output_dir = tmp_path / "test-project"
    src_dir = output_dir / "src"

    return ProjectContext(
        name="testProject",
        output_dir=output_dir,
        src_dir=src_dir,
        entrypoint_path=src_dir / "main.py",
        sdk_provider=sdk_provider,
        iac_provider="CDK" if template_dir_selection == TemplateDirSelection.MONOREPO else None,
        model_provider=model_provider,
        template_dir_selection=template_dir_selection,
        runtime_protocol=RuntimeProtocol.HTTP,
        deployment_type=DeploymentType.CONTAINER
        if template_dir_selection == TemplateDirSelection.MONOREPO
        else DeploymentType.DIRECT_CODE_DEPLOY,
        python_dependencies=[],
        iac_dir=None,
        agent_name="testProject_Agent",
    )


class TestStrandsFeature:
    """Tests for StrandsFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert StrandsFeature.feature_dir_name == SDKProvider.STRANDS

    def test_monorepo_dependencies(self, tmp_path):
        """Test monorepo mode dependencies."""
        ctx = create_context(tmp_path, SDKProvider.STRANDS, ModelProvider.Bedrock, TemplateDirSelection.MONOREPO)
        feature = StrandsFeature()
        feature.before_apply(ctx)

        assert "strands-agents >= 1.13.0" in feature.python_dependencies
        assert "mcp >= 1.19.0" in feature.python_dependencies

    def test_runtime_only_bedrock_dependencies(self, tmp_path):
        """Test runtime_only mode with Bedrock dependencies."""
        ctx = create_context(tmp_path, SDKProvider.STRANDS, ModelProvider.Bedrock, TemplateDirSelection.RUNTIME_ONLY)
        feature = StrandsFeature()
        feature.before_apply(ctx)

        assert "strands-agents >= 1.13.0" in feature.python_dependencies
        # model_provider_name is no longer set for Strands (templates moved to centralized location)
        assert feature.model_provider_name is None

    def test_runtime_only_openai_dependencies(self, tmp_path):
        """Test runtime_only mode with OpenAI dependencies."""
        ctx = create_context(tmp_path, SDKProvider.STRANDS, ModelProvider.OpenAI, TemplateDirSelection.RUNTIME_ONLY)
        feature = StrandsFeature()
        feature.before_apply(ctx)

        assert "strands-agents[openai] >= 1.13.0" in feature.python_dependencies
        # model_provider_name is no longer set for Strands (templates moved to centralized location)
        assert feature.model_provider_name is None

    def test_runtime_only_anthropic_dependencies(self, tmp_path):
        """Test runtime_only mode with Anthropic dependencies."""
        ctx = create_context(tmp_path, SDKProvider.STRANDS, ModelProvider.Anthropic, TemplateDirSelection.RUNTIME_ONLY)
        feature = StrandsFeature()
        feature.before_apply(ctx)

        assert "strands-agents[anthropic] >= 1.13.0" in feature.python_dependencies
        # model_provider_name is no longer set for Strands (templates moved to centralized location)
        assert feature.model_provider_name is None

    def test_runtime_only_gemini_dependencies(self, tmp_path):
        """Test runtime_only mode with Gemini dependencies."""
        ctx = create_context(tmp_path, SDKProvider.STRANDS, ModelProvider.Gemini, TemplateDirSelection.RUNTIME_ONLY)
        feature = StrandsFeature()
        feature.before_apply(ctx)

        assert "strands-agents[gemini] >= 1.13.0" in feature.python_dependencies
        # model_provider_name is no longer set for Strands (templates moved to centralized location)
        assert feature.model_provider_name is None


class TestCrewAIFeature:
    """Tests for CrewAIFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert CrewAIFeature.feature_dir_name == SDKProvider.CREWAI

    def test_monorepo_dependencies(self, tmp_path):
        """Test monorepo mode dependencies."""
        ctx = create_context(tmp_path, SDKProvider.CREWAI, ModelProvider.Bedrock, TemplateDirSelection.MONOREPO)
        feature = CrewAIFeature()
        feature.before_apply(ctx)

        assert "crewai[tools]>=1.3.0" in feature.python_dependencies
        assert "crewai-tools[mcp]>=1.3.0" in feature.python_dependencies
        assert "mcp>=1.20.0" in feature.python_dependencies

    def test_runtime_only_bedrock_dependencies(self, tmp_path):
        """Test runtime_only mode with Bedrock dependencies."""
        ctx = create_context(tmp_path, SDKProvider.CREWAI, ModelProvider.Bedrock, TemplateDirSelection.RUNTIME_ONLY)
        feature = CrewAIFeature()
        feature.before_apply(ctx)

        assert "crewai[tools,bedrock]>=1.3.0" in feature.python_dependencies
        assert feature.model_provider_name == "bedrock"

    def test_runtime_only_openai_dependencies(self, tmp_path):
        """Test runtime_only mode with OpenAI dependencies."""
        ctx = create_context(tmp_path, SDKProvider.CREWAI, ModelProvider.OpenAI, TemplateDirSelection.RUNTIME_ONLY)
        feature = CrewAIFeature()
        feature.before_apply(ctx)

        assert "crewai[tools,openai]>=1.3.0" in feature.python_dependencies
        assert feature.model_provider_name == "openai"

    def test_runtime_only_anthropic_dependencies(self, tmp_path):
        """Test runtime_only mode with Anthropic dependencies."""
        ctx = create_context(tmp_path, SDKProvider.CREWAI, ModelProvider.Anthropic, TemplateDirSelection.RUNTIME_ONLY)
        feature = CrewAIFeature()
        feature.before_apply(ctx)

        assert "crewai[tools,anthropic]>=1.3.0" in feature.python_dependencies
        assert feature.model_provider_name == "anthropic"

    def test_runtime_only_gemini_dependencies(self, tmp_path):
        """Test runtime_only mode with Gemini dependencies."""
        ctx = create_context(tmp_path, SDKProvider.CREWAI, ModelProvider.Gemini, TemplateDirSelection.RUNTIME_ONLY)
        feature = CrewAIFeature()
        feature.before_apply(ctx)

        assert "crewai[tools,google-genai]>=1.3.0" in feature.python_dependencies
        assert feature.model_provider_name == "gemini"


class TestLangChainLangGraphFeature:
    """Tests for LangChainLangGraphFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert LangChainLangGraphFeature.feature_dir_name == SDKProvider.LANG_CHAIN_LANG_GRAPH

    def test_monorepo_dependencies(self, tmp_path):
        """Test monorepo mode dependencies."""
        ctx = create_context(
            tmp_path, SDKProvider.LANG_CHAIN_LANG_GRAPH, ModelProvider.Bedrock, TemplateDirSelection.MONOREPO
        )
        feature = LangChainLangGraphFeature()
        feature.before_apply(ctx)

        assert "langgraph >= 1.0.2" in feature.python_dependencies
        assert "langchain_aws >= 1.0.0" in feature.python_dependencies
        assert "mcp >= 1.19.0" in feature.python_dependencies

    def test_runtime_only_bedrock_dependencies(self, tmp_path):
        """Test runtime_only mode with Bedrock dependencies."""
        ctx = create_context(
            tmp_path, SDKProvider.LANG_CHAIN_LANG_GRAPH, ModelProvider.Bedrock, TemplateDirSelection.RUNTIME_ONLY
        )
        feature = LangChainLangGraphFeature()
        feature.before_apply(ctx)

        assert "langchain_aws >= 1.0.0" in feature.python_dependencies
        assert feature.model_provider_name == "bedrock"

    def test_runtime_only_openai_dependencies(self, tmp_path):
        """Test runtime_only mode with OpenAI dependencies."""
        ctx = create_context(
            tmp_path, SDKProvider.LANG_CHAIN_LANG_GRAPH, ModelProvider.OpenAI, TemplateDirSelection.RUNTIME_ONLY
        )
        feature = LangChainLangGraphFeature()
        feature.before_apply(ctx)

        assert "langchain-openai >= 1.0.3" in feature.python_dependencies
        assert feature.model_provider_name == "openai"

    def test_runtime_only_anthropic_dependencies(self, tmp_path):
        """Test runtime_only mode with Anthropic dependencies."""
        ctx = create_context(
            tmp_path, SDKProvider.LANG_CHAIN_LANG_GRAPH, ModelProvider.Anthropic, TemplateDirSelection.RUNTIME_ONLY
        )
        feature = LangChainLangGraphFeature()
        feature.before_apply(ctx)

        assert "langchain-anthropic >= 1.1.0" in feature.python_dependencies
        assert feature.model_provider_name == "anthropic"

    def test_runtime_only_gemini_dependencies(self, tmp_path):
        """Test runtime_only mode with Gemini dependencies."""
        ctx = create_context(
            tmp_path, SDKProvider.LANG_CHAIN_LANG_GRAPH, ModelProvider.Gemini, TemplateDirSelection.RUNTIME_ONLY
        )
        feature = LangChainLangGraphFeature()
        feature.before_apply(ctx)

        assert "langchain-google-genai >= 3.0.3" in feature.python_dependencies
        assert feature.model_provider_name == "gemini"


class TestOpenAIAgentsFeature:
    """Tests for OpenAIAgentsFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert OpenAIAgentsFeature.feature_dir_name == SDKProvider.OPENAI_AGENTS

    def test_default_dependencies(self):
        """Test default dependencies are set."""
        assert "openai-agents>=0.4.2" in OpenAIAgentsFeature.python_dependencies

    def test_runtime_only_sets_model_provider_name(self, tmp_path):
        """Test runtime_only mode sets model_provider_name."""
        ctx = create_context(
            tmp_path, SDKProvider.OPENAI_AGENTS, ModelProvider.OpenAI, TemplateDirSelection.RUNTIME_ONLY
        )
        feature = OpenAIAgentsFeature()
        feature.before_apply(ctx)

        assert feature.model_provider_name == "openai"

    def test_monorepo_no_model_provider_name(self, tmp_path):
        """Test monorepo mode does not set model_provider_name."""
        ctx = create_context(tmp_path, SDKProvider.OPENAI_AGENTS, ModelProvider.OpenAI, TemplateDirSelection.MONOREPO)
        feature = OpenAIAgentsFeature()
        feature.before_apply(ctx)

        assert feature.model_provider_name is None


class TestGoogleADKFeature:
    """Tests for GoogleADKFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert GoogleADKFeature.feature_dir_name == SDKProvider.GOOGLE_ADK

    def test_default_dependencies(self):
        """Test default dependencies are set."""
        assert "google-adk>=1.17.0" in GoogleADKFeature.python_dependencies

    def test_runtime_only_sets_model_provider_name(self, tmp_path):
        """Test runtime_only mode sets model_provider_name."""
        ctx = create_context(tmp_path, SDKProvider.GOOGLE_ADK, ModelProvider.Gemini, TemplateDirSelection.RUNTIME_ONLY)
        feature = GoogleADKFeature()
        feature.before_apply(ctx)

        assert feature.model_provider_name == "gemini"

    def test_monorepo_no_model_provider_name(self, tmp_path):
        """Test monorepo mode does not set model_provider_name."""
        ctx = create_context(tmp_path, SDKProvider.GOOGLE_ADK, ModelProvider.Gemini, TemplateDirSelection.MONOREPO)
        feature = GoogleADKFeature()
        feature.before_apply(ctx)

        assert feature.model_provider_name is None


class TestAutogenFeature:
    """Tests for AutogenFeature class."""

    def test_feature_dir_name(self):
        """Test that feature_dir_name is set correctly."""
        assert AutogenFeature.feature_dir_name == SDKProvider.AUTOGEN

    def test_monorepo_dependencies(self, tmp_path):
        """Test monorepo mode dependencies."""
        ctx = create_context(tmp_path, SDKProvider.AUTOGEN, ModelProvider.Bedrock, TemplateDirSelection.MONOREPO)
        feature = AutogenFeature()
        feature.before_apply(ctx)

        assert "autogen-agentchat>=0.7.5" in feature.python_dependencies
        assert "autogen-ext[bedrock]>=0.7.5" in feature.python_dependencies
        assert "autogen-ext[mcp]>=0.7.5" in feature.python_dependencies

    def test_runtime_only_bedrock_dependencies(self, tmp_path):
        """Test runtime_only mode with Bedrock dependencies."""
        ctx = create_context(tmp_path, SDKProvider.AUTOGEN, ModelProvider.Bedrock, TemplateDirSelection.RUNTIME_ONLY)
        feature = AutogenFeature()
        feature.before_apply(ctx)

        assert "autogen-ext[anthropic]>=0.7.5" in feature.python_dependencies
        assert feature.model_provider_name == "bedrock"

    def test_runtime_only_openai_dependencies(self, tmp_path):
        """Test runtime_only mode with OpenAI dependencies."""
        ctx = create_context(tmp_path, SDKProvider.AUTOGEN, ModelProvider.OpenAI, TemplateDirSelection.RUNTIME_ONLY)
        feature = AutogenFeature()
        feature.before_apply(ctx)

        assert "autogen-ext[openai]>=0.7.5" in feature.python_dependencies
        assert feature.model_provider_name == "openai"

    def test_runtime_only_anthropic_dependencies(self, tmp_path):
        """Test runtime_only mode with Anthropic dependencies."""
        ctx = create_context(tmp_path, SDKProvider.AUTOGEN, ModelProvider.Anthropic, TemplateDirSelection.RUNTIME_ONLY)
        feature = AutogenFeature()
        feature.before_apply(ctx)

        assert "autogen-ext[anthropic]>=0.7.5" in feature.python_dependencies
        assert feature.model_provider_name == "anthropic"

    def test_runtime_only_gemini_dependencies(self, tmp_path):
        """Test runtime_only mode with Gemini uses OpenAI client."""
        ctx = create_context(tmp_path, SDKProvider.AUTOGEN, ModelProvider.Gemini, TemplateDirSelection.RUNTIME_ONLY)
        feature = AutogenFeature()
        feature.before_apply(ctx)

        # Gemini uses OpenAI's client for AutoGen
        assert "autogen-ext[openai]>=0.7.5" in feature.python_dependencies
        assert feature.model_provider_name == "gemini"
