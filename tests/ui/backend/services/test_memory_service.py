"""Tests for MemoryService."""

import pytest
from unittest.mock import Mock, patch
from bedrock_agentcore_starter_toolkit.ui.backend.services.memory_service import (
    MemoryService,
)


@pytest.fixture
def mock_memory_manager():
    """Create a mock MemoryManager."""
    manager = Mock()
    return manager


def test_memory_service_init():
    """Test MemoryService initialization."""
    service = MemoryService(region="us-east-1")

    assert service.region == "us-east-1"
    assert service._memory_manager is None


def test_memory_service_init_no_region():
    """Test MemoryService initialization without region."""
    service = MemoryService()

    assert service.region is None


def test_get_memory_manager(mock_memory_manager):
    """Test _get_memory_manager creates manager."""
    service = MemoryService(region="us-east-1")

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.memory_service.MemoryManager"
    ) as mock_manager_class:
        mock_manager_class.return_value = mock_memory_manager

        manager = service._get_memory_manager()

        assert manager == mock_memory_manager
        mock_manager_class.assert_called_once_with(region_name="us-east-1")


def test_get_memory_manager_no_region():
    """Test _get_memory_manager without region raises error."""
    service = MemoryService()

    with pytest.raises(ValueError, match="Region not configured"):
        service._get_memory_manager()


def test_get_memory_manager_cached(mock_memory_manager):
    """Test _get_memory_manager caches manager."""
    service = MemoryService(region="us-east-1")

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.memory_service.MemoryManager"
    ) as mock_manager_class:
        mock_manager_class.return_value = mock_memory_manager

        manager1 = service._get_memory_manager()
        manager2 = service._get_memory_manager()

        assert manager1 == manager2
        mock_manager_class.assert_called_once()


def test_get_memory_details(mock_memory_manager):
    """Test get_memory_details."""
    service = MemoryService(region="us-east-1")

    mock_memory = {
        "id": "memory-123",
        "name": "Test Memory",
        "status": "ENABLED",
        "eventExpiryDuration": 30,
        "strategies": [
            {
                "id": "strategy-1",
                "name": "Semantic Strategy",
                "type": "SEMANTIC",
                "status": "ENABLED",
            }
        ],
    }

    mock_memory_manager.get_memory.return_value = mock_memory

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.memory_service.MemoryManager"
    ) as mock_manager_class:
        mock_manager_class.return_value = mock_memory_manager

        result = service.get_memory_details("memory-123")

        assert result["memory_id"] == "memory-123"
        assert result["name"] == "Test Memory"
        assert result["status"] == "ENABLED"
        assert result["event_expiry_days"] == 30
        assert result["memory_type"] == "short-term-and-long-term"
        assert len(result["strategies"]) == 1


def test_get_memory_details_exception(mock_memory_manager):
    """Test get_memory_details with exception."""
    service = MemoryService(region="us-east-1")

    mock_memory_manager.get_memory.side_effect = Exception("Memory not found")

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.memory_service.MemoryManager"
    ) as mock_manager_class:
        mock_manager_class.return_value = mock_memory_manager

        with pytest.raises(Exception, match="Memory not found"):
            service.get_memory_details("memory-123")


def test_format_strategies():
    """Test _format_strategies."""
    service = MemoryService(region="us-east-1")

    strategies = [
        {
            "id": "strategy-1",
            "name": "Semantic Strategy",
            "type": "SEMANTIC",
            "status": "ENABLED",
            "description": "A semantic strategy",
            "namespaces": ["ns1", "ns2"],
            "configuration": {"key": "value"},
        }
    ]

    result = service._format_strategies(strategies)

    assert len(result) == 1
    assert result[0]["strategy_id"] == "strategy-1"
    assert result[0]["name"] == "Semantic Strategy"
    assert result[0]["type"] == "semantic"
    assert result[0]["status"] == "ENABLED"
    assert result[0]["description"] == "A semantic strategy"
    assert result[0]["namespaces"] == ["ns1", "ns2"]


def test_format_strategies_with_object():
    """Test _format_strategies with object that has get_dict method."""
    service = MemoryService(region="us-east-1")

    mock_strategy = Mock()
    mock_strategy.get_dict.return_value = {
        "id": "strategy-1",
        "name": "Test Strategy",
        "type": "SUMMARIZATION",
        "status": "ENABLED",
    }

    result = service._format_strategies([mock_strategy])

    assert len(result) == 1
    assert result[0]["strategy_id"] == "strategy-1"
    assert result[0]["type"] == "summary"


def test_get_strategy_type_semantic():
    """Test _get_strategy_type for semantic."""
    service = MemoryService(region="us-east-1")

    strategy_data = {"type": "SEMANTIC"}
    assert service._get_strategy_type(strategy_data) == "semantic"


def test_get_strategy_type_summary():
    """Test _get_strategy_type for summary."""
    service = MemoryService(region="us-east-1")

    strategy_data = {"type": "SUMMARIZATION"}
    assert service._get_strategy_type(strategy_data) == "summary"


def test_get_strategy_type_user_preference():
    """Test _get_strategy_type for user preference."""
    service = MemoryService(region="us-east-1")

    strategy_data = {"type": "USER_PREFERENCE"}
    assert service._get_strategy_type(strategy_data) == "user_preference"


def test_get_strategy_type_custom():
    """Test _get_strategy_type for custom."""
    service = MemoryService(region="us-east-1")

    strategy_data = {"type": "CUSTOM"}
    assert service._get_strategy_type(strategy_data) == "custom"


def test_get_strategy_type_from_config():
    """Test _get_strategy_type inferred from configuration."""
    service = MemoryService(region="us-east-1")

    strategy_data = {"configuration": {"semanticConfiguration": {}}}
    assert service._get_strategy_type(strategy_data) == "semantic"

    strategy_data = {"configuration": {"summarizationConfiguration": {}}}
    assert service._get_strategy_type(strategy_data) == "summary"

    strategy_data = {"configuration": {"userPreferenceConfiguration": {}}}
    assert service._get_strategy_type(strategy_data) == "user_preference"

    strategy_data = {"configuration": {"customConfiguration": {}}}
    assert service._get_strategy_type(strategy_data) == "custom"


def test_get_strategy_type_unknown():
    """Test _get_strategy_type for unknown type."""
    service = MemoryService(region="us-east-1")

    strategy_data = {}
    assert service._get_strategy_type(strategy_data) == "unknown"


def test_extract_configuration_custom():
    """Test _extract_configuration for custom strategy."""
    service = MemoryService(region="us-east-1")

    strategy_data = {
        "configuration": {
            "customConfiguration": {
                "extraction": {"key": "value"},
                "consolidation": {"key2": "value2"},
            }
        }
    }

    result = service._extract_configuration(strategy_data)

    assert result["extraction"] == {"key": "value"}
    assert result["consolidation"] == {"key2": "value2"}


def test_extract_configuration_none():
    """Test _extract_configuration with no configuration."""
    service = MemoryService(region="us-east-1")

    strategy_data = {}
    result = service._extract_configuration(strategy_data)

    assert result is None


def test_extract_configuration_other():
    """Test _extract_configuration for non-custom strategy."""
    service = MemoryService(region="us-east-1")

    strategy_data = {"configuration": {"semanticConfiguration": {"key": "value"}}}

    result = service._extract_configuration(strategy_data)

    assert result == {"semanticConfiguration": {"key": "value"}}


def test_determine_memory_type_short_term():
    """Test _determine_memory_type for short-term."""
    service = MemoryService(region="us-east-1")

    strategies = [
        {"type": "summary"},
    ]

    assert service._determine_memory_type(strategies) == "short-term"


def test_determine_memory_type_long_term():
    """Test _determine_memory_type for long-term."""
    service = MemoryService(region="us-east-1")

    strategies = [
        {"type": "semantic"},
    ]

    assert service._determine_memory_type(strategies) == "short-term-and-long-term"


def test_determine_memory_type_user_preference():
    """Test _determine_memory_type with user preference."""
    service = MemoryService(region="us-east-1")

    strategies = [
        {"type": "user_preference"},
    ]

    assert service._determine_memory_type(strategies) == "short-term-and-long-term"


def test_determine_memory_type_mixed():
    """Test _determine_memory_type with mixed strategies."""
    service = MemoryService(region="us-east-1")

    strategies = [
        {"type": "summary"},
        {"type": "semantic"},
    ]

    assert service._determine_memory_type(strategies) == "short-term-and-long-term"


def test_get_memory_details_no_strategies(mock_memory_manager):
    """Test get_memory_details with no strategies."""
    service = MemoryService(region="us-east-1")

    mock_memory = {
        "id": "memory-123",
        "name": "Test Memory",
        "status": "ENABLED",
        "eventExpiryDuration": 90,
        "strategies": [],
    }

    mock_memory_manager.get_memory.return_value = mock_memory

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.memory_service.MemoryManager"
    ) as mock_manager_class:
        mock_manager_class.return_value = mock_memory_manager

        result = service.get_memory_details("memory-123")

        assert result["memory_type"] == "short-term"
        assert result["event_expiry_days"] == 90
