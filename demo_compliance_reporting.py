"""
Demo script for the Compliance Reporting System

Demonstrates:
- Automated compliance report generation
- Regulatory requirement tracking and validation
- Customizable reporting templates for different jurisdictions
- Real-time compliance monitoring and alerting
"""

import json
from datetime import datetime, timedelta
from src.compliance_reporting import (
    ComplianceReportingSystem,
    Jurisdiction,
    ReportFormat,
    RegulatoryRequirement
)


def demo_requirement_validation():
    """Demonstrate regulatory requirement validation"""
    print("=" * 70)
    print("COMPLIANCE REPORTING DEMO - REQUIREMENT VALIDATION")
    print("=" * 70)
    
    system = ComplianceReportingSystem()
    
    print(f"\nTotal regulatory requirements loaded: {len(system.requirements)}")
    
    # Show sample requirements
    print("\nSample Requirements:")
    for i, (req_id, req) in enumerate(list(system.requirements.items())[:3]):
        print(f"\n{i+1}. {req.title}")
        print(f"   ID: {req_id}")
        print(f"   Regulation: {req.regulation}")
        print(f"   Jurisdiction: {req.jurisdiction}")
        print(f"   Mandatory: {req.mandatory}")
        print(f"   Status: {req.status}")
    
    # Validate PCI DSS encryption requirement
    print("\n" + "-" * 70)
    print("Validating PCI DSS Encryption Requirement...")
    print("-" * 70)
    
    evidence = {
        "encryption_enabled": True,
        "encryption_algorithm": "AES-256",
        "key_management": "AWS KMS",
        "logging_enabled": True,
        "log_count": 1500
    }
    
    result = system.validate_requirement("PCI_DSS_3.2.1", evidence)
    
    if result["success"]:
        print(f"✅ Validation completed")
        print(f"   Compliance Score: {result['compliance_score']:.2%}")
        print(f"   Status: {result['status']}")
        print(f"   Timestamp: {result['timestamp']}")
        print(f"\n   Validation Results:")
        for validation in result['validation_results']:
            status = "✓" if validation['met'] else "✗"
            print(f"   {status} {validation['criterion']}")
    
    # Validate GDPR requirement with missing evidence
    print("\n" + "-" * 70)
    print("Validating GDPR Right to Erasure (with incomplete evidence)...")
    print("-" * 70)
    
    incomplete_evidence = {
        "deletion_mechanism": False,  # Not implemented
        "logging_enabled": True
    }
    
    result = system.validate_requirement("GDPR_ART_17", incomplete_evidence)
    
    if result["success"]:
        print(f"⚠️  Validation completed with issues")
        print(f"   Compliance Score: {result['compliance_score']:.2%}")
        print(f"   Status: {result['status']}")
        print(f"\n   Validation Results:")
        for validation in result['validation_results']:
            status = "✓" if validation['met'] else "✗"
            print(f"   {status} {validation['criterion']}")


def demo_report_generation():
    """Demonstrate automated compliance report generation"""
    print("\n" + "=" * 70)
    print("COMPLIANCE REPORTING DEMO - REPORT GENERATION")
    print("=" * 70)
    
    system = ComplianceReportingSystem()
    
    # Validate some requirements first
    print("\nPreparing compliance data...")
    
    # Validate multiple requirements
    validations = [
        ("PCI_DSS_3.2.1", {"encryption_enabled": True, "logging_enabled": True, "log_count": 1000}),
        ("PCI_DSS_10.1", {"logging_enabled": True, "log_count": 5000, "encryption_enabled": True}),
        ("GDPR_ART_6", {"consent_obtained": True, "logging_enabled": True}),
        ("GDPR_ART_17", {"deletion_mechanism": True, "logging_enabled": True}),
        ("BSA_CTR", {"monitoring_active": True, "logging_enabled": True}),
    ]
    
    for req_id, evidence in validations:
        system.validate_requirement(req_id, evidence)
    
    # Prepare audit data
    audit_data = {
        "total_events": 15000,
        "complete_trails": 14850,
        "total_transactions": 10000,
        "violations": 50,
        "period": "Last 30 days",
        "by_event_type": {
            "transaction_received": 10000,
            "decision_made": 10000,
            "policy_violation": 50,
            "system_event": 4950
        },
        "by_severity": {
            "info": 14500,
            "warning": 450,
            "critical": 50
        },
        "integrity_check": {
            "verified": True,
            "total_entries": 15000
        },
        "key_findings": [
            "All audit trails verified for integrity",
            "50 policy violations detected and addressed",
            "99% audit trail completeness achieved"
        ]
    }
    
    # Generate reports for different jurisdictions
    jurisdictions = [
        Jurisdiction.US_FEDERAL,
        Jurisdiction.EU,
        Jurisdiction.GLOBAL
    ]
    
    for jurisdiction in jurisdictions:
        print(f"\n{'-' * 70}")
        print(f"Generating {jurisdiction.value.upper()} Compliance Report...")
        print(f"{'-' * 70}")
        
        report = system.generate_report(
            jurisdiction=jurisdiction,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            audit_data=audit_data,
            format=ReportFormat.JSON
        )
        
        print(f"\n📊 Report Generated: {report['report_id']}")
        print(f"   Template: {report['template']}")
        print(f"   Overall Compliance Score: {report['overall_compliance_score']:.2%}")
        print(f"   Status: {report['status']}")
        
        print(f"\n   Requirements Summary:")
        summary = report['requirements_summary']
        print(f"   • Total: {summary['total']}")
        print(f"   • Compliant: {summary['compliant']} ✓")
        print(f"   • Partial: {summary['partial']} ⚠")
        print(f"   • Non-Compliant: {summary['non_compliant']} ✗")
        print(f"   • Pending: {summary['pending']}")
        
        # Show executive summary
        if 'executive_summary' in report['sections']:
            exec_summary = report['sections']['executive_summary']
            print(f"\n   Executive Summary:")
            print(f"   {exec_summary['overview']}")
            print(f"   Compliance Rate: {exec_summary['compliance_rate']}")
        
        # Show active alerts
        if report['active_alerts']:
            print(f"\n   ⚠️  Active Alerts: {len(report['active_alerts'])}")
            for alert in report['active_alerts'][:3]:
                print(f"   • [{alert['severity'].upper()}] {alert['title']}")
        
        print(f"\n   Report saved to: compliance_reports/{report['report_id']}.json")


def demo_real_time_monitoring():
    """Demonstrate real-time compliance monitoring"""
    print("\n" + "=" * 70)
    print("COMPLIANCE REPORTING DEMO - REAL-TIME MONITORING")
    print("=" * 70)
    
    system = ComplianceReportingSystem()
    
    # Validate requirements
    print("\nSetting up compliance baseline...")
    validations = [
        ("PCI_DSS_3.2.1", {"encryption_enabled": True, "logging_enabled": True}),
        ("PCI_DSS_10.1", {"logging_enabled": True, "log_count": 5000}),
        ("GDPR_ART_6", {"consent_obtained": True}),
        ("GDPR_ART_17", {"deletion_mechanism": False}),  # Non-compliant
        ("GDPR_ART_33", {"notification_system": False}),  # Non-compliant
        ("BSA_CTR", {"monitoring_active": True}),
        ("BSA_SAR", {"monitoring_active": False}),  # Non-compliant
    ]
    
    for req_id, evidence in validations:
        system.validate_requirement(req_id, evidence)
    
    # Simulate monitoring with various scenarios
    print("\n" + "-" * 70)
    print("Scenario 1: Normal Operations")
    print("-" * 70)
    
    audit_data_normal = {
        "total_events": 10000,
        "complete_trails": 9950,
        "total_transactions": 8000,
        "violations": 40
    }
    
    alerts = system.monitor_compliance(audit_data_normal)
    
    print(f"\n✅ Monitoring completed")
    print(f"   New alerts generated: {len(alerts)}")
    
    if alerts:
        print(f"\n   Generated Alerts:")
        for alert in alerts:
            print(f"   • [{alert.severity.upper()}] {alert.title}")
            print(f"     {alert.description}")
    
    # Scenario 2: Degraded compliance
    print("\n" + "-" * 70)
    print("Scenario 2: Degraded Compliance (High Violation Rate)")
    print("-" * 70)
    
    audit_data_degraded = {
        "total_events": 10000,
        "complete_trails": 9500,  # Below threshold
        "total_transactions": 8000,
        "violations": 200  # High violation rate
    }
    
    alerts = system.monitor_compliance(audit_data_degraded)
    
    print(f"\n⚠️  Monitoring completed with issues")
    print(f"   New alerts generated: {len(alerts)}")
    
    if alerts:
        print(f"\n   Generated Alerts:")
        for alert in alerts:
            severity_icon = "🔴" if alert.severity == "critical" else "🟡"
            print(f"   {severity_icon} [{alert.severity.upper()}] {alert.title}")
            print(f"     {alert.description}")
    
    # Show all active alerts
    print("\n" + "-" * 70)
    print("Active Alerts Summary")
    print("-" * 70)
    
    active_alerts = system.get_active_alerts()
    print(f"\nTotal active alerts: {len(active_alerts)}")
    
    critical_alerts = system.get_active_alerts(severity="critical")
    high_alerts = system.get_active_alerts(severity="high")
    
    print(f"   Critical: {len(critical_alerts)}")
    print(f"   High: {len(high_alerts)}")
    
    # Resolve an alert
    if active_alerts:
        print(f"\n   Resolving alert: {active_alerts[0].alert_id}")
        system.resolve_alert(
            active_alerts[0].alert_id,
            "Issue addressed through system configuration update"
        )
        print(f"   ✅ Alert resolved")


def demo_compliance_dashboard():
    """Demonstrate compliance dashboard"""
    print("\n" + "=" * 70)
    print("COMPLIANCE REPORTING DEMO - COMPLIANCE DASHBOARD")
    print("=" * 70)
    
    system = ComplianceReportingSystem()
    
    # Setup compliance state
    validations = [
        ("PCI_DSS_3.2.1", {"encryption_enabled": True, "logging_enabled": True}),
        ("PCI_DSS_10.1", {"logging_enabled": True, "log_count": 5000}),
        ("GDPR_ART_6", {"consent_obtained": True}),
        ("GDPR_ART_17", {"deletion_mechanism": True}),
        ("GDPR_ART_33", {"notification_system": True}),
        ("BSA_CTR", {"monitoring_active": True}),
        ("BSA_SAR", {"monitoring_active": True}),
    ]
    
    for req_id, evidence in validations:
        system.validate_requirement(req_id, evidence)
    
    # Update monitoring
    audit_data = {
        "total_events": 10000,
        "complete_trails": 9950,
        "total_transactions": 8000,
        "violations": 40
    }
    
    system.monitor_compliance(audit_data)
    
    # Get dashboard data
    dashboard = system.get_compliance_dashboard()
    
    print(f"\n📊 COMPLIANCE DASHBOARD")
    print(f"   Timestamp: {dashboard['timestamp']}")
    print(f"   Overall Status: {dashboard['overall_status'].upper()}")
    
    print(f"\n   📈 Key Metrics:")
    for metric_id, metric in dashboard['metrics'].items():
        status_icon = "✓" if metric['status'] == "compliant" else "✗"
        print(f"   {status_icon} {metric['name']}")
        print(f"      Current: {metric['current_value']:.4f} | Threshold: {metric['threshold']:.4f}")
        print(f"      Status: {metric['status']} | Trend: {metric['trend']}")
    
    print(f"\n   🎯 Requirements Status:")
    req_status = dashboard['requirements_status']
    print(f"   • Total Requirements: {req_status['total']}")
    print(f"   • Compliant: {req_status['compliant']} ({req_status['compliant']/req_status['total']*100:.1f}%)")
    print(f"   • Partial: {req_status['partial']}")
    print(f"   • Non-Compliant: {req_status['non_compliant']}")
    
    print(f"\n   🚨 Active Alerts:")
    alerts_summary = dashboard['active_alerts']
    print(f"   • Total: {alerts_summary['total']}")
    print(f"   • Critical: {alerts_summary['critical']}")
    print(f"   • High: {alerts_summary['high']}")
    
    if alerts_summary['alerts']:
        print(f"\n   Recent Alerts:")
        for alert in alerts_summary['alerts'][:3]:
            print(f"   • [{alert['severity'].upper()}] {alert['title']}")


def demo_jurisdiction_templates():
    """Demonstrate customizable jurisdiction templates"""
    print("\n" + "=" * 70)
    print("COMPLIANCE REPORTING DEMO - JURISDICTION TEMPLATES")
    print("=" * 70)
    
    system = ComplianceReportingSystem()
    
    print(f"\nAvailable Jurisdiction Templates:")
    
    for jurisdiction, template in system.report_templates.items():
        print(f"\n{'-' * 70}")
        print(f"📋 {template['name']}")
        print(f"   Jurisdiction: {jurisdiction}")
        print(f"   Regulations Covered: {', '.join(template['regulations'])}")
        print(f"\n   Report Sections:")
        for i, section in enumerate(template['sections'], 1):
            print(f"   {i}. {section.replace('_', ' ').title()}")
        print(f"\n   Required Signatures:")
        for sig in template['required_signatures']:
            print(f"   • {sig.replace('_', ' ').title()}")


def main():
    """Run all compliance reporting demos"""
    print("🛡️  COMPLIANCE REPORTING SYSTEM DEMONSTRATION")
    print("=" * 70)
    print("This demo showcases automated compliance reporting with:")
    print("• Regulatory requirement tracking and validation")
    print("• Multi-jurisdiction report generation")
    print("• Real-time compliance monitoring and alerting")
    print("• Customizable reporting templates")
    print("=" * 70)
    
    try:
        demo_requirement_validation()
        demo_report_generation()
        demo_real_time_monitoring()
        demo_compliance_dashboard()
        demo_jurisdiction_templates()
        
        print("\n" + "=" * 70)
        print("✅ COMPLIANCE REPORTING DEMO COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nThe compliance reporting system demonstrated:")
        print("• ✓ Automated regulatory requirement validation")
        print("• ✓ Multi-jurisdiction compliance report generation")
        print("• ✓ Real-time compliance monitoring with alerting")
        print("• ✓ Customizable templates for US, EU, UK, and Global")
        print("• ✓ Comprehensive compliance dashboard")
        print("• ✓ Requirement tracking across PCI DSS, GDPR, BSA/AML, SOX")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
