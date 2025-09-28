"""
Demo script for Context-Aware Decision Making System.

This script demonstrates the capabilities of the context manager and how it
provides contextual insights for fraud detection decisions.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from memory_system.context_manager import ContextManager, ContextualInsight
from memory_system.memory_manager import MemoryManager
from memory_system.models import (
    Transaction, FraudPattern, FraudDecision, DecisionContext,
    Location, DeviceInfo, UserBehaviorProfile, RiskLevel, SimilarCase
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_user_profile(user_id: str) -> UserBehaviorProfile:
    """Create a sample user behavior profile."""
    return UserBehaviorProfile(
        user_id=user_id,
        typical_spending_range={"min": 20.0, "max": 300.0, "avg": 85.0},
        frequent_merchants=["Starbucks", "Amazon", "Target", "Shell", "McDonald's"],
        common_locations=[
            Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
            Location(country="US", city="Boston", latitude=42.3601, longitude=-71.0589)
        ],
        preferred_categories=["food", "online_retail", "gas", "groceries"],
        transaction_frequency={"daily": 3, "weekly": 21, "monthly": 90},
        risk_score=0.2,
        last_updated=datetime.now() - timedelta(days=1),
        transaction_count=450
    )


def create_sample_transactions() -> List[Transaction]:
    """Create various sample transactions for different scenarios."""
    transactions = []
    
    # Scenario 1: Normal transaction - familiar merchant, typical amount
    transactions.append(Transaction(
        id="tx_normal_001",
        user_id="user_regular",
        amount=Decimal("45.50"),
        currency="USD",
        merchant="Starbucks",
        category="food",
        location=Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
        timestamp=datetime.now() - timedelta(hours=2),
        card_type="credit",
        device_info=DeviceInfo(device_id="device_mobile_001", device_type="mobile", os="iOS"),
        ip_address="192.168.1.100",
        session_id="session_normal_001"
    ))
    
    # Scenario 2: High amount transaction - exceeds typical spending
    transactions.append(Transaction(
        id="tx_high_amount_001",
        user_id="user_regular",
        amount=Decimal("850.00"),
        currency="USD",
        merchant="Electronics Store",
        category="electronics",
        location=Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
        timestamp=datetime.now() - timedelta(hours=1),
        card_type="credit",
        device_info=DeviceInfo(device_id="device_mobile_001", device_type="mobile", os="iOS"),
        ip_address="192.168.1.100",
        session_id="session_high_001"
    ))
    
    # Scenario 3: Geographic anomaly - transaction in unfamiliar location
    transactions.append(Transaction(
        id="tx_geo_anomaly_001",
        user_id="user_regular",
        amount=Decimal("120.00"),
        currency="EUR",
        merchant="Paris Boutique",
        category="retail",
        location=Location(country="FR", city="Paris", latitude=48.8566, longitude=2.3522),
        timestamp=datetime.now() - timedelta(minutes=30),
        card_type="credit",
        device_info=DeviceInfo(device_id="device_unknown", device_type="desktop", os="Windows"),
        ip_address="82.45.123.45",
        session_id="session_geo_001"
    ))
    
    # Scenario 4: Late night transaction - temporal anomaly
    late_night_time = datetime.now().replace(hour=3, minute=15, second=0, microsecond=0)
    transactions.append(Transaction(
        id="tx_late_night_001",
        user_id="user_regular",
        amount=Decimal("75.00"),
        currency="USD",
        merchant="24/7 Gas Station",
        category="gas",
        location=Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
        timestamp=late_night_time,
        card_type="credit",
        device_info=DeviceInfo(device_id="device_mobile_001", device_type="mobile", os="iOS"),
        ip_address="192.168.1.100",
        session_id="session_late_001"
    ))
    
    # Scenario 5: Velocity pattern - multiple rapid transactions
    base_time = datetime.now() - timedelta(minutes=15)
    for i in range(3):
        transactions.append(Transaction(
            id=f"tx_velocity_{i:03d}",
            user_id="user_velocity",
            amount=Decimal(f"{50 + i * 25}.00"),
            currency="USD",
            merchant=f"Online Store {i+1}",
            category="online_retail",
            location=Location(country="US", city="Los Angeles", latitude=34.0522, longitude=-118.2437),
            timestamp=base_time + timedelta(minutes=i * 3),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_desktop_001", device_type="desktop", os="Windows"),
            ip_address="10.0.0.50",
            session_id=f"session_velocity_{i}"
        ))
    
    return transactions


def create_mock_similar_cases() -> List[SimilarCase]:
    """Create mock similar cases for demonstration."""
    return [
        SimilarCase(
            case_id="similar_001",
            transaction_id="tx_historical_001",
            similarity_score=0.85,
            decision=FraudDecision.APPROVED,
            outcome="legitimate",
            reasoning="Similar merchant and amount, user's regular pattern",
            timestamp=datetime.now() - timedelta(days=5)
        ),
        SimilarCase(
            case_id="similar_002",
            transaction_id="tx_historical_002",
            similarity_score=0.78,
            decision=FraudDecision.DECLINED,
            outcome="confirmed_fraud",
            reasoning="High amount transaction flagged as fraudulent",
            timestamp=datetime.now() - timedelta(days=12)
        ),
        SimilarCase(
            case_id="similar_003",
            transaction_id="tx_historical_003",
            similarity_score=0.72,
            decision=FraudDecision.APPROVED,
            outcome="legitimate",
            reasoning="Regular merchant, typical spending pattern",
            timestamp=datetime.now() - timedelta(days=8)
        )
    ]


def create_mock_decision_history() -> List[DecisionContext]:
    """Create mock decision history for demonstration."""
    history = []
    
    # Recent legitimate transactions
    for i in range(5):
        history.append(DecisionContext(
            transaction_id=f"tx_recent_{i:03d}",
            user_id="user_regular",
            decision=FraudDecision.APPROVED,
            confidence_score=0.85 + i * 0.02,
            reasoning_steps=[f"Regular transaction pattern {i+1}"],
            evidence=[f"Familiar merchant and location {i+1}"],
            timestamp=datetime.now() - timedelta(days=i+1),
            processing_time_ms=150.0 + i * 10,
            agent_version="1.0.0"
        ))
    
    # One flagged transaction
    history.append(DecisionContext(
        transaction_id="tx_flagged_001",
        user_id="user_regular",
        decision=FraudDecision.FLAGGED,
        confidence_score=0.65,
        reasoning_steps=["Unusual merchant category"],
        evidence=["First time transaction with this merchant type"],
        timestamp=datetime.now() - timedelta(days=7),
        processing_time_ms=280.0,
        agent_version="1.0.0"
    ))
    
    return history


class MockMemoryManager:
    """Mock memory manager for demonstration purposes."""
    
    def __init__(self):
        self.user_profiles = {}
        self.similar_cases = create_mock_similar_cases()
        self.decision_history = create_mock_decision_history()
        
        # Add sample user profile
        self.user_profiles["user_regular"] = create_user_profile("user_regular")
        self.user_profiles["user_velocity"] = UserBehaviorProfile(
            user_id="user_velocity",
            typical_spending_range={"min": 10.0, "max": 150.0, "avg": 65.0},
            frequent_merchants=["Online Store 1", "Online Store 2", "Digital Market"],
            common_locations=[
                Location(country="US", city="Los Angeles", latitude=34.0522, longitude=-118.2437)
            ],
            preferred_categories=["online_retail", "digital_goods"],
            transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
            risk_score=0.4,
            last_updated=datetime.now(),
            transaction_count=180
        )
    
    def get_similar_transactions(self, transaction, threshold=0.7, limit=10):
        """Return mock similar cases."""
        return self.similar_cases[:limit]
    
    def get_user_profile(self, user_id):
        """Return user profile if exists."""
        return self.user_profiles.get(user_id)
    
    def get_risk_profile(self, user_id):
        """Return None for simplicity in demo."""
        return None
    
    def get_user_decision_history(self, user_id, days_back=90):
        """Return mock decision history."""
        return [d for d in self.decision_history if d.user_id == user_id]


def demonstrate_context_analysis(context_manager: ContextManager, transaction: Transaction):
    """Demonstrate context analysis for a single transaction."""
    print(f"\n{'='*80}")
    print(f"CONTEXT ANALYSIS FOR TRANSACTION: {transaction.id}")
    print(f"{'='*80}")
    
    print(f"Transaction Details:")
    print(f"  User ID: {transaction.user_id}")
    print(f"  Amount: ${transaction.amount} {transaction.currency}")
    print(f"  Merchant: {transaction.merchant}")
    print(f"  Category: {transaction.category}")
    print(f"  Location: {transaction.location.city}, {transaction.location.country}")
    print(f"  Timestamp: {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Device: {transaction.device_info.device_type} ({transaction.device_info.os})")
    
    # Get transaction context
    context = context_manager.get_transaction_context(transaction)
    
    print(f"\nContext Analysis Results:")
    print(f"  Similar Cases Found: {len(context.get('similar_cases', []))}")
    print(f"  User Profile Available: {'Yes' if context.get('user_profile') else 'No'}")
    print(f"  Risk Profile Available: {'Yes' if context.get('risk_profile') else 'No'}")
    print(f"  Decision History Items: {len(context.get('decision_history', []))}")
    
    # Display contextual insights
    insights = context.get('contextual_insights', [])
    print(f"\nContextual Insights ({len(insights)} found):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight.insight_type.replace('_', ' ').title()}")
        print(f"     Description: {insight.description}")
        print(f"     Confidence: {insight.confidence:.3f}")
        print(f"     Risk Impact: {insight.risk_impact:+.3f}")
        print(f"     Evidence: {', '.join(insight.supporting_evidence)}")
    
    # Display risk factors
    risk_factors = context.get('risk_factors', {})
    print(f"\nRisk Factors ({len(risk_factors)} identified):")
    for factor_name, factor_value in risk_factors.items():
        risk_level = "HIGH" if factor_value > 0.6 else "MEDIUM" if factor_value > 0.3 else "LOW"
        print(f"  {factor_name.replace('_', ' ').title()}: {factor_value:.3f} ({risk_level})")
    
    # Get contextual recommendation
    recommendation = context_manager.get_contextual_recommendation(transaction)
    
    print(f"\nContextual Recommendation:")
    print(f"  Decision: {recommendation['recommendation']}")
    print(f"  Confidence: {recommendation['confidence']:.3f}")
    print(f"  Risk Score: {recommendation['risk_score']:+.3f}")
    
    print(f"\nReasoning:")
    for i, reason in enumerate(recommendation['reasoning'], 1):
        print(f"  {i}. {reason}")
    
    return recommendation


def demonstrate_scenario_comparison(context_manager: ContextManager, transactions: List[Transaction]):
    """Demonstrate how context affects decisions across different scenarios."""
    print(f"\n{'='*80}")
    print(f"SCENARIO COMPARISON - CONTEXT-AWARE DECISIONS")
    print(f"{'='*80}")
    
    recommendations = []
    
    for transaction in transactions:
        recommendation = context_manager.get_contextual_recommendation(transaction)
        recommendations.append((transaction, recommendation))
    
    # Display comparison table
    print(f"\n{'Transaction ID':<20} {'Amount':<10} {'Location':<15} {'Decision':<15} {'Confidence':<12} {'Risk Score':<12}")
    print(f"{'-'*20} {'-'*10} {'-'*15} {'-'*15} {'-'*12} {'-'*12}")
    
    for transaction, rec in recommendations:
        location = f"{transaction.location.city[:12]}..."[:15] if len(transaction.location.city) > 12 else transaction.location.city
        print(f"{transaction.id:<20} ${float(transaction.amount):<9.2f} {location:<15} {rec['recommendation']:<15} {rec['confidence']:<12.3f} {rec['risk_score']:<+12.3f}")
    
    # Analyze patterns in recommendations
    print(f"\nDecision Pattern Analysis:")
    
    approve_count = sum(1 for _, rec in recommendations if rec['recommendation'] == 'APPROVE')
    decline_count = sum(1 for _, rec in recommendations if rec['recommendation'] == 'DECLINE')
    review_count = sum(1 for _, rec in recommendations if rec['recommendation'] in ['FLAG_FOR_REVIEW', 'MANUAL_REVIEW'])
    
    print(f"  Approved: {approve_count}/{len(recommendations)} ({approve_count/len(recommendations)*100:.1f}%)")
    print(f"  Declined: {decline_count}/{len(recommendations)} ({decline_count/len(recommendations)*100:.1f}%)")
    print(f"  Review Required: {review_count}/{len(recommendations)} ({review_count/len(recommendations)*100:.1f}%)")
    
    # Identify highest and lowest risk transactions
    sorted_recs = sorted(recommendations, key=lambda x: x[1]['risk_score'])
    
    print(f"\nRisk Analysis:")
    print(f"  Lowest Risk: {sorted_recs[0][0].id} (Risk Score: {sorted_recs[0][1]['risk_score']:+.3f})")
    print(f"  Highest Risk: {sorted_recs[-1][0].id} (Risk Score: {sorted_recs[-1][1]['risk_score']:+.3f})")
    
    return recommendations


def demonstrate_context_evolution(context_manager: ContextManager):
    """Demonstrate how context evolves with user behavior."""
    print(f"\n{'='*80}")
    print(f"CONTEXT EVOLUTION DEMONSTRATION")
    print(f"{'='*80}")
    
    print("This demonstration shows how user context affects decision making:")
    print("\n1. New User vs Established User:")
    print("   - New users have limited context, leading to more conservative decisions")
    print("   - Established users benefit from rich behavioral profiles")
    
    print("\n2. Risk Profile Evolution:")
    print("   - Users with consistent legitimate patterns get lower risk scores")
    print("   - Users with mixed patterns require more scrutiny")
    
    print("\n3. Contextual Learning:")
    print("   - Similar transaction analysis improves over time")
    print("   - Geographic and temporal patterns become more refined")
    
    print("\n4. Adaptive Thresholds:")
    print("   - Decision confidence adjusts based on available context")
    print("   - Risk factors are weighted by historical accuracy")


def main():
    """Main demonstration function."""
    print("Context-Aware Decision Making System Demo")
    print("=" * 80)
    
    try:
        # Initialize components
        print("Initializing Context-Aware Decision System...")
        
        mock_memory_manager = MockMemoryManager()
        context_manager = ContextManager(mock_memory_manager)
        
        # Create sample transactions
        transactions = create_sample_transactions()
        
        print(f"\nCreated {len(transactions)} sample transactions for analysis")
        
        # Demonstrate detailed context analysis for key scenarios
        key_scenarios = [
            ("Normal Transaction", transactions[0]),
            ("High Amount Transaction", transactions[1]),
            ("Geographic Anomaly", transactions[2]),
            ("Late Night Transaction", transactions[3])
        ]
        
        for scenario_name, transaction in key_scenarios:
            print(f"\n{'='*60}")
            print(f"SCENARIO: {scenario_name}")
            print(f"{'='*60}")
            demonstrate_context_analysis(context_manager, transaction)
        
        # Demonstrate scenario comparison
        demonstrate_scenario_comparison(context_manager, transactions)
        
        # Demonstrate context evolution concepts
        demonstrate_context_evolution(context_manager)
        
        print(f"\n{'='*80}")
        print("DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print("\nKey Capabilities Demonstrated:")
        print("✓ Contextual insight generation from historical data")
        print("✓ Risk factor analysis based on user behavior")
        print("✓ Similar case analysis and pattern matching")
        print("✓ Adaptive decision making with confidence scoring")
        print("✓ Multi-factor risk assessment")
        print("✓ Temporal and geographic anomaly detection")
        print("\nThe Context-Aware Decision System is ready for integration!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()