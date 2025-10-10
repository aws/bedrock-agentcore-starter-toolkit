"""
Event-Driven Response System

Provides immediate response triggers for fraud detection with automated
blocking, alerting, and event correlation capabilities.
"""

import logging
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue, PriorityQueue, Empty
import uuid

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of fraud detection events."""
    FRAUD_DETECTED = "fraud_detected"
    HIGH_RISK_TRANSACTION = "high_risk_transaction"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    VELOCITY_EXCEEDED = "velocity_exceeded"
    LOCATION_ANOMALY = "location_anomaly"
    DEVICE_ANOMALY = "device_anomaly"
    ACCOUNT_COMPROMISE = "account_compromise"
    COMPLIANCE_VIOLATION = "compliance_violation"


class EventSeverity(Enum):
    """Event severity levels."""
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class ResponseAction(Enum):
    """Types of automated responses."""
    BLOCK_TRANSACTION = "block_transaction"
    BLOCK_ACCOUNT = "block_account"
    REQUIRE_VERIFICATION = "require_verification"
    SEND_ALERT = "send_alert"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    LOG_EVENT = "log_event"
    UPDATE_RISK_SCORE = "update_risk_score"
    NOTIFY_CUSTOMER = "notify_customer"


class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class FraudEvent:
    """Fraud detection event."""
    event_id: str
    event_type: EventType
    severity: EventSeverity
    timestamp: datetime
    source_agent: str
    transaction_id: Optional[str]
    user_id: Optional[str]
    details: Dict[str, Any]
    risk_score: float
    confidence_score: float
    evidence: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering by severity."""
        return self.severity.value > other.severity.value


@dataclass
class ResponseRule:
    """Rule for automated response to events."""
    rule_id: str
    name: str
    event_types: List[EventType]
    severity_threshold: EventSeverity
    conditions: Dict[str, Any]
    actions: List[ResponseAction]
    enabled: bool = True
    priority: int = 100
    cooldown_seconds: int = 0
    max_executions_per_hour: int = 1000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseExecution:
    """Record of response execution."""
    execution_id: str
    event_id: str
    rule_id: str
    action: ResponseAction
    executed_at: datetime
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class EventCorrelation:
    """Correlated events for pattern detection."""
    correlation_id: str
    events: List[FraudEvent]
    pattern_type: str
    confidence_score: float
    created_at: datetime
    time_window_minutes: int
    correlation_factors: List[str]


class EventResponseSystem:
    """
    Event-driven response system for real-time fraud detection.
    
    Features:
    - Immediate response triggers
    - Automated blocking and alerting
    - Event prioritization and correlation
    - Pattern detection across event streams
    """
    
    def __init__(self, max_queue_size: int = 10000):
        """
        Initialize event response system.
        
        Args:
            max_queue_size: Maximum size of event queue
        """
        self.max_queue_size = max_queue_size
        
        # Event processing
        self.event_queue = PriorityQueue(maxsize=max_queue_size)
        self.pending_events: Dict[str, FraudEvent] = {}
        self.processed_events: Dict[str, FraudEvent] = {}
        
        # Response rules and executions
        self.response_rules: Dict[str, ResponseRule] = {}
        self.response_executions: List[ResponseExecution] = []
        self.rule_execution_counts: Dict[str, Dict[str, int]] = {}  # rule_id -> hour -> count
        self.rule_last_execution: Dict[str, datetime] = {}
        
        # Event correlation
        self.correlation_windows: Dict[str, List[FraudEvent]] = {}
        self.active_correlations: Dict[str, EventCorrelation] = {}
        self.correlation_rules = []
        
        # Response handlers
        self.action_handlers: Dict[ResponseAction, Callable] = {}
        self.event_listeners: List[Callable[[FraudEvent], None]] = []
        
        # Threading and processing
        self.is_running = False
        self.processor_thread = None
        self.correlation_thread = None
        
        # Configuration
        self.enable_correlation = True
        self.correlation_window_minutes = 10
        self.max_correlation_events = 100
        self.cleanup_interval_hours = 24
        
        # Metrics
        self.metrics = {
            "events_processed": 0,
            "responses_executed": 0,
            "correlations_detected": 0,
            "blocked_transactions": 0,
            "alerts_sent": 0,
            "processing_errors": 0
        }
        
        logger.info("Event response system initialized")
    
    def add_response_rule(self, rule: ResponseRule) -> bool:
        """
        Add a response rule to the system.
        
        Args:
            rule: Response rule to add
            
        Returns:
            True if rule was added successfully
        """
        try:
            self.response_rules[rule.rule_id] = rule
            logger.info(f"Added response rule: {rule.name} ({rule.rule_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add response rule {rule.rule_id}: {str(e)}")
            return False
    
    def remove_response_rule(self, rule_id: str) -> bool:
        """
        Remove a response rule from the system.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            True if rule was removed successfully
        """
        if rule_id in self.response_rules:
            del self.response_rules[rule_id]
            logger.info(f"Removed response rule: {rule_id}")
            return True
        
        return False
    
    def register_action_handler(self, action: ResponseAction, handler: Callable) -> None:
        """
        Register a handler for a response action.
        
        Args:
            action: Response action type
            handler: Handler function
        """
        self.action_handlers[action] = handler
        logger.debug(f"Registered handler for action: {action.value}")
    
    def add_event_listener(self, listener: Callable[[FraudEvent], None]) -> None:
        """
        Add an event listener for notifications.
        
        Args:
            listener: Event listener function
        """
        self.event_listeners.append(listener)
        logger.debug("Added event listener")
    
    def submit_event(self, event: FraudEvent) -> bool:
        """
        Submit a fraud event for processing.
        
        Args:
            event: Fraud event to process
            
        Returns:
            True if event was queued successfully
        """
        try:
            # Add to pending events
            self.pending_events[event.event_id] = event
            
            # Add to priority queue
            self.event_queue.put_nowait(event)
            
            # Notify listeners
            for listener in self.event_listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Error in event listener: {str(e)}")
            
            logger.debug(f"Queued event {event.event_id} of type {event.event_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit event {event.event_id}: {str(e)}")
            return False
    
    def start(self) -> None:
        """Start the event response system."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start event processor thread
        self.processor_thread = threading.Thread(target=self._event_processor_loop, daemon=True)
        self.processor_thread.start()
        
        # Start correlation thread if enabled
        if self.enable_correlation:
            self.correlation_thread = threading.Thread(target=self._correlation_loop, daemon=True)
            self.correlation_thread.start()
        
        logger.info("Event response system started")
    
    def stop(self) -> None:
        """Stop the event response system."""
        self.is_running = False
        
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        
        if self.correlation_thread:
            self.correlation_thread.join(timeout=5)
        
        logger.info("Event response system stopped")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        return {
            "events_processed": self.metrics["events_processed"],
            "responses_executed": self.metrics["responses_executed"],
            "correlations_detected": self.metrics["correlations_detected"],
            "blocked_transactions": self.metrics["blocked_transactions"],
            "alerts_sent": self.metrics["alerts_sent"],
            "processing_errors": self.metrics["processing_errors"],
            "queue_size": self.event_queue.qsize(),
            "pending_events": len(self.pending_events),
            "active_rules": len([r for r in self.response_rules.values() if r.enabled]),
            "active_correlations": len(self.active_correlations)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed system status."""
        metrics = self.get_metrics()
        
        return {
            "is_running": self.is_running,
            "enable_correlation": self.enable_correlation,
            "metrics": metrics,
            "rules": {
                rule_id: {
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "event_types": [et.value for et in rule.event_types],
                    "actions": [a.value for a in rule.actions]
                }
                for rule_id, rule in self.response_rules.items()
            },
            "recent_executions": [
                {
                    "execution_id": exec.execution_id,
                    "action": exec.action.value,
                    "success": exec.success,
                    "executed_at": exec.executed_at.isoformat()
                }
                for exec in self.response_executions[-10:]  # Last 10 executions
            ]
        }
    
    def _event_processor_loop(self) -> None:
        """Main event processing loop."""
        while self.is_running:
            try:
                # Get next event from queue
                try:
                    event = self.event_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Process event
                self._process_event(event)
                
                # Update metrics
                self.metrics["events_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error in event processor loop: {str(e)}")
                self.metrics["processing_errors"] += 1
                time.sleep(1)
    
    def _process_event(self, event: FraudEvent) -> None:
        """Process a single fraud event."""
        try:
            logger.debug(f"Processing event {event.event_id} of type {event.event_type.value}")
            
            # Find matching response rules
            matching_rules = self._find_matching_rules(event)
            
            # Execute responses for matching rules
            for rule in matching_rules:
                if self._can_execute_rule(rule):
                    self._execute_rule_responses(event, rule)
            
            # Add to correlation window if enabled
            if self.enable_correlation:
                self._add_to_correlation_window(event)
            
            # Move to processed events
            self.processed_events[event.event_id] = event
            if event.event_id in self.pending_events:
                del self.pending_events[event.event_id]
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {str(e)}")
            self.metrics["processing_errors"] += 1
    
    def _find_matching_rules(self, event: FraudEvent) -> List[ResponseRule]:
        """Find response rules that match the event."""
        matching_rules = []
        
        for rule in self.response_rules.values():
            if not rule.enabled:
                continue
            
            # Check event type match
            if event.event_type not in rule.event_types:
                continue
            
            # Check severity threshold
            if event.severity.value < rule.severity_threshold.value:
                continue
            
            # Check additional conditions
            if self._evaluate_rule_conditions(event, rule):
                matching_rules.append(rule)
        
        # Sort by priority
        matching_rules.sort(key=lambda r: r.priority)
        
        return matching_rules
    
    def _evaluate_rule_conditions(self, event: FraudEvent, rule: ResponseRule) -> bool:
        """Evaluate rule conditions against event."""
        conditions = rule.conditions
        
        # Risk score threshold
        if "min_risk_score" in conditions:
            if event.risk_score < conditions["min_risk_score"]:
                return False
        
        # Confidence threshold
        if "min_confidence" in conditions:
            if event.confidence_score < conditions["min_confidence"]:
                return False
        
        # User ID filter
        if "user_ids" in conditions:
            if event.user_id not in conditions["user_ids"]:
                return False
        
        # Transaction amount threshold
        if "min_amount" in conditions and event.transaction_id:
            transaction_amount = event.details.get("amount", 0)
            if transaction_amount < conditions["min_amount"]:
                return False
        
        # Time-based conditions
        if "time_window" in conditions:
            window = conditions["time_window"]
            if "start_hour" in window and "end_hour" in window:
                current_hour = event.timestamp.hour
                if not (window["start_hour"] <= current_hour <= window["end_hour"]):
                    return False
        
        return True
    
    def _can_execute_rule(self, rule: ResponseRule) -> bool:
        """Check if rule can be executed (cooldown and rate limits)."""
        current_time = datetime.now()
        
        # Check cooldown
        if rule.cooldown_seconds > 0:
            last_execution = self.rule_last_execution.get(rule.rule_id)
            if last_execution:
                time_since_last = (current_time - last_execution).total_seconds()
                if time_since_last < rule.cooldown_seconds:
                    return False
        
        # Check hourly rate limit
        current_hour = current_time.strftime("%Y-%m-%d-%H")
        if rule.rule_id not in self.rule_execution_counts:
            self.rule_execution_counts[rule.rule_id] = {}
        
        hour_count = self.rule_execution_counts[rule.rule_id].get(current_hour, 0)
        if hour_count >= rule.max_executions_per_hour:
            return False
        
        return True
    
    def _execute_rule_responses(self, event: FraudEvent, rule: ResponseRule) -> None:
        """Execute all response actions for a rule."""
        for action in rule.actions:
            try:
                execution = self._execute_action(event, rule, action)
                self.response_executions.append(execution)
                
                if execution.success:
                    self.metrics["responses_executed"] += 1
                    
                    # Update specific action metrics
                    if action == ResponseAction.BLOCK_TRANSACTION:
                        self.metrics["blocked_transactions"] += 1
                    elif action == ResponseAction.SEND_ALERT:
                        self.metrics["alerts_sent"] += 1
                
            except Exception as e:
                logger.error(f"Error executing action {action.value} for rule {rule.rule_id}: {str(e)}")
        
        # Update rule execution tracking
        current_time = datetime.now()
        current_hour = current_time.strftime("%Y-%m-%d-%H")
        
        self.rule_last_execution[rule.rule_id] = current_time
        
        if rule.rule_id not in self.rule_execution_counts:
            self.rule_execution_counts[rule.rule_id] = {}
        
        self.rule_execution_counts[rule.rule_id][current_hour] = \
            self.rule_execution_counts[rule.rule_id].get(current_hour, 0) + 1
    
    def _execute_action(self, event: FraudEvent, rule: ResponseRule, action: ResponseAction) -> ResponseExecution:
        """Execute a single response action."""
        start_time = time.time()
        execution_id = str(uuid.uuid4())
        
        execution = ResponseExecution(
            execution_id=execution_id,
            event_id=event.event_id,
            rule_id=rule.rule_id,
            action=action,
            executed_at=datetime.now(),
            success=False
        )
        
        try:
            # Check if we have a registered handler
            if action in self.action_handlers:
                handler = self.action_handlers[action]
                result = handler(event, rule)
                execution.result = result
                execution.success = True
            else:
                # Default action implementations
                result = self._default_action_handler(event, rule, action)
                execution.result = result
                execution.success = True
            
            logger.debug(f"Executed action {action.value} for event {event.event_id}")
            
        except Exception as e:
            execution.error_message = str(e)
            execution.success = False
            logger.error(f"Failed to execute action {action.value}: {str(e)}")
        
        execution.execution_time_ms = (time.time() - start_time) * 1000
        return execution
    
    def _default_action_handler(self, event: FraudEvent, rule: ResponseRule, action: ResponseAction) -> Dict[str, Any]:
        """Default implementation for response actions."""
        if action == ResponseAction.LOG_EVENT:
            logger.info(f"FRAUD EVENT: {event.event_type.value} - {event.event_id}")
            return {"logged": True}
        
        elif action == ResponseAction.BLOCK_TRANSACTION:
            logger.warning(f"BLOCKING TRANSACTION: {event.transaction_id}")
            return {"blocked": True, "transaction_id": event.transaction_id}
        
        elif action == ResponseAction.SEND_ALERT:
            logger.warning(f"FRAUD ALERT: {event.event_type.value} - Risk: {event.risk_score}")
            return {"alert_sent": True, "severity": event.severity.value}
        
        elif action == ResponseAction.ESCALATE_TO_HUMAN:
            logger.critical(f"ESCALATING TO HUMAN: {event.event_id}")
            return {"escalated": True, "event_id": event.event_id}
        
        else:
            logger.info(f"Action {action.value} executed (default handler)")
            return {"action": action.value, "executed": True}
    
    def _correlation_loop(self) -> None:
        """Event correlation processing loop."""
        while self.is_running:
            try:
                self._detect_event_correlations()
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in correlation loop: {str(e)}")
                time.sleep(10)
    
    def _add_to_correlation_window(self, event: FraudEvent) -> None:
        """Add event to correlation window for pattern detection."""
        # Group events by user for correlation
        if event.user_id:
            key = f"user_{event.user_id}"
            if key not in self.correlation_windows:
                self.correlation_windows[key] = []
            
            self.correlation_windows[key].append(event)
            
            # Keep only recent events
            cutoff_time = datetime.now() - timedelta(minutes=self.correlation_window_minutes)
            self.correlation_windows[key] = [
                e for e in self.correlation_windows[key]
                if e.timestamp > cutoff_time
            ]
            
            # Limit window size
            if len(self.correlation_windows[key]) > self.max_correlation_events:
                self.correlation_windows[key] = self.correlation_windows[key][-self.max_correlation_events:]
    
    def _detect_event_correlations(self) -> None:
        """Detect patterns and correlations in event streams."""
        for key, events in self.correlation_windows.items():
            if len(events) < 2:
                continue
            
            # Detect velocity patterns
            self._detect_velocity_correlation(key, events)
            
            # Detect location patterns
            self._detect_location_correlation(key, events)
            
            # Detect device patterns
            self._detect_device_correlation(key, events)
    
    def _detect_velocity_correlation(self, key: str, events: List[FraudEvent]) -> None:
        """Detect velocity-based correlations."""
        # Count events in last few minutes
        recent_events = [
            e for e in events
            if (datetime.now() - e.timestamp).total_seconds() < 300  # 5 minutes
        ]
        
        if len(recent_events) >= 3:  # 3+ events in 5 minutes
            correlation_id = f"velocity_{key}_{int(time.time())}"
            
            if correlation_id not in self.active_correlations:
                correlation = EventCorrelation(
                    correlation_id=correlation_id,
                    events=recent_events,
                    pattern_type="high_velocity",
                    confidence_score=0.8,
                    created_at=datetime.now(),
                    time_window_minutes=5,
                    correlation_factors=["event_frequency", "time_proximity"]
                )
                
                self.active_correlations[correlation_id] = correlation
                self.metrics["correlations_detected"] += 1
                
                logger.warning(f"Detected high velocity pattern: {correlation_id}")
                
                # Generate correlation event
                self._generate_correlation_event(correlation)
    
    def _detect_location_correlation(self, key: str, events: List[FraudEvent]) -> None:
        """Detect location-based correlations."""
        # Look for impossible travel patterns
        location_events = [
            e for e in events
            if "location" in e.details and e.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        if len(location_events) >= 2:
            # Check for impossible travel between locations
            for i in range(len(location_events) - 1):
                event1 = location_events[i]
                event2 = location_events[i + 1]
                
                time_diff = abs((event2.timestamp - event1.timestamp).total_seconds())
                
                # If events are very close in time but from different locations
                if time_diff < 3600 and event1.details.get("location") != event2.details.get("location"):
                    correlation_id = f"location_{key}_{int(time.time())}"
                    
                    if correlation_id not in self.active_correlations:
                        correlation = EventCorrelation(
                            correlation_id=correlation_id,
                            events=[event1, event2],
                            pattern_type="impossible_travel",
                            confidence_score=0.9,
                            created_at=datetime.now(),
                            time_window_minutes=60,
                            correlation_factors=["location_distance", "time_proximity"]
                        )
                        
                        self.active_correlations[correlation_id] = correlation
                        self.metrics["correlations_detected"] += 1
                        
                        logger.warning(f"Detected impossible travel pattern: {correlation_id}")
                        
                        # Generate correlation event
                        self._generate_correlation_event(correlation)
    
    def _detect_device_correlation(self, key: str, events: List[FraudEvent]) -> None:
        """Detect device-based correlations."""
        # Look for multiple device usage patterns
        device_events = [
            e for e in events
            if "device_id" in e.details and e.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        if len(device_events) >= 2:
            unique_devices = set(e.details.get("device_id") for e in device_events)
            
            if len(unique_devices) >= 3:  # 3+ different devices in 1 hour
                correlation_id = f"device_{key}_{int(time.time())}"
                
                if correlation_id not in self.active_correlations:
                    correlation = EventCorrelation(
                        correlation_id=correlation_id,
                        events=device_events,
                        pattern_type="multiple_devices",
                        confidence_score=0.7,
                        created_at=datetime.now(),
                        time_window_minutes=60,
                        correlation_factors=["device_diversity", "time_proximity"]
                    )
                    
                    self.active_correlations[correlation_id] = correlation
                    self.metrics["correlations_detected"] += 1
                    
                    logger.warning(f"Detected multiple device pattern: {correlation_id}")
                    
                    # Generate correlation event
                    self._generate_correlation_event(correlation)
    
    def _generate_correlation_event(self, correlation: EventCorrelation) -> None:
        """Generate a new event based on detected correlation."""
        correlation_event = FraudEvent(
            event_id=f"corr_{correlation.correlation_id}",
            event_type=EventType.SUSPICIOUS_PATTERN,
            severity=EventSeverity.HIGH,
            timestamp=datetime.now(),
            source_agent="correlation_engine",
            transaction_id=None,
            user_id=correlation.events[0].user_id if correlation.events else None,
            details={
                "pattern_type": correlation.pattern_type,
                "correlated_events": [e.event_id for e in correlation.events],
                "time_window_minutes": correlation.time_window_minutes,
                "correlation_factors": correlation.correlation_factors
            },
            risk_score=0.8,
            confidence_score=correlation.confidence_score,
            evidence=[f"Correlated {len(correlation.events)} events in {correlation.time_window_minutes} minutes"]
        )
        
        # Submit the correlation event for processing
        self.submit_event(correlation_event)


def create_fraud_event(
    event_type: EventType,
    severity: EventSeverity,
    source_agent: str,
    details: Dict[str, Any],
    risk_score: float,
    confidence_score: float,
    transaction_id: str = None,
    user_id: str = None
) -> FraudEvent:
    """
    Create a fraud event.
    
    Args:
        event_type: Type of fraud event
        severity: Event severity level
        source_agent: Agent that detected the event
        details: Event details and context
        risk_score: Risk score (0.0 to 1.0)
        confidence_score: Confidence score (0.0 to 1.0)
        transaction_id: Related transaction ID (optional)
        user_id: Related user ID (optional)
        
    Returns:
        FraudEvent instance
    """
    return FraudEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        severity=severity,
        timestamp=datetime.now(),
        source_agent=source_agent,
        transaction_id=transaction_id,
        user_id=user_id,
        details=details,
        risk_score=risk_score,
        confidence_score=confidence_score,
        evidence=[]
    )


def create_response_rule(
    name: str,
    event_types: List[EventType],
    severity_threshold: EventSeverity,
    actions: List[ResponseAction],
    conditions: Dict[str, Any] = None,
    priority: int = 100,
    cooldown_seconds: int = 0
) -> ResponseRule:
    """
    Create a response rule.
    
    Args:
        name: Rule name
        event_types: Event types to match
        severity_threshold: Minimum severity to trigger
        actions: Actions to execute
        conditions: Additional conditions (optional)
        priority: Rule priority (lower = higher priority)
        cooldown_seconds: Cooldown between executions
        
    Returns:
        ResponseRule instance
    """
    return ResponseRule(
        rule_id=str(uuid.uuid4()),
        name=name,
        event_types=event_types,
        severity_threshold=severity_threshold,
        conditions=conditions or {},
        actions=actions,
        priority=priority,
        cooldown_seconds=cooldown_seconds
    )