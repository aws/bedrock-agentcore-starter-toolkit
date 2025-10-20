"""
Compliance Agent

Specialized agent for regulatory compliance checking, audit trail generation,
automated report creation, and policy enforcement for fraud detection systems.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import os
import sys

# Ensure project root is on sys.path when running this file directly
# This allows absolute imports like `memory_system` to resolve when the
# working directory is not the repository root.
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from base_agent import BaseAgent, AgentConfiguration, AgentCapability, ProcessingResult
from src.models import Transaction, DecisionContext, FraudDecision
from src.memory_manager import MemoryManager

# Mark imported models as intentionally used (prevents unused-import warnings)
_ = (Transaction, DecisionContext, FraudDecision)

logger = logging.getLogger(__name__)

class ComplianceRegulation(Enum):
    """Supported compliance regulations."""
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    SOX = "sox"
    BSA_AML = "bsa_aml"
    FFIEC = "ffiec"
    PSD2 = "psd2"
    CCPA = "ccpa"


class AuditEventType(Enum):
    """Types of audit events."""
    TRANSACTION_PROCESSED = "transaction_processed"
    DECISION_MADE = "decision_made"
    POLICY_VIOLATION = "policy_violation"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"


class ComplianceStatus(Enum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class AuditEvent:
    """Audit trail event record."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str]
    transaction_id: Optional[str]
    agent_id: str
    event_description: str
    event_data: Dict[str, Any] = field(default_factory=dict)
    compliance_tags: List[str] = field(default_factory=list)
    data_hash: Optional[str] = None
    
    def __post_init__(self):
        """Generate data hash for integrity verification."""
        if not self.data_hash:
            data_str = json.dumps({
                "event_id": self.event_id,
                "event_type": self.event_type.value,
                "timestamp": self.timestamp.isoformat(),
                "event_description": self.event_description,
                "event_data": self.event_data
            }, sort_keys=True)
            self.data_hash = hashlib.sha256(data_str.encode()).hexdigest()


@dataclass
class ComplianceCheck:
    """Individual compliance check result."""
    regulation: ComplianceRegulation
    check_name: str
    status: ComplianceStatus
    description: str
    requirements: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical
@dataclass
class ComplianceReport:
    """Compliance assessment report."""
    report_id: str
    report_type: str
    generation_timestamp: datetime
    reporting_period_start: datetime
    reporting_period_end: datetime
    regulations_covered: List[ComplianceRegulation]
    compliance_checks: List[ComplianceCheck] = field(default_factory=list)
    overall_compliance_score: float = 0.0
    summary_statistics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    audit_events_count: int = 0


@dataclass
class PolicyViolation:
    """Policy violation record."""
    violation_id: str
    policy_name: str
    violation_type: str
    severity: str
    description: str
    transaction_id: Optional[str]
    user_id: Optional[str]
    timestamp: datetime
    resolution_status: str = "open"  # open, investigating, resolved
    resolution_notes: Optional[str] = None


class ComplianceAgent(BaseAgent):
    """
    Specialized agent for regulatory compliance and audit management.
    
    Capabilities:
    - Regulatory compliance checking
    - Audit trail generation and management
    - Automated report creation for regulatory authorities
    - Policy enforcement and violation detection
    - Data retention and privacy compliance
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        config: Optional[AgentConfiguration] = None
    ):
        """
        Initialize the Compliance Agent.
        
        Args:
            memory_manager: Memory manager for data access
            config: Agent configuration (optional)
        """
        if config is None:
            config = AgentConfiguration(
                agent_id="compliance_agent_001",
                agent_name="ComplianceAgent",
                version="1.0.0",
                capabilities=[
                    AgentCapability.COMPLIANCE_CHECKING,
                    AgentCapability.REAL_TIME_PROCESSING,
                    AgentCapability.BATCH_PROCESSING
                ],
                max_concurrent_requests=20,
                timeout_seconds=30,
                custom_parameters={
                    "audit_retention_days": 2555,  # 7 years
                    "report_generation_enabled": True,
                    "real_time_monitoring": True,
                    "supported_regulations": [
                        ComplianceRegulation.PCI_DSS.value,
                        ComplianceRegulation.GDPR.value,
                        ComplianceRegulation.BSA_AML.value
                    ]
                }
            )
        
        self.memory_manager = memory_manager
        
        # Audit trail storage
        self.audit_events = []
        self.policy_violations = []
        
        # Compliance policies and rules
        self.compliance_policies = {}
        self.regulatory_requirements = {}
        
        super().__init__(config)
    
    def _initialize_agent(self) -> None:
        """Initialize compliance agent specific components."""
        self.logger.info("Initializing Compliance Agent")
        
        # Initialize compliance policies
        self._initialize_compliance_policies()
        
        # Initialize regulatory requirements
        self._initialize_regulatory_requirements()
        
        # Initialize audit trail system
        self._initialize_audit_system()
        
        self.logger.info("Compliance Agent initialized successfully")
    
    def process_request(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process a compliance request.
        
        Args:
            request_data: Dictionary containing compliance request data
            
        Returns:
            ProcessingResult with compliance analysis
        """
        try:
            request_type = request_data.get("request_type", "compliance_check")
            
            if request_type == "compliance_check":
                return self._process_compliance_check(request_data)
            elif request_type == "audit_event":
                return self._process_audit_event(request_data)
            elif request_type == "generate_report":
                return self._process_report_generation(request_data)
            elif request_type == "policy_check":
                return self._process_policy_check(request_data)
            else:
                return ProcessingResult(
                    success=False,
                    result_data={},
                    processing_time_ms=0.0,
                    confidence_score=0.0,
                    error_message=f"Unknown request type: {request_type}"
                )
                
        except Exception as e:
            self.logger.error(f"Error processing compliance request: {str(e)}")
            return ProcessingResult(
                success=False,
                result_data={},
                processing_time_ms=0.0,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _process_compliance_check(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """Process compliance check request."""
        transaction_data = request_data.get("transaction")
        decision_data = request_data.get("decision_context")
        regulations = request_data.get("regulations", ["pci_dss", "gdpr"])
        
        compliance_checks = []
        
        for regulation_str in regulations:
            try:
                regulation = ComplianceRegulation(regulation_str)
                check_result = self._perform_compliance_check(
                    regulation, transaction_data, decision_data
                )
                compliance_checks.append(check_result)
            except ValueError:
                self.logger.warning(f"Unknown regulation: {regulation_str}")
        
        # Calculate overall compliance score
        if compliance_checks:
            compliant_count = sum(1 for check in compliance_checks 
                                if check.status == ComplianceStatus.COMPLIANT)
            overall_score = compliant_count / len(compliance_checks)
        else:
            overall_score = 0.0
        
        # Log audit event
        self._log_audit_event(
            AuditEventType.SYSTEM_EVENT,
            "Compliance check performed",
            transaction_id=transaction_data.get("id") if transaction_data else None,
            event_data={
                "regulations_checked": regulations,
                "compliance_score": overall_score
            }
        )
        
        return ProcessingResult(
            success=True,
            result_data={
                "compliance_checks": [check.__dict__ for check in compliance_checks],
                "overall_compliance_score": overall_score,
                "timestamp": datetime.now().isoformat()
            },
            processing_time_ms=0.0,
            confidence_score=overall_score,
            metadata={
                "agent_type": "compliance_agent",
                "regulations_checked": len(compliance_checks)
            }
        )
    
    def _process_audit_event(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """Process audit event logging request."""
        event_type_str = request_data.get("event_type", "system_event")
        description = request_data.get("description", "")
        transaction_id = request_data.get("transaction_id")
        user_id = request_data.get("user_id")
        event_data = request_data.get("event_data", {})
        
        try:
            event_type = AuditEventType(event_type_str)
        except ValueError:
            event_type = AuditEventType.SYSTEM_EVENT
        
        audit_event = self._log_audit_event(
            event_type, description, user_id, transaction_id, event_data
        )
        
        return ProcessingResult(
            success=True,
            result_data={
                "audit_event": audit_event.__dict__,
                "event_logged": True
            },
            processing_time_ms=0.0,
            confidence_score=1.0,
            metadata={"agent_type": "compliance_agent"}
        )
    
    def _process_report_generation(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """Process compliance report generation request."""
        report_type = request_data.get("report_type", "compliance_summary")
        start_date_str = request_data.get("start_date")
        end_date_str = request_data.get("end_date")
        regulations = request_data.get("regulations", ["pci_dss", "gdpr"])
        
        # Parse dates
        try:
            start_date = datetime.fromisoformat(start_date_str) if start_date_str else datetime.now() - timedelta(days=30)
            end_date = datetime.fromisoformat(end_date_str) if end_date_str else datetime.now()
        except ValueError:
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
        
        # Generate report
        report = self._generate_compliance_report(
            report_type, start_date, end_date, regulations
        )
        
        # Log audit event
        self._log_audit_event(
            AuditEventType.SYSTEM_EVENT,
            f"Compliance report generated: {report_type}",
            event_data={
                "report_id": report.report_id,
                "report_type": report_type,
                "period": f"{start_date.date()} to {end_date.date()}"
            }
        )
        
        return ProcessingResult(
            success=True,
            result_data={
                "report": report.__dict__,
                "report_generated": True
            },
            processing_time_ms=0.0,
            confidence_score=1.0,
            metadata={"agent_type": "compliance_agent"}
        )
    
    def _process_policy_check(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """Process policy violation check request."""
        transaction_data = request_data.get("transaction")
        decision_data = request_data.get("decision_context")
        
        violations = self._check_policy_violations(transaction_data, decision_data)
        
        # Log violations
        for violation in violations:
            self._log_audit_event(
                AuditEventType.POLICY_VIOLATION,
                f"Policy violation detected: {violation.policy_name}",
                user_id=violation.user_id,
                transaction_id=violation.transaction_id,
                event_data={
                    "violation_id": violation.violation_id,
                    "policy_name": violation.policy_name,
                    "severity": violation.severity
                }
            )
        
        return ProcessingResult(
            success=True,
            result_data={
                "policy_violations": [v.__dict__ for v in violations],
                "violations_count": len(violations),
                "has_violations": len(violations) > 0
            },
            processing_time_ms=0.0,
            confidence_score=1.0 if len(violations) == 0 else 0.5,
            metadata={"agent_type": "compliance_agent"}
        )
    
    def _initialize_compliance_policies(self) -> None:
        """Initialize compliance policies and rules."""
        self.compliance_policies = {
            "transaction_limits": {
                "daily_limit": 10000.00,
                "single_transaction_limit": 5000.00,
                "velocity_limit": 5,  # transactions per hour
                "cross_border_limit": 2000.00
            },
            "data_retention": {
                "transaction_data_days": 2555,  # 7 years
                "audit_log_days": 2555,
                "user_data_days": 1825,  # 5 years
                "decision_context_days": 2555
            },
            "privacy_protection": {
                "pii_encryption_required": True,
                "data_anonymization_required": True,
                "consent_tracking_required": True,
                "right_to_deletion_supported": True
            },
            "access_control": {
                "multi_factor_auth_required": True,
                "role_based_access": True,
                "audit_all_access": True,
                "session_timeout_minutes": 30
            }
        }
        
        self.logger.info("Compliance policies initialized")
    
    def _initialize_regulatory_requirements(self) -> None:
        """Initialize regulatory requirements for different compliance frameworks."""
        self.regulatory_requirements = {
            ComplianceRegulation.PCI_DSS: {
                "requirements": [
                    "Install and maintain a firewall configuration",
                    "Do not use vendor-supplied defaults for system passwords",
                    "Protect stored cardholder data",
                    "Encrypt transmission of cardholder data across open networks",
                    "Protect all systems against malware",
                    "Develop and maintain secure systems and applications",
                    "Restrict access to cardholder data by business need to know",
                    "Identify and authenticate access to system components",
                    "Restrict physical access to cardholder data",
                    "Track and monitor all access to network resources",
                    "Regularly test security systems and processes",
                    "Maintain a policy that addresses information security"
                ],
                "data_protection": ["card_number", "expiry_date", "cvv"],
                "audit_requirements": ["access_logs", "transaction_logs", "security_events"]
            },
            ComplianceRegulation.GDPR: {
                "requirements": [
                    "Lawful basis for processing personal data",
                    "Data subject consent management",
                    "Right to access personal data",
                    "Right to rectification of personal data",
                    "Right to erasure (right to be forgotten)",
                    "Right to restrict processing",
                    "Right to data portability",
                    "Right to object to processing",
                    "Data protection by design and by default",
                    "Data breach notification within 72 hours"
                ],
                "data_protection": ["personal_identifiers", "financial_data", "location_data"],
                "audit_requirements": ["consent_records", "data_processing_logs", "breach_notifications"]
            },
            ComplianceRegulation.BSA_AML: {
                "requirements": [
                    "Customer identification program (CIP)",
                    "Suspicious activity reporting (SAR)",
                    "Currency transaction reporting (CTR)",
                    "Record keeping requirements",
                    "Anti-money laundering program",
                    "Beneficial ownership identification",
                    "Enhanced due diligence for high-risk customers",
                    "Ongoing monitoring of customer relationships"
                ],
                "data_protection": ["customer_identity", "transaction_patterns", "risk_assessments"],
                "audit_requirements": ["sar_filings", "ctr_reports", "customer_due_diligence"]
            },
            ComplianceRegulation.SOX: {
                "requirements": [
                    "Internal controls over financial reporting",
                    "Management assessment of internal controls",
                    "Auditor attestation of internal controls",
                    "Disclosure controls and procedures",
                    "Code of ethics for senior financial officers",
                    "Whistleblower protection",
                    "Document retention policies",
                    "Certification of financial statements"
                ],
                "data_protection": ["financial_statements", "internal_controls", "audit_evidence"],
                "audit_requirements": ["control_testing", "deficiency_tracking", "remediation_evidence"]
            }
        }
        
        self.logger.info("Regulatory requirements initialized")
    
    def _initialize_audit_system(self) -> None:
        """Initialize audit trail system."""
        # Initialize audit event storage
        self.audit_events = []
        self.policy_violations = []
        
        # Log system initialization
        self._log_audit_event(
            AuditEventType.SYSTEM_EVENT,
            "Compliance Agent audit system initialized",
            event_data={"agent_version": self.config.version}
        )
        
        self.logger.info("Audit system initialized")
    
    def _perform_compliance_check(
        self,
        regulation: ComplianceRegulation,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> ComplianceCheck:
        """
        Perform compliance check for a specific regulation.
        
        Args:
            regulation: Compliance regulation to check
            transaction_data: Transaction data to validate
            decision_data: Decision context data
            
        Returns:
            ComplianceCheck result
        """
        check_name = f"{regulation.value}_compliance_check"
        requirements = self.regulatory_requirements.get(regulation, {}).get("requirements", [])
        violations = []
        recommendations = []
        status = ComplianceStatus.COMPLIANT
        
        if regulation == ComplianceRegulation.PCI_DSS:
            violations, recommendations = self._check_pci_dss_compliance(transaction_data, decision_data)
        elif regulation == ComplianceRegulation.GDPR:
            violations, recommendations = self._check_gdpr_compliance(transaction_data, decision_data)
        elif regulation == ComplianceRegulation.BSA_AML:
            violations, recommendations = self._check_bsa_aml_compliance(transaction_data, decision_data)
        elif regulation == ComplianceRegulation.SOX:
            violations, recommendations = self._check_sox_compliance(transaction_data, decision_data)
        
        # Determine compliance status
        if violations:
            critical_violations = [v for v in violations if "critical" in v.lower()]
            if critical_violations:
                status = ComplianceStatus.NON_COMPLIANT
            else:
                status = ComplianceStatus.WARNING
        
        return ComplianceCheck(
            regulation=regulation,
            check_name=check_name,
            status=status,
            description=f"Compliance check for {regulation.value}",
            requirements=requirements,
            violations=violations,
            recommendations=recommendations,
            severity="high" if status == ComplianceStatus.NON_COMPLIANT else "medium"
        )
    
    def _check_pci_dss_compliance(
        self,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """Check PCI DSS compliance requirements."""
        violations = []
        recommendations = []
        
        if transaction_data:
            # Check for sensitive card data exposure
            sensitive_fields = ["card_number", "cvv", "pin"]
            for field in sensitive_fields:
                if field in transaction_data and not self._is_data_encrypted(transaction_data.get(field)):
                    violations.append(f"Unencrypted {field} detected in transaction data")
                    recommendations.append(f"Encrypt {field} data before storage or transmission")
            
            # Check transaction amount limits
            amount = transaction_data.get("amount", 0)
            if amount > self.compliance_policies["transaction_limits"]["single_transaction_limit"]:
                violations.append(f"Transaction amount {amount} exceeds single transaction limit")
                recommendations.append("Implement additional verification for high-value transactions")
        
        if decision_data:
            # Check audit trail completeness
            required_audit_fields = ["decision_timestamp", "decision_reason", "agent_id"]
            for field in required_audit_fields:
                if field not in decision_data:
                    violations.append(f"Missing required audit field: {field}")
                    recommendations.append(f"Ensure {field} is logged for all decisions")
        
        return violations, recommendations
    
    def _check_gdpr_compliance(
        self,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """Check GDPR compliance requirements."""
        violations = []
        recommendations = []
        
        if transaction_data:
            # Check for personal data processing consent
            user_id = transaction_data.get("user_id")
            if user_id and not self._has_processing_consent(user_id):
                violations.append(f"No processing consent found for user {user_id}")
                recommendations.append("Obtain explicit consent before processing personal data")
            
            # Check for data minimization
            pii_fields = ["email", "phone", "address", "name"]
            unnecessary_pii = []
            for field in pii_fields:
                if field in transaction_data and not self._is_pii_necessary(field, "fraud_detection"):
                    unnecessary_pii.append(field)
            
            if unnecessary_pii:
                violations.append(f"Unnecessary PII fields detected: {', '.join(unnecessary_pii)}")
                recommendations.append("Remove unnecessary PII fields to comply with data minimization")
        
        if decision_data:
            # Check for automated decision-making disclosure
            if decision_data.get("automated_decision") and not decision_data.get("human_review_available"):
                violations.append("Automated decision without human review option")
                recommendations.append("Provide option for human review of automated decisions")
        
        return violations, recommendations
    
    def _check_bsa_aml_compliance(
        self,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """Check BSA/AML compliance requirements."""
        violations = []
        recommendations = []
        
        if transaction_data:
            amount = transaction_data.get("amount", 0)
            
            # Check for CTR reporting threshold
            if amount >= 10000:
                if not self._has_ctr_filing(transaction_data):
                    violations.append(f"CTR filing required for transaction amount {amount}")
                    recommendations.append("File Currency Transaction Report (CTR) for transactions ≥ $10,000")
            
            # Check for suspicious activity patterns
            user_id = transaction_data.get("user_id")
            if user_id and self._is_suspicious_pattern(user_id, transaction_data):
                if not self._has_sar_filing(user_id):
                    violations.append(f"Suspicious activity detected for user {user_id} without SAR filing")
                    recommendations.append("File Suspicious Activity Report (SAR) for detected patterns")
            
            # Check customer identification
            if not self._has_customer_identification(user_id):
                violations.append(f"Incomplete customer identification for user {user_id}")
                recommendations.append("Complete Customer Identification Program (CIP) requirements")
        
        return violations, recommendations
    
    def _check_sox_compliance(
        self,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """Check SOX compliance requirements."""
        violations = []
        recommendations = []
        
        if decision_data:
            # Check for proper internal controls
            if not decision_data.get("control_validation"):
                violations.append("Missing internal control validation for financial decision")
                recommendations.append("Implement control validation for all financial decisions")
            
            # Check for segregation of duties
            if decision_data.get("decision_maker") == decision_data.get("reviewer"):
                violations.append("Segregation of duties violation - same person making and reviewing decision")
                recommendations.append("Ensure different individuals make and review financial decisions")
            
            # Check for proper documentation
            required_docs = ["decision_rationale", "supporting_evidence", "approval_chain"]
            missing_docs = [doc for doc in required_docs if doc not in decision_data]
            if missing_docs:
                violations.append(f"Missing required documentation: {', '.join(missing_docs)}")
                recommendations.append("Maintain complete documentation for all financial decisions")
        
        return violations, recommendations
    
    def _log_audit_event(
        self,
        event_type: AuditEventType,
        description: str,
        user_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            description: Event description
            user_id: Associated user ID
            transaction_id: Associated transaction ID
            event_data: Additional event data
            
        Returns:
            AuditEvent object
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            transaction_id=transaction_id,
            agent_id=self.config.agent_id,
            event_description=description,
            event_data=event_data or {},
            compliance_tags=self._get_compliance_tags(event_type, event_data)
        )
        
        # Store audit event
        self.audit_events.append(event)
        
        # Log to system logger
        self.logger.info(f"Audit event logged: {event.event_id} - {description}")
        
        return event
    
    def _check_policy_violations(
        self,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> List[PolicyViolation]:
        """
        Check for policy violations in transaction or decision data.
        
        Args:
            transaction_data: Transaction data to check
            decision_data: Decision context data to check
            
        Returns:
            List of PolicyViolation objects
        """
        violations = []
        
        if transaction_data:
            user_id = transaction_data.get("user_id")
            transaction_id = transaction_data.get("id")
            amount = transaction_data.get("amount", 0)
            
            # Check transaction limits
            daily_limit = self.compliance_policies["transaction_limits"]["daily_limit"]
            single_limit = self.compliance_policies["transaction_limits"]["single_transaction_limit"]
            
            if amount > single_limit:
                violations.append(PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_name="single_transaction_limit",
                    violation_type="amount_limit_exceeded",
                    severity="high",
                    description=f"Transaction amount {amount} exceeds single transaction limit {single_limit}",
                    transaction_id=transaction_id,
                    user_id=user_id,
                    timestamp=datetime.now()
                ))
            
            # Check velocity limits
            if self._check_velocity_violation(user_id):
                violations.append(PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_name="velocity_limit",
                    violation_type="velocity_exceeded",
                    severity="medium",
                    description=f"User {user_id} exceeded velocity limits",
                    transaction_id=transaction_id,
                    user_id=user_id,
                    timestamp=datetime.now()
                ))
            
            # Check cross-border limits
            if self._is_cross_border_transaction(transaction_data):
                cross_border_limit = self.compliance_policies["transaction_limits"]["cross_border_limit"]
                if amount > cross_border_limit:
                    violations.append(PolicyViolation(
                        violation_id=str(uuid.uuid4()),
                        policy_name="cross_border_limit",
                        violation_type="cross_border_limit_exceeded",
                        severity="medium",
                        description=f"Cross-border transaction amount {amount} exceeds limit {cross_border_limit}",
                        transaction_id=transaction_id,
                        user_id=user_id,
                        timestamp=datetime.now()
                    ))
        
        if decision_data:
            # Check access control violations
            if not self._validate_access_controls(decision_data):
                violations.append(PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_name="access_control",
                    violation_type="unauthorized_access",
                    severity="critical",
                    description="Access control validation failed",
                    transaction_id=decision_data.get("transaction_id"),
                    user_id=decision_data.get("user_id"),
                    timestamp=datetime.now()
                ))
        
        # Store violations
        self.policy_violations.extend(violations)
        
        return violations
    
    def _generate_compliance_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        regulations: List[str]
    ) -> ComplianceReport:
        """
        Generate compliance report for specified period and regulations.
        
        Args:
            report_type: Type of report to generate
            start_date: Report period start date
            end_date: Report period end date
            regulations: List of regulations to include
            
        Returns:
            ComplianceReport object
        """
        report_id = str(uuid.uuid4())
        
        # Filter audit events for the period
        period_events = [
            event for event in self.audit_events
            if start_date <= event.timestamp <= end_date
        ]
        
        # Perform compliance checks for each regulation
        compliance_checks = []
        regulation_enums = []
        
        for reg_str in regulations:
            try:
                regulation = ComplianceRegulation(reg_str)
                regulation_enums.append(regulation)
                
                # Perform aggregate compliance check
                check = self._perform_aggregate_compliance_check(regulation, period_events)
                compliance_checks.append(check)
                
            except ValueError:
                self.logger.warning(f"Unknown regulation: {reg_str}")
        
        # Calculate overall compliance score
        if compliance_checks:
            compliant_count = sum(1 for check in compliance_checks 
                                if check.status == ComplianceStatus.COMPLIANT)
            overall_score = compliant_count / len(compliance_checks)
        else:
            overall_score = 0.0
        
        # Generate summary statistics
        summary_stats = {
            "total_audit_events": len(period_events),
            "policy_violations": len([e for e in period_events 
                                   if e.event_type == AuditEventType.POLICY_VIOLATION]),
            "transactions_processed": len([e for e in period_events 
                                        if e.event_type == AuditEventType.TRANSACTION_PROCESSED]),
            "decisions_made": len([e for e in period_events 
                                 if e.event_type == AuditEventType.DECISION_MADE]),
            "compliance_checks_performed": len(compliance_checks),
            "regulations_assessed": len(regulation_enums)
        }
        
        # Generate recommendations
        recommendations = self._generate_compliance_recommendations(compliance_checks)
        
        return ComplianceReport(
            report_id=report_id,
            report_type=report_type,
            generation_timestamp=datetime.now(),
            reporting_period_start=start_date,
            reporting_period_end=end_date,
            regulations_covered=regulation_enums,
            compliance_checks=compliance_checks,
            overall_compliance_score=overall_score,
            summary_statistics=summary_stats,
            recommendations=recommendations,
            audit_events_count=len(period_events)
        )
    
    def get_audit_trail(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> List[AuditEvent]:
        """
        Retrieve audit trail with optional filters.
        
        Args:
            start_date: Filter events after this date
            end_date: Filter events before this date
            event_type: Filter by event type
            user_id: Filter by user ID
            transaction_id: Filter by transaction ID
            
        Returns:
            List of AuditEvent objects
        """
        filtered_events = self.audit_events.copy()
        
        # Apply filters
        if start_date:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_date]
        
        if end_date:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_date]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if transaction_id:
            filtered_events = [e for e in filtered_events if e.transaction_id == transaction_id]
        
        # Sort by timestamp (most recent first)
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return filtered_events
    
    def get_policy_violations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[PolicyViolation]:
        """
        Retrieve policy violations with optional filters.
        
        Args:
            start_date: Filter violations after this date
            end_date: Filter violations before this date
            severity: Filter by severity level
            status: Filter by resolution status
            
        Returns:
            List of PolicyViolation objects
        """
        filtered_violations = self.policy_violations.copy()
        
        # Apply filters
        if start_date:
            filtered_violations = [v for v in filtered_violations if v.timestamp >= start_date]
        
        if end_date:
            filtered_violations = [v for v in filtered_violations if v.timestamp <= end_date]
        
        if severity:
            filtered_violations = [v for v in filtered_violations if v.severity == severity]
        
        if status:
            filtered_violations = [v for v in filtered_violations if v.resolution_status == status]
        
        # Sort by timestamp (most recent first)
        filtered_violations.sort(key=lambda x: x.timestamp, reverse=True)
        
        return filtered_violations
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of audit trail data.
        
        Returns:
            Dict containing integrity verification results
        """
        integrity_results = {
            "total_events": len(self.audit_events),
            "verified_events": 0,
            "corrupted_events": 0,
            "missing_hashes": 0,
            "integrity_score": 0.0,
            "corrupted_event_ids": []
        }
        
        for event in self.audit_events:
            if not event.data_hash:
                integrity_results["missing_hashes"] += 1
                continue
            
            # Recalculate hash and compare
            data_str = json.dumps({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "event_description": event.event_description,
                "event_data": event.event_data
            }, sort_keys=True)
            
            calculated_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            if calculated_hash == event.data_hash:
                integrity_results["verified_events"] += 1
            else:
                integrity_results["corrupted_events"] += 1
                integrity_results["corrupted_event_ids"].append(event.event_id)
        
        # Calculate integrity score
        total_checkable = integrity_results["total_events"] - integrity_results["missing_hashes"]
        if total_checkable > 0:
            integrity_results["integrity_score"] = integrity_results["verified_events"] / total_checkable
        
        return integrity_results
    
    def _log_audit_event_duplicate(
        self,
        event_type: AuditEventType,
        description: str,
        user_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log an audit event (duplicate method - should be removed).
        
        Args:
            event_type: Type of audit event
            description: Event description
            user_id: Associated user ID (optional)
            transaction_id: Associated transaction ID (optional)
            event_data: Additional event data (optional)
            
        Returns:
            AuditEvent that was logged
        """
        audit_event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            transaction_id=transaction_id,
            agent_id=self.config.agent_id,
            event_description=description,
            event_data=event_data or {},
            compliance_tags=self._get_compliance_tags(event_type, event_data)
        )
        
        # Store audit event
        self.audit_events.append(audit_event)
        
        # Log to system logger
        self.logger.info(f"Audit event logged: {audit_event.event_id} - {description}")
        
        return audit_event
    
    def _check_policy_violations(
        self,
        transaction_data: Optional[Dict[str, Any]],
        decision_data: Optional[Dict[str, Any]]
    ) -> List[PolicyViolation]:
        """
        Check for policy violations.
        
        Args:
            transaction_data: Transaction data to check
            decision_data: Decision context data
            
        Returns:
            List of policy violations found
        """
        violations = []
        
        if transaction_data:
            # Check transaction limit policies
            amount = transaction_data.get("amount", 0)
            if amount > self.compliance_policies["transaction_limits"]["single_transaction_limit"]:
                violations.append(PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_name="single_transaction_limit",
                    violation_type="amount_exceeded",
                    severity="high",
                    description=f"Transaction amount {amount} exceeds limit",
                    transaction_id=transaction_data.get("id"),
                    user_id=transaction_data.get("user_id"),
                    timestamp=datetime.now()
                ))
            
            # Check velocity policies
            user_id = transaction_data.get("user_id")
            if user_id and self._check_velocity_violation(user_id):
                violations.append(PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_name="velocity_limit",
                    violation_type="transaction_frequency",
                    severity="medium",
                    description="Transaction velocity limit exceeded",
                    transaction_id=transaction_data.get("id"),
                    user_id=user_id,
                    timestamp=datetime.now()
                ))
            
            # Check cross-border policies
            if self._is_cross_border_transaction(transaction_data):
                if amount > self.compliance_policies["transaction_limits"]["cross_border_limit"]:
                    violations.append(PolicyViolation(
                        violation_id=str(uuid.uuid4()),
                        policy_name="cross_border_limit",
                        violation_type="cross_border_amount",
                        severity="high",
                        description=f"Cross-border transaction amount {amount} exceeds limit",
                        transaction_id=transaction_data.get("id"),
                        user_id=transaction_data.get("user_id"),
                        timestamp=datetime.now()
                    ))
        
        if decision_data:
            # Check access control policies
            if not self._validate_access_controls(decision_data):
                violations.append(PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    policy_name="access_control",
                    violation_type="unauthorized_access",
                    severity="critical",
                    description="Access control policy violation detected",
                    transaction_id=decision_data.get("transaction_id"),
                    user_id=decision_data.get("user_id"),
                    timestamp=datetime.now()
                ))
        
        return violations
    
    def _generate_compliance_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        regulations: List[str]
    ) -> ComplianceReport:
        """
        Generate compliance report.
        
        Args:
            report_type: Type of report to generate
            start_date: Report period start date
            end_date: Report period end date
            regulations: List of regulations to include
            
        Returns:
            ComplianceReport
        """
        report_id = str(uuid.uuid4())
        
        # Filter audit events by date range
        period_events = [
            event for event in self.audit_events
            if start_date <= event.timestamp <= end_date
        ]
        
        # Generate compliance checks for each regulation
        compliance_checks = []
        for reg_str in regulations:
            try:
                regulation = ComplianceRegulation(reg_str)
                # Perform aggregate compliance check for the period
                check = self._perform_aggregate_compliance_check(regulation, period_events)
                compliance_checks.append(check)
            except ValueError:
                self.logger.warning(f"Unknown regulation in report: {reg_str}")
        
        # Calculate overall compliance score
        if compliance_checks:
            compliant_count = sum(1 for check in compliance_checks 
                                if check.status == ComplianceStatus.COMPLIANT)
            overall_score = compliant_count / len(compliance_checks)
        else:
            overall_score = 0.0
        
        # Generate summary statistics
        summary_stats = {
            "total_audit_events": len(period_events),
            "policy_violations": len([v for v in self.policy_violations 
                                   if start_date <= v.timestamp <= end_date]),
            "compliance_checks_performed": len(compliance_checks),
            "regulations_assessed": len(regulations),
            "period_days": (end_date - start_date).days
        }
        
        # Generate recommendations
        recommendations = self._generate_compliance_recommendations(compliance_checks)
        
        return ComplianceReport(
            report_id=report_id,
            report_type=report_type,
            generation_timestamp=datetime.now(),
            reporting_period_start=start_date,
            reporting_period_end=end_date,
            regulations_covered=[ComplianceRegulation(reg) for reg in regulations],
            compliance_checks=compliance_checks,
            overall_compliance_score=overall_score,
            summary_statistics=summary_stats,
            recommendations=recommendations,
            audit_events_count=len(period_events)
        )
    
    # Helper methods for compliance checking
    def _is_data_encrypted(self, data: Any) -> bool:
        """Check if data appears to be encrypted."""
        if not isinstance(data, str):
            return False
        # Simple heuristic - encrypted data typically doesn't contain readable patterns
        return len(data) > 20 and not any(char.isalpha() for char in data[:10])
    
    def _has_processing_consent(self, user_id: str) -> bool:
        """Check if user has given consent for data processing."""
        # In a real implementation, this would check a consent database
        return True  # Placeholder implementation
    
    def _is_pii_necessary(self, field: str, purpose: str) -> bool:
        """Check if PII field is necessary for the given purpose."""
        necessary_fields = {
            "fraud_detection": ["user_id", "transaction_amount", "merchant", "location"]
        }
        return field in necessary_fields.get(purpose, [])
    
    def _has_ctr_filing(self, transaction_data: Dict[str, Any]) -> bool:
        """Check if CTR has been filed for transaction."""
        # Placeholder implementation
        return False
    
    def _is_suspicious_pattern(self, user_id: str, transaction_data: Dict[str, Any]) -> bool:
        """Check if transaction shows suspicious patterns."""
        # Placeholder implementation - would use pattern detection logic
        return False
    
    def _has_sar_filing(self, user_id: str) -> bool:
        """Check if SAR has been filed for user."""
        # Placeholder implementation
        return False
    
    def _has_customer_identification(self, user_id: str) -> bool:
        """Check if customer identification is complete."""
        # Placeholder implementation
        return True
    
    def _check_velocity_violation(self, user_id: str) -> bool:
        """Check if user has exceeded velocity limits."""
        # Placeholder implementation
        return False
    
    def _is_cross_border_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """Check if transaction is cross-border."""
        # Placeholder implementation
        return transaction_data.get("merchant_country") != transaction_data.get("user_country")
    
    def _validate_access_controls(self, decision_data: Dict[str, Any]) -> bool:
        """Validate access control policies."""
        # Placeholder implementation
        return True
    
    def _get_compliance_tags(self, event_type: AuditEventType, event_data: Optional[Dict[str, Any]]) -> List[str]:
        """Get compliance tags for audit event."""
        tags = []
        
        if event_type == AuditEventType.TRANSACTION_PROCESSED:
            tags.extend(["pci_dss", "bsa_aml"])
        elif event_type == AuditEventType.POLICY_VIOLATION:
            tags.extend(["compliance_violation", "audit_required"])
        elif event_type == AuditEventType.DATA_ACCESS:
            tags.extend(["gdpr", "data_protection"])
        
        return tags
    
    def _perform_aggregate_compliance_check(
        self,
        regulation: ComplianceRegulation,
        events: List[AuditEvent]
    ) -> ComplianceCheck:
        """Perform aggregate compliance check for a regulation over a period."""
        violations = []
        recommendations = []
        
        # Analyze events for compliance violations
        violation_events = [e for e in events if e.event_type == AuditEventType.POLICY_VIOLATION]
        
        if violation_events:
            violations.append(f"Found {len(violation_events)} policy violations in period")
            recommendations.append("Review and address policy violations")
        
        # Check audit trail completeness
        required_events = [AuditEventType.TRANSACTION_PROCESSED, AuditEventType.DECISION_MADE]
        for event_type in required_events:
            event_count = len([e for e in events if e.event_type == event_type])
            if event_count == 0:
                violations.append(f"No {event_type.value} events found in audit trail")
                recommendations.append(f"Ensure {event_type.value} events are properly logged")
        
        status = ComplianceStatus.NON_COMPLIANT if violations else ComplianceStatus.COMPLIANT
        
        return ComplianceCheck(
            regulation=regulation,
            check_name=f"{regulation.value}_aggregate_check",
            status=status,
            description=f"Aggregate compliance check for {regulation.value}",
            requirements=self.regulatory_requirements.get(regulation, {}).get("requirements", []),
            violations=violations,
            recommendations=recommendations,
            severity="high" if violations else "low"
        )
    
    def _generate_compliance_recommendations(self, compliance_checks: List[ComplianceCheck]) -> List[str]:
        """Generate compliance recommendations based on check results."""
        recommendations = []
        
        # Collect all recommendations from checks
        for check in compliance_checks:
            recommendations.extend(check.recommendations)
        
        # Add general recommendations
        non_compliant_checks = [c for c in compliance_checks if c.status == ComplianceStatus.NON_COMPLIANT]
        if non_compliant_checks:
            recommendations.append("Prioritize addressing non-compliant regulations")
            recommendations.append("Implement regular compliance monitoring")
        
        warning_checks = [c for c in compliance_checks if c.status == ComplianceStatus.WARNING]
        if warning_checks:
            recommendations.append("Review and address compliance warnings")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations