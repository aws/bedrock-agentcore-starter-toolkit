"""
Pattern Learning and Adaptation Engine

Implements fraud pattern detection, learning algorithms, and continuous improvement
through feedback incorporation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import statistics
from decimal import Decimal

from .models import (
    Transaction, FraudPattern, FraudDecision, DecisionContext,
    UserBehaviorProfile, RiskLevel
)
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class PatternMetrics:
    """Metrics for evaluating pattern effectiveness."""
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    
    @property
    def precision(self) -> float:
        """Calculate precision (TP / (TP + FP))."""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)
    
    @property
    def recall(self) -> float:
        """Calculate recall (TP / (TP + FN))."""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)
    
    @property
    def f1_score(self) -> float:
        """Calculate F1 score (2 * precision * recall / (precision + recall))."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)
    
    @property
    def accuracy(self) -> float:
        """Calculate accuracy ((TP + TN) / (TP + TN + FP + FN))."""
        total = self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total


@dataclass
class LearningFeedback:
    """Feedback data for pattern learning."""
    transaction_id: str
    actual_outcome: str  # "fraud", "legitimate", "unknown"
    predicted_decision: FraudDecision
    confidence_score: float
    pattern_ids_triggered: List[str]
    timestamp: datetime
    feedback_source: str  # "manual_review", "customer_dispute", "investigation"
    additional_context: Dict[str, Any] = field(default_factory=dict)


class PatternLearningEngine:
    """
    Engine for learning and adapting fraud detection patterns.
    
    Provides capabilities for:
    - Fraud pattern detection and creation
    - Learning algorithm for updating detection rules
    - Feedback incorporation for continuous improvement
    - Performance monitoring for learning effectiveness
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize the Pattern Learning Engine.
        
        Args:
            memory_manager: MemoryManager instance for data persistence
        """
        self.memory_manager = memory_manager
        self.pattern_metrics: Dict[str, PatternMetrics] = {}
        self.learning_rate = 0.1
        self.min_pattern_confidence = 0.6
        self.pattern_update_threshold = 10  # Minimum feedback samples before updating
    
    def detect_new_patterns(
        self, 
        lookback_days: int = 30,
        min_occurrences: int = 5
    ) -> List[FraudPattern]:
        """
        Detect new fraud patterns from recent transaction data.
        
        Args:
            lookback_days: Number of days to analyze
            min_occurrences: Minimum occurrences to consider a pattern
            
        Returns:
            List of newly detected fraud patterns
        """
        logger.info(f"Detecting new patterns from last {lookback_days} days")
        
        # Get recent transactions and decisions
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Analyze velocity patterns
        velocity_patterns = self._detect_velocity_patterns(start_date, end_date, min_occurrences)
        
        # Analyze merchant patterns
        merchant_patterns = self._detect_merchant_patterns(start_date, end_date, min_occurrences)
        
        # Analyze geographic patterns
        geographic_patterns = self._detect_geographic_patterns(start_date, end_date, min_occurrences)
        
        # Analyze amount patterns
        amount_patterns = self._detect_amount_patterns(start_date, end_date, min_occurrences)
        
        new_patterns = velocity_patterns + merchant_patterns + geographic_patterns + amount_patterns
        
        # Store new patterns
        for pattern in new_patterns:
            success = self.memory_manager.store_fraud_pattern(pattern)
            if success:
                logger.info(f"Stored new pattern: {pattern.pattern_id}")
            else:
                logger.error(f"Failed to store pattern: {pattern.pattern_id}")
        
        return new_patterns
    
    def _detect_velocity_patterns(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        min_occurrences: int
    ) -> List[FraudPattern]:
        """Detect velocity-based fraud patterns."""
        patterns = []
        
        # Get all users with multiple transactions in the period
        user_transactions = defaultdict(list)
        
        # This would typically query the database for transactions in the date range
        # For now, we'll create a sample pattern
        
        # Detect rapid-fire transaction pattern
        pattern = FraudPattern(
            pattern_id=f"velocity_rapid_fire_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pattern_type="velocity_fraud",
            description="Multiple transactions within short time window",
            indicators=[
                "More than 3 transactions in 5 minutes",
                "Increasing transaction amounts",
                "Different merchants or locations"
            ],
            confidence_threshold=0.8,
            detection_count=0,
            false_positive_rate=0.0,
            created_at=datetime.now(),
            last_seen=datetime.now(),
            effectiveness_score=0.0
        )
        patterns.append(pattern)
        
        return patterns
    
    def _detect_merchant_patterns(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        min_occurrences: int
    ) -> List[FraudPattern]:
        """Detect merchant-based fraud patterns."""
        patterns = []
        
        # Detect high-risk merchant pattern
        pattern = FraudPattern(
            pattern_id=f"merchant_high_risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pattern_type="merchant_fraud",
            description="Transactions with high-risk merchants",
            indicators=[
                "Merchant in high-risk category",
                "Multiple failed transactions from same merchant",
                "Unusual transaction amounts for merchant type"
            ],
            confidence_threshold=0.7,
            detection_count=0,
            false_positive_rate=0.0,
            created_at=datetime.now(),
            last_seen=datetime.now(),
            effectiveness_score=0.0
        )
        patterns.append(pattern)
        
        return patterns
    
    def _detect_geographic_patterns(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        min_occurrences: int
    ) -> List[FraudPattern]:
        """Detect geographic-based fraud patterns."""
        patterns = []
        
        # Detect impossible travel pattern
        pattern = FraudPattern(
            pattern_id=f"geo_impossible_travel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pattern_type="geographic_fraud",
            description="Impossible travel between transaction locations",
            indicators=[
                "Transactions in different countries within short time",
                "Distance exceeds possible travel time",
                "No travel history to destination country"
            ],
            confidence_threshold=0.9,
            detection_count=0,
            false_positive_rate=0.0,
            created_at=datetime.now(),
            last_seen=datetime.now(),
            effectiveness_score=0.0
        )
        patterns.append(pattern)
        
        return patterns
    
    def _detect_amount_patterns(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        min_occurrences: int
    ) -> List[FraudPattern]:
        """Detect amount-based fraud patterns."""
        patterns = []
        
        # Detect round amount pattern
        pattern = FraudPattern(
            pattern_id=f"amount_round_numbers_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pattern_type="amount_fraud",
            description="Suspicious round number transactions",
            indicators=[
                "Multiple round number amounts (100, 200, 500)",
                "Amounts just below reporting thresholds",
                "Unusual amount for merchant category"
            ],
            confidence_threshold=0.6,
            detection_count=0,
            false_positive_rate=0.0,
            created_at=datetime.now(),
            last_seen=datetime.now(),
            effectiveness_score=0.0
        )
        patterns.append(pattern)
        
        return patterns
    
    def incorporate_feedback(self, feedback: LearningFeedback) -> bool:
        """
        Incorporate feedback to improve pattern detection.
        
        Args:
            feedback: LearningFeedback object with outcome information
            
        Returns:
            bool: True if feedback was successfully incorporated
        """
        try:
            logger.info(f"Incorporating feedback for transaction {feedback.transaction_id}")
            
            # Update pattern metrics for each triggered pattern
            for pattern_id in feedback.pattern_ids_triggered:
                if pattern_id not in self.pattern_metrics:
                    self.pattern_metrics[pattern_id] = PatternMetrics()
                
                metrics = self.pattern_metrics[pattern_id]
                
                # Update metrics based on feedback
                if feedback.actual_outcome == "fraud":
                    if feedback.predicted_decision in [FraudDecision.DECLINED, FraudDecision.FLAGGED]:
                        metrics.true_positives += 1
                    else:
                        metrics.false_negatives += 1
                elif feedback.actual_outcome == "legitimate":
                    if feedback.predicted_decision in [FraudDecision.DECLINED, FraudDecision.FLAGGED]:
                        metrics.false_positives += 1
                    else:
                        metrics.true_negatives += 1
                
                # Check if we have enough feedback to update the pattern
                total_feedback = (metrics.true_positives + metrics.false_positives + 
                                metrics.true_negatives + metrics.false_negatives)
                
                if total_feedback >= self.pattern_update_threshold:
                    self._update_pattern_parameters(pattern_id, metrics)
            
            return True
            
        except Exception as e:
            logger.error(f"Error incorporating feedback: {str(e)}")
            return False
    
    def _update_pattern_parameters(self, pattern_id: str, metrics: PatternMetrics) -> bool:
        """
        Update pattern parameters based on performance metrics.
        
        Args:
            pattern_id: ID of the pattern to update
            metrics: Performance metrics for the pattern
            
        Returns:
            bool: True if pattern was successfully updated
        """
        try:
            # Get existing pattern
            patterns = self.memory_manager.get_all_fraud_patterns()
            pattern = next((p for p in patterns if p.pattern_id == pattern_id), None)
            
            if not pattern:
                logger.warning(f"Pattern {pattern_id} not found for update")
                return False
            
            # Calculate new parameters
            old_threshold = pattern.confidence_threshold
            old_effectiveness = pattern.effectiveness_score
            
            # Adjust confidence threshold based on precision
            if metrics.precision < 0.7:  # Too many false positives
                pattern.confidence_threshold = min(0.95, pattern.confidence_threshold + self.learning_rate)
            elif metrics.precision > 0.9 and metrics.recall < 0.7:  # Too conservative
                pattern.confidence_threshold = max(0.5, pattern.confidence_threshold - self.learning_rate)
            
            # Update effectiveness score (F1 score)
            pattern.effectiveness_score = metrics.f1_score
            
            # Update false positive rate
            total_positives = metrics.true_positives + metrics.false_positives
            if total_positives > 0:
                pattern.false_positive_rate = metrics.false_positives / total_positives
            
            # Update detection count
            pattern.detection_count += metrics.true_positives + metrics.false_positives
            
            # Update last seen
            pattern.last_seen = datetime.now()
            
            # Store updated pattern
            success = self.memory_manager.store_fraud_pattern(pattern)
            
            if success:
                logger.info(f"Updated pattern {pattern_id}: threshold {old_threshold:.3f} -> {pattern.confidence_threshold:.3f}, "
                          f"effectiveness {old_effectiveness:.3f} -> {pattern.effectiveness_score:.3f}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating pattern {pattern_id}: {str(e)}")
            return False
    
    def evaluate_pattern_performance(self, days_back: int = 30) -> Dict[str, Dict[str, float]]:
        """
        Evaluate the performance of all fraud patterns.
        
        Args:
            days_back: Number of days to look back for evaluation
            
        Returns:
            Dictionary mapping pattern IDs to performance metrics
        """
        performance_report = {}
        
        try:
            # Get all patterns
            patterns = self.memory_manager.get_all_fraud_patterns()
            
            for pattern in patterns:
                if pattern.pattern_id in self.pattern_metrics:
                    metrics = self.pattern_metrics[pattern.pattern_id]
                    
                    performance_report[pattern.pattern_id] = {
                        "precision": metrics.precision,
                        "recall": metrics.recall,
                        "f1_score": metrics.f1_score,
                        "accuracy": metrics.accuracy,
                        "false_positive_rate": pattern.false_positive_rate,
                        "effectiveness_score": pattern.effectiveness_score,
                        "detection_count": pattern.detection_count,
                        "confidence_threshold": pattern.confidence_threshold
                    }
                else:
                    # Pattern has no feedback yet
                    performance_report[pattern.pattern_id] = {
                        "precision": 0.0,
                        "recall": 0.0,
                        "f1_score": 0.0,
                        "accuracy": 0.0,
                        "false_positive_rate": pattern.false_positive_rate,
                        "effectiveness_score": pattern.effectiveness_score,
                        "detection_count": pattern.detection_count,
                        "confidence_threshold": pattern.confidence_threshold
                    }
            
            logger.info(f"Evaluated performance for {len(performance_report)} patterns")
            return performance_report
            
        except Exception as e:
            logger.error(f"Error evaluating pattern performance: {str(e)}")
            return {}
    
    def get_learning_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate recommendations for improving pattern learning.
        
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        try:
            performance_report = self.evaluate_pattern_performance()
            
            for pattern_id, metrics in performance_report.items():
                # Low precision - too many false positives
                if metrics["precision"] < 0.7:
                    recommendations.append({
                        "pattern_id": pattern_id,
                        "type": "increase_threshold",
                        "reason": f"Low precision ({metrics['precision']:.3f}) - too many false positives",
                        "suggested_action": "Increase confidence threshold or refine indicators",
                        "priority": "high" if metrics["precision"] < 0.5 else "medium"
                    })
                
                # Low recall - missing fraud cases
                if metrics["recall"] < 0.7:
                    recommendations.append({
                        "pattern_id": pattern_id,
                        "type": "decrease_threshold",
                        "reason": f"Low recall ({metrics['recall']:.3f}) - missing fraud cases",
                        "suggested_action": "Decrease confidence threshold or add more indicators",
                        "priority": "high" if metrics["recall"] < 0.5 else "medium"
                    })
                
                # Low detection count - pattern not triggering
                if metrics["detection_count"] < 5:
                    recommendations.append({
                        "pattern_id": pattern_id,
                        "type": "review_pattern",
                        "reason": f"Low detection count ({metrics['detection_count']}) - pattern rarely triggers",
                        "suggested_action": "Review pattern relevance or broaden indicators",
                        "priority": "low"
                    })
                
                # High effectiveness - good pattern
                if metrics["f1_score"] > 0.8:
                    recommendations.append({
                        "pattern_id": pattern_id,
                        "type": "maintain_pattern",
                        "reason": f"High F1 score ({metrics['f1_score']:.3f}) - well-performing pattern",
                        "suggested_action": "Maintain current configuration",
                        "priority": "low"
                    })
            
            logger.info(f"Generated {len(recommendations)} learning recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating learning recommendations: {str(e)}")
            return []
    
    def optimize_pattern_thresholds(self) -> Dict[str, float]:
        """
        Optimize confidence thresholds for all patterns based on performance.
        
        Returns:
            Dictionary mapping pattern IDs to new optimal thresholds
        """
        optimized_thresholds = {}
        
        try:
            for pattern_id, metrics in self.pattern_metrics.items():
                if (metrics.true_positives + metrics.false_positives + 
                    metrics.true_negatives + metrics.false_negatives) < self.pattern_update_threshold:
                    continue  # Not enough data
                
                # Find optimal threshold that maximizes F1 score
                # This is a simplified optimization - in practice, you might use more sophisticated methods
                current_f1 = metrics.f1_score
                
                # Try different threshold adjustments
                best_threshold = None
                best_f1 = current_f1
                
                for adjustment in [-0.2, -0.1, -0.05, 0.05, 0.1, 0.2]:
                    # Get current pattern
                    patterns = self.memory_manager.get_all_fraud_patterns()
                    pattern = next((p for p in patterns if p.pattern_id == pattern_id), None)
                    
                    if pattern:
                        new_threshold = max(0.1, min(0.95, pattern.confidence_threshold + adjustment))
                        
                        # Simulate performance with new threshold
                        # In practice, you'd need historical data to evaluate this properly
                        simulated_f1 = self._simulate_threshold_performance(pattern_id, new_threshold)
                        
                        if simulated_f1 > best_f1:
                            best_f1 = simulated_f1
                            best_threshold = new_threshold
                
                if best_threshold is not None:
                    optimized_thresholds[pattern_id] = best_threshold
            
            logger.info(f"Optimized thresholds for {len(optimized_thresholds)} patterns")
            return optimized_thresholds
            
        except Exception as e:
            logger.error(f"Error optimizing pattern thresholds: {str(e)}")
            return {}
    
    def _simulate_threshold_performance(self, pattern_id: str, threshold: float) -> float:
        """
        Simulate pattern performance with a different threshold.
        
        Args:
            pattern_id: ID of the pattern
            threshold: New threshold to simulate
            
        Returns:
            Simulated F1 score
        """
        # This is a simplified simulation
        # In practice, you'd use historical data to evaluate threshold changes
        
        if pattern_id in self.pattern_metrics:
            metrics = self.pattern_metrics[pattern_id]
            
            # Simple heuristic: higher threshold reduces false positives but may increase false negatives
            threshold_factor = threshold / 0.7  # Assuming 0.7 as baseline
            
            adjusted_fp = max(0, metrics.false_positives * (2 - threshold_factor))
            adjusted_fn = metrics.false_negatives * threshold_factor
            
            # Calculate adjusted F1 score
            adjusted_tp = metrics.true_positives
            adjusted_tn = metrics.true_negatives
            
            if adjusted_tp + adjusted_fp == 0:
                precision = 0
            else:
                precision = adjusted_tp / (adjusted_tp + adjusted_fp)
            
            if adjusted_tp + adjusted_fn == 0:
                recall = 0
            else:
                recall = adjusted_tp / (adjusted_tp + adjusted_fn)
            
            if precision + recall == 0:
                return 0.0
            
            return 2 * precision * recall / (precision + recall)
        
        return 0.0