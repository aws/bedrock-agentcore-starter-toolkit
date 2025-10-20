"""
Agent Communication Protocol

Provides standardized communication framework for inter-agent messaging,
discovery, registration, and coordination in the fraud detection system.
"""

import logging
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    REGISTRATION = "registration"
    DEREGISTRATION = "deregistration"
    ERROR = "error"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AgentStatus(Enum):
    """Agent status for coordination."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class MessageDeliveryStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AgentInfo:
    """Information about an agent in the system."""
    agent_id: str
    agent_name: str
    agent_type: str
    capabilities: List[str]
    status: AgentStatus
    endpoint: str
    last_heartbeat: datetime
    load_factor: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentInfo':
        """Create from dictionary."""
        data = data.copy()
        data['status'] = AgentStatus(data['status'])
        data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
        return cls(**data)


@dataclass
class Message:
    """Inter-agent communication message."""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    payload: Dict[str, Any]
    timestamp: datetime
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['priority'] = self.priority.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        data = data.copy()
        data['message_type'] = MessageType(data['message_type'])
        data['priority'] = MessagePriority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < self.max_retries


@dataclass
class MessageDelivery:
    """Message delivery tracking."""
    message_id: str
    recipient_id: str
    status: MessageDeliveryStatus
    timestamp: datetime
    error_message: Optional[str] = None
    delivery_time_ms: Optional[float] = None


class MessageHandler(ABC):
    """Abstract base class for message handlers."""
    
    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[Message]:
        """
        Handle incoming message and optionally return response.
        
        Args:
            message: Incoming message to handle
            
        Returns:
            Optional response message
        """
        pass


class CommunicationProtocol:
    """
    Agent communication protocol implementation.
    
    Provides standardized messaging, discovery, and coordination
    capabilities for the multi-agent fraud detection system.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        capabilities: List[str],
        endpoint: str = "local"
    ):
        """
        Initialize communication protocol.
        
        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            agent_type: Type/category of agent
            capabilities: List of agent capabilities
            endpoint: Communication endpoint
        """
        self.agent_info = AgentInfo(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            capabilities=capabilities,
            status=AgentStatus.OFFLINE,
            endpoint=endpoint,
            last_heartbeat=datetime.now()
        )
        
        # Message handling
        self.message_handlers: Dict[MessageType, List[MessageHandler]] = {}
        self.message_queue = Queue()
        self.outbound_queue = Queue()
        self.delivery_tracking: Dict[str, MessageDelivery] = {}
        
        # Agent registry
        self.known_agents: Dict[str, AgentInfo] = {}
        self.agent_discovery_callbacks: List[Callable[[AgentInfo], None]] = []
        
        # Communication state
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.heartbeat_interval = 30  # seconds
        self.message_timeout = 60  # seconds
        
        logger.info(f"Initialized communication protocol for agent {agent_id}")
    
    def start(self) -> None:
        """Start the communication protocol."""
        if self.is_running:
            return
        
        self.is_running = True
        self.agent_info.status = AgentStatus.ONLINE
        
        # Start background threads
        self.executor.submit(self._message_processor)
        self.executor.submit(self._outbound_processor)
        self.executor.submit(self._heartbeat_sender)
        self.executor.submit(self._cleanup_expired_messages)
        
        # Send registration message
        self._send_registration()
        
        logger.info(f"Communication protocol started for agent {self.agent_info.agent_id}")
    
    def stop(self) -> None:
        """Stop the communication protocol."""
        if not self.is_running:
            return
        
        # Send deregistration message
        self._send_deregistration()
        
        self.is_running = False
        self.agent_info.status = AgentStatus.OFFLINE
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info(f"Communication protocol stopped for agent {self.agent_info.agent_id}")
    
    def register_handler(self, message_type: MessageType, handler: MessageHandler) -> None:
        """
        Register a message handler for specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Handler instance
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type.value} messages")
    
    def send_message(
        self,
        recipient_id: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> str:
        """
        Send message to another agent.
        
        Args:
            recipient_id: Target agent ID
            message_type: Type of message
            payload: Message payload
            priority: Message priority
            correlation_id: Optional correlation ID for request/response
            timeout_seconds: Message timeout
            
        Returns:
            Message ID for tracking
        """
        message_id = str(uuid.uuid4())
        expires_at = None
        if timeout_seconds:
            expires_at = datetime.now() + timedelta(seconds=timeout_seconds)
        
        message = Message(
            message_id=message_id,
            message_type=message_type,
            sender_id=self.agent_info.agent_id,
            recipient_id=recipient_id,
            payload=payload,
            timestamp=datetime.now(),
            priority=priority,
            correlation_id=correlation_id,
            expires_at=expires_at
        )
        
        # Add to outbound queue
        self.outbound_queue.put(message)
        
        # Track delivery
        self.delivery_tracking[message_id] = MessageDelivery(
            message_id=message_id,
            recipient_id=recipient_id,
            status=MessageDeliveryStatus.PENDING,
            timestamp=datetime.now()
        )
        
        logger.debug(f"Queued message {message_id} to {recipient_id}")
        return message_id
    
    def broadcast_message(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """
        Broadcast message to all known agents.
        
        Args:
            message_type: Type of message
            payload: Message payload
            priority: Message priority
            
        Returns:
            Message ID for tracking
        """
        message_id = str(uuid.uuid4())
        
        message = Message(
            message_id=message_id,
            message_type=message_type,
            sender_id=self.agent_info.agent_id,
            recipient_id=None,  # Broadcast
            payload=payload,
            timestamp=datetime.now(),
            priority=priority
        )
        
        self.outbound_queue.put(message)
        logger.debug(f"Queued broadcast message {message_id}")
        return message_id
    
    def send_request(
        self,
        recipient_id: str,
        request_type: str,
        request_data: Dict[str, Any],
        timeout_seconds: int = 30
    ) -> str:
        """
        Send request message and return correlation ID for response tracking.
        
        Args:
            recipient_id: Target agent ID
            request_type: Type of request
            request_data: Request data
            timeout_seconds: Request timeout
            
        Returns:
            Correlation ID for response tracking
        """
        correlation_id = str(uuid.uuid4())
        
        payload = {
            "request_type": request_type,
            "request_data": request_data
        }
        
        self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.REQUEST,
            payload=payload,
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds
        )
        
        return correlation_id
    
    def send_response(
        self,
        recipient_id: str,
        correlation_id: str,
        response_data: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Send response message.
        
        Args:
            recipient_id: Target agent ID
            correlation_id: Correlation ID from original request
            response_data: Response data
            success: Whether request was successful
            error_message: Error message if unsuccessful
            
        Returns:
            Message ID
        """
        payload = {
            "success": success,
            "response_data": response_data,
            "error_message": error_message
        }
        
        return self.send_message(
            recipient_id=recipient_id,
            message_type=MessageType.RESPONSE,
            payload=payload,
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id
        )
    
    def discover_agents(self, agent_type: Optional[str] = None) -> List[AgentInfo]:
        """
        Discover available agents.
        
        Args:
            agent_type: Optional filter by agent type
            
        Returns:
            List of discovered agents
        """
        # Send discovery message
        payload = {"agent_type_filter": agent_type} if agent_type else {}
        self.broadcast_message(MessageType.DISCOVERY, payload)
        
        # Return currently known agents
        agents = list(self.known_agents.values())
        if agent_type:
            agents = [agent for agent in agents if agent.agent_type == agent_type]
        
        return agents
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Get information about a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information or None if not found
        """
        return self.known_agents.get(agent_id)
    
    def get_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """
        Get agents that have a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of agents with the capability
        """
        return [
            agent for agent in self.known_agents.values()
            if capability in agent.capabilities and agent.status == AgentStatus.ONLINE
        ]
    
    def register_discovery_callback(self, callback: Callable[[AgentInfo], None]) -> None:
        """
        Register callback for agent discovery events.
        
        Args:
            callback: Function to call when new agent is discovered
        """
        self.agent_discovery_callbacks.append(callback)
    
    def get_message_delivery_status(self, message_id: str) -> Optional[MessageDelivery]:
        """
        Get delivery status for a message.
        
        Args:
            message_id: Message identifier
            
        Returns:
            Delivery status or None if not found
        """
        return self.delivery_tracking.get(message_id)
    
    def receive_message(self, message_data: Dict[str, Any]) -> None:
        """
        Receive message from external source.
        
        Args:
            message_data: Serialized message data
        """
        try:
            message = Message.from_dict(message_data)
            self.message_queue.put(message)
            logger.debug(f"Received message {message.message_id} from {message.sender_id}")
        except Exception as e:
            logger.error(f"Failed to deserialize message: {str(e)}")
    
    def _message_processor(self) -> None:
        """Process incoming messages."""
        while self.is_running:
            try:
                message = self.message_queue.get(timeout=1.0)
                self._handle_message(message)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
    
    def _handle_message(self, message: Message) -> None:
        """Handle individual message."""
        try:
            # Check if message is expired
            if message.is_expired():
                logger.warning(f"Received expired message {message.message_id}")
                return
            
            # Handle system messages
            if message.message_type == MessageType.REGISTRATION:
                self._handle_registration(message)
            elif message.message_type == MessageType.DEREGISTRATION:
                self._handle_deregistration(message)
            elif message.message_type == MessageType.HEARTBEAT:
                self._handle_heartbeat(message)
            elif message.message_type == MessageType.DISCOVERY:
                self._handle_discovery(message)
            
            # Handle with registered handlers
            handlers = self.message_handlers.get(message.message_type, [])
            for handler in handlers:
                try:
                    response = asyncio.run(handler.handle_message(message))
                    if response and message.message_type == MessageType.REQUEST:
                        # Send response back
                        self.outbound_queue.put(response)
                except Exception as e:
                    logger.error(f"Handler error for message {message.message_id}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error handling message {message.message_id}: {str(e)}")
    
    def _outbound_processor(self) -> None:
        """Process outbound messages."""
        while self.is_running:
            try:
                message = self.outbound_queue.get(timeout=1.0)
                self._deliver_message(message)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing outbound message: {str(e)}")
    
    def _deliver_message(self, message: Message) -> None:
        """Deliver message to recipient(s)."""
        try:
            start_time = time.time()
            
            # Check if message is expired
            if message.is_expired():
                self._update_delivery_status(
                    message.message_id,
                    MessageDeliveryStatus.TIMEOUT,
                    "Message expired before delivery"
                )
                return
            
            # Serialize message
            message_data = message.to_dict()
            
            if message.recipient_id:
                # Unicast message
                success = self._send_to_agent(message.recipient_id, message_data)
                status = MessageDeliveryStatus.DELIVERED if success else MessageDeliveryStatus.FAILED
                
                self._update_delivery_status(
                    message.message_id,
                    status,
                    None if success else "Delivery failed",
                    (time.time() - start_time) * 1000
                )
            else:
                # Broadcast message
                for agent_id in self.known_agents:
                    if agent_id != self.agent_info.agent_id:
                        self._send_to_agent(agent_id, message_data)
            
        except Exception as e:
            logger.error(f"Error delivering message {message.message_id}: {str(e)}")
            self._update_delivery_status(
                message.message_id,
                MessageDeliveryStatus.FAILED,
                str(e)
            )
    
    def _send_to_agent(self, agent_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Send message to specific agent.
        
        Args:
            agent_id: Target agent ID
            message_data: Serialized message
            
        Returns:
            True if sent successfully
        """
        # In a real implementation, this would use actual transport
        # (HTTP, WebSocket, message queue, etc.)
        
        # For demo purposes, simulate message delivery
        agent_info = self.known_agents.get(agent_id)
        if not agent_info or agent_info.status != AgentStatus.ONLINE:
            return False
        
        # Simulate network delay
        time.sleep(0.001)
        
        logger.debug(f"Delivered message to agent {agent_id}")
        return True
    
    def _update_delivery_status(
        self,
        message_id: str,
        status: MessageDeliveryStatus,
        error_message: Optional[str] = None,
        delivery_time_ms: Optional[float] = None
    ) -> None:
        """Update message delivery status."""
        if message_id in self.delivery_tracking:
            delivery = self.delivery_tracking[message_id]
            delivery.status = status
            delivery.error_message = error_message
            delivery.delivery_time_ms = delivery_time_ms
    
    def _heartbeat_sender(self) -> None:
        """Send periodic heartbeat messages."""
        while self.is_running:
            try:
                # Update heartbeat timestamp
                self.agent_info.last_heartbeat = datetime.now()
                
                # Send heartbeat to all known agents
                payload = {
                    "agent_info": self.agent_info.to_dict(),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.broadcast_message(MessageType.HEARTBEAT, payload, MessagePriority.LOW)
                
                # Sleep until next heartbeat
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error sending heartbeat: {str(e)}")
                time.sleep(5)  # Shorter retry interval on error
    
    def _cleanup_expired_messages(self) -> None:
        """Clean up expired messages and delivery tracking."""
        while self.is_running:
            try:
                current_time = datetime.now()
                expired_deliveries = []
                
                # Find expired delivery tracking entries
                for message_id, delivery in self.delivery_tracking.items():
                    if (current_time - delivery.timestamp).total_seconds() > self.message_timeout:
                        expired_deliveries.append(message_id)
                
                # Remove expired entries
                for message_id in expired_deliveries:
                    del self.delivery_tracking[message_id]
                
                if expired_deliveries:
                    logger.debug(f"Cleaned up {len(expired_deliveries)} expired delivery records")
                
                # Clean up stale agent entries
                stale_agents = []
                for agent_id, agent_info in self.known_agents.items():
                    if (current_time - agent_info.last_heartbeat).total_seconds() > (self.heartbeat_interval * 3):
                        stale_agents.append(agent_id)
                
                for agent_id in stale_agents:
                    logger.info(f"Removing stale agent: {agent_id}")
                    del self.known_agents[agent_id]
                
                time.sleep(60)  # Run cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup: {str(e)}")
                time.sleep(60)
    
    def _send_registration(self) -> None:
        """Send registration message to announce presence."""
        payload = {
            "agent_info": self.agent_info.to_dict(),
            "action": "register"
        }
        
        self.broadcast_message(MessageType.REGISTRATION, payload, MessagePriority.HIGH)
        logger.info(f"Sent registration for agent {self.agent_info.agent_id}")
    
    def _send_deregistration(self) -> None:
        """Send deregistration message to announce departure."""
        payload = {
            "agent_info": self.agent_info.to_dict(),
            "action": "deregister"
        }
        
        self.broadcast_message(MessageType.DEREGISTRATION, payload, MessagePriority.HIGH)
        logger.info(f"Sent deregistration for agent {self.agent_info.agent_id}")
    
    def _handle_registration(self, message: Message) -> None:
        """Handle agent registration message."""
        try:
            agent_data = message.payload.get("agent_info")
            if agent_data:
                agent_info = AgentInfo.from_dict(agent_data)
                
                # Don't register ourselves
                if agent_info.agent_id == self.agent_info.agent_id:
                    return
                
                # Add to known agents
                self.known_agents[agent_info.agent_id] = agent_info
                
                # Notify discovery callbacks
                for callback in self.agent_discovery_callbacks:
                    try:
                        callback(agent_info)
                    except Exception as e:
                        logger.error(f"Error in discovery callback: {str(e)}")
                
                logger.info(f"Registered agent: {agent_info.agent_id} ({agent_info.agent_name})")
                
        except Exception as e:
            logger.error(f"Error handling registration: {str(e)}")
    
    def _handle_deregistration(self, message: Message) -> None:
        """Handle agent deregistration message."""
        try:
            agent_data = message.payload.get("agent_info")
            if agent_data:
                agent_id = agent_data.get("agent_id")
                if agent_id and agent_id in self.known_agents:
                    del self.known_agents[agent_id]
                    logger.info(f"Deregistered agent: {agent_id}")
                    
        except Exception as e:
            logger.error(f"Error handling deregistration: {str(e)}")
    
    def _handle_heartbeat(self, message: Message) -> None:
        """Handle heartbeat message."""
        try:
            agent_data = message.payload.get("agent_info")
            if agent_data:
                agent_info = AgentInfo.from_dict(agent_data)
                
                # Don't process our own heartbeat
                if agent_info.agent_id == self.agent_info.agent_id:
                    return
                
                # Update known agent info
                if agent_info.agent_id in self.known_agents:
                    self.known_agents[agent_info.agent_id] = agent_info
                else:
                    # New agent discovered via heartbeat
                    self.known_agents[agent_info.agent_id] = agent_info
                    logger.info(f"Discovered new agent via heartbeat: {agent_info.agent_id}")
                    
        except Exception as e:
            logger.error(f"Error handling heartbeat: {str(e)}")
    
    def _handle_discovery(self, message: Message) -> None:
        """Handle discovery request."""
        try:
            # Send our registration in response to discovery
            payload = {
                "agent_info": self.agent_info.to_dict(),
                "action": "discovery_response"
            }
            
            self.send_message(
                recipient_id=message.sender_id,
                message_type=MessageType.REGISTRATION,
                payload=payload,
                priority=MessagePriority.NORMAL
            )
            
        except Exception as e:
            logger.error(f"Error handling discovery: {str(e)}")


# Convenience message handlers
class RequestHandler(MessageHandler):
    """Handler for request messages with callback function."""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Initialize request handler.
        
        Args:
            callback: Function to handle request and return response data
        """
        self.callback = callback
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle request message."""
        try:
            request_data = message.payload.get("request_data", {})
            response_data = self.callback(request_data)
            
            # Create response message
            response_payload = {
                "success": True,
                "response_data": response_data
            }
            
            return Message(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.RESPONSE,
                sender_id=message.recipient_id,  # We are now the sender
                recipient_id=message.sender_id,
                payload=response_payload,
                timestamp=datetime.now(),
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            # Create error response
            error_payload = {
                "success": False,
                "error_message": str(e)
            }
            
            return Message(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.RESPONSE,
                sender_id=message.recipient_id,
                recipient_id=message.sender_id,
                payload=error_payload,
                timestamp=datetime.now(),
                correlation_id=message.correlation_id
            )


class NotificationHandler(MessageHandler):
    """Handler for notification messages with callback function."""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Initialize notification handler.
        
        Args:
            callback: Function to handle notification
        """
        self.callback = callback
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle notification message."""
        try:
            self.callback(message.payload)
        except Exception as e:
            logger.error(f"Error in notification handler: {str(e)}")
        
        return None  # No response for notifications