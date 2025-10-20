"""
Unit tests for Agent Communication Protocol.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.communication_protocol import (
    CommunicationProtocol, Message, MessageType, MessagePriority, AgentStatus,
    AgentInfo, MessageDelivery, MessageDeliveryStatus, RequestHandler, NotificationHandler
)


@pytest.fixture
def agent_protocol():
    """Create communication protocol for testing."""
    return CommunicationProtocol(
        agent_id="test_agent_001",
        agent_name="Test Agent",
        agent_type="fraud_detection",
        capabilities=["transaction_analysis", "pattern_detection"],
        endpoint="test://localhost:8001"
    )


@pytest.fixture
def sample_message():
    """Create sample message for testing."""
    return Message(
        message_id="msg_123",
        message_type=MessageType.REQUEST,
        sender_id="sender_001",
        recipient_id="recipient_001",
        payload={"request_type": "analyze_transaction", "data": {"amount": 100.0}},
        timestamp=datetime.now(),
        priority=MessagePriority.HIGH,
        correlation_id="corr_456"
    )


@pytest.fixture
def sample_agent_info():
    """Create sample agent info for testing."""
    return AgentInfo(
        agent_id="agent_002",
        agent_name="Pattern Detection Agent",
        agent_type="pattern_detection",
        capabilities=["pattern_analysis", "anomaly_detection"],
        status=AgentStatus.ONLINE,
        endpoint="test://localhost:8002",
        last_heartbeat=datetime.now(),
        load_factor=0.3
    )


class TestMessage:
    """Test cases for Message class."""
    
    def test_message_creation(self):
        """Test creating a message."""
        message = Message(
            message_id="test_msg",
            message_type=MessageType.NOTIFICATION,
            sender_id="sender",
            recipient_id="recipient",
            payload={"data": "test"},
            timestamp=datetime.now()
        )
        
        assert message.message_id == "test_msg"
        assert message.message_type == MessageType.NOTIFICATION
        assert message.sender_id == "sender"
        assert message.recipient_id == "recipient"
        assert message.payload["data"] == "test"
    
    def test_message_serialization(self, sample_message):
        """Test message serialization and deserialization."""
        # Serialize to dict
        message_dict = sample_message.to_dict()
        
        assert message_dict["message_id"] == "msg_123"
        assert message_dict["message_type"] == "request"
        assert message_dict["priority"] == 3  # HIGH priority value
        assert isinstance(message_dict["timestamp"], str)
        
        # Deserialize from dict
        restored_message = Message.from_dict(message_dict)
        
        assert restored_message.message_id == sample_message.message_id
        assert restored_message.message_type == sample_message.message_type
        assert restored_message.sender_id == sample_message.sender_id
        assert restored_message.priority == sample_message.priority
    
    def test_message_expiration(self):
        """Test message expiration logic."""
        # Create expired message
        expired_message = Message(
            message_id="expired",
            message_type=MessageType.REQUEST,
            sender_id="sender",
            recipient_id="recipient",
            payload={},
            timestamp=datetime.now(),
            expires_at=datetime.now() - timedelta(seconds=1)
        )
        
        assert expired_message.is_expired() is True
        
        # Create non-expired message
        valid_message = Message(
            message_id="valid",
            message_type=MessageType.REQUEST,
            sender_id="sender",
            recipient_id="recipient",
            payload={},
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=60)
        )
        
        assert valid_message.is_expired() is False
    
    def test_message_retry_logic(self):
        """Test message retry logic."""
        message = Message(
            message_id="retry_test",
            message_type=MessageType.REQUEST,
            sender_id="sender",
            recipient_id="recipient",
            payload={},
            timestamp=datetime.now(),
            max_retries=3
        )
        
        # Should be able to retry initially
        assert message.can_retry() is True
        
        # Increment retry count
        message.retry_count = 2
        assert message.can_retry() is True
        
        # Exceed max retries
        message.retry_count = 3
        assert message.can_retry() is False


class TestAgentInfo:
    """Test cases for AgentInfo class."""
    
    def test_agent_info_creation(self, sample_agent_info):
        """Test creating agent info."""
        assert sample_agent_info.agent_id == "agent_002"
        assert sample_agent_info.agent_name == "Pattern Detection Agent"
        assert sample_agent_info.status == AgentStatus.ONLINE
        assert "pattern_analysis" in sample_agent_info.capabilities
    
    def test_agent_info_serialization(self, sample_agent_info):
        """Test agent info serialization."""
        # Serialize to dict
        agent_dict = sample_agent_info.to_dict()
        
        assert agent_dict["agent_id"] == "agent_002"
        assert agent_dict["status"] == "online"
        assert isinstance(agent_dict["last_heartbeat"], str)
        
        # Deserialize from dict
        restored_agent = AgentInfo.from_dict(agent_dict)
        
        assert restored_agent.agent_id == sample_agent_info.agent_id
        assert restored_agent.status == sample_agent_info.status
        assert restored_agent.capabilities == sample_agent_info.capabilities


class TestCommunicationProtocol:
    """Test cases for CommunicationProtocol class."""
    
    def test_protocol_initialization(self, agent_protocol):
        """Test protocol initialization."""
        assert agent_protocol.agent_info.agent_id == "test_agent_001"
        assert agent_protocol.agent_info.agent_name == "Test Agent"
        assert agent_protocol.agent_info.agent_type == "fraud_detection"
        assert agent_protocol.agent_info.status == AgentStatus.OFFLINE
        assert "transaction_analysis" in agent_protocol.agent_info.capabilities
    
    def test_protocol_start_stop(self, agent_protocol):
        """Test starting and stopping the protocol."""
        # Initially offline
        assert agent_protocol.agent_info.status == AgentStatus.OFFLINE
        assert agent_protocol.is_running is False
        
        # Start protocol
        agent_protocol.start()
        assert agent_protocol.agent_info.status == AgentStatus.ONLINE
        assert agent_protocol.is_running is True
        
        # Stop protocol
        agent_protocol.stop()
        assert agent_protocol.agent_info.status == AgentStatus.OFFLINE
        assert agent_protocol.is_running is False
    
    def test_message_handler_registration(self, agent_protocol):
        """Test registering message handlers."""
        # Create mock handler
        handler = Mock()
        
        # Register handler
        agent_protocol.register_handler(MessageType.REQUEST, handler)
        
        # Verify handler is registered
        assert MessageType.REQUEST in agent_protocol.message_handlers
        assert handler in agent_protocol.message_handlers[MessageType.REQUEST]
    
    def test_send_message(self, agent_protocol):
        """Test sending messages."""
        # Send message
        message_id = agent_protocol.send_message(
            recipient_id="target_agent",
            message_type=MessageType.NOTIFICATION,
            payload={"alert": "fraud_detected"},
            priority=MessagePriority.HIGH
        )
        
        # Verify message is queued
        assert message_id is not None
        assert message_id in agent_protocol.delivery_tracking
        
        # Check delivery tracking
        delivery = agent_protocol.delivery_tracking[message_id]
        assert delivery.recipient_id == "target_agent"
        assert delivery.status == MessageDeliveryStatus.PENDING
    
    def test_broadcast_message(self, agent_protocol):
        """Test broadcasting messages."""
        # Add some known agents
        agent_protocol.known_agents["agent_1"] = AgentInfo(
            agent_id="agent_1", agent_name="Agent 1", agent_type="test",
            capabilities=[], status=AgentStatus.ONLINE, endpoint="test1",
            last_heartbeat=datetime.now()
        )
        
        # Broadcast message
        message_id = agent_protocol.broadcast_message(
            message_type=MessageType.DISCOVERY,
            payload={"discover": True}
        )
        
        assert message_id is not None
    
    def test_send_request_response(self, agent_protocol):
        """Test request-response pattern."""
        # Send request
        correlation_id = agent_protocol.send_request(
            recipient_id="service_agent",
            request_type="analyze_pattern",
            request_data={"pattern_id": "pattern_123"},
            timeout_seconds=30
        )
        
        assert correlation_id is not None
        
        # Send response
        response_id = agent_protocol.send_response(
            recipient_id="requester_agent",
            correlation_id=correlation_id,
            response_data={"analysis_result": "fraud_detected"},
            success=True
        )
        
        assert response_id is not None
    
    def test_agent_discovery(self, agent_protocol, sample_agent_info):
        """Test agent discovery functionality."""
        # Add agent to known agents
        agent_protocol.known_agents[sample_agent_info.agent_id] = sample_agent_info
        
        # Discover all agents
        agents = agent_protocol.discover_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == sample_agent_info.agent_id
        
        # Discover by type
        pattern_agents = agent_protocol.discover_agents("pattern_detection")
        assert len(pattern_agents) == 1
        
        fraud_agents = agent_protocol.discover_agents("fraud_detection")
        assert len(fraud_agents) == 0
    
    def test_get_agents_by_capability(self, agent_protocol, sample_agent_info):
        """Test getting agents by capability."""
        # Add agent to known agents
        agent_protocol.known_agents[sample_agent_info.agent_id] = sample_agent_info
        
        # Find agents with specific capability
        pattern_agents = agent_protocol.get_agents_by_capability("pattern_analysis")
        assert len(pattern_agents) == 1
        assert pattern_agents[0].agent_id == sample_agent_info.agent_id
        
        # Find agents with non-existent capability
        ml_agents = agent_protocol.get_agents_by_capability("machine_learning")
        assert len(ml_agents) == 0
    
    def test_discovery_callback(self, agent_protocol):
        """Test agent discovery callbacks."""
        callback_called = False
        discovered_agent = None
        
        def discovery_callback(agent_info):
            nonlocal callback_called, discovered_agent
            callback_called = True
            discovered_agent = agent_info
        
        # Register callback
        agent_protocol.register_discovery_callback(discovery_callback)
        
        # Simulate agent registration
        new_agent = AgentInfo(
            agent_id="new_agent",
            agent_name="New Agent",
            agent_type="test",
            capabilities=["testing"],
            status=AgentStatus.ONLINE,
            endpoint="test://new",
            last_heartbeat=datetime.now()
        )
        
        # Simulate registration message
        registration_message = Message(
            message_id="reg_msg",
            message_type=MessageType.REGISTRATION,
            sender_id="new_agent",
            recipient_id=None,
            payload={"agent_info": new_agent.to_dict(), "action": "register"},
            timestamp=datetime.now()
        )
        
        agent_protocol._handle_registration(registration_message)
        
        # Verify callback was called
        assert callback_called is True
        assert discovered_agent.agent_id == "new_agent"
    
    def test_message_delivery_tracking(self, agent_protocol):
        """Test message delivery status tracking."""
        # Send message
        message_id = agent_protocol.send_message(
            recipient_id="target",
            message_type=MessageType.NOTIFICATION,
            payload={"test": True}
        )
        
        # Check initial status
        delivery = agent_protocol.get_message_delivery_status(message_id)
        assert delivery is not None
        assert delivery.status == MessageDeliveryStatus.PENDING
        
        # Update delivery status
        agent_protocol._update_delivery_status(
            message_id,
            MessageDeliveryStatus.DELIVERED,
            delivery_time_ms=150.0
        )
        
        # Check updated status
        delivery = agent_protocol.get_message_delivery_status(message_id)
        assert delivery.status == MessageDeliveryStatus.DELIVERED
        assert delivery.delivery_time_ms == 150.0
    
    def test_receive_message(self, agent_protocol, sample_message):
        """Test receiving external messages."""
        # Serialize message
        message_data = sample_message.to_dict()
        
        # Receive message
        agent_protocol.receive_message(message_data)
        
        # Message should be in queue (we can't easily test queue contents)
        # but we can verify no exceptions were raised
        assert True
    
    def test_heartbeat_handling(self, agent_protocol):
        """Test heartbeat message handling."""
        # Create heartbeat message
        agent_info = AgentInfo(
            agent_id="heartbeat_agent",
            agent_name="Heartbeat Agent",
            agent_type="test",
            capabilities=[],
            status=AgentStatus.ONLINE,
            endpoint="test://heartbeat",
            last_heartbeat=datetime.now()
        )
        
        heartbeat_message = Message(
            message_id="hb_msg",
            message_type=MessageType.HEARTBEAT,
            sender_id="heartbeat_agent",
            recipient_id=None,
            payload={"agent_info": agent_info.to_dict()},
            timestamp=datetime.now()
        )
        
        # Handle heartbeat
        agent_protocol._handle_heartbeat(heartbeat_message)
        
        # Verify agent was added/updated
        assert "heartbeat_agent" in agent_protocol.known_agents
        assert agent_protocol.known_agents["heartbeat_agent"].agent_id == "heartbeat_agent"


class TestRequestHandler:
    """Test cases for RequestHandler."""
    
    def test_request_handler_success(self):
        """Test successful request handling."""
        def handle_request(request_data):
            return {"result": f"processed_{request_data.get('id', 'unknown')}"}
        
        handler = RequestHandler(handle_request)
        
        # Create request message
        request_message = Message(
            message_id="req_msg",
            message_type=MessageType.REQUEST,
            sender_id="requester",
            recipient_id="handler",
            payload={"request_data": {"id": "test_123"}},
            timestamp=datetime.now(),
            correlation_id="corr_123"
        )
        
        # Handle request
        import asyncio
        response = asyncio.run(handler.handle_message(request_message))
        
        # Verify response
        assert response is not None
        assert response.message_type == MessageType.RESPONSE
        assert response.sender_id == "handler"
        assert response.recipient_id == "requester"
        assert response.correlation_id == "corr_123"
        assert response.payload["success"] is True
        assert response.payload["response_data"]["result"] == "processed_test_123"
    
    def test_request_handler_error(self):
        """Test request handler error handling."""
        def handle_request(request_data):
            raise ValueError("Test error")
        
        handler = RequestHandler(handle_request)
        
        request_message = Message(
            message_id="req_msg",
            message_type=MessageType.REQUEST,
            sender_id="requester",
            recipient_id="handler",
            payload={"request_data": {}},
            timestamp=datetime.now(),
            correlation_id="corr_123"
        )
        
        # Handle request
        import asyncio
        response = asyncio.run(handler.handle_message(request_message))
        
        # Verify error response
        assert response is not None
        assert response.payload["success"] is False
        assert "Test error" in response.payload["error_message"]


class TestNotificationHandler:
    """Test cases for NotificationHandler."""
    
    def test_notification_handler(self):
        """Test notification handling."""
        received_payload = None
        
        def handle_notification(payload):
            nonlocal received_payload
            received_payload = payload
        
        handler = NotificationHandler(handle_notification)
        
        notification_message = Message(
            message_id="notif_msg",
            message_type=MessageType.NOTIFICATION,
            sender_id="notifier",
            recipient_id="handler",
            payload={"alert": "fraud_detected", "severity": "high"},
            timestamp=datetime.now()
        )
        
        # Handle notification
        import asyncio
        response = asyncio.run(handler.handle_message(notification_message))
        
        # Verify notification was processed
        assert received_payload is not None
        assert received_payload["alert"] == "fraud_detected"
        assert received_payload["severity"] == "high"
        assert response is None  # No response for notifications


if __name__ == "__main__":
    pytest.main([__file__])