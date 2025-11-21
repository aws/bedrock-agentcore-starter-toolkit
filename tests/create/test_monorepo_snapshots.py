"""Snapshot tests for monorepo template generation from scratch."""

from unittest.mock import patch

import pytest

from bedrock_agentcore_starter_toolkit.create.constants import IACProvider, ModelProvider, SDKProvider
from bedrock_agentcore_starter_toolkit.create.generate import generate_project

from .test_helper.syrupy_util import snapshot_dir_tree

# Define SDK + IaC Provider combinations for monorepo mode
MONOREPO_SCENARIOS_WITHOUT_EXISTING_CONFIG = [
    # Strands with CDK and Terraform
    pytest.param(SDKProvider.STRANDS, IACProvider.CDK, id="strands-cdk"),
    pytest.param(SDKProvider.STRANDS, IACProvider.TERRAFORM, id="strands-terraform"),
    # LangGraph with CDK and Terraform
    pytest.param(SDKProvider.LANG_GRAPH, IACProvider.CDK, id="langgraph-cdk"),
    pytest.param(SDKProvider.LANG_GRAPH, IACProvider.TERRAFORM, id="langgraph-terraform"),
    # CrewAI with CDK and Terraform
    pytest.param(SDKProvider.CREWAI, IACProvider.CDK, id="crewai-cdk"),
    pytest.param(SDKProvider.CREWAI, IACProvider.TERRAFORM, id="crewai-terraform"),
    # AutoGen with CDK and Terraform
    pytest.param(SDKProvider.AUTOGEN, IACProvider.CDK, id="autogen-cdk"),
    pytest.param(SDKProvider.AUTOGEN, IACProvider.TERRAFORM, id="autogen-terraform"),
    # OpenAI Agents with CDK and Terraform
    pytest.param(SDKProvider.OPENAI_AGENTS, IACProvider.CDK, id="openaiagents-cdk"),
    pytest.param(SDKProvider.OPENAI_AGENTS, IACProvider.TERRAFORM, id="openaiagents-terraform"),
    # Google ADK with CDK and Terraform
    pytest.param(SDKProvider.GOOGLE_ADK, IACProvider.CDK, id="googleadk-cdk"),
    pytest.param(SDKProvider.GOOGLE_ADK, IACProvider.TERRAFORM, id="googleadk-terraform"),
]


@pytest.mark.parametrize("sdk_provider,iac_provider", MONOREPO_SCENARIOS_WITHOUT_EXISTING_CONFIG)
def test_monorepo_snapshots(sdk_provider, iac_provider, tmp_path, monkeypatch, snapshot, mock_container_runtime):
    """Test monorepo template generation for all SDK/IaC provider combinations."""
    monkeypatch.chdir(tmp_path)

    # Generate project
    with patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message"):
        generate_project(
            name="testProject",
            sdk_provider=sdk_provider,
            iac_provider=iac_provider,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
        )

    project_dir = tmp_path / "testProject"
    assert project_dir.exists()

    # Snapshot the generated project structure
    result = snapshot_dir_tree(project_dir)
    assert result == snapshot
