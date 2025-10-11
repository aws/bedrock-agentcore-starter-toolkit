"""
Compliance Reporting System

Automated compliance report generation with regulatory requirement tracking,
customizable templates for different jurisdictions, and real-time monitoring.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from pathlib import Path


class ReportFormat(Enum):
    """Supported report formats"""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"


class Jurisdiction(Enum):
    """Regulatory jurisdictions"""
    US_FEDERAL = "us_federal"
    EU = "eu"
    UK = "uk"
    APAC = "apac"
    GLOBAL = "global"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNDER_REVIEW = "under_review"


@dataclass
class RegulatoryRequirement:
    """Individual regulatory requirement"""
    requirement_id: str
    regulation: str
    jurisdiction: str
    title: str
    description: str
    mandatory: bool
    validation_criteria: List[str]
    evidence_required: List[str]
    last_validated: Optional[str] = None
    status: str = "pending"
    compliance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ComplianceMetric:
    """Compliance metric for monitoring"""
    metric_id: str
    name: str
    description: str
    current_value: float
    threshold: float
    status: str
    timestamp: str
    trend: str = "stable"  # improving, declining, stable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ComplianceAlert:
    """Real-time compliance alert"""
    alert_id: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    requirement_id: Optional[str]
    triggered_at: str
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ComplianceReportingSystem:
    """
    Comprehensive compliance reporting system with automated report generation,
    regulatory tracking, customizable templates, and real-time monitoring.
    """
    
    def __init__(self, storage_path: str = "compliance_reports"):
        """
        Initialize compliance reporting system
        
        Args:
            storage_path: Directory for storing reports
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.requirements: Dict[str, RegulatoryRequirement] = {}
        self.metrics: Dict[str, ComplianceMetric] = {}
        self.alerts: List[ComplianceAlert] = []
        self.report_templates: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_requirements()
        self._initialize_templates()
        self._initialize_metrics()
    
    def _initialize_requirements(self):
        """Initialize regulatory requirements database"""
        # PCI DSS Requirements
        pci_requirements = [
            RegulatoryRequirement(
                requirement_id="PCI_DSS_3.2.1",
                regulation="PCI DSS",
                jurisdiction=Jurisdiction.GLOBAL.value,
                title="Protect Stored Cardholder Data",
                description="Cardholder data must be encrypted using strong cryptography",
                mandatory=True,
                validation_criteria=[
                    "All card numbers encrypted at rest",
                    "Encryption keys properly managed",
                    "Access to encryption keys restricted"
                ],
                evidence_required=["encryption_audit", "key_management_logs"]
            ),
            RegulatoryRequirement(
                requirement_id="PCI_DSS_10.1",
                regulation="PCI DSS",
                jurisdiction=Jurisdiction.GLOBAL.value,
                title="Audit Trail Implementation",
                description="Implement audit trails to link all access to system components",
                mandatory=True,
                validation_criteria=[
                    "All user access logged",
                    "All administrative actions logged",
                    "Logs protected from tampering"
                ],
                evidence_required=["audit_logs", "log_integrity_verification"]
            )
        ]
        
        # GDPR Requirements
        gdpr_requirements = [
            RegulatoryRequirement(
                requirement_id="GDPR_ART_6",
                regulation="GDPR",
                jurisdiction=Jurisdiction.EU.value,
                title="Lawful Basis for Processing",
                description="Personal data processing must have a lawful basis",
                mandatory=True,
                validation_criteria=[
                    "Consent obtained where required",
                    "Legitimate interest documented",
                    "Processing purpose clearly defined"
                ],
                evidence_required=["consent_records", "processing_purpose_documentation"]
            ),
            RegulatoryRequirement(
                requirement_id="GDPR_ART_17",
                regulation="GDPR",
                jurisdiction=Jurisdiction.EU.value,
                title="Right to Erasure",
                description="Data subjects have the right to request data deletion",
                mandatory=True,
                validation_criteria=[
                    "Deletion mechanism implemented",
                    "Deletion requests processed within 30 days",
                    "Deletion confirmation provided"
                ],
                evidence_required=["deletion_logs", "request_processing_records"]
            ),
            RegulatoryRequirement(
                requirement_id="GDPR_ART_33",
                regulation="GDPR",
                jurisdiction=Jurisdiction.EU.value,
                title="Breach Notification",
                description="Data breaches must be reported within 72 hours",
                mandatory=True,
                validation_criteria=[
                    "Breach detection system in place",
                    "Notification process documented",
                    "72-hour timeline achievable"
                ],
                evidence_required=["breach_detection_logs", "notification_procedures"]
            )
        ]
        
        # BSA/AML Requirements
        bsa_requirements = [
            RegulatoryRequirement(
                requirement_id="BSA_CTR",
                regulation="BSA/AML",
                jurisdiction=Jurisdiction.US_FEDERAL.value,
                title="Currency Transaction Reporting",
                description="Report cash transactions over $10,000",
                mandatory=True,
                validation_criteria=[
                    "Transactions over $10,000 identified",
                    "CTR filed within required timeframe",
                    "Complete transaction details captured"
                ],
                evidence_required=["ctr_filings", "transaction_monitoring_logs"]
            ),
            RegulatoryRequirement(
                requirement_id="BSA_SAR",
                regulation="BSA/AML",
                jurisdiction=Jurisdiction.US_FEDERAL.value,
                title="Suspicious Activity Reporting",
                description="Report suspicious transactions that may indicate money laundering",
                mandatory=True,
                validation_criteria=[
                    "Suspicious activity detection system operational",
                    "SAR filed within 30 days of detection",
                    "Adequate investigation documentation"
                ],
                evidence_required=["sar_filings", "investigation_reports"]
            )
        ]
        
        # Store all requirements
        for req in pci_requirements + gdpr_requirements + bsa_requirements:
            self.requirements[req.requirement_id] = req
    
    def _initialize_templates(self):
        """Initialize report templates for different jurisdictions"""
        self.report_templates = {
            Jurisdiction.US_FEDERAL.value: {
                "name": "US Federal Compliance Report",
                "regulations": ["PCI DSS", "BSA/AML", "SOX"],
                "sections": [
                    "executive_summary",
                    "regulatory_overview",
                    "compliance_status",
                    "audit_findings",
                    "risk_assessment",
                    "remediation_plan",
                    "certifications"
                ],
                "required_signatures": ["compliance_officer", "ceo", "auditor"]
            },
            Jurisdiction.EU.value: {
                "name": "EU GDPR Compliance Report",
                "regulations": ["GDPR", "PSD2"],
                "sections": [
                    "executive_summary",
                    "data_protection_overview",
                    "processing_activities",
                    "data_subject_rights",
                    "security_measures",
                    "breach_incidents",
                    "dpo_assessment"
                ],
                "required_signatures": ["dpo", "data_controller"]
            },
            Jurisdiction.UK.value: {
                "name": "UK Financial Compliance Report",
                "regulations": ["UK GDPR", "FCA Requirements"],
                "sections": [
                    "executive_summary",
                    "regulatory_compliance",
                    "financial_controls",
                    "customer_protection",
                    "operational_resilience",
                    "governance"
                ],
                "required_signatures": ["compliance_officer", "cfo"]
            },
            Jurisdiction.GLOBAL.value: {
                "name": "Global Compliance Summary",
                "regulations": ["PCI DSS", "ISO 27001"],
                "sections": [
                    "executive_summary",
                    "multi_jurisdiction_overview",
                    "global_compliance_status",
                    "regional_variations",
                    "harmonization_efforts"
                ],
                "required_signatures": ["global_compliance_head"]
            }
        }
    
    def _initialize_metrics(self):
        """Initialize compliance monitoring metrics"""
        metrics = [
            ComplianceMetric(
                metric_id="overall_compliance_score",
                name="Overall Compliance Score",
                description="Aggregate compliance score across all regulations",
                current_value=0.0,
                threshold=0.95,
                status="pending",
                timestamp=datetime.now().isoformat()
            ),
            ComplianceMetric(
                metric_id="audit_trail_completeness",
                name="Audit Trail Completeness",
                description="Percentage of transactions with complete audit trails",
                current_value=0.0,
                threshold=0.99,
                status="pending",
                timestamp=datetime.now().isoformat()
            ),
            ComplianceMetric(
                metric_id="data_breach_response_time",
                name="Data Breach Response Time",
                description="Average time to respond to data breaches (hours)",
                current_value=0.0,
                threshold=72.0,
                status="pending",
                timestamp=datetime.now().isoformat()
            ),
            ComplianceMetric(
                metric_id="policy_violation_rate",
                name="Policy Violation Rate",
                description="Percentage of transactions with policy violations",
                current_value=0.0,
                threshold=0.01,
                status="pending",
                timestamp=datetime.now().isoformat()
            )
        ]
        
        for metric in metrics:
            self.metrics[metric.metric_id] = metric

    def validate_requirement(
        self,
        requirement_id: str,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a regulatory requirement with provided evidence
        
        Args:
            requirement_id: ID of requirement to validate
            evidence: Evidence data for validation
            
        Returns:
            Validation result
        """
        if requirement_id not in self.requirements:
            return {
                "success": False,
                "error": f"Requirement {requirement_id} not found"
            }
        
        requirement = self.requirements[requirement_id]
        validation_results = []
        passed_criteria = 0
        
        # Validate each criterion
        for criterion in requirement.validation_criteria:
            # Simple validation logic - can be extended
            criterion_met = self._check_criterion(criterion, evidence)
            validation_results.append({
                "criterion": criterion,
                "met": criterion_met
            })
            if criterion_met:
                passed_criteria += 1
        
        # Calculate compliance score
        compliance_score = passed_criteria / len(requirement.validation_criteria) if requirement.validation_criteria else 0.0
        
        # Update requirement status
        requirement.compliance_score = compliance_score
        requirement.last_validated = datetime.now().isoformat()
        
        if compliance_score >= 1.0:
            requirement.status = ComplianceStatus.COMPLIANT.value
        elif compliance_score >= 0.7:
            requirement.status = ComplianceStatus.PARTIAL.value
        else:
            requirement.status = ComplianceStatus.NON_COMPLIANT.value
        
        return {
            "success": True,
            "requirement_id": requirement_id,
            "compliance_score": compliance_score,
            "status": requirement.status,
            "validation_results": validation_results,
            "timestamp": requirement.last_validated
        }
    
    def _check_criterion(self, criterion: str, evidence: Dict[str, Any]) -> bool:
        """Check if a validation criterion is met"""
        # Simplified validation - in production, this would be more sophisticated
        criterion_lower = criterion.lower()
        
        # Check for encryption-related criteria
        if "encrypt" in criterion_lower:
            return evidence.get("encryption_enabled", False)
        
        # Check for logging-related criteria
        if "log" in criterion_lower:
            return evidence.get("logging_enabled", False) and evidence.get("log_count", 0) > 0
        
        # Check for consent-related criteria
        if "consent" in criterion_lower:
            return evidence.get("consent_obtained", False)
        
        # Check for deletion-related criteria
        if "deletion" in criterion_lower or "erasure" in criterion_lower:
            return evidence.get("deletion_mechanism", False)
        
        # Check for notification-related criteria
        if "notification" in criterion_lower or "breach" in criterion_lower:
            return evidence.get("notification_system", False)
        
        # Check for transaction monitoring
        if "transaction" in criterion_lower and "monitor" in criterion_lower:
            return evidence.get("monitoring_active", False)
        
        # Default: check if criterion keyword exists in evidence
        return any(key.lower() in criterion_lower for key in evidence.keys())
    
    def generate_report(
        self,
        jurisdiction: Jurisdiction,
        start_date: datetime,
        end_date: datetime,
        audit_data: Dict[str, Any],
        format: ReportFormat = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """
        Generate compliance report for specified jurisdiction
        
        Args:
            jurisdiction: Regulatory jurisdiction
            start_date: Report period start
            end_date: Report period end
            audit_data: Audit trail and compliance data
            format: Output format
            
        Returns:
            Generated report
        """
        template = self.report_templates.get(jurisdiction.value, self.report_templates[Jurisdiction.GLOBAL.value])
        
        # Filter requirements for this jurisdiction
        relevant_requirements = [
            req for req in self.requirements.values()
            if req.jurisdiction == jurisdiction.value or req.jurisdiction == Jurisdiction.GLOBAL.value
        ]
        
        # Calculate overall compliance
        if relevant_requirements:
            overall_score = sum(req.compliance_score for req in relevant_requirements) / len(relevant_requirements)
        else:
            overall_score = 0.0
        
        # Build report structure
        report = {
            "report_id": f"COMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "jurisdiction": jurisdiction.value,
            "template": template["name"],
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "generated_at": datetime.now().isoformat(),
            "overall_compliance_score": overall_score,
            "status": self._determine_overall_status(overall_score),
            "sections": {}
        }
        
        # Generate each section
        for section in template["sections"]:
            report["sections"][section] = self._generate_section(
                section, relevant_requirements, audit_data
            )
        
        # Add requirements summary
        report["requirements_summary"] = {
            "total": len(relevant_requirements),
            "compliant": sum(1 for r in relevant_requirements if r.status == ComplianceStatus.COMPLIANT.value),
            "partial": sum(1 for r in relevant_requirements if r.status == ComplianceStatus.PARTIAL.value),
            "non_compliant": sum(1 for r in relevant_requirements if r.status == ComplianceStatus.NON_COMPLIANT.value),
            "pending": sum(1 for r in relevant_requirements if r.status == "pending")
        }
        
        # Add metrics
        report["metrics"] = {
            metric_id: metric.to_dict()
            for metric_id, metric in self.metrics.items()
        }
        
        # Add active alerts
        report["active_alerts"] = [
            alert.to_dict() for alert in self.alerts if not alert.resolved
        ]
        
        # Save report
        self._save_report(report, format)
        
        return report
    
    def _determine_overall_status(self, score: float) -> str:
        """Determine overall compliance status from score"""
        if score >= 0.95:
            return ComplianceStatus.COMPLIANT.value
        elif score >= 0.7:
            return ComplianceStatus.PARTIAL.value
        else:
            return ComplianceStatus.NON_COMPLIANT.value
    
    def _generate_section(
        self,
        section_name: str,
        requirements: List[RegulatoryRequirement],
        audit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a specific report section"""
        if section_name == "executive_summary":
            return self._generate_executive_summary(requirements, audit_data)
        elif section_name == "regulatory_overview":
            return self._generate_regulatory_overview(requirements)
        elif section_name == "compliance_status":
            return self._generate_compliance_status(requirements)
        elif section_name == "audit_findings":
            return self._generate_audit_findings(audit_data)
        elif section_name == "risk_assessment":
            return self._generate_risk_assessment(requirements, audit_data)
        elif section_name == "remediation_plan":
            return self._generate_remediation_plan(requirements)
        else:
            return {"section": section_name, "content": "Section content placeholder"}
    
    def _generate_executive_summary(
        self,
        requirements: List[RegulatoryRequirement],
        audit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary section"""
        compliant_count = sum(1 for r in requirements if r.status == ComplianceStatus.COMPLIANT.value)
        total_count = len(requirements)
        
        return {
            "overview": f"Compliance assessment covering {total_count} regulatory requirements",
            "compliance_rate": f"{compliant_count}/{total_count} requirements met",
            "key_findings": [
                f"{compliant_count} requirements fully compliant",
                f"{sum(1 for r in requirements if r.status == ComplianceStatus.PARTIAL.value)} requirements partially compliant",
                f"{sum(1 for r in requirements if r.status == ComplianceStatus.NON_COMPLIANT.value)} requirements non-compliant"
            ],
            "audit_events_reviewed": audit_data.get("total_events", 0),
            "period_covered": audit_data.get("period", "N/A")
        }
    
    def _generate_regulatory_overview(
        self,
        requirements: List[RegulatoryRequirement]
    ) -> Dict[str, Any]:
        """Generate regulatory overview section"""
        regulations = {}
        for req in requirements:
            if req.regulation not in regulations:
                regulations[req.regulation] = {
                    "total_requirements": 0,
                    "compliant": 0,
                    "requirements": []
                }
            regulations[req.regulation]["total_requirements"] += 1
            if req.status == ComplianceStatus.COMPLIANT.value:
                regulations[req.regulation]["compliant"] += 1
            regulations[req.regulation]["requirements"].append({
                "id": req.requirement_id,
                "title": req.title,
                "status": req.status,
                "score": req.compliance_score
            })
        
        return {
            "regulations_covered": list(regulations.keys()),
            "regulation_details": regulations
        }
    
    def _generate_compliance_status(
        self,
        requirements: List[RegulatoryRequirement]
    ) -> Dict[str, Any]:
        """Generate compliance status section"""
        return {
            "requirements": [
                {
                    "id": req.requirement_id,
                    "regulation": req.regulation,
                    "title": req.title,
                    "status": req.status,
                    "compliance_score": req.compliance_score,
                    "last_validated": req.last_validated,
                    "mandatory": req.mandatory
                }
                for req in requirements
            ]
        }
    
    def _generate_audit_findings(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate audit findings section"""
        return {
            "total_events": audit_data.get("total_events", 0),
            "events_by_type": audit_data.get("by_event_type", {}),
            "events_by_severity": audit_data.get("by_severity", {}),
            "integrity_verified": audit_data.get("integrity_check", {}).get("verified", False),
            "key_findings": audit_data.get("key_findings", [])
        }
    
    def _generate_risk_assessment(
        self,
        requirements: List[RegulatoryRequirement],
        audit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate risk assessment section"""
        high_risk_requirements = [
            req for req in requirements
            if req.mandatory and req.status != ComplianceStatus.COMPLIANT.value
        ]
        
        return {
            "overall_risk_level": "high" if high_risk_requirements else "low",
            "high_risk_requirements": len(high_risk_requirements),
            "risk_factors": [
                {
                    "requirement": req.requirement_id,
                    "title": req.title,
                    "risk_level": "high" if req.mandatory else "medium",
                    "status": req.status
                }
                for req in high_risk_requirements
            ],
            "mitigation_priority": "immediate" if high_risk_requirements else "routine"
        }
    
    def _generate_remediation_plan(
        self,
        requirements: List[RegulatoryRequirement]
    ) -> Dict[str, Any]:
        """Generate remediation plan section"""
        non_compliant = [
            req for req in requirements
            if req.status in [ComplianceStatus.NON_COMPLIANT.value, ComplianceStatus.PARTIAL.value]
        ]
        
        remediation_items = []
        for req in non_compliant:
            remediation_items.append({
                "requirement_id": req.requirement_id,
                "title": req.title,
                "current_status": req.status,
                "priority": "high" if req.mandatory else "medium",
                "recommended_actions": [
                    f"Review {criterion}" for criterion in req.validation_criteria
                ],
                "estimated_timeline": "30 days" if req.mandatory else "90 days"
            })
        
        return {
            "total_items": len(remediation_items),
            "high_priority": sum(1 for item in remediation_items if item["priority"] == "high"),
            "items": remediation_items
        }
    
    def _save_report(self, report: Dict[str, Any], format: ReportFormat):
        """Save report to storage"""
        filename = f"{report['report_id']}.{format.value}"
        filepath = self.storage_path / filename
        
        if format == ReportFormat.JSON:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
        elif format == ReportFormat.HTML:
            html_content = self._generate_html_report(report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        # PDF and CSV formats would require additional libraries
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML formatted report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report - {report['report_id']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e8f4f8; border-radius: 5px; }}
        .compliant {{ color: green; }}
        .non-compliant {{ color: red; }}
        .partial {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Compliance Report</h1>
    <div class="summary">
        <p><strong>Report ID:</strong> {report['report_id']}</p>
        <p><strong>Jurisdiction:</strong> {report['jurisdiction']}</p>
        <p><strong>Period:</strong> {report['period']['start']} to {report['period']['end']}</p>
        <p><strong>Overall Compliance Score:</strong> {report['overall_compliance_score']:.2%}</p>
        <p><strong>Status:</strong> <span class="{report['status']}">{report['status']}</span></p>
    </div>
    
    <h2>Requirements Summary</h2>
    <div class="metric">
        <strong>Total:</strong> {report['requirements_summary']['total']}
    </div>
    <div class="metric">
        <strong class="compliant">Compliant:</strong> {report['requirements_summary']['compliant']}
    </div>
    <div class="metric">
        <strong class="partial">Partial:</strong> {report['requirements_summary']['partial']}
    </div>
    <div class="metric">
        <strong class="non-compliant">Non-Compliant:</strong> {report['requirements_summary']['non_compliant']}
    </div>
    
    <h2>Report Sections</h2>
    <p>Detailed sections available in JSON format</p>
</body>
</html>
"""
        return html
    
    def monitor_compliance(self, audit_data: Dict[str, Any]) -> List[ComplianceAlert]:
        """
        Real-time compliance monitoring and alerting
        
        Args:
            audit_data: Current audit and compliance data
            
        Returns:
            List of generated alerts
        """
        new_alerts = []
        
        # Update metrics
        self._update_metrics(audit_data)
        
        # Check each metric against thresholds
        for metric_id, metric in self.metrics.items():
            if self._is_threshold_violated(metric):
                alert = self._create_alert(metric)
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        # Check requirement compliance
        for req_id, req in self.requirements.items():
            if req.mandatory and req.status == ComplianceStatus.NON_COMPLIANT.value:
                alert = ComplianceAlert(
                    alert_id=f"ALERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{req_id}",
                    severity="critical",
                    title=f"Mandatory Requirement Non-Compliant: {req.title}",
                    description=f"Requirement {req_id} is mandatory but currently non-compliant",
                    requirement_id=req_id,
                    triggered_at=datetime.now().isoformat()
                )
                new_alerts.append(alert)
                self.alerts.append(alert)
        
        return new_alerts
    
    def _update_metrics(self, audit_data: Dict[str, Any]):
        """Update compliance metrics with current data"""
        # Update overall compliance score
        if self.requirements:
            overall_score = sum(req.compliance_score for req in self.requirements.values()) / len(self.requirements)
            self.metrics["overall_compliance_score"].current_value = overall_score
            self.metrics["overall_compliance_score"].timestamp = datetime.now().isoformat()
            self.metrics["overall_compliance_score"].status = "compliant" if overall_score >= 0.95 else "non_compliant"
        
        # Update audit trail completeness
        if audit_data.get("total_events"):
            completeness = audit_data.get("complete_trails", 0) / audit_data["total_events"]
            self.metrics["audit_trail_completeness"].current_value = completeness
            self.metrics["audit_trail_completeness"].timestamp = datetime.now().isoformat()
            self.metrics["audit_trail_completeness"].status = "compliant" if completeness >= 0.99 else "non_compliant"
        
        # Update policy violation rate
        if audit_data.get("total_transactions"):
            violation_rate = audit_data.get("violations", 0) / audit_data["total_transactions"]
            self.metrics["policy_violation_rate"].current_value = violation_rate
            self.metrics["policy_violation_rate"].timestamp = datetime.now().isoformat()
            self.metrics["policy_violation_rate"].status = "compliant" if violation_rate <= 0.01 else "non_compliant"
    
    def _is_threshold_violated(self, metric: ComplianceMetric) -> bool:
        """Check if metric threshold is violated"""
        if metric.name == "Data Breach Response Time":
            # Lower is better
            return metric.current_value > metric.threshold
        else:
            # Higher is better for most metrics
            return metric.current_value < metric.threshold
    
    def _create_alert(self, metric: ComplianceMetric) -> ComplianceAlert:
        """Create alert from metric threshold violation"""
        severity = "critical" if metric.current_value < metric.threshold * 0.8 else "high"
        
        return ComplianceAlert(
            alert_id=f"ALERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{metric.metric_id}",
            severity=severity,
            title=f"Compliance Metric Threshold Violated: {metric.name}",
            description=f"{metric.name} is {metric.current_value:.2f}, threshold is {metric.threshold:.2f}",
            requirement_id=None,
            triggered_at=datetime.now().isoformat()
        )
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[ComplianceAlert]:
        """
        Get active compliance alerts
        
        Args:
            severity: Filter by severity level
            
        Returns:
            List of active alerts
        """
        active = [alert for alert in self.alerts if not alert.resolved]
        
        if severity:
            active = [alert for alert in active if alert.severity == severity]
        
        return active
    
    def resolve_alert(self, alert_id: str, resolution_notes: str):
        """
        Resolve a compliance alert
        
        Args:
            alert_id: Alert ID to resolve
            resolution_notes: Notes about resolution
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolution_notes = resolution_notes
                break
    
    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """
        Get real-time compliance dashboard data
        
        Returns:
            Dashboard data with metrics and alerts
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": self._determine_overall_status(
                self.metrics["overall_compliance_score"].current_value
            ),
            "metrics": {
                metric_id: metric.to_dict()
                for metric_id, metric in self.metrics.items()
            },
            "active_alerts": {
                "total": len([a for a in self.alerts if not a.resolved]),
                "critical": len([a for a in self.alerts if not a.resolved and a.severity == "critical"]),
                "high": len([a for a in self.alerts if not a.resolved and a.severity == "high"]),
                "alerts": [a.to_dict() for a in self.alerts if not a.resolved]
            },
            "requirements_status": {
                "total": len(self.requirements),
                "compliant": sum(1 for r in self.requirements.values() if r.status == ComplianceStatus.COMPLIANT.value),
                "non_compliant": sum(1 for r in self.requirements.values() if r.status == ComplianceStatus.NON_COMPLIANT.value),
                "partial": sum(1 for r in self.requirements.values() if r.status == ComplianceStatus.PARTIAL.value)
            }
        }
