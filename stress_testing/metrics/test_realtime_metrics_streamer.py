"""
Tests for Real-Time Metrics Streamer.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from ..models import SystemMetrics, AgentMetrics, BusinessMetrics
from .realtime_metrics_streamer import (
    RealTimeMetricsStreamer,
    MetricType,
    ClientSubscription,
    MetricsBatch,
    WEBSOCKETS_AVAILABLE
)


# Skip all tests if websockets not available
pytestmark = pytest.mark.skipif(
    not WEBSOCKETS_AVAILABLE,
    reason="websockets library not installed"
)


class TestMetricsBatch:
    """Test MetricsBatch functionality."""
    
    def test_add_metric(self):
        """Test adding metrics to batch."""
        batch = MetricsBatch(batch_size=5)
        
        batch.add_metric({'value': 1})
        batch.add_metric({'value': 2})
        
        assert len(batch.metrics) == 2
        assert not batch.is_empty()
    
    def test_should_flush_by_size(self):
        """Test batch flushes when size limit reached."""
        batch = MetricsBatch(batch_size=3)
        
        batch.add_metric({'value': 1})
        batch.add_metric({'value': 2})
        assert not batch.should_flush()
        
        batch.add_metric({'value': 3})
        assert batch.should_flush()
    
    def test_should_flush_by_timeout(self):
        """Test batch flushes after timeout."""
        batch = MetricsBatch(batch_size=10, batch_timeout_seconds=0.1)
        
        batch.add_metric({'value': 1})
        assert not batch.should_flush()
        
        # Wait for timeout
        import time
        time.sleep(0.15)
        assert batch.should_flush()
    
    def test_flush(self):
        """Test flushing batch."""
        batch = MetricsBatch(batch_size=5)
        
        batch.add_metric({'value': 1})
        batch.add_metric({'value': 2})
        batch.add_metric({'value': 3})
        
        metrics = batch.flush()
        
        assert len(metrics) == 3
        assert batch.is_empty()
        assert len(batch.metrics) == 0


class TestClientSubscription:
    """Test ClientSubscription functionality."""
    
    def test_initialization(self):
        """Test client subscription initialization."""
        mock_ws = Mock()
        sub = ClientSubscription("client_1", mock_ws)
        
        assert sub.client_id == "client_1"
        assert sub.websocket == mock_ws
        assert MetricType.ALL in sub.subscribed_metrics
        assert sub.update_interval_seconds == 1.0
    
    def test_is_subscribed_to_all(self):
        """Test subscription to all metrics."""
        mock_ws = Mock()
        sub = ClientSubscription("client_1", mock_ws)
        
        assert sub.is_subscribed_to(MetricType.SYSTEM)
        assert sub.is_subscribed_to(MetricType.AGENT)
        assert sub.is_subscribed_to(MetricType.BUSINESS)
    
    def test_is_subscribed_to_specific(self):
        """Test subscription to specific metrics."""
        mock_ws = Mock()
        sub = ClientSubscription("client_1", mock_ws)
        
        sub.subscribed_metrics = {MetricType.SYSTEM, MetricType.AGENT}
        
        assert sub.is_subscribed_to(MetricType.SYSTEM)
        assert sub.is_subscribed_to(MetricType.AGENT)
        assert not sub.is_subscribed_to(MetricType.BUSINESS)
    
    def test_should_send_update(self):
        """Test update interval checking."""
        import time
        
        mock_ws = Mock()
        sub = ClientSubscription("client_1", mock_ws)
        sub.update_interval_seconds = 0.1
        
        # Mark as sent first to set baseline
        sub.mark_update_sent()
        
        # Should not send immediately after marking
        assert not sub.should_send_update()
        
        # Wait for interval
        time.sleep(0.15)
        assert sub.should_send_update()
        
        # After marking sent again, should not send
        sub.mark_update_sent()
        assert not sub.should_send_update()
    
    def test_apply_filters_agent_ids(self):
        """Test filtering by agent IDs."""
        mock_ws = Mock()
        sub = ClientSubscription("client_1", mock_ws)
        sub.filters = {'agent_ids': ['agent_1', 'agent_2']}
        
        data = {
            'agents': [
                {'agent_id': 'agent_1', 'value': 1},
                {'agent_id': 'agent_2', 'value': 2},
                {'agent_id': 'agent_3', 'value': 3}
            ]
        }
        
        filtered = sub.apply_filters(data)
        
        assert len(filtered['agents']) == 2
        assert all(a['agent_id'] in ['agent_1', 'agent_2'] for a in filtered['agents'])
    
    def test_apply_filters_fields(self):
        """Test filtering by fields."""
        mock_ws = Mock()
        sub = ClientSubscription("client_1", mock_ws)
        sub.filters = {'fields': ['throughput_tps', 'error_rate']}
        
        data = {
            'throughput_tps': 1000,
            'error_rate': 0.01,
            'cpu_utilization': 0.75,
            'memory_utilization': 0.60
        }
        
        filtered = sub.apply_filters(data)
        
        assert 'throughput_tps' in filtered
        assert 'error_rate' in filtered
        assert 'cpu_utilization' not in filtered
        assert 'memory_utilization' not in filtered


class TestRealTimeMetricsStreamer:
    """Test RealTimeMetricsStreamer functionality."""
    
    def test_initialization(self):
        """Test streamer initialization."""
        streamer = RealTimeMetricsStreamer(host="localhost", port=8765)
        
        assert streamer.host == "localhost"
        assert streamer.port == 8765
        assert not streamer.is_running
        assert len(streamer.clients) == 0
    
    def test_serialize_metric_dataclass(self):
        """Test serializing dataclass metrics."""
        streamer = RealTimeMetricsStreamer()
        
        metric = SystemMetrics(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            throughput_tps=1000.0,
            requests_total=10000,
            requests_successful=9900,
            requests_failed=100,
            avg_response_time_ms=150.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=300.0,
            p99_response_time_ms=500.0,
            max_response_time_ms=1000.0,
            error_rate=0.01,
            timeout_rate=0.001,
            cpu_utilization=0.75,
            memory_utilization=0.60,
            network_throughput_mbps=100.0
        )
        
        serialized = streamer._serialize_metric(metric)
        
        assert isinstance(serialized, dict)
        assert serialized['throughput_tps'] == 1000.0
        assert serialized['error_rate'] == 0.01
        assert 'timestamp' in serialized
    
    def test_serialize_metric_dict(self):
        """Test serializing dictionary metrics."""
        streamer = RealTimeMetricsStreamer()
        
        metric = {
            'value': 100,
            'timestamp': datetime(2024, 1, 1, 12, 0, 0),
            'nested': {'key': 'value'}
        }
        
        serialized = streamer._serialize_metric(metric)
        
        assert isinstance(serialized, dict)
        assert serialized['value'] == 100
        assert isinstance(serialized['timestamp'], str)
        assert serialized['nested']['key'] == 'value'
    
    @pytest.mark.asyncio
    async def test_queue_metric(self):
        """Test queuing metrics."""
        streamer = RealTimeMetricsStreamer()
        
        metric_data = {
            'metric_type': 'system',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {'value': 100}
        }
        
        await streamer.queue_metric(metric_data)
        
        assert streamer.metrics_queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_system_metrics(self):
        """Test broadcasting system metrics."""
        streamer = RealTimeMetricsStreamer()
        
        metric = SystemMetrics(
            timestamp=datetime.utcnow(),
            throughput_tps=1000.0,
            requests_total=10000,
            requests_successful=9900,
            requests_failed=100,
            avg_response_time_ms=150.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=300.0,
            p99_response_time_ms=500.0,
            max_response_time_ms=1000.0,
            error_rate=0.01,
            timeout_rate=0.001,
            cpu_utilization=0.75,
            memory_utilization=0.60,
            network_throughput_mbps=100.0
        )
        
        await streamer.broadcast_system_metrics(metric)
        
        assert streamer.metrics_queue.qsize() == 1
        
        queued_data = await streamer.metrics_queue.get()
        assert queued_data['metric_type'] == 'system'
        assert 'data' in queued_data
    
    @pytest.mark.asyncio
    async def test_broadcast_agent_metrics(self):
        """Test broadcasting agent metrics."""
        streamer = RealTimeMetricsStreamer()
        
        metrics = [
            AgentMetrics(
                agent_id="agent_1",
                agent_name="Test Agent",
                timestamp=datetime.utcnow(),
                requests_processed=1000,
                avg_response_time_ms=150.0,
                p95_response_time_ms=300.0,
                p99_response_time_ms=500.0,
                success_rate=0.99,
                error_count=10,
                timeout_count=5,
                current_load=0.75,
                concurrent_requests=20,
                health_score=0.95
            )
        ]
        
        await streamer.broadcast_agent_metrics(metrics)
        
        assert streamer.metrics_queue.qsize() == 1
        
        queued_data = await streamer.metrics_queue.get()
        assert queued_data['metric_type'] == 'agent'
        assert isinstance(queued_data['data'], list)
    
    @pytest.mark.asyncio
    async def test_broadcast_business_metrics(self):
        """Test broadcasting business metrics."""
        streamer = RealTimeMetricsStreamer()
        
        metric = BusinessMetrics(
            timestamp=datetime.utcnow(),
            transactions_processed=10000,
            transactions_per_second=100.0,
            fraud_detected=200,
            fraud_prevented_amount=50000.0,
            fraud_detection_rate=0.02,
            fraud_detection_accuracy=0.95,
            cost_per_transaction=0.02,
            total_cost=200.0,
            roi_percentage=150.0,
            money_saved=100000.0,
            payback_period_months=6.0,
            customer_impact_score=0.95,
            false_positive_impact=0.02,
            performance_vs_baseline=1.5,
            cost_vs_baseline=0.5
        )
        
        await streamer.broadcast_business_metrics(metric)
        
        assert streamer.metrics_queue.qsize() == 1
        
        queued_data = await streamer.metrics_queue.get()
        assert queued_data['metric_type'] == 'business'
    
    def test_get_statistics(self):
        """Test getting streamer statistics."""
        streamer = RealTimeMetricsStreamer()
        
        stats = streamer.get_statistics()
        
        assert 'is_running' in stats
        assert 'connected_clients' in stats
        assert 'total_messages_sent' in stats
        assert stats['connected_clients'] == 0
        assert not stats['is_running']
    
    def test_get_client_count(self):
        """Test getting client count."""
        streamer = RealTimeMetricsStreamer()
        
        assert streamer.get_client_count() == 0
    
    def test_is_client_connected(self):
        """Test checking if client is connected."""
        streamer = RealTimeMetricsStreamer()
        
        assert not streamer.is_client_connected("client_1")


@pytest.mark.asyncio
async def test_integration_metric_flow():
    """Integration test for metric flow through streamer."""
    streamer = RealTimeMetricsStreamer()
    
    # Queue various metrics
    system_metric = SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=1000.0,
        requests_total=10000,
        requests_successful=9900,
        requests_failed=100,
        avg_response_time_ms=150.0,
        p50_response_time_ms=120.0,
        p95_response_time_ms=300.0,
        p99_response_time_ms=500.0,
        max_response_time_ms=1000.0,
        error_rate=0.01,
        timeout_rate=0.001,
        cpu_utilization=0.75,
        memory_utilization=0.60,
        network_throughput_mbps=100.0
    )
    
    await streamer.broadcast_system_metrics(system_metric)
    
    agent_metrics = [
        AgentMetrics(
            agent_id="agent_1",
            agent_name="Test Agent",
            timestamp=datetime.utcnow(),
            requests_processed=1000,
            avg_response_time_ms=150.0,
            p95_response_time_ms=300.0,
            p99_response_time_ms=500.0,
            success_rate=0.99,
            error_count=10,
            timeout_count=5,
            current_load=0.75,
            concurrent_requests=20,
            health_score=0.95
        )
    ]
    
    await streamer.broadcast_agent_metrics(agent_metrics)
    
    # Verify metrics are queued
    assert streamer.metrics_queue.qsize() == 2
    
    # Get statistics
    stats = streamer.get_statistics()
    assert stats['metrics_queue_size'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
