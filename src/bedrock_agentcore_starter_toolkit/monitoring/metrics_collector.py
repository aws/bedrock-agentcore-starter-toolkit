"""Metrics collection system for agent performance monitoring."""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from .utils import validate_agent_id, sanitize_log_group_name


class MetricsCollector:
    """Collects and aggregates performance metrics from CloudWatch."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize metrics collector."""
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.logs = boto3.client("logs", region_name=region)
        self.region = region

    def collect_agent_metrics(self, agent_id: str, hours: int = 1) -> Dict:
        """Collect comprehensive metrics for an agent."""
        # Validate agent ID for security
        is_valid, error = validate_agent_id(agent_id)
        if not is_valid:
            raise ValueError(f"Invalid agent ID: {error}")
            
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = {
            "agent_id": agent_id,
            "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "performance": self._get_performance_metrics(agent_id, start_time, end_time),
            "errors": self._get_error_metrics(agent_id, start_time, end_time),
            "usage": self._get_usage_metrics(agent_id, start_time, end_time),
        }
        
        return metrics

    def _get_performance_metrics(self, agent_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """Get performance metrics (latency, throughput)."""
        try:
            # Query CloudWatch metrics
            response = self.cloudwatch.get_metric_statistics(
                Namespace="bedrock-agentcore",
                MetricName="Duration",
                Dimensions=[{"Name": "AgentId", "Value": agent_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5 minutes
                Statistics=["Average", "Maximum", "Minimum"]
            )
            
            datapoints = response.get("Datapoints", [])
            if not datapoints:
                return {"avg_latency": 0, "max_latency": 0, "min_latency": 0, "request_count": 0}
            
            return {
                "avg_latency": sum(d["Average"] for d in datapoints) / len(datapoints),
                "max_latency": max(d["Maximum"] for d in datapoints),
                "min_latency": min(d["Minimum"] for d in datapoints),
                "request_count": len(datapoints)
            }
        except ClientError:
            return {"avg_latency": 0, "max_latency": 0, "min_latency": 0, "request_count": 0}

    def _get_error_metrics(self, agent_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """Get error rate and failure metrics."""
        log_group = sanitize_log_group_name(agent_id)
        
        try:
            # Query error logs
            response = self.logs.filter_log_events(
                logGroupName=log_group,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern="ERROR"
            )
            
            error_count = len(response.get("events", []))
            
            # Get total requests for error rate calculation
            total_response = self.logs.filter_log_events(
                logGroupName=log_group,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern="[timestamp, request_id, ...]"
            )
            
            total_requests = len(total_response.get("events", []))
            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "error_count": error_count,
                "total_requests": total_requests,
                "error_rate": round(error_rate, 2)
            }
        except ClientError:
            return {"error_count": 0, "total_requests": 0, "error_rate": 0}

    def _get_usage_metrics(self, agent_id: str, start_time: datetime, end_time: datetime) -> Dict:
        """Get resource usage metrics."""
        try:
            # Memory usage
            memory_response = self.cloudwatch.get_metric_statistics(
                Namespace="bedrock-agentcore",
                MetricName="MemoryUtilization",
                Dimensions=[{"Name": "AgentId", "Value": agent_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum"]
            )
            
            memory_data = memory_response.get("Datapoints", [])
            avg_memory = sum(d["Average"] for d in memory_data) / len(memory_data) if memory_data else 0
            max_memory = max(d["Maximum"] for d in memory_data) if memory_data else 0
            
            return {
                "avg_memory_usage": round(avg_memory, 2),
                "max_memory_usage": round(max_memory, 2),
                "memory_efficiency": round((avg_memory / max_memory * 100) if max_memory > 0 else 0, 2)
            }
        except ClientError:
            return {"avg_memory_usage": 0, "max_memory_usage": 0, "memory_efficiency": 0}

    def get_real_time_metrics(self, agent_id: str) -> Dict:
        """Get real-time metrics for the last 5 minutes."""
        return self.collect_agent_metrics(agent_id, hours=0.083)  # 5 minutes

    def get_historical_trends(self, agent_id: str, days: int = 7) -> List[Dict]:
        """Get historical performance trends."""
        trends = []
        end_time = datetime.utcnow()
        
        for day in range(days):
            day_start = end_time - timedelta(days=day+1)
            day_end = end_time - timedelta(days=day)
            
            daily_metrics = self.collect_agent_metrics(agent_id, hours=24)
            daily_metrics["date"] = day_start.strftime("%Y-%m-%d")
            trends.append(daily_metrics)
        
        return trends