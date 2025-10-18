"""
Agent Metrics Collector - Collects metrics from agents during stress testing.

This module integrates with the existing AgentDashboardAPI to collect individual
agent performance data, calculate coordination efficiency metrics, and track
workload distribution across agents.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

from ..models import AgentMetrics


logger = logging.getLogger(__name__)


class AgentMetricsCollector:
    """
    Collects and aggregates metrics from individual agents during stress testing.
    
    Integrates with AgentDashboardAPI to gather real-time agent performance data,
    calculate coordination efficiency, and track workload distribution.
    """
    
    def __init__(self, agent_dashboard_api=None):
        """
        Initialize the agent metrics collector.
        
        Args:
            agent_dashboard_api: Instance of AgentDashboardAPI for metrics collection
        """
        self.agent_dashboard_api = agent_dashboard_api
        self.metrics_history: Dict[str, List[AgentMetrics]] = defaultdict(list)
        self.coordination_events_count = 0
        self.last_collection_time = None
        
        logger.info("AgentMetricsCollector initialized")
    
    def set_agent_dashboard_api(self, agent_dashboard_api):
        """
        Set or update the AgentDashboardAPI instance.
        
        Args:
            agent_dashboard_api: Instance of AgentDashboardAPI
        """
        self.agent_dashboard_api = agent_dashboard_api
        logger.info("AgentDashboardAPI instance set")
    
    async def collect_agent_metrics(self) -> List[AgentMetrics]:
        """
        Collect current metrics from all agents.
        
        Returns:
            List of AgentMetrics for all active agents
        """
        if not self.agent_dashboard_api:
            logger.warning("AgentDashboardAPI not set, returning empty metrics")
            return []
        
        try:
            # Get all agents from dashboard API
            agents_data = self.agent_dashboard_api.get_all_agents()
            
            agent_metrics_list = []
            
            for agent_data in agents_data:
                # Extract metrics from agent data
                metrics_data = agent_data.get('metrics', {})
                
                # Create AgentMetrics object
                agent_metrics = AgentMetrics(
                    agent_id=agent_data['agent_id'],
                    agent_name=agent_data['agent_name'],
                    timestamp=datetime.utcnow(),
                    requests_processed=metrics_data.get('requests_processed', 0),
                    avg_response_time_ms=metrics_data.get('average_response_time_ms', 0.0),
                    p95_response_time_ms=metrics_data.get('average_response_time_ms', 0.0) * 1.8,
                    p99_response_time_ms=metrics_data.get('average_response_time_ms', 0.0) * 2.5,
                    success_rate=metrics_data.get('success_rate', 1.0),
                    error_count=metrics_data.get('error_count', 0),
                    timeout_count=0,  # Not tracked in current API
                    current_load=metrics_data.get('current_load', 0.0),
                    concurrent_requests=int(metrics_data.get('current_load', 0.0) * 20),
                    health_score=agent_data.get('health_score', 1.0),
                    status=self._map_agent_status(agent_data.get('status', 'active')),
                    decision_accuracy=None,  # Will be calculated separately
                    false_positive_rate=None,
                    false_negative_rate=None
                )
                
                agent_metrics_list.append(agent_metrics)
                
                # Store in history
                self.metrics_history[agent_metrics.agent_id].append(agent_metrics)
                
                # Keep only last 1000 data points per agent
                if len(self.metrics_history[agent_metrics.agent_id]) > 1000:
                    self.metrics_history[agent_metrics.agent_id] = \
                        self.metrics_history[agent_metrics.agent_id][-1000:]
            
            self.last_collection_time = datetime.utcnow()
            
            logger.debug(f"Collected metrics from {len(agent_metrics_list)} agents")
            return agent_metrics_list
            
        except Exception as e:
            logger.error(f"Error collecting agent metrics: {e}", exc_info=True)
            return []
    
    def _map_agent_status(self, api_status: str) -> str:
        """
        Map AgentDashboardAPI status to stress testing status.
        
        Args:
            api_status: Status from AgentDashboardAPI
            
        Returns:
            Mapped status string
        """
        status_map = {
            'active': 'healthy',
            'idle': 'healthy',
            'busy': 'healthy',
            'error': 'unhealthy',
            'offline': 'unhealthy',
            'starting': 'degraded',
            'stopping': 'degraded'
        }
        return status_map.get(api_status.lower(), 'unknown')
    
    async def calculate_coordination_efficiency(self) -> Dict[str, Any]:
        """
        Calculate coordination efficiency metrics across all agents.
        
        Returns:
            Dictionary containing coordination efficiency metrics
        """
        if not self.agent_dashboard_api:
            logger.warning("AgentDashboardAPI not set, returning empty coordination metrics")
            return self._empty_coordination_metrics()
        
        try:
            # Get coordination events from dashboard API
            events_data = self.agent_dashboard_api.get_coordination_events(limit=1000)
            
            if not events_data.get('success', False):
                return self._empty_coordination_metrics()
            
            events = events_data.get('events', [])
            self.coordination_events_count = len(events)
            
            # Calculate coordination metrics
            total_events = len(events)
            
            if total_events == 0:
                return self._empty_coordination_metrics()
            
            # Calculate average coordination time
            coordination_times = [
                event.get('duration_ms', 0.0)
                for event in events
                if event.get('event_type') == 'coordination'
            ]
            
            avg_coordination_time = (
                sum(coordination_times) / len(coordination_times)
                if coordination_times else 0.0
            )
            
            # Calculate success rate
            successful_events = sum(
                1 for event in events
                if event.get('status') == 'completed'
            )
            coordination_success_rate = successful_events / total_events if total_events > 0 else 0.0
            
            # Calculate event type distribution
            event_types = defaultdict(int)
            for event in events:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] += 1
            
            # Calculate agent participation
            agent_participation = defaultdict(int)
            for event in events:
                source = event.get('source_agent')
                target = event.get('target_agent')
                if source:
                    agent_participation[source] += 1
                if target:
                    agent_participation[target] += 1
            
            # Calculate coordination efficiency score (0.0 to 1.0)
            # Based on success rate, average time, and event distribution
            time_efficiency = max(0, 1 - (avg_coordination_time / 1000))  # Normalize to 1s
            efficiency_score = (coordination_success_rate * 0.6 + time_efficiency * 0.4)
            
            return {
                'total_coordination_events': total_events,
                'avg_coordination_time_ms': round(avg_coordination_time, 2),
                'coordination_success_rate': round(coordination_success_rate, 4),
                'coordination_efficiency_score': round(efficiency_score, 4),
                'event_type_distribution': dict(event_types),
                'agent_participation': dict(agent_participation),
                'events_per_second': self._calculate_events_per_second(events),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating coordination efficiency: {e}", exc_info=True)
            return self._empty_coordination_metrics()
    
    def _calculate_events_per_second(self, events: List[Dict[str, Any]]) -> float:
        """
        Calculate events per second from event list.
        
        Args:
            events: List of coordination events
            
        Returns:
            Events per second rate
        """
        if not events or len(events) < 2:
            return 0.0
        
        try:
            # Get timestamps of first and last events
            first_timestamp = datetime.fromisoformat(events[0]['timestamp'])
            last_timestamp = datetime.fromisoformat(events[-1]['timestamp'])
            
            duration_seconds = (last_timestamp - first_timestamp).total_seconds()
            
            if duration_seconds > 0:
                return len(events) / duration_seconds
            
        except Exception as e:
            logger.debug(f"Error calculating events per second: {e}")
        
        return 0.0
    
    def _empty_coordination_metrics(self) -> Dict[str, Any]:
        """Return empty coordination metrics structure."""
        return {
            'total_coordination_events': 0,
            'avg_coordination_time_ms': 0.0,
            'coordination_success_rate': 0.0,
            'coordination_efficiency_score': 0.0,
            'event_type_distribution': {},
            'agent_participation': {},
            'events_per_second': 0.0,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def track_workload_distribution(self) -> Dict[str, Any]:
        """
        Track and analyze workload distribution across agents.
        
        Returns:
            Dictionary containing workload distribution metrics
        """
        if not self.agent_dashboard_api:
            logger.warning("AgentDashboardAPI not set, returning empty workload metrics")
            return self._empty_workload_metrics()
        
        try:
            # Get current agent metrics
            agents_data = self.agent_dashboard_api.get_all_agents()
            
            if not agents_data:
                return self._empty_workload_metrics()
            
            # Extract workload data
            agent_loads = {}
            agent_requests = {}
            agent_response_times = {}
            
            for agent_data in agents_data:
                agent_id = agent_data['agent_id']
                metrics = agent_data.get('metrics', {})
                
                agent_loads[agent_id] = metrics.get('current_load', 0.0)
                agent_requests[agent_id] = metrics.get('requests_processed', 0)
                agent_response_times[agent_id] = metrics.get('average_response_time_ms', 0.0)
            
            # Calculate distribution statistics
            loads = list(agent_loads.values())
            requests = list(agent_requests.values())
            
            if not loads:
                return self._empty_workload_metrics()
            
            # Calculate load balance metrics
            avg_load = sum(loads) / len(loads)
            max_load = max(loads)
            min_load = min(loads)
            load_variance = sum((l - avg_load) ** 2 for l in loads) / len(loads)
            load_std_dev = load_variance ** 0.5
            
            # Calculate load imbalance percentage
            load_imbalance = ((max_load - min_load) / avg_load * 100) if avg_load > 0 else 0.0
            
            # Calculate request distribution
            total_requests = sum(requests)
            request_distribution = {
                agent_id: (count / total_requests * 100) if total_requests > 0 else 0.0
                for agent_id, count in agent_requests.items()
            }
            
            # Determine if workload is balanced (variance < 30%)
            is_balanced = load_imbalance < 30.0
            
            # Calculate workload efficiency score (0.0 to 1.0)
            # Lower imbalance = higher efficiency
            efficiency_score = max(0, 1 - (load_imbalance / 100))
            
            return {
                'agent_loads': agent_loads,
                'agent_requests': agent_requests,
                'agent_response_times': agent_response_times,
                'avg_load': round(avg_load, 4),
                'max_load': round(max_load, 4),
                'min_load': round(min_load, 4),
                'load_std_dev': round(load_std_dev, 4),
                'load_imbalance_percentage': round(load_imbalance, 2),
                'is_balanced': is_balanced,
                'request_distribution_percentage': {
                    k: round(v, 2) for k, v in request_distribution.items()
                },
                'workload_efficiency_score': round(efficiency_score, 4),
                'total_requests': total_requests,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error tracking workload distribution: {e}", exc_info=True)
            return self._empty_workload_metrics()
    
    def _empty_workload_metrics(self) -> Dict[str, Any]:
        """Return empty workload metrics structure."""
        return {
            'agent_loads': {},
            'agent_requests': {},
            'agent_response_times': {},
            'avg_load': 0.0,
            'max_load': 0.0,
            'min_load': 0.0,
            'load_std_dev': 0.0,
            'load_imbalance_percentage': 0.0,
            'is_balanced': True,
            'request_distribution_percentage': {},
            'workload_efficiency_score': 0.0,
            'total_requests': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_agent_performance_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance summary for a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Performance summary dictionary or None if agent not found
        """
        if not self.agent_dashboard_api:
            logger.warning("AgentDashboardAPI not set")
            return None
        
        try:
            agent_data = self.agent_dashboard_api.get_agent(agent_id)
            
            if not agent_data:
                logger.warning(f"Agent {agent_id} not found")
                return None
            
            metrics = agent_data.get('metrics', {})
            
            # Get historical data if available
            history = self.metrics_history.get(agent_id, [])
            
            # Calculate trends if we have history
            trend_data = {}
            if len(history) >= 2:
                recent = history[-10:]  # Last 10 data points
                
                avg_response_trend = [m.avg_response_time_ms for m in recent]
                load_trend = [m.current_load for m in recent]
                
                trend_data = {
                    'response_time_trend': 'improving' if len(avg_response_trend) > 1 and avg_response_trend[-1] < avg_response_trend[0] else 'stable',
                    'load_trend': 'increasing' if len(load_trend) > 1 and load_trend[-1] > load_trend[0] else 'stable',
                    'data_points': len(recent)
                }
            
            return {
                'agent_id': agent_id,
                'agent_name': agent_data['agent_name'],
                'agent_type': agent_data['agent_type'],
                'status': agent_data['status'],
                'health_score': agent_data['health_score'],
                'metrics': {
                    'requests_processed': metrics.get('requests_processed', 0),
                    'avg_response_time_ms': metrics.get('average_response_time_ms', 0.0),
                    'success_rate': metrics.get('success_rate', 1.0),
                    'error_count': metrics.get('error_count', 0),
                    'current_load': metrics.get('current_load', 0.0)
                },
                'trends': trend_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent performance summary: {e}", exc_info=True)
            return None
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for all agents including coordination and workload.
        
        Returns:
            Dictionary containing all agent-related metrics
        """
        # Collect all metrics concurrently
        agent_metrics, coordination_metrics, workload_metrics = await asyncio.gather(
            self.collect_agent_metrics(),
            self.calculate_coordination_efficiency(),
            self.track_workload_distribution(),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(agent_metrics, Exception):
            logger.error(f"Error collecting agent metrics: {agent_metrics}")
            agent_metrics = []
        
        if isinstance(coordination_metrics, Exception):
            logger.error(f"Error collecting coordination metrics: {coordination_metrics}")
            coordination_metrics = self._empty_coordination_metrics()
        
        if isinstance(workload_metrics, Exception):
            logger.error(f"Error collecting workload metrics: {workload_metrics}")
            workload_metrics = self._empty_workload_metrics()
        
        return {
            'agent_metrics': [
                {
                    'agent_id': m.agent_id,
                    'agent_name': m.agent_name,
                    'timestamp': m.timestamp.isoformat(),
                    'requests_processed': m.requests_processed,
                    'avg_response_time_ms': m.avg_response_time_ms,
                    'p95_response_time_ms': m.p95_response_time_ms,
                    'p99_response_time_ms': m.p99_response_time_ms,
                    'success_rate': m.success_rate,
                    'error_count': m.error_count,
                    'current_load': m.current_load,
                    'health_score': m.health_score,
                    'status': m.status
                }
                for m in agent_metrics
            ],
            'coordination_efficiency': coordination_metrics,
            'workload_distribution': workload_metrics,
            'summary': {
                'total_agents': len(agent_metrics),
                'healthy_agents': sum(1 for m in agent_metrics if m.status == 'healthy'),
                'avg_health_score': (
                    sum(m.health_score for m in agent_metrics) / len(agent_metrics)
                    if agent_metrics else 0.0
                ),
                'total_requests_processed': sum(m.requests_processed for m in agent_metrics),
                'avg_response_time_ms': (
                    sum(m.avg_response_time_ms for m in agent_metrics) / len(agent_metrics)
                    if agent_metrics else 0.0
                ),
                'overall_success_rate': (
                    sum(m.success_rate for m in agent_metrics) / len(agent_metrics)
                    if agent_metrics else 0.0
                )
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_metrics_history(self, agent_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get historical metrics for one or all agents.
        
        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of data points per agent
            
        Returns:
            Dictionary containing historical metrics
        """
        if agent_id:
            history = self.metrics_history.get(agent_id, [])[-limit:]
            return {
                'agent_id': agent_id,
                'data_points': len(history),
                'history': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'requests_processed': m.requests_processed,
                        'avg_response_time_ms': m.avg_response_time_ms,
                        'success_rate': m.success_rate,
                        'current_load': m.current_load,
                        'health_score': m.health_score
                    }
                    for m in history
                ]
            }
        else:
            return {
                'agents': {
                    aid: {
                        'data_points': len(history[-limit:]),
                        'history': [
                            {
                                'timestamp': m.timestamp.isoformat(),
                                'requests_processed': m.requests_processed,
                                'avg_response_time_ms': m.avg_response_time_ms,
                                'success_rate': m.success_rate,
                                'current_load': m.current_load,
                                'health_score': m.health_score
                            }
                            for m in history[-limit:]
                        ]
                    }
                    for aid, history in self.metrics_history.items()
                }
            }
    
    def clear_history(self):
        """Clear all stored metrics history."""
        self.metrics_history.clear()
        self.coordination_events_count = 0
        self.last_collection_time = None
        logger.info("Metrics history cleared")
