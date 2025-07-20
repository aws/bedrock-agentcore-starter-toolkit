"""Performance dashboard for visualizing agent metrics."""

import json
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from .metrics_collector import MetricsCollector


class PerformanceDashboard:
    """Creates and manages CloudWatch dashboards for agent performance."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize dashboard manager."""
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.metrics_collector = MetricsCollector(region)
        self.region = region

    def create_agent_dashboard(self, agent_id: str, dashboard_name: Optional[str] = None) -> str:
        """Create a comprehensive dashboard for an agent."""
        if not dashboard_name:
            dashboard_name = f"BedrockAgentCore-{agent_id}"

        dashboard_body = self._build_dashboard_config(agent_id)
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            return f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}"
        except ClientError as e:
            raise RuntimeError(f"Failed to create dashboard: {e}")

    def _build_dashboard_config(self, agent_id: str) -> Dict:
        """Build CloudWatch dashboard configuration."""
        return {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["bedrock-agentcore", "Duration", "AgentId", agent_id, {"stat": "Average"}],
                            [".", ".", ".", ".", {"stat": "Maximum"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Response Latency",
                        "yAxis": {"left": {"min": 0}}
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["bedrock-agentcore", "RequestCount", "AgentId", agent_id]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Request Volume",
                        "yAxis": {"left": {"min": 0}}
                    }
                },
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["bedrock-agentcore", "ErrorRate", "AgentId", agent_id]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Error Rate (%)",
                        "yAxis": {"left": {"min": 0, "max": 100}}
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["bedrock-agentcore", "MemoryUtilization", "AgentId", agent_id]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Memory Usage (%)",
                        "yAxis": {"left": {"min": 0, "max": 100}}
                    }
                },
                {
                    "type": "log",
                    "x": 0, "y": 12, "width": 24, "height": 6,
                    "properties": {
                        "query": f"SOURCE '/aws/bedrock-agentcore/runtimes/{agent_id}'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
                        "region": self.region,
                        "title": "Recent Errors",
                        "view": "table"
                    }
                }
            ]
        }

    def get_dashboard_url(self, agent_id: str) -> str:
        """Get URL for existing dashboard."""
        dashboard_name = f"BedrockAgentCore-{agent_id}"
        return f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}"

    def generate_performance_report(self, agent_id: str, hours: int = 24) -> Dict:
        """Generate a comprehensive performance report."""
        metrics = self.metrics_collector.collect_agent_metrics(agent_id, hours)
        trends = self.metrics_collector.get_historical_trends(agent_id, days=7)
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        return {
            "agent_id": agent_id,
            "report_time": metrics["time_range"]["end"],
            "performance_score": performance_score,
            "current_metrics": metrics,
            "trends": trends,
            "recommendations": recommendations,
            "dashboard_url": self.get_dashboard_url(agent_id)
        }

    def _calculate_performance_score(self, metrics: Dict) -> int:
        """Calculate overall performance score (0-100)."""
        score = 100
        
        # Deduct for high latency
        avg_latency = metrics["performance"]["avg_latency"]
        if avg_latency > 5000:  # 5 seconds
            score -= 30
        elif avg_latency > 2000:  # 2 seconds
            score -= 15
        
        # Deduct for high error rate
        error_rate = metrics["errors"]["error_rate"]
        if error_rate > 5:
            score -= 25
        elif error_rate > 1:
            score -= 10
        
        # Deduct for high memory usage
        memory_usage = metrics["usage"]["avg_memory_usage"]
        if memory_usage > 80:
            score -= 20
        elif memory_usage > 60:
            score -= 10
        
        return max(0, score)

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        if metrics["performance"]["avg_latency"] > 2000:
            recommendations.append("Consider optimizing agent logic to reduce response time")
        
        if metrics["errors"]["error_rate"] > 1:
            recommendations.append("Investigate error patterns and implement better error handling")
        
        if metrics["usage"]["avg_memory_usage"] > 70:
            recommendations.append("Monitor memory usage and consider optimizing memory-intensive operations")
        
        if metrics["performance"]["request_count"] < 10:
            recommendations.append("Low usage detected - consider promoting agent or checking integration")
        
        if not recommendations:
            recommendations.append("Performance looks good! Continue monitoring for any changes")
        
        return recommendations