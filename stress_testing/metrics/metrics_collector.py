"""
Metrics Collector - Collects metrics from various sources.

Simplified version for fast-track implementation.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..models import SystemMetrics, AgentMetrics, BusinessMetrics
from .agent_metrics_collector import AgentMetricsCollector


logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics from load generator, agents, and business logic."""
    
    def __init__(self, agent_dashboard_api=None):
        """
        Initialize metrics collector.
        
        Args:
            agent_dashboard_api: Optional AgentDashboardAPI instance for agent metrics
        """
        self.load_generator = None
        self.is_collecting = False
        
        # Simulated data for demo
        self.total_transactions = 0
        self.total_fraud_detected = 0
        self.total_cost = 0.0
        
        # Agent metrics collector
        self.agent_metrics_collector = AgentMetricsCollector(agent_dashboard_api)
        
        logger.info("MetricsCollector initialized")
    
    def set_load_generator(self, load_generator):
        """Set load generator reference."""
        self.load_generator = load_generator
    
    def set_agent_dashboard_api(self, agent_dashboard_api):
        """
        Set AgentDashboardAPI instance for agent metrics collection.
        
        Args:
            agent_dashboard_api: Instance of AgentDashboardAPI
        """
        self.agent_metrics_collector.set_agent_dashboard_api(agent_dashboard_api)
        logger.info("AgentDashboardAPI set for agent metrics collection")
    
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all metrics from all sources.
        
        Returns:
            Dictionary with system, agents, and business metrics
        """
        return {
            'system': await self.collect_system_metrics(),
            'agents': await self.collect_agent_metrics(),
            'business': await self.collect_business_metrics()
        }
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect system-level metrics."""
        if self.load_generator:
            return self.load_generator.get_metrics()
        
        # Return empty metrics if no load generator
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
    
    async def collect_agent_metrics(self) -> List[AgentMetrics]:
        """
        Collect agent-specific metrics.
        
        Uses AgentMetricsCollector to get real metrics from AgentDashboardAPI
        if available, otherwise falls back to simulated metrics.
        """
        # Try to collect real agent metrics first
        real_metrics = await self.agent_metrics_collector.collect_agent_metrics()
        
        if real_metrics:
            logger.debug(f"Collected {len(real_metrics)} real agent metrics")
            return real_metrics
        
        # Fallback to simulated metrics for demo
        logger.debug("Using simulated agent metrics (AgentDashboardAPI not available)")
        agents = []
        
        agent_names = [
            "Transaction Analyzer",
            "Pattern Detector",
            "Risk Assessor",
            "Decision Maker"
        ]
        
        for i, name in enumerate(agent_names):
            # Simulate realistic metrics
            base_load = random.uniform(0.5, 0.9)
            base_response = random.uniform(100, 300)
            
            agents.append(AgentMetrics(
                agent_id=f"agent_{i+1}",
                agent_name=name,
                timestamp=datetime.utcnow(),
                requests_processed=random.randint(1000, 5000),
                avg_response_time_ms=base_response,
                p95_response_time_ms=base_response * 1.8,
                p99_response_time_ms=base_response * 2.5,
                success_rate=random.uniform(0.95, 0.99),
                error_count=random.randint(5, 50),
                timeout_count=random.randint(0, 10),
                current_load=base_load,
                concurrent_requests=int(base_load * 20),
                health_score=random.uniform(0.90, 0.99),
                status="healthy" if base_load < 0.85 else "degraded",
                decision_accuracy=random.uniform(0.92, 0.98),
                false_positive_rate=random.uniform(0.01, 0.05),
                false_negative_rate=random.uniform(0.005, 0.02)
            ))
        
        return agents
    
    async def collect_business_metrics(self) -> BusinessMetrics:
        """Collect business-level metrics."""
        # Update counters based on load generator
        if self.load_generator:
            self.total_transactions = self.load_generator.total_sent
            # Simulate fraud detection (2% fraud rate, 95% detection accuracy)
            expected_fraud = int(self.total_transactions * 0.02)
            self.total_fraud_detected = int(expected_fraud * 0.95)
            # Simulate cost ($0.025 per transaction)
            self.total_cost = self.total_transactions * 0.025
        
        fraud_prevented = self.total_fraud_detected * 300  # $300 avg fraud amount
        
        return BusinessMetrics(
            timestamp=datetime.utcnow(),
            transactions_processed=self.total_transactions,
            transactions_per_second=self.load_generator.current_tps if self.load_generator else 0,
            fraud_detected=self.total_fraud_detected,
            fraud_prevented_amount=fraud_prevented,
            fraud_detection_rate=0.02,  # 2% of transactions are fraud
            fraud_detection_accuracy=0.95,  # 95% accuracy
            cost_per_transaction=0.025,
            total_cost=self.total_cost,
            roi_percentage=((fraud_prevented - self.total_cost) / self.total_cost * 100) if self.total_cost > 0 else 0,
            money_saved=fraud_prevented - self.total_cost,
            payback_period_months=6.0,
            customer_impact_score=0.92,
            false_positive_impact=0.05,
            performance_vs_baseline=1.5,  # 50% better than baseline
            cost_vs_baseline=0.6  # 40% cheaper than baseline
        )
    
    async def collect_cloudwatch_metrics(self) -> Dict[str, Any]:
        """Collect CloudWatch metrics (simulated for demo)."""
        return {
            'lambda': {
                'invocations': random.randint(1000, 10000),
                'errors': random.randint(0, 50),
                'duration_avg': random.uniform(100, 500),
                'throttles': random.randint(0, 10)
            },
            'dynamodb': {
                'read_capacity': random.uniform(50, 100),
                'write_capacity': random.uniform(30, 80),
                'throttled_requests': random.randint(0, 5)
            },
            'kinesis': {
                'incoming_records': random.randint(1000, 10000),
                'iterator_age_ms': random.uniform(100, 1000)
            },
            'bedrock': {
                'model_invocations': random.randint(100, 1000),
                'model_latency_ms': random.uniform(200, 800)
            }
        }
    
    async def get_coordination_efficiency(self) -> Dict[str, Any]:
        """
        Get coordination efficiency metrics across all agents.
        
        Returns:
            Dictionary containing coordination efficiency metrics
        """
        return await self.agent_metrics_collector.calculate_coordination_efficiency()
    
    async def get_workload_distribution(self) -> Dict[str, Any]:
        """
        Get workload distribution metrics across all agents.
        
        Returns:
            Dictionary containing workload distribution metrics
        """
        return await self.agent_metrics_collector.track_workload_distribution()
    
    async def get_agent_performance_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance summary for a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Performance summary dictionary or None if agent not found
        """
        return await self.agent_metrics_collector.get_agent_performance_summary(agent_id)
    
    async def get_comprehensive_agent_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for all agents including coordination and workload.
        
        Returns:
            Dictionary containing all agent-related metrics
        """
        return await self.agent_metrics_collector.get_all_metrics()
    
    def get_agent_metrics_history(self, agent_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get historical metrics for one or all agents.
        
        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of data points per agent
            
        Returns:
            Dictionary containing historical metrics
        """
        return self.agent_metrics_collector.get_metrics_history(agent_id, limit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            'is_collecting': self.is_collecting,
            'total_transactions': self.total_transactions,
            'total_fraud_detected': self.total_fraud_detected,
            'total_cost': self.total_cost,
            'agent_metrics_collector': {
                'last_collection_time': (
                    self.agent_metrics_collector.last_collection_time.isoformat()
                    if self.agent_metrics_collector.last_collection_time else None
                ),
                'coordination_events_count': self.agent_metrics_collector.coordination_events_count,
                'agents_tracked': len(self.agent_metrics_collector.metrics_history)
            }
        }
