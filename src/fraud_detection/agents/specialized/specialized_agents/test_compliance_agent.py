"""
Unit tests for the Compliance Agent.
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from compliance_agent import (
    ComplianceAgent, ComplianceRegulation, AuditEventType, ComplianceStatus,
    AuditEvent, ComplianceCheck, ComplianceReport, PolicyViolation
)
from base_agent import AgentConfiguration, AgentCapability
from src.models import Transaction, DecisionContext, FraudDecision, Location, DeviceInfo


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager for testing."""
    return Mock()


@pytest.fixture
def compliance_agent(mock_memory_manager):
    """Create a compliance agent for testing."""
    config = AgentConfiguration(
        agent_id="test_compliance_agent",
        agent_name="TestComplianceAgent",
        version="1.0.0",
        capabilities=[
            AgentCapability.COMPLIANCE_CHECKING,
            AgentCapability.REAL_TIME_PROCESSING
        ]
    )
    return ComplianceAgent(mock_memory_manager, config)


@pytest.fixture
def sample_transaction_data():
    """Create sample transaction data for testing."""
    return {
        "id": "tx_123456",
        "user_id": "user_789",
        "amount": 150.00,
        "currency": "USD",
        "merchant": "Amazon",
        "category": "online_retail",
        "location": {
            "country": "US",
            "city": "New York"
        },
        "timestamp": datetime.now().isoformat(),
        "card_type": "credit"
    }


@pytest.fixture
def sample_decision_data():
    """Create sample decision context data for testing."""
    return {
        "transaction_id": "tx_123456",
        "user_id": "user_789",
        "decision": "approved",
        "confidence_score": 0.85,
        "reasoning_steps": ["Amount within normal range", "Merchant frequently used"],
        "timestamp": datetime.now().isoformat(),
        "agent_version": "1.0.0"
    }


class TestComplianceAgent:
    """Test cases for ComplianceAgent functionality."""
    
    def test_agent_initialization(self, compliance_agent):
        """Test that compliance agent initializes correctly."""
        assert compliance_agent.config.agent_name == "TestComplianceAgent"
        assert compliance_agent.config.version == "1.0.0"
        assert AgentCapability.COMPLIANCE_CHECKING in compliance_agent.config.capabilities
        
        # Check that policies are initialized
        assert "transaction_limits" in compliance_agent.compliance_policies
        assert "data_retention" in compliance_agent.compliance_policies
        
        # Check that regulatory requirements are initialized
        assert ComplianceRegulation.PCI_DSS in compliance_agent.regulatory_requirements
        assert ComplianceRegulation.GDPR in compliance_agent.regulatory_requirements
    
    def test_compliance_check_request(self, compliance_agent, sample_transaction_data, sample_decision_data):
        """Test compliance check processing."""
        request_data = {
            "request_type": "compliance_check",
            "transaction": sample_transaction_data,
            "decision_context": sample_decision_data,
            "regulations": ["pci_dss", "gdpr"]
        }
        
        result = compliance_agent.process_request(request_data)
        
        assert result.success is True
        assert "compliance_checks" in result.result_data
        assert "overall_compliance_score" in result.result_data
        assert len(result.result_data["compliance_checks"]) == 2
        
        # Check that audit event was logged
        assert len(compliance_agent.audit_events) > 0
        audit_event = compliance_agent.audit_events[-1]
        assert audit_event.event_type == AuditEventType.SYSTEM_EVENT
        assert "Compliance check performed" in audit_event.event_description
    
    def test_audit_event_logging(self, compliance_agent):
        """Test audit event logging functionality."""
        request_data = {
            "request_type": "audit_event",
            "event_type": "transaction_processed",
            "description": "Test transaction processed",
            "transaction_id": "tx_123",
            "user_id": "user_456",
            "event_data": {"amount": 100.0}
        }
        
        result = compliance_agent.process_request(request_data)
        
        assert result.success is True
        assert result.result_data["event_logged"] is True
        
        # Verify audit event was stored
        assert len(compliance_agent.audit_events) > 0
        audit_event = compliance_agent.audit_events[-1]
        assert audit_event.event_type == AuditEventType.TRANSACTION_PROCESSED
        assert audit_event.transaction_id == "tx_123"
        assert audit_event.user_id == "user_456"
        assert audit_event.data_hash is not None
    
    def test_report_generation(self, compliance_agent):
        """Test compliance report generation."""
        # Add some audit events first
        compliance_agent._log_audit_event(
            AuditEventType.TRANSACTION_PROCESSED,
            "Test transaction",
            transaction_id="tx_1"
        )
        compliance_agent._log_audit_event(
            AuditEventType.DECISION_MADE,
            "Test decision",
            transaction_id="tx_1"
        )
        
        request_data = {
            "request_type": "generate_report",
            "report_type": "compliance_summary",
            "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
            "end_date": datetime.now().isoformat(),
            "regulations": ["pci_dss", "gdpr"]
        }
        
        result = compliance_agent.process_request(request_data)
        
        assert result.success is True
        assert "report" in result.result_data
        
        report_data = result.result_data["report"]
        assert report_data["report_type"] == "compliance_summary"
        assert "compliance_checks" in report_data
        assert "overall_compliance_score" in report_data
        assert "summary_statistics" in report_data
    
    def test_policy_violation_check(self, compliance_agent, sample_transaction_data, sample_decision_data):
        """Test policy violation detection."""
        # Create transaction that exceeds limits
        high_amount_transaction = sample_transaction_data.copy()
        high_amount_transaction["amount"] = 10000.0  # Exceeds single transaction limit
        
        request_data = {
            "request_type": "policy_check",
            "transaction": high_amount_transaction,
            "decision_context": sample_decision_data
        }
        
        result = compliance_agent.process_request(request_data)
        
        assert result.success is True
        assert result.result_data["has_violations"] is True
        assert len(result.result_data["policy_violations"]) > 0
        
        violation = result.result_data["policy_violations"][0]
        assert violation["policy_name"] == "single_transaction_limit"
        assert violation["severity"] == "high"
    
    def test_pci_dss_compliance_check(self, compliance_agent, sample_transaction_data, sample_decision_data):
        """Test PCI DSS specific compliance checks."""
        # Add unencrypted card data to trigger violation
        transaction_with_card_data = sample_transaction_data.copy()
        transaction_with_card_data["card_number"] = "4111111111111111"  # Unencrypted
        
        check = compliance_agent._perform_compliance_check(
            ComplianceRegulation.PCI_DSS,
            transaction_with_card_data,
            sample_decision_data
        )
        
        assert check.regulation == ComplianceRegulation.PCI_DSS
        assert len(check.violations) > 0
        assert any("card_number" in violation for violation in check.violations)
        assert len(check.recommendations) > 0
    
    def test_gdpr_compliance_check(self, compliance_agent, sample_transaction_data, sample_decision_data):
        """Test GDPR specific compliance checks."""
        # Mock consent check to return False
        with patch.object(compliance_agent, '_has_processing_consent', return_value=False):
            check = compliance_agent._perform_compliance_check(
                ComplianceRegulation.GDPR,
                sample_transaction_data,
                sample_decision_data
            )
        
        assert check.regulation == ComplianceRegulation.GDPR
        assert len(check.violations) > 0
        assert any("consent" in violation.lower() for violation in check.violations)
    
    def test_bsa_aml_compliance_check(self, compliance_agent, sample_transaction_data, sample_decision_data):
        """Test BSA/AML specific compliance checks."""
        # Create high-value transaction requiring CTR
        high_value_transaction = sample_transaction_data.copy()
        high_value_transaction["amount"] = 15000.0  # Above CTR threshold
        
        check = compliance_agent._perform_compliance_check(
            ComplianceRegulation.BSA_AML,
            high_value_transaction,
            sample_decision_data
        )
        
        assert check.regulation == ComplianceRegulation.BSA_AML
        assert len(check.violations) > 0
        assert any("CTR" in violation for violation in check.violations)
    
    def test_audit_trail_retrieval(self, compliance_agent):
        """Test audit trail retrieval with filters."""
        # Add multiple audit events
        compliance_agent._log_audit_event(
            AuditEventType.TRANSACTION_PROCESSED,
            "Transaction 1",
            user_id="user_1",
            transaction_id="tx_1"
        )
        compliance_agent._log_audit_event(
            AuditEventType.DECISION_MADE,
            "Decision 1",
            user_id="user_1",
            transaction_id="tx_1"
        )
        compliance_agent._log_audit_event(
            AuditEventType.POLICY_VIOLATION,
            "Violation 1",
            user_id="user_2",
            transaction_id="tx_2"
        )
        
        # Test retrieval without filters
        all_events = compliance_agent.get_audit_trail()
        assert len(all_events) >= 3
        
        # Test retrieval with user filter
        user_events = compliance_agent.get_audit_trail(user_id="user_1")
        assert len(user_events) == 2
        assert all(event.user_id == "user_1" for event in user_events)
        
        # Test retrieval with event type filter
        violation_events = compliance_agent.get_audit_trail(event_type=AuditEventType.POLICY_VIOLATION)
        assert len(violation_events) >= 1
        assert all(event.event_type == AuditEventType.POLICY_VIOLATION for event in violation_events)
    
    def test_policy_violations_retrieval(self, compliance_agent, sample_transaction_data):
        """Test policy violations retrieval with filters."""
        # Create violations
        violations = compliance_agent._check_policy_violations(sample_transaction_data, None)
        
        # Add a high-amount transaction to create violation
        high_amount_data = sample_transaction_data.copy()
        high_amount_data["amount"] = 10000.0
        more_violations = compliance_agent._check_policy_violations(high_amount_data, None)
        
        # Test retrieval without filters
        all_violations = compliance_agent.get_policy_violations()
        assert len(all_violations) >= len(more_violations)
        
        # Test retrieval with severity filter
        high_severity_violations = compliance_agent.get_policy_violations(severity="high")
        assert all(v.severity == "high" for v in high_severity_violations)
    
    def test_audit_integrity_verification(self, compliance_agent):
        """Test audit trail integrity verification."""
        # Add some audit events
        compliance_agent._log_audit_event(
            AuditEventType.TRANSACTION_PROCESSED,
            "Test transaction",
            transaction_id="tx_1"
        )
        compliance_agent._log_audit_event(
            AuditEventType.DECISION_MADE,
            "Test decision",
            transaction_id="tx_1"
        )
        
        # Verify integrity
        integrity_results = compliance_agent.verify_audit_integrity()
        
        assert integrity_results["total_events"] >= 2
        assert integrity_results["verified_events"] >= 2
        assert integrity_results["corrupted_events"] == 0
        assert integrity_results["integrity_score"] > 0.0
        
        # Test with corrupted data
        if compliance_agent.audit_events:
            # Corrupt the first event's hash
            compliance_agent.audit_events[0].data_hash = "corrupted_hash"
            
            integrity_results = compliance_agent.verify_audit_integrity()
            assert integrity_results["corrupted_events"] >= 1
            assert len(integrity_results["corrupted_event_ids"]) >= 1
    
    def test_compliance_tags_generation(self, compliance_agent):
        """Test compliance tags generation for audit events."""
        # Test transaction processed event
        tags = compliance_agent._get_compliance_tags(
            AuditEventType.TRANSACTION_PROCESSED,
            {"amount": 100.0}
        )
        assert "pci_dss" in tags
        assert "bsa_aml" in tags
        
        # Test policy violation event
        tags = compliance_agent._get_compliance_tags(
            AuditEventType.POLICY_VIOLATION,
            {"violation_type": "amount_limit"}
        )
        assert "compliance_violation" in tags
        assert "audit_required" in tags
        
        # Test data access event
        tags = compliance_agent._get_compliance_tags(
            AuditEventType.DATA_ACCESS,
            {"data_type": "personal"}
        )
        assert "gdpr" in tags
        assert "data_protection" in tags
    
    def test_unknown_request_type(self, compliance_agent):
        """Test handling of unknown request types."""
        request_data = {
            "request_type": "unknown_request",
            "data": "test"
        }
        
        result = compliance_agent.process_request(request_data)
        
        assert result.success is False
        assert "Unknown request type" in result.error_message
    
    def test_error_handling(self, compliance_agent):
        """Test error handling in compliance agent."""
        # Test with malformed request data
        request_data = {
            "request_type": "compliance_check",
            "transaction": None,  # Invalid transaction data
            "regulations": ["invalid_regulation"]
        }
        
        result = compliance_agent.process_request(request_data)
        
        # Should handle gracefully and not crash
        assert isinstance(result.success, bool)
        assert isinstance(result.result_data, dict)
    
    def test_compliance_report_statistics(self, compliance_agent):
        """Test compliance report statistics calculation."""
        # Add various types of audit events
        compliance_agent._log_audit_event(
            AuditEventType.TRANSACTION_PROCESSED,
            "Transaction 1"
        )
        compliance_agent._log_audit_event(
            AuditEventType.DECISION_MADE,
            "Decision 1"
        )
        compliance_agent._log_audit_event(
            AuditEventType.POLICY_VIOLATION,
            "Violation 1"
        )
        
        # Generate report
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        
        report = compliance_agent._generate_compliance_report(
            "test_report",
            start_date,
            end_date,
            ["pci_dss"]
        )
        
        assert report.report_type == "test_report"
        assert report.audit_events_count >= 3
        assert report.summary_statistics["total_audit_events"] >= 3
        assert report.summary_statistics["policy_violations"] >= 1
        assert report.summary_statistics["transactions_processed"] >= 1
        assert report.summary_statistics["decisions_made"] >= 1
    
    def test_data_encryption_check(self, compliance_agent):
        """Test data encryption validation."""
        # Test with unencrypted data
        assert not compliance_agent._is_data_encrypted("plain_text_data")
        
        # Test with encrypted-looking data (base64 or hex)
        assert compliance_agent._is_data_encrypted("YWJjZGVmZ2hpams=")  # base64
        assert compliance_agent._is_data_encrypted("a1b2c3d4e5f6")  # hex-like
    
    def test_similarity_calculation(self, compliance_agent, sample_transaction_data):
        """Test transaction similarity calculation for compliance patterns."""
        # Create similar transaction
        similar_transaction = sample_transaction_data.copy()
        similar_transaction["amount"] = 155.0  # Slightly different amount
        
        # This would be used in pattern detection for compliance
        # The actual similarity calculation would be in the memory manager
        # but we can test the compliance agent's use of it
        
        # Test that compliance agent can handle similar transaction analysis
        request_data = {
            "request_type": "compliance_check",
            "transaction": similar_transaction,
            "regulations": ["pci_dss"]
        }
        
        result = compliance_agent.process_request(request_data)
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__])