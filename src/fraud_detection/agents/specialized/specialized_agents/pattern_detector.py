"""
Pattern Detection Agent

Specialized agent for anomaly detection using statistical models, behavioral pattern
recognition, trend analysis, and pattern similarity matching.
"""

import logging
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math

from .base_agent import BaseAgent, AgentConfiguration, AgentCapability, ProcessingResult
from memory_system.models import Transaction, DecisionContext, UserBehaviorProfile, FraudDecision
from memory_system.memory_manager import MemoryManager
from memory_system.pattern_learning import PatternLearningEngine

logger = logging.getLogger(__name__)


@dataclass
class AnomalyScore:
    """Anomaly detection result."""
    anomaly_type: str
    score: float  # 0-1, higher = more anomalous
    confidence: float
    description: str
    statistical_evidence: Dict[str, float] = field(default_factory=dict)
    threshold_used: float = 0.0


@dataclass
class BehavioralPattern:
    """Behavioral pattern analysis result."""
    pattern_id: str
    pattern_type: str
    description: str
    strength: float  # 0-1, how strong the pattern is
    frequency: int
    last_seen: datetime
    trend_direction: str  # "increasing", "decreasing", "stable"
    risk_level: str  # "low", "medium", "high"


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    metric_name: str
    trend_direction: str
    trend_strength: float  # 0-1
    prediction_confidence: float
    current_value: float
    predicted_next_value: float
    time_window_days: int
    data_points: int


@dataclass
class PatternDetectionResult:
    """Complete pattern detection analysis result."""
    transaction_id: str
    anomaly_scores: List[AnomalyScore] = field(default_factory=list)
    behavioral_patterns: List[BehavioralPattern] = field(default_factory=list)
    trend_analyses: List[TrendAnalysis] = field(default_factory=list)
    overall_anomaly_score: float = 0.0
    pattern_similarity_matches: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class PatternDetector(BaseAgent):
    """
    Specialized agent for pattern detection and anomaly analysis.
    
    Capabilities:
    - Statistical anomaly detection
    - Behavioral pattern recognition
    - Trend analysis and prediction
    - Pattern similarity matching
    - Real-time pattern monitoring
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        pattern_learning_engine: PatternLearningEngine,
        config: Optional[AgentConfiguration] = None
    ):
        """
        Initialize the Pattern Detection Agent.
        
        Args:
            memory_manager: Memory manager for data access
            pattern_learning_engine: Pattern learning engine for pattern analysis
            config: Agent configuration (optional)
        """
        if config is None:
            config = AgentConfiguration(
                agent_id="pattern_detector_001",
                agent_name="PatternDetector",
                version="1.0.0",
                capabilities=[
                    AgentCapability.PATTERN_DETECTION,
                    AgentCapability.REAL_TIME_PROCESSING,
                    AgentCapability.LEARNING_ADAPTATION
                ],
                max_concurrent_requests=30,
                timeout_seconds=15,
                custom_parameters={
                    "anomaly_threshold": 0.7,
                    "pattern_similarity_threshold": 0.8,
                    "trend_analysis_window_days": 30,
                    "min_data_points_for_analysis": 10
                }
            )
        
        self.memory_manager = memory_manager
        self.pattern_learning_engine = pattern_learning_engine
        
        # Statistical models and thresholds
        self.statistical_models = {}
        self.user_baselines = {}  # user_id -> baseline statistics
        self.pattern_cache = {}  # Cache for frequently accessed patterns
        
        super().__init__(config)
    
    def _initialize_agent(self) -> None:
        """Initialize pattern detector specific components."""
        self.logger.info("Initializing Pattern Detection Agent")
        
        # Initialize statistical models
        self._initialize_statistical_models()
        
        # Initialize anomaly detection thresholds
        self.anomaly_thresholds = {
            "amount_anomaly": 2.5,  # Standard deviations
            "frequency_anomaly": 2.0,
            "temporal_anomaly": 1.5,
            "merchant_anomaly": 3.0,
            "location_anomaly": 2.0
        }
        
        # Initialize pattern recognition parameters
        self.pattern_recognition_config = {
            "min_pattern_occurrences": 3,
            "pattern_time_window_days": 90,
            "similarity_threshold": 0.75
        }
        
        self.logger.info("Pattern Detection Agent initialized successfully")
    
    def process_request(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process a pattern detection request.
        
        Args:
            request_data: Dictionary containing transaction data and analysis type
            
        Returns:
            ProcessingResult with pattern detection analysis
        """
        try:
            # Extract transaction and analysis parameters
            transaction = self._extract_transaction(request_data)
            analysis_type = request_data.get("analysis_type", "full")
            
            if not transaction:
                return ProcessingResult(
                    success=False,
                    result_data={},
                    processing_time_ms=0.0,
                    confidence_score=0.0,
                    error_message="Invalid transaction data"
                )
            
            # Perform pattern detection analysis
            detection_result = self._analyze_patterns(transaction, analysis_type)
            
            return ProcessingResult(
                success=True,
                result_data={
                    "pattern_detection": detection_result.__dict__,
                    "transaction_id": transaction.id,
                    "analysis_type": analysis_type,
                    "timestamp": datetime.now().isoformat()
                },
                processing_time_ms=0.0,  # Will be set by base class
                confidence_score=self._calculate_overall_confidence(detection_result),
                metadata={
                    "agent_type": "pattern_detector",
                    "analysis_version": "1.0.0"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error in pattern detection: {str(e)}")
            return ProcessingResult(
                success=False,
                result_data={},
                processing_time_ms=0.0,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _extract_transaction(self, request_data: Dict[str, Any]) -> Optional[Transaction]:
        """Extract transaction from request data."""
        try:
            if "transaction" in request_data:
                tx_data = request_data["transaction"]
            else:
                tx_data = request_data
            
            # For demo purposes, create a simplified transaction
            from memory_system.models import Location, DeviceInfo
            
            location = Location(
                country=tx_data.get("location", {}).get("country", ""),
                city=tx_data.get("location", {}).get("city", "")
            )
            
            device_info = DeviceInfo(
                device_id=tx_data.get("device_info", {}).get("device_id", ""),
                device_type=tx_data.get("device_info", {}).get("device_type", ""),
                os=tx_data.get("device_info", {}).get("os", "")
            )
            
            transaction = Transaction(
                id=tx_data.get("id", ""),
                user_id=tx_data.get("user_id", ""),
                amount=Decimal(str(tx_data.get("amount", 0))),
                currency=tx_data.get("currency", "USD"),
                merchant=tx_data.get("merchant", ""),
                category=tx_data.get("category", ""),
                location=location,
                timestamp=datetime.fromisoformat(tx_data.get("timestamp", datetime.now().isoformat())),
                card_type=tx_data.get("card_type", ""),
                device_info=device_info,
                ip_address=tx_data.get("ip_address", ""),
                session_id=tx_data.get("session_id", ""),
                metadata=tx_data.get("metadata", {})
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error extracting transaction: {str(e)}")
            return None
    
    def _analyze_patterns(self, transaction: Transaction, analysis_type: str) -> PatternDetectionResult:
        """Perform comprehensive pattern detection analysis."""
        result = PatternDetectionResult(transaction_id=transaction.id)
        
        # 1. Statistical Anomaly Detection
        if analysis_type in ["full", "anomaly"]:
            anomaly_scores = self._detect_statistical_anomalies(transaction)
            result.anomaly_scores.extend(anomaly_scores)
        
        # 2. Behavioral Pattern Recognition
        if analysis_type in ["full", "behavioral"]:
            behavioral_patterns = self._recognize_behavioral_patterns(transaction)
            result.behavioral_patterns.extend(behavioral_patterns)
        
        # 3. Trend Analysis
        if analysis_type in ["full", "trend"]:
            trend_analyses = self._analyze_trends(transaction)
            result.trend_analyses.extend(trend_analyses)
        
        # 4. Pattern Similarity Matching
        if analysis_type in ["full", "similarity"]:
            similarity_matches = self._find_pattern_similarities(transaction)
            result.pattern_similarity_matches.extend(similarity_matches)
        
        # 5. Calculate overall anomaly score
        result.overall_anomaly_score = self._calculate_overall_anomaly_score(result)
        
        # 6. Generate recommendations
        result.recommendations = self._generate_pattern_recommendations(result)
        
        return result
    
    def _detect_statistical_anomalies(self, transaction: Transaction) -> List[AnomalyScore]:
        """Detect statistical anomalies using various models."""
        anomalies = []
        
        # Get user baseline statistics
        user_baseline = self._get_user_baseline(transaction.user_id)
        
        # Amount anomaly detection
        amount_anomaly = self._detect_amount_anomaly(transaction, user_baseline)
        if amount_anomaly:
            anomalies.append(amount_anomaly)
        
        # Temporal anomaly detection
        temporal_anomaly = self._detect_temporal_anomaly(transaction, user_baseline)
        if temporal_anomaly:
            anomalies.append(temporal_anomaly)
        
        # Merchant anomaly detection
        merchant_anomaly = self._detect_merchant_anomaly(transaction, user_baseline)
        if merchant_anomaly:
            anomalies.append(merchant_anomaly)
        
        # Location anomaly detection
        location_anomaly = self._detect_location_anomaly(transaction, user_baseline)
        if location_anomaly:
            anomalies.append(location_anomaly)
        
        return anomalies
    
    def _detect_amount_anomaly(self, transaction: Transaction, baseline: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Detect anomalies in transaction amount."""
        if not baseline.get("amount_stats"):
            return None
        
        amount = float(transaction.amount)
        mean_amount = baseline["amount_stats"]["mean"]
        std_amount = baseline["amount_stats"]["std"]
        
        if std_amount == 0:
            return None
        
        z_score = abs(amount - mean_amount) / std_amount
        threshold = self.anomaly_thresholds["amount_anomaly"]
        
        if z_score > threshold:
            anomaly_score = min(1.0, z_score / (threshold * 2))
            confidence = min(0.95, 0.5 + (z_score - threshold) / threshold)
            
            return AnomalyScore(
                anomaly_type="amount_anomaly",
                score=anomaly_score,
                confidence=confidence,
                description=f"Transaction amount ${amount:.2f} is {z_score:.1f} standard deviations from user's average ${mean_amount:.2f}",
                statistical_evidence={
                    "z_score": z_score,
                    "user_mean": mean_amount,
                    "user_std": std_amount,
                    "threshold": threshold
                },
                threshold_used=threshold
            )
        
        return None
    
    def _detect_temporal_anomaly(self, transaction: Transaction, baseline: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Detect temporal anomalies (unusual times)."""
        hour = transaction.timestamp.hour
        
        # Check for obviously unusual times
        if 2 <= hour <= 5:  # Late night/early morning
            return AnomalyScore(
                anomaly_type="temporal_anomaly",
                score=0.7,
                confidence=0.8,
                description=f"Transaction at unusual hour: {hour:02d}:00 (late night/early morning)",
                statistical_evidence={"hour": hour, "time_category": "late_night"}
            )
        
        return None
    
    def _detect_merchant_anomaly(self, transaction: Transaction, baseline: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Detect merchant-related anomalies."""
        merchant = transaction.merchant
        
        # Check for high-risk merchant categories
        high_risk_keywords = ["casino", "gambling", "crypto", "bitcoin", "adult", "pharmacy"]
        merchant_lower = merchant.lower()
        
        for keyword in high_risk_keywords:
            if keyword in merchant_lower:
                return AnomalyScore(
                    anomaly_type="merchant_anomaly",
                    score=0.8,
                    confidence=0.9,
                    description=f"Transaction with high-risk merchant category: {merchant}",
                    statistical_evidence={
                        "merchant": merchant,
                        "risk_keyword": keyword,
                        "risk_category": "high_risk_merchant"
                    }
                )
        
        return None
    
    def _detect_location_anomaly(self, transaction: Transaction, baseline: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Detect location-related anomalies."""
        location = transaction.location
        
        if baseline.get("location_stats"):
            common_countries = baseline["location_stats"]["common_countries"]
            
            # Check for new country
            if location.country not in common_countries:
                return AnomalyScore(
                    anomaly_type="location_anomaly",
                    score=0.7,
                    confidence=0.8,
                    description=f"Transaction in new country: {location.country}",
                    statistical_evidence={
                        "country": location.country,
                        "city": location.city,
                        "is_new_country": True,
                        "common_countries": common_countries
                    }
                )
        
        return None
    
    def _recognize_behavioral_patterns(self, transaction: Transaction) -> List[BehavioralPattern]:
        """Recognize behavioral patterns in user's transaction history."""
        patterns = []
        
        # Get user's transaction history
        user_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=self.pattern_recognition_config["pattern_time_window_days"]
        )
        
        if len(user_transactions) < self.pattern_recognition_config["min_pattern_occurrences"]:
            return patterns
        
        # Add current transaction to analysis
        all_transactions = user_transactions + [transaction]
        
        # Detect spending patterns
        spending_patterns = self._detect_spending_patterns(all_transactions)
        patterns.extend(spending_patterns)
        
        return patterns
    
    def _detect_spending_patterns(self, transactions: List[Transaction]) -> List[BehavioralPattern]:
        """Detect spending behavior patterns."""
        patterns = []
        
        if len(transactions) < 5:
            return patterns
        
        # Analyze spending amounts over time
        amounts = [float(tx.amount) for tx in transactions[-10:]]  # Last 10 transactions
        
        # Check for escalating spending pattern
        if len(amounts) >= 5:
            increases = sum(1 for i in range(1, len(amounts)) if amounts[i] > amounts[i-1])
            if increases >= len(amounts) * 0.7:  # 70% of transactions are increases
                patterns.append(BehavioralPattern(
                    pattern_id=f"escalating_spending_{transactions[-1].user_id}",
                    pattern_type="escalating_spending",
                    description="User shows escalating spending pattern",
                    strength=increases / len(amounts),
                    frequency=increases,
                    last_seen=transactions[-1].timestamp,
                    trend_direction="increasing",
                    risk_level="medium"
                ))
        
        return patterns
    
    def _analyze_trends(self, transaction: Transaction) -> List[TrendAnalysis]:
        """Analyze trends in user behavior."""
        trends = []
        
        # Get user's transaction history for trend analysis
        window_days = self.config.custom_parameters.get("trend_analysis_window_days", 30)
        user_transactions = self.memory_manager.get_user_transaction_history(
            transaction.user_id, days_back=window_days
        )
        
        min_data_points = self.config.custom_parameters.get("min_data_points_for_analysis", 10)
        if len(user_transactions) < min_data_points:
            return trends
        
        # Analyze spending amount trend
        amount_trend = self._analyze_amount_trend(user_transactions, window_days)
        if amount_trend:
            trends.append(amount_trend)
        
        return trends
    
    def _analyze_amount_trend(self, transactions: List[Transaction], window_days: int) -> Optional[TrendAnalysis]:
        """Analyze trend in transaction amounts."""
        if len(transactions) < 5:
            return None
        
        # Sort transactions by timestamp
        sorted_transactions = sorted(transactions, key=lambda tx: tx.timestamp)
        amounts = [float(tx.amount) for tx in sorted_transactions]
        
        # Simple linear trend analysis
        n = len(amounts)
        x = list(range(n))
        
        # Calculate linear regression
        x_mean = sum(x) / n
        y_mean = sum(amounts) / n
        
        numerator = sum((x[i] - x_mean) * (amounts[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return None
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Determine trend direction and strength
        trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        trend_strength = min(1.0, abs(slope) / (y_mean / n) if y_mean > 0 else 0)
        
        # Predict next value
        predicted_next = slope * n + intercept
        
        # Calculate confidence based on R-squared
        y_pred = [slope * i + intercept for i in x]
        ss_res = sum((amounts[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((amounts[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return TrendAnalysis(
            metric_name="transaction_amount",
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            prediction_confidence=max(0.1, min(0.9, r_squared)),
            current_value=amounts[-1],
            predicted_next_value=max(0, predicted_next),
            time_window_days=window_days,
            data_points=len(amounts)
        )
    
    def _find_pattern_similarities(self, transaction: Transaction) -> List[Dict[str, Any]]:
        """Find similar patterns in known fraud patterns."""
        similarities = []
        
        try:
            # Get all known fraud patterns
            fraud_patterns = self.memory_manager.get_all_fraud_patterns()
            
            similarity_threshold = self.config.custom_parameters.get("pattern_similarity_threshold", 0.8)
            
            for pattern in fraud_patterns:
                similarity_score = self._calculate_pattern_similarity(transaction, pattern)
                
                if similarity_score >= similarity_threshold:
                    similarities.append({
                        "pattern_id": pattern.pattern_id,
                        "pattern_type": pattern.pattern_type,
                        "similarity_score": similarity_score,
                        "description": pattern.description,
                        "effectiveness_score": pattern.effectiveness_score
                    })
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            
        except Exception as e:
            self.logger.warning(f"Error finding pattern similarities: {str(e)}")
        
        return similarities[:5]  # Return top 5 matches
    
    def _calculate_pattern_similarity(self, transaction: Transaction, pattern) -> float:
        """Calculate similarity between transaction and known pattern."""
        # Simplified similarity calculation
        similarity_factors = []
        
        # Check pattern type relevance
        if pattern.pattern_type == "velocity_fraud":
            # Check if transaction shows velocity characteristics
            recent_transactions = self.memory_manager.get_user_transaction_history(
                transaction.user_id, days_back=1, limit=10
            )
            if len(recent_transactions) > 3:
                similarity_factors.append(0.8)
            else:
                similarity_factors.append(0.2)
        
        elif pattern.pattern_type == "amount_fraud":
            # Check if transaction amount is suspicious
            if float(transaction.amount) > 1000:
                similarity_factors.append(0.7)
            else:
                similarity_factors.append(0.3)
        
        else:
            similarity_factors.append(0.4)
        
        # Calculate overall similarity
        if similarity_factors:
            return sum(similarity_factors) / len(similarity_factors)
        else:
            return 0.0
    
    def _calculate_overall_anomaly_score(self, result: PatternDetectionResult) -> float:
        """Calculate overall anomaly score from all detected anomalies."""
        if not result.anomaly_scores:
            return 0.0
        
        # Weight different types of anomalies
        weights = {
            "amount_anomaly": 0.3,
            "temporal_anomaly": 0.2,
            "merchant_anomaly": 0.3,
            "location_anomaly": 0.2
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for anomaly in result.anomaly_scores:
            weight = weights.get(anomaly.anomaly_type, 0.1)
            weighted_score += anomaly.score * anomaly.confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            return min(1.0, weighted_score / total_weight)
        else:
            return 0.0
    
    def _calculate_overall_confidence(self, result: PatternDetectionResult) -> float:
        """Calculate overall confidence in the pattern detection results."""
        confidence_factors = []
        
        # Confidence from anomaly detection
        if result.anomaly_scores:
            avg_anomaly_confidence = sum(a.confidence for a in result.anomaly_scores) / len(result.anomaly_scores)
            confidence_factors.append(avg_anomaly_confidence)
        
        # Confidence from behavioral patterns
        if result.behavioral_patterns:
            avg_pattern_strength = sum(p.strength for p in result.behavioral_patterns) / len(result.behavioral_patterns)
            confidence_factors.append(avg_pattern_strength)
        
        # Confidence from trend analysis
        if result.trend_analyses:
            avg_trend_confidence = sum(t.prediction_confidence for t in result.trend_analyses) / len(result.trend_analyses)
            confidence_factors.append(avg_trend_confidence)
        
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5  # Default confidence
    
    def _generate_pattern_recommendations(self, result: PatternDetectionResult) -> List[str]:
        """Generate recommendations based on pattern detection results."""
        recommendations = []
        
        # Recommendations based on anomaly scores
        high_anomalies = [a for a in result.anomaly_scores if a.score > 0.7]
        if high_anomalies:
            recommendations.append(f"High anomaly detected: {', '.join(a.anomaly_type for a in high_anomalies)}")
        
        # Recommendations based on overall anomaly score
        if result.overall_anomaly_score > 0.8:
            recommendations.append("RECOMMEND: Decline transaction due to high anomaly score")
        elif result.overall_anomaly_score > 0.5:
            recommendations.append("RECOMMEND: Flag transaction for manual review")
        else:
            recommendations.append("RECOMMEND: Approve transaction - low anomaly score")
        
        return recommendations
    
    def _get_user_baseline(self, user_id: str) -> Dict[str, Any]:
        """Get or calculate user baseline statistics."""
        if user_id in self.user_baselines:
            return self.user_baselines[user_id]
        
        # Calculate baseline from user's transaction history
        baseline = self._calculate_user_baseline(user_id)
        self.user_baselines[user_id] = baseline
        
        return baseline
    
    def _calculate_user_baseline(self, user_id: str) -> Dict[str, Any]:
        """Calculate baseline statistics for a user."""
        baseline = {}
        
        try:
            # Get user's transaction history
            transactions = self.memory_manager.get_user_transaction_history(user_id, days_back=90)
            
            if len(transactions) < 5:
                return baseline
            
            # Amount statistics
            amounts = [float(tx.amount) for tx in transactions]
            baseline["amount_stats"] = {
                "mean": statistics.mean(amounts),
                "std": statistics.stdev(amounts) if len(amounts) > 1 else 0,
                "median": statistics.median(amounts),
                "min": min(amounts),
                "max": max(amounts)
            }
            
            # Location statistics
            countries = [tx.location.country for tx in transactions if tx.location.country]
            cities = [tx.location.city for tx in transactions if tx.location.city]
            
            baseline["location_stats"] = {
                "common_countries": list(set(countries)),
                "common_cities": list(set(cities))
            }
            
        except Exception as e:
            self.logger.warning(f"Error calculating user baseline: {str(e)}")
        
        return baseline
    
    def _initialize_statistical_models(self) -> None:
        """Initialize statistical models for anomaly detection."""
        self.statistical_models = {
            "z_score": {"threshold": 2.5},
            "isolation_forest": {"contamination": 0.1},
            "local_outlier_factor": {"n_neighbors": 20}
        }
    
    def get_pattern_cache_stats(self) -> Dict[str, Any]:
        """Get pattern cache statistics."""
        return {
            "cached_patterns": len(self.pattern_cache),
            "cached_baselines": len(self.user_baselines),
            "cache_size_estimate": len(str(self.pattern_cache)) + len(str(self.user_baselines))
        }
    
    def clear_pattern_cache(self) -> None:
        """Clear pattern cache to free memory."""
        self.pattern_cache.clear()
        self.user_baselines.clear()
        self.logger.info("Pattern cache cleared")