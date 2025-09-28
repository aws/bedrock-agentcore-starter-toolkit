"""
Demo script for Context-Aware Decision Making System.

This script demonstrates the capabilities of the context manager including
contextual analysis, risk assessment, and intelligent recommendations.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from memory_system.context_manager import ContextManager, ContextualInsight
from memory_system.memory_manager import MemoryManager
from memory_system.models import (
    Transaction, DecisionContext, UserBehaviorProfile, 
    FraudPattern, SimilarCase, RiskProfile, FraudDecision,
    Location, DeviceInfo, RiskLevel
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_scenarios() -> List[Dict[str, Any]]:
    """Create various test scenarios for demonstration."""
    scenarios = []
    
    # Scenario 1: Low-risk legitimate transaction
    scenarios.append({
        "name": "Low-Risk Legitimate Transaction",
        "description": "Regular user making a typical purchase at a familiar merchant",
        "transaction": Transaction(
            id="tx_legitimate_001",
            user_id="user_regular_123",
            amount=Decimal("45.99"),
            currency="USD",
            merchant="Starbucks",
            category="food",
            location=Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
            timestamp=datetime.now().replace(hour=14),  # Afternoon
            card_type="credit",
            device_info=DeviceInfo(device_id="device_regular", device_type="mobile", os="iOS"),
            ip_address="192.168.1.100",
            session_id="session_regular_001"
        ),
        "user_profile": UserBehaviorProfile(
            user_id="user_regular_123",
            typical_spending_range={"min": 10.0, "max": 200.0, "avg": 65.0},
            frequent_merchants=["Starbucks", "Amazon", "Target", "Whole Foods"],
            common_locations=[
                Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
                Location(country="US", city="Brooklyn", latitude=40.6782, longitude=-73.9442)
            ],
            preferred_categories=["food", "groceries", "online_retail"],
            transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
            risk_score=0.15,
            last_updated=datetime.now(),
            transaction_count=450
        ),
        "similar_cases": [
            SimilarCase(
                case_id="case_leg_001",
                transaction_id="tx_similar_leg_001",
                similarity_score=0.9,
                decision=FraudDecision.APPROVED,
                outcome="legitimate",
                reasoning="Regular merchant and typical amount",
                timestamp=datetime.now() - timedelta(days=2)
            )
        ],
        "expected_outcome": "APPROVE"
    })
    
    # Scenario 2: High-risk suspicious transaction
    scenarios.append({
        "name": "High-Risk Suspicious Transaction",
        "description": "Large transaction in foreign country with new merchant",
        "transaction": Transaction(
            id="tx_suspicious_001",
            user_id="user_regular_123",  # Same user as scenario 1
            amount=Decimal("2500.00"),  # Much higher than typical
            currency="EUR",
            merchant="Luxury Store Paris",
            category="luxury_goods",
            location=Location(country="FR", city="Paris", latitude=48.8566, longitude=2.3522),
            timestamp=datetime.now().replace(hour=3),  # Late night
            card_type="credit",
            device_info=DeviceInfo(device_id="device_unknown", device_type="desktop", os="Windows"),
            ip_address="82.45.123.45",  # Foreign IP
            session_id="session_suspicious_001"
        ),
        "user_profile": UserBehaviorProfile(  # Same profile as scenario 1
            user_id="user_regular_123",
            typical_spending_range={"min": 10.0, "max": 200.0, "avg": 65.0},
            frequent_merchants=["Starbucks", "Amazon", "Target", "Whole Foods"],
            common_locations=[
                Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
                Location(country="US", city="Brooklyn", latitude=40.6782, longitude=-73.9442)
            ],
            preferred_categories=["food", "groceries", "online_retail"],
            transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
            risk_score=0.15,
            last_updated=datetime.now(),
            transaction_count=450
        ),
        "similar_cases": [
            SimilarCase(
                case_id="case_fraud_001",
                transaction_id="tx_similar_fraud_001",
                similarity_score=0.75,
                decision=FraudDecision.DECLINED,
                outcome="fraud",
                reasoning="Unusual location and high amount",
                timestamp=datetime.now() - timedelta(days=5)
            )
        ],
        "expected_outcome": "DECLINE"
    })
    
    # Scenario 3: Velocity fraud pattern
    scenarios.append({
        "name": "Velocity Fraud Pattern",
        "description": "Multiple rapid transactions in short time period",
        "transaction": Transaction(
            id="tx_velocity_004",
            user_id="user_velocity_456",
            amount=Decimal("299.99"),
            currency="USD",
            merchant="Online Electronics Store",
            category="electronics",
            location=Location(country="US", city="Los Angeles", latitude=34.0522, longitude=-118.2437),
            timestamp=datetime.now(),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_velocity", device_type="desktop", os="Windows"),
            ip_address="10.0.0.50",
            session_id="session_velocity_004"
        ),
        "user_profile": UserBehaviorProfile(
            user_id="user_velocity_456",
            typical_spending_range={"min": 50.0, "max": 500.0, "avg": 150.0},
            frequent_merchants=["Best Buy", "Amazon", "Newegg"],
            common_locations=[
                Location(country="US", city="Los Angeles", latitude=34.0522, longitude=-118.2437)
            ],
            preferred_categories=["electronics", "online_retail"],
            transaction_frequency={"daily": 1, "weekly": 7, "monthly": 30},
            risk_score=0.25,
            last_updated=datetime.now(),
            transaction_count=120
        ),
        "similar_cases": [],
        "decision_history": [  # Recent rapid transactions
            DecisionContext(
                transaction_id="tx_velocity_001",
                user_id="user_velocity_456",
                decision=FraudDecision.APPROVED,
                confidence_score=0.7,
                reasoning_steps=["First transaction approved"],
                evidence=["Normal merchant"],
                timestamp=datetime.now() - timedelta(minutes=45),
                processing_time_ms=150.0,
                agent_version="1.0.0"
            ),
            DecisionContext(
                transaction_id="tx_velocity_002",
                user_id="user_velocity_456",
                decision=FraudDecision.APPROVED,
                confidence_score=0.6,
                reasoning_steps=["Second transaction approved with caution"],
                evidence=["Increasing amounts"],
                timestamp=datetime.now() - timedelta(minutes=30),
                processing_time_ms=200.0,
                agent_version="1.0.0"
            ),
            DecisionContext(
                transaction_id="tx_velocity_003",
                user_id="user_velocity_456",
                decision=FraudDecision.FLAGGED,
                confidence_score=0.8,
                reasoning_steps=["Third transaction flagged for review"],
                evidence=["Rapid succession pattern"],
                timestamp=datetime.now() - timedelta(minutes=15),
                processing_time_ms=180.0,
                agent_version="1.0.0"
            )
        ],
        "expected_outcome": "FLAG_FOR_REVIEW"
    })
    
    # Scenario 4: New user with limited history
    scenarios.append({
        "name": "New User Transaction",
        "description": "New user making their first significant purchase",
        "transaction": Transaction(
            id="tx_newuser_001",
            user_id="user_new_789",
            amount=Decimal("899.99"),
            currency="USD",
            merchant="Apple Store",
            category="electronics",
            location=Location(country="US", city="San Francisco", latitude=37.7749, longitude=-122.4194),
            timestamp=datetime.now().replace(hour=16),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_new", device_type="mobile", os="iOS"),
            ip_address="192.168.1.200",
            session_id="session_new_001"
        ),
        "user_profile": None,  # No profile for new user
        "similar_cases": [],
        "decision_history": [],
        "expected_outcome": "FLAG_FOR_REVIEW"
    })
    
    return scenarios


def demonstrate_contextual_analysis(context_manager: ContextManager, scenario: Dict[str, Any]):
    """Demonstrate contextual analysis for a scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    
    transaction = scenario["transaction"]
    print(f"\nTransaction Details:")
    print(f"  ID: {transaction.id}")
    print(f"  User: {transaction.user_id}")
    print(f"  Amount: {transaction.currency} {transaction.amount}")
    print(f"  Merchant: {transaction.merchant}")
    print(f"  Location: {transaction.location.city}, {transaction.location.country}")
    print(f"  Time: {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Device: {transaction.device_info.device_type} ({transaction.device_info.os})")
    
    # Get contextual analysis
    context = context_manager.get_transaction_context(transaction)
    
    print(f"\nContextual Analysis:")
    print(f"  Similar Cases Found: {len(context.get('similar_cases', []))}")
    print(f"  User Profile Available: {'Yes' if context.get('user_profile') else 'No'}")
    print(f"  Risk Profile Available: {'Yes' if context.get('risk_profile') else 'No'}")
    print(f"  Decision History Count: {len(context.get('decision_history', []))}")
    
    # Display contextual insights
    insights = context.get("contextual_insights", [])
    print(f"\nContextual Insights ({len(insights)} found):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight.insight_type.replace('_', ' ').title()}")
        print(f"     Description: {insight.description}")
        print(f"     Confidence: {insight.confidence:.3f}")
        print(f"     Risk Impact: {insight.risk_impact:+.3f}")
        print(f"     Evidence: {', '.join(insight.supporting_evidence)}")
    
    # Display risk factors
    risk_factors = context.get("risk_factors", {})
    print(f"\nRisk Factors Analysis:")
    for factor_name, factor_value in risk_factors.items():
        risk_level = "HIGH" if factor_value > 0.6 else "MEDIUM" if factor_value > 0.3 else "LOW"
        print(f"  {factor_name.replace('_', ' ').title()}: {factor_value:.3f} ({risk_level})")
    
    return context


def demonstrate_recommendation_engine(context_manager: ContextManager, scenario: Dict[str, Any]):
    """Demonstrate the recommendation engine."""
    print(f"\n{'-'*60}")
    print("RECOMMENDATION ENGINE")
    print(f"{'-'*60}")
    
    transaction = scenario["transaction"]
    
    # Get recommendation
    recommendation = context_manager.get_contextual_recommendation(transaction)
    
    print(f"Recommendation: {recommendation['recommendation']}")
    print(f"Confidence: {recommendation['confidence']:.3f}")
    print(f"Risk Score: {recommendation['risk_score']:+.3f}")
    
    print(f"\nReasoning ({len(recommendation['reasoning'])} factors):")
    for i, reason in enumerate(recommendation['reasoning'], 1):
        print(f"  {i}. {reason}")
    
    # Context summary
    summary = recommendation['context_summary']
    print(f"\nContext Summary:")
    print(f"  Similar Cases: {summary.get('similar_cases_count', 0)}")
    print(f"  Insights Generated: {summary.get('insights_count', 0)}")
    print(f"  Risk Factors: {summary.get('risk_factors_count', 0)}")
    print(f"  User Profile: {'Available' if summary.get('has_user_profile') else 'Not Available'}")
    print(f"  Risk Profile: {'Available' if summary.get('has_risk_profile') else 'Not Available'}")
    
    # Compare with expected outcome
    expected = scenario.get("expected_outcome", "UNKNOWN")
    actual = recommendation['recommendation']
    match_status = "✓ MATCH" if expected == actual else "✗ DIFFERENT"
    
    print(f"\nOutcome Comparison:")
    print(f"  Expected: {expected}")
    print(f"  Actual: {actual}")
    print(f"  Status: {match_status}")
    
    return recommendation


def demonstrate_risk_evolution(context_manager: ContextManager):
    """Demonstrate risk evolution tracking."""
    print(f"\n{'='*80}")
    print("RISK EVOLUTION DEMONSTRATION")
    print(f"{'='*80}")
    
    # Create a series of transactions showing risk evolution
    user_id = "user_evolution_999"
    base_time = datetime.now() - timedelta(days=30)
    
    transactions = []
    
    # Week 1: Normal behavior
    for i in range(3):
        transactions.append(Transaction(
            id=f"tx_evo_week1_{i}",
            user_id=user_id,
            amount=Decimal(f"{50 + i * 10}.00"),
            currency="USD",
            merchant="Regular Store",
            category="groceries",
            location=Location(country="US", city="Chicago"),
            timestamp=base_time + timedelta(days=i * 2),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_regular", device_type="mobile", os="iOS"),
            ip_address="192.168.1.100",
            session_id=f"session_week1_{i}"
        ))
    
    # Week 2: Slightly elevated risk
    for i in range(2):
        transactions.append(Transaction(
            id=f"tx_evo_week2_{i}",
            user_id=user_id,
            amount=Decimal(f"{150 + i * 50}.00"),  # Higher amounts
            currency="USD",
            merchant="Online Store",
            category="electronics",
            location=Location(country="US", city="Chicago"),
            timestamp=base_time + timedelta(days=7 + i * 2),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_regular", device_type="desktop", os="Windows"),  # Different device
            ip_address="192.168.1.100",
            session_id=f"session_week2_{i}"
        ))
    
    # Week 3: High risk behavior
    transactions.append(Transaction(
        id="tx_evo_week3_1",
        user_id=user_id,
        amount=Decimal("1500.00"),  # Very high amount
        currency="USD",
        merchant="Luxury Retailer",
        category="luxury_goods",
        location=Location(country="US", city="Las Vegas"),  # Different city
        timestamp=base_time + timedelta(days=14),
        card_type="credit",
        device_info=DeviceInfo(device_id="device_unknown", device_type="desktop", os="Windows"),
        ip_address="10.0.0.50",  # Different IP
        session_id="session_week3_1"
    ))
    
    print("Analyzing risk evolution over time...")
    
    for i, tx in enumerate(transactions):
        print(f"\nTransaction {i+1}: {tx.id}")
        print(f"  Amount: ${tx.amount}")
        print(f"  Merchant: {tx.merchant}")
        print(f"  Location: {tx.location.city}")
        print(f"  Device: {tx.device_info.device_type}")
        print(f"  Date: {tx.timestamp.strftime('%Y-%m-%d')}")
        
        # Analyze context (simplified for demo)
        context = {
            "user_profile": None,
            "decision_history": [],
            "similar_cases": []
        }
        
        risk_factors = context_manager._analyze_risk_factors(tx, context)
        overall_risk = sum(risk_factors.values()) / len(risk_factors) if risk_factors else 0
        
        risk_level = "HIGH" if overall_risk > 0.6 else "MEDIUM" if overall_risk > 0.3 else "LOW"
        print(f"  Overall Risk: {overall_risk:.3f} ({risk_level})")


def main():
    """Main demonstration function."""
    print("Context-Aware Decision Making System Demo")
    print("=" * 80)
    
    try:
        # Initialize components (using mock for demo)
        print("Initializing Context-Aware Decision System...")
        
        # Create a mock memory manager for demo purposes
        class MockMemoryManager:
            def __init__(self):
                self.scenarios_data = {}
            
            def get_similar_transactions(self, transaction, threshold, limit):
                scenario_data = self.scenarios_data.get(transaction.user_id, {})
                return scenario_data.get("similar_cases", [])
            
            def get_user_profile(self, user_id):
                scenario_data = self.scenarios_data.get(user_id, {})
                return scenario_data.get("user_profile")
            
            def get_risk_profile(self, user_id):
                scenario_data = self.scenarios_data.get(user_id, {})
                return scenario_data.get("risk_profile")
            
            def get_user_decision_history(self, user_id, days_back):
                scenario_data = self.scenarios_data.get(user_id, {})
                return scenario_data.get("decision_history", [])
            
            def set_scenario_data(self, user_id, data):
                self.scenarios_data[user_id] = data
        
        mock_memory_manager = MockMemoryManager()
        context_manager = ContextManager(mock_memory_manager)
        
        # Create test scenarios
        scenarios = create_test_scenarios()
        
        print(f"\nCreated {len(scenarios)} test scenarios for demonstration\n")
        
        # Demonstrate each scenario
        for scenario in scenarios:
            # Set up mock data for this scenario
            user_id = scenario["transaction"].user_id
            mock_memory_manager.set_scenario_data(user_id, {
                "user_profile": scenario.get("user_profile"),
                "similar_cases": scenario.get("similar_cases", []),
                "decision_history": scenario.get("decision_history", []),
                "risk_profile": scenario.get("risk_profile")
            })
            
            # Demonstrate contextual analysis
            context = demonstrate_contextual_analysis(context_manager, scenario)
            
            # Demonstrate recommendation engine
            recommendation = demonstrate_recommendation_engine(context_manager, scenario)
            
            print()  # Add spacing between scenarios
        
        # Demonstrate risk evolution
        demonstrate_risk_evolution(context_manager)
        
        print(f"\n{'='*80}")
        print("DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print("\nKey Capabilities Demonstrated:")
        print("✓ Contextual transaction analysis")
        print("✓ Risk factor assessment")
        print("✓ Contextual insights generation")
        print("✓ Intelligent recommendation engine")
        print("✓ Risk evolution tracking")
        print("✓ Multi-scenario decision making")
        print("\nThe Context-Aware Decision Making System is ready for integration!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()