"""
Unit tests for the Memory Manager with DynamoDB integration.
"""

import pytest
import boto3
from moto import mock_dynamodb
from datetime import datetime, timedelta
from decimal import Decimal

from .memory_manager import MemoryManager
from .models import (
    Transaction, DecisionContext, UserBehaviorProfile, FraudPattern,
    RiskProfile, Location, DeviceInfo, FraudDecision, RiskLevel
)


@pytest.fixture
def mock_dynamodb_setup():
    """Set up mock DynamoDB for testing."""
    with mock_dynamodb():
        # Create memory manager with local endpoint
        memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
        
        # Set up tables
        success = memory_manager.setup_tables()
        assert success, "Failed to set up DynamoDB tables"
        
        yield memory_manager


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return Transaction(
        id="tx_123456",
        user_id="user_789",
        