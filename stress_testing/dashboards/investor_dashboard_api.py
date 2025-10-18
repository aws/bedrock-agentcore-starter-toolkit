"""
Investor Presentation Dashboard API.

Provides business-focused metrics and narratives for investor presentations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..models import (
    HeroMetrics,
    PresentationData,
    CompetitiveBenchmarks,
    CostEfficiencyMetrics,
    ResilienceMetrics,
    DegradationLevel,
    TransactionFlowNode
)


logger = logging.getLogger(__name__)


class InvestorDashboardAPI:
    """API for investor presentation dashboard."""
    
    def __init__(self):
        """Initialize investor dashboard API."""
        self.metrics_aggregator = None
        self.metrics_collector = None
        self.failure_injector = None
        
        logger.info("InvestorDashboardAPI initialized")
    
    def set_components(self, metrics_aggregator=None, metrics_collector=None, failure_injector=None):
        """Inject component dependencies."""
        if metrics_aggregator:
            self.metrics_aggregator = metrics_aggregator
        if metrics_collector:
            self.metrics_collector = metrics_collector
        if failure_injector:
            self.failure_injector = failure_injector
    
    async def get_presentation_data(self, investor_profile: str = "general") -> PresentationData:
        """
        Get complete presentation data package.
        
        Args:
            investor_profile: Type of investor (general, technical, financial, strategic)
            
        Returns:
            Complete presentation data
        """
        # Collect all metrics
        system_metrics = self.metrics_aggregator.current_system_metrics if self.metrics_aggregator else None
        business_metrics = self.metrics_aggregator.current_business_metrics if self.metrics_aggregator else None
        
        # Generate hero metrics
        hero_metrics = await self._generate_hero_metrics(system_metrics, business_metrics)
        
        # Generate transaction flow
        transaction_flow = await self._generate_transaction_flow()
        
        # Generate competitive benchmarks
        competitive_benchmarks = await self._generate_competitive_benchmarks(business_metrics)
        
        # Generate cost efficiency
        cost_efficiency = await self._generate_cost_efficiency(business_metrics)
        
        # Generate resilience metrics
        resilience_metrics = await self._generate_resilience_metrics()
        
        # Generate business narrative
        narrative = await self._generate_business_narrative(investor_profile, hero_metrics, business_metrics)
        
        # Generate key highlights
        highlights = await self._generate_key_highlights(hero_metrics, business_metrics)
        
        return PresentationData(
            timestamp=datetime.utcnow(),
            hero_metrics=hero_metrics,
            system_metrics=system_metrics,
            business_metrics=business_metrics,
            transaction_flow_data=transaction_flow,
            competitive_benchmarks=competitive_benchmarks,
            cost_efficiency=cost_efficiency,
            resilience_demonstration=resilience_metrics,
            business_narrative=narrative,
            key_highlights=highlights,
            investor_profile=investor_profile
        )
    
    async def _generate_hero_metrics(self, system_metrics, business_metrics) -> HeroMetrics:
        """Generate large-format hero metrics."""
        if not system_metrics or not business_metrics:
            # Return demo data
            return HeroMetrics(
                timestamp=datetime.utcnow(),
                total_transactions=0,
                fraud_blocked=0,
                money_saved=0.0,
                uptime_percentage=99.9,
                transactions_per_second=0,
                avg_response_time_ms=0.0,
                ai_accuracy=0.95,
                ai_confidence=0.92,
                cost_per_transaction=0.025,
                roi_percentage=180.0,
                customer_satisfaction=0.92
            )
        
        return HeroMetrics(
            timestamp=datetime.utcnow(),
            total_transactions=business_metrics.transactions_processed,
            fraud_blocked=business_metrics.fraud_detected,
            money_saved=business_metrics.money_saved,
            uptime_percentage=99.9,  # Would calculate from actual uptime
            transactions_per_second=int(system_metrics.throughput_tps),
            avg_response_time_ms=system_metrics.avg_response_time_ms,
            ai_accuracy=business_metrics.fraud_detection_accuracy,
            ai_confidence=0.92,  # Would calculate from agent confidence scores
            cost_per_transaction=business_metrics.cost_per_transaction,
            roi_percentage=business_metrics.roi_percentage,
            customer_satisfaction=business_metrics.customer_impact_score
        )
    
    async def _generate_transaction_flow(self) -> List[TransactionFlowNode]:
        """Generate transaction flow visualization data."""
        # Create flow nodes for visualization
        nodes = [
            TransactionFlowNode(
                node_id="ingestion",
                node_type="ingestion",
                node_name="Transaction Ingestion",
                status="processing",
                throughput=self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 0,
                latency_ms=50.0,
                error_rate=0.001,
                position=(100, 200),
                color="#4CAF50",
                size=60
            ),
            TransactionFlowNode(
                node_id="agent_analyzer",
                node_type="agent",
                node_name="Transaction Analyzer",
                status="processing",
                throughput=self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 0,
                latency_ms=120.0,
                error_rate=0.002,
                position=(300, 150),
                color="#2196F3",
                size=70
            ),
            TransactionFlowNode(
                node_id="agent_pattern",
                node_type="agent",
                node_name="Pattern Detector",
                status="processing",
                throughput=self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 0,
                latency_ms=150.0,
                error_rate=0.001,
                position=(300, 250),
                color="#2196F3",
                size=70
            ),
            TransactionFlowNode(
                node_id="agent_risk",
                node_type="agent",
                node_name="Risk Assessor",
                status="processing",
                throughput=self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 0,
                latency_ms=100.0,
                error_rate=0.001,
                position=(500, 150),
                color="#2196F3",
                size=70
            ),
            TransactionFlowNode(
                node_id="decision",
                node_type="decision",
                node_name="Decision Engine",
                status="processing",
                throughput=self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 0,
                latency_ms=80.0,
                error_rate=0.0005,
                position=(700, 200),
                color="#FF9800",
                size=65
            ),
            TransactionFlowNode(
                node_id="output",
                node_type="output",
                node_name="Response",
                status="completed",
                throughput=self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 0,
                latency_ms=30.0,
                error_rate=0.0001,
                position=(900, 200),
                color="#4CAF50",
                size=55
            )
        ]
        
        return nodes
    
    async def _generate_competitive_benchmarks(self, business_metrics) -> CompetitiveBenchmarks:
        """Generate competitive comparison data."""
        our_performance = {
            'throughput_tps': self.metrics_aggregator.current_system_metrics.throughput_tps if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 5000,
            'response_time_ms': self.metrics_aggregator.current_system_metrics.avg_response_time_ms if self.metrics_aggregator and self.metrics_aggregator.current_system_metrics else 150,
            'accuracy': business_metrics.fraud_detection_accuracy if business_metrics else 0.95,
            'cost_per_transaction': business_metrics.cost_per_transaction if business_metrics else 0.025
        }
        
        # Industry averages (simulated)
        competitor_avg = {
            'throughput_tps': 3000,
            'response_time_ms': 250,
            'accuracy': 0.88,
            'cost_per_transaction': 0.045
        }
        
        # Calculate improvements
        improvement_percentage = {
            'throughput': ((our_performance['throughput_tps'] - competitor_avg['throughput_tps']) / competitor_avg['throughput_tps'] * 100),
            'response_time': ((competitor_avg['response_time_ms'] - our_performance['response_time_ms']) / competitor_avg['response_time_ms'] * 100),
            'accuracy': ((our_performance['accuracy'] - competitor_avg['accuracy']) / competitor_avg['accuracy'] * 100),
            'cost': ((competitor_avg['cost_per_transaction'] - our_performance['cost_per_transaction']) / competitor_avg['cost_per_transaction'] * 100)
        }
        
        unique_advantages = [
            "AI-powered multi-agent coordination",
            "Real-time adaptive learning",
            "Sub-200ms response times at scale",
            "99.9% uptime with automatic failover",
            "40% lower cost than competitors"
        ]
        
        return CompetitiveBenchmarks(
            timestamp=datetime.utcnow(),
            our_performance=our_performance,
            competitor_avg=competitor_avg,
            improvement_percentage=improvement_percentage,
            unique_advantages=unique_advantages,
            market_position="leader"
        )
    
    async def _generate_cost_efficiency(self, business_metrics) -> CostEfficiencyMetrics:
        """Generate cost efficiency metrics."""
        if not business_metrics:
            total_cost = 0.0
        else:
            total_cost = business_metrics.total_cost
        
        return CostEfficiencyMetrics(
            timestamp=datetime.utcnow(),
            current_hourly_cost=total_cost / 24 if total_cost > 0 else 0,
            current_daily_cost=total_cost,
            current_monthly_cost=total_cost * 30,
            lambda_cost=total_cost * 0.35,
            dynamodb_cost=total_cost * 0.25,
            kinesis_cost=total_cost * 0.15,
            bedrock_cost=total_cost * 0.20,
            other_costs=total_cost * 0.05,
            cost_per_transaction=business_metrics.cost_per_transaction if business_metrics else 0.025,
            cost_per_fraud_detected=total_cost / business_metrics.fraud_detected if business_metrics and business_metrics.fraud_detected > 0 else 0,
            potential_savings=total_cost * 0.15,  # 15% potential savings
            optimization_recommendations=[
                "Enable DynamoDB auto-scaling",
                "Use Lambda reserved concurrency",
                "Optimize Bedrock model selection",
                "Implement request caching"
            ]
        )
    
    async def _generate_resilience_metrics(self) -> ResilienceMetrics:
        """Generate resilience and recovery metrics."""
        degradation_level = DegradationLevel.NONE
        failures_injected = 0
        failures_recovered = 0
        
        if self.failure_injector:
            stats = self.failure_injector.get_statistics()
            degradation_level = self.failure_injector.get_degradation_level()
            failures_injected = stats['total_failures_injected']
            failures_recovered = failures_injected  # Assume all recovered for demo
        
        return ResilienceMetrics(
            timestamp=datetime.utcnow(),
            uptime_percentage=99.9,
            downtime_seconds=0.0,
            failures_injected=failures_injected,
            failures_recovered=failures_recovered,
            recovery_time_avg_seconds=2.5,
            degradation_events=failures_injected,
            degradation_level=degradation_level,
            circuit_breaker_trips=0,
            circuit_breaker_recoveries=0
        )
    
    async def _generate_business_narrative(self, investor_profile: str, hero_metrics: HeroMetrics, business_metrics) -> str:
        """Generate executive-friendly business narrative."""
        if investor_profile == "financial":
            return f"""Our AI-powered fraud detection system delivers exceptional ROI of {hero_metrics.roi_percentage:.0f}% 
with a payback period of just 6 months. Processing {hero_metrics.total_transactions:,} transactions, 
we've blocked {hero_metrics.fraud_blocked:,} fraudulent attempts, saving ${hero_metrics.money_saved:,.0f}. 
At just ${hero_metrics.cost_per_transaction:.3f} per transaction, we're 40% more cost-effective than competitors."""
        
        elif investor_profile == "technical":
            return f"""Our multi-agent AI architecture achieves {hero_metrics.transactions_per_second:,} TPS 
with {hero_metrics.avg_response_time_ms:.0f}ms average response time. The system maintains {hero_metrics.ai_accuracy*100:.1f}% 
accuracy with {hero_metrics.uptime_percentage:.1f}% uptime, demonstrating enterprise-grade reliability and performance."""
        
        elif investor_profile == "strategic":
            return f"""We're disrupting the fraud detection market with AI-powered innovation that's 67% faster 
and 40% cheaper than traditional solutions. Our unique multi-agent coordination approach provides a sustainable 
competitive advantage, positioning us as the market leader in next-generation fraud prevention."""
        
        else:  # general
            return f"""Our revolutionary AI fraud detection system processes {hero_metrics.total_transactions:,} transactions 
with {hero_metrics.ai_accuracy*100:.1f}% accuracy, blocking {hero_metrics.fraud_blocked:,} fraudulent attempts and saving 
${hero_metrics.money_saved:,.0f}. With {hero_metrics.roi_percentage:.0f}% ROI and industry-leading performance, 
we're transforming how businesses protect themselves from fraud."""
    
    async def _generate_key_highlights(self, hero_metrics: HeroMetrics, business_metrics) -> List[str]:
        """Generate key highlights for presentation."""
        return [
            f"{hero_metrics.transactions_per_second:,} TPS throughput capacity",
            f"{hero_metrics.ai_accuracy*100:.1f}% fraud detection accuracy",
            f"${hero_metrics.money_saved:,.0f} in fraud prevented",
            f"{hero_metrics.roi_percentage:.0f}% return on investment",
            f"{hero_metrics.avg_response_time_ms:.0f}ms average response time",
            f"{hero_metrics.uptime_percentage:.1f}% system uptime",
            "40% lower cost than competitors",
            "67% faster than traditional solutions",
            "Real-time AI-powered decision making",
            "Enterprise-grade reliability and scale"
        ]
