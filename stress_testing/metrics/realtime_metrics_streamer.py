"""
Real-Time Metrics Streamer - WebSocket-based metrics broadcasting.

This module provides real-time metrics streaming to connected clients with:
- WebSocket server for metric broadcasting
- Metric update batching for efficiency
- Client subscription management
- Metric filtering based on client preferences
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Set, List, Any, Optional, Callable
from enum import Enum

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be streamed."""
    SYSTEM = "system"
    AGENT = "agent"
    BUSINESS = "business"
    HERO = "hero"
    PRESENTATION = "presentation"
    CLOUDWATCH = "cloudwatch"
    ALL = "all"


class ClientSubscription:
    """Manages a client's subscription preferences."""
    
    def __init__(self, client_id: str, websocket: WebSocketServerProtocol):
        self.client_id = client_id
        self.websocket = websocket
        self.subscribed_metrics: Set[MetricType] = {MetricType.ALL}
        self.filters: Dict[str, Any] = {}
        self.last_update_time = time.time()
        self.update_interval_seconds = 1.0  # Default 1 second
        self.connected_at = datetime.utcnow()
        self.messages_sent = 0
        
    def is_subscribed_to(self, metric_type: MetricType) -> bool:
        """Check if client is subscribed to a metric type."""
        return MetricType.ALL in self.subscribed_metrics or metric_type in self.subscribed_metrics
    
    def should_send_update(self) -> bool:
        """Check if enough time has passed to send an update."""
        return (time.time() - self.last_update_time) >= self.update_interval_seconds
    
    def mark_update_sent(self):
        """Mark that an update was sent."""
        self.last_update_time = time.time()
        self.messages_sent += 1
    
    def apply_filters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply client-specific filters to data."""
        if not self.filters:
            return data
        
        filtered_data = data.copy()
        
        # Apply agent filter if specified
        if 'agent_ids' in self.filters and 'agents' in filtered_data:
            agent_ids = set(self.filters['agent_ids'])
            if isinstance(filtered_data['agents'], dict):
                filtered_data['agents'] = {
                    k: v for k, v in filtered_data['agents'].items()
                    if k in agent_ids
                }
            elif isinstance(filtered_data['agents'], list):
                filtered_data['agents'] = [
                    agent for agent in filtered_data['agents']
                    if agent.get('agent_id') in agent_ids
                ]
        
        # Apply metric field filter if specified
        if 'fields' in self.filters:
            allowed_fields = set(self.filters['fields'])
            filtered_data = {
                k: v for k, v in filtered_data.items()
                if k in allowed_fields
            }
        
        return filtered_data


class MetricsBatch:
    """Batches metrics for efficient transmission."""
    
    def __init__(self, batch_size: int = 10, batch_timeout_seconds: float = 0.5):
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.metrics: List[Dict[str, Any]] = []
        self.last_flush_time = time.time()
        
    def add_metric(self, metric: Dict[str, Any]):
        """Add a metric to the batch."""
        self.metrics.append(metric)
    
    def should_flush(self) -> bool:
        """Check if batch should be flushed."""
        return (
            len(self.metrics) >= self.batch_size or
            (time.time() - self.last_flush_time) >= self.batch_timeout_seconds
        )
    
    def flush(self) -> List[Dict[str, Any]]:
        """Flush and return all batched metrics."""
        metrics = self.metrics.copy()
        self.metrics.clear()
        self.last_flush_time = time.time()
        return metrics
    
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.metrics) == 0


class RealTimeMetricsStreamer:
    """
    WebSocket server for real-time metrics streaming.
    
    Features:
    - WebSocket server for metric broadcasting
    - Metric update batching for efficiency
    - Client subscription management
    - Metric filtering based on client preferences
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        batch_size: int = 10,
        batch_timeout_seconds: float = 0.5
    ):
        """
        Initialize the real-time metrics streamer.
        
        Args:
            host: Host to bind WebSocket server to
            port: Port for WebSocket server
            batch_size: Number of metrics to batch before sending
            batch_timeout_seconds: Maximum time to wait before flushing batch
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets library not available. Install with: pip install websockets")
        
        self.host = host
        self.port = port
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        
        # Client management
        self.clients: Dict[str, ClientSubscription] = {}
        self.client_counter = 0
        
        # Metric batching per client
        self.client_batches: Dict[str, MetricsBatch] = {}
        
        # Server state
        self.is_running = False
        self.server = None
        self.broadcast_task = None
        
        # Metrics queue
        self.metrics_queue: asyncio.Queue = asyncio.Queue()
        
        # Statistics
        self.total_messages_sent = 0
        self.total_clients_connected = 0
        self.start_time = None
        
        logger.info(f"RealTimeMetricsStreamer initialized (host={host}, port={port})")
    
    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Cannot start WebSocket server: websockets library not installed")
            return
        
        if self.is_running:
            logger.warning("WebSocket server already running")
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        
        # Start broadcast task
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the WebSocket server."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel broadcast task
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        close_tasks = []
        for client in self.clients.values():
            close_tasks.append(client.websocket.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.clients.clear()
        self.client_batches.clear()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new client connection."""
        # Generate client ID
        self.client_counter += 1
        client_id = f"client_{self.client_counter}"
        
        # Create subscription
        subscription = ClientSubscription(client_id, websocket)
        self.clients[client_id] = subscription
        self.client_batches[client_id] = MetricsBatch(
            self.batch_size,
            self.batch_timeout_seconds
        )
        self.total_clients_connected += 1
        
        logger.info(f"Client connected: {client_id} (total: {len(self.clients)})")
        
        # Send welcome message
        await self._send_to_client(client_id, {
            'type': 'welcome',
            'client_id': client_id,
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Connected to real-time metrics stream'
        })
        
        try:
            # Handle client messages
            async for message in websocket:
                await self._handle_client_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.client_batches:
                del self.client_batches[client_id]
            logger.info(f"Client removed: {client_id} (remaining: {len(self.clients)})")
    
    async def _handle_client_message(self, client_id: str, message: str):
        """Handle a message from a client."""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                await self._handle_subscribe(client_id, data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscribe(client_id, data)
            elif message_type == 'set_filters':
                await self._handle_set_filters(client_id, data)
            elif message_type == 'set_update_interval':
                await self._handle_set_update_interval(client_id, data)
            elif message_type == 'ping':
                await self._send_to_client(client_id, {'type': 'pong'})
            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {message}")
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
    
    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]):
        """Handle subscription request."""
        if client_id not in self.clients:
            return
        
        metric_types = data.get('metric_types', ['all'])
        subscription = self.clients[client_id]
        
        for metric_type_str in metric_types:
            try:
                metric_type = MetricType(metric_type_str.lower())
                subscription.subscribed_metrics.add(metric_type)
            except ValueError:
                logger.warning(f"Invalid metric type: {metric_type_str}")
        
        logger.info(f"Client {client_id} subscribed to: {metric_types}")
        
        await self._send_to_client(client_id, {
            'type': 'subscription_confirmed',
            'metric_types': [mt.value for mt in subscription.subscribed_metrics]
        })
    
    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]):
        """Handle unsubscription request."""
        if client_id not in self.clients:
            return
        
        metric_types = data.get('metric_types', [])
        subscription = self.clients[client_id]
        
        for metric_type_str in metric_types:
            try:
                metric_type = MetricType(metric_type_str.lower())
                subscription.subscribed_metrics.discard(metric_type)
            except ValueError:
                logger.warning(f"Invalid metric type: {metric_type_str}")
        
        logger.info(f"Client {client_id} unsubscribed from: {metric_types}")
    
    async def _handle_set_filters(self, client_id: str, data: Dict[str, Any]):
        """Handle filter configuration."""
        if client_id not in self.clients:
            return
        
        filters = data.get('filters', {})
        subscription = self.clients[client_id]
        subscription.filters = filters
        
        logger.info(f"Client {client_id} filters updated: {filters}")
        
        await self._send_to_client(client_id, {
            'type': 'filters_updated',
            'filters': filters
        })
    
    async def _handle_set_update_interval(self, client_id: str, data: Dict[str, Any]):
        """Handle update interval configuration."""
        if client_id not in self.clients:
            return
        
        interval = data.get('interval_seconds', 1.0)
        subscription = self.clients[client_id]
        subscription.update_interval_seconds = max(0.1, min(interval, 60.0))  # Clamp between 0.1 and 60
        
        logger.info(f"Client {client_id} update interval set to: {subscription.update_interval_seconds}s")
    
    async def _send_to_client(self, client_id: str, data: Dict[str, Any]):
        """Send data to a specific client."""
        if client_id not in self.clients:
            return
        
        subscription = self.clients[client_id]
        
        try:
            message = json.dumps(data)
            await subscription.websocket.send(message)
            subscription.mark_update_sent()
            self.total_messages_sent += 1
        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"Cannot send to {client_id}: connection closed")
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
    
    async def _broadcast_loop(self):
        """Background task to broadcast metrics to clients."""
        logger.info("Broadcast loop started")
        
        while self.is_running:
            try:
                # Process metrics from queue
                while not self.metrics_queue.empty():
                    metric_data = await self.metrics_queue.get()
                    await self._broadcast_metric(metric_data)
                
                # Flush any pending batches
                await self._flush_pending_batches()
                
                # Small delay to prevent busy loop
                await asyncio.sleep(0.1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(1)
        
        logger.info("Broadcast loop stopped")
    
    async def _broadcast_metric(self, metric_data: Dict[str, Any]):
        """Broadcast a metric to all subscribed clients."""
        metric_type_str = metric_data.get('metric_type', 'system')
        
        try:
            metric_type = MetricType(metric_type_str.lower())
        except ValueError:
            metric_type = MetricType.SYSTEM
        
        # Send to each subscribed client
        for client_id, subscription in list(self.clients.items()):
            if not subscription.is_subscribed_to(metric_type):
                continue
            
            if not subscription.should_send_update():
                # Add to batch for later
                self.client_batches[client_id].add_metric(metric_data)
                continue
            
            # Apply filters
            filtered_data = subscription.apply_filters(metric_data)
            
            # Send immediately
            await self._send_to_client(client_id, {
                'type': 'metric_update',
                'data': filtered_data
            })
    
    async def _flush_pending_batches(self):
        """Flush pending batches for clients that should receive updates."""
        for client_id, batch in list(self.client_batches.items()):
            if client_id not in self.clients:
                continue
            
            subscription = self.clients[client_id]
            
            if batch.should_flush() and not batch.is_empty():
                metrics = batch.flush()
                
                # Apply filters to each metric
                filtered_metrics = [
                    subscription.apply_filters(metric)
                    for metric in metrics
                ]
                
                # Send batch
                await self._send_to_client(client_id, {
                    'type': 'metric_batch',
                    'count': len(filtered_metrics),
                    'data': filtered_metrics
                })
    
    async def broadcast_system_metrics(self, metrics: Any):
        """Broadcast system metrics to all clients."""
        await self.queue_metric({
            'metric_type': 'system',
            'timestamp': datetime.utcnow().isoformat(),
            'data': self._serialize_metric(metrics)
        })
    
    async def broadcast_agent_metrics(self, metrics: List[Any]):
        """Broadcast agent metrics to all clients."""
        await self.queue_metric({
            'metric_type': 'agent',
            'timestamp': datetime.utcnow().isoformat(),
            'data': [self._serialize_metric(m) for m in metrics]
        })
    
    async def broadcast_business_metrics(self, metrics: Any):
        """Broadcast business metrics to all clients."""
        await self.queue_metric({
            'metric_type': 'business',
            'timestamp': datetime.utcnow().isoformat(),
            'data': self._serialize_metric(metrics)
        })
    
    async def broadcast_hero_metrics(self, metrics: Any):
        """Broadcast hero metrics to all clients."""
        await self.queue_metric({
            'metric_type': 'hero',
            'timestamp': datetime.utcnow().isoformat(),
            'data': self._serialize_metric(metrics)
        })
    
    async def broadcast_presentation_data(self, data: Any):
        """Broadcast presentation data to all clients."""
        await self.queue_metric({
            'metric_type': 'presentation',
            'timestamp': datetime.utcnow().isoformat(),
            'data': self._serialize_metric(data)
        })
    
    async def queue_metric(self, metric_data: Dict[str, Any]):
        """Queue a metric for broadcasting."""
        await self.metrics_queue.put(metric_data)
    
    def _serialize_metric(self, metric: Any) -> Dict[str, Any]:
        """Serialize a metric object to dictionary."""
        if hasattr(metric, '__dict__'):
            # Handle dataclass or object with __dict__
            try:
                return asdict(metric)
            except:
                return {k: self._serialize_value(v) for k, v in metric.__dict__.items()}
        elif isinstance(metric, dict):
            return {k: self._serialize_value(v) for k, v in metric.items()}
        else:
            return {'value': str(metric)}
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif hasattr(value, '__dict__'):
            try:
                return asdict(value)
            except:
                return str(value)
        else:
            return value
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get streamer statistics."""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'connected_clients': len(self.clients),
            'total_clients_connected': self.total_clients_connected,
            'total_messages_sent': self.total_messages_sent,
            'uptime_seconds': uptime_seconds,
            'metrics_queue_size': self.metrics_queue.qsize(),
            'batch_size': self.batch_size,
            'batch_timeout_seconds': self.batch_timeout_seconds,
            'clients': [
                {
                    'client_id': sub.client_id,
                    'subscribed_metrics': [mt.value for mt in sub.subscribed_metrics],
                    'update_interval_seconds': sub.update_interval_seconds,
                    'messages_sent': sub.messages_sent,
                    'connected_duration_seconds': (
                        datetime.utcnow() - sub.connected_at
                    ).total_seconds()
                }
                for sub in self.clients.values()
            ]
        }
    
    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)
    
    def is_client_connected(self, client_id: str) -> bool:
        """Check if a client is connected."""
        return client_id in self.clients
