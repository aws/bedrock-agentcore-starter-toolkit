"""
Demo script for Agent Communication Protocol

Demonstrates the agent communication capabilities including:
- Agent discovery and registration
- Inter-agent messaging
- Request-response patterns
- Broadcast notifications
- Heartbeat monitoring
"""

import sys
import os
import time
import threading
from datetime import datetime

# Add project root to path for imports
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.communication_protocol import (
    CommunicationProtocol, MessageType, MessagePriority, AgentStatus,
    RequestHandler, NotificationHandler
)


class DemoFraudAgent:
    """Demo fraud detection agent with communication capabilities."""
    
    def __init__(self, agent_id: str, agent_name: str, capabilities: list):
        """Initialize demo agent."""
        self.protocol = CommunicationProtocol(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type="fraud_detection",
            capabilities=capabilities,
            endpoint=f"demo://{agent_id}"
        )
        
        # Register message handlers
        self._setup_handlers()
        
        # Agent state
        self.processed_requests = 0
        self.received_notifications = 0
    
    def _setup_handlers(self):
        """Set up message handlers."""
        # Request handler for transaction analysis
        def handle_analysis_request(request_data):
            self.processed_requests += 1
            transaction = request_data.get("transaction", {})
            
            # Simulate analysis
            time.sleep(0.1)  # Simulate processing time
            
            # Mock fraud analysis result
            amount = transaction.get("amount", 0)
            risk_score = min(0.9, amount / 10000.0)  # Higher amounts = higher risk
            
            return {
                "transaction_id": transaction.get("id", "unknown"),
                "risk_score": risk_score,
                "decision": "flagged" if risk_score > 0.5 else "approved",
                "analysis_time": 0.1,
                "agent_id": self.protocol.agent_info.agent_id
            }
        
        request_handler = RequestHandler(handle_analysis_request)
        self.protocol.register_handler(MessageType.REQUEST, request_handler)
        
        # Notification handler for alerts
        def handle_alert_notification(payload):
            self.received_notifications += 1
            alert_type = payload.get("alert_type", "unknown")
            severity = payload.get("severity", "medium")
            
            print(f"  [{self.protocol.agent_info.agent_id}] Received {severity} alert: {alert_type}")
        
        notification_handler = NotificationHandler(handle_alert_notification)
        self.protocol.register_handler(MessageType.NOTIFICATION, notification_handler)
    
    def start(self):
        """Start the agent."""
        self.protocol.start()
        print(f"Started agent: {self.protocol.agent_info.agent_name} ({self.protocol.agent_info.agent_id})")
    
    def stop(self):
        """Stop the agent."""
        self.protocol.stop()
        print(f"Stopped agent: {self.protocol.agent_info.agent_name}")
    
    def get_stats(self):
        """Get agent statistics."""
        return {
            "agent_id": self.protocol.agent_info.agent_id,
            "agent_name": self.protocol.agent_info.agent_name,
            "status": self.protocol.agent_info.status.value,
            "processed_requests": self.processed_requests,
            "received_notifications": self.received_notifications,
            "known_agents": len(self.protocol.known_agents)
        }


def demo_agent_discovery():
    """Demonstrate agent discovery and registration."""
    print("=" * 60)
    print("AGENT COMMUNICATION DEMO - DISCOVERY & REGISTRATION")
    print("=" * 60)
    
    # Create multiple agents
    agents = [
        DemoFraudAgent("transaction_analyzer", "Transaction Analyzer", ["transaction_analysis", "risk_scoring"]),
        DemoFraudAgent("pattern_detector", "Pattern Detector", ["pattern_detection", "anomaly_detection"]),
        DemoFraudAgent("compliance_checker", "Compliance Checker", ["compliance_checking", "audit_trail"])
    ]
    
    print(f"\nStarting {len(agents)} agents...")
    
    # Start all agents
    for agent in agents:
        agent.start()
        time.sleep(0.5)  # Stagger startup
    
    # Wait for discovery
    print("\nWaiting for agent discovery...")
    time.sleep(3)
    
    # Show discovered agents
    print(f"\nAgent Discovery Results:")
    for agent in agents:
        known_agents = agent.protocol.discover_agents()
        print(f"\n{agent.protocol.agent_info.agent_name}:")
        print(f"  Known Agents: {len(known_agents)}")
        
        for known_agent in known_agents:
            print(f"    • {known_agent.agent_name} ({known_agent.agent_id})")
            print(f"      Type: {known_agent.agent_type}")
            print(f"      Status: {known_agent.status.value}")
            print(f"      Capabilities: {', '.join(known_agent.capabilities)}")
    
    # Test capability-based discovery
    print(f"\n--- Capability-Based Discovery ---")
    analyzer = agents[0]
    
    # Find agents with specific capabilities
    pattern_agents = analyzer.protocol.get_agents_by_capability("pattern_detection")
    compliance_agents = analyzer.protocol.get_agents_by_capability("compliance_checking")
    
    print(f"Agents with pattern detection: {len(pattern_agents)}")
    for agent in pattern_agents:
        print(f"  • {agent.agent_name}")
    
    print(f"Agents with compliance checking: {len(compliance_agents)}")
    for agent in compliance_agents:
        print(f"  • {agent.agent_name}")
    
    # Stop all agents
    print(f"\nStopping agents...")
    for agent in agents:
        agent.stop()


def demo_request_response():
    """Demonstrate request-response communication pattern."""
    print("\n" + "=" * 60)
    print("AGENT COMMUNICATION DEMO - REQUEST-RESPONSE")
    print("=" * 60)
    
    # Create requester and responder agents
    requester = DemoFraudAgent("fraud_coordinator", "Fraud Coordinator", ["coordination", "decision_making"])
    analyzer = DemoFraudAgent("transaction_analyzer", "Transaction Analyzer", ["transaction_analysis"])
    
    print("\nStarting requester and analyzer agents...")
    requester.start()
    analyzer.start()
    
    # Wait for discovery
    time.sleep(2)
    
    # Sample transactions to analyze
    transactions = [
        {"id": "tx_001", "amount": 150.00, "merchant": "Coffee Shop", "user_id": "user_123"},
        {"id": "tx_002", "amount": 5000.00, "merchant": "Electronics Store", "user_id": "user_456"},
        {"id": "tx_003", "amount": 25.00, "merchant": "Gas Station", "user_id": "user_789"},
        {"id": "tx_004", "amount": 15000.00, "merchant": "Luxury Cars", "user_id": "user_101"}
    ]
    
    print(f"\nSending {len(transactions)} analysis requests...")
    
    # Send analysis requests
    correlation_ids = []
    for transaction in transactions:
        print(f"\nRequesting analysis for transaction {transaction['id']}:")
        print(f"  Amount: ${transaction['amount']:.2f}")
        print(f"  Merchant: {transaction['merchant']}")
        
        correlation_id = requester.protocol.send_request(
            recipient_id="transaction_analyzer",
            request_type="analyze_transaction",
            request_data={"transaction": transaction},
            timeout_seconds=10
        )
        
        correlation_ids.append(correlation_id)
        print(f"  Request sent with correlation ID: {correlation_id}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Wait for processing
    print(f"\nWaiting for analysis results...")
    time.sleep(3)
    
    # Check agent statistics
    print(f"\n--- Agent Statistics ---")
    requester_stats = requester.get_stats()
    analyzer_stats = analyzer.get_stats()
    
    print(f"Requester ({requester_stats['agent_name']}):")
    print(f"  Status: {requester_stats['status']}")
    print(f"  Known Agents: {requester_stats['known_agents']}")
    
    print(f"\nAnalyzer ({analyzer_stats['agent_name']}):")
    print(f"  Status: {analyzer_stats['status']}")
    print(f"  Processed Requests: {analyzer_stats['processed_requests']}")
    print(f"  Known Agents: {analyzer_stats['known_agents']}")
    
    # Stop agents
    requester.stop()
    analyzer.stop()


def demo_broadcast_notifications():
    """Demonstrate broadcast notification system."""
    print("\n" + "=" * 60)
    print("AGENT COMMUNICATION DEMO - BROADCAST NOTIFICATIONS")
    print("=" * 60)
    
    # Create multiple agents
    agents = [
        DemoFraudAgent("alert_manager", "Alert Manager", ["alert_management", "notification"]),
        DemoFraudAgent("fraud_monitor_1", "Fraud Monitor 1", ["monitoring", "analysis"]),
        DemoFraudAgent("fraud_monitor_2", "Fraud Monitor 2", ["monitoring", "analysis"]),
        DemoFraudAgent("compliance_monitor", "Compliance Monitor", ["compliance", "monitoring"])
    ]
    
    print(f"\nStarting {len(agents)} agents...")
    
    # Start all agents
    for agent in agents:
        agent.start()
        time.sleep(0.3)
    
    # Wait for discovery
    time.sleep(2)
    
    # Alert manager sends various notifications
    alert_manager = agents[0]
    
    # Sample alerts to broadcast
    alerts = [
        {
            "alert_type": "high_risk_transaction",
            "severity": "high",
            "transaction_id": "tx_suspicious_001",
            "risk_score": 0.95,
            "description": "Unusually high transaction amount detected"
        },
        {
            "alert_type": "velocity_fraud",
            "severity": "medium",
            "user_id": "user_velocity_001",
            "transaction_count": 15,
            "description": "Multiple rapid transactions detected"
        },
        {
            "alert_type": "compliance_violation",
            "severity": "critical",
            "violation_type": "data_retention",
            "description": "Data retention policy violation detected"
        },
        {
            "alert_type": "system_maintenance",
            "severity": "low",
            "maintenance_window": "2024-01-15 02:00-04:00",
            "description": "Scheduled system maintenance notification"
        }
    ]
    
    print(f"\nBroadcasting {len(alerts)} alerts...")
    
    for alert in alerts:
        print(f"\nBroadcasting {alert['severity']} alert: {alert['alert_type']}")
        print(f"  Description: {alert['description']}")
        
        # Broadcast alert notification
        message_id = alert_manager.protocol.broadcast_message(
            message_type=MessageType.NOTIFICATION,
            payload=alert,
            priority=MessagePriority.HIGH if alert['severity'] == 'critical' else MessagePriority.NORMAL
        )
        
        print(f"  Broadcast message ID: {message_id}")
        
        # Wait between alerts
        time.sleep(1)
    
    # Wait for processing
    print(f"\nWaiting for alert processing...")
    time.sleep(2)
    
    # Show notification statistics
    print(f"\n--- Notification Statistics ---")
    for agent in agents:
        stats = agent.get_stats()
        print(f"{stats['agent_name']}:")
        print(f"  Received Notifications: {stats['received_notifications']}")
    
    # Stop all agents
    print(f"\nStopping agents...")
    for agent in agents:
        agent.stop()


def demo_heartbeat_monitoring():
    """Demonstrate heartbeat monitoring and agent health."""
    print("\n" + "=" * 60)
    print("AGENT COMMUNICATION DEMO - HEARTBEAT MONITORING")
    print("=" * 60)
    
    # Create agents with different behaviors
    stable_agent = DemoFraudAgent("stable_agent", "Stable Agent", ["analysis"])
    monitor_agent = DemoFraudAgent("monitor_agent", "Monitor Agent", ["monitoring"])
    
    print("\nStarting agents for heartbeat monitoring...")
    stable_agent.start()
    monitor_agent.start()
    
    # Wait for initial discovery
    time.sleep(2)
    
    print(f"\nMonitoring agent heartbeats...")
    
    # Monitor for several heartbeat cycles
    for cycle in range(1, 4):
        print(f"\n--- Heartbeat Cycle {cycle} ---")
        
        # Check known agents and their last heartbeat
        known_agents = monitor_agent.protocol.known_agents
        
        for agent_id, agent_info in known_agents.items():
            time_since_heartbeat = (datetime.now() - agent_info.last_heartbeat).total_seconds()
            
            print(f"Agent: {agent_info.agent_name}")
            print(f"  Status: {agent_info.status.value}")
            print(f"  Last Heartbeat: {time_since_heartbeat:.1f} seconds ago")
            print(f"  Load Factor: {agent_info.load_factor:.2f}")
        
        # Wait for next cycle
        time.sleep(5)
    
    # Simulate agent going offline
    print(f"\n--- Simulating Agent Offline ---")
    print("Stopping stable agent to simulate offline condition...")
    stable_agent.stop()
    
    # Wait and check again
    time.sleep(10)
    
    print(f"\nChecking agent status after offline simulation...")
    known_agents = monitor_agent.protocol.known_agents
    
    for agent_id, agent_info in known_agents.items():
        time_since_heartbeat = (datetime.now() - agent_info.last_heartbeat).total_seconds()
        
        print(f"Agent: {agent_info.agent_name}")
        print(f"  Status: {agent_info.status.value}")
        print(f"  Last Heartbeat: {time_since_heartbeat:.1f} seconds ago")
        
        if time_since_heartbeat > 60:
            print(f"  ⚠️  Agent appears to be offline (no heartbeat for {time_since_heartbeat:.1f}s)")
    
    # Stop remaining agents
    monitor_agent.stop()


def demo_message_delivery_tracking():
    """Demonstrate message delivery tracking and status monitoring."""
    print("\n" + "=" * 60)
    print("AGENT COMMUNICATION DEMO - MESSAGE DELIVERY TRACKING")
    print("=" * 60)
    
    # Create sender and receiver agents
    sender = DemoFraudAgent("message_sender", "Message Sender", ["communication"])
    receiver = DemoFraudAgent("message_receiver", "Message Receiver", ["processing"])
    
    print("\nStarting sender and receiver agents...")
    sender.start()
    receiver.start()
    
    # Wait for discovery
    time.sleep(2)
    
    # Send various types of messages
    messages = [
        {
            "type": MessageType.NOTIFICATION,
            "payload": {"alert": "test_alert", "priority": "low"},
            "priority": MessagePriority.LOW
        },
        {
            "type": MessageType.REQUEST,
            "payload": {"request_type": "status_check", "data": {}},
            "priority": MessagePriority.NORMAL
        },
        {
            "type": MessageType.NOTIFICATION,
            "payload": {"alert": "critical_alert", "priority": "high"},
            "priority": MessagePriority.CRITICAL
        }
    ]
    
    print(f"\nSending {len(messages)} messages with delivery tracking...")
    
    message_ids = []
    for i, msg in enumerate(messages):
        print(f"\nSending message {i+1}:")
        print(f"  Type: {msg['type'].value}")
        print(f"  Priority: {msg['priority'].value}")
        
        message_id = sender.protocol.send_message(
            recipient_id="message_receiver",
            message_type=msg['type'],
            payload=msg['payload'],
            priority=msg['priority']
        )
        
        message_ids.append(message_id)
        print(f"  Message ID: {message_id}")
        
        time.sleep(0.5)
    
    # Wait for delivery
    print(f"\nWaiting for message delivery...")
    time.sleep(3)
    
    # Check delivery status
    print(f"\n--- Message Delivery Status ---")
    for i, message_id in enumerate(message_ids):
        delivery = sender.protocol.get_message_delivery_status(message_id)
        
        if delivery:
            print(f"Message {i+1} ({message_id}):")
            print(f"  Status: {delivery.status.value}")
            print(f"  Recipient: {delivery.recipient_id}")
            
            if delivery.delivery_time_ms:
                print(f"  Delivery Time: {delivery.delivery_time_ms:.1f}ms")
            
            if delivery.error_message:
                print(f"  Error: {delivery.error_message}")
        else:
            print(f"Message {i+1}: No delivery tracking found")
    
    # Stop agents
    sender.stop()
    receiver.stop()


def main():
    """Run all agent communication demos."""
    print("🤖 AGENT COMMUNICATION PROTOCOL DEMONSTRATION")
    print("This demo showcases inter-agent communication capabilities")
    print("for coordinated fraud detection including discovery, messaging,")
    print("and monitoring in a multi-agent system.")
    
    try:
        demo_agent_discovery()
        demo_request_response()
        demo_broadcast_notifications()
        demo_heartbeat_monitoring()
        demo_message_delivery_tracking()
        
        print("\n" + "=" * 60)
        print("✅ AGENT COMMUNICATION DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe agent communication protocol demonstrated:")
        print("• Agent discovery and registration")
        print("• Request-response communication patterns")
        print("• Broadcast notification system")
        print("• Heartbeat monitoring and health tracking")
        print("• Message delivery tracking and status monitoring")
        print("• Capability-based agent discovery")
        print("• Multi-agent coordination and messaging")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()