"""Snapshot tests for runtime_only template generation."""

from unittest.mock import patch

import pytest

from bedrock_agentcore_starter_toolkit.create.constants import ModelProvider, SDKProvider
from bedrock_agentcore_starter_toolkit.create.generate import generate_project

from .test_helper.syrupy_util import snapshot_dir_tree

# Define valid SDK + Model Provider combinations
RUNTIME_SCENARIOS = [
    # Strands with all providers
    pytest.param(SDKProvider.STRANDS, ModelProvider.Bedrock, id="strands-bedrock"),
    pytest.param(SDKProvider.STRANDS, ModelProvider.OpenAI, id="strands-openai"),
    pytest.param(SDKProvider.STRANDS, ModelProvider.Anthropic, id="strands-anthropic"),
    pytest.param(SDKProvider.STRANDS, ModelProvider.Gemini, id="strands-gemini"),
    # LangGraph with all providers
    pytest.param(SDKProvider.LANG_GRAPH, ModelProvider.Bedrock, id="langgraph-bedrock"),
    pytest.param(SDKProvider.LANG_GRAPH, ModelProvider.OpenAI, id="langgraph-openai"),
    pytest.param(SDKProvider.LANG_GRAPH, ModelProvider.Anthropic, id="langgraph-anthropic"),
    pytest.param(SDKProvider.LANG_GRAPH, ModelProvider.Gemini, id="langgraph-gemini"),
    # CrewAI with all providers
    pytest.param(SDKProvider.CREWAI, ModelProvider.Bedrock, id="crewai-bedrock"),
    pytest.param(SDKProvider.CREWAI, ModelProvider.OpenAI, id="crewai-openai"),
    pytest.param(SDKProvider.CREWAI, ModelProvider.Anthropic, id="crewai-anthropic"),
    pytest.param(SDKProvider.CREWAI, ModelProvider.Gemini, id="crewai-gemini"),
    # AutoGen with all providers
    pytest.param(SDKProvider.AUTOGEN, ModelProvider.Bedrock, id="autogen-bedrock"),
    pytest.param(SDKProvider.AUTOGEN, ModelProvider.OpenAI, id="autogen-openai"),
    pytest.param(SDKProvider.AUTOGEN, ModelProvider.Anthropic, id="autogen-anthropic"),
    pytest.param(SDKProvider.AUTOGEN, ModelProvider.Gemini, id="autogen-gemini"),
    # OpenAI Agents - only OpenAI provider
    pytest.param(SDKProvider.OPENAI_AGENTS, ModelProvider.OpenAI, id="openaiagents-openai"),
    # Google ADK - only Gemini provider
    pytest.param(SDKProvider.GOOGLE_ADK, ModelProvider.Gemini, id="googleadk-gemini"),
]


@pytest.mark.parametrize("sdk_provider,model_provider", RUNTIME_SCENARIOS)
def test_runtime_only_snapshots(sdk_provider, model_provider, tmp_path, monkeypatch, snapshot):
    """Test runtime_only template generation for all SDK/model provider combinations."""
    monkeypatch.chdir(tmp_path)

    # Generate project
    with patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message"):
        generate_project(
            name="testProject",
            sdk_provider=sdk_provider,
            iac_provider=None,
            model_provider=model_provider,
            provider_api_key="test-api-key" if model_provider != ModelProvider.Bedrock else None,
            agent_config=None,
            use_venv=False,
            git_init=False,
        )

    project_dir = tmp_path / "testProject"
    assert project_dir.exists()

    # Snapshot the generated project structure
    result = snapshot_dir_tree(project_dir)
    assert result == snapshot
