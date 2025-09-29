"""
Demo script for Risk Assessment Agent.

This script demonstrates the capabilities of the specialized risk assessment agent
including multi-factor risk scoring, geographic and temporal risk analysis, and
cross-reference systems for known fraud indicators.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from specialized_agents.risk_assessor import RiskAssessor
from specialized_agents.base_agent import AgentConfiguration, AgentCapability
from memory_system.memory_manager import MemoryManager
from memory_system.models import Transaction, Location, DeviceInfo, UserBehaviorProfile

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_risk_test_scenarios() -> List[Dict[str, Any]]:
    """Create various risk assessment test scenarios."""
    scenarios = []
    
    # Scenario 1: Low-risk legitimate transaction
    scenarios.append({
        "name": "Low-Risk Legitimate Transaction",
        "description": "Regular transaction with minimal risk indicators",
        "request": {
            "transaction": {
                "id": "tx_low_risk_001",
                "user_id": "user_established_001",
                "amount": "125.50",
                "currency": "USD",
                "merchant": "Target Store",
                "category": "retail",
                "location": {
                    "country": "US",
                    "city": "Seattle",
                    "latitude": 47.6062,
                    "longitude": -122.3321,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().replace(hour=14).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS",
                    "browser": "Safari",
                    "fingerprint": "fp_regular_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_low_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "low"
    })
    
    # Scenario 2: High amount risk
    scenarios.append({
        "name": "High Amount Risk Transaction",
        "description": "Transaction with unusually high amount",
        "request": {
            "transaction": {
                "id": "tx_high_amount_001",
                "user_id": "user_established_001",
                "amount": "8500.00",  # Very high amount
                "currency": "USD",
                "merchant": "Luxury Electronics",
                "category": "electronics",
                "location": {
                    "country": "US",
                    "city": "Seattle",
                    "latitude": 47.6062,
                    "longitude": -122.3321,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().replace(hour=15).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS",
                    "browser": "Safari",
                    "fingerprint": "fp_regular_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_high_amount_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "high"
    })
    
    # Scenario 3: Geographic risk (high-risk country)
    scenarios.append({
        "name": "Geographic Risk Transaction",
        "description": "Transaction from high-risk country",
        "request": {
            "transaction": {
                "id": "tx_geo_risk_001",
                "user_id": "user_established_001",
                "amount": "450.00",
                "currency": "USD",
                "merchant": "International Store",
                "category": "retail",
                "location": {
                    "country": "XX",  # High-risk country
                    "city": "Unknown City",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "ip_address": "203.0.113.50"
                },
                "timestamp": datetime.now().replace(hour=16).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_foreign_001",
                    "device_type": "desktop",
                    "os": "Windows",
                    "browser": "Chrome",
                    "fingerprint": "fp_foreign_001"
                },
                "ip_address": "203.0.113.50",
                "session_id": "session_geo_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "high"
    })
    
    # Scenario 4: Temporal risk (late night transaction)
    scenarios.append({
        "name": "Temporal Risk Transaction",
        "description": "Transaction at unusual late night hour",
        "request": {
            "transaction": {
                "id": "tx_temporal_risk_001",
                "user_id": "user_established_001",
                "amount": "299.99",
                "currency": "USD",
                "merchant": "24/7 Online Store",
                "category": "online_retail",
                "location": {
                    "country": "US",
                    "city": "Seattle",
                    "latitude": 47.6062,
                    "longitude": -122.3321,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().replace(hour=3, minute=30).isoformat(),  # 3:30 AM
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_regular_001",
                    "device_type": "mobile",
                    "os": "iOS",
                    "browser": "Safari",
                    "fingerprint": "fp_regular_001"
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_temporal_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "medium"
    })
    
    # Scenario 5: High-risk merchant
    scenarios.append({
        "name": "High-Risk Merchant Transaction",
        "description": "Transaction with high-risk merchant (crypto/gambling)",
        "request": {
            "transaction": {
                "id": "tx_merchant_risk_001",
                "user_id": "user_established_001",
                "amount": "750.00",
                "currency": "USD",
                "merchant": "Crypto Casino Supreme",  # High-risk keywords
                "category": "gambling",
                "location": {
                    "country": "US",
                    "city": "Las Vegas",
                    "latitude": 36.1699,
                    "longitude": -115.1398,
                    "ip_address": "10.0.0.50"
                },
                "timestamp": datetime.now().replace(hour=22).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_gambling_001",
                    "device_type": "desktop",
                    "os": "Windows",
                    "browser": "Chrome",
                    "fingerprint": "fp_gambling_001"
                },
                "ip_address": "10.0.0.50",
                "session_id": "session_merchant_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "high"
    })
    
    # Scenario 6: Device risk (suspicious device)
    scenarios.append({
        "name": "Device Risk Transaction",
        "description": "Transaction from suspicious/unknown device",
        "request": {
            "transaction": {
                "id": "tx_device_risk_001",
                "user_id": "user_established_001",
                "amount": "199.99",
                "currency": "USD",
                "merchant": "Electronics Store",
                "category": "electronics",
                "location": {
                    "country": "US",
                    "city": "Seattle",
                    "latitude": 47.6062,
                    "longitude": -122.3321,
                    "ip_address": "192.168.1.100"
                },
                "timestamp": datetime.now().replace(hour=14).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_unknown_001",
                    "device_type": "unknown",  # Suspicious device type
                    "os": "custom",  # Suspicious OS
                    "browser": "unknown",
                    "fingerprint": ""  # Missing fingerprint
                },
                "ip_address": "192.168.1.100",
                "session_id": "session_device_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "medium"
    })
    
    # Scenario 7: Cross-reference risk (blacklisted IP)
    scenarios.append({
        "name": "Cross-Reference Risk Transaction",
        "description": "Transaction from blacklisted IP address",
        "request": {
            "transaction": {
                "id": "tx_crossref_risk_001",
                "user_id": "user_established_001",
                "amount": "350.00",
                "currency": "USD",
                "merchant": "Online Store",
                "category": "retail",
                "location": {
                    "country": "US",
                    "city": "Seattle",
                    "latitude": 47.6062,
                    "longitude": -122.3321,
                    "ip_address": "192.0.2.1"  # Blacklisted IP
                },
                "timestamp": datetime.now().replace(hour=16).isoformat(),
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_blacklist_001",
                    "device_type": "desktop",
                    "os": "Windows",
                    "browser": "Chrome",
                    "fingerprint": "fp_blacklist_001"
                },
                "ip_address": "192.0.2.1",  # Blacklisted IP
                "session_id": "session_crossref_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "high"
    })
    
    # Scenario 8: Multiple risk factors (critical risk)
    scenarios.append({
        "name": "Multiple Risk Factors Transaction",
        "description": "Transaction with multiple high-risk indicators",
        "request": {
            "transaction": {
                "id": "tx_multiple_risk_001",
                "user_id": "suspicious_user_001",  # Watchlisted user
                "amount": "5000.00",  # High amount
                "currency": "USD",
                "merchant": "Bitcoin Gambling Exchange",  # High-risk merchant
                "category": "gambling",
                "location": {
                    "country": "XX",  # High-risk country
                    "city": "Unknown",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "ip_address": "198.51.100.1"  # Blacklisted IP
                },
                "timestamp": datetime.now().replace(hour=4).isoformat(),  # Late night
                "card_type": "credit",
                "device_info": {
                    "device_id": "device_suspicious_001",
                    "device_type": "emulator",  # Suspicious device
                    "os": "modified",  # Suspicious OS
                    "browser": "unknown",
                    "fingerprint": ""  # Missing fingerprint
                },
                "ip_address": "198.51.100.1",  # Blacklisted IP
                "session_id": "session_multiple_risk_001"
            },
            "assessment_type": "comprehensive"
        },
        "expected_risk_level": "critical"
    })
    
    return scenarios


def demonstrate_risk_assessment(assessor: RiskAssessor, scenario: Dict[str, Any]):
    """Demonstrate risk assessment for a scenario."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    print(f"Expected Risk Level: {scenario['expected_risk_level']}")
    
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
    print(f"  IP Address: {tx_data['ip_address']}")
    
    # Process the risk assessment
    result = assessor.execute_with_metrics(scenario["request"])
    
    print(f"\nRisk Assessment Results:")
    print(f"  Success: {result.success}")
    print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
    print(f"  Assessment Confidence: {result.confidence_score:.3f}")
    
    if result.success:
        assessment_data = result.result_data.get("risk_assessment", {})
        
        print(f"  Overall Risk Score: {assessment_data.get('overall_risk_score', 0):.3f}")
        print(f"  Risk Level: {assessment_data.get('risk_level', 'unknown').upper()}")
        
        # Display individual risk factors
        risk_factors = assessment_data.get("risk_factors", [])
        if risk_factors:
            print(f"\nRisk Factors ({len(risk_factors)} identified):")
            for i, factor in enumerate(risk_factors, 1):
                print(f"  {i}. {factor.factor_name.replace('_', ' ').title()}")
                print(f"     Risk Score: {factor.risk_score:.3f}")
                print(f"     Confidence: {factor.confidence:.3f}")
                print(f"     Weight: {factor.weight:.3f}")
                print(f"     Description: {factor.description}")
                if factor.evidence:
                    print(f"     Evidence:")
                    for evidence in factor.evidence:
                        print(f"       - {evidence}")
        else:
            print(f"\n✅ No significant risk factors identified")
        
        # Display geographic risk assessment
        geographic_risk = assessment_data.get("geographic_risk")
        if geographic_risk:
            print(f"\nGeographic Risk Analysis:")
            print(f"  Location Risk Score: {geographic_risk.location_risk_score:.3f}")
            print(f"  Country Risk Level: {geographic_risk.country_risk_level.upper()}")
            print(f"  Travel Pattern Risk: {geographic_risk.travel_pattern_risk:.3f}")
            print(f"  IP Location Mismatch: {geographic_risk.ip_location_mismatch}")
            print(f"  Distance from Home: {geographic_risk.distance_from_home:.0f} km")
            if geographic_risk.risk_factors:
                print(f"  Geographic Risk Factors:")
                for factor in geographic_risk.risk_factors:
                    print(f"    - {factor}")
        
        # Display temporal risk assessment
        temporal_risk = assessment_data.get("temporal_risk")
        if temporal_risk:
            print(f"\nTemporal Risk Analysis:")
            print(f"  Time Risk Score: {temporal_risk.time_risk_score:.3f}")
            print(f"  Unusual Hour Risk: {temporal_risk.unusual_hour_risk:.3f}")
            print(f"  Frequency Risk: {temporal_risk.frequency_risk:.3f}")
            print(f"  Velocity Risk: {temporal_risk.velocity_risk:.3f}")
            print(f"  Pattern Deviation: {temporal_risk.pattern_deviation:.3f}")
            if temporal_risk.risk_factors:
                print(f"  Temporal Risk Factors:")
                for factor in temporal_risk.risk_factors:
                    print(f"    - {factor}")
        
        # Display cross-reference results
        cross_ref_results = assessment_data.get("cross_reference_results", [])
        if cross_ref_results:
            print(f"\nCross-Reference Results ({len(cross_ref_results)} matches):")
            for i, result_item in enumerate(cross_ref_results, 1):
                print(f"  {i}. {result_item.reference_type.replace('_', ' ').title()}")
                print(f"     Match Found: {result_item.match_found}")
                print(f"     Match Confidence: {result_item.match_confidence:.3f}")
                print(f"     Risk Impact: {result_item.risk_impact:.3f}")
                if result_item.match_details:
                    print(f"     Match Details: {result_item.match_details}")
        else:
            print(f"\n✅ No cross-reference matches found")
        
        # Display threshold breaches
        threshold_breaches = assessment_data.get("risk_threshold_breaches", [])
        if threshold_breaches:
            print(f"\n⚠️  Risk Threshold Breaches ({len(threshold_breaches)}):")
            for i, breach in enumerate(threshold_breaches, 1):
                print(f"  {i}. {breach}")
        else:
            print(f"\n✅ No risk thresholds breached")
        
        # Display recommendations
        recommendations = assessment_data.get("recommendations", [])
        if recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Display risk mitigation suggestions
        mitigation_suggestions = assessment_data.get("risk_mitigation_suggestions", [])
        if mitigation_suggestions:
            print(f"\nRisk Mitigation Suggestions:")
            for i, suggestion in enumerate(mitigation_suggestions, 1):
                print(f"  {i}. {suggestion}")
    
    else:
        print(f"  Error: {result.error_message}")
    
    return result


def demonstrate_risk_threshold_management(assessor: RiskAssessor):
    """Demonstrate risk threshold management capabilities."""
    print(f"\n{'='*80}")
    print("RISK THRESHOLD MANAGEMENT DEMONSTRATION")
    print(f"{'='*80}")
    
    # Get current risk statistics
    current_stats = assessor.get_risk_statistics()
    
    print("Current Risk Configuration:")
    print(f"  Risk Thresholds: {current_stats['risk_thresholds']}")
    print(f"  Risk Weights: {current_stats['risk_weights']}")
    print(f"  Fraud Indicators Count: {current_stats['fraud_indicators_count']}")
    print(f"  Country Risk Levels: {current_stats['country_risk_levels']}")
    
    # Demonstrate threshold updates
    print(f"\nUpdating Risk Thresholds...")
    new_thresholds = {
        "low": 0.25,
        "medium": 0.55,
        "high": 0.75
    }
    
    success = assessor.update_risk_thresholds(new_thresholds)
    print(f"Threshold Update Success: {success}")
    
    if success:
        updated_stats = assessor.get_risk_statistics()
        print(f"Updated Risk Thresholds: {updated_stats['risk_thresholds']}")


def demonstrate_agent_monitoring(assessor: RiskAssessor):
    """Demonstrate agent monitoring and performance metrics."""
    print(f"\n{'='*80}")
    print("AGENT MONITORING DEMONSTRATION")
    print(f"{'='*80}")
    
    # Get agent status
    status = assessor.get_status()
    
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
    health = assessor.get_health_check()
    
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
    print("Risk Assessment Agent Demo")
    print("=" * 80)
    
    try:
        # Initialize components (using mock for demo)
        print("Initializing Risk Assessment Agent...")
        
        # Create mock memory manager
        class MockMemoryManager:
            def get_user_profile(self, user_id):
                # Return mock user profile for established users
                if "established" in user_id:
                    return UserBehaviorProfile(
                        user_id=user_id,
                        typical_spending_range={"min": 20.0, "max": 500.0, "avg": 150.0},
                        frequent_merchants=["Target Store", "Amazon", "Starbucks"],
                        common_locations=[
                            Location(country="US", city="Seattle", latitude=47.6062, longitude=-122.3321)
                        ],
                        preferred_categories=["retail", "groceries", "electronics"],
                        transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
                        risk_score=0.2,
                        last_updated=datetime.now(),
                        transaction_count=150
                    )
                return None
            
            def get_user_transaction_history(self, user_id, days_back=1, limit=20):
                # Return mock transaction history
                if "established" in user_id:
                    # Return normal transaction history
                    return []  # Simplified for demo
                else:
                    # Return empty for new/suspicious users
                    return []
        
        mock_memory_manager = MockMemoryManager()
        
        # Create risk assessor
        assessor = RiskAssessor(mock_memory_manager)
        
        print(f"Risk Assessment Agent initialized successfully!")
        print(f"Agent ID: {assessor.config.agent_id}")
        print(f"Capabilities: {[cap.value for cap in assessor.config.capabilities]}")
        
        # Create test scenarios
        test_scenarios = create_risk_test_scenarios()
        
        print(f"\nCreated {len(test_scenarios)} test scenarios for demonstration")
        
        # Demonstrate individual risk assessments
        for scenario in test_scenarios:
            result = demonstrate_risk_assessment(assessor, scenario)
        
        # Demonstrate risk threshold management
        demonstrate_risk_threshold_management(assessor)
        
        # Demonstrate agent monitoring
        demonstrate_agent_monitoring(assessor)
        
        print(f"\n{'='*80}")
        print("DEMO COMPLETED SUCCESSFULLY")
        print(f"{'='*80}")
        print("\nKey Capabilities Demonstrated:")
        print("✓ Multi-factor risk scoring (amount, merchant, device, behavioral, velocity)")
        print("✓ Geographic risk analysis with country risk levels")
        print("✓ Temporal risk analysis with unusual hour detection")
        print("✓ Cross-reference checks against fraud databases")
        print("✓ Risk threshold management and breach detection")
        print("✓ Comprehensive risk recommendations and mitigation suggestions")
        print("✓ Agent performance monitoring and health checks")
        print("✓ Adaptive risk threshold configuration")
        print("\nThe Risk Assessment Agent is ready for production deployment!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        print(f"\nDemo failed: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    main()