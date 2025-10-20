#!/usr/bin/env python3
"""
Demo script for Memory Manager with DynamoDB Integration

This script demonstrates the key functionality of the Memory Manager including:
- Setting up DynamoDB tables
- Storing and retrieving transactions
- Managing user profiles and decision context
- Finding similar transactions
- Memory optimization features
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.memory_manager import MemoryManager
from src.models import (
    Transaction, DecisionContext, UserBehaviorProfile, FraudPattern,
    RiskProfile, Location, DeviceInfo, FraudDecision, RiskLevel
)


def create_sample_transaction(tx_id: str, user_id: str, amount: float, merchant: str) -> Transaction:
    """Create a sample transaction for testing."""
    return Transaction(
        id=tx_id,
        user_id=user_id,
        amount=Decimal(str(amount)),
        currency="USD",
        merchant=merchant,
        category="retail",
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
        session_id=f"session_{tx_id}",
        metadata={"channel": "mobile_app"}
    )


def create_sample_decision_context(tx_id: str, user_id: str, decision: FraudDecision) -> DecisionContext:
    """Create a sample decision context for testing."""
    return DecisionContext(
        transaction_id=tx_id,
        user_id=user_id,
        decision=decision,
        confidence_score=0.85,
        reasoning_steps=[
            "Transaction amount within user's typical range",
            "Merchant is frequently used by user",
            "Location matches user's common locations"
        ],
        evidence=[
            "User has previous transactions with this merchant",
            "Device fingerprint matches previous sessions"
        ],
        timestamp=datetime.now(),
        processing_time_ms=250.5,
        agent_version="1.0.0",
        external_tools_used=["geolocation_api", "device_fingerprint"]
    )


def create_sample_user_profile(user_id: str) -> UserBehaviorProfile:
    """Create a sample user behavior profile for testing."""
    return UserBehaviorProfile(
        user_id=user_id,
        typical_spending_range={"min": 10.0, "max": 500.0, "avg": 125.0},
        frequent_merchants=["Amazon", "Starbucks", "Target"],
        common_locations=[
            Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
            Location(country="US", city="Boston", latitude=42.3601, longitude=-71.0589)
        ],
        preferred_categories=["retail", "food", "groceries"],
        transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
        risk_score=0.3,
        last_updated=datetime.now(),
        transaction_count=150
    )


def create_sample_risk_profile(user_id: str) -> RiskProfile:
    """Create a sample risk profile for testing."""
    return RiskProfile(
        user_id=user_id,
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


def demo_memory_manager():
    """Demonstrate Memory Manager functionality."""
    print("🧠 Memory Manager with DynamoDB Integration Demo")
    print("=" * 60)
    
    # Initialize Memory Manager (using local DynamoDB for demo)
    print("\n1. Initializing Memory Manager...")
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    
    # Set up tables
    print("2. Setting up DynamoDB tables...")
    success = memory_manager.setup_tables()
    if success:
        print("✅ Tables created successfully")
    else:
        print("❌ Failed to create tables - using existing tables")
    
    # Test transaction storage and retrieval
    print("\n3. Testing Transaction Storage...")
    
    # Create sample transactions
    transactions = [
        create_sample_transaction("tx_001", "user_123", 150.00, "Amazon"),
        create_sample_transaction("tx_002", "user_123", 75.50, "Starbucks"),
        create_sample_transaction("tx_003", "user_123", 200.00, "Target"),
        create_sample_transaction("tx_004", "user_456", 300.00, "Amazon"),
    ]
    
    # Store transactions individually
    for tx in transactions[:2]:
        success = memory_manager.store_transaction(tx)
        print(f"   Stored transaction {tx.id}: {'✅' if success else '❌'}")
    
    # Store transactions in batch
    batch_result = memory_manager.batch_store_transactions(transactions[2:])
    print(f"   Batch stored: {batch_result['success']} success, {batch_result['failures']} failures")
    
    # Test transaction retrieval
    print("\n4. Testing Transaction Retrieval...")
    
    # Get user transaction history
    history = memory_manager.get_user_transaction_history("user_123")
    print(f"   Retrieved {len(history)} transactions for user_123")
    
    # Get transaction by ID
    tx = memory_manager.get_transaction_by_id("tx_001")
    if tx:
        print(f"   Retrieved transaction: {tx.id} - ${tx.amount} at {tx.merchant}")
    
    # Get transaction statistics
    stats = memory_manager.get_user_transaction_stats("user_123")
    if "error" not in stats:
        print(f"   User stats: {stats['total_transactions']} transactions, avg ${stats['average_amount']:.2f}")
    
    # Test decision context storage
    print("\n5. Testing Decision Context Storage...")
    
    decisions = [
        create_sample_decision_context("tx_001", "user_123", FraudDecision.APPROVED),
        create_sample_decision_context("tx_002", "user_123", FraudDecision.APPROVED),
        create_sample_decision_context("tx_003", "user_123", FraudDecision.FLAGGED),
    ]
    
    for decision in decisions:
        success = memory_manager.store_decision_context(decision)
        print(f"   Stored decision for {decision.transaction_id}: {'✅' if success else '❌'}")
    
    # Retrieve decision history
    decision_history = memory_manager.get_user_decision_history("user_123")
    print(f"   Retrieved {len(decision_history)} decisions for user_123")
    
    # Test user profile management
    print("\n6. Testing User Profile Management...")
    
    # Store user profile
    profile = create_sample_user_profile("user_123")
    success = memory_manager.store_user_profile(profile)
    print(f"   Stored user profile: {'✅' if success else '❌'}")
    
    # Retrieve user profile
    retrieved_profile = memory_manager.get_user_profile("user_123")
    if retrieved_profile:
        print(f"   Retrieved profile: {len(retrieved_profile.frequent_merchants)} merchants, risk score {retrieved_profile.risk_score}")
    
    # Update user profile
    updates = {
        "risk_score": 0.4,
        "transaction_count": 155,
        "last_updated": datetime.now()
    }
    success = memory_manager.update_user_profile("user_123", updates)
    print(f"   Updated user profile: {'✅' if success else '❌'}")
    
    # Test risk profile management
    print("\n7. Testing Risk Profile Management...")
    
    risk_profile = create_sample_risk_profile("user_123")
    success = memory_manager.store_risk_profile(risk_profile)
    print(f"   Stored risk profile: {'✅' if success else '❌'}")
    
    retrieved_risk = memory_manager.get_risk_profile("user_123")
    if retrieved_risk:
        print(f"   Retrieved risk profile: {retrieved_risk.overall_risk_level.value} risk level")
    
    # Test fraud pattern storage
    print("\n8. Testing Fraud Pattern Storage...")
    
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
    
    success = memory_manager.store_fraud_pattern(pattern)
    print(f"   Stored fraud pattern: {'✅' if success else '❌'}")
    
    patterns = memory_manager.get_fraud_patterns_by_type("velocity_fraud")
    print(f"   Retrieved {len(patterns)} velocity fraud patterns")
    
    # Test similarity matching
    print("\n9. Testing Transaction Similarity Matching...")
    
    # Create a new transaction similar to existing ones
    new_tx = create_sample_transaction("tx_005", "user_123", 155.00, "Amazon")
    
    similar_cases = memory_manager.get_similar_transactions(new_tx, similarity_threshold=0.5)
    print(f"   Found {len(similar_cases)} similar transactions")
    
    for case in similar_cases[:3]:  # Show top 3
        print(f"     - Transaction {case.transaction_id}: similarity {case.similarity_score:.2f}, decision {case.decision.value}")
    
    # Test memory usage statistics
    print("\n10. Testing Memory Usage Statistics...")
    
    usage_stats = memory_manager.get_memory_usage_stats()
    print("   Table usage statistics:")
    for table_name, stats in usage_stats.items():
        if "error" not in stats:
            print(f"     - {table_name}: {stats.get('item_count', 'N/A')} items")
        else:
            print(f"     - {table_name}: Error - {stats['error']}")
    
    print("\n✅ Memory Manager Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("  • DynamoDB table setup and configuration")
    print("  • Transaction storage and retrieval with indexing")
    print("  • Decision context management")
    print("  • User behavior profile management")
    print("  • Risk profile tracking")
    print("  • Fraud pattern storage")
    print("  • Transaction similarity matching")
    print("  • Batch operations for performance")
    print("  • Memory usage monitoring")
    print("  • Data optimization features")


if __name__ == "__main__":
    try:
        demo_memory_manager()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()