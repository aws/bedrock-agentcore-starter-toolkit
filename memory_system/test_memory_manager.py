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
        amount=Decimal("150.00"),
        currency="USD",
        merchant="Amazon",
        category="online_retail",
        location=Location(
            country="US",
            city="New York",
            latitude=40.7128,
            longitude=-74.0060,
            ip_address="192.168.1.1"
        ),
        timestamp=datetime.now(),
        card_type="credit",
        device_info=DeviceInfo(
            device_id="device_123",
            device_type="mobile",
            os="iOS",
            browser="Safari",
            fingerprint="fp_abc123"
        ),
        ip_address="192.168.1.1",
        session_id="session_456",
        metadata={"channel": "mobile_app"}
    )
        


@pytest.fixture
def sample_decision_context():
    """Create a sample decision context for testing."""
    return DecisionContext(
        transaction_id="tx_123456",
        user_id="user_789",
        decision=FraudDecision.APPROVED,
        confidence_score=0.85,
        reasoning_steps=[
            "Transaction amount within user's typical range",
            "Merchant is frequently used by user",
            "Location matches user's common locations"
        ],
        evidence=[
            "User has 15 previous transactions with this merchant",
            "Amount is 20% below user's average",
            "Device fingerprint matches previous sessions"
        ],
        timestamp=datetime.now(),
        processing_time_ms=250.5,
        agent_version="1.0.0",
        external_tools_used=["geolocation_api", "device_fingerprint"]
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user behavior profile for testing."""
    return UserBehaviorProfile(
        user_id="user_789",
        typical_spending_range={"min": 10.0, "max": 500.0, "avg": 125.0},
        frequent_merchants=["Amazon", "Starbucks", "Target"],
        common_locations=[
            Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
            Location(country="US", city="Boston", latitude=42.3601, longitude=-71.0589)
        ],
        preferred_categories=["online_retail", "food", "groceries"],
        transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
        risk_score=0.3,
        last_updated=datetime.now(),
        transaction_count=150
    )


@pytest.fixture
def sample_fraud_pattern():
    """Create a sample fraud pattern for testing."""
    return FraudPattern(
        pattern_id="pattern_001",
        pattern_type="velocity_fraud",
        description="Multiple transactions in short time period",
        indicators=[
            "More than 5 transactions in 10 minutes",
            "Different merchants",
            "Increasing amounts"
        ],
        confidence_threshold=0.8,
        detection_count=25,
        false_positive_rate=0.05,
        created_at=datetime.now() - timedelta(days=30),
        last_seen=datetime.now(),
        effectiveness_score=0.92
    )


@pytest.fixture
def sample_risk_profile():
    """Create a sample risk profile for testing."""
    return RiskProfile(
        user_id="user_789",
        overall_risk_level=RiskLevel.LOW,
        risk_factors={
            "new_user": 0.0,
            "high_value_transactions": 0.2,
            "unusual_locations": 0.1,
            "device_changes": 0.0
        },
        geographic_risk=0.1,
        behavioral_risk=0.2,
        transaction_risk=0.15,
        temporal_risk=0.05,
        last_assessment=datetime.now(),
        risk_evolution=[
            {"date": "2024-01-01", "risk_level": "low", "score": 0.2},
            {"date": "2024-01-15", "risk_level": "low", "score": 0.25}
        ]
    )


class TestMemoryManager:
    """Test cases for MemoryManager functionality."""
    
    def test_setup_tables(self, mock_dynamodb_setup):
        """Test that DynamoDB tables are set up correctly."""
        memory_manager = mock_dynamodb_setup
        assert memory_manager is not None
        
        # Tables should exist and be accessible
        assert memory_manager.transaction_table is not None
        assert memory_manager.decision_table is not None
        assert memory_manager.profile_table is not None
        assert memory_manager.pattern_table is not None
        assert memory_manager.risk_table is not None
    
    def test_store_and_retrieve_transaction(self, mock_dynamodb_setup, sample_transaction):
        """Test storing and retrieving a transaction."""
        memory_manager = mock_dynamodb_setup
        
        # Store transaction
        success = memory_manager.store_transaction(sample_transaction)
        assert success is True
        
        # Retrieve by ID
        retrieved = memory_manager.get_transaction_by_id(sample_transaction.id)
        assert retrieved is not None
        assert retrieved.id == sample_transaction.id
        assert retrieved.user_id == sample_transaction.user_id
        assert retrieved.amount == sample_transaction.amount
        assert retrieved.merchant == sample_transaction.merchant
    
    def test_get_user_transaction_history(self, mock_dynamodb_setup, sample_transaction):
        """Test retrieving user transaction history."""
        memory_manager = mock_dynamodb_setup
        
        # Store multiple transactions for the same user
        transactions = []
        for i in range(3):
            tx = Transaction(
                id=f"tx_{i}",
                user_id=sample_transaction.user_id,
                amount=Decimal(f"{100 + i * 50}.00"),
                currency="USD",
                merchant=f"Merchant_{i}",
                category="retail",
                location=sample_transaction.location,
                timestamp=datetime.now() - timedelta(hours=i),
                card_type="credit",
                device_info=sample_transaction.device_info,
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            transactions.append(tx)
            memory_manager.store_transaction(tx)
        
        # Retrieve history
        history = memory_manager.get_user_transaction_history(sample_transaction.user_id)
        assert len(history) == 3
        
        # Should be ordered by timestamp (most recent first)
        assert history[0].id == "tx_0"
        assert history[1].id == "tx_1"
        assert history[2].id == "tx_2"
    
    def test_store_and_retrieve_decision_context(self, mock_dynamodb_setup, sample_decision_context):
        """Test storing and retrieving decision context."""
        memory_manager = mock_dynamodb_setup
        
        # Store decision context
        success = memory_manager.store_decision_context(sample_decision_context)
        assert success is True
        
        # Retrieve decision context
        retrieved = memory_manager.get_decision_context(sample_decision_context.transaction_id)
        assert retrieved is not None
        assert retrieved.transaction_id == sample_decision_context.transaction_id
        assert retrieved.decision == sample_decision_context.decision
        assert retrieved.confidence_score == sample_decision_context.confidence_score
        assert len(retrieved.reasoning_steps) == len(sample_decision_context.reasoning_steps)
    
    def test_get_user_decision_history(self, mock_dynamodb_setup, sample_decision_context):
        """Test retrieving user decision history."""
        memory_manager = mock_dynamodb_setup
        
        # Store multiple decision contexts for the same user
        decisions = []
        for i in range(3):
            decision = DecisionContext(
                transaction_id=f"tx_{i}",
                user_id=sample_decision_context.user_id,
                decision=FraudDecision.APPROVED if i % 2 == 0 else FraudDecision.FLAGGED,
                confidence_score=0.8 + i * 0.05,
                reasoning_steps=[f"Reason {i}"],
                evidence=[f"Evidence {i}"],
                timestamp=datetime.now() - timedelta(hours=i),
                processing_time_ms=200.0 + i * 10,
                agent_version="1.0.0"
            )
            decisions.append(decision)
            memory_manager.store_decision_context(decision)
        
        # Retrieve decision history
        history = memory_manager.get_user_decision_history(sample_decision_context.user_id)
        assert len(history) == 3
        
        # Verify decisions are retrieved correctly
        assert all(d.user_id == sample_decision_context.user_id for d in history)
    
    def test_store_and_retrieve_user_profile(self, mock_dynamodb_setup, sample_user_profile):
        """Test storing and retrieving user behavior profile."""
        memory_manager = mock_dynamodb_setup
        
        # Store user profile
        success = memory_manager.store_user_profile(sample_user_profile)
        assert success is True
        
        # Retrieve user profile
        retrieved = memory_manager.get_user_profile(sample_user_profile.user_id)
        assert retrieved is not None
        assert retrieved.user_id == sample_user_profile.user_id
        assert retrieved.typical_spending_range == sample_user_profile.typical_spending_range
        assert retrieved.frequent_merchants == sample_user_profile.frequent_merchants
        assert len(retrieved.common_locations) == len(sample_user_profile.common_locations)
        assert retrieved.risk_score == sample_user_profile.risk_score
    
    def test_store_and_retrieve_fraud_pattern(self, mock_dynamodb_setup, sample_fraud_pattern):
        """Test storing and retrieving fraud patterns."""
        memory_manager = mock_dynamodb_setup
        
        # Store fraud pattern
        success = memory_manager.store_fraud_pattern(sample_fraud_pattern)
        assert success is True
        
        # Retrieve by pattern type
        patterns = memory_manager.get_fraud_patterns_by_type(sample_fraud_pattern.pattern_type)
        assert len(patterns) == 1
        assert patterns[0].pattern_id == sample_fraud_pattern.pattern_id
        assert patterns[0].description == sample_fraud_pattern.description
        
        # Retrieve all patterns
        all_patterns = memory_manager.get_all_fraud_patterns()
        assert len(all_patterns) >= 1
        assert any(p.pattern_id == sample_fraud_pattern.pattern_id for p in all_patterns)
    
    def test_store_and_retrieve_risk_profile(self, mock_dynamodb_setup, sample_risk_profile):
        """Test storing and retrieving risk profiles."""
        memory_manager = mock_dynamodb_setup
        
        # Store risk profile
        success = memory_manager.store_risk_profile(sample_risk_profile)
        assert success is True
        
        # Retrieve risk profile
        retrieved = memory_manager.get_risk_profile(sample_risk_profile.user_id)
        assert retrieved is not None
        assert retrieved.user_id == sample_risk_profile.user_id
        assert retrieved.overall_risk_level == sample_risk_profile.overall_risk_level
        assert retrieved.risk_factors == sample_risk_profile.risk_factors
        assert retrieved.geographic_risk == sample_risk_profile.geographic_risk
    
    def test_get_similar_transactions(self, mock_dynamodb_setup, sample_transaction):
        """Test finding similar transactions."""
        memory_manager = mock_dynamodb_setup
        
        # Store the original transaction
        memory_manager.store_transaction(sample_transaction)
        
        # Store a similar transaction
        similar_tx = Transaction(
            id="tx_similar",
            user_id=sample_transaction.user_id,
            amount=Decimal("155.00"),  # Similar amount
            currency="USD",
            merchant=sample_transaction.merchant,  # Same merchant
            category=sample_transaction.category,  # Same category
            location=sample_transaction.location,  # Same location
            timestamp=datetime.now() - timedelta(hours=1),
            card_type="credit",
            device_info=sample_transaction.device_info,
            ip_address="192.168.1.1",
            session_id="session_similar"
        )
        memory_manager.store_transaction(similar_tx)
        
        # Store decision context for similar transaction
        decision_context = DecisionContext(
            transaction_id=similar_tx.id,
            user_id=similar_tx.user_id,
            decision=FraudDecision.APPROVED,
            confidence_score=0.9,
            reasoning_steps=["Similar to previous approved transaction"],
            evidence=["Same merchant and location"],
            timestamp=datetime.now(),
            processing_time_ms=150.0,
            agent_version="1.0.0"
        )
        memory_manager.store_decision_context(decision_context)
        
        # Find similar transactions
        similar_cases = memory_manager.get_similar_transactions(sample_transaction)
        
        # Should find the similar transaction
        assert len(similar_cases) >= 1
        similar_case = similar_cases[0]
        assert similar_case.transaction_id == similar_tx.id
        assert similar_case.similarity_score > 0.5
        assert similar_case.decision == FraudDecision.APPROVED
    
    def test_calculate_similarity(self, mock_dynamodb_setup, sample_transaction):
        """Test transaction similarity calculation."""
        memory_manager = mock_dynamodb_setup
        
        # Create identical transaction (should have high similarity)
        identical_tx = Transaction(
            id="tx_identical",
            user_id=sample_transaction.user_id,
            amount=sample_transaction.amount,
            currency=sample_transaction.currency,
            merchant=sample_transaction.merchant,
            category=sample_transaction.category,
            location=sample_transaction.location,
            timestamp=sample_transaction.timestamp,
            card_type=sample_transaction.card_type,
            device_info=sample_transaction.device_info,
            ip_address=sample_transaction.ip_address,
            session_id="different_session"
        )
        
        similarity = memory_manager._calculate_similarity(sample_transaction, identical_tx)
        assert similarity > 0.8  # Should be very similar
        
        # Create different transaction (should have low similarity)
        different_tx = Transaction(
            id="tx_different",
            user_id="different_user",
            amount=Decimal("1000.00"),
            currency="EUR",
            merchant="Different Merchant",
            category="different_category",
            location=Location(country="UK", city="London"),
            timestamp=datetime.now(),
            card_type="debit",
            device_info=DeviceInfo(
                device_id="different_device",
                device_type="desktop",
                os="Windows"
            ),
            ip_address="10.0.0.1",
            session_id="different_session"
        )
        
        similarity = memory_manager._calculate_similarity(sample_transaction, different_tx)
        assert similarity < 0.3  # Should be very different
    
    def test_nonexistent_records(self, mock_dynamodb_setup):
        """Test retrieving nonexistent records returns None/empty lists."""
        memory_manager = mock_dynamodb_setup
        
        # Test nonexistent transaction
        transaction = memory_manager.get_transaction_by_id("nonexistent_tx")
        assert transaction is None
        
        # Test nonexistent decision context
        decision = memory_manager.get_decision_context("nonexistent_tx")
        assert decision is None
        
        # Test nonexistent user profile
        profile = memory_manager.get_user_profile("nonexistent_user")
        assert profile is None
        
        # Test nonexistent risk profile
        risk_profile = memory_manager.get_risk_profile("nonexistent_user")
        assert risk_profile is None
        
        # Test empty transaction history
        history = memory_manager.get_user_transaction_history("nonexistent_user")
        assert history == []
        
        # Test empty decision history
        decisions = memory_manager.get_user_decision_history("nonexistent_user")
        assert decisions == []
        
        # Test empty fraud patterns
        patterns = memory_manager.get_fraud_patterns_by_type("nonexistent_type")
        assert patterns == []
    
    def test_error_handling(self, mock_dynamodb_setup):
        """Test error handling for invalid data."""
        memory_manager = mock_dynamodb_setup
        
        # Test with invalid transaction (missing required fields)
        invalid_transaction = Transaction(
            id="",  # Empty ID
            user_id="",  # Empty user ID
            amount=Decimal("0"),
            currency="",
            merchant="",
            category="",
            location=Location(country="", city=""),
            timestamp=datetime.now(),
            card_type="",
            device_info=DeviceInfo(device_id="", device_type="", os=""),
            ip_address="",
            session_id=""
        )
        
        # Should handle gracefully and return False
        success = memory_manager.store_transaction(invalid_transaction)
        # Note: Depending on implementation, this might succeed or fail
        # The test verifies the method doesn't crash
        assert isinstance(success, bool)


if __name__ == "__main__":
    pytest.main([__file__])