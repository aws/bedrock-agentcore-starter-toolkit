"""Operational insights and analytics for agent performance."""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from .metrics_collector import MetricsCollector


class OperationalInsights:
    """Provides operational intelligence and analytics for agents."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize operational insights analyzer."""
        self.logs = boto3.client("logs", region_name=region)
        self.metrics_collector = MetricsCollector(region)
        self.region = region

    def analyze_conversation_patterns(self, agent_id: str, hours: int = 24) -> Dict:
        """Analyze conversation patterns and user behavior."""
        log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}"
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        try:
            # Get conversation logs
            response = self.logs.filter_log_events(
                logGroupName=log_group,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern="[timestamp, request_id, level, message]"
            )
            
            events = response.get("events", [])
            
            # Analyze patterns
            session_analysis = self._analyze_sessions(events)
            topic_analysis = self._analyze_topics(events)
            user_behavior = self._analyze_user_behavior(events)
            
            return {
                "agent_id": agent_id,
                "analysis_period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
                "total_conversations": len(events),
                "session_analysis": session_analysis,
                "topic_analysis": topic_analysis,
                "user_behavior": user_behavior
            }
        except ClientError:
            return {"error": "Unable to access logs", "agent_id": agent_id}

    def detect_performance_anomalies(self, agent_id: str, days: int = 7) -> Dict:
        """Detect performance anomalies and unusual patterns."""
        trends = self.metrics_collector.get_historical_trends(agent_id, days)
        
        anomalies = {
            "latency_spikes": [],
            "error_bursts": [],
            "usage_anomalies": [],
            "traffic_patterns": []
        }
        
        # Analyze each day's metrics
        for i, day_metrics in enumerate(trends):
            if i == 0:  # Skip first day (no comparison)
                continue
                
            prev_metrics = trends[i-1]
            
            # Check for latency spikes
            current_latency = day_metrics["performance"]["avg_latency"]
            prev_latency = prev_metrics["performance"]["avg_latency"]
            
            if current_latency > prev_latency * 2 and current_latency > 1000:
                anomalies["latency_spikes"].append({
                    "date": day_metrics["date"],
                    "current": current_latency,
                    "previous": prev_latency,
                    "increase": f"{((current_latency / prev_latency - 1) * 100):.1f}%"
                })
            
            # Check for error rate increases
            current_errors = day_metrics["errors"]["error_rate"]
            prev_errors = prev_metrics["errors"]["error_rate"]
            
            if current_errors > prev_errors * 3 and current_errors > 1:
                anomalies["error_bursts"].append({
                    "date": day_metrics["date"],
                    "current": current_errors,
                    "previous": prev_errors
                })
        
        return {
            "agent_id": agent_id,
            "analysis_period": f"Last {days} days",
            "anomalies_detected": sum(len(v) for v in anomalies.values()),
            "anomalies": anomalies
        }

    def generate_optimization_recommendations(self, agent_id: str) -> Dict:
        """Generate specific optimization recommendations."""
        # Get comprehensive data
        current_metrics = self.metrics_collector.collect_agent_metrics(agent_id, hours=24)
        conversation_patterns = self.analyze_conversation_patterns(agent_id, hours=24)
        anomalies = self.detect_performance_anomalies(agent_id, days=7)
        
        recommendations = {
            "performance": [],
            "reliability": [],
            "cost": [],
            "user_experience": []
        }
        
        # Performance recommendations
        avg_latency = current_metrics["performance"]["avg_latency"]
        if avg_latency > 3000:
            recommendations["performance"].append({
                "priority": "high",
                "issue": "High response latency",
                "recommendation": "Optimize agent processing logic or increase compute resources",
                "impact": "Improve user experience and reduce timeout risks"
            })
        
        # Reliability recommendations
        error_rate = current_metrics["errors"]["error_rate"]
        if error_rate > 2:
            recommendations["reliability"].append({
                "priority": "high",
                "issue": "Elevated error rate",
                "recommendation": "Implement better error handling and input validation",
                "impact": "Reduce failed requests and improve reliability"
            })
        
        # Cost optimization
        memory_usage = current_metrics["usage"]["avg_memory_usage"]
        if memory_usage < 30:
            recommendations["cost"].append({
                "priority": "medium",
                "issue": "Low memory utilization",
                "recommendation": "Consider reducing allocated memory to optimize costs",
                "impact": "Reduce operational costs without affecting performance"
            })
        
        # User experience
        total_conversations = conversation_patterns.get("total_conversations", 0)
        if total_conversations > 0:
            session_length = conversation_patterns.get("session_analysis", {}).get("avg_session_length", 0)
            if session_length > 10:
                recommendations["user_experience"].append({
                    "priority": "medium",
                    "issue": "Long conversation sessions",
                    "recommendation": "Analyze if users are struggling to get answers quickly",
                    "impact": "Improve user satisfaction and reduce support burden"
                })
        
        return {
            "agent_id": agent_id,
            "generated_at": datetime.utcnow().isoformat(),
            "total_recommendations": sum(len(v) for v in recommendations.values()),
            "recommendations": recommendations
        }

    def _analyze_sessions(self, events: List[Dict]) -> Dict:
        """Analyze session patterns from log events."""
        sessions = defaultdict(list)
        
        for event in events:
            message = event.get("message", "")
            # Extract session ID if present
            session_match = re.search(r'session[_-]?id[:\s]+([a-zA-Z0-9-]+)', message, re.IGNORECASE)
            if session_match:
                session_id = session_match.group(1)
                sessions[session_id].append(event)
        
        if not sessions:
            return {"total_sessions": 0, "avg_session_length": 0}
        
        session_lengths = [len(session_events) for session_events in sessions.values()]
        
        return {
            "total_sessions": len(sessions),
            "avg_session_length": sum(session_lengths) / len(session_lengths),
            "max_session_length": max(session_lengths),
            "min_session_length": min(session_lengths)
        }

    def _analyze_topics(self, events: List[Dict]) -> Dict:
        """Analyze conversation topics and keywords."""
        all_text = " ".join(event.get("message", "") for event in events)
        
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
        word_counts = Counter(words)
        
        # Filter out common words
        common_words = {"this", "that", "with", "have", "will", "from", "they", "been", "were", "said", "each", "which", "their", "time", "would", "there", "could", "other"}
        filtered_counts = {word: count for word, count in word_counts.items() if word not in common_words}
        
        top_topics = dict(Counter(filtered_counts).most_common(10))
        
        return {
            "total_unique_words": len(filtered_counts),
            "top_topics": top_topics,
            "vocabulary_diversity": len(filtered_counts) / len(words) if words else 0
        }

    def _analyze_user_behavior(self, events: List[Dict]) -> Dict:
        """Analyze user interaction patterns."""
        hourly_activity = defaultdict(int)
        
        for event in events:
            timestamp = event.get("timestamp", 0)
            hour = datetime.fromtimestamp(timestamp / 1000).hour
            hourly_activity[hour] += 1
        
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1]) if hourly_activity else (0, 0)
        
        return {
            "peak_hour": peak_hour[0],
            "peak_activity": peak_hour[1],
            "hourly_distribution": dict(hourly_activity),
            "total_interactions": sum(hourly_activity.values())
        }