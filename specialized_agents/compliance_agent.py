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
from memory_system.models import Transaction, DecisionContext, FraudDecision
from memory_system.memory_manager import MemoryManager

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