"""Unit tests for memory configuration in create command."""

from unittest.mock import patch

import pytest
import yaml

from bedrock_agentcore_starter_toolkit.cli.create.commands import _handle_basic_runtime_flow
from bedrock_agentcore_starter_toolkit.cli.create.prompt_util import prompt_memory
from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    MemoryConfig,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.generate import generate_project
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util.create_agentcore_yaml import write_minimal_create_runtime_yaml


class TestPromptMemory:
    """Tests for prompt_memory function."""

    @patch("bedrock_agentcore_starter_toolkit.cli.create.prompt_util.select_one")
    def test_returns_stm_only_when_selected(self, mock_select_one):
        """Test that prompt returns STM_ONLY when user selects Short-term memory."""
        mock_select_one.return_value = "Short-term memory"

        result = prompt_memory()

        assert result == MemoryConfig.STM
        mock_select_one.assert_called_once_with(
            title="What kind of memory should your agent have?",
            options=["None", "Short-term memory", "Long-term and short-term memory"],
        )

    @patch("bedrock_agentcore_starter_toolkit.cli.create.prompt_util.select_one")
    def test_returns_stm_and_ltm_when_selected(self, mock_select_one):
        """Test that prompt returns STM_AND_LTM when user selects combined memory."""
        mock_select_one.return_value = "Long-term and short-term memory"

        result = prompt_memory()

        assert result == MemoryConfig.STM_AND_LTM

    @patch("bedrock_agentcore_starter_toolkit.cli.create.prompt_util.select_one")
    def test_returns_no_memory_when_selected(self, mock_select_one):
        """Test that prompt returns NO_MEMORY when user selects None."""
        mock_select_one.return_value = "None"

        result = prompt_memory()

        assert result == MemoryConfig.NONE

    @patch("bedrock_agentcore_starter_toolkit.cli.create.prompt_util.select_one")
    def test_raises_error_on_unknown_selection(self, mock_select_one):
        """Test that prompt raises ValueError if an unknown option is selected (sanity check)."""
        mock_select_one.return_value = "Super Memory"

        with pytest.raises(ValueError, match="Unknown memory display name"):
            prompt_memory()


class TestHandleBasicRuntimeFlowMemory:
    """Tests for memory logic in _handle_basic_runtime_flow."""

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_model_provider")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_sdk_provider")
    def test_prompts_memory_for_strands_interactive(self, mock_sdk, mock_model, mock_memory):
        """Test that memory is prompted for Strands SDK in interactive mode."""
        mock_sdk.return_value = "Strands"
        mock_model.return_value = ModelProvider.Bedrock
        mock_memory.return_value = MemoryConfig.STM_AND_LTM

        sdk, model, api_key, memory = _handle_basic_runtime_flow(
            sdk=None, model_provider=None, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "Strands"
        assert memory == MemoryConfig.STM_AND_LTM
        mock_memory.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_model_provider")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_sdk_provider")
    def test_default_no_memory_for_strands_non_interactive(self, mock_sdk, mock_model, mock_memory):
        """Test that memory defaults to None (implying NO_MEMORY) in non-interactive mode."""
        mock_sdk.return_value = "Strands"
        mock_model.return_value = ModelProvider.Bedrock

        sdk, model, api_key, memory = _handle_basic_runtime_flow(
            sdk=None, model_provider=None, provider_api_key=None, non_interactive_flag=True
        )

        assert sdk == "Strands"
        assert memory is None
        mock_memory.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_model_provider")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_sdk_provider")
    def test_no_memory_prompt_for_non_strands_sdk(self, mock_sdk, mock_model, mock_memory):
        """Test that memory is not prompted for non-Strands SDKs (returns None)."""
        mock_sdk.return_value = "LangChain_LangGraph"
        mock_model.return_value = ModelProvider.Bedrock

        sdk, model, api_key, memory = _handle_basic_runtime_flow(
            sdk=None, model_provider=None, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "LangChain_LangGraph"
        assert memory is None
        mock_memory.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.ModelProvider")
    def test_memory_prompted_when_sdk_provided_as_strands_interactive(self, mock_model_provider, mock_memory):
        """Test memory is prompted when SDK provided as Strands in interactive mode."""
        mock_model_provider.get_providers_list.return_value = [ModelProvider.Bedrock]
        mock_memory.return_value = MemoryConfig.STM

        sdk, model, api_key, memory = _handle_basic_runtime_flow(
            sdk="Strands", model_provider=ModelProvider.Bedrock, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "Strands"
        assert memory == MemoryConfig.STM
        mock_memory.assert_called_once()


class TestGenerateProjectMemory:
    """Tests for memory parameter in generate_project."""

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    def test_stm_and_ltm_sets_correct_context_fields(
        self, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that memory='STM_AND_LTM' enables memory and sets long_term=True."""
        monkeypatch.chdir(tmp_path)
        captured_context = None

        def capture_context(ctx, *args):
            nonlocal captured_context
            captured_context = ctx

        mock_yaml.side_effect = capture_context

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=MemoryConfig.STM_AND_LTM,
        )

        assert captured_context.memory_enabled is True
        assert captured_context.memory_name == "testProject_Memory"
        assert captured_context.memory_is_long_term is True

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    def test_stm_only_sets_correct_context_fields(
        self, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that memory='STM_ONLY' enables memory but sets long_term=False."""
        monkeypatch.chdir(tmp_path)
        captured_context = None

        def capture_context(ctx, *args):
            nonlocal captured_context
            captured_context = ctx

        mock_yaml.side_effect = capture_context

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=MemoryConfig.STM,
        )

        assert captured_context.memory_enabled is True
        assert captured_context.memory_name == "testProject_Memory"
        assert captured_context.memory_is_long_term is False

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    def test_no_memory_disables_context_fields(
        self, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that memory='NO_MEMORY' disables memory in ProjectContext."""
        monkeypatch.chdir(tmp_path)
        captured_context = None

        def capture_context(ctx, *args):
            nonlocal captured_context
            captured_context = ctx

        mock_yaml.side_effect = capture_context

        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            memory=MemoryConfig.NONE,
        )

        assert captured_context.memory_enabled is False


class TestWriteMinimalCreateRuntimeYamlMemory:
    """Tests for memory configuration in write_minimal_create_runtime_yaml."""

    def _create_runtime_context(self, tmp_path, memory_enabled=False, memory_is_long_term=False):
        """Helper to create a ProjectContext for runtime testing."""
        output_dir = tmp_path / "test-project"
        output_dir.mkdir(parents=True, exist_ok=True)
        src_dir = output_dir / "src"
        src_dir.mkdir(exist_ok=True)

        return ProjectContext(
            name="testProject",
            output_dir=output_dir,
            src_dir=src_dir,
            entrypoint_path=src_dir / "main.py",
            sdk_provider="Strands",
            iac_provider=None,
            model_provider=ModelProvider.Bedrock,
            template_dir_selection=TemplateDirSelection.RUNTIME_ONLY,
            runtime_protocol=RuntimeProtocol.HTTP,
            deployment_type=DeploymentType.DIRECT_CODE_DEPLOY,
            python_dependencies=[],
            agent_name="testProject_Agent",
            memory_enabled=memory_enabled,
            memory_name="testProject_Memory" if memory_enabled else None,
            memory_event_expiry_days=30 if memory_enabled else None,
            memory_is_long_term=memory_is_long_term,
            api_key_env_var_name=None,
        )

    def test_memory_config_included_when_enabled_with_ltm(self, tmp_path):
        """Test that memory config is included in YAML when memory is enabled with LTM."""
        ctx = self._create_runtime_context(tmp_path, memory_enabled=True, memory_is_long_term=True)
        yaml_path = write_minimal_create_runtime_yaml(ctx, MemoryConfig.STM_AND_LTM)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_data = data["agents"]["testProject_Agent"]
        assert "memory" in agent_data
        assert agent_data["memory"]["mode"] == "STM_AND_LTM"
        assert agent_data["memory"]["memory_name"] == "testProject_Memory"
        assert agent_data["memory"]["event_expiry_days"] == 30

    def test_memory_config_included_when_enabled_stm_only(self, tmp_path):
        """Test that memory config is included with STM_ONLY when memory_is_long_term is False."""
        ctx = self._create_runtime_context(tmp_path, memory_enabled=True, memory_is_long_term=False)
        yaml_path = write_minimal_create_runtime_yaml(ctx, MemoryConfig.STM)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_data = data["agents"]["testProject_Agent"]
        assert "memory" in agent_data
        assert agent_data["memory"]["mode"] == "STM_ONLY"
        assert agent_data["memory"]["memory_name"] == "testProject_Memory"
        assert agent_data["memory"]["event_expiry_days"] == 30

    def test_memory_config_not_included_when_disabled(self, tmp_path):
        """Test that memory config is NOT included in YAML when memory is disabled."""
        ctx = self._create_runtime_context(tmp_path, memory_enabled=False)
        yaml_path = write_minimal_create_runtime_yaml(ctx, None)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_data = data["agents"]["testProject_Agent"]
        if "memory" in agent_data:
            assert agent_data["memory"]["mode"] == "NO_MEMORY"
