#!/usr/bin/env python3
"""
Integration test for Memory Manager functionality.

This test validates the core Memory Manager functionality without requiring
external dependencies like moto.
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_system.memory_manager import MemoryManager
from memory_system.models import (
    Transaction, DecisionContext, UserBehaviorProfile, FraudPattern,
    RiskProfile, Location, DeviceInfo, FraudDecision, RiskLevel
)


def test_memory_manager_initialization():
    """Test Memory Manager initialization."""
    print("Testing Memory Manager initialization...")
    
    # Test with local endpoint (for development)
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    assert memory_manager is not None
    assert memory_manager.config is not None
    
    # Test table references
    assert memory_manager.transaction_table is not None
    assert memory_manager.decision_table is not None
    assert memory_manager.profile_table is not None
    assert memory_manager.pattern_table is not None
    assert memory_manager.risk_table is not None
    
    print("✅ Memory Manager initialization test passed")


def test_transaction_model_creation():
    """Test creating transaction models."""
    print("Testing transaction model creation...")
    
    location = Location(
        country="US",
        city="New York",
        latitude=40.7128,
        longitude=-74.0060,
        ip_address="192.168.1.1"
    )
    
    device_info = DeviceInfo(
        device_id="device_123",
        device_type="mobile",
        os="iOS",
        browser="Safari",
        fingerprint="fp_abc123"
    )
    
    transaction = Transaction(
        id="tx_123456",
        user_id="user_789",
        amount=Decimal("150.00"),
        currency="USD",
        merchant="Amazon",
        category="online_retail",
        location=location,
        timestamp=datetime.now(),
        card_type="credit",
        device_info=device_info,
        ip_address="192.168.1.1",
        session_id="session_456",
        metadata={"channel": "mobile_app"}
    )
    
    assert transaction.id == "tx_123456"
    assert transaction.user_id == "user_789"
    assert transaction.amount == Decimal("150.00")
    assert transaction.merchant == "Amazon"
    assert transaction.location.country == "US"
    assert transaction.device_info.device_type == "mobile"
    
    print("✅ Transaction model creation test passed")


def test_decision_context_model():
    """Test creating decision context models."""
    print("Testing decision context model creation...")
    
    decision_context = DecisionContext(
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
    
    assert decision_context.transaction_id == "tx_123456"
    assert decision_context.decision == FraudDecision.APPROVED
    assert decision_context.confidence_score == 0.85
    assert len(decision_context.reasoning_steps) == 3
    assert len(decision_context.evidence) == 3
    
    print("✅ Decision context model creation test passed")


def test_user_profile_model():
    """Test creating user behavior profile models."""
    print("Testing user behavior profile model creation...")
    
    profile = UserBehaviorProfile(
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
    
    assert profile.user_id == "user_789"
    assert profile.typical_spending_range["max"] == 500.0
    assert len(profile.frequent_merchants) == 3
    assert len(profile.common_locations) == 2
    assert profile.risk_score == 0.3
    
    print("✅ User behavior profile model creation test passed")


def test_fraud_pattern_model():
    """Test creating fraud pattern models."""
    print("Testing fraud pattern model creation...")
    
    pattern = FraudPattern(
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
    
    assert pattern.pattern_id == "pattern_001"
    assert pattern.pattern_type == "velocity_fraud"
    assert len(pattern.indicators) == 3
    assert pattern.confidence_threshold == 0.8
    assert pattern.effectiveness_score == 0.92
    
    print("✅ Fraud pattern model creation test passed")


def test_risk_profile_model():
    """Test creating risk profile models."""
    print("Testing risk profile model creation...")
    
    risk_profile = RiskProfile(
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
    
    assert risk_profile.user_id == "user_789"
    assert risk_profile.overall_risk_level == RiskLevel.LOW
    assert len(risk_profile.risk_factors) == 4
    assert risk_profile.geographic_risk == 0.1
    assert len(risk_profile.risk_evolution) == 2
    
    print("✅ Risk profile model creation test passed")


def test_similarity_calculation():
    """Test transaction similarity calculation."""
    print("Testing transaction similarity calculation...")
    
    # Create memory manager instance
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    
    # Create two similar transactions
    location = Location(country="US", city="New York")
    device_info = DeviceInfo(device_id="device_123", device_type="mobile", os="iOS")
    
    tx1 = Transaction(
        id="tx_001",
        user_id="user_123",
        amount=Decimal("150.00"),
        currency="USD",
        merchant="Amazon",
        category="retail",
        location=location,
        timestamp=datetime.now(),
        card_type="credit",
        device_info=device_info,
        ip_address="192.168.1.1",
        session_id="session_1"
    )
    
    tx2 = Transaction(
        id="tx_002",
        user_id="user_123",
        amount=Decimal("155.00"),  # Similar amount
        currency="USD",
        merchant="Amazon",  # Same merchant
        category="retail",  # Same category
        location=location,  # Same location
        timestamp=datetime.now(),
        card_type="credit",
        device_info=device_info,  # Same device
        ip_address="192.168.1.1",
        session_id="session_2"
    )
    
    # Calculate similarity
    similarity = memory_manager._calculate_similarity(tx1, tx2)
    
    # Should be high similarity (same merchant, category, location, device, similar amount)
    assert similarity > 0.5, f"Expected high similarity, got {similarity}"
    
    # Create a very different transaction
    tx3 = Transaction(
        id="tx_003",
        user_id="user_456",  # Different user
        amount=Decimal("1000.00"),  # Very different amount
        currency="EUR",  # Different currency
        merchant="Different Store",  # Different merchant
        category="travel",  # Different category
        location=Location(country="UK", city="London"),  # Different location
        timestamp=datetime.now(),
        card_type="debit",  # Different card type
        device_info=DeviceInfo(device_id="device_456", device_type="desktop", os="Windows"),
        ip_address="10.0.0.1",
        session_id="session_3"
    )
    
    # Calculate similarity with very different transaction
    similarity_low = memory_manager._calculate_similarity(tx1, tx3)
    
    # Should be low similarity
    assert similarity_low < 0.3, f"Expected low similarity, got {similarity_low}"
    
    print(f"✅ Similarity calculation test passed (high: {similarity:.2f}, low: {similarity_low:.2f})")


def test_dynamodb_config():
    """Test DynamoDB configuration."""
    print("Testing DynamoDB configuration...")
    
    from memory_system.dynamodb_config import DynamoDBConfig
    
    config = DynamoDBConfig(endpoint_url='http://localhost:8000')
    assert config is not None
    
    # Test table definitions
    table_defs = config.get_table_definitions()
    assert len(table_defs) == 5
    
    expected_tables = [
        'TransactionHistory',
        'DecisionContext', 
        'UserBehaviorProfiles',
        'FraudPatterns',
        'RiskProfiles'
    ]
    
    for table_name in expected_tables:
        assert table_name in table_defs
        assert 'TableName' in table_defs[table_name]
        assert 'KeySchema' in table_defs[table_name]
        assert 'AttributeDefinitions' in table_defs[table_name]
    
    print("✅ DynamoDB configuration test passed")


def run_all_tests():
    """Run all integration tests."""
    print("🧠 Memory Manager Integration Tests")
    print("=" * 50)
    
    tests = [
        test_memory_manager_initialization,
        test_transaction_model_creation,
        test_decision_context_model,
        test_user_profile_model,
        test_fraud_pattern_model,
        test_risk_profile_model,
        test_similarity_calculation,
        test_dynamodb_config
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {str(e)}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Memory Manager is ready for use.")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)