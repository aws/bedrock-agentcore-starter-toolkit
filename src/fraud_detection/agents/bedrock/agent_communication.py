#!/usr/bin/env python3
"""
Agent Communication Protocols
Handles message passing, coordination, and communication between agents
"""

import json
import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages between agents"""
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_RESPONSE = "analysis_response"
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"
    HEARTBEAT = "heartbeat"

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class AgentMessage:
    """Standard message format for agent communication"""
    message_id: str
    message_type: MessageType
    sender_agent_id: str
    recipient_agent_id: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: str = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())

@dataclass
class AgentRegistration:
    """Agent registration information"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    endpoint: str
    status: str
    last_heartbeat: str
    metadata: Dict[str, Any]

class AgentCommunicationManager:
    """
    Manages communication between agents in the fraud detection system
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize communication manager"""
        self.region_name = region_name
        self.agent_registry: Dict[str, AgentRegistration] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.pending_messages: Dict[str, AgentMessage] = {}
        self.message_history: List[AgentMessage] = []
        
        # AWS clients for message passing
        self.eventbridge_client = boto3.client('events', region_name=region_name)
        self.sqs_client = boto3.client('sqs', region_name=region_name)
        
        # Thread pool for async message processing
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Initialize message handlers
        self._setup_message_handlers()
        
        logger.info("AgentCommunicationManager initialized")
    
    def _setup_message_handlers(self):
        """Set up default message handlers"""
        self.message_handlers = {
            MessageType.ANALYSIS_REQUEST: self._handle_analysis_request,
            MessageType.ANALYSIS_RESPONSE: self._handle_analysis_response,
            MessageType.COORDINATION_REQUEST: self._handle_coordination_request,
            MessageType.COORDINATION_RESPONSE: self._handle_coordination_response,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.ERROR_NOTIFICATION: self._handle_error_notification,
            MessageType.HEARTBEAT: self._handle_heartbeat
        }
    
    def register_agent(self, agent_registration: AgentRegistration):
        """Register an agent in the communication system"""
        logger.info(f"Registering agent: {agent_registration.agent_id}")
        
        agent_registration.last_heartbeat = datetime.now().isoformat()
        self.agent_registry[agent_registration.agent_id] = agent_registration
        
        # Send registration confirmation
        confirmation_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.STATUS_UPDATE,
            sender_agent_id="communication_manager",
            recipient_agent_id=agent_registration.agent_id,
            payload={
                "status": "registered",
                "registration_time": datetime.now().isoformat(),
                "capabilities_confirmed": agent_registration.capabilities
            }
        )
        
        self._send_message_async(confirmation_message)
        logger.info(f"Agent {agent_registration.agent_id} registered successfully")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            logger.info(f"Agent {agent_id} unregistered")
        else:
            logger.warning(f"Attempted to unregister unknown agent: {agent_id}")
    
    def send_message(self, message: AgentMessage) -> bool:
        """Send a message to another agent"""
        logger.info(f"Sending message {message.message_id} from {message.sender_agent_id} to {message.recipient_agent_id}")
        
        try:
            # Validate recipient exists
            if message.recipient_agent_id not in self.agent_registry:
                logger.error(f"Recipient agent {message.recipient_agent_id} not found")
                return False
            
            # Check message TTL
            if self._is_message_expired(message):
                logger.warning(f"Message {message.message_id} expired, not sending")
                return False
            
            # Store message for tracking
            self.pending_messages[message.message_id] = message
            self.message_history.append(message)
            
            # Send via appropriate channel
            success = self._route_message(message)
            
            if success:
                logger.info(f"Message {message.message_id} sent successfully")
            else:
                logger.error(f"Failed to send message {message.message_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending message {message.message_id}: {str(e)}")
            return False
    
    def send_message_async(self, message: AgentMessage) -> asyncio.Future:
        """Send a message asynchronously"""
        return self.executor.submit(self.send_message, message)
    
    def broadcast_message(self, message: AgentMessage, agent_types: Optional[List[str]] = None) -> Dict[str, bool]:
        """Broadcast a message to multiple agents"""
        logger.info(f"Broadcasting message {message.message_id} to agent types: {agent_types}")
        
        results = {}
        target_agents = []
        
        # Determine target agents
        for agent_id, registration in self.agent_registry.items():
            if agent_types is None or registration.agent_type in agent_types:
                target_agents.append(agent_id)
        
        # Send to each target agent
        for agent_id in target_agents:
            # Create individual message for each recipient
            individual_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=message.message_type,
                sender_agent_id=message.sender_agent_id,
                recipient_agent_id=agent_id,
                payload=message.payload,
                priority=message.priority,
                correlation_id=message.message_id  # Link to original broadcast
            )
            
            results[agent_id] = self.send_message(individual_message)
        
        logger.info(f"Broadcast completed: {sum(results.values())}/{len(results)} successful")
        return results
    
    def request_response(self, request_message: AgentMessage, timeout_seconds: int = 30) -> Optional[AgentMessage]:
        """Send a request and wait for response"""
        logger.info(f"Sending request {request_message.message_id} and waiting for response")
        
        # Set up response tracking
        response_correlation_id = request_message.message_id
        
        # Send the request
        if not self.send_message(request_message):
            logger.error("Failed to send request message")
            return None
        
        # Wait for response
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            # Check for response in message history
            for message in reversed(self.message_history):
                if (message.correlation_id == response_correlation_id and 
                    message.sender_agent_id == request_message.recipient_agent_id):
                    logger.info(f"Received response for request {request_message.message_id}")
                    return message
            
            # Short sleep to avoid busy waiting
            asyncio.sleep(0.1)
        
        logger.warning(f"Timeout waiting for response to request {request_message.message_id}")
        return None
    
    def coordinate_agents(self, coordination_request: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multiple agents for a complex task"""
        logger.info("Starting agent coordination")
        
        coordination_id = str(uuid.uuid4())
        required_agents = coordination_request.get('required_agents', [])
        task_data = coordination_request.get('task_data', {})
        
        # Send coordination requests to all required agents
        coordination_responses = {}
        futures = []
        
        for agent_id in required_agents:
            coord_message = AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.COORDINATION_REQUEST,
                sender_agent_id="orchestrator",
                recipient_agent_id=agent_id,
                payload={
                    "coordination_id": coordination_id,
                    "task_data": task_data,
                    "required_agents": required_agents
                },
                priority=MessagePriority.HIGH
            )
            
            future = self.send_message_async(coord_message)
            futures.append((agent_id, future))
        
        # Collect responses
        for agent_id, future in futures:
            try:
                success = future.result(timeout=30)
                coordination_responses[agent_id] = {
                    "status": "success" if success else "failed",
                    "agent_id": agent_id
                }
            except Exception as e:
                coordination_responses[agent_id] = {
                    "status": "error",
                    "error": str(e),
                    "agent_id": agent_id
                }
        
        coordination_result = {
            "coordination_id": coordination_id,
            "responses": coordination_responses,
            "success_count": sum(1 for r in coordination_responses.values() if r["status"] == "success"),
            "total_agents": len(required_agents),
            "completion_time": datetime.now().isoformat()
        }
        
        logger.info(f"Agent coordination completed: {coordination_result['success_count']}/{coordination_result['total_agents']} successful")
        return coordination_result
    
    def _route_message(self, message: AgentMessage) -> bool:
        """Route message to appropriate delivery mechanism"""
        try:
            # For now, use EventBridge for message routing
            # In production, this could use SQS, SNS, or direct HTTP calls
            
            event_detail = {
                "message": asdict(message),
                "routing_info": {
                    "sender": message.sender_agent_id,
                    "recipient": message.recipient_agent_id,
                    "message_type": message.message_type.value
                }
            }
            
            response = self.eventbridge_client.put_events(
                Entries=[
                    {
                        'Source': 'fraud-detection.agent-communication',
                        'DetailType': f'Agent Message - {message.message_type.value}',
                        'Detail': json.dumps(event_detail, default=str),
                        'EventBusName': 'default'
                    }
                ]
            )
            
            return response['FailedEntryCount'] == 0
            
        except Exception as e:
            logger.error(f"Failed to route message: {str(e)}")
            return False
    
    def _send_message_async(self, message: AgentMessage):
        """Send message asynchronously (internal use)"""
        self.executor.submit(self.send_message, message)
    
    def _is_message_expired(self, message: AgentMessage) -> bool:
        """Check if message has expired based on TTL"""
        message_time = datetime.fromisoformat(message.timestamp)
        expiry_time = message_time + timedelta(seconds=message.ttl_seconds)
        return datetime.now() > expiry_time
    
    def _handle_analysis_request(self, message: AgentMessage):
        """Handle analysis request messages"""
        logger.info(f"Handling analysis request: {message.message_id}")
        # Implementation would depend on specific agent type
        pass
    
    def _handle_analysis_response(self, message: AgentMessage):
        """Handle analysis response messages"""
        logger.info(f"Handling analysis response: {message.message_id}")
        # Process the response and update pending requests
        pass
    
    def _handle_coordination_request(self, message: AgentMessage):
        """Handle coordination request messages"""
        logger.info(f"Handling coordination request: {message.message_id}")
        # Coordinate with other agents as requested
        pass
    
    def _handle_coordination_response(self, message: AgentMessage):
        """Handle coordination response messages"""
        logger.info(f"Handling coordination response: {message.message_id}")
        # Process coordination response
        pass
    
    def _handle_status_update(self, message: AgentMessage):
        """Handle status update messages"""
        logger.info(f"Handling status update: {message.message_id}")
        # Update agent status in registry
        pass
    
    def _handle_error_notification(self, message: AgentMessage):
        """Handle error notification messages"""
        logger.error(f"Received error notification: {message.message_id} - {message.payload}")
        # Log error and potentially trigger recovery actions
        pass
    
    def _handle_heartbeat(self, message: AgentMessage):
        """Handle heartbeat messages"""
        logger.debug(f"Received heartbeat from {message.sender_agent_id}")
        
        # Update last heartbeat time
        if message.sender_agent_id in self.agent_registry:
            self.agent_registry[message.sender_agent_id].last_heartbeat = message.timestamp
    
    def process_incoming_message(self, message_data: Dict[str, Any]):
        """Process incoming message from external source"""
        try:
            # Parse message
            message = AgentMessage(**message_data)
            
            # Add to history
            self.message_history.append(message)
            
            # Route to appropriate handler
            if message.message_type in self.message_handlers:
                handler = self.message_handlers[message.message_type]
                self.executor.submit(handler, message)
            else:
                logger.warning(f"No handler for message type: {message.message_type}")
                
        except Exception as e:
            logger.error(f"Error processing incoming message: {str(e)}")
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent"""
        if agent_id in self.agent_registry:
            registration = self.agent_registry[agent_id]
            return {
                "agent_id": agent_id,
                "agent_type": registration.agent_type,
                "status": registration.status,
                "last_heartbeat": registration.last_heartbeat,
                "capabilities": registration.capabilities,
                "is_healthy": self._is_agent_healthy(agent_id)
            }
        return None
    
    def _is_agent_healthy(self, agent_id: str) -> bool:
        """Check if agent is healthy based on heartbeat"""
        if agent_id not in self.agent_registry:
            return False
        
        last_heartbeat = datetime.fromisoformat(
            self.agent_registry[agent_id].last_heartbeat
        )
        
        # Consider agent unhealthy if no heartbeat for 5 minutes
        return (datetime.now() - last_heartbeat).total_seconds() < 300
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        total_messages = len(self.message_history)
        pending_messages = len(self.pending_messages)
        registered_agents = len(self.agent_registry)
        healthy_agents = sum(1 for agent_id in self.agent_registry if self._is_agent_healthy(agent_id))
        
        # Message type distribution
        message_type_counts = {}
        for message in self.message_history:
            msg_type = message.message_type.value
            message_type_counts[msg_type] = message_type_counts.get(msg_type, 0) + 1
        
        return {
            "total_messages": total_messages,
            "pending_messages": pending_messages,
            "registered_agents": registered_agents,
            "healthy_agents": healthy_agents,
            "message_type_distribution": message_type_counts,
            "stats_generated": datetime.now().isoformat()
        }
    
    def cleanup_expired_messages(self):
        """Clean up expired messages and stale data"""
        logger.info("Cleaning up expired messages")
        
        current_time = datetime.now()
        
        # Remove expired pending messages
        expired_messages = []
        for message_id, message in self.pending_messages.items():
            if self._is_message_expired(message):
                expired_messages.append(message_id)
        
        for message_id in expired_messages:
            del self.pending_messages[message_id]
        
        # Keep only recent message history (last 1000 messages)
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-1000:]
        
        logger.info(f"Cleanup completed: removed {len(expired_messages)} expired messages")

# Utility functions for creating common message types
def create_analysis_request(sender_id: str, recipient_id: str, transaction_data: Dict[str, Any]) -> AgentMessage:
    """Create a standard analysis request message"""
    return AgentMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.ANALYSIS_REQUEST,
        sender_agent_id=sender_id,
        recipient_agent_id=recipient_id,
        payload={
            "transaction_data": transaction_data,
            "analysis_type": "fraud_detection",
            "priority": "normal"
        },
        priority=MessagePriority.NORMAL
    )

def create_coordination_request(sender_id: str, required_agents: List[str], task_data: Dict[str, Any]) -> AgentMessage:
    """Create a coordination request for multiple agents"""
    return AgentMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.COORDINATION_REQUEST,
        sender_agent_id=sender_id,
        recipient_agent_id="broadcast",
        payload={
            "required_agents": required_agents,
            "task_data": task_data,
            "coordination_type": "parallel_analysis"
        },
        priority=MessagePriority.HIGH
    )

def create_heartbeat_message(agent_id: str) -> AgentMessage:
    """Create a heartbeat message"""
    return AgentMessage(
        message_id=str(uuid.uuid4()),
        message_type=MessageType.HEARTBEAT,
        sender_agent_id=agent_id,
        recipient_agent_id="communication_manager",
        payload={
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        },
        priority=MessagePriority.LOW,
        ttl_seconds=60
    )