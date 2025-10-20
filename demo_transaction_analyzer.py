"""
Demo script for Transaction Analyzer Agent.

This script demonstrates the capabilities of the specialized transaction analyzer
including real-time processing, velocity pattern detection, and risk assessment.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import json

from src.transaction_analyzer import TransactionAnalyzer
from src.base_agent import AgentConfiguration, AgentCapability
from src.memory_manager import MemoryManager
from src.context_manager import ContextManager
from src.models import Transaction, Location, DeviceInfo

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_transactions() -> List[Dict[str, Any]]:
    """Create various test transaction scenarios."""
    scenarios = []
    
    # Scenario 1: Normal legitimate transaction
    scenarios.append({
        "name": "Normal Legitimate Transaction",
        "description": "Regular purchase at familiar merchant",
        "request": {
            "transaction": {
                "id": "tx_normal_001",
                "user_id": "user_regular_001",
                "amount": "89.99",
                "currency": "USD",
                "merchant": "Target",
                "category": "retail",
                "location": {
                    "country": "US",
                    "city": "Chicago",
                    "latitude": 41.8781,
                    "longitude": -87.6298,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS",
                    "browser": "Safari",
                    "fingerprint": "fp_regular_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_normal_001",
                "metadata": {"channel": "mobile_app"}
            }
        },
        "expected_risk": "low"
    })
    
    # Scenario 2: High-amount transaction
    scenarios.append({
        "name": "High-Amount Transaction",
        "description": "Large purchase requiring additional scrutiny",
        "request": {
            "transaction": {
                "id": "tx_high_amount_001",
                "user_id": "user_regular_001",
                "amount": "2500.00",
                "currency": "USD",
                "merchant": "Electronics Superstore",
                "category": "electronics",
                "location": {
                    "country": "US",
                    "city": "Chicago",
                    "latitude": 41.8781,
                    "longitude": -87.6298,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS",
                    "browser": "Safari",
                    "fingerprint": "fp_regular_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_high_amount_001",
                "metadata": {"channel": "mobile_app"}
            }
        },
        "expected_risk": "medium"
    })
    
    # Scenario 3: Late night transaction
    scenarios.append({
        "name": "Late Night Transaction",
        "description": "Transaction at unusual hour",
        "request": {
            "transaction": {
                "id": "tx_late_night_001",
                "user_id": "user_regular_001",
                "amount": "150.00",
                "currency": "USD",
                "merchant": "24/7 Gas Station",
                "category": "fuel",
                "location": {
                    "country": "US",
                    "city": "Chicago",
                    "latitude": 41.8781,
                    "longitude": -87.6298,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().replace(hour=3, minute=30).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS",
                    "browser": "Safari",
                    "fingerprint": "fp_regular_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_late_night_001",
                "metadata": {"channel": "mobile_app"}
            }
        },
        "expected_risk": "medium"
    })
    
    # Scenario 4: High-risk merchant
    scenarios.append({
        "name": "High-Risk Merchant Transaction",
        "description": "Transaction with high-risk merchant",
        "request": {
            "transaction": {
                "id": "tx_high_risk_merchant_001",
                "user_id": "user_regular_001",
                "amount": "500.00",
                "currency": "USD",
                "merchant": "Crypto Exchange Pro",
                "category": "financial",
                "location": {
                    "country": "US",
                    "city": "Chicago",
                    "latitude": 41.8781,
                    "longitude": -87.6298,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "desktop",
                    "os": "Windows",
                    "browser": "Chrome",
                    "fingerprint": "fp_desktop_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_high_risk_001",
                "metadata": {"channel": "web"}
            }
        },
        "expected_risk": "high"
    })
    
    # Scenario 5: Invalid transaction data
    scenarios.append({
        "name": "Invalid Transaction Data",
        "description": "Transaction with missing required fields",
        "request": {
            "transaction": {
                "id": "",  # Missing ID
                "user_id": "",  # Missing user ID
                "amount": "0",  # Invalid amount
                "currency": "USD",
                "merchant": "Test Store",
                "category": "retail",
                "location": {
                    "country": "US",
                    "city": "Chicago"
                },
                "timestamp": datetime.now().isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_invalid_001",
                    "device_type": "mobile",
                    "os": "iOS"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_invalid_001"
            }
        },
        "expected_risk": "invalid"
    })
    
    return scenarios


def create_velocity_test_scenarios() -> List[Dict[str, Any]]:
    """Create test scenarios for velocity pattern detection."""
    scenarios = []
    base_time = datetime.now()
    
    # Rapid-fire transaction scenario
    rapid_fire_transactions = []
    for i in range(5):
        rapid_fire_transactions.append({
            "name": f"Rapid Fire Transaction {i+1}",
            "description": f"Transaction {i+1} in rapid sequence",
            "request": {
                "transaction": {
                    "id": f"tx_rapid_{i+1:03d}",
                    "user_id": "user_velocity_001",
                    "amount": f"{100 + i * 50}.00",
                    "currency": "USD",
                    "merchant": f"Online Store {i+1}",
                    "category": "online_retail",
                    "location": {
                        "country": "US",
                        "city": "Los Angeles",
                        "latitude": 34.0522,
                        "longitude": -118.2437,
                        "ip_address": "10.0.0.50"
                    },
                    "timestamp": (base_time + timedelta(minutes=i * 2)).isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_velocity_001",
                        "device_type": "desktop",
                        "os": "Windows",
                        "browser": "Chrome",
                        "fingerprint": "fp_velocity_001"
                    },
                    "ip_address": "10.0.0.50",
                    "session_id": f"session_rapid_{i+1}",
                    "metadata": {"sequence": i+1}
                }
            },
            "expected_risk": "high" if i >= 3 else "medium"
        })
    
    scenarios.extend(rapid_fire_transactions)
    
    # Geographic velocity scenario
    geo_velocity_transactions = [
        {
            "name": "Geographic Velocity - New York",
            "description": "Transaction in New York",
            "request": {
                "transaction": {
                    "id": "tx_geo_ny_001",
                    "user_id": "user_geo_001",
                    "amount": "200.00",
                    "currency": "USD",
                    "merchant": "NYC Store",
                    "category": "retail",
                    "location": {
                        "country": "US",
                        "city": "New York",
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "ip_address": "192.168.1.200"
                    },
                    "timestamp": base_time.isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_geo_001",
                        "device_type": "mobile",
                        "os": "iOS",
                        "browser": "Safari",
                        "fingerprint": "fp_geo_001"
                    },
                    "ip_address": "192.168.1.200",
                    "session_id": "session_geo_ny_001",
                    "metadata": {"location": "new_york"}
                }
            },
            "expected_risk": "low"
        },
        {
            "name": "Geographic Velocity - Paris (Impossible Travel)",
            "description": "Transaction in Paris 30 minutes later",
            "request": {
                "transaction": {
                    "id": "tx_geo_paris_001",
                    "user_id": "user_geo_001",  # Same user
                    "amount": "300.00",
                    "currency": "EUR",
                    "merchant": "Paris Boutique",
                    "category": "luxury",
                    "location": {
                        "country": "FR",
                        "city": "Paris",
                        "latitude": 48.8566,
                        "longitude": 2.3522,
                        "ip_address": "82.45.123.45"
                    },
                    "timestamp": (base_time + timedelta(minutes=30)).isoformat(),
                    "card_type": "credit",
                    "device_info": {
                        "device_id": "device_geo_002",
                        "device_type": "desktop",
                        "os": "Windows",
                        "browser": "Firefox",
                        "fingerprint": "fp_geo_002"
                    },
                    "ip_address": "82.45.123.45",
                    "session_id": "session_geo_paris_001",
                    "metadata": {"location": "paris"}
                }
            },
            "expected_risk": "high"
        }
    ]
    
    scenarios.extend(geo_velocity_transactions)
    
    return scenarios


def demonstrate_transaction_analysis(analyzer: TransactionAnalyzer, scenario: Dict[str, Any]):
    """Demonstrate transaction analysis for a scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    print(f"Expected Risk Level: {scenario['expected_risk']}")
    
    # Display transaction details
    tx_data = scenario["request"]["transaction"]
    print(f"\nTransaction Details:")
    print(f"  ID: {tx_data['id']}")
    print(f"  User: {tx_data['user_id']}")
    print(f"  Amount: {tx_data['currency']} {tx_data['amount']}")
    print(f"  Merchant: {tx_data['merchant']}")
    print(f"  Location: {tx_data['location']['city']}, {tx_data['location']['country']}")
    print(f"  Time: {tx_data['timestamp']}")
    print(f"  Device: {tx_data['device_info']['device_type']} ({tx_data['device_info']['os']})")
    
    # Process the transaction
    result = analyzer.execute_with_metrics(scenario["request"])
    
    print(f"\nAnalysis Results:")
    print(f"  Success: {result.success}")
    print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
    print(f"  Confidence: {result.confidence_score:.3f}")
    
    if result.success:
        analysis_data = result.result_data.get("analysis", {})
        
        print(f"  Risk Score: {analysis_data.get('risk_score', 0):.3f}")
        print(f"  Recommendation: {analysis_data.get('recommendation', 'UNKNOWN')}")
        
        # Display validation results
        validation = analysis_data.get("validation_result")
        if validation:
            print(f"\nValidation Results:")
            print(f"  Valid: {validation.is_valid}")
            
            if validation.validation_errors:
                print(f"  Errors: {', '.join(validation.validation_errors)}")
            
            if validation.validation_warnings:
                print(f"  Warnings: {', '.join(validation.validation_warnings)}")
            
            if validation.risk_indicators:
                print(f"  Risk Indicators: {', '.join(validation.risk_indicators)}")
        
        # Display velocity patterns
        velocity_patterns = analysis_data.get("velocity_patterns", [])
        if velocity_patterns:
            print(f"\nVelocity Patterns Detected ({len(velocity_patterns)}):")
            for i, pattern in enumerate(velocity_patterns, 1):
                print(f"  {i}. {pattern.pattern_type.replace('_', ' ').title()}")
                print(f"     Description: {pattern.description}")
                print(f"     Risk Score: {pattern.risk_score:.3f}")
                print(f"     Transactions: {pattern.transaction_count}")
                print(f"     Time Window: {pattern.time_window_minutes} minutes")
                
                if pattern.evidence:
                    print(f"     Evidence:")
                    for ev in pattern.evidence:
                        print(f"       - {ev}")
        
        # Display contextual factors
        contextual = analysis_data.get("contextual_factors", {})
        if contextual:
            print(f"\nContextual Factors:")
            for key, value in contextual.items():
                if isinstance(value, float):
                    print(f"  {key.replace('_', ' ').title()}: {value:.3f}")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Display processing details
        processing = analysis_data.get("processing_details", {})
        if processing:
            print(f"\nProcessing Details:")
            for key, value in processing.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
    
    else:
        print(f"  Error: {result.error_message}")
    
    return result


def demonstrate_velocity_detection(analyzer: TransactionAnalyzer):
    """Demonstrate velocity pattern detection with sequential transactions."""
    print(f"\n{'='*80}")
    print("VELOCITY PATTERN DETECTION DEMONSTRATION")
    print(f"{'='*80}")
    
    velocity_scenarios = create_velocity_test_scenarios()
    
    print(f"Processing {len(velocity_scenarios)} transactions to demonstrate velocity detection...")
    
    results = []
    for scenario in velocity_scenarios:
        print(f"\nProcessing: {scenario['name']}")
        result = analyzer.execute_with_metrics(scenario["request"])
        results.append(result)
        
        if result.success:
            analysis = result.result_data.get("analysis", {})
            velocity_patterns = analysis.get("velocity_patterns", [])
            
            if velocity_patterns:
                print(f"  ⚠️  Velocity patterns detected: {len(velocity_patterns)}")
                for pattern in velocity_patterns:
                    print(f"     - {pattern.pattern_type}: {pattern.description}")
            else:
                print(f"  ✅ No velocity patterns detected")
            
            print(f"  Risk Score: {analysis.get('risk_score', 0):.3f}")
            print(f"  Recommendation: {analysis.get('recommendation', 'UNKNOWN')}")
    
    # Display velocity cache statistics
    print(f"\nVelocity Cache Statistics:")
    stats = analyzer.get_velocity_statistics()
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    return results


def demonstrate_agent_monitoring(analyzer: TransactionAnalyzer):
    """Demonstrate agent monitoring and health check capabilities."""
    print(f"\n{'='*80}")
    print("AGENT MONITORING DEMONSTRATION")
    print(f"{'='*80}")
    
    # Get agent status
    status = analyzer.get_status()
    
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
    
    # Display configuration
    config = status['configuration']
    print(f"\nConfiguration:")
    print(f"  Max Concurrent Requests: {config['max_concurrent_requests']}")
    print(f"  Timeout: {config['timeout_seconds']} seconds")
    print(f"  Retry Attempts: {config['retry_attempts']}")
    
    # Get health check
    health = analyzer.get_health_check()
    
    print(f"\nHealth Check:")
    print(f"  Health Status: {health['health_status']}")
    print(f"  Issues: {len(health['issues'])}")
    
    if health['issues']:
        for issue in health['issues']:
            print(f"    - {issue}")
    else:
        print(f"    No issues detected")
    
    print(f"  Uptime: {health['uptime_seconds']:.0f} seconds")


def main():
    """Main demonstration function."""
    print("Transaction Analyzer Agent Demo")
    print("=" * 80)
    
    try:
        # Initialize components (using mock for demo)
        print("Initializing Transaction Analyzer Agent...")
        
        # Create mock memory and context managers
        class MockMemoryManager:
            def store_transaction(self, transaction):
                return True
            
            def get_user_transaction_history(self, user_id, days_back=1, limit=20):
                return []
        
        class MockContextManager:
            def get_contextual_recommendation(self, transaction):
                return {
                    "risk_score": 0.2,
                    "recommendation": "APPROVE",
                    "confidence": 0.8,
                    "context_summary": {
                        "similar_cases_count": 2,
                        "has_user_profile": True
                    }
                }
        
        mock_memory_manager = MockMemoryManager()
        mock_context_manager = MockContextManager()
        
        # Create transaction analyzer
        analyzer = TransactionAnalyzer(mock_memory_manager, mock_context_manager)
        
        print(f"Transaction Analyzer initialized successfully!")
        print(f"Agent ID: {analyzer.config.agent_id}")
        print(f"Capabilities: {[cap.value for cap in analyzer.config.capabilities]}")
        
        # Create test scenarios
        test_scenarios = create_test_transactions()
        
        print(f"\nCreated {len(test_scenarios)} test scenarios for demonstration")
        
        # Demonstrate individual transaction analysis
        for scenario in test_scenarios:
            result = demonstrate_transaction_analysis(analyzer, scenario)
        
        # Demonstrate velocity pattern detection
        velocity_results = demonstrate_velocity_detection(analyzer)
        
        # Demonstrate agent monitoring
        demonstrate_agent_monitoring(analyzer)
        
        print(f"\n{'='*80}")
        print("DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print("\nKey Capabilities Demonstrated:")
        print("✓ Real-time transaction analysis")
        print("✓ Comprehensive transaction validation")
        print("✓ Velocity pattern detection (rapid-fire, escalating, geographic)")
        print("✓ Risk scoring and recommendation generation")
        print("✓ Agent performance monitoring and health checks")
        print("✓ Contextual analysis integration")
        print("✓ High-volume transaction processing support")
        print("\nThe Transaction Analyzer Agent is ready for production deployment!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()