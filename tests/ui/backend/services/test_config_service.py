"""Tests for ConfigService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.ui.backend.services.config_service import (
    ConfigService,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock()
    config.get_agent_config = Mock()

    # Mock agent config
    agent_config = Mock()
    agent_config.name = "test-agent"
    agent_config.bedrock_agentcore = Mock()
    agent_config.bedrock_agentcore.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"
    agent_config.aws = Mock()
    agent_config.aws.region = "us-east-1"
    agent_config.memory = Mock()
    agent_config.memory.memory_id = "memory-123"
    agent_config.authorizer_configuration = {"oauth": "config"}

    config.get_agent_config.return_value = agent_config
    return config


def test_config_service_init_with_path():
    """Test ConfigService initialization with config path."""
    config_path = Path("/tmp/test_config.yaml")

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService(config_path)

        assert service.config_path == config_path
        mock_load.assert_called_once_with(config_path)


def test_config_service_init_without_path():
    """Test ConfigService initialization without config path."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService()

        assert service.config_path == Path.cwd() / "project_config.yaml"


def test_config_service_load_config_success(mock_config):
    """Test successful config loading."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        assert service._config == mock_config
        assert service.is_configured()


def test_config_service_load_config_failure():
    """Test config loading failure."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService()

        assert service._config is None
        assert not service.is_configured()


def test_config_service_load_config_exception():
    """Test config loading with exception."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.side_effect = Exception("Load error")
        service = ConfigService()

        assert service._config is None
        assert not service.is_configured()


def test_get_config(mock_config):
    """Test get_config returns loaded configuration."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        assert service.get_config() == mock_config


def test_get_agent_config(mock_config):
    """Test get_agent_config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        agent_config = service.get_agent_config("test-agent")
        assert agent_config is not None
        mock_config.get_agent_config.assert_called_once_with("test-agent")


def test_get_agent_config_no_config():
    """Test get_agent_config with no config loaded."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService()

        assert service.get_agent_config() is None


def test_get_agent_config_exception(mock_config):
    """Test get_agent_config with exception."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        mock_config.get_agent_config.side_effect = Exception("Error")
        service = ConfigService()

        assert service.get_agent_config() is None


def test_get_agent_name(mock_config):
    """Test get_agent_name."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        name = service.get_agent_name()
        assert name == "test-agent"


def test_get_agent_name_no_config():
    """Test get_agent_name with no config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService()

        assert service.get_agent_name() is None


def test_get_agent_arn(mock_config):
    """Test get_agent_arn."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        arn = service.get_agent_arn()
        assert arn == "arn:aws:bedrock:us-east-1:123456789012:agent/test"


def test_get_agent_arn_no_bedrock_config(mock_config):
    """Test get_agent_arn with no bedrock config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        agent_config = mock_config.get_agent_config.return_value
        agent_config.bedrock_agentcore = None
        service = ConfigService()

        assert service.get_agent_arn() is None


def test_get_region(mock_config):
    """Test get_region."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        region = service.get_region()
        assert region == "us-east-1"


def test_get_region_no_aws_config(mock_config):
    """Test get_region with no AWS config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        agent_config = mock_config.get_agent_config.return_value
        agent_config.aws = None
        service = ConfigService()

        assert service.get_region() is None


def test_get_memory_id(mock_config):
    """Test get_memory_id."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        memory_id = service.get_memory_id()
        assert memory_id == "memory-123"


def test_get_memory_id_no_memory_config(mock_config):
    """Test get_memory_id with no memory config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        agent_config = mock_config.get_agent_config.return_value
        agent_config.memory = None
        service = ConfigService()

        assert service.get_memory_id() is None


def test_has_oauth_config(mock_config):
    """Test has_oauth_config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService()

        assert service.has_oauth_config() is True


def test_has_oauth_config_no_oauth(mock_config):
    """Test has_oauth_config with no OAuth."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        agent_config = mock_config.get_agent_config.return_value
        agent_config.authorizer_configuration = None
        service = ConfigService()

        assert service.has_oauth_config() is False


def test_has_oauth_config_no_config():
    """Test has_oauth_config with no config."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService()

        assert service.has_oauth_config() is False


def test_config_service_init_with_agent_name():
    """Test ConfigService initialization with agent name."""
    config_path = Path("/tmp/test_config.yaml")

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = None
        service = ConfigService(config_path, agent_name="custom-agent")

        assert service.config_path == config_path
        assert service.agent_name == "custom-agent"


def test_get_agent_config_uses_instance_agent_name(mock_config):
    """Test get_agent_config uses instance agent_name when no parameter provided."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService(agent_name="instance-agent")

        service.get_agent_config()
        mock_config.get_agent_config.assert_called_once_with("instance-agent")


def test_get_agent_config_parameter_overrides_instance(mock_config):
    """Test get_agent_config parameter overrides instance agent_name."""
    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.config_service.load_config_if_exists"
    ) as mock_load:
        mock_load.return_value = mock_config
        service = ConfigService(agent_name="instance-agent")

        service.get_agent_config("override-agent")
        mock_config.get_agent_config.assert_called_once_with("override-agent")
