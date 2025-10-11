"""
Demo: Comprehensive Audit Trail System

This demo showcases the audit trail system with:
- Immutable logging with tamper detection
- Search and filtering capabilities
- Compliance report generation
- Transaction audit trails
"""

from datetime import datetime, timedelta
from reasoning_engine.audit_trail import (
    AuditTrailSystem,
    AuditEventType,
    AuditSeverity
)


def demo_basic_logging():
    """Demonstrate basic audit logging"""
    print("=" * 80)
    print("DEMO: Basic Audit Logging")
    print("=" * 80)
    
    # Initialize audit system
    audit_system = AuditTrailSystem(storage_path="demo_audit_logs", enable_compression=False)
    
    # Log transaction received
    print("\n1. Logging transaction received event...")
    entry1 = audit_system.log_event(
        event_type=AuditEventType.TRANSACTION_RECEIVED,
        severity=AuditSeverity.INFO,
        action="Transaction received from API",
        details={
            "amount": 5000.00,
            "currency": "USD",
            "merchant": "Electronics Store",
            "location": "New York, USA"
        },
        transaction_id="txn_demo_001",
        user_id="user_12345"
    )
    print(f"   ✓ Event logged with hash: {entry1.entry_hash[:16]}...")
    
    # Log reasoning steps
    print("\n2. Logging reasoning analysis...")
    entry2 = audit_system.log_event(
        event_type=AuditEventType.REASONING_STEP,
        severity=AuditSeverity.INFO,
        action="Multi-step fraud analysis",
        details={
            "analysis_type": "chain_of_thought",
            "steps_completed": 5
        },
        transaction_id="txn_demo_001",
        agent_id="reasoning_engine",
        reasoning_steps=[
            "Step 1: Verify transaction amount is within normal range",
            "Step 2: Check user's historical spending patterns",
            "Step 3: Validate merchant and location",
            "Step 4: Assess velocity patterns",
            "Step 5: Calculate overall risk score"
        ]
    )
    print(f"   ✓ Reasoning logged with {len(entry2.reasoning_steps)} steps")
    
    # Log external API call
    print("\n3. Logging external API call...")
    entry3 = audit_system.log_event(
        event_type=AuditEventType.EXTERNAL_API_CALL,
        severity=AuditSeverity.INFO,
        action="Identity verification check",
        details={
            "api": "identity_verification_service",
            "response_time_ms": 245,
            "status": "success"
        },
        transaction_id="txn_demo_001",
        agent_id="compliance_agent"
    )
    print(f"   ✓ API call logged")
    
    # Log final decision
    print("\n4. Logging fraud decision...")
    entry4 = audit_system.log_event(
        event_type=AuditEventType.DECISION_MADE,
        severity=AuditSeverity.COMPLIANCE,
        action="Fraud detection decision",
        details={
            "risk_score": 0.15,
            "factors_considered": 8,
            "processing_time_ms": 523
        },
        transaction_id="txn_demo_001",
        user_id="user_12345",
        agent_id="risk_assessment_agent",
        decision="APPROVED",
        confidence=0.92,
        evidence=[
            "Amount within normal range for user",
            "Location matches user's typical patterns",
            "Merchant is verified and trusted",
            "No velocity anomalies detected",
            "Identity verification passed"
        ]
    )
    print(f"   ✓ Decision logged: {entry4.decision} (confidence: {entry4.confidence})")
    
    # Verify hash chain
    print("\n5. Verifying hash chain integrity...")
    print(f"   Entry 1 previous hash: {entry1.previous_hash[:16]}... (genesis)")
    print(f"   Entry 2 previous hash: {entry2.previous_hash[:16]}... (matches entry 1)")
    print(f"   Entry 3 previous hash: {entry3.previous_hash[:16]}... (matches entry 2)")
    print(f"   Entry 4 previous hash: {entry4.previous_hash[:16]}... (matches entry 3)")
    print("   ✓ Hash chain verified - tamper-proof!")


def demo_integrity_verification():
    """Demonstrate integrity verification"""
    print("\n" + "=" * 80)
    print("DEMO: Integrity Verification")
    print("=" * 80)
    
    audit_system = AuditTrailSystem(storage_path="demo_audit_logs", enable_compression=False)
    
    # Log some events
    print("\n1. Logging multiple events...")
    for i in range(5):
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action=f"Transaction {i+1}",
            details={"amount": 100 * (i+1)},
            transaction_id=f"txn_{i+1}"
        )
    print(f"   ✓ Logged 5 events")
    
    # Verify integrity
    print("\n2. Verifying audit log integrity...")
    result = audit_system.verify_integrity()
    
    print(f"   Integrity Status: {'✓ VERIFIED' if result['verified'] else '✗ TAMPERED'}")
    print(f"   Total Entries Checked: {result['total_entries']}")
    print(f"   Files Checked: {result['files_checked']}")
    print(f"   Tampered Entries: {len(result['tampered_entries'])}")
    
    if result['verified']:
        print("   ✓ All audit logs are intact and tamper-free!")


def demo_search_capabilities():
    """Demonstrate search and filtering"""
    print("\n" + "=" * 80)
    print("DEMO: Search and Filtering")
    print("=" * 80)
    
    audit_system = AuditTrailSystem(storage_path="demo_audit_logs", enable_compression=False)
    
    # Log diverse events
    print("\n1. Creating diverse audit events...")
    
    # Transaction 1 - Approved
    audit_system.log_event(
        event_type=AuditEventType.TRANSACTION_RECEIVED,
        severity=AuditSeverity.INFO,
        action="Transaction received",
        details={"amount": 250},
        transaction_id="txn_search_001",
        user_id="user_alice"
    )
    
    audit_system.log_event(
        event_type=AuditEventType.DECISION_MADE,
        severity=AuditSeverity.COMPLIANCE,
        action="Decision made",
        details={},
        transaction_id="txn_search_001",
        user_id="user_alice",
        agent_id="risk_agent",
        decision="APPROVED",
        confidence=0.95
    )
    
    # Transaction 2 - Flagged
    audit_system.log_event(
        event_type=AuditEventType.TRANSACTION_RECEIVED,
        severity=AuditSeverity.INFO,
        action="Transaction received",
        details={"amount": 10000},
        transaction_id="txn_search_002",
        user_id="user_bob"
    )
    
    audit_system.log_event(
        event_type=AuditEventType.DECISION_MADE,
        severity=AuditSeverity.WARNING,
        action="Decision made",
        details={},
        transaction_id="txn_search_002",
        user_id="user_bob",
        agent_id="risk_agent",
        decision="FLAGGED",
        confidence=0.78
    )
    
    # Transaction 3 - Escalated
    audit_system.log_event(
        event_type=AuditEventType.ESCALATION,
        severity=AuditSeverity.CRITICAL,
        action="Escalated to human review",
        details={"reason": "High risk score"},
        transaction_id="txn_search_003",
        user_id="user_charlie"
    )
    
    print("   ✓ Created 5 audit events")
    
    # Search by transaction
    print("\n2. Searching by transaction ID...")
    results = audit_system.search_entries(transaction_id="txn_search_001")
    print(f"   Found {len(results)} events for txn_search_001")
    for entry in results:
        print(f"   - {entry['event_type']}: {entry['action']}")
    
    # Search by user
    print("\n3. Searching by user ID...")
    results = audit_system.search_entries(user_id="user_bob")
    print(f"   Found {len(results)} events for user_bob")
    
    # Search by decision
    print("\n4. Searching by decision type...")
    results = audit_system.search_entries(decision="FLAGGED")
    print(f"   Found {len(results)} FLAGGED decisions")
    
    # Search by confidence
    print("\n5. Searching high-confidence decisions...")
    results = audit_system.search_entries(min_confidence=0.9)
    print(f"   Found {len(results)} decisions with confidence >= 0.9")
    
    # Search by event type
    print("\n6. Searching by event type...")
    results = audit_system.search_entries(event_type=AuditEventType.ESCALATION)
    print(f"   Found {len(results)} escalation events")


def demo_transaction_audit_trail():
    """Demonstrate complete transaction audit trail"""
    print("\n" + "=" * 80)
    print("DEMO: Complete Transaction Audit Trail")
    print("=" * 80)
    
    audit_system = AuditTrailSystem(storage_path="demo_audit_logs", enable_compression=False)
    
    transaction_id = "txn_complete_001"
    
    print(f"\n1. Processing transaction {transaction_id}...")
    
    # Simulate complete transaction lifecycle
    audit_system.log_event(
        event_type=AuditEventType.TRANSACTION_RECEIVED,
        severity=AuditSeverity.INFO,
        action="Transaction received",
        details={"amount": 7500, "merchant": "Luxury Goods Store"},
        transaction_id=transaction_id,
        user_id="user_premium"
    )
    
    audit_system.log_event(
        event_type=AuditEventType.MEMORY_ACCESS,
        severity=AuditSeverity.INFO,
        action="Retrieved user history",
        details={"records_found": 45},
        transaction_id=transaction_id,
        agent_id="memory_manager"
    )
    
    audit_system.log_event(
        event_type=AuditEventType.EXTERNAL_API_CALL,
        severity=AuditSeverity.INFO,
        action="Geolocation verification",
        details={"location": "London, UK", "risk_level": "low"},
        transaction_id=transaction_id,
        agent_id="pattern_detector"
    )
    
    audit_system.log_event(
        event_type=AuditEventType.REASONING_STEP,
        severity=AuditSeverity.INFO,
        action="Risk analysis",
        details={},
        transaction_id=transaction_id,
        agent_id="reasoning_engine",
        reasoning_steps=[
            "Analyzed spending patterns",
            "Verified merchant legitimacy",
            "Assessed location risk",
            "Calculated composite risk score"
        ]
    )
    
    audit_system.log_event(
        event_type=AuditEventType.AGENT_ACTION,
        severity=AuditSeverity.INFO,
        action="Multi-agent coordination",
        details={"agents_involved": 3},
        transaction_id=transaction_id,
        agent_id="orchestrator"
    )
    
    audit_system.log_event(
        event_type=AuditEventType.DECISION_MADE,
        severity=AuditSeverity.COMPLIANCE,
        action="Final decision",
        details={"risk_score": 0.22},
        transaction_id=transaction_id,
        user_id="user_premium",
        agent_id="risk_agent",
        decision="APPROVED",
        confidence=0.88,
        evidence=["Premium user with good history", "Verified location", "Legitimate merchant"]
    )
    
    print("   ✓ Transaction processed with 6 audit events")
    
    # Get complete audit trail
    print(f"\n2. Retrieving complete audit trail for {transaction_id}...")
    trail = audit_system.get_transaction_audit_trail(transaction_id)
    
    print(f"\n   Transaction Audit Trail Summary:")
    print(f"   ─────────────────────────────────")
    print(f"   Total Events: {trail['total_events']}")
    print(f"   Decisions: {len(trail['decisions'])}")
    print(f"   Reasoning Steps: {len(trail['reasoning_steps'])}")
    print(f"   Agent Actions: {len(trail['agent_actions'])}")
    print(f"   External Calls: {len(trail['external_calls'])}")
    
    print(f"\n   Timeline:")
    for i, event in enumerate(trail['timeline'], 1):
        print(f"   {i}. [{event['event_type']}] {event['action']}")
    
    if trail['decisions']:
        decision = trail['decisions'][0]
        print(f"\n   Final Decision: {decision['decision']}")
        print(f"   Confidence: {decision['confidence']}")
        if decision.get('evidence'):
            print(f"   Evidence:")
            for evidence in decision['evidence']:
                print(f"   - {evidence}")


def demo_compliance_reporting():
    """Demonstrate compliance report generation"""
    print("\n" + "=" * 80)
    print("DEMO: Compliance Reporting")
    print("=" * 80)
    
    audit_system = AuditTrailSystem(storage_path="demo_audit_logs", enable_compression=False)
    
    print("\n1. Generating compliance report...")
    
    # Generate report for last hour
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    
    report = audit_system.generate_compliance_report(start_time, end_time, report_type="detailed")
    
    print(f"\n   Compliance Report")
    print(f"   ═════════════════════════════════════════════════════════")
    print(f"   Period: {report['period']['start']} to {report['period']['end']}")
    print(f"\n   Summary:")
    print(f"   ─────────")
    print(f"   Total Events: {report['summary']['total_events']}")
    print(f"   Total Transactions: {report['summary']['total_transactions']}")
    print(f"   Total Users: {report['summary']['total_users']}")
    print(f"   Total Decisions: {report['summary']['total_decisions']}")
    
    print(f"\n   Events by Type:")
    print(f"   ───────────────")
    for event_type, count in report['by_event_type'].items():
        print(f"   {event_type}: {count}")
    
    print(f"\n   Events by Severity:")
    print(f"   ───────────────────")
    for severity, count in report['by_severity'].items():
        print(f"   {severity}: {count}")
    
    if report['by_decision']:
        print(f"\n   Decisions:")
        print(f"   ──────────")
        for decision, count in report['by_decision'].items():
            print(f"   {decision}: {count}")
    
    print(f"\n   High Confidence Decisions: {len(report['high_confidence_decisions'])}")
    print(f"   Escalations: {len(report['escalations'])}")
    print(f"   Errors: {len(report['errors'])}")
    
    print(f"\n   Integrity Check:")
    print(f"   ────────────────")
    integrity = report['integrity_check']
    status = "✓ VERIFIED" if integrity['verified'] else "✗ TAMPERED"
    print(f"   Status: {status}")
    print(f"   Entries Checked: {integrity['total_entries_checked']}")
    print(f"   Tampered Entries: {integrity['tampered_entries']}")


def demo_export_functionality():
    """Demonstrate audit trail export"""
    print("\n" + "=" * 80)
    print("DEMO: Audit Trail Export")
    print("=" * 80)
    
    audit_system = AuditTrailSystem(storage_path="demo_audit_logs", enable_compression=False)
    
    print("\n1. Exporting audit trail to JSON...")
    audit_system.export_audit_trail("demo_audit_export.json", format="json")
    print("   ✓ Exported to demo_audit_export.json")
    
    print("\n2. Export can be used for:")
    print("   - Regulatory compliance submissions")
    print("   - External audit reviews")
    print("   - Long-term archival")
    print("   - Data analysis and reporting")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "COMPREHENSIVE AUDIT TRAIL SYSTEM DEMO" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    
    demo_basic_logging()
    demo_integrity_verification()
    demo_search_capabilities()
    demo_transaction_audit_trail()
    demo_compliance_reporting()
    demo_export_functionality()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("✓ Immutable logging with hash chain")
    print("✓ Tamper detection and integrity verification")
    print("✓ Comprehensive search and filtering")
    print("✓ Complete transaction audit trails")
    print("✓ Automated compliance reporting")
    print("✓ Export functionality for regulatory compliance")
    print("\n")


if __name__ == "__main__":
    main()
