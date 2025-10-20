"""
Demo script for Fraud Database Integration

Demonstrates the fraud database capabilities including:
- Similarity search for known fraud cases
- Real-time fraud pattern matching
- Fraud case reporting and management
- Statistical analysis and pattern updates
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path for imports
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.tool_integrator import ToolIntegrator
from src.fraud_database import (
    FraudDatabaseTool, FraudCase, FraudType, FraudCaseStatus,
    create_fraud_database_tool
)


def create_sample_transactions():
    """Create sample transaction data for testing."""
    transactions = []
    
    # High-value transaction (likely to match patterns)
    transactions.append({
        "transaction_id": "tx_001",
        "amount": 2500.00,
        "currency": "USD",
        "merchant": "Luxury Electronics Store",
        "category": "electronics",
        "timestamp": datetime.now().isoformat(),
        "user_id": "user_001",
        "card_type": "credit",
        "location": {
            "country": "US",
            "city": "New York",
            "ip_address": "192.168.1.100"
        },
        "device_info": {
            "device_id": "device_001",
            "device_type": "mobile"
        }
    })
    
    # Normal transaction
    transactions.append({
        "transaction_id": "tx_002",
        "amount": 85.50,
        "currency": "USD",
        "merchant": "Local Coffee Shop",
        "category": "food",
        "timestamp": datetime.now().isoformat(),
        "user_id": "user_002",
        "card_type": "debit",
        "location": {
            "country": "US",
            "city": "San Francisco",
            "ip_address": "10.0.0.50"
        }
    })
    
    # Suspicious velocity pattern
    transactions.append({
        "transaction_id": "tx_003",
        "amount": 150.00,
        "currency": "USD",
        "merchant": "Online Gaming Store",
        "category": "gaming",
        "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
        "user_id": "user_003",
        "card_type": "credit",
        "location": {
            "country": "US",
            "city": "Austin",
            "ip_address": "172.16.0.25"
        }
    })
    
    # International transaction
    transactions.append({
        "transaction_id": "tx_004",
        "amount": 750.00,
        "currency": "EUR",
        "merchant": "European Fashion Boutique",
        "category": "clothing",
        "timestamp": datetime.now().isoformat(),
        "user_id": "user_004",
        "card_type": "credit",
        "location": {
            "country": "FR",
            "city": "Paris",
            "ip_address": "203.0.113.45"
        }
    })
    
    return transactions


def demo_similarity_search():
    """Demonstrate similarity search for known fraud cases."""
    print("=" * 60)
    print("FRAUD DATABASE DEMO - SIMILARITY SEARCH")
    print("=" * 60)
    
    # Create fraud database tool
    tool = create_fraud_database_tool(
        tool_id="demo_fraud_db",
        database_type="generic",
        api_key="demo_api_key"
    )
    
    transactions = create_sample_transactions()
    
    print(f"\nSearching for similar fraud cases for {len(transactions)} transactions...")
    
    for i, transaction in enumerate(transactions):
        print(f"\n--- Transaction {i+1}: {transaction['transaction_id']} ---")
        print(f"Amount: ${transaction['amount']:.2f} {transaction['currency']}")
        print(f"Merchant: {transaction['merchant']}")
        print(f"Location: {transaction['location']['city']}, {transaction['location']['country']}")
        
        # Search for similar cases
        similar_cases = tool.search_similar_cases(
            transaction_data=transaction,
            user_data={"user_id": transaction["user_id"]},
            fraud_types=[FraudType.CARD_NOT_PRESENT, FraudType.VELOCITY_FRAUD]
        )
        
        if similar_cases:
            print(f"Found {len(similar_cases)} similar fraud cases:")
            for case in similar_cases:
                print(f"  • Case {case.case_id}:")
                print(f"    Similarity: {case.similarity_score:.2f}")
                print(f"    Type: {case.fraud_type.value}")
                print(f"    Status: {case.status.value}")
                print(f"    Confidence: {case.confidence_score:.2f}")
                
                if case.match_reasons:
                    print(f"    Reasons: {', '.join(case.match_reasons[:2])}")
                
                # Show similarity metrics
                if case.similarity_metrics:
                    metrics_str = ", ".join([
                        f"{metric.value}: {score:.2f}" 
                        for metric, score in list(case.similarity_metrics.items())[:2]
                    ])
                    print(f"    Metrics: {metrics_str}")
        else:
            print("No similar fraud cases found")


def demo_pattern_matching():
    """Demonstrate fraud pattern matching."""
    print("\n" + "=" * 60)
    print("FRAUD DATABASE DEMO - PATTERN MATCHING")
    print("=" * 60)
    
    tool = create_fraud_database_tool(
        tool_id="demo_pattern_db",
        database_type="generic",
        api_key="demo_api_key"
    )
    
    transactions = create_sample_transactions()
    
    print(f"\nChecking {len(transactions)} transactions against fraud patterns...")
    
    for i, transaction in enumerate(transactions):
        print(f"\n--- Transaction {i+1}: {transaction['transaction_id']} ---")
        print(f"Amount: ${transaction['amount']:.2f}")
        print(f"Time: {datetime.fromisoformat(transaction['timestamp']).strftime('%H:%M:%S')}")
        
        # Check fraud patterns
        pattern_matches = tool.check_fraud_patterns(transaction)
        
        if pattern_matches:
            print(f"⚠️  Matched {len(pattern_matches)} fraud patterns:")
            for match in pattern_matches:
                print(f"  • Pattern: {match.pattern_name}")
                print(f"    Score: {match.match_score:.2f}")
                print(f"    Type: {match.fraud_type.value}")
                print(f"    Action: {match.recommended_action}")
                print(f"    Confidence: {match.confidence_level}")
                
                if match.matched_criteria:
                    print(f"    Criteria: {', '.join(match.matched_criteria)}")
                
                if match.risk_indicators:
                    print(f"    Risks: {', '.join(match.risk_indicators)}")
        else:
            print("✅ No fraud patterns matched")


def demo_case_reporting():
    """Demonstrate fraud case reporting and management."""
    print("\n" + "=" * 60)
    print("FRAUD DATABASE DEMO - CASE REPORTING")
    print("=" * 60)
    
    tool = create_fraud_database_tool(
        tool_id="demo_case_db",
        database_type="generic",
        api_key="demo_api_key"
    )
    
    # Create sample fraud cases to report
    fraud_cases = [
        FraudCase(
            case_id="case_001",
            fraud_type=FraudType.CARD_NOT_PRESENT,
            status=FraudCaseStatus.CONFIRMED,
            transaction_data={
                "transaction_id": "tx_fraud_001",
                "amount": 3500.00,
                "merchant": "Suspicious Online Store",
                "timestamp": datetime.now().isoformat()
            },
            user_data={
                "user_id": "user_fraud_001",
                "account_age_days": 15,
                "previous_fraud_count": 0
            },
            detection_method="pattern_matching",
            confidence_score=0.95,
            financial_impact=3500.00,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            tags=["high_amount", "new_account", "suspicious_merchant"],
            investigation_notes="High-value transaction from new account to suspicious merchant"
        ),
        FraudCase(
            case_id="case_002",
            fraud_type=FraudType.VELOCITY_FRAUD,
            status=FraudCaseStatus.SUSPECTED,
            transaction_data={
                "transaction_id": "tx_fraud_002",
                "amount": 200.00,
                "merchant": "Gaming Platform",
                "timestamp": datetime.now().isoformat()
            },
            user_data={
                "user_id": "user_fraud_002",
                "account_age_days": 180
            },
            detection_method="velocity_analysis",
            confidence_score=0.78,
            financial_impact=200.00,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            tags=["velocity", "gaming"],
            investigation_notes="Multiple rapid transactions detected"
        )
    ]
    
    print(f"\nReporting {len(fraud_cases)} fraud cases...")
    
    for case in fraud_cases:
        print(f"\n--- Reporting Case: {case.case_id} ---")
        print(f"Type: {case.fraud_type.value}")
        print(f"Status: {case.status.value}")
        print(f"Amount: ${case.financial_impact:.2f}")
        print(f"Confidence: {case.confidence_score:.2f}")
        print(f"Tags: {', '.join(case.tags)}")
        
        # Report the case
        success = tool.report_fraud_case(case)
        
        if success:
            print("✅ Case reported successfully")
            
            # Update case status (simulate investigation progress)
            if case.status == FraudCaseStatus.SUSPECTED:
                print("   Updating case status to 'investigating'...")
                update_success = tool.update_case_status(
                    case.case_id,
                    FraudCaseStatus.INVESTIGATING,
                    "Investigation started by fraud team"
                )
                if update_success:
                    print("✅ Case status updated successfully")
                else:
                    print("❌ Failed to update case status")
        else:
            print("❌ Failed to report case")


def demo_fraud_statistics():
    """Demonstrate fraud statistics and analytics."""
    print("\n" + "=" * 60)
    print("FRAUD DATABASE DEMO - STATISTICS & ANALYTICS")
    print("=" * 60)
    
    tool = create_fraud_database_tool(
        tool_id="demo_stats_db",
        database_type="generic",
        api_key="demo_api_key"
    )
    
    # Get fraud statistics for different time periods
    time_periods = [
        ("Last 7 days", datetime.now() - timedelta(days=7), datetime.now()),
        ("Last 30 days", datetime.now() - timedelta(days=30), datetime.now()),
        ("Last 90 days", datetime.now() - timedelta(days=90), datetime.now())
    ]
    
    print("\nFraud Statistics Analysis:")
    
    for period_name, start_date, end_date in time_periods:
        print(f"\n--- {period_name} ---")
        
        # Get general statistics
        stats = tool.get_fraud_statistics(start_date, end_date)
        
        if stats:
            print(f"Total Cases: {stats.get('total_cases', 0)}")
            print(f"Confirmed Fraud: {stats.get('confirmed_fraud', 0)}")
            print(f"False Positives: {stats.get('false_positives', 0)}")
            print(f"Detection Accuracy: {stats.get('detection_accuracy', 0):.1%}")
            print(f"Average Impact: ${stats.get('average_financial_impact', 0):.2f}")
            
            # Show fraud type breakdown
            if 'fraud_types' in stats:
                print("Fraud Types:")
                for fraud_type, count in stats['fraud_types'].items():
                    print(f"  • {fraud_type.replace('_', ' ').title()}: {count}")
        else:
            print("No statistics available for this period")
    
    # Get statistics for specific fraud types
    print(f"\n--- Fraud Type Analysis ---")
    specific_types = [FraudType.CARD_NOT_PRESENT, FraudType.VELOCITY_FRAUD]
    
    for fraud_type in specific_types:
        stats = tool.get_fraud_statistics(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            fraud_types=[fraud_type]
        )
        
        if stats:
            print(f"{fraud_type.value.replace('_', ' ').title()}:")
            print(f"  Cases: {stats.get('total_cases', 0)}")
            print(f"  Accuracy: {stats.get('detection_accuracy', 0):.1%}")


def demo_pattern_updates():
    """Demonstrate fraud pattern updates and management."""
    print("\n" + "=" * 60)
    print("FRAUD DATABASE DEMO - PATTERN UPDATES")
    print("=" * 60)
    
    tool = create_fraud_database_tool(
        tool_id="demo_pattern_update_db",
        database_type="generic",
        api_key="demo_api_key"
    )
    
    print("\nRetrieving latest fraud patterns...")
    
    # Get all latest patterns
    all_patterns = tool.get_latest_patterns()
    
    if all_patterns:
        print(f"Found {len(all_patterns)} active fraud patterns:")
        
        for pattern in all_patterns:
            print(f"\n• Pattern: {pattern.pattern_name}")
            print(f"  ID: {pattern.pattern_id}")
            print(f"  Type: {pattern.fraud_type.value}")
            print(f"  Effectiveness: {pattern.effectiveness_score:.2%}")
            print(f"  False Positive Rate: {pattern.false_positive_rate:.2%}")
            print(f"  Cases Detected: {pattern.case_count}")
            print(f"  Last Updated: {pattern.last_updated.strftime('%Y-%m-%d %H:%M')}")
            
            if pattern.detection_criteria:
                print(f"  Criteria: {', '.join(pattern.detection_criteria[:2])}")
            
            if pattern.pattern_rules:
                rules_str = ", ".join([
                    f"{k}: {v}" for k, v in list(pattern.pattern_rules.items())[:2]
                ])
                print(f"  Rules: {rules_str}")
    else:
        print("No fraud patterns available")
    
    # Get patterns updated in the last week
    print(f"\n--- Recent Pattern Updates ---")
    last_week = datetime.now() - timedelta(days=7)
    recent_patterns = tool.get_latest_patterns(last_update=last_week)
    
    if recent_patterns:
        print(f"Found {len(recent_patterns)} patterns updated in the last week:")
        for pattern in recent_patterns:
            print(f"  • {pattern.pattern_name} (updated: {pattern.last_updated.strftime('%Y-%m-%d')})")
    else:
        print("No patterns updated in the last week")


def demo_tool_integration():
    """Demonstrate fraud database integration with tool integrator."""
    print("\n" + "=" * 60)
    print("FRAUD DATABASE DEMO - TOOL INTEGRATION")
    print("=" * 60)
    
    # Create tool integrator
    integrator = ToolIntegrator()
    
    # Create multiple fraud database tools
    primary_db = create_fraud_database_tool(
        tool_id="primary_fraud_db",
        database_type="generic",
        api_key="primary_api_key"
    )
    
    backup_db = create_fraud_database_tool(
        tool_id="backup_fraud_db",
        database_type="generic",
        api_key="backup_api_key"
    )
    
    # Register tools
    integrator.register_tool(primary_db)
    integrator.register_tool(backup_db)
    
    # Set up fallback chain
    integrator.set_fallback_chain("primary_fraud_db", ["backup_fraud_db"])
    
    print("Registered fraud database tools:")
    print(f"  • Primary: {primary_db.config.tool_name}")
    print(f"  • Backup: {backup_db.config.tool_name}")
    
    # Test integrated search
    test_transaction = {
        "transaction_id": "tx_integration_test",
        "amount": 1800.00,
        "merchant": "Test Merchant",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\nTesting integrated similarity search...")
    
    # Call through integrator
    response = integrator.call_tool(
        "primary_fraud_db", 
        "search_similar", 
        {"transaction_data": test_transaction}
    )
    
    print(f"Response Success: {response.success}")
    print(f"Tool Used: {response.tool_id}")
    print(f"Response Time: {response.response_time_ms:.1f}ms")
    
    if response.success and "similar_cases" in response.data:
        cases_count = len(response.data["similar_cases"])
        print(f"Similar Cases Found: {cases_count}")
    
    # Show tool health
    print(f"\nTool Health Status:")
    health = integrator.health_check()
    print(f"Overall Status: {health['overall_status']}")
    
    for tool_id, tool_health in health['tools'].items():
        print(f"  {tool_id}: {tool_health['health']} (success rate: {tool_health['success_rate']:.1f}%)")


def main():
    """Run all fraud database demos."""
    print("🔍 FRAUD DATABASE INTEGRATION DEMONSTRATION")
    print("This demo showcases fraud database capabilities for")
    print("pattern matching, similarity search, and case management.")
    
    try:
        demo_similarity_search()
        demo_pattern_matching()
        demo_case_reporting()
        demo_fraud_statistics()
        demo_pattern_updates()
        demo_tool_integration()
        
        print("\n" + "=" * 60)
        print("✅ FRAUD DATABASE DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe fraud database integration demonstrated:")
        print("• Similarity search for known fraud cases")
        print("• Real-time fraud pattern matching")
        print("• Fraud case reporting and status management")
        print("• Statistical analysis and trend monitoring")
        print("• Pattern updates and effectiveness tracking")
        print("• Multi-database integration with fallback support")
        print("• Performance monitoring and health checking")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()