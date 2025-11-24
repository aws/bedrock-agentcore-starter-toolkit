"""Unit tests for memory configuration in create command."""

from unittest.mock import patch

import yaml

from bedrock_agentcore_starter_toolkit.cli.create.commands import _handle_basic_runtime_flow
from bedrock_agentcore_starter_toolkit.cli.create.prompt_util import prompt_memory_enabled
from bedrock_agentcore_starter_toolkit.create.constants import (
    DeploymentType,
    ModelProvider,
    RuntimeProtocol,
    TemplateDirSelection,
)
from bedrock_agentcore_starter_toolkit.create.generate import generate_project
from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util.create_agentcore_yaml import write_minimal_create_runtime_yaml


class TestPromptMemoryEnabled:
    """Tests for prompt_memory_enabled function."""

    @patch("bedrock_agentcore_starter_toolkit.cli.create.prompt_util.select_one")
    def test_returns_true_when_user_selects_yes(self, mock_select_one):
        """Test that prompt returns True when user selects 'Yes' option."""
        mock_select_one.return_value = "Yes, use default memory configuration"

        result = prompt_memory_enabled()

        assert result is True
        mock_select_one.assert_called_once_with(
            title="Do you want to enable memory?", options=["No", "Yes, use default memory configuration"]
        )

    @patch("bedrock_agentcore_starter_toolkit.cli.create.prompt_util.select_one")
    def test_returns_false_when_user_selects_no(self, mock_select_one):
        """Test that prompt returns False when user selects 'No' option."""
        mock_select_one.return_value = "No"

        result = prompt_memory_enabled()

        assert result is False
        mock_select_one.assert_called_once_with(
            title="Do you want to enable memory?", options=["No", "Yes, use default memory configuration"]
        )


class TestHandleBasicRuntimeFlowMemory:
    """Tests for memory logic in _handle_basic_runtime_flow."""

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory_enabled")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_model_provider")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_sdk_provider")
    def test_prompts_memory_for_strands_interactive(self, mock_sdk, mock_model, mock_memory):
        """Test that memory is prompted for Strands SDK in interactive mode."""
        mock_sdk.return_value = "Strands"
        mock_model.return_value = ModelProvider.Bedrock
        mock_memory.return_value = True

        sdk, model, api_key, enable_memory = _handle_basic_runtime_flow(
            sdk=None, model_provider=None, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "Strands"
        assert enable_memory is True
        mock_memory.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory_enabled")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_model_provider")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_sdk_provider")
    def test_no_memory_prompt_for_strands_non_interactive(self, mock_sdk, mock_model, mock_memory):
        """Test that memory is not prompted in non-interactive mode."""
        mock_sdk.return_value = "Strands"
        mock_model.return_value = ModelProvider.Bedrock

        sdk, model, api_key, enable_memory = _handle_basic_runtime_flow(
            sdk=None, model_provider=None, provider_api_key=None, non_interactive_flag=True
        )

        assert sdk == "Strands"
        assert enable_memory is False
        mock_memory.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory_enabled")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_model_provider")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_sdk_provider")
    def test_no_memory_prompt_for_non_strands_sdk(self, mock_sdk, mock_model, mock_memory):
        """Test that memory is not prompted for non-Strands SDKs."""
        mock_sdk.return_value = "LangChain"
        mock_model.return_value = ModelProvider.Bedrock

        sdk, model, api_key, enable_memory = _handle_basic_runtime_flow(
            sdk=None, model_provider=None, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "LangChain"
        assert enable_memory is False
        mock_memory.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory_enabled")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.ModelProvider")
    def test_memory_disabled_when_sdk_provided_as_langchain(self, mock_model_provider, mock_memory):
        """Test memory is disabled when SDK is provided as LangChain (not Strands)."""
        mock_model_provider.get_providers_list.return_value = [ModelProvider.Bedrock]

        sdk, model, api_key, enable_memory = _handle_basic_runtime_flow(
            sdk="LangChain", model_provider=ModelProvider.Bedrock, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "LangChain"
        assert enable_memory is False
        mock_memory.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.prompt_memory_enabled")
    @patch("bedrock_agentcore_starter_toolkit.cli.create.commands.ModelProvider")
    def test_memory_prompted_when_sdk_provided_as_strands_interactive(self, mock_model_provider, mock_memory):
        """Test memory is prompted when SDK provided as Strands in interactive mode."""
        mock_model_provider.get_providers_list.return_value = [ModelProvider.Bedrock]
        mock_memory.return_value = True

        sdk, model, api_key, enable_memory = _handle_basic_runtime_flow(
            sdk="Strands", model_provider=ModelProvider.Bedrock, provider_api_key=None, non_interactive_flag=False
        )

        assert sdk == "Strands"
        assert enable_memory is True
        mock_memory.assert_called_once()


class TestGenerateProjectMemory:
    """Tests for memory parameter in generate_project."""

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    def test_memory_enabled_sets_context_fields(
        self, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that enable_memory=True sets correct ProjectContext fields."""
        monkeypatch.chdir(tmp_path)

        # We need to capture the context passed to write_minimal_create_runtime_yaml
        captured_context = None

        def capture_context(ctx):
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
            enable_memory=True,
        )

        # Verify memory fields were set correctly
        assert captured_context is not None
        assert captured_context.memory_enabled is True
        assert captured_context.memory_name == "testProject_Memory"
        assert captured_context.memory_event_expiry_days == 30
        assert captured_context.memory_is_long_term is True  # Default: STM + LTM

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    def test_memory_disabled_clears_context_fields(
        self, mock_yaml, mock_baseline, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that enable_memory=False disables memory in ProjectContext."""
        monkeypatch.chdir(tmp_path)

        captured_context = None

        def capture_context(ctx):
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
            enable_memory=False,
        )

        # Verify memory is disabled
        assert captured_context is not None
        assert captured_context.memory_enabled is False

    @patch("bedrock_agentcore_starter_toolkit.create.generate.emit_create_completed_message")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.create_and_init_venv")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_iac_generation")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_with_iac_project_yaml")
    @patch("bedrock_agentcore_starter_toolkit.create.generate._apply_baseline_and_sdk_features")
    @patch("bedrock_agentcore_starter_toolkit.create.generate.write_minimal_create_runtime_yaml")
    def test_memory_not_applied_for_iac_provider(
        self, mock_runtime_yaml, mock_baseline, mock_iac_yaml, mock_iac_gen, mock_venv, mock_emit, tmp_path, monkeypatch
    ):
        """Test that enable_memory doesn't affect IAC provider flow."""
        monkeypatch.chdir(tmp_path)

        # For IAC provider, write_minimal_create_runtime_yaml should not be called
        generate_project(
            name="testProject",
            sdk_provider="Strands",
            iac_provider="CDK",
            model_provider=ModelProvider.Bedrock,
            provider_api_key=None,
            agent_config=None,
            use_venv=False,
            git_init=False,
            enable_memory=True,
        )

        # write_minimal_create_runtime_yaml should not be called for IAC flow
        mock_runtime_yaml.assert_not_called()
        # write_minimal_create_with_iac_project_yaml should be called instead
        mock_iac_yaml.assert_called_once()


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
        yaml_path = write_minimal_create_runtime_yaml(ctx)

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
        yaml_path = write_minimal_create_runtime_yaml(ctx)

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
        yaml_path = write_minimal_create_runtime_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_data = data["agents"]["testProject_Agent"]
        # Memory key should not exist when disabled, or if it exists, it should be NO_MEMORY
        if "memory" in agent_data:
            # If memory key exists (from default MemoryConfig), it should be NO_MEMORY mode
            assert agent_data["memory"]["mode"] == "NO_MEMORY"
        # Otherwise, memory key should not exist at all (preferred behavior)
        # Both are acceptable behaviors

    def test_yaml_file_created_with_memory(self, tmp_path):
        """Test that YAML file is created successfully with memory configuration."""
        ctx = self._create_runtime_context(tmp_path, memory_enabled=True, memory_is_long_term=True)
        yaml_path = write_minimal_create_runtime_yaml(ctx)

        assert yaml_path.exists()
        assert yaml_path.name == ".bedrock_agentcore.yaml"

    def test_default_memory_uses_stm_and_ltm(self, tmp_path):
        """Test that default memory configuration uses both STM and LTM."""
        ctx = self._create_runtime_context(tmp_path, memory_enabled=True, memory_is_long_term=True)
        yaml_path = write_minimal_create_runtime_yaml(ctx)

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        agent_data = data["agents"]["testProject_Agent"]
        # Default configuration should be STM_AND_LTM
        assert agent_data["memory"]["mode"] == "STM_AND_LTM"
