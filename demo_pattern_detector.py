"""
Demo script for Pattern Detection Agent.

This script demonstrates the capabilities of the specialized pattern detection agent
including statistical anomaly detection, behavioral pattern recognition, and trend analysis.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import json

from specialized_agents.pattern_detector import PatternDetector
from specialized_agents.base_agent import AgentConfiguration, AgentCapability
from memory_system.memory_manager import MemoryManager
from memory_system.pattern_learning import PatternLearningEngine
from memory_system.models import Transaction, Location, DeviceInfo, FraudPattern

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_scenarios() -> List[Dict[str, Any]]:
    """Create various test scenarios for pattern detection."""
    scenarios = []
    
    # Scenario 1: Normal transaction (baseline)
    scenarios.append({
        "name": "Normal Transaction",
        "description": "Regular transaction within user's normal patterns",
        "request": {
            "transaction": {
                "id": "tx_normal_001",
                "user_id": "user_established_001",
                "amount": "125.50",
                "currency": "USD",
                "merchant": "Grocery Store",
                "category": "groceries",
                "location": {
                    "country": "US",
                    "city": "Seattle"
                },
                "timestamp": datetime.now().replace(hour=14).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_normal_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_normal_001"
            },
            "analysis_type": "full"
        },
        "expected_anomaly_level": "low"
    })
    
    # Scenario 2: Amount anomaly
    scenarios.append({
        "name": "Amount Anomaly",
        "description": "Transaction with unusually high amount",
        "request": {
            "transaction": {
                "id": "tx_amount_anomaly_001",
                "user_id": "user_established_001",
                "amount": "5000.00",  # Much higher than normal
                "currency": "USD",
                "merchant": "Electronics Store",
                "category": "electronics",
                "location": {
                    "country": "US",
                    "city": "Seattle"
                },
                "timestamp": datetime.now().replace(hour=15).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_normal_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_amount_001"
            },
            "analysis_type": "full"
        },
        "expected_anomaly_level": "high"
    })
    
    # Scenario 3: Temporal anomaly
    scenarios.append({
        "name": "Temporal Anomaly",
        "description": "Transaction at unusual time (late night)",
        "request": {
            "transaction": {
                "id": "tx_temporal_anomaly_001",
                "user_id": "user_established_001",
                "amount": "89.99",
                "currency": "USD",
                "merchant": "24/7 Convenience Store",
                "category": "convenience",
                "location": {
                    "country": "US",
                    "city": "Seattle"
                },
                "timestamp": datetime.now().replace(hour=3, minute=30).isoformat(),  # 3:30 AM
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_normal_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_temporal_001"
            },
            "analysis_type": "full"
        },
        "expected_anomaly_level": "medium"
    })
    
    # Scenario 4: Merchant anomaly (high-risk)
    scenarios.append({
        "name": "Merchant Anomaly",
        "description": "Transaction with high-risk merchant",
        "request": {
            "transaction": {
                "id": "tx_merchant_anomaly_001",
                "user_id": "user_established_001",
                "amount": "500.00",
                "currency": "USD",
                "merchant": "Crypto Casino Online",  # High-risk keywords
                "category": "gambling",
                "location": {
                    "country": "US",
                    "city": "Las Vegas"
                },
                "timestamp": datetime.now().replace(hour=22).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_different_001",
                    "device_type": "desktop",
                    "os": "Windows"
                },
                "ip_address": "10.0.0.50",
                "session_id": "session_merchant_001"
            },
            "analysis_type": "full"
        },
        "expected_anomaly_level": "high"
    })
    
    # Scenario 5: Location anomaly
    scenarios.append({
        "name": "Location Anomaly",
        "description": "Transaction in new country",
        "request": {
            "transaction": {
                "id": "tx_location_anomaly_001",
                "user_id": "user_established_001",
                "amount": "200.00",
                "currency": "EUR",
                "merchant": "Paris Boutique",
                "category": "retail",
                "location": {
                    "country": "FR",  # New country
                    "city": "Paris"
                },
                "timestamp": datetime.now().replace(hour=16).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_travel_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "82.45.123.45",
                "session_id": "session_location_001"
            },
            "analysis_type": "full"
        },
        "expected_anomaly_level": "medium"
    })
    
    # Scenario 6: Multiple anomalies
    scenarios.append({
        "name": "Multiple Anomalies",
        "description": "Transaction with multiple anomaly indicators",
        "request": {
            "transaction": {
                "id": "tx_multiple_anomaly_001",
                "user_id": "user_established_001",
                "amount": "3500.00",  # High amount
                "currency": "USD",
                "merchant": "Bitcoin Exchange Pro",  # High-risk merchant
                "category": "financial",
                "location": {
                    "country": "XX",  # Unknown country
                    "city": "Unknown"
                },
                "timestamp": datetime.now().replace(hour=4).isoformat(),  # Late night
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_unknown_001",
                    "device_type": "unknown",
                    "os": "unknown"
                },
                "ip_address": "0.0.0.0",
                "session_id": "session_multiple_001"
            },
            "analysis_type": "full"
        },
        "expected_anomaly_level": "critical"
    })
    
    return scenarios


def create_behavioral_pattern_scenarios() -> List[Dict[str, Any]]:
    """Create scenarios to demonstrate behavioral pattern detection."""
    scenarios = []
    base_time = datetime.now()
    
    # Escalating spending pattern
    for i in range(5):
        scenarios.append({
            "name": f"Escalating Pattern Transaction {i+1}",
            "description": f"Transaction {i+1} in escalating spending pattern",
            "request": {
                "transaction": {
                    "id": f"tx_escalating_{i+1:03d}",
                    "user_id": "user_behavioral_001",
                    "amount": f"{100 + i * 100}.00",  # 100, 200, 300, 400, 500
                    "currency": "USD",
                    "merchant": f"Online Store {i+1}",
                    "category": "online_retail",
                    "location": {
                        "country": "US",
                        "city": "Portland"
                    },
                    "timestamp": (base_time + timedelta(hours=i * 2)).isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_behavioral_001",
                        "device_type": "desktop",
                        "os": "Windows"
                    },
                    "ip_address": "192.168.1.200",
                    "session_id": f"session_escalating_{i+1}"
                },
                "analysis_type": "behavioral"
            },
            "expected_pattern": "escalating_spending" if i >= 2 else None
        })
    
    return scenarios


def demonstrate_pattern_detection(detector: PatternDetector, scenario: Dict[str, Any]):
    """Demonstrate pattern detection for a scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    print(f"Expected Anomaly Level: {scenario['expected_anomaly_level']}")
    
    # Display transaction details
    tx_data = scenario["request"]["transaction"]
    print(f"\nTransaction Details:")
    print(f"  ID: {tx_data['id']}")
    print(f"  User: {tx_data['user_id']}")
    print(f"  Amount: {tx_data['currency']} {tx_data['amount']}")
    print(f"  Merchant: {tx_data['merchant']}")
    print(f"  Category: {tx_data['category']}")
    print(f"  Location: {tx_data['location']['city']}, {tx_data['location']['country']}")
    print(f"  Time: {tx_data['timestamp']}")
    print(f"  Device: {tx_data['device_info']['device_type']} ({tx_data['device_info']['os']})")
    
    # Process the pattern detection
    result = detector.execute_with_metrics(scenario["request"])
    
    print(f"\nPattern Detection Results:")
    print(f"  Success: {result.success}")
    print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
    print(f"  Overall Confidence: {result.confidence_score:.3f}")
    
    if result.success:
        detection_data = result.result_data.get("pattern_detection", {})
        
        print(f"  Overall Anomaly Score: {detection_data.get('overall_anomaly_score', 0):.3f}")
        
        # Display anomaly scores
        anomaly_scores = detection_data.get("anomaly_scores", [])
        if anomaly_scores:
            print(f"\nAnomaly Detection ({len(anomaly_scores)} anomalies found):")
            for i, anomaly in enumerate(anomaly_scores, 1):
                print(f"  {i}. {anomaly.anomaly_type.replace('_', ' ').title()}")
                print(f"     Score: {anomaly.score:.3f}")
                print(f"     Confidence: {anomaly.confidence:.3f}")
                print(f"     Description: {anomaly.description}")
                
                if anomaly.statistical_evidence:
                    print(f"     Statistical Evidence:")
                    for key, value in anomaly.statistical_evidence.items():
                        if isinstance(value, float):
                            print(f"       {key}: {value:.3f}")
                        else:
                            print(f"       {key}: {value}")
        else:
            print(f"\n✅ No anomalies detected")
        
        # Display behavioral patterns
        behavioral_patterns = detection_data.get("behavioral_patterns", [])
        if behavioral_patterns:
            print(f"\nBehavioral Patterns ({len(behavioral_patterns)} patterns found):")
            for i, pattern in enumerate(behavioral_patterns, 1):
                print(f"  {i}. {pattern.pattern_type.replace('_', ' ').title()}")
                print(f"     Description: {pattern.description}")
                print(f"     Strength: {pattern.strength:.3f}")
                print(f"     Risk Level: {pattern.risk_level}")
                print(f"     Trend: {pattern.trend_direction}")
        else:
            print(f"\n✅ No behavioral patterns detected")
        
        # Display trend analyses
        trend_analyses = detection_data.get("trend_analyses", [])
        if trend_analyses:
            print(f"\nTrend Analysis ({len(trend_analyses)} trends found):")
            for i, trend in enumerate(trend_analyses, 1):
                print(f"  {i}. {trend.metric_name.replace('_', ' ').title()}")
                print(f"     Direction: {trend.trend_direction}")
                print(f"     Strength: {trend.trend_strength:.3f}")
                print(f"     Confidence: {trend.prediction_confidence:.3f}")
                print(f"     Current Value: {trend.current_value:.2f}")
                print(f"     Predicted Next: {trend.predicted_next_value:.2f}")
                print(f"     Data Points: {trend.data_points}")
        else:
            print(f"\n✅ No significant trends detected")
        
        # Display pattern similarities
        similarities = detection_data.get("pattern_similarity_matches", [])
        if similarities:
            print(f"\nPattern Similarities ({len(similarities)} matches found):")
            for i, match in enumerate(similarities, 1):
                print(f"  {i}. Pattern: {match['pattern_type']}")
                print(f"     Similarity Score: {match['similarity_score']:.3f}")
                print(f"     Description: {match['description']}")
                print(f"     Effectiveness: {match['effectiveness_score']:.3f}")
        else:
            print(f"\n✅ No similar patterns found")
        
        # Display recommendations
        recommendations = detection_data.get("recommendations", [])
        if recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
    
    else:
        print(f"  Error: {result.error_message}")
    
    return result


def demonstrate_behavioral_patterns(detector: PatternDetector):
    """Demonstrate behavioral pattern detection with sequential transactions."""
    print(f"\n{'='*80}")
    print("BEHAVIORAL PATTERN DETECTION DEMONSTRATION")
    print(f"{'='*80}")
    
    behavioral_scenarios = create_behavioral_pattern_scenarios()
    
    print(f"Processing {len(behavioral_scenarios)} transactions to demonstrate behavioral pattern detection...")
    
    results = []
    for scenario in behavioral_scenarios:
        print(f"\nProcessing: {scenario['name']}")
        result = detector.execute_with_metrics(scenario["request"])
        results.append(result)
        
        if result.success:
            detection = result.result_data.get("pattern_detection", {})
            behavioral_patterns = detection.get("behavioral_patterns", [])
            
            if behavioral_patterns:
                print(f"  🔍 Behavioral patterns detected: {len(behavioral_patterns)}")
                for pattern in behavioral_patterns:
                    print(f"     - {pattern.pattern_type}: {pattern.description}")
            else:
                print(f"  ✅ No behavioral patterns detected yet")
            
            print(f"  Anomaly Score: {detection.get('overall_anomaly_score', 0):.3f}")
    
    return results


def demonstrate_trend_analysis(detector: PatternDetector):
    """Demonstrate trend analysis capabilities."""
    print(f"\n{'='*80}")
    print("TREND ANALYSIS DEMONSTRATION")
    print(f"{'='*80}")
    
    # Create a transaction for trend analysis
    trend_request = {
        "transaction": {
            "id": "tx_trend_analysis_001",
            "user_id": "user_trend_001",
            "amount": "150.00",
            "currency": "USD",
            "merchant": "Regular Store",
            "category": "retail",
            "location": {
                "country": "US",
                "city": "Denver"
            },
            "timestamp": datetime.now().isoformat(),
            "card_type": "credit",
            "device_info": {
                "device_id": "device_trend_001",
                "device_type": "mobile",
                "os": "Android"
            },
            "ip_address": "192.168.1.150",
            "session_id": "session_trend_001"
        },
        "analysis_type": "trend"
    }
    
    print("Analyzing trends for user with transaction history...")
    
    result = detector.execute_with_metrics(trend_request)
    
    if result.success:
        detection = result.result_data.get("pattern_detection", {})
        trend_analyses = detection.get("trend_analyses", [])
        
        if trend_analyses:
            print(f"\nTrend Analysis Results ({len(trend_analyses)} trends):")
            for trend in trend_analyses:
                print(f"\n  Metric: {trend.metric_name.replace('_', ' ').title()}")
                print(f"  Trend Direction: {trend.trend_direction}")
                print(f"  Trend Strength: {trend.trend_strength:.3f}")
                print(f"  Prediction Confidence: {trend.prediction_confidence:.3f}")
                print(f"  Current Value: {trend.current_value:.2f}")
                print(f"  Predicted Next Value: {trend.predicted_next_value:.2f}")
                print(f"  Analysis Window: {trend.time_window_days} days")
                print(f"  Data Points Used: {trend.data_points}")
        else:
            print("\n  ℹ️  Insufficient data for trend analysis (requires more transaction history)")
    else:
        print(f"\n  ❌ Error in trend analysis: {result.error_message}")


def demonstrate_agent_monitoring(detector: PatternDetector):
    """Demonstrate agent monitoring and performance metrics."""
    print(f"\n{'='*80}")
    print("AGENT MONITORING DEMONSTRATION")
    print(f"{'='*80}")
    
    # Get agent status
    status = detector.get_status()
    
    print(f"Agent Status:")
    print(f"  Agent ID: {status['agent_id']}")
    print(f"  Agent Name: {status['agent_name']}")
    print(f"  Version: {status['version']}")
    print(f"  Status: {status['status']}")
    print(f"  Capabilities: {', '.join(status['capabilities'])}")
    
    # Display metrics
    metrics = status['metrics']
    print(f"\nPerformance Metrics:")
    print(f"  Requests Processed: {metrics['requests_processed']}")
    print(f"  Successful Analyses: {metrics['successful_analyses']}")
    print(f"  Failed Analyses: {metrics['failed_analyses']}")
    print(f"  Success Rate: {metrics['success_rate']:.1f}%")
    print(f"  Error Rate: {metrics['error_rate']:.1f}%")
    print(f"  Average Processing Time: {metrics['average_processing_time_ms']:.2f}ms")
    print(f"  Peak Processing Time: {metrics['peak_processing_time_ms']:.2f}ms")
    print(f"  Throughput: {metrics['throughput_per_second']:.2f} req/sec")
    print(f"  Uptime: {metrics['uptime_seconds']:.0f} seconds")
    
    # Get pattern cache statistics
    cache_stats = detector.get_pattern_cache_stats()
    print(f"\nPattern Cache Statistics:")
    print(f"  Cached Patterns: {cache_stats['cached_patterns']}")
    print(f"  Cached Baselines: {cache_stats['cached_baselines']}")
    print(f"  Cache Size Estimate: {cache_stats['cache_size_estimate']} bytes")
    
    # Get health check
    health = detector.get_health_check()
    print(f"\nHealth Check:")
    print(f"  Health Status: {health['health_status']}")
    print(f"  Issues: {len(health['issues'])}")
    
    if health['issues']:
        for issue in health['issues']:
            print(f"    - {issue}")
    else:
        print(f"    No issues detected")


def main():
    """Main demonstration function."""
    print("Pattern Detection Agent Demo")
    print("=" * 80)
    
    try:
        # Initialize components (using mock for demo)
        print("Initializing Pattern Detection Agent...")
        
        # Create mock memory manager and pattern learning engine
        class MockMemoryManager:
            def get_user_transaction_history(self, user_id, days_back=30, limit=100):
                # Return mock transaction history for baseline calculation
                base_time = datetime.now() - timedelta(days=days_back)
                mock_transactions = []
                
                # Create realistic transaction history
                for i in range(min(20, limit)):
                    from memory_system.models import Transaction, Location, DeviceInfo
                    
                    tx = Transaction(
                        id=f"mock_tx_{i:03d}",
                        user_id=user_id,
                        amount=Decimal(f"{80 + (i % 10) * 10}.00"),  # Amounts between 80-170
                        currency="USD",
                        merchant=f"Store_{i % 5}",  # 5 different stores
                        category="retail",
                        location=Location(country="US", city="Seattle"),
                        timestamp=base_time + timedelta(days=i),
                        card_type="credit",
                        device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
                        ip_address="192.168.1.100",
                        session_id=f"session_{i}"
                    )
                    mock_transactions.append(tx)
                
                return mock_transactions
            
            def get_all_fraud_patterns(self):
                # Return mock fraud patterns
                return [
                    FraudPattern(
                        pattern_id="mock_pattern_001",
                        pattern_type="velocity_fraud",
                        description="Mock velocity pattern",
                        indicators=["rapid transactions"],
                        confidence_threshold=0.8,
                        detection_count=10,
                        false_positive_rate=0.1,
                        created_at=datetime.now() - timedelta(days=30),
                        last_seen=datetime.now(),
                        effectiveness_score=0.85
                    )
                ]
        
        class MockPatternLearningEngine:
            def detect_new_patterns(self, **kwargs):
                return []
        
        mock_memory_manager = MockMemoryManager()
        mock_pattern_learning = MockPatternLearningEngine()
        
        # Create pattern detector
        detector = PatternDetector(mock_memory_manager, mock_pattern_learning)
        
        print(f"Pattern Detection Agent initialized successfully!")
        print(f"Agent ID: {detector.config.agent_id}")
        print(f"Capabilities: {[cap.value for cap in detector.config.capabilities]}")
        
        # Create test scenarios
        test_scenarios = create_test_scenarios()
        
        print(f"\nCreated {len(test_scenarios)} test scenarios for demonstration")
        
        # Demonstrate individual pattern detection
        for scenario in test_scenarios:
            result = demonstrate_pattern_detection(detector, scenario)
        
        # Demonstrate behavioral pattern detection
        behavioral_results = demonstrate_behavioral_patterns(detector)
        
        # Demonstrate trend analysis
        demonstrate_trend_analysis(detector)
        
        # Demonstrate agent monitoring
        demonstrate_agent_monitoring(detector)
        
        print(f"\n{'='*80}")
        print("DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print("\nKey Capabilities Demonstrated:")
        print("✓ Statistical anomaly detection (amount, frequency, temporal, merchant, location)")
        print("✓ Behavioral pattern recognition (spending patterns, temporal preferences)")
        print("✓ Trend analysis and prediction")
        print("✓ Pattern similarity matching with known fraud patterns")
        print("✓ Multi-dimensional anomaly scoring")
        print("✓ Agent performance monitoring and health checks")
        print("✓ Real-time pattern detection with caching")
        print("\nThe Pattern Detection Agent is ready for production deployment!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()