"""
Metrics Aggregator - Collects and aggregates metrics from multiple sources.

This module implements real-time metrics collection, aggregation, and streaming
for stress test monitoring and dashboard updates.
"""

import asyncio
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from dataclasses import replace

from ..models import (
    SystemMetrics,
    AgentMetrics,
    BusinessMetrics,
    RealTimeMetrics,
    TestStatus
)


logger = logging.getLogger(__name__)


class MetricsBuffer:
    """
    Circular buffer for storing time-series metrics data.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize metrics buffer.
        
        Args:
            max_size: Maximum number of metrics to store
        """
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
    
    def add(self, metric: Any):
        """Add a metric to the buffer."""
        self.buffer.append(metric)
    
    def get_all(self) -> List[Any]:
        """Get all metrics in the buffer."""
        return list(self.buffer)
    
    def get_recent(self, count: int) -> List[Any]:
        """
        Get the most recent N metrics.
        
        Args:
            count: Number of recent metrics to retrieve
            
        Returns:
            List of recent metrics
        """
        return list(self.buffer)[-count:] if count <= len(self.buffer) else list(self.buffer)
    
    def clear(self):
        """Clear all metrics from the buffer."""
        self.buffer.clear()
    
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)


class MetricsAggregator:
    """
    Aggregates metrics from multiple sources and provides real-time streaming.
    
    Collects metrics from load generators, agents, AWS services, and business
    logic, then aggregates and streams them to dashboards and storage.
    """
    
    def __init__(self, buffer_size: int = 1000, aggregation_interval_seconds: float = 1.0):
        """
        Initialize metrics aggregator.
        
        Args:
            buffer_size: Maximum number of metrics to buffer
            aggregation_interval_seconds: Interval for metric aggregation
        """
        self.buffer_size = buffer_size
        self.aggregation_interval = aggregation_interval_seconds
        
        # Metric buffers
        self.system_metrics_buffer = MetricsBuffer(buffer_size)
        self.agent_metrics_buffers: Dict[str, MetricsBuffer] = {}
        self.business_metrics_buffer = MetricsBuffer(buffer_size)
        
        # Current metrics (latest values)
        self.current_system_metrics: Optional[SystemMetrics] = None
        self.current_agent_metrics: Dict[str, AgentMetrics] = {}
        self.current_business_metrics: Optional[BusinessMetrics] = None
        
        # Aggregation state
        self.is_collecting = False
        self.collection_task: Optional[asyncio.Task] = None
        
        # Metric sources (callbacks to collect metrics)
        self.metric_sources: Dict[str, Callable] = {}
        
        # Streaming subscribers
        self.subscribers: List[Callable] = []
        
        # Statistics tracking
        self.total_metrics_collected = 0
        self.collection_start_time: Optional[datetime] = None
        
        logger.info(f"MetricsAggregator initialized with buffer_size={buffer_size}, interval={aggregation_interval_seconds}s")
    
    def register_metric_source(self, source_name: str, callback: Callable):
        """
        Register a metric source callback.
        
        Args:
            source_name: Name of the metric source
            callback: Async function that returns metrics
        """
        self.metric_sources[source_name] = callback
        logger.debug(f"Registered metric source: {source_name}")
    
    def subscribe(self, callback: Callable):
        """
        Subscribe to real-time metric updates.
        
        Args:
            callback: Async function to call with metric updates
        """
        self.subscribers.append(callback)
        logger.debug(f"Added subscriber (total: {len(self.subscribers)})")
    
    def unsubscribe(self, callback: Callable):
        """
        Unsubscribe from metric updates.
        
        Args:
            callback: Callback to remove
        """
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.debug(f"Removed subscriber (total: {len(self.subscribers)})")
    
    async def start_collection(self):
        """Start collecting metrics at regular intervals."""
        if self.is_collecting:
            logger.warning("Metrics collection already running")
            return
        
        self.is_collecting = True
        self.collection_start_time = datetime.utcnow()
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started metrics collection")
    
    async def stop_collection(self):
        """Stop collecting metrics."""
        if not self.is_collecting:
            logger.warning("Metrics collection not running")
            return
        
        self.is_collecting = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped metrics collection (total collected: {self.total_metrics_collected})")
    
    async def _collection_loop(self):
        """Main collection loop that runs at regular intervals."""
        try:
            while self.is_collecting:
                await self._collect_metrics()
                await asyncio.sleep(self.aggregation_interval)
        except asyncio.CancelledError:
            logger.info("Collection loop cancelled")
        except Exception as e:
            logger.error(f"Error in collection loop: {e}")
            self.is_collecting = False
    
    async def _collect_metrics(self):
        """Collect metrics from all registered sources."""
        try:
            # Collect from all sources
            for source_name, callback in self.metric_sources.items():
                try:
                    if asyncio.iscoroutinefunction(callback):
                        metrics = await callback()
                    else:
                        metrics = callback()
                    
                    # Process collected metrics
                    if metrics:
                        await self._process_collected_metrics(source_name, metrics)
                        
                except Exception as e:
                    logger.error(f"Error collecting from {source_name}: {e}")
            
            # Increment counter
            self.total_metrics_collected += 1
            
            # Stream to subscribers
            await self._stream_to_subscribers()
            
        except Exception as e:
            logger.error(f"Error in _collect_metrics: {e}")
    
    async def _process_collected_metrics(self, source_name: str, metrics: Any):
        """
        Process metrics collected from a source.
        
        Args:
            source_name: Name of the source
            metrics: Collected metrics
        """
        # Handle different metric types
        if isinstance(metrics, SystemMetrics):
            self.add_system_metrics(metrics)
        elif isinstance(metrics, AgentMetrics):
            self.add_agent_metrics(metrics)
        elif isinstance(metrics, BusinessMetrics):
            self.add_business_metrics(metrics)
        elif isinstance(metrics, dict):
            # Handle dictionary of metrics
            if 'system' in metrics:
                self.add_system_metrics(metrics['system'])
            if 'agents' in metrics:
                for agent_metrics in metrics['agents']:
                    self.add_agent_metrics(agent_metrics)
            if 'business' in metrics:
                self.add_business_metrics(metrics['business'])
    
    async def _stream_to_subscribers(self):
        """Stream current metrics to all subscribers."""
        if not self.subscribers:
            return
        
        # Create real-time metrics snapshot
        real_time_metrics = self.get_real_time_metrics()
        
        # Notify all subscribers
        for subscriber in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(real_time_metrics)
                else:
                    subscriber(real_time_metrics)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    def add_system_metrics(self, metrics: SystemMetrics):
        """
        Add system metrics to the aggregator.
        
        Args:
            metrics: System metrics to add
        """
        self.system_metrics_buffer.add(metrics)
        self.current_system_metrics = metrics
    
    def add_agent_metrics(self, metrics: AgentMetrics):
        """
        Add agent metrics to the aggregator.
        
        Args:
            metrics: Agent metrics to add
        """
        agent_id = metrics.agent_id
        
        # Create buffer for agent if it doesn't exist
        if agent_id not in self.agent_metrics_buffers:
            self.agent_metrics_buffers[agent_id] = MetricsBuffer(self.buffer_size)
        
        self.agent_metrics_buffers[agent_id].add(metrics)
        self.current_agent_metrics[agent_id] = metrics
    
    def add_business_metrics(self, metrics: BusinessMetrics):
        """
        Add business metrics to the aggregator.
        
        Args:
            metrics: Business metrics to add
        """
        self.business_metrics_buffer.add(metrics)
        self.current_business_metrics = metrics
    
    def get_real_time_metrics(self, test_id: str = "unknown", test_status: TestStatus = TestStatus.RUNNING) -> RealTimeMetrics:
        """
        Get current real-time metrics snapshot.
        
        Args:
            test_id: Current test ID
            test_status: Current test status
            
        Returns:
            RealTimeMetrics object
        """
        # Calculate elapsed time
        elapsed_seconds = 0.0
        if self.collection_start_time:
            elapsed_seconds = (datetime.utcnow() - self.collection_start_time).total_seconds()
        
        # Get current TPS
        current_tps = 0.0
        target_tps = 0.0
        if self.current_system_metrics:
            current_tps = self.current_system_metrics.throughput_tps
        
        return RealTimeMetrics(
            timestamp=datetime.utcnow(),
            test_id=test_id,
            test_status=test_status,
            current_tps=current_tps,
            target_tps=target_tps,
            elapsed_seconds=elapsed_seconds,
            remaining_seconds=0.0,  # To be calculated by orchestrator
            system_metrics=self.current_system_metrics or self._create_empty_system_metrics(),
            agent_metrics=self.current_agent_metrics.copy(),
            business_metrics=self.current_business_metrics or self._create_empty_business_metrics()
        )
    
    def calculate_aggregated_metrics(self, window_seconds: int = 60) -> Dict[str, Any]:
        """
        Calculate aggregated metrics over a time window.
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            Dictionary of aggregated metrics
        """
        # Calculate how many samples to include
        samples_count = int(window_seconds / self.aggregation_interval)
        
        # Get recent system metrics
        recent_system = self.system_metrics_buffer.get_recent(samples_count)
        
        if not recent_system:
            return {}
        
        # Calculate aggregations
        aggregated = {
            'window_seconds': window_seconds,
            'sample_count': len(recent_system),
            'throughput': {
                'avg': statistics.mean([m.throughput_tps for m in recent_system]),
                'min': min([m.throughput_tps for m in recent_system]),
                'max': max([m.throughput_tps for m in recent_system]),
                'stddev': statistics.stdev([m.throughput_tps for m in recent_system]) if len(recent_system) > 1 else 0.0
            },
            'response_time': {
                'avg': statistics.mean([m.avg_response_time_ms for m in recent_system]),
                'p95_avg': statistics.mean([m.p95_response_time_ms for m in recent_system]),
                'p99_avg': statistics.mean([m.p99_response_time_ms for m in recent_system])
            },
            'error_rate': {
                'avg': statistics.mean([m.error_rate for m in recent_system]),
                'max': max([m.error_rate for m in recent_system])
            },
            'resource_utilization': {
                'cpu_avg': statistics.mean([m.cpu_utilization for m in recent_system]),
                'memory_avg': statistics.mean([m.memory_utilization for m in recent_system]),
                'network_avg': statistics.mean([m.network_throughput_mbps for m in recent_system])
            }
        }
        
        return aggregated
    
    def calculate_percentile(self, values: List[float], percentile: float) -> float:
        """
        Calculate percentile from a list of values.
        
        Args:
            values: List of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def calculate_rate(self, metric_name: str, window_seconds: int = 60) -> float:
        """
        Calculate rate of change for a metric.
        
        Args:
            metric_name: Name of the metric
            window_seconds: Time window in seconds
            
        Returns:
            Rate of change per second
        """
        samples_count = int(window_seconds / self.aggregation_interval)
        recent_system = self.system_metrics_buffer.get_recent(samples_count)
        
        if len(recent_system) < 2:
            return 0.0
        
        # Calculate rate based on metric name
        if metric_name == 'requests':
            first_total = recent_system[0].requests_total
            last_total = recent_system[-1].requests_total
            time_diff = (recent_system[-1].timestamp - recent_system[0].timestamp).total_seconds()
            return (last_total - first_total) / time_diff if time_diff > 0 else 0.0
        
        return 0.0
    
    def get_metrics_history(self, metric_type: str = 'system', count: Optional[int] = None) -> List[Any]:
        """
        Get historical metrics.
        
        Args:
            metric_type: Type of metrics ('system', 'business')
            count: Number of recent metrics to retrieve (None for all)
            
        Returns:
            List of historical metrics
        """
        if metric_type == 'system':
            return self.system_metrics_buffer.get_recent(count) if count else self.system_metrics_buffer.get_all()
        elif metric_type == 'business':
            return self.business_metrics_buffer.get_recent(count) if count else self.business_metrics_buffer.get_all()
        else:
            return []
    
    def get_agent_metrics_history(self, agent_id: str, count: Optional[int] = None) -> List[AgentMetrics]:
        """
        Get historical metrics for a specific agent.
        
        Args:
            agent_id: Agent ID
            count: Number of recent metrics to retrieve (None for all)
            
        Returns:
            List of agent metrics
        """
        if agent_id not in self.agent_metrics_buffers:
            return []
        
        buffer = self.agent_metrics_buffers[agent_id]
        return buffer.get_recent(count) if count else buffer.get_all()
    
    def clear_all_metrics(self):
        """Clear all buffered metrics."""
        self.system_metrics_buffer.clear()
        self.business_metrics_buffer.clear()
        for buffer in self.agent_metrics_buffers.values():
            buffer.clear()
        
        self.current_system_metrics = None
        self.current_agent_metrics.clear()
        self.current_business_metrics = None
        self.total_metrics_collected = 0
        
        logger.info("Cleared all metrics")
    
    def _create_empty_system_metrics(self) -> SystemMetrics:
        """Create empty system metrics."""
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            throughput_tps=0.0,
            requests_total=0,
            requests_successful=0,
            requests_failed=0,
            avg_response_time_ms=0.0,
            p50_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            p99_response_time_ms=0.0,
            max_response_time_ms=0.0,
            error_rate=0.0,
            timeout_rate=0.0,
            cpu_utilization=0.0,
            memory_utilization=0.0,
            network_throughput_mbps=0.0
        )
    
    def _create_empty_business_metrics(self) -> BusinessMetrics:
        """Create empty business metrics."""
        return BusinessMetrics(
            timestamp=datetime.utcnow(),
            transactions_processed=0,
            transactions_per_second=0.0,
            fraud_detected=0,
            fraud_prevented_amount=0.0,
            fraud_detection_rate=0.0,
            fraud_detection_accuracy=0.0,
            cost_per_transaction=0.0,
            total_cost=0.0,
            roi_percentage=0.0,
            money_saved=0.0,
            payback_period_months=0.0,
            customer_impact_score=0.0,
            false_positive_impact=0.0,
            performance_vs_baseline=0.0,
            cost_vs_baseline=0.0
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregator statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            'total_metrics_collected': self.total_metrics_collected,
            'is_collecting': self.is_collecting,
            'collection_start_time': self.collection_start_time.isoformat() if self.collection_start_time else None,
            'system_metrics_count': self.system_metrics_buffer.size(),
            'business_metrics_count': self.business_metrics_buffer.size(),
            'agent_count': len(self.agent_metrics_buffers),
            'subscriber_count': len(self.subscribers),
            'metric_source_count': len(self.metric_sources)
        }
