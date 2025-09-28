"""
Unit tests for the Transaction Analyzer Agent.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from .transaction_analyzer import TransactionAnalyzerAgent, VelocityWindow, TransactionAnalysisResult
from .base_agent import AgentConfiguration, AgentCapability, AgentStatus
from memory_system.models import Transaction, FraudDecision, Location, DeviceInfo
from memory_system.memory_manager import MemoryManager
from reasoning_engine.chain_of_thought import ReasoningEngine


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager."""
    return Mock(spec=MemoryManager)


@pytest.fixture
def mock_reasoning_engine():
    """Create a mock reasoning engine."""
    return Mock(spec=ReasoningEngine)


@pytest.fixture
def agent_config():
    """Create agent configuration for testing."""
    return AgentConfiguration(
 