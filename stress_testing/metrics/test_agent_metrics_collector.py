"""
Unit tests for AgentMetricsCollector.

Tests the integration with AgentDashboardAPI and metrics collection functionality.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from stress_testing.metrics.agent_metrics_collector import AgentMetricsCollector


class TestAgentMetricsCollector:
    """Test suite for AgentMetricsCollector."""
    
    @pytest.fixture
    def mock_agent_dashboard_api(self):
        """Create a mock AgentDashboardAPI."""
        api = Mock()
        
        # Mock get_all_agents response
        api.get_all_agents.return_value = [
            {
                'agent_id': 'agent_1',
                'agent_name': 'Transaction Analyzer',
                'agent_type': 'transaction_analyzer',
                'status': 'active',
                'health_score': 0.95,
                'metrics': {
                    'requests_processed': 1000,
                    'average_response_time_ms': 150.5,
                    'success_rate': 0.98,
                    'error_count': 20,
                    'current_load': 0.75
                }
            },
            {
                'agent_id': 'agent_2',
                'agent_name': 'Pattern Detector',
                'agent_type': 'pattern_detector',
                'status': 'active',
                'health_score': 0.92,
                'metrics': {
                    'requests_processed': 800,
                    'average_response_time_ms': 200.0,
                    'success_rate': 0.96,
                    'error_count': 32,
                    'current_load': 0.65
                }
            }
        ]
        
        # Mock get_agent response
        api.get_agent.return_value = {
            'agent_id': 'agent_1',
            'agent_name': 'Transaction Analyzer',
            'agent_type': 'transaction_analyzer',
            'status': 'active',
            'health_score': 0.95,
            'metrics': {
                'requests_processed': 1000,
                'average_response_time_ms': 150.5,
                'success_rate': 0.98,
                'error_count': 20,
                'current_load': 0.75
            }
        }
        
        # Mock get_coordination_events response
        api.get_coordination_events.return_value = {
            'success': True,
            'total_events': 3,
            'events': [
                {
                    'event_id': 'evt_1',
                    'timestamp': datetime.utcnow().isoformat(),
                    'event_type': 'coordination',
                    'source_agent': 'agent_1',
                    'target_agent': 'agent_2',
                    'status': 'completed',
                    'duration_ms': 50.0
                },
                {
                    'event_id': 'evt_2',
                    'timestamp': datetime.utcnow().isoformat(),
                    'event_type': 'coordination',
                    'source_agent': 'agent_2',
                    'target_agent': 'agent_1',
                    'status': 'completed',
                    'duration_ms': 75.0
                },
                {
                    'event_id': 'evt_3',
                    'timestamp': datetime.utcnow().isoformat(),
                    'event_type': 'request',
                    'source_agent': 'agent_1',
                    'target_agent': None,
                    'status': 'completed',
                    'duration_ms': 25.0
                }
            ]
        }
        
        return api
    
    @pytest.fixture
    def collector(self, mock_agent_dashboard_api):
        """Create an AgentMetricsCollector with mock API."""
        return AgentMetricsCollector(mock_agent_dashboard_api)
    
    def test_initialization(self):
        """Test collector initialization."""
        collector = AgentMetricsCollector()
        
        assert collector.agent_dashboard_api is None
        assert len(collector.metrics_history) == 0
        assert collector.coordination_events_count == 0
        assert collector.last_collection_time is None
    
    def test_set_agent_dashboard_api(self, mock_agent_dashboard_api):
        """Test setting AgentDashboardAPI."""
        collector = AgentMetricsCollector()
        collector.set_agent_dashboard_api(mock_agent_dashboard_api)
        
        assert collector.agent_dashboard_api is not None
        assert collector.agent_dashboard_api == mock_agent_dashboard_api
    
    @pytest.mark.asyncio
    async def test_collect_agent_metrics(self, collector, mock_agent_dashboard_api):
        """Test collecting agent metrics."""
        metrics = await collector.collect_agent_metrics()
        
        assert len(metrics) == 2
        assert metrics[0].agent_id == 'agent_1'
        assert metrics[0].agent_name == 'Transaction Analyzer'
        assert metrics[0].requests_processed == 1000
        assert metrics[0].avg_response_time_ms == 150.5
        assert metrics[0].success_rate == 0.98
        assert metrics[0].current_load == 0.75
        assert metrics[0].health_score == 0.95
        
        # Verify metrics are stored in history
        assert len(collector.metrics_history['agent_1']) == 1
        assert len(collector.metrics_history['agent_2']) == 1
    
    @pytest.mark.asyncio
    async def test_collect_agent_metrics_without_api(self):
        """Test collecting metrics without AgentDashboardAPI."""
        collector = AgentMetricsCollector()
        metrics = await collector.collect_agent_metrics()
        
        assert len(metrics) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_coordination_efficiency(self, collector):
        """Test calculating coordination efficiency."""
        efficiency = await collector.calculate_coordination_efficiency()
        
        assert 'total_coordination_events' in efficiency
        assert 'avg_coordination_time_ms' in efficiency
        assert 'coordination_success_rate' in efficiency
        assert 'coordination_efficiency_score' in efficiency
        assert 'event_type_distribution' in efficiency
        assert 'agent_participation' in efficiency
        
        assert efficiency['total_coordination_events'] == 3
        assert efficiency['coordination_success_rate'] == 1.0  # All completed
        assert 0.0 <= efficiency['coordination_efficiency_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_coordination_efficiency_without_api(self):
        """Test coordination efficiency without AgentDashboardAPI."""
        collector = AgentMetricsCollector()
        efficiency = await collector.calculate_coordination_efficiency()
        
        assert efficiency['total_coordination_events'] == 0
        assert efficiency['coordination_success_rate'] == 0.0
        assert efficiency['coordination_efficiency_score'] == 0.0
    
    @pytest.mark.asyncio
    async def test_track_workload_distribution(self, collector):
        """Test tracking workload distribution."""
        workload = await collector.track_workload_distribution()
        
        assert 'agent_loads' in workload
        assert 'agent_requests' in workload
        assert 'avg_load' in workload
        assert 'max_load' in workload
        assert 'min_load' in workload
        assert 'load_imbalance_percentage' in workload
        assert 'is_balanced' in workload
        assert 'workload_efficiency_score' in workload
        
        assert len(workload['agent_loads']) == 2
        assert 'agent_1' in workload['agent_loads']
        assert 'agent_2' in workload['agent_loads']
        assert workload['agent_loads']['agent_1'] == 0.75
        assert workload['agent_loads']['agent_2'] == 0.65
    
    @pytest.mark.asyncio
    async def test_track_workload_distribution_without_api(self):
        """Test workload distribution without AgentDashboardAPI."""
        collector = AgentMetricsCollector()
        workload = await collector.track_workload_distribution()
        
        assert workload['avg_load'] == 0.0
        assert workload['is_balanced'] is True
        assert len(workload['agent_loads']) == 0
    
    @pytest.mark.asyncio
    async def test_get_agent_performance_summary(self, collector):
        """Test getting agent performance summary."""
        summary = await collector.get_agent_performance_summary('agent_1')
        
        assert summary is not None
        assert summary['agent_id'] == 'agent_1'
        assert summary['agent_name'] == 'Transaction Analyzer'
        assert summary['status'] == 'active'
        assert 'metrics' in summary
        assert 'trends' in summary
    
    @pytest.mark.asyncio
    async def test_get_agent_performance_summary_not_found(self, collector):
        """Test getting summary for non-existent agent."""
        collector.agent_dashboard_api.get_agent.return_value = None
        summary = await collector.get_agent_performance_summary('nonexistent')
        
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_get_all_metrics(self, collector):
        """Test getting all comprehensive metrics."""
        all_metrics = await collector.get_all_metrics()
        
        assert 'agent_metrics' in all_metrics
        assert 'coordination_efficiency' in all_metrics
        assert 'workload_distribution' in all_metrics
        assert 'summary' in all_metrics
        
        summary = all_metrics['summary']
        assert summary['total_agents'] == 2
        assert summary['healthy_agents'] == 2
        assert summary['total_requests_processed'] == 1800  # 1000 + 800
    
    def test_get_metrics_history_single_agent(self, collector):
        """Test getting metrics history for single agent."""
        # Add some history
        collector.metrics_history['agent_1'] = [Mock(
            timestamp=datetime.utcnow(),
            requests_processed=100,
            avg_response_time_ms=150.0,
            success_rate=0.98,
            current_load=0.75,
            health_score=0.95
        )]
        
        history = collector.get_metrics_history('agent_1')
        
        assert 'agent_id' in history
        assert history['agent_id'] == 'agent_1'
        assert 'data_points' in history
        assert history['data_points'] == 1
        assert 'history' in history
    
    def test_get_metrics_history_all_agents(self, collector):
        """Test getting metrics history for all agents."""
        # Add some history
        collector.metrics_history['agent_1'] = [Mock(
            timestamp=datetime.utcnow(),
            requests_processed=100,
            avg_response_time_ms=150.0,
            success_rate=0.98,
            current_load=0.75,
            health_score=0.95
        )]
        
        history = collector.get_metrics_history()
        
        assert 'agents' in history
        assert 'agent_1' in history['agents']
    
    def test_clear_history(self, collector):
        """Test clearing metrics history."""
        # Add some data
        collector.metrics_history['agent_1'] = [Mock()]
        collector.coordination_events_count = 10
        collector.last_collection_time = datetime.utcnow()
        
        collector.clear_history()
        
        assert len(collector.metrics_history) == 0
        assert collector.coordination_events_count == 0
        assert collector.last_collection_time is None
    
    def test_map_agent_status(self, collector):
        """Test agent status mapping."""
        assert collector._map_agent_status('active') == 'healthy'
        assert collector._map_agent_status('idle') == 'healthy'
        assert collector._map_agent_status('busy') == 'healthy'
        assert collector._map_agent_status('error') == 'unhealthy'
        assert collector._map_agent_status('offline') == 'unhealthy'
        assert collector._map_agent_status('starting') == 'degraded'
        assert collector._map_agent_status('stopping') == 'degraded'
        assert collector._map_agent_status('unknown_status') == 'unknown'
    
    @pytest.mark.asyncio
    async def test_metrics_history_limit(self, collector):
        """Test that metrics history is limited to 1000 entries."""
        # Simulate collecting metrics 1100 times
        for i in range(1100):
            await collector.collect_agent_metrics()
        
        # Check that history is limited
        for agent_id in collector.metrics_history:
            assert len(collector.metrics_history[agent_id]) <= 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
