"""Tests for Bedrock AgentCore status operation."""

from unittest.mock import MagicMock, Mock, patch

import pytest

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

    def test_status_with_deployed_agent(self, mock_boto3_clients, tmp_path):
        """Test status for deployed agent with runtime details."""
        # Create config file with deployed agent
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
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock successful runtime responses
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "test-agent-id",
            "agentRuntimeArn": "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            "status": "READY",
            "createdAt": "2024-01-01T00:00:00Z",
        }

        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {
            "agentRuntimeEndpointArn": (
                "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
            ),
            "status": "READY",
            "endpointUrl": "https://example.com/endpoint",
        }

        result = get_status(config_path)

        # Verify result structure
        assert hasattr(result, "config")
        assert hasattr(result, "agent")
        assert hasattr(result, "endpoint")

        # Verify config info
        assert result.config.name == "test-agent"
        assert result.config.entrypoint == "test.py"
        assert result.config.region == "us-west-2"
        assert result.config.account == "123456789012"
        assert result.config.execution_role == "arn:aws:iam::123456789012:role/TestRole"
        assert result.config.agent_id == "test-agent-id"
        assert result.config.agent_arn == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"

        # Verify agent details
        assert result.agent is not None
        assert result.agent["status"] == "READY"
        assert result.agent["agentRuntimeId"] == "test-agent-id"

        # Verify endpoint details
        assert result.endpoint is not None
        assert result.endpoint["status"] == "READY"
        assert "endpointUrl" in result.endpoint

        # Verify Bedrock AgentCore client was called
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.assert_called_once_with(
            agentRuntimeId="test-agent-id"
        )
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.assert_called_once_with(
            agentRuntimeId="test-agent-id", endpointName="DEFAULT"
        )

    def test_status_not_deployed(self, tmp_path):
        """Test status for non-deployed agent."""
        # Create config file without deployment info
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),  # No agent_id/agent_arn
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        result = get_status(config_path)

        # Verify config info is populated
        assert result.config.name == "test-agent"
        assert result.config.agent_id is None
        assert result.config.agent_arn is None

        # Verify agent/endpoint details are None (not deployed)
        assert result.agent is None
        assert result.endpoint is None

    def test_status_runtime_error(self, mock_boto3_clients, tmp_path):
        """Test status with runtime API errors."""
        # Create config file with deployed agent
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock runtime API errors
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.side_effect = Exception("Agent not found")
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.side_effect = Exception(
            "Endpoint not accessible"
        )

        result = get_status(config_path)

        # Verify config info is still populated
        assert result.config.name == "test-agent"
        assert result.config.agent_id == "test-agent-id"

        # Verify error details are captured
        assert result.agent is not None
        assert result.agent["error"] == "Agent not found"
        assert result.endpoint is not None
        assert result.endpoint["error"] == "Endpoint not accessible"

    def test_status_missing_config(self, tmp_path):
        """Test status fails when config file not found."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            get_status(nonexistent_config)

    def test_status_client_initialization_error(self, tmp_path):
        """Test status with Bedrock AgentCore client initialization failure."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock client initialization failure
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.status.BedrockAgentCoreClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Failed to initialize client")

            result = get_status(config_path)

            # Verify error is captured
            assert result.agent is not None
            assert "Failed to initialize Bedrock AgentCore client" in result.agent["error"]
            assert result.endpoint is not None
            assert "Failed to initialize Bedrock AgentCore client" in result.endpoint["error"]

    def test_status_partial_failure(self, mock_boto3_clients, tmp_path):
        """Test status when agent call succeeds but endpoint call fails."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock partial success
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "test-agent-id",
            "status": "READY",
        }
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.side_effect = Exception("Endpoint error")

        result = get_status(config_path)

        # Verify agent succeeded
        assert result.agent is not None
        assert result.agent["status"] == "READY"
        assert result.agent["agentRuntimeId"] == "test-agent-id"

        # Verify endpoint failed
        assert result.endpoint is not None
        assert result.endpoint["error"] == "Endpoint error"

    def test_status_config_info_creation(self, mock_boto3_clients, tmp_path):
        """Test StatusConfigInfo creation with all fields."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="my-test-agent",
            entrypoint="src/handler.py",
            aws=AWSConfig(
                region="eu-west-1",
                account="987654321098",
                execution_role="arn:aws:iam::987654321098:role/MyCustomRole",
                ecr_repository="987654321098.dkr.ecr.eu-west-1.amazonaws.com/my-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="my-agent-id-123",
                agent_arn="arn:aws:bedrock_agentcore:eu-west-1:987654321098:agent-runtime/my-agent-id-123",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="my-test-agent", agents={"my-test-agent": agent_config}
        )
        save_config(project_config, config_path)

        # Mock runtime responses so the test doesn't make real API calls
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "my-agent-id-123",
            "status": "READY",
        }
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

        result = get_status(config_path)

        # Verify all config fields are properly mapped
        assert result.config.name == "my-test-agent"
        assert result.config.entrypoint == "src/handler.py"
        assert result.config.region == "eu-west-1"
        assert result.config.account == "987654321098"
        assert result.config.execution_role == "arn:aws:iam::987654321098:role/MyCustomRole"
        assert result.config.ecr_repository == "987654321098.dkr.ecr.eu-west-1.amazonaws.com/my-repo"
        assert result.config.agent_id == "my-agent-id-123"
        assert (
            result.config.agent_arn == "arn:aws:bedrock_agentcore:eu-west-1:987654321098:agent-runtime/my-agent-id-123"
        )

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

        # Mock memory manager with the NEW methods
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            # Mock the three methods that status.py actually calls
            mock_memory_manager.get_memory_status.return_value = "ACTIVE"
            mock_memory_manager.get_memory.return_value = {
                "id": "mem-12345",
                "name": "test_memory",
                "description": None,
                "eventExpiryDuration": 30,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
            }
            mock_memory_manager.get_memory_strategies.return_value = [
                {
                    "strategyId": "strat-1",
                    "name": "UserPreferences",
                    "type": "USER_PREFERENCE",
                    "status": "ACTIVE",
                    "namespaces": [],
                },
                {
                    "strategyId": "strat-2",
                    "name": "SemanticFacts",
                    "type": "SEMANTIC",
                    "status": "ACTIVE",
                    "namespaces": [],
                },
            ]

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
                mode="STM_AND_LTM",
                memory_name="test-agent-memory",
                memory_id="mem-12345",
                memory_arn="arn:aws:bedrock-memory:us-west-2:123456789012:memory/mem-12345",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock memory manager with the NEW methods
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            mock_memory_manager.get_memory_status.return_value = "CREATING"
            mock_memory_manager.get_memory.return_value = {
                "id": "mem-12345",
                "name": "test-agent-memory",
                "description": None,
                "eventExpiryDuration": None,
                "createdAt": None,
                "updatedAt": None,
            }
            mock_memory_manager.get_memory_strategies.return_value = []

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
            assert result.config.memory_enabled is False
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

        # Mock memory manager with the NEW methods
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
        ) as mock_memory_manager_class:
            mock_memory_manager = Mock()

            mock_memory_manager.get_memory_status.return_value = "FAILED"
            mock_memory_manager.get_memory.return_value = {
                "id": "mem-12345",
                "name": "test-agent-memory",
                "description": None,
                "eventExpiryDuration": None,
                "createdAt": None,
                "updatedAt": None,
            }
            mock_memory_manager.get_memory_strategies.return_value = []

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

            # Mock the three methods - no strategies for STM only
            mock_memory_manager.get_memory_status.return_value = "ACTIVE"
            mock_memory_manager.get_memory.return_value = {
                "id": "mem-12345",
                "name": "test_memory",
                "description": None,
                "eventExpiryDuration": None,
                "createdAt": None,
                "updatedAt": None,
            }
            mock_memory_manager.get_memory_strategies.return_value = []  # No strategies

            mock_memory_manager_class.return_value = mock_memory_manager

            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

            result = get_status(config_path)

            assert result.config.memory_id == "mem-12345"
            assert result.config.memory_type == "STM only"

    def test_status_with_vpc_configuration(self, mock_boto3_clients, tmp_path):
        """Test status displays VPC network configuration."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                        security_groups=["sg-abc123xyz789", "sg-def456ghi012"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock EC2 client for VPC ID retrieval
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123456"}]
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.status.BedrockAgentCoreClient"
            ) as mock_client_class,
        ):
            # Setup mock client to return dicts (not Mock objects)
            mock_client = MagicMock()
            mock_client.get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_client.get_agent_runtime_endpoint.return_value = {"status": "READY"}
            mock_client_class.return_value = mock_client

            result = get_status(config_path)

            # Verify VPC configuration is included in status
            assert result.config.network_mode == "VPC"
            assert result.config.network_subnets == ["subnet-abc123def456", "subnet-xyz789ghi012"]
            assert result.config.network_security_groups == ["sg-abc123xyz789", "sg-def456ghi012"]

    def test_status_with_public_network_configuration(self, mock_boto3_clients, tmp_path):
        """Test status displays PUBLIC network configuration."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # REPLACE THIS SECTION:
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.status.BedrockAgentCoreClient"
        ) as mock_client_class:
            # Setup mock client to return dicts (not Mock objects)
            mock_client = MagicMock()
            mock_client.get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_client.get_agent_runtime_endpoint.return_value = {"status": "READY"}
            mock_client_class.return_value = mock_client

            result = get_status(config_path)

            # Verify PUBLIC configuration
            assert result.config.network_mode == "PUBLIC"
            assert result.config.network_subnets is None
            assert result.config.network_security_groups is None
            assert result.config.network_vpc_id is None

    def test_status_vpc_id_retrieval_failure(self, mock_boto3_clients, tmp_path):
        """Test status handles VPC ID retrieval failure gracefully."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock EC2 client to fail
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.side_effect = Exception("EC2 API unavailable")

        # REPLACE THIS SECTION:
        with (
            patch("boto3.client", return_value=mock_ec2),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.status.BedrockAgentCoreClient"
            ) as mock_client_class,
        ):
            # Setup mock client to return dicts (not Mock objects)
            mock_client = MagicMock()
            mock_client.get_agent_runtime.return_value = {
                "agentRuntimeId": "test-agent-id",
                "status": "READY",
            }
            mock_client.get_agent_runtime_endpoint.return_value = {"status": "READY"}
            mock_client_class.return_value = mock_client

            result = get_status(config_path)

            # Verify VPC info is still populated but VPC ID is None
            assert result.config.network_mode == "VPC"
            assert result.config.network_subnets == ["subnet-abc123def456"]
            assert result.config.network_security_groups == ["sg-abc123xyz789"]
            assert result.config.network_vpc_id is None  # Failed to retrieve
