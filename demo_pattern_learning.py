"""
Demo script for Pattern Learning and Adaptation Engine.

This script demonstrates the capabilities of the pattern learning system
including pattern detection, feedback incorporation, and performance optimization.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from src.pattern_learning import PatternLearningEngine, LearningFeedback
from src.memory_manager import MemoryManager
from src.models import (
    Transaction, FraudPattern, FraudDecision, DecisionContext,
    Location, DeviceInfo, UserBehaviorProfile, RiskLevel
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_transactions() -> List[Transaction]:
    """Create sample transactions for demonstration."""
    transactions = []
    
    # Normal transaction
    transactions.append(Transaction(
        id="tx_001",
        user_id="user_123",
        amount=Decimal("50.00"),
        currency="USD",
        merchant="Starbucks",
        category="food",
        location=Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
        timestamp=datetime.now() - timedelta(hours=2),
        card_type="credit",
        device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
        ip_address="192.168.1.100",
        session_id="session_001"
    ))
    
    # Suspicious velocity pattern - multiple transactions in short time
    base_time = datetime.now() - timedelta(minutes=30)
    for i in range(4):
        transactions.append(Transaction(
            id=f"tx_velocity_{i:03d}",
            user_id="user_456",
            amount=Decimal(f"{100 + i * 50}.00"),
            currency="USD",
            merchant=f"OnlineMerchant_{i}",
            category="online_retail",
            location=Location(country="US", city="Los Angeles", latitude=34.0522, longitude=-118.2437),
            timestamp=base_time + timedelta(minutes=i * 2),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_002", device_type="desktop", os="Windows"),
            ip_address="10.0.0.50",
            session_id=f"session_velocity_{i}"
        ))
    
    # Geographic anomaly - impossible travel
    transactions.append(Transaction(
        id="tx_geo_001",
        user_id="user_789",
        amount=Decimal("200.00"),
        currency="USD",
        merchant="Local Store NYC",
        category="retail",
        location=Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
        timestamp=datetime.now() - timedelta(hours=1),
        card_type="credit",
        device_info=DeviceInfo(device_id="device_003", device_type="mobile", os="Android"),
        ip_address="192.168.1.200",
        session_id="session_geo_001"
    ))
    
    transactions.append(Transaction(
        id="tx_geo_002",
        user_id="user_789",  # Same user
        amount=Decimal("150.00"),
        currency="EUR",
        merchant="Paris Shop",
        category="retail",
        location=Location(country="FR", city="Paris", latitude=48.8566, longitude=2.3522),
        timestamp=datetime.now() - timedelta(minutes=30),  # 30 minutes later in Paris!
        card_type="credit",
        device_info=DeviceInfo(device_id="device_004", device_type="desktop", os="Windows"),
        ip_address="82.45.123.45",
        session_id="session_geo_002"
    ))
    
    return transactions


def create_sample_feedback() -> List[LearningFeedback]:
    """Create sample feedback for pattern learning."""
    feedback_list = []
    
    # Feedback for velocity pattern (confirmed fraud)
    for i in range(4):
        feedback_list.append(LearningFeedback(
            transaction_id=f"tx_velocity_{i:03d}",
            actual_outcome="fraud",
            predicted_decision=FraudDecision.DECLINED,
            confidence_score=0.85 + i * 0.03,
            pattern_ids_triggered=["velocity_rapid_fire_pattern"],
            timestamp=datetime.now(),
            feedback_source="investigation_team",
            additional_context={"investigation_id": f"inv_{i:03d}", "confirmed_by": "analyst_1"}
        ))
    
    # Feedback for geographic pattern (confirmed fraud)
    feedback_list.append(LearningFeedback(
        transaction_id="tx_geo_002",
        actual_outcome="fraud",
        predicted_decision=FraudDecision.DECLINED,
        confidence_score=0.95,
        pattern_ids_triggered=["geo_impossible_travel_pattern"],
        timestamp=datetime.now(),
        feedback_source="manual_review",
        additional_context={"reviewer": "senior_analyst", "confidence": "high"}
    ))
    
    # Some false positive feedback
    feedback_list.append(LearningFeedback(
        transaction_id="tx_001",
        actual_outcome="legitimate",
        predicted_decision=FraudDecision.FLAGGED,
        confidence_score=0.65,
        pattern_ids_triggered=["amount_round_numbers_pattern"],
        timestamp=datetime.now(),
        feedback_source="customer_dispute",
        additional_context={"dispute_id": "disp_001", "customer_verified": True}
    ))
    
    return feedback_list


def demonstrate_pattern_detection(engine: PatternLearningEngine):
    """Demonstrate automatic pattern detection."""
    print("\n" + "="*60)
    print("PATTERN DETECTION DEMONSTRATION")
    print("="*60)
    
    logger.info("Detecting new fraud patterns...")
    
    # Detect new patterns
    new_patterns = engine.detect_new_patterns(lookback_days=30, min_occurrences=3)
    
    print(f"\nDetected {len(new_patterns)} new fraud patterns:")
    for i, pattern in enumerate(new_patterns, 1):
        print(f"\n{i}. Pattern ID: {pattern.pattern_id}")
        print(f"   Type: {pattern.pattern_type}")
        print(f"   Description: {pattern.description}")
        print(f"   Confidence Threshold: {pattern.confidence_threshold:.3f}")
        print(f"   Indicators:")
        for indicator in pattern.indicators:
            print(f"     - {indicator}")
    
    return new_patterns


def demonstrate_feedback_incorporation(engine: PatternLearningEngine, feedback_list: List[LearningFeedback]):
    """Demonstrate feedback incorporation and learning."""
    print("\n" + "="*60)
    print("FEEDBACK INCORPORATION DEMONSTRATION")
    print("="*60)
    
    logger.info("Incorporating feedback for pattern learning...")
    
    print(f"\nIncorporating {len(feedback_list)} feedback samples:")
    
    for i, feedback in enumerate(feedback_list, 1):
        success = engine.incorporate_feedback(feedback)
        
        print(f"\n{i}. Transaction: {feedback.transaction_id}")
        print(f"   Actual Outcome: {feedback.actual_outcome}")
        print(f"   Predicted Decision: {feedback.predicted_decision.value}")
        print(f"   Confidence: {feedback.confidence_score:.3f}")
        print(f"   Patterns Triggered: {', '.join(feedback.pattern_ids_triggered)}")
        print(f"   Feedback Source: {feedback.feedback_source}")
        print(f"   Incorporation Status: {'Success' if success else 'Failed'}")
    
    # Show updated metrics
    print(f"\nPattern Metrics After Feedback:")
    for pattern_id, metrics in engine.pattern_metrics.items():
        print(f"\n  Pattern: {pattern_id}")
        print(f"    True Positives: {metrics.true_positives}")
        print(f"    False Positives: {metrics.false_positives}")
        print(f"    True Negatives: {metrics.true_negatives}")
        print(f"    False Negatives: {metrics.false_negatives}")
        print(f"    Precision: {metrics.precision:.3f}")
        print(f"    Recall: {metrics.recall:.3f}")
        print(f"    F1 Score: {metrics.f1_score:.3f}")
        print(f"    Accuracy: {metrics.accuracy:.3f}")


def demonstrate_performance_evaluation(engine: PatternLearningEngine):
    """Demonstrate pattern performance evaluation."""
    print("\n" + "="*60)
    print("PERFORMANCE EVALUATION DEMONSTRATION")
    print("="*60)
    
    logger.info("Evaluating pattern performance...")
    
    # Evaluate performance
    performance_report = engine.evaluate_pattern_performance(days_back=30)
    
    print(f"\nPerformance Report for {len(performance_report)} patterns:")
    
    for pattern_id, metrics in performance_report.items():
        print(f"\n  Pattern: {pattern_id}")
        print(f"    Precision: {metrics['precision']:.3f}")
        print(f"    Recall: {metrics['recall']:.3f}")
        print(f"    F1 Score: {metrics['f1_score']:.3f}")
        print(f"    Accuracy: {metrics['accuracy']:.3f}")
        print(f"    False Positive Rate: {metrics['false_positive_rate']:.3f}")
        print(f"    Effectiveness Score: {metrics['effectiveness_score']:.3f}")
        print(f"    Detection Count: {metrics['detection_count']}")
        print(f"    Confidence Threshold: {metrics['confidence_threshold']:.3f}")


def demonstrate_learning_recommendations(engine: PatternLearningEngine):
    """Demonstrate learning recommendations generation."""
    print("\n" + "="*60)
    print("LEARNING RECOMMENDATIONS DEMONSTRATION")
    print("="*60)
    
    logger.info("Generating learning recommendations...")
    
    # Get recommendations
    recommendations = engine.get_learning_recommendations()
    
    print(f"\nGenerated {len(recommendations)} learning recommendations:")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. Pattern: {rec['pattern_id']}")
        print(f"   Type: {rec['type']}")
        print(f"   Priority: {rec['priority'].upper()}")
        print(f"   Reason: {rec['reason']}")
        print(f"   Suggested Action: {rec['suggested_action']}")


def demonstrate_threshold_optimization(engine: PatternLearningEngine):
    """Demonstrate pattern threshold optimization."""
    print("\n" + "="*60)
    print("THRESHOLD OPTIMIZATION DEMONSTRATION")
    print("="*60)
    
    logger.info("Optimizing pattern thresholds...")
    
    # Show current thresholds
    print("\nCurrent Pattern Thresholds:")
    for pattern_id, metrics in engine.pattern_metrics.items():
        print(f"  {pattern_id}: Current metrics available for optimization")
    
    # Optimize thresholds
    optimized_thresholds = engine.optimize_pattern_thresholds()
    
    print(f"\nOptimized Thresholds for {len(optimized_thresholds)} patterns:")
    
    for pattern_id, new_threshold in optimized_thresholds.items():
        print(f"  {pattern_id}: {new_threshold:.3f}")
    
    if not optimized_thresholds:
        print("  No threshold optimizations found (insufficient data or already optimal)")


def main():
    """Main demonstration function."""
    print("Pattern Learning and Adaptation Engine Demo")
    print("=" * 60)
    
    try:
        # Initialize components (using mock for demo)
        print("Initializing Pattern Learning Engine...")
        
        # Create a mock memory manager for demo purposes
        class MockMemoryManager:
            def __init__(self):
                self.patterns = []
            
            def store_fraud_pattern(self, pattern):
                self.patterns.append(pattern)
                return True
            
            def get_all_fraud_patterns(self):
                return self.patterns
        
        mock_memory_manager = MockMemoryManager()
        engine = PatternLearningEngine(mock_memory_manager)
        
        # Set lower thresholds for demo
        engine.pattern_update_threshold = 2
        
        # Demonstrate pattern detection
        detected_patterns = demonstrate_pattern_detection(engine)
        
        # Create sample feedback
        feedback_list = create_sample_feedback()
        
        # Add some patterns to the mock memory manager for feedback demo
        for pattern in detected_patterns:
            mock_memory_manager.store_fraud_pattern(pattern)
        
        # Demonstrate feedback incorporation
        demonstrate_feedback_incorporation(engine, feedback_list)
        
        # Demonstrate performance evaluation
        demonstrate_performance_evaluation(engine)
        
        # Demonstrate learning recommendations
        demonstrate_learning_recommendations(engine)
        
        # Demonstrate threshold optimization
        demonstrate_threshold_optimization(engine)
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey Capabilities Demonstrated:")
        print("✓ Automatic fraud pattern detection")
        print("✓ Feedback incorporation and learning")
        print("✓ Performance evaluation and metrics")
        print("✓ Learning recommendations generation")
        print("✓ Threshold optimization")
        print("\nThe Pattern Learning Engine is ready for integration!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()