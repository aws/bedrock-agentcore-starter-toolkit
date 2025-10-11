"""
Comprehensive Audit Trail System for Fraud Detection

This module provides immutable audit logging with tamper detection,
search capabilities, and automated compliance reporting.
"""

import hashlib
import json
import gzip
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events"""
    TRANSACTION_RECEIVED = "transaction_received"
    DECISION_MADE = "decision_made"
    REASONING_STEP = "reasoning_step"
    AGENT_ACTION = "agent_action"
    EXTERNAL_API_CALL = "external_api_call"
    MEMORY_ACCESS = "memory_access"
    ESCALATION = "escalation"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    COMPLIANCE = "compliance"


@dataclass
class AuditEntry:
    """Immutable audit log entry with tamper detection"""
    timestamp: str
    event_type: str
    severity: str
    transaction_id: Optional[str]
    user_id: Optional[str]
    agent_id: Optional[str]
    action: str
    details: Dict[str, Any]
    reasoning_steps: Optional[List[str]]
    decision: Optional[str]
    confidence: Optional[float]
    evidence: Optional[List[str]]
    previous_hash: str
    entry_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class AuditTrailSystem:
    """
    Comprehensive audit trail system with immutable logging,
    tamper detection, and compliance reporting.
    """
    
    def __init__(self, storage_path: str = "audit_logs", enable_compression: bool = True):
        """
        Initialize audit trail system
        
        Args:
            storage_path: Directory for storing audit logs
            enable_compression: Enable gzip compression for logs
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.enable_compression = enable_compression
        self.previous_hash = "0" * 64  # Genesis hash
        self.current_log_file = None
        self.entries_count = 0
        self.max_entries_per_file = 10000
        
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash for tamper detection
        
        Args:
            data: Data to hash
            
        Returns:
            Hexadecimal hash string
        """
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def _get_log_filename(self) -> Path:
        """Generate log filename with timestamp and microseconds"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        extension = ".jsonl.gz" if self.enable_compression else ".jsonl"
        return self.storage_path / f"audit_log_{timestamp}{extension}"
    
    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        details: Dict[str, Any],
        transaction_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        reasoning_steps: Optional[List[str]] = None,
        decision: Optional[str] = None,
        confidence: Optional[float] = None,
        evidence: Optional[List[str]] = None
    ) -> AuditEntry:
        """
        Log an audit event with tamper detection
        
        Args:
            event_type: Type of audit event
            severity: Severity level
            action: Action description
            details: Additional details
            transaction_id: Associated transaction ID
            user_id: Associated user ID
            agent_id: Agent that performed the action
            reasoning_steps: Reasoning steps taken
            decision: Decision made
            confidence: Confidence score
            evidence: Supporting evidence
            
        Returns:
            Created audit entry
        """
        # Create entry data
        entry_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "transaction_id": transaction_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "action": action,
            "details": details,
            "reasoning_steps": reasoning_steps,
            "decision": decision,
            "confidence": confidence,
            "evidence": evidence,
            "previous_hash": self.previous_hash
        }
        
        # Calculate hash for tamper detection
        entry_hash = self._calculate_hash(entry_data)
        entry_data["entry_hash"] = entry_hash
        
        # Create audit entry
        entry = AuditEntry(**entry_data)
        
        # Write to storage
        self._write_entry(entry)
        
        # Update previous hash for chain
        self.previous_hash = entry_hash
        
        return entry

    def _write_entry(self, entry: AuditEntry):
        """Write audit entry to storage"""
        # Rotate log file if needed (check before incrementing)
        if self.current_log_file is None or self.entries_count > 0 and self.entries_count % self.max_entries_per_file == 0:
            self.current_log_file = self._get_log_filename()
        
        # Write entry
        entry_json = json.dumps(entry.to_dict())
        
        if self.enable_compression:
            with gzip.open(self.current_log_file, 'at', encoding='utf-8') as f:
                f.write(entry_json + '\n')
        else:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(entry_json + '\n')
        
        # Increment counter after write
        self.entries_count += 1
    
    def verify_integrity(self, log_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Verify integrity of audit log using hash chain
        
        Args:
            log_file: Specific log file to verify (None for all)
            
        Returns:
            Verification result with details
        """
        files_to_verify = [log_file] if log_file else sorted(self.storage_path.glob("audit_log_*"))
        
        results = {
            "verified": True,
            "total_entries": 0,
            "tampered_entries": [],
            "files_checked": 0
        }
        
        previous_hash = "0" * 64
        
        for file_path in files_to_verify:
            results["files_checked"] += 1
            
            # Read entries
            if file_path.suffix == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    entries = [json.loads(line) for line in f]
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entries = [json.loads(line) for line in f]
            
            # Verify each entry
            for idx, entry in enumerate(entries):
                results["total_entries"] += 1
                
                # Check previous hash chain
                if entry["previous_hash"] != previous_hash:
                    results["verified"] = False
                    results["tampered_entries"].append({
                        "file": str(file_path),
                        "entry_index": idx,
                        "reason": "broken_hash_chain",
                        "expected_previous_hash": previous_hash,
                        "actual_previous_hash": entry["previous_hash"]
                    })
                
                # Verify entry hash
                stored_hash = entry.pop("entry_hash")
                calculated_hash = self._calculate_hash(entry)
                entry["entry_hash"] = stored_hash
                
                if stored_hash != calculated_hash:
                    results["verified"] = False
                    results["tampered_entries"].append({
                        "file": str(file_path),
                        "entry_index": idx,
                        "reason": "hash_mismatch",
                        "expected_hash": calculated_hash,
                        "actual_hash": stored_hash
                    })
                
                previous_hash = stored_hash
        
        return results
    
    def search_entries(
        self,
        transaction_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        decision: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Search audit trail with filtering
        
        Args:
            transaction_id: Filter by transaction ID
            user_id: Filter by user ID
            agent_id: Filter by agent ID
            event_type: Filter by event type
            severity: Filter by severity
            start_time: Filter by start time
            end_time: Filter by end time
            decision: Filter by decision
            min_confidence: Minimum confidence score
            max_results: Maximum results to return
            
        Returns:
            List of matching audit entries
        """
        results = []
        
        for file_path in sorted(self.storage_path.glob("audit_log_*")):
            # Read entries
            if file_path.suffix == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    entries = [json.loads(line) for line in f]
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entries = [json.loads(line) for line in f]
            
            # Filter entries
            for entry in entries:
                # Apply filters
                if transaction_id and entry.get("transaction_id") != transaction_id:
                    continue
                if user_id and entry.get("user_id") != user_id:
                    continue
                if agent_id and entry.get("agent_id") != agent_id:
                    continue
                if event_type and entry.get("event_type") != event_type.value:
                    continue
                if severity and entry.get("severity") != severity.value:
                    continue
                if decision and entry.get("decision") != decision:
                    continue
                if min_confidence and (entry.get("confidence") or 0) < min_confidence:
                    continue
                
                # Time filters
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue
                
                results.append(entry)
                
                if len(results) >= max_results:
                    return results
        
        return results
    
    def generate_compliance_report(
        self,
        start_time: datetime,
        end_time: datetime,
        report_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        Generate automated compliance report
        
        Args:
            start_time: Report start time
            end_time: Report end time
            report_type: Type of report (standard, detailed, summary)
            
        Returns:
            Compliance report data
        """
        # Search all entries in time range
        entries = self.search_entries(
            start_time=start_time,
            end_time=end_time,
            max_results=100000
        )
        
        # Aggregate statistics
        report = {
            "report_type": report_type,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "summary": {
                "total_events": len(entries),
                "total_transactions": len(set(e.get("transaction_id") for e in entries if e.get("transaction_id"))),
                "total_users": len(set(e.get("user_id") for e in entries if e.get("user_id"))),
                "total_decisions": sum(1 for e in entries if e.get("decision"))
            },
            "by_event_type": {},
            "by_severity": {},
            "by_decision": {},
            "high_confidence_decisions": [],
            "escalations": [],
            "errors": []
        }
        
        # Aggregate by categories
        for entry in entries:
            # By event type
            event_type = entry.get("event_type", "unknown")
            report["by_event_type"][event_type] = report["by_event_type"].get(event_type, 0) + 1
            
            # By severity
            severity = entry.get("severity", "unknown")
            report["by_severity"][severity] = report["by_severity"].get(severity, 0) + 1
            
            # By decision
            if entry.get("decision"):
                decision = entry["decision"]
                report["by_decision"][decision] = report["by_decision"].get(decision, 0) + 1
            
            # High confidence decisions
            if entry.get("confidence") and entry["confidence"] >= 0.9:
                report["high_confidence_decisions"].append({
                    "timestamp": entry["timestamp"],
                    "transaction_id": entry.get("transaction_id"),
                    "decision": entry.get("decision"),
                    "confidence": entry["confidence"]
                })
            
            # Escalations
            if entry.get("event_type") == AuditEventType.ESCALATION.value:
                report["escalations"].append({
                    "timestamp": entry["timestamp"],
                    "transaction_id": entry.get("transaction_id"),
                    "reason": entry.get("details", {}).get("reason")
                })
            
            # Errors
            if entry.get("event_type") == AuditEventType.SYSTEM_ERROR.value:
                report["errors"].append({
                    "timestamp": entry["timestamp"],
                    "error": entry.get("details", {}).get("error")
                })
        
        # Add integrity verification
        verification = self.verify_integrity()
        report["integrity_check"] = {
            "verified": verification["verified"],
            "total_entries_checked": verification["total_entries"],
            "tampered_entries": len(verification["tampered_entries"])
        }
        
        return report
    
    def export_audit_trail(
        self,
        output_file: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json"
    ):
        """
        Export audit trail for regulatory reporting
        
        Args:
            output_file: Output file path
            start_time: Start time filter
            end_time: End time filter
            format: Export format (json, csv)
        """
        entries = self.search_entries(
            start_time=start_time,
            end_time=end_time,
            max_results=1000000
        )
        
        if format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
        elif format == "csv":
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if entries:
                    writer = csv.DictWriter(f, fieldnames=entries[0].keys())
                    writer.writeheader()
                    writer.writerows(entries)
    
    def get_transaction_audit_trail(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get complete audit trail for a specific transaction
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Complete audit trail with timeline
        """
        entries = self.search_entries(transaction_id=transaction_id)
        
        return {
            "transaction_id": transaction_id,
            "total_events": len(entries),
            "timeline": sorted(entries, key=lambda x: x["timestamp"]),
            "decisions": [e for e in entries if e.get("decision")],
            "reasoning_steps": [e for e in entries if e.get("reasoning_steps")],
            "agent_actions": [e for e in entries if e.get("agent_id")],
            "external_calls": [e for e in entries if e.get("event_type") == AuditEventType.EXTERNAL_API_CALL.value]
        }
