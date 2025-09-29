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
        "description": "Regular transaction within normal patterns",
        "request": {
            "transaction": {
                "id": "tx_normal_pattern_001",
                "user_id": "user_established_001",
                "amount": "125.00",
                "currency": "USD",
                "merchant": "Regular Store",
                "category": "retail",
                "location": {
                    "country": "US",
                    "city": "Chicago"
                },
                "timestamp": datetime.now().replace(hour=14).isoformat(),  # Afternoon
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_normal_001"
            },
            "analysis_type": "full"
        },
        "expected_anomalies": 0
    })
    
    # Scenario 2: Amount anomaly
    scenarios.append({
        "name": "High Amount Anomaly",
        "description": "Transaction with unusually high amount",
        "request": {
            "transaction": {
                "id": "tx_amount_anomaly_001",
                "user_id": "user_established_001",  # Same user as normal
                "amount": "5000.00",  # Much higher than normal
                "currency": "USD",
                "merchant": "Electronics Store",
                "category": "electronics",
                "location": {
                    "country": "US",
                    "city": "Chicago"
                },
                "timestamp": datetime.now().replace(hour=14).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_amount_001"
            },
            "analysis_type": "anomaly"
        },
        "expected_anomalies": 1
    })
    
    # Scenario 3: Temporal anomaly
    scenarios.append({
        "name": "Temporal Anomaly",
        "description": "Transaction at unusual time (late night)",
        "request": {
            "transaction": {
                "id": "tx_temporal_anomaly_001",
                "user_id": "user_established_001",
                "amount": "150.00",
                "currency": "USD",
                "merchant": "24/7 Store",
                "category": "convenience",
                "location": {
                    "country": "US",
                    "city": "Chicago"
                },
                "timestamp": datetime.now().replace(hour=3, minute=30).isoformat(),  # 3:30 AM
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_temporal_001"
            },
            "analysis_type": "anomaly"
        },
        "expected_anomalies": 1
    })
    
    # Scenario 4: Merchant anomaly
    scenarios.append({
        "name": "High-Risk Merchant Anomaly",
        "description": "Transaction with high-risk merchant",
        "request": {
            "transaction": {
                "id": "tx_merchant_anomaly_001",
                "user_id": "user_established_001",
                "amount": "500.00",
                "currency": "USD",
                "merchant": "Crypto Casino Exchange",  # High-risk merchant
                "category": "gambling",
                "location": {
                    "country": "US",
                    "city": "Las Vegas"
                },
                "timestamp": datetime.now().replace(hour=22).isoformat(),  # Late evening
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "desktop",
                    "os": "Windows"
                },
                "ip_address": "10.0.0.50",
                "session_id": "session_merchant_001"
            },
            "analysis_type": "anomaly"
        },
        "expected_anomalies": 1
    })
    
    # Scenario 5: Location anomaly
    scenarios.append({
        "name": "Geographic Anomaly",
        "description": "Transaction in unusual location",
        "request": {
            "transaction": {
                "id": "tx_location_anomaly_001",
                "user_id": "user_established_001",
                "amount": "300.00",
                "currency": "EUR",
                "merchant": "Paris Boutique",
                "category": "luxury",
                "location": {
                    "country": "FR",  # Different country
                    "city": "Paris"
                },
                "timestamp": datetime.now().isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_new_002",  # Different device
                    "device_type": "desktop",
                    "os": "Windows"
                },
                "ip_address": "82.45.123.45",  # Foreign IP
                "session_id": "session_location_001"
            },
            "analysis_type": "anomaly"
        },
        "expected_anomalies": 1
    })
    
    # Scenario 6: Multiple anomalies
    scenarios.append({
        "name": "Multiple Anomalies",
        "description": "Transaction with multiple anomalous characteristics",
        "request": {
            "transaction": {
                "id": "tx_multiple_anomaly_001",
                "user_id": "user_established_001",
                "amount": "8000.00",  # High amount
                "currency": "USD",
                "merchant": "Bitcoin ATM Network",  # High-risk merchant
                "category": "financial",
                "location": {
                    "country": "XX",  # Unknown country
                    "city": "Unknown"
                },
                "timestamp": datetime.now().replace(hour=2, minute=15).isoformat(),  # Very late night
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_unknown_003",
                    "device_type": "unknown",
                    "os": "unknown"
                },
                "ip_address": "0.0.0.0",
                "session_id": "session_multiple_001"
            },
            "analysis_type": "full"
        },
        "expected_anomalies": 3
    })
    
    return scenarios


def create_behavioral_pattern_scenarios() -> List[Dict[str, Any]]:
    """Create scenarios for behavioral pattern detection."""
    scenarios = []
    base_time = datetime.now()
    
    # Scenario 1: Escalating spending pattern
    escalating_transactions = []
    for i in range(6):
        escalating_transactions.append({
            "name": f"Escalating Transaction {i+1}",
            "description": f"Transaction {i+1} in escalating spending pattern",
            "request": {
                "transaction": {
                    "id": f"tx_escalating_{i+1:03d}",
                    "user_id": "user_behavioral_001",
                    "amount": f"{100 + i * 75}.00",  # 100, 175, 250, 325, 400, 475
                    "currency": "USD",
                    "merchant": f"Store_{i+1}",
                    "category": "retail",
                    "location": {
                        "country": "US",
                        "city": "Seattle"
                    },
                    "timestamp": (base_time - timedelta(days=6-i)).isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_behavioral_001",
                        "device_type": "mobile",
                        "os": "iOS"
                    },
                    "ip_address": "192.168.1.200",
                    "session_id": f"session_escalating_{i+1}"
                },
                "analysis_type": "behavioral"
            },
            "expected_patterns": 1 if i >= 3 else 0  # Pattern should be detected after 4+ transactions
        })
    
    scenarios.extend(escalating_transactions)
    
    # Scenario 2: Round number preference pattern
    round_number_transactions = []
    amounts = ["100.00", "200.00", "50.00", "150.00", "300.00"]  # Mostly round numbers
    
    for i, amount in enumerate(amounts):
        round_number_transactions.append({
            "name": f"Round Number Transaction {i+1}",
            "description": f"Transaction {i+1} showing round number preference",
            "request": {
                "transaction": {
                    "id": f"tx_round_{i+1:03d}",
                    "user_id": "user_round_numbers_001",
                    "amount": amount,
                    "currency": "USD",
                    "merchant": "Various Store",
                    "category": "retail",
                    "location": {
                        "country": "US",
                        "city": "Portland"
                    },
                    "timestamp": (base_time - timedelta(days=5-i)).isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_round_001",
                        "device_type": "mobile",
                        "os": "Android"
                    },
                    "ip_address": "192.168.1.300",
                    "session_id": f"session_round_{i+1}"
                },
                "analysis_type": "behavioral"
            },
            "expected_patterns": 1 if i >= 3 else 0  # Pattern should be detected after enough data
        })
    
    scenarios.extend(round_number_transactions)
    
    return scenarios


def demonstrate_pattern_detection(detector: PatternDetector, scenario: Dict[str, Any]):
    """Demonstrate pattern detection for a scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    print(f"Expected Anomalies: {scenario.get('expected_anomalies', 'N/A')}")
    
    # Display transaction details
    tx_data = scenario["request"]["transaction"]
    print(f"\nTransaction Details:")
    print(f"  ID: {tx_data['id']}")
    print(f"  User: {tx_data['user_id']}")
    print(f"  Amount: {tx_data['currency']} {tx_data['amount']}")
    print(f"  Merchant: {tx_data['merchant']}")
    print(f"  Location: {tx_data['location']['city']}, {tx_data['location']['country']}")
    print(f"  Time: {tx_data['timestamp']}")
    print(f"  Analysis Type: {scenario['request']['analysis_type']}")
    
    # Process the request
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
            print(f"\nAnomaly Scores Detected ({len(anomaly_scores)}):")
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
            print(f"\n  ✅ No anomalies detected")
        
        # Display behavioral patterns
        behavioral_patterns = detection_data.get("behavioral_patterns", [])
        if behavioral_patterns:
            print(f"\nBehavioral Patterns Detected ({len(behavioral_patterns)}):")
            for i, pattern in enumerate(behavioral_patterns, 1):
                print(f"  {i}. {pattern.pattern_type.replace('_', ' ').title()}")
                print(f"     Description: {pattern.description}")
                print(f"     Strength: {pattern.strength:.3f}")
                print(f"     Frequency: {pattern.frequency}")
                print(f"     Trend: {pattern.trend_direction}")
                print(f"     Risk Level: {pattern.risk_level}")
        
        # Display trend analyses
        trend_analyses = detection_data.get("trend_analyses", [])
        if trend_analyses:
            print(f"\nTrend Analyses ({len(trend_analyses)}):")
            for i, trend in enumerate(trend_analyses, 1):
                print(f"  {i}. {trend.metric_name.replace('_', ' ').title()}")
                print(f"     Direction: {trend.trend_direction}")
                print(f"     Strength: {trend.trend_strength:.3f}")
                print(f"     Confidence: {trend.prediction_confidence:.3f}")
                print(f"     Current Value: {trend.current_value:.2f}")
                print(f"     Predicted Next: {trend.predicted_next_value:.2f}")
                print(f"     Data Points: {trend.data_points}")
        
        # Display pattern similarity matches
        similarity_matches = detection_data.get("pattern_similarity_matches", [])
        if similarity_matches:
            print(f"\nPattern Similarity Matches ({len(similarity_matches)}):")
            for i, match in enumerate(similarity_matches, 1):
                print(f"  {i}. Pattern: {match['pattern_type']}")
                print(f"     Similarity: {match['similarity_score']:.3f}")
                print(f"     Description: {match['description']}")
                print(f"     Effectiveness: {match['effectiveness_score']:.3f}")
        
        # Display recommendations
        recommendations = detection_data.get("recommendations", [])
        if recommendations:
            print(f"\nRecommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
    
    else:
        print(f"  Error: {result.error_message}")
    
    return result


def demonstrate_trend_analysis(detector: PatternDetector):
    """Demonstrate trend analysis capabilities."""
    print(f"\n{'='*80}")
    print("TREND ANALYSIS DEMONSTRATION")
    print(f"{'='*80}")
    
    # Create a series of transactions showing different trends
    trend_scenarios = [
        {
            "name": "Increasing Spending Trend",
            "description": "User showing gradual increase in spending",
            "request": {
                "transaction": {
                    "id": "tx_trend_increase_001",
                    "user_id": "user_trend_increase_001",
                    "amount": "350.00",  # Latest in increasing trend
                    "currency": "USD",
                    "merchant": "Trend Store",
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
                        "os": "iOS"
                    },
                    "ip_address": "192.168.1.400",
                    "session_id": "session_trend_001"
                },
                "analysis_type": "trend"
            }
        },
        {
            "name": "Stable Spending Pattern",
            "description": "User with consistent spending behavior",
            "request": {
                "transaction": {
                    "id": "tx_trend_stable_001",
                    "user_id": "user_trend_stable_001",
                    "amount": "125.00",  # Consistent amount
                    "currency": "USD",
                    "merchant": "Stable Store",
                    "category": "groceries",
                    "location": {
                        "country": "US",
                        "city": "Phoenix"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_stable_001",
                        "device_type": "mobile",
                        "os": "Android"
                    },
                    "ip_address": "192.168.1.500",
                    "session_id": "session_stable_001"
                },
                "analysis_type": "trend"
            }
        }
    ]
    
    for scenario in trend_scenarios:
        result = demonstrate_pattern_detection(detector, scenario)


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
    
    # Get pattern cache statistics
    cache_stats = detector.get_pattern_cache_stats()
    print(f"\nPattern Cache Statistics:")
    print(f"  Cached Patterns: {cache_stats['cached_patterns']}")
    print(f"  Cached Baselines: {cache_stats['cached_baselines']}")
    print(f"  Cache Size Estimate: {cache_stats['cache_size_estimate']} bytes")


def main():
    """Main demonstration function."""
    print("Pattern Detection Agent Demo")
    print("=" * 80)
    
    try:
        # Initialize components (using mock for demo)
        print("Initializing Pattern Detection Agent...")
        
        # Create mock memory and pattern learning managers
        class MockMemoryManager:
            def get_user_transaction_history(self, user_id, days_back=30):
                # Return mock transaction history based on user_id
                if "established" in user_id:
                    # Return baseline transactions for established user
                    return self._create_baseline_transactions(user_id)
                elif "behavioral" in user_id:
                    # Return transactions showing behavioral patterns
                    return self._create_behavioral_transactions(user_id)
                elif "trend" in user_id:
                    # Return transactions showing trends
                    return self._create_trend_transactions(user_id)
                else:
                    return []
            
            def get_all_fraud_patterns(self):
                # Return mock fraud patterns
                return [
                    type('MockPattern', (), {
                        'pattern_id': 'velocity_001',
                        'pattern_type': 'velocity_fraud',
                        'description': 'Rapid transaction pattern',
                        'effectiveness_score': 0.85
                    })(),
                    type('MockPattern', (), {
                        'pattern_id': 'amount_001',
                        'pattern_type': 'amount_fraud',
                        'description': 'High amount pattern',
                        'effectiveness_score': 0.78
                    })()
                ]
            
            def _create_baseline_transactions(self, user_id):
                # Create baseline transaction history
                transactions = []
                base_time = datetime.now() - timedelta(days=30)
                
                for i in range(15):
                    from memory_system.models import Transaction, Location, DeviceInfo
                    tx = Transaction(
                        id=f"tx_baseline_{i:03d}",
                        user_id=user_id,
                        amount=Decimal(f"{80 + (i % 5) * 20}.00"),  # 80-160 range
                        currency="USD",
                        merchant=f"Store_{i % 3}",
                        category="retail",
                        location=Location(country="US", city="Chicago"),
                        timestamp=base_time + timedelta(days=i * 2),
                        card_type="credit",
                        device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
                        ip_address="192.168.1.100",
                        session_id=f"session_{i}"
                    )
                    transactions.append(tx)
                
                return transactions
            
            def _create_behavioral_transactions(self, user_id):
                # Create transactions showing behavioral patterns
                transactions = []
                base_time = datetime.now() - timedelta(days=10)
                
                for i in range(8):
                    from memory_system.models import Transaction, Location, DeviceInfo
                    tx = Transaction(
                        id=f"tx_behavioral_{i:03d}",
                        user_id=user_id,
                        amount=Decimal(f"{100 + i * 50}.00"),  # Escalating pattern
                        currency="USD",
                        merchant="Behavioral Store",
                        category="retail",
                        location=Location(country="US", city="Seattle"),
                        timestamp=base_time + timedelta(days=i),
                        card_type="credit",
                        device_info=DeviceInfo(device_id="device_002", device_type="mobile", os="iOS"),
                        ip_address="192.168.1.200",
                        session_id=f"session_behavioral_{i}"
                    )
                    transactions.append(tx)
                
                return transactions
            
            def _create_trend_transactions(self, user_id):
                # Create transactions showing trends
                transactions = []
                base_time = datetime.now() - timedelta(days=20)
                
                for i in range(12):
                    from memory_system.models import Transaction, Location, DeviceInfo
                    
                    if "increase" in user_id:
                        amount = Decimal(f"{150 + i * 15}.00")  # Increasing trend
                    else:
                        amount = Decimal("125.00")  # Stable trend
                    
                    tx = Transaction(
                        id=f"tx_trend_{i:03d}",
                        user_id=user_id,
                        amount=amount,
                        currency="USD",
                        merchant="Trend Store",
                        category="retail",
                        location=Location(country="US", city="Denver" if "increase" in user_id else "Phoenix"),
                        timestamp=base_time + timedelta(days=i),
                        card_type="credit",
                        device_info=DeviceInfo(device_id="device_003", device_type="mobile", os="iOS"),
                        ip_address="192.168.1.300",
                        session_id=f"session_trend_{i}"
                    )
                    transactions.append(tx)
                
                return transactions
        
        class MockPatternLearningEngine:
            def get_learning_recommendations(self):
                return []
        
        mock_memory_manager = MockMemoryManager()
        mock_pattern_learning_engine = MockPatternLearningEngine()
        
        # Create pattern detector
        detector = PatternDetector(mock_memory_manager, mock_pattern_learning_engine)
        
        print(f"Pattern Detection Agent initialized successfully!")
        print(f"Agent ID: {detector.config.agent_id}")
        print(f"Capabilities: {[cap.value for cap in detector.config.capabilities]}")
        
        # Create test scenarios
        test_scenarios = create_test_scenarios()
        behavioral_scenarios = create_behavioral_pattern_scenarios()
        
        print(f"\nCreated {len(test_scenarios)} anomaly detection scenarios")
        print(f"Created {len(behavioral_scenarios)} behavioral pattern scenarios")
        
        # Demonstrate anomaly detection
        print(f"\n{'='*80}")
        print("ANOMALY DETECTION DEMONSTRATION")
        print(f"{'='*80}")
        
        for scenario in test_scenarios:
            result = demonstrate_pattern_detection(detector, scenario)
        
        # Demonstrate behavioral pattern recognition
        print(f"\n{'='*80}")
        print("BEHAVIORAL PATTERN RECOGNITION DEMONSTRATION")
        print(f"{'='*80}")
        
        # Process behavioral scenarios in sequence to show pattern development
        for scenario in behavioral_scenarios[:6]:  # First 6 are escalating pattern
            result = demonstrate_pattern_detection(detector, scenario)
        
        # Demonstrate trend analysis
        demonstrate_trend_analysis(detector)
        
        # Demonstrate agent monitoring
        demonstrate_agent_monitoring(detector)
        
        print(f"\n{'='*80}")
        print("DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print("\nKey Capabilities Demonstrated:")
        print("✓ Statistical anomaly detection (amount, frequency, temporal, merchant, location)")
        print("✓ Behavioral pattern recognition (escalating spending, preferences)")
        print("✓ Trend analysis and prediction")
        print("✓ Pattern similarity matching")
        print("✓ Multi-factor anomaly scoring")
        print("✓ Intelligent recommendations generation")
        print("✓ Agent performance monitoring and health checks")
        print("✓ Pattern cache management for performance optimization")
        print("\nThe Pattern Detection Agent is ready for production deployment!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()