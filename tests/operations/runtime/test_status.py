"""Tests for Bedrock AgentCore status operation."""

from unittest.mock import Mock, patch

from bedrock_agentcore_starter_toolkit.operations.runtime.status import get_status
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    MemoryConfig,
    NetworkConfiguration,
    ObservabilityConfig,
)


class TestStatusOperation:
    """Test get_status functionality."""

    # ... (keep all other test methods unchanged until test_status_with_memory_enabled) ...

    def test_status_with_memory_enabled(self, mock_boto3_clients, tmp_path):
        """Test status for agent with memory enabled."""
        # Create config file with deployed agent and memory
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
            memory=MemoryConfig(
                mode="STM_AND_LTM",
                memory_id="mem-12345",
                memory_arn="arn:aws:memory:us-west-2:123456789012:memory/mem-12345",
                memory_name="test_memory",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock memory manager
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            # Create proper mock that matches what status.py expects
            mock_memory = {"status": "ACTIVE", "strategies": [{"name": "UserPreferences"}, {"name": "SemanticFacts"}]}

            mock_memory_manager.get_memory.return_value = mock_memory
            mock_memory_manager_class.return_value = mock_memory_manager

            # Mock Bedrock AgentCore client responses
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

            result = get_status(config_path)

            assert result.config.memory_id == "mem-12345"
            assert result.config.memory_enabled is True
            assert result.config.memory_type == "STM+LTM (2 strategies)"
            assert result.config.memory_status == "ACTIVE"

    def test_status_with_memory_provisioning(self, mock_boto3_clients, tmp_path):
        """Test status for agent with memory in provisioning state."""
        # Create config file with deployed agent and memory
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
            memory=MemoryConfig(
                mode="STM_AND_LTM",  # Changed from enabled=True, enable_ltm=True
                memory_name="test-agent-memory",
                memory_id="mem-12345",
                memory_arn="arn:aws:bedrock-memory:us-west-2:123456789012:memory/mem-12345",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock memory manager
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            mock_memory = {"status": "CREATING", "strategies": []}

            mock_memory_manager.get_memory.return_value = mock_memory
            mock_memory_manager_class.return_value = mock_memory_manager

            # Mock Bedrock AgentCore client responses
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

            # Get status
            result = get_status(config_path)

            # Verify provisioning memory information
            assert result.config.memory_id == "mem-12345"
            assert result.config.memory_enabled is False  # Not ready yet
            assert result.config.memory_type == "STM+LTM (provisioning...)"
            assert result.config.memory_status == "CREATING"

    def test_status_with_memory_error(self, mock_boto3_clients, tmp_path):
        """Test status for agent with memory in error state."""
        # Create config file with deployed agent and memory
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
            memory=MemoryConfig(
                mode="STM_AND_LTM",  # Changed from enabled=True, enable_ltm=True
                memory_name="test-agent-memory",
                memory_id="mem-12345",
                memory_arn="arn:aws:bedrock-memory:us-west-2:123456789012:memory/mem-12345",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock memory manager to throw exception
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()
            mock_memory_manager.get_memory.side_effect = Exception("Memory access denied")
            mock_memory_manager_class.return_value = mock_memory_manager

            # Mock Bedrock AgentCore client responses
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

            result = get_status(config_path)

            # Check error handling
            assert result.config.memory_enabled is False
            assert "Error checking: Memory access denied" in result.config.memory_type

    def test_status_with_memory_failed_state(self, mock_boto3_clients, tmp_path):
        """Test status for agent with memory in FAILED state."""
        # Create config file with deployed agent and memory
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
            memory=MemoryConfig(
                mode="STM_AND_LTM",
                memory_name="test-agent-memory",
                memory_id="mem-12345",
                memory_arn="arn:aws:bedrock-memory:us-west-2:123456789012:memory/mem-12345",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock memory manager
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            mock_memory = {
                "id": "mem-12345",
                "name": "test-agent-memory",
                "status": "FAILED",
                "strategies": [],
                "description": None,
                "eventExpiryDuration": None,
                "createdAt": None,
                "updatedAt": None,
            }

            mock_memory_manager.get_memory.return_value = mock_memory
            mock_memory_manager_class.return_value = mock_memory_manager

            # Mock Bedrock AgentCore client responses
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

            # Get status
            result = get_status(config_path)

            # Verify failed memory information
            assert result.config.memory_id == "mem-12345"
            assert result.config.memory_enabled is False
            assert result.config.memory_type == "Error (FAILED)"
            assert result.config.memory_status == "FAILED"

    def test_status_with_memory_no_strategies(self, mock_boto3_clients, tmp_path):
        """Test status with memory but no strategies (covers line 89-90)."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
            memory=MemoryConfig(
                mode="STM_ONLY",
                memory_id="mem-12345",
                memory_arn="arn:aws:memory:us-west-2:123456789012:memory/mem-12345",
                memory_name="test_memory",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            # Return dictionary with no strategies
            mock_memory = {
                "id": "mem-12345",
                "status": "ACTIVE",
                # No strategies key - test handling of missing field
            }

            mock_memory_manager.get_memory.return_value = mock_memory
            mock_memory_manager_class.return_value = mock_memory_manager

            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

            result = get_status(config_path)

            assert result.config.memory_id == "mem-12345"
            assert result.config.memory_type == "STM only"
