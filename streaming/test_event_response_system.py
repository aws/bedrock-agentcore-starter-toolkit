"""
Unit tests for Event-Driven Response System.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from streaming.event_response_system import (
    EventResponseSystem, FraudEvent, ResponseRule, ResponseExecution,
    EventType, EventSeverity, ResponseAction, create_fraud_event, create_response_rule
)


@pytest.fixture
def event_system():
    """Create event response system for testing."""
    return EventResponseSystem(max_queue_size=100)


@pytest.fixture
def sample_fraud_event():
    """Create sample fraud event."""
    return create_fraud_event(
        event_type=EventType.FRAUD_DETECTED,
        severity=EventSeverity.HIGH,
        source_agent="test_agent",
        details={"transaction_id": "txn_123", "amount": 1000.0},
        risk_score=0.8,
        confidence_score=0.9,
        transaction_id="txn_123",
        user_id="user_456"
    )


@pytest.fixture
def sample_response_rule():
    """Create sample response rule."""
    return create_response_rule(
        name="Block High Risk Transactions",
        event_types=[EventType.FRAUD_DETECTED, EventType.HIGH_RISK_TRANSACTION],
        severity_threshold=EventSeverity.HIGH,
        actions=[ResponseAction.BLOCK_TRANSACTION, ResponseAction.SEND_ALERT],
        conditions={"min_risk_score": 0.7},
        priority=10
    )


class TestEventResponseSystem:
    """Test cases for EventResponseSystem."""
    
    def test_system_initialization(self, event_system):
        """Test event response system initialization."""
        assert event_system.max_queue_size == 100
        assert len(event_system.response_rules) == 0
        assert event_system.is_running is False
        assert event_system.enable_correlation is True
    
    def test_add_response_rule(self, event_system, sample_response_rule):
        """Test adding response rules."""
        success = event_system.add_response_rule(sample_response_rule)
        
        assert success is True
        assert sample_response_rule.rule_id in event_system.response_rules
        assert len(event_system.response_rules) == 1
    
    def test_remove_response_rule(self, event_system, sample_response_rule):
        """Test removing response rules."""
        # Add rule first
        event_system.add_response_rule(sample_response_rule)
        
        # Then remove it
        success = event_system.remove_response_rule(sample_response_rule.rule_id)
        
        assert success is True
        assert sample_response_rule.rule_id not in event_system.response_rules
        assert len(event_system.response_rules) == 0
    
    def test_register_action_handler(self, event_system):
        """Test registering action handlers."""
        def test_handler(event, rule):
            return {"handled": True}
        
        event_system.register_action_handler(ResponseAction.BLOCK_TRANSACTION, test_handler)
        
        assert ResponseAction.BLOCK_TRANSACTION in event_system.action_handlers
        assert event_system.action_handlers[ResponseAction.BLOCK_TRANSACTION] == test_handler
    
    def test_add_event_listener(self, event_system):
        """Test adding event listeners."""
        def test_listener(event):
            pass
        
        event_system.add_event_listener(test_listener)
        
        assert len(event_system.event_listeners) == 1
        assert test_listener in event_system.event_listeners
    
    def test_submit_event(self, event_system, sample_fraud_event):
        """Test submitting fraud events."""
        success = event_system.submit_event(sample_fraud_event)
        
        assert success is True
        assert sample_fraud_event.event_id in event_system.pending_events
        assert event_system.event_queue.qsize() == 1
    
    def test_event_listener_notification(self, event_system, sample_fraud_event):
        """Test event listener notifications."""
        received_events = []
        
        def test_listener(event):
            received_events.append(event)
        
        event_system.add_event_listener(test_listener)
        event_system.submit_event(sample_fraud_event)
        
        assert len(received_events) == 1
        assert received_events[0].event_id == sample_fraud_event.event_id
    
    def test_find_matching_rules(self, event_system, sample_fraud_event, sample_response_rule):
        """Test finding matching response rules."""
        event_system.add_response_rule(sample_response_rule)
        
        matching_rules = event_system._find_matching_rules(sample_fraud_event)
        
        assert len(matching_rules) == 1
        assert matching_rules[0].rule_id == sample_response_rule.rule_id
    
    def test_evaluate_rule_conditions(self, event_system, sample_fraud_event):
        """Test rule condition evaluation."""
        # Rule with risk score condition
        rule_with_conditions = create_response_rule(
            name="High Risk Rule",
            event_types=[EventType.FRAUD_DETECTED],
            severity_threshold=EventSeverity.MEDIUM,
            actions=[ResponseAction.SEND_ALERT],
            conditions={"min_risk_score": 0.7, "min_confidence": 0.8}
        )
        
        # Should match (event has risk_score=0.8, confidence=0.9)
        matches = event_system._evaluate_rule_conditions(sample_fraud_event, rule_with_conditions)
        assert matches is True
        
        # Rule with higher threshold
        rule_high_threshold = create_response_rule(
            name="Very High Risk Rule",
            event_types=[EventType.FRAUD_DETECTED],
            severity_threshold=EventSeverity.MEDIUM,
            actions=[ResponseAction.BLOCK_TRANSACTION],
            conditions={"min_risk_score": 0.9}  # Higher than event's 0.8
        )
        
        # Should not match
        matches = event_system._evaluate_rule_conditions(sample_fraud_event, rule_high_threshold)
        assert matches is False
    
    def test_can_execute_rule(self, event_system):
        """Test rule execution constraints."""
        rule = create_response_rule(
            name="Test Rule",
            event_types=[EventType.FRAUD_DETECTED],
            severity_threshold=EventSeverity.LOW,
            actions=[ResponseAction.LOG_EVENT],
            cooldown_seconds=60,  # 1 minute cooldown
            priority=100
        )
        
        # Should be able to execute initially
        can_execute = event_system._can_execute_rule(rule)
        assert can_execute is True
        
        # Simulate recent execution
        event_system.rule_last_execution[rule.rule_id] = datetime.now()
        
        # Should not be able to execute due to cooldown
        can_execute = event_system._can_execute_rule(rule)
        assert can_execute is False
    
    def test_default_action_handler(self, event_system, sample_fraud_event, sample_response_rule):
        """Test default action handlers."""
        # Test LOG_EVENT action
        result = event_system._default_action_handler(
            sample_fraud_event, sample_response_rule, ResponseAction.LOG_EVENT
        )
        assert result["logged"] is True
        
        # Test BLOCK_TRANSACTION action
        result = event_system._default_action_handler(
            sample_fraud_event, sample_response_rule, ResponseAction.BLOCK_TRANSACTION
        )
        assert result["blocked"] is True
        assert result["transaction_id"] == "txn_123"
        
        # Test SEND_ALERT action
        result = event_system._default_action_handler(
            sample_fraud_event, sample_response_rule, ResponseAction.SEND_ALERT
        )
        assert result["alert_sent"] is True
        assert result["severity"] == EventSeverity.HIGH.value
    
    def test_custom_action_handler(self, event_system, sample_fraud_event, sample_response_rule):
        """Test custom action handlers."""
        def custom_block_handler(event, rule):
            return {"custom_blocked": True, "event_id": event.event_id}
        
        event_system.register_action_handler(ResponseAction.BLOCK_TRANSACTION, custom_block_handler)
        
        execution = event_system._execute_action(
            sample_fraud_event, sample_response_rule, ResponseAction.BLOCK_TRANSACTION
        )
        
        assert execution.success is True
        assert execution.result["custom_blocked"] is True
        assert execution.result["event_id"] == sample_fraud_event.event_id
    
    def test_get_metrics(self, event_system, sample_fraud_event):
        """Test getting system metrics."""
        event_system.submit_event(sample_fraud_event)
        
        metrics = event_system.get_metrics()
        
        assert "events_processed" in metrics
        assert "responses_executed" in metrics
        assert "queue_size" in metrics
        assert "pending_events" in metrics
        
        assert metrics["queue_size"] == 1
        assert metrics["pending_events"] == 1
    
    def test_get_status(self, event_system, sample_response_rule):
        """Test getting system status."""
        event_system.add_response_rule(sample_response_rule)
        
        status = event_system.get_status()
        
        assert "is_running" in status
        assert "metrics" in status
        assert "rules" in status
        assert "recent_executions" in status
        
        assert len(status["rules"]) == 1
        assert sample_response_rule.rule_id in status["rules"]
    
    def test_start_stop_system(self, event_system):
        """Test starting and stopping the system."""
        # Start system
        event_system.start()
        assert event_system.is_running is True
        
        # Stop system
        event_system.stop()
        assert event_system.is_running is False
    
    def test_event_correlation_window(self, event_system):
        """Test event correlation window management."""
        event1 = create_fraud_event(
            EventType.VELOCITY_EXCEEDED, EventSeverity.MEDIUM, "agent1",
            {"location": "NY"}, 0.6, 0.8, user_id="user_123"
        )
        
        event2 = create_fraud_event(
            EventType.LOCATION_ANOMALY, EventSeverity.MEDIUM, "agent2",
            {"location": "CA"}, 0.7, 0.9, user_id="user_123"
        )
        
        # Add events to correlation window
        event_system._add_to_correlation_window(event1)
        event_system._add_to_correlation_window(event2)
        
        # Check that events are in correlation window
        user_key = "user_user_123"
        assert user_key in event_system.correlation_windows
        assert len(event_system.correlation_windows[user_key]) == 2
    
    def test_velocity_correlation_detection(self, event_system):
        """Test velocity correlation detection."""
        user_id = "user_velocity_test"
        
        # Create multiple events in short time window
        events = []
        for i in range(4):
            event = create_fraud_event(
                EventType.HIGH_RISK_TRANSACTION, EventSeverity.MEDIUM, f"agent_{i}",
                {"amount": 100 * (i + 1)}, 0.6, 0.8, user_id=user_id
            )
            events.append(event)
            event_system._add_to_correlation_window(event)
        
        # Detect correlations
        event_system._detect_velocity_correlation(f"user_{user_id}", events)
        
        # Should detect high velocity pattern
        assert len(event_system.active_correlations) > 0
        
        # Check correlation details
        correlation = list(event_system.active_correlations.values())[0]
        assert correlation.pattern_type == "high_velocity"
        assert len(correlation.events) >= 3


class TestFraudEvent:
    """Test cases for FraudEvent class."""
    
    def test_fraud_event_creation(self):
        """Test fraud event creation."""
        event = create_fraud_event(
            event_type=EventType.SUSPICIOUS_PATTERN,
            severity=EventSeverity.CRITICAL,
            source_agent="pattern_detector",
            details={"pattern": "impossible_travel"},
            risk_score=0.95,
            confidence_score=0.88,
            user_id="user_789"
        )
        
        assert event.event_type == EventType.SUSPICIOUS_PATTERN
        assert event.severity == EventSeverity.CRITICAL
        assert event.source_agent == "pattern_detector"
        assert event.risk_score == 0.95
        assert event.confidence_score == 0.88
        assert event.user_id == "user_789"
        assert event.event_id is not None
    
    def test_event_priority_ordering(self):
        """Test event priority ordering for queue."""
        high_event = create_fraud_event(
            EventType.FRAUD_DETECTED, EventSeverity.HIGH, "agent1",
            {}, 0.8, 0.9
        )
        
        critical_event = create_fraud_event(
            EventType.ACCOUNT_COMPROMISE, EventSeverity.CRITICAL, "agent2",
            {}, 0.9, 0.95
        )
        
        # Critical should be "less than" high for priority queue ordering
        assert critical_event < high_event


class TestResponseRule:
    """Test cases for ResponseRule class."""
    
    def test_response_rule_creation(self):
        """Test response rule creation."""
        rule = create_response_rule(
            name="Critical Fraud Response",
            event_types=[EventType.FRAUD_DETECTED, EventType.ACCOUNT_COMPROMISE],
            severity_threshold=EventSeverity.CRITICAL,
            actions=[ResponseAction.BLOCK_ACCOUNT, ResponseAction.ESCALATE_TO_HUMAN],
            conditions={"min_risk_score": 0.9},
            priority=1,
            cooldown_seconds=300
        )
        
        assert rule.name == "Critical Fraud Response"
        assert len(rule.event_types) == 2
        assert EventType.FRAUD_DETECTED in rule.event_types
        assert rule.severity_threshold == EventSeverity.CRITICAL
        assert len(rule.actions) == 2
        assert ResponseAction.BLOCK_ACCOUNT in rule.actions
        assert rule.conditions["min_risk_score"] == 0.9
        assert rule.priority == 1
        assert rule.cooldown_seconds == 300
        assert rule.enabled is True


class TestResponseExecution:
    """Test cases for ResponseExecution class."""
    
    def test_response_execution_creation(self, sample_fraud_event, sample_response_rule):
        """Test response execution creation."""
        execution = ResponseExecution(
            execution_id="exec_123",
            event_id=sample_fraud_event.event_id,
            rule_id=sample_response_rule.rule_id,
            action=ResponseAction.BLOCK_TRANSACTION,
            executed_at=datetime.now(),
            success=True,
            result={"blocked": True},
            execution_time_ms=150.0
        )
        
        assert execution.execution_id == "exec_123"
        assert execution.event_id == sample_fraud_event.event_id
        assert execution.rule_id == sample_response_rule.rule_id
        assert execution.action == ResponseAction.BLOCK_TRANSACTION
        assert execution.success is True
        assert execution.result["blocked"] is True
        assert execution.execution_time_ms == 150.0


if __name__ == "__main__":
    pytest.main([__file__])