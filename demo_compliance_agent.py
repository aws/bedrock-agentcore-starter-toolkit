"""
Demo script for the Compliance Agent

Demonstrates the compliance agent's capabilities including:
- Regulatory compliance checking
- Audit trail generation
- Policy violation detection
- Compliance report generation
"""

import json
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path for imports
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.compliance_agent import (
    ComplianceAgent, ComplianceRegulation, AuditEventType
)
from src.base_agent import AgentConfiguration, AgentCapability
from src.memory_manager import MemoryManager
from src.models import Transaction, DecisionContext, FraudDecision, Location, DeviceInfo


def create_sample_transactions():
    """Create sample transactions for testing."""
    transactions = []
    
    # Normal transaction
    transactions.append({
        "id": "tx_001",
        "user_id": "user_123",
        "amount": 150.00,
        "currency": "USD",
        "merchant": "Amazon",
        "category": "online_retail",
        "location": {"country": "US", "city": "New York"},
        "timestamp": datetime.now().isoformat(),
        "card_type": "credit"
    })
    
    # High-value transaction (triggers CTR requirement)
    transactions.append({
        "id": "tx_002",
        "user_id": "user_456",
        "amount": 12000.00,
        "currency": "USD",
        "merchant": "Luxury Cars Inc",
        "category": "automotive",
        "location": {"country": "US", "city": "Los Angeles"},
        "timestamp": datetime.now().isoformat(),
        "card_type": "credit"
    })
    
    # Transaction with PII data (GDPR concern)
    transactions.append({
        "id": "tx_003",
        "user_id": "user_789",
        "amount": 75.50,
        "currency": "EUR",
        "merchant": "European Store",
        "category": "retail",
        "location": {"country": "DE", "city": "Berlin"},
        "timestamp": datetime.now().isoformat(),
        "card_type": "debit",
        "email": "user@example.com",  # PII that might not be necessary
        "phone": "+49123456789"  # PII that might not be necessary
    })
    
    # Cross-border transaction
    transactions.append({
        "id": "tx_004",
        "user_id": "user_123",
        "amount": 2500.00,
        "currency": "USD",
        "merchant": "International Supplier",
        "category": "business",
        "location": {"country": "CN", "city": "Shanghai"},
        "user_country": "US",
        "merchant_country": "CN",
        "timestamp": datetime.now().isoformat(),
        "card_type": "business"
    })
    
    return transactions


def create_sample_decisions():
    """Create sample decision contexts."""
    decisions = []
    
    decisions.append({
        "transaction_id": "tx_001",
        "user_id": "user_123",
        "decision": "approved",
        "confidence_score": 0.95,
        "reasoning_steps": [
            "Transaction amount within user's typical range",
            "Merchant frequently used by user",
            "Location matches user's common locations"
        ],
        "timestamp": datetime.now().isoformat(),
        "agent_version": "1.0.0",
        "automated_decision": True,
        "human_review_available": True
    })
    
    decisions.append({
        "transaction_id": "tx_002",
        "user_id": "user_456",
        "decision": "flagged",
        "confidence_score": 0.75,
        "reasoning_steps": [
            "High transaction amount requires additional verification",
            "First-time merchant for this user",
            "Amount exceeds daily spending pattern"
        ],
        "timestamp": datetime.now().isoformat(),
        "agent_version": "1.0.0",
        "automated_decision": True,
        "human_review_available": True,
        "control_validation": True,
        "decision_maker": "fraud_agent_001",
        "reviewer": "human_reviewer_001"
    })
    
    decisions.append({
        "transaction_id": "tx_003",
        "user_id": "user_789",
        "decision": "approved",
        "confidence_score": 0.88,
        "reasoning_steps": [
            "Transaction amount is low risk",
            "User has good transaction history",
            "Location matches user profile"
        ],
        "timestamp": datetime.now().isoformat(),
        "agent_version": "1.0.0",
        "automated_decision": True,
        "human_review_available": False  # GDPR violation - no human review option
    })
    
    return decisions


def demo_compliance_checking():
    """Demonstrate compliance checking functionality."""
    print("=" * 60)
    print("COMPLIANCE AGENT DEMO - COMPLIANCE CHECKING")
    print("=" * 60)
    
    # Initialize compliance agent
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    
    config = AgentConfiguration(
        agent_id="demo_compliance_agent",
        agent_name="DemoComplianceAgent",
        version="1.0.0",
        capabilities=[
            AgentCapability.COMPLIANCE_CHECKING,
            AgentCapability.REAL_TIME_PROCESSING
        ]
    )
    
    compliance_agent = ComplianceAgent(memory_manager, config)
    
    transactions = create_sample_transactions()
    decisions = create_sample_decisions()
    
    print(f"\nTesting compliance for {len(transactions)} transactions...")
    
    for i, (transaction, decision) in enumerate(zip(transactions, decisions)):
        print(f"\n--- Transaction {i+1}: {transaction['id']} ---")
        print(f"Amount: ${transaction['amount']:.2f}")
        print(f"Merchant: {transaction['merchant']}")
        print(f"Location: {transaction['location']['country']}")
        
        # Perform compliance check
        request_data = {
            "request_type": "compliance_check",
            "transaction": transaction,
            "decision_context": decision,
            "regulations": ["pci_dss", "gdpr", "bsa_aml"]
        }
        
        result = compliance_agent.process_request(request_data)
        
        if result.success:
            print(f"Overall Compliance Score: {result.result_data['overall_compliance_score']:.2f}")
            
            for check in result.result_data['compliance_checks']:
                regulation = check['regulation']
                status = check['status']
                print(f"  {regulation}: {status}")
                
                if check['violations']:
                    print(f"    Violations:")
                    for violation in check['violations']:
                        print(f"      - {violation}")
                
                if check['recommendations']:
                    print(f"    Recommendations:")
                    for rec in check['recommendations'][:2]:  # Show first 2
                        print(f"      - {rec}")
        else:
            print(f"Compliance check failed: {result.error_message}")


def demo_policy_violations():
    """Demonstrate policy violation detection."""
    print("\n" + "=" * 60)
    print("COMPLIANCE AGENT DEMO - POLICY VIOLATION DETECTION")
    print("=" * 60)
    
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    compliance_agent = ComplianceAgent(memory_manager)
    
    transactions = create_sample_transactions()
    decisions = create_sample_decisions()
    
    print(f"\nChecking policy violations for {len(transactions)} transactions...")
    
    total_violations = 0
    
    for i, (transaction, decision) in enumerate(zip(transactions, decisions)):
        print(f"\n--- Transaction {i+1}: {transaction['id']} ---")
        
        request_data = {
            "request_type": "policy_check",
            "transaction": transaction,
            "decision_context": decision
        }
        
        result = compliance_agent.process_request(request_data)
        
        if result.success:
            violations_count = result.result_data['violations_count']
            total_violations += violations_count
            
            if violations_count > 0:
                print(f"⚠️  Found {violations_count} policy violations:")
                for violation in result.result_data['policy_violations']:
                    print(f"  - {violation['policy_name']}: {violation['description']}")
                    print(f"    Severity: {violation['severity']}")
            else:
                print("✅ No policy violations detected")
        else:
            print(f"Policy check failed: {result.error_message}")
    
    print(f"\nTotal policy violations detected: {total_violations}")


def demo_audit_trail():
    """Demonstrate audit trail functionality."""
    print("\n" + "=" * 60)
    print("COMPLIANCE AGENT DEMO - AUDIT TRAIL MANAGEMENT")
    print("=" * 60)
    
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    compliance_agent = ComplianceAgent(memory_manager)
    
    print("\nLogging various audit events...")
    
    # Log different types of audit events
    audit_requests = [
        {
            "request_type": "audit_event",
            "event_type": "transaction_processed",
            "description": "High-value transaction processed",
            "transaction_id": "tx_002",
            "user_id": "user_456",
            "event_data": {"amount": 12000.0, "risk_level": "high"}
        },
        {
            "request_type": "audit_event",
            "event_type": "decision_made",
            "description": "Fraud detection decision made",
            "transaction_id": "tx_002",
            "user_id": "user_456",
            "event_data": {"decision": "flagged", "confidence": 0.75}
        },
        {
            "request_type": "audit_event",
            "event_type": "policy_violation",
            "description": "Transaction limit exceeded",
            "transaction_id": "tx_002",
            "user_id": "user_456",
            "event_data": {"policy": "single_transaction_limit", "limit": 5000.0}
        },
        {
            "request_type": "audit_event",
            "event_type": "data_access",
            "description": "User profile accessed for risk assessment",
            "user_id": "user_456",
            "event_data": {"accessor": "risk_agent", "data_type": "profile"}
        }
    ]
    
    for request in audit_requests:
        result = compliance_agent.process_request(request)
        if result.success:
            event = result.result_data['audit_event']
            print(f"✅ Logged: {event['event_type']} - {event['event_description']}")
        else:
            print(f"❌ Failed to log audit event: {result.error_message}")
    
    # Retrieve and display audit trail
    print(f"\nRetrieving audit trail...")
    audit_events = compliance_agent.get_audit_trail()
    
    print(f"Total audit events: {len(audit_events)}")
    print("\nRecent audit events:")
    for event in audit_events[:5]:  # Show last 5 events
        print(f"  {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {event.event_type.value}")
        print(f"    {event.event_description}")
        if event.user_id:
            print(f"    User: {event.user_id}")
        if event.transaction_id:
            print(f"    Transaction: {event.transaction_id}")
        print()
    
    # Test audit integrity
    print("Verifying audit trail integrity...")
    integrity_results = compliance_agent.verify_audit_integrity()
    print(f"  Total events: {integrity_results['total_events']}")
    print(f"  Verified events: {integrity_results['verified_events']}")
    print(f"  Corrupted events: {integrity_results['corrupted_events']}")
    print(f"  Integrity score: {integrity_results['integrity_score']:.2%}")


def demo_compliance_reporting():
    """Demonstrate compliance report generation."""
    print("\n" + "=" * 60)
    print("COMPLIANCE AGENT DEMO - COMPLIANCE REPORTING")
    print("=" * 60)
    
    memory_manager = MemoryManager(endpoint_url='http://localhost:8000')
    compliance_agent = ComplianceAgent(memory_manager)
    
    # First, generate some audit events and compliance checks
    transactions = create_sample_transactions()
    decisions = create_sample_decisions()
    
    print("Generating compliance data...")
    
    # Process transactions to generate audit events
    for transaction, decision in zip(transactions, decisions):
        # Compliance check
        compliance_agent.process_request({
            "request_type": "compliance_check",
            "transaction": transaction,
            "decision_context": decision,
            "regulations": ["pci_dss", "gdpr", "bsa_aml"]
        })
        
        # Policy check
        compliance_agent.process_request({
            "request_type": "policy_check",
            "transaction": transaction,
            "decision_context": decision
        })
    
    # Generate compliance report
    print("\nGenerating compliance report...")
    
    report_request = {
        "request_type": "generate_report",
        "report_type": "monthly_compliance_summary",
        "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "regulations": ["pci_dss", "gdpr", "bsa_aml"]
    }
    
    result = compliance_agent.process_request(report_request)
    
    if result.success:
        report = result.result_data['report']
        
        print(f"\n📊 COMPLIANCE REPORT")
        print(f"Report ID: {report['report_id']}")
        print(f"Report Type: {report['report_type']}")
        print(f"Period: {report['reporting_period_start'][:10]} to {report['reporting_period_end'][:10]}")
        print(f"Overall Compliance Score: {report['overall_compliance_score']:.2%}")
        
        print(f"\n📈 SUMMARY STATISTICS")
        stats = report['summary_statistics']
        print(f"  Total Audit Events: {stats['total_audit_events']}")
        print(f"  Policy Violations: {stats['policy_violations']}")
        print(f"  Transactions Processed: {stats['transactions_processed']}")
        print(f"  Decisions Made: {stats['decisions_made']}")
        print(f"  Compliance Checks: {stats['compliance_checks_performed']}")
        
        print(f"\n🔍 COMPLIANCE CHECKS")
        for check in report['compliance_checks']:
            regulation = check['regulation']
            status = check['status']
            violations_count = len(check['violations'])
            print(f"  {regulation}: {status} ({violations_count} violations)")
        
        print(f"\n💡 RECOMMENDATIONS")
        for i, rec in enumerate(report['recommendations'][:5], 1):
            print(f"  {i}. {rec}")
        
    else:
        print(f"Report generation failed: {result.error_message}")


def main():
    """Run all compliance agent demos."""
    print("🛡️  COMPLIANCE AGENT DEMONSTRATION")
    print("This demo showcases the compliance agent's capabilities for")
    print("regulatory compliance, audit trails, and policy enforcement.")
    
    try:
        demo_compliance_checking()
        demo_policy_violations()
        demo_audit_trail()
        demo_compliance_reporting()
        
        print("\n" + "=" * 60)
        print("✅ COMPLIANCE AGENT DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe compliance agent demonstrated:")
        print("• Multi-regulation compliance checking (PCI DSS, GDPR, BSA/AML)")
        print("• Real-time policy violation detection")
        print("• Comprehensive audit trail management")
        print("• Automated compliance report generation")
        print("• Audit trail integrity verification")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()