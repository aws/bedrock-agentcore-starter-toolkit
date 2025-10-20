"""
Advanced Analytics Dashboard API

Provides fraud pattern visualization, decision accuracy tracking,
explainable AI interface, and real-time fraud detection statistics.
"""

import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from collections import defaultdict


class FraudPattern(Enum):
    """Types of fraud patterns"""
    VELOCITY_ABUSE = "velocity_abuse"
    AMOUNT_MANIPULATION = "amount_manipulation"
    LOCATION_ANOMALY = "location_anomaly"
    MERCHANT_FRAUD = "merchant_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    CARD_TESTING = "card_testing"
    SYNTHETIC_IDENTITY = "synthetic_identity"


class DecisionOutcome(Enum):
    """Decision outcomes for accuracy tracking"""
    TRUE_POSITIVE = "true_positive"  # Correctly identified fraud
    TRUE_NEGATIVE = "true_negative"  # Correctly identified legitimate
    FALSE_POSITIVE = "false_positive"  # Incorrectly flagged as fraud
    FALSE_NEGATIVE = "false_negative"  # Missed fraud


@dataclass
class FraudPatternData:
    """Fraud pattern detection data"""
    pattern_type: str
    occurrences: int
    detection_rate: float
    avg_amount: float
    trend: str  # increasing, decreasing, stable
    last_detected: str
    severity: str  # low, medium, high, critical


@dataclass
class DecisionMetrics:
    """Decision accuracy metrics"""
    total_decisions: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    timestamp: str


@dataclass
class FraudStatistics:
    """Real-time fraud detection statistics"""
    total_transactions: int
    flagged_transactions: int
    blocked_transactions: int
    fraud_rate: float
    avg_transaction_amount: float
    total_amount_saved: float
    high_risk_users: int
    active_patterns: int
    timestamp: str


@dataclass
class ExplainableDecision:
    """Explainable AI decision data"""
    transaction_id: str
    decision: str
    confidence: float
    reasoning_steps: List[str]
    evidence: List[Dict[str, Any]]
    risk_factors: List[Dict[str, Any]]
    alternative_outcomes: List[Dict[str, Any]]
    timestamp: str


@dataclass
class TrendData:
    """Time series trend data"""
    timestamp: str
    value: float
    label: str


class AnalyticsDashboardAPI:
    """
    Advanced analytics dashboard API for fraud detection insights,
    pattern visualization, and decision analysis.
    """
    
    def __init__(self):
        """Initialize analytics dashboard API"""
        self.fraud_patterns: Dict[str, FraudPatternData] = {}
        self.decision_history: List[DecisionMetrics] = []
        self.fraud_statistics: FraudStatistics = None
        self.explainable_decisions: Dict[str, ExplainableDecision] = {}
        self.trend_data: Dict[str, List[TrendData]] = defaultdict(list)
        
        self._initialize_patterns()
        self._initialize_statistics()
    
    def _initialize_patterns(self):
        """Initialize fraud pattern data"""
        patterns = [
            FraudPatternData(
                pattern_type=FraudPattern.VELOCITY_ABUSE.value,
                occurrences=45,
                detection_rate=0.87,
                avg_amount=1250.50,
                trend="increasing",
                last_detected=datetime.now().isoformat(),
                severity="high"
            ),
            FraudPatternData(
                pattern_type=FraudPattern.AMOUNT_MANIPULATION.value,
                occurrences=23,
                detection_rate=0.92,
                avg_amount=3500.00,
                trend="stable",
                last_detected=(datetime.now() - timedelta(hours=2)).isoformat(),
                severity="medium"
            ),
            FraudPatternData(
                pattern_type=FraudPattern.LOCATION_ANOMALY.value,
                occurrences=67,
                detection_rate=0.78,
                avg_amount=850.25,
                trend="decreasing",
                last_detected=(datetime.now() - timedelta(minutes=30)).isoformat(),
                severity="high"
            ),
            FraudPatternData(
                pattern_type=FraudPattern.MERCHANT_FRAUD.value,
                occurrences=12,
                detection_rate=0.95,
                avg_amount=5200.00,
                trend="stable",
                last_detected=(datetime.now() - timedelta(hours=5)).isoformat(),
                severity="critical"
            ),
            FraudPatternData(
                pattern_type=FraudPattern.ACCOUNT_TAKEOVER.value,
                occurrences=8,
                detection_rate=0.88,
                avg_amount=2100.00,
                trend="increasing",
                last_detected=(datetime.now() - timedelta(hours=1)).isoformat(),
                severity="critical"
            )
        ]
        
        for pattern in patterns:
            self.fraud_patterns[pattern.pattern_type] = pattern
    
    def _initialize_statistics(self):
        """Initialize fraud statistics"""
        self.fraud_statistics = FraudStatistics(
            total_transactions=15420,
            flagged_transactions=342,
            blocked_transactions=156,
            fraud_rate=0.0222,
            avg_transaction_amount=425.75,
            total_amount_saved=324500.00,
            high_risk_users=28,
            active_patterns=5,
            timestamp=datetime.now().isoformat()
        )
    
    def get_fraud_patterns(self) -> List[Dict[str, Any]]:
        """
        Get all detected fraud patterns
        
        Returns:
            List of fraud pattern data
        """
        return [pattern.to_dict() if hasattr(pattern, 'to_dict') else asdict(pattern) 
                for pattern in self.fraud_patterns.values()]
    
    def get_pattern_trends(self, pattern_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get trend data for a specific fraud pattern
        
        Args:
            pattern_type: Type of fraud pattern
            hours: Number of hours of historical data
            
        Returns:
            List of trend data points
        """
        # Generate sample trend data
        trends = []
        now = datetime.now()
        
        for i in range(hours):
            timestamp = now - timedelta(hours=hours-i)
            value = random.randint(0, 10) + random.random()
            
            trends.append({
                "timestamp": timestamp.isoformat(),
                "value": value,
                "label": timestamp.strftime("%H:%M")
            })
        
        return trends
    
    def get_decision_metrics(self) -> Dict[str, Any]:
        """
        Get current decision accuracy metrics
        
        Returns:
            Decision metrics data
        """
        # Calculate metrics
        tp = 1245  # True positives
        tn = 13850  # True negatives
        fp = 97  # False positives
        fn = 45  # False negatives
        
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics = DecisionMetrics(
            total_decisions=total,
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            timestamp=datetime.now().isoformat()
        )
        
        return asdict(metrics)
    
    def get_decision_accuracy_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get decision accuracy trend over time
        
        Args:
            days: Number of days of historical data
            
        Returns:
            List of accuracy trend data points
        """
        trends = []
        now = datetime.now()
        
        for i in range(days * 24):  # Hourly data points
            timestamp = now - timedelta(hours=days*24-i)
            accuracy = 0.92 + random.uniform(-0.05, 0.05)
            precision = 0.94 + random.uniform(-0.04, 0.04)
            recall = 0.89 + random.uniform(-0.06, 0.06)
            
            trends.append({
                "timestamp": timestamp.isoformat(),
                "accuracy": max(0, min(1, accuracy)),
                "precision": max(0, min(1, precision)),
                "recall": max(0, min(1, recall)),
                "label": timestamp.strftime("%m/%d %H:%M")
            })
        
        return trends
    
    def get_fraud_statistics(self) -> Dict[str, Any]:
        """
        Get real-time fraud detection statistics
        
        Returns:
            Fraud statistics data
        """
        return asdict(self.fraud_statistics)
    
    def update_fraud_statistics(self, 
                               transactions: int = 0,
                               flagged: int = 0,
                               blocked: int = 0):
        """
        Update fraud statistics with new data
        
        Args:
            transactions: Number of new transactions
            flagged: Number of newly flagged transactions
            blocked: Number of newly blocked transactions
        """
        self.fraud_statistics.total_transactions += transactions
        self.fraud_statistics.flagged_transactions += flagged
        self.fraud_statistics.blocked_transactions += blocked
        
        if self.fraud_statistics.total_transactions > 0:
            self.fraud_statistics.fraud_rate = (
                self.fraud_statistics.flagged_transactions / 
                self.fraud_statistics.total_transactions
            )
        
        self.fraud_statistics.timestamp = datetime.now().isoformat()
    
    def get_explainable_decision(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get explainable AI decision for a transaction
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Explainable decision data or None
        """
        if transaction_id in self.explainable_decisions:
            return asdict(self.explainable_decisions[transaction_id])
        
        # Generate sample explainable decision
        decision = ExplainableDecision(
            transaction_id=transaction_id,
            decision="flagged",
            confidence=0.87,
            reasoning_steps=[
                "Analyzed transaction amount: $2,450.00",
                "Checked user transaction history: 3 transactions in last hour",
                "Evaluated location: New location detected (500 miles from last transaction)",
                "Assessed merchant risk: Medium risk merchant category",
                "Calculated velocity score: 8.5/10 (high)",
                "Applied fraud pattern matching: Velocity abuse pattern detected",
                "Final decision: Flag for review based on multiple risk factors"
            ],
            evidence=[
                {"type": "amount", "value": 2450.00, "risk": "medium", "weight": 0.3},
                {"type": "velocity", "value": 3, "risk": "high", "weight": 0.4},
                {"type": "location", "value": "500 miles", "risk": "high", "weight": 0.3}
            ],
            risk_factors=[
                {"factor": "High velocity", "score": 8.5, "impact": "high"},
                {"factor": "Location anomaly", "score": 7.2, "impact": "medium"},
                {"factor": "Amount deviation", "score": 6.8, "impact": "medium"}
            ],
            alternative_outcomes=[
                {"decision": "approve", "confidence": 0.13, "reason": "Low probability based on risk factors"},
                {"decision": "block", "confidence": 0.45, "reason": "Could be blocked if additional risk factors present"}
            ],
            timestamp=datetime.now().isoformat()
        )
        
        self.explainable_decisions[transaction_id] = decision
        return asdict(decision)
    
    def get_fraud_heatmap(self) -> Dict[str, Any]:
        """
        Get fraud detection heatmap data
        
        Returns:
            Heatmap data with time and pattern distribution
        """
        hours = 24
        patterns = list(FraudPattern)
        
        heatmap_data = []
        
        for hour in range(hours):
            for pattern in patterns:
                intensity = random.randint(0, 10)
                heatmap_data.append({
                    "hour": hour,
                    "pattern": pattern.value,
                    "intensity": intensity,
                    "label": f"{hour}:00"
                })
        
        return {
            "data": heatmap_data,
            "hours": hours,
            "patterns": [p.value for p in patterns]
        }
    
    def get_risk_distribution(self) -> Dict[str, Any]:
        """
        Get risk score distribution
        
        Returns:
            Risk distribution data
        """
        # Generate risk score distribution
        distribution = {
            "low": 12850,  # 0-3
            "medium": 2100,  # 4-6
            "high": 380,  # 7-8
            "critical": 90  # 9-10
        }
        
        total = sum(distribution.values())
        
        return {
            "distribution": distribution,
            "percentages": {
                risk: (count / total * 100) for risk, count in distribution.items()
            },
            "total": total
        }
    
    def get_top_fraud_indicators(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top fraud indicators
        
        Args:
            limit: Number of top indicators to return
            
        Returns:
            List of top fraud indicators
        """
        indicators = [
            {"indicator": "Multiple transactions in short time", "occurrences": 145, "accuracy": 0.89},
            {"indicator": "Unusual location", "occurrences": 132, "accuracy": 0.85},
            {"indicator": "High transaction amount", "occurrences": 98, "accuracy": 0.92},
            {"indicator": "New merchant", "occurrences": 87, "accuracy": 0.78},
            {"indicator": "Card not present", "occurrences": 76, "accuracy": 0.81},
            {"indicator": "International transaction", "occurrences": 65, "accuracy": 0.83},
            {"indicator": "Unusual time of day", "occurrences": 54, "accuracy": 0.76},
            {"indicator": "Multiple failed attempts", "occurrences": 43, "accuracy": 0.94},
            {"indicator": "Device fingerprint mismatch", "occurrences": 38, "accuracy": 0.88},
            {"indicator": "Billing address mismatch", "occurrences": 32, "accuracy": 0.86}
        ]
        
        return indicators[:limit]
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics summary
        
        Returns:
            Analytics summary with all key metrics
        """
        return {
            "fraud_statistics": self.get_fraud_statistics(),
            "decision_metrics": self.get_decision_metrics(),
            "active_patterns": len(self.fraud_patterns),
            "pattern_summary": {
                "total_occurrences": sum(p.occurrences for p in self.fraud_patterns.values()),
                "avg_detection_rate": sum(p.detection_rate for p in self.fraud_patterns.values()) / len(self.fraud_patterns),
                "critical_patterns": sum(1 for p in self.fraud_patterns.values() if p.severity == "critical")
            },
            "risk_distribution": self.get_risk_distribution(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_stress_test_metrics(self) -> Dict[str, Any]:
        """
        Get stress test specific metrics
        
        Returns:
            Stress test metrics including accuracy under load
        """
        return {
            "current_load_tps": random.randint(1000, 5000),
            "peak_load_tps": 10000,
            "test_duration_seconds": random.randint(300, 3600),
            "fraud_detection_accuracy": 0.94 + random.uniform(-0.02, 0.02),
            "pattern_recognition_rate": 0.87 + random.uniform(-0.03, 0.03),
            "ml_model_performance": {
                "inference_time_ms": random.uniform(50, 150),
                "accuracy": 0.95 + random.uniform(-0.02, 0.02),
                "precision": 0.93 + random.uniform(-0.02, 0.02),
                "recall": 0.91 + random.uniform(-0.02, 0.02)
            },
            "accuracy_vs_load": self._generate_accuracy_vs_load(),
            "pattern_detection_rates": self._generate_pattern_detection_rates(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_accuracy_vs_load(self) -> List[Dict[str, Any]]:
        """Generate accuracy vs load data points"""
        data_points = []
        for tps in range(0, 10001, 500):
            # Accuracy degrades slightly at higher loads
            base_accuracy = 0.95
            load_factor = tps / 10000
            accuracy = base_accuracy - (load_factor * 0.05) + random.uniform(-0.01, 0.01)
            
            data_points.append({
                "tps": tps,
                "accuracy": max(0.85, min(0.98, accuracy)),
                "precision": max(0.83, min(0.96, accuracy + random.uniform(-0.02, 0.02))),
                "recall": max(0.82, min(0.95, accuracy + random.uniform(-0.03, 0.01)))
            })
        
        return data_points
    
    def _generate_pattern_detection_rates(self) -> Dict[str, Any]:
        """Generate pattern detection rates for heatmap"""
        patterns = [p.value for p in FraudPattern]
        load_levels = ["low", "medium", "high", "peak"]
        
        heatmap_data = []
        for pattern in patterns:
            for load in load_levels:
                # Detection rate varies by load
                base_rate = 0.90
                if load == "medium":
                    base_rate = 0.88
                elif load == "high":
                    base_rate = 0.85
                elif load == "peak":
                    base_rate = 0.82
                
                rate = base_rate + random.uniform(-0.05, 0.05)
                
                heatmap_data.append({
                    "pattern": pattern,
                    "load_level": load,
                    "detection_rate": max(0.75, min(0.98, rate))
                })
        
        return {
            "data": heatmap_data,
            "patterns": patterns,
            "load_levels": load_levels
        }
    
    def simulate_analytics_activity(self):
        """Simulate analytics activity for demo purposes"""
        # Update fraud statistics
        self.update_fraud_statistics(
            transactions=random.randint(10, 50),
            flagged=random.randint(0, 5),
            blocked=random.randint(0, 2)
        )
        
        # Update pattern occurrences
        for pattern in self.fraud_patterns.values():
            if random.random() > 0.7:
                pattern.occurrences += random.randint(1, 3)
                pattern.last_detected = datetime.now().isoformat()
