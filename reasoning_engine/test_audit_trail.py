"""
Tests for Comprehensive Audit Trail System
"""

import pytest
import json
import gzip
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from audit_trail import (
    AuditTrailSystem,
    AuditEventType,
    AuditSeverity,
    AuditEntry
)


@pytest.fixture
def temp_audit_dir():
    """Create temporary directory for audit logs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def audit_system(temp_audit_dir):
    """Create audit trail system instance"""
    return AuditTrailSystem(storage_path=temp_audit_dir, enable_compression=False)


@pytest.fixture
def audit_system_compressed(temp_audit_dir):
    """Create audit trail system with compression"""
    return AuditTrailSystem(storage_path=temp_audit_dir, enable_compression=True)


class TestAuditEntry:
    """Test audit entry creation and serialization"""
    
    def test_audit_entry_creation(self):
        """Test creating audit entry"""
        entry = AuditEntry(
            timestamp="2024-01-01T12:00:00",
            event_type=AuditEventType.DECISION_MADE.value,
            severity=AuditSeverity.COMPLIANCE.value,
            transaction_id="txn_123",
            user_id="user_456",
            agent_id="risk_agent",
            action="fraud_decision",
            details={"amount": 1000},
            reasoning_steps=["step1", "step2"],
            decision="APPROVED",
            confidence=0.95,
            evidence=["evidence1"],
            previous_hash="abc123",
            entry_hash="def456"
        )
        
        assert entry.transaction_id == "txn_123"
        assert entry.decision == "APPROVED"
        assert entry.confidence == 0.95
    
    def test_audit_entry_to_dict(self):
        """Test converting audit entry to dictionary"""
        entry = AuditEntry(
            timestamp="2024-01-01T12:00:00",
            event_type=AuditEventType.DECISION_MADE.value,
            severity=AuditSeverity.INFO.value,
            transaction_id="txn_123",
            user_id=None,
            agent_id=None,
            action="test_action",
            details={},
            reasoning_steps=None,
            decision=None,
            confidence=None,
            evidence=None,
            previous_hash="abc",
            entry_hash="def"
        )
        
        entry_dict = entry.to_dict()
        assert isinstance(entry_dict, dict)
        assert entry_dict["transaction_id"] == "txn_123"
        assert entry_dict["event_type"] == AuditEventType.DECISION_MADE.value


class TestAuditTrailSystem:
    """Test audit trail system functionality"""
    
    def test_initialization(self, temp_audit_dir):
        """Test audit system initialization"""
        system = AuditTrailSystem(storage_path=temp_audit_dir)
        
        assert system.storage_path.exists()
        assert system.previous_hash == "0" * 64
        assert system.entries_count == 0
    
    def test_log_event_basic(self, audit_system):
        """Test logging basic audit event"""
        entry = audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="transaction_received",
            details={"amount": 500, "currency": "USD"},
            transaction_id="txn_001"
        )
        
        assert entry.transaction_id == "txn_001"
        assert entry.event_type == AuditEventType.TRANSACTION_RECEIVED.value
        assert entry.severity == AuditSeverity.INFO.value
        assert entry.entry_hash is not None
        assert len(entry.entry_hash) == 64
    
    def test_log_event_with_decision(self, audit_system):
        """Test logging decision event"""
        entry = audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.COMPLIANCE,
            action="fraud_decision",
            details={"risk_score": 0.85},
            transaction_id="txn_002",
            user_id="user_123",
            agent_id="risk_agent",
            reasoning_steps=["Check amount", "Check location", "Assess risk"],
            decision="FLAGGED",
            confidence=0.85,
            evidence=["High amount", "Unusual location"]
        )
        
        assert entry.decision == "FLAGGED"
        assert entry.confidence == 0.85
        assert len(entry.reasoning_steps) == 3
        assert len(entry.evidence) == 2
    
    def test_hash_chain_integrity(self, audit_system):
        """Test hash chain for tamper detection"""
        # Log multiple events
        entry1 = audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="event1",
            details={}
        )
        
        entry2 = audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event2",
            details={}
        )
        
        entry3 = audit_system.log_event(
            event_type=AuditEventType.AGENT_ACTION,
            severity=AuditSeverity.INFO,
            action="event3",
            details={}
        )
        
        # Verify hash chain
        assert entry1.previous_hash == "0" * 64
        assert entry2.previous_hash == entry1.entry_hash
        assert entry3.previous_hash == entry2.entry_hash
    
    def test_write_entry_uncompressed(self, audit_system):
        """Test writing entries without compression"""
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="test_write",
            details={"test": "data"}
        )
        
        # Check file was created
        log_files = list(audit_system.storage_path.glob("audit_log_*.jsonl"))
        assert len(log_files) == 1
        
        # Verify content
        with open(log_files[0], 'r') as f:
            content = f.read()
            assert "test_write" in content
    
    def test_write_entry_compressed(self, audit_system_compressed):
        """Test writing entries with compression"""
        audit_system_compressed.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="test_compressed",
            details={"test": "data"}
        )
        
        # Check compressed file was created
        log_files = list(audit_system_compressed.storage_path.glob("audit_log_*.jsonl.gz"))
        assert len(log_files) == 1
        
        # Verify content
        with gzip.open(log_files[0], 'rt') as f:
            content = f.read()
            assert "test_compressed" in content
    
    def test_log_rotation(self, audit_system):
        """Test log file rotation"""
        audit_system.max_entries_per_file = 5
        
        # Log more entries than max
        for i in range(12):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action=f"event_{i}",
                details={}
            )
        
        # Should have created multiple files
        log_files = list(audit_system.storage_path.glob("audit_log_*.jsonl"))
        assert len(log_files) >= 2


class TestAuditIntegrity:
    """Test audit trail integrity verification"""
    
    def test_verify_integrity_valid(self, audit_system):
        """Test integrity verification with valid logs"""
        # Log some events
        for i in range(5):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action=f"event_{i}",
                details={}
            )
        
        # Verify integrity
        result = audit_system.verify_integrity()
        
        assert result["verified"] is True
        assert result["total_entries"] == 5
        assert len(result["tampered_entries"]) == 0
    
    def test_verify_integrity_tampered(self, audit_system):
        """Test integrity verification with tampered logs"""
        # Log some events
        for i in range(3):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action=f"event_{i}",
                details={}
            )
        
        # Tamper with log file
        log_files = list(audit_system.storage_path.glob("audit_log_*.jsonl"))
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
        
        # Modify second entry
        entry = json.loads(lines[1])
        entry["details"]["tampered"] = True
        lines[1] = json.dumps(entry) + '\n'
        
        with open(log_files[0], 'w') as f:
            f.writelines(lines)
        
        # Verify integrity - should detect tampering
        result = audit_system.verify_integrity()
        
        assert result["verified"] is False
        assert len(result["tampered_entries"]) > 0


class TestAuditSearch:
    """Test audit trail search functionality"""
    
    def test_search_by_transaction_id(self, audit_system):
        """Test searching by transaction ID"""
        # Log events for different transactions
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="event1",
            details={},
            transaction_id="txn_001"
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event2",
            details={},
            transaction_id="txn_001"
        )
        
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="event3",
            details={},
            transaction_id="txn_002"
        )
        
        # Search for specific transaction
        results = audit_system.search_entries(transaction_id="txn_001")
        
        assert len(results) == 2
        assert all(e["transaction_id"] == "txn_001" for e in results)
    
    def test_search_by_user_id(self, audit_system):
        """Test searching by user ID"""
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event1",
            details={},
            user_id="user_123"
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event2",
            details={},
            user_id="user_456"
        )
        
        results = audit_system.search_entries(user_id="user_123")
        
        assert len(results) == 1
        assert results[0]["user_id"] == "user_123"
    
    def test_search_by_event_type(self, audit_system):
        """Test searching by event type"""
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="event1",
            details={}
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event2",
            details={}
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event3",
            details={}
        )
        
        results = audit_system.search_entries(event_type=AuditEventType.DECISION_MADE)
        
        assert len(results) == 2
        assert all(e["event_type"] == AuditEventType.DECISION_MADE.value for e in results)
    
    def test_search_by_time_range(self, audit_system):
        """Test searching by time range"""
        now = datetime.now()
        
        # Log events at different times (simulated by modifying timestamps)
        for i in range(5):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action=f"event_{i}",
                details={}
            )
        
        # Search with time range
        start_time = now - timedelta(minutes=5)
        end_time = now + timedelta(minutes=5)
        
        results = audit_system.search_entries(
            start_time=start_time,
            end_time=end_time
        )
        
        assert len(results) == 5
    
    def test_search_by_decision(self, audit_system):
        """Test searching by decision"""
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event1",
            details={},
            decision="APPROVED"
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event2",
            details={},
            decision="FLAGGED"
        )
        
        results = audit_system.search_entries(decision="FLAGGED")
        
        assert len(results) == 1
        assert results[0]["decision"] == "FLAGGED"
    
    def test_search_by_confidence(self, audit_system):
        """Test searching by minimum confidence"""
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event1",
            details={},
            confidence=0.95
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.INFO,
            action="event2",
            details={},
            confidence=0.75
        )
        
        results = audit_system.search_entries(min_confidence=0.9)
        
        assert len(results) == 1
        assert results[0]["confidence"] >= 0.9
    
    def test_search_max_results(self, audit_system):
        """Test max results limit"""
        # Log many events
        for i in range(20):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action=f"event_{i}",
                details={}
            )
        
        results = audit_system.search_entries(max_results=10)
        
        assert len(results) == 10


class TestComplianceReporting:
    """Test compliance report generation"""
    
    def test_generate_compliance_report(self, audit_system):
        """Test generating compliance report"""
        # Log various events
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="receive",
            details={},
            transaction_id="txn_001"
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.COMPLIANCE,
            action="decide",
            details={},
            transaction_id="txn_001",
            decision="APPROVED",
            confidence=0.95
        )
        
        audit_system.log_event(
            event_type=AuditEventType.ESCALATION,
            severity=AuditSeverity.WARNING,
            action="escalate",
            details={"reason": "manual_review_needed"},
            transaction_id="txn_002"
        )
        
        # Generate report
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)
        
        report = audit_system.generate_compliance_report(start_time, end_time)
        
        assert report["summary"]["total_events"] == 3
        assert report["summary"]["total_transactions"] == 2
        assert report["summary"]["total_decisions"] == 1
        assert len(report["high_confidence_decisions"]) == 1
        assert len(report["escalations"]) == 1
        assert report["integrity_check"]["verified"] is True
    
    def test_report_aggregations(self, audit_system):
        """Test report aggregations"""
        # Log events of different types
        for i in range(3):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action="receive",
                details={}
            )
        
        for i in range(2):
            audit_system.log_event(
                event_type=AuditEventType.DECISION_MADE,
                severity=AuditSeverity.COMPLIANCE,
                action="decide",
                details={},
                decision="APPROVED"
            )
        
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)
        
        report = audit_system.generate_compliance_report(start_time, end_time)
        
        assert report["by_event_type"]["transaction_received"] == 3
        assert report["by_event_type"]["decision_made"] == 2
        assert report["by_severity"]["info"] == 3
        assert report["by_severity"]["compliance"] == 2
        assert report["by_decision"]["APPROVED"] == 2


class TestAuditExport:
    """Test audit trail export functionality"""
    
    def test_export_json(self, audit_system, temp_audit_dir):
        """Test exporting audit trail as JSON"""
        # Log some events
        for i in range(3):
            audit_system.log_event(
                event_type=AuditEventType.TRANSACTION_RECEIVED,
                severity=AuditSeverity.INFO,
                action=f"event_{i}",
                details={}
            )
        
        # Export
        output_file = Path(temp_audit_dir) / "export.json"
        audit_system.export_audit_trail(str(output_file), format="json")
        
        # Verify export
        assert output_file.exists()
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert len(data) == 3
    
    def test_get_transaction_audit_trail(self, audit_system):
        """Test getting complete audit trail for transaction"""
        # Log events for transaction
        audit_system.log_event(
            event_type=AuditEventType.TRANSACTION_RECEIVED,
            severity=AuditSeverity.INFO,
            action="receive",
            details={},
            transaction_id="txn_123"
        )
        
        audit_system.log_event(
            event_type=AuditEventType.REASONING_STEP,
            severity=AuditSeverity.INFO,
            action="analyze",
            details={},
            transaction_id="txn_123",
            reasoning_steps=["step1", "step2"]
        )
        
        audit_system.log_event(
            event_type=AuditEventType.DECISION_MADE,
            severity=AuditSeverity.COMPLIANCE,
            action="decide",
            details={},
            transaction_id="txn_123",
            decision="APPROVED"
        )
        
        # Get trail
        trail = audit_system.get_transaction_audit_trail("txn_123")
        
        assert trail["transaction_id"] == "txn_123"
        assert trail["total_events"] == 3
        assert len(trail["timeline"]) == 3
        assert len(trail["decisions"]) == 1
        assert len(trail["reasoning_steps"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
