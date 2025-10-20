"""
Unit tests for the Pattern Learning and Adaptation Engine.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from .pattern_learning import (
    PatternLearningEngine, PatternMetrics, LearningFeedback
)
from .models import (
    Transaction, FraudPattern, FraudDecision, DecisionContext,
    Location, DeviceInfo, RiskLevel
)
from .memory_manager import MemoryManager


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager for testing."""
    return Mock(spec=MemoryManager)


@pytest.fixture
def pattern_learning_engine(mock_memory_manager):
    """Create a pattern learning engine for testing."""
    return PatternLearningEngine(mock_memory_manager)


@pytest.fixture
def sample_fraud_pattern():
    """Create a sample fraud pattern for testing."""
    return FraudPattern(
        pattern_id="test_pattern_001",
        pattern_type="velocity_fraud",
        description="Test velocity pattern",
        indicators=["Multiple transactions", "Short time window"],
        confidence_threshold=0.8,
        detection_count=10,
        false_positive_rate=0.1,
        created_at=datetime.now() - timedelta(days=30),
        last_seen=datetime.now(),
        effectiveness_score=0.85
    )


@pytest.fixture
def sample_learning_feedback():
    """Create sample learning feedback for testing."""
    return LearningFeedback(
        transaction_id="tx_123",
        actual_outcome="fraud",
        predicted_decision=FraudDecision.DECLINED,
        confidence_score=0.9,
        pattern_ids_triggered=["test_pattern_001"],
        timestamp=datetime.now(),
        feedback_source="manual_review",
        additional_context={"reviewer": "analyst_1"}
    )


class TestPatternMetrics:
    """Test cases for PatternMetrics class."""
    
    def test_precision_calculation(self):
        """Test precision calculation."""
        metrics = PatternMetrics(true_positives=8, false_positives=2, true_negatives=15, false_negatives=1)
        assert metrics.precision == 0.8  # 8 / (8 + 2)
    
    def test_recall_calculation(self):
        """Test recall calculation."""
        metrics = PatternMetrics(true_positives=8, false_positives=2, true_negatives=15, false_negatives=1)
        assert abs(metrics.recall - 0.8889) < 0.001  # 8 / (8 + 1)
    
    def test_f1_score_calculation(self):
        """Test F1 score calculation."""
        metrics = PatternMetrics(true_positives=8, false_positives=2, true_negatives=15, false_negatives=1)
        expected_f1 = 2 * 0.8 * 0.8889 / (0.8 + 0.8889)
        assert abs(metrics.f1_score - expected_f1) < 0.001
    
    def test_accuracy_calculation(self):
        """Test accuracy calculation."""
        metrics = PatternMetrics(true_positives=8, false_positives=2, true_negatives=15, false_negatives=1)
        assert abs(metrics.accuracy - 0.8846) < 0.001  # (8 + 15) / (8 + 2 + 15 + 1)
    
    def test_zero_division_handling(self):
        """Test handling of zero division cases."""
        metrics = PatternMetrics()
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0
        assert metrics.accuracy == 0.0


class TestPatternLearningEngine:
    """Test cases for PatternLearningEngine functionality."""
    
    def test_initialization(self, mock_memory_manager):
        """Test pattern learning engine initialization."""
        engine = PatternLearningEngine(mock_memory_manager)
        
        assert engine.memory_manager == mock_memory_manager
        assert engine.pattern_metrics == {}
        assert engine.learning_rate == 0.1
        assert engine.min_pattern_confidence == 0.6
        assert engine.pattern_update_threshold == 10
    
    def test_detect_new_patterns(self, pattern_learning_engine, mock_memory_manager):
        """Test detection of new fraud patterns."""
        # Mock the memory manager to return empty results for simplicity
        mock_memory_manager.store_fraud_pattern.return_value = True
        
        # Detect new patterns
        new_patterns = pattern_learning_engine.detect_new_patterns(lookback_days=30, min_occurrences=5)
        
        # Should detect at least some patterns
        assert len(new_patterns) > 0
        
        # Check that patterns have required attributes
        for pattern in new_patterns:
            assert pattern.pattern_id is not None
            assert pattern.pattern_type is not None
            assert pattern.description is not None
            assert len(pattern.indicators) > 0
            assert 0 <= pattern.confidence_threshold <= 1
            assert pattern.created_at is not None
    
    def test_incorporate_feedback_true_positive(self, pattern_learning_engine, sample_learning_feedback):
        """Test incorporating feedback for true positive case."""
        # Modify feedback to be a true positive
        feedback = sample_learning_feedback
        feedback.actual_outcome = "fraud"
        feedback.predicted_decision = FraudDecision.DECLINED
        
        # Incorporate feedback
        success = pattern_learning_engine.incorporate_feedback(feedback)
        assert success is True
        
        # Check that metrics were updated
        pattern_id = feedback.pattern_ids_triggered[0]
        assert pattern_id in pattern_learning_engine.pattern_metrics
        
        metrics = pattern_learning_engine.pattern_metrics[pattern_id]
        assert metrics.true_positives == 1
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 0
        assert metrics.false_negatives == 0
    
    def test_incorporate_feedback_false_positive(self, pattern_learning_engine, sample_learning_feedback):
        """Test incorporating feedback for false positive case."""
        # Modify feedback to be a false positive
        feedback = sample_learning_feedback
        feedback.actual_outcome = "legitimate"
        feedback.predicted_decision = FraudDecision.DECLINED
        
        # Incorporate feedback
        success = pattern_learning_engine.incorporate_feedback(feedback)
        assert success is True
        
        # Check that metrics were updated
        pattern_id = feedback.pattern_ids_triggered[0]
        metrics = pattern_learning_engine.pattern_metrics[pattern_id]
        assert metrics.true_positives == 0
        assert metrics.false_positives == 1
        assert metrics.true_negatives == 0
        assert metrics.false_negatives == 0
    
    def test_incorporate_feedback_false_negative(self, pattern_learning_engine, sample_learning_feedback):
        """Test incorporating feedback for false negative case."""
        # Modify feedback to be a false negative
        feedback = sample_learning_feedback
        feedback.actual_outcome = "fraud"
        feedback.predicted_decision = FraudDecision.APPROVED
        
        # Incorporate feedback
        success = pattern_learning_engine.incorporate_feedback(feedback)
        assert success is True
        
        # Check that metrics were updated
        pattern_id = feedback.pattern_ids_triggered[0]
        metrics = pattern_learning_engine.pattern_metrics[pattern_id]
        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 0
        assert metrics.false_negatives == 1
    
    def test_incorporate_feedback_true_negative(self, pattern_learning_engine, sample_learning_feedback):
        """Test incorporating feedback for true negative case."""
        # Modify feedback to be a true negative
        feedback = sample_learning_feedback
        feedback.actual_outcome = "legitimate"
        feedback.predicted_decision = FraudDecision.APPROVED
        
        # Incorporate feedback
        success = pattern_learning_engine.incorporate_feedback(feedback)
        assert success is True
        
        # Check that metrics were updated
        pattern_id = feedback.pattern_ids_triggered[0]
        metrics = pattern_learning_engine.pattern_metrics[pattern_id]
        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.true_negatives == 1
        assert metrics.false_negatives == 0
    
    def test_pattern_update_after_threshold_feedback(self, pattern_learning_engine, mock_memory_manager, sample_fraud_pattern):
        """Test that patterns are updated after reaching feedback threshold."""
        # Set up mock to return the sample pattern
        mock_memory_manager.get_all_fraud_patterns.return_value = [sample_fraud_pattern]
        mock_memory_manager.store_fraud_pattern.return_value = True
        
        # Set a low threshold for testing
        pattern_learning_engine.pattern_update_threshold = 2
        
        pattern_id = sample_fraud_pattern.pattern_id
        
        # Add feedback to reach threshold
        for i in range(2):
            feedback = LearningFeedback(
                transaction_id=f"tx_{i}",
                actual_outcome="fraud",
                predicted_decision=FraudDecision.DECLINED,
                confidence_score=0.9,
                pattern_ids_triggered=[pattern_id],
                timestamp=datetime.now(),
                feedback_source="manual_review"
            )
            pattern_learning_engine.incorporate_feedback(feedback)
        
        # Verify that store_fraud_pattern was called (pattern was updated)
        assert mock_memory_manager.store_fraud_pattern.called
    
    def test_evaluate_pattern_performance(self, pattern_learning_engine, mock_memory_manager, sample_fraud_pattern):
        """Test pattern performance evaluation."""
        # Set up mock to return sample pattern
        mock_memory_manager.get_all_fraud_patterns.return_value = [sample_fraud_pattern]
        
        # Add some metrics for the pattern
        pattern_id = sample_fraud_pattern.pattern_id
        pattern_learning_engine.pattern_metrics[pattern_id] = PatternMetrics(
            true_positives=8, false_positives=2, true_negatives=15, false_negatives=1
        )
        
        # Evaluate performance
        performance_report = pattern_learning_engine.evaluate_pattern_performance()
        
        # Check that report contains expected data
        assert pattern_id in performance_report
        metrics = performance_report[pattern_id]
        
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "accuracy" in metrics
        assert "false_positive_rate" in metrics
        assert "effectiveness_score" in metrics
        assert "detection_count" in metrics
        assert "confidence_threshold" in metrics
        
        # Verify calculated values
        assert metrics["precision"] == 0.8
        assert abs(metrics["recall"] - 0.8889) < 0.001
    
    def test_get_learning_recommendations(self, pattern_learning_engine, mock_memory_manager, sample_fraud_pattern):
        """Test generation of learning recommendations."""
        # Set up mock to return sample pattern
        mock_memory_manager.get_all_fraud_patterns.return_value = [sample_fraud_pattern]
        
        # Add metrics with low precision (high false positive rate)
        pattern_id = sample_fraud_pattern.pattern_id
        pattern_learning_engine.pattern_metrics[pattern_id] = PatternMetrics(
            true_positives=3, false_positives=7, true_negatives=10, false_negatives=1
        )
        
        # Get recommendations
        recommendations = pattern_learning_engine.get_learning_recommendations()
        
        # Should have recommendations for low precision
        assert len(recommendations) > 0
        
        # Check for increase threshold recommendation
        increase_threshold_recs = [r for r in recommendations if r["type"] == "increase_threshold"]
        assert len(increase_threshold_recs) > 0
        
        rec = increase_threshold_recs[0]
        assert rec["pattern_id"] == pattern_id
        assert "precision" in rec["reason"]
        assert rec["priority"] in ["high", "medium", "low"]
    
    def test_optimize_pattern_thresholds(self, pattern_learning_engine, mock_memory_manager, sample_fraud_pattern):
        """Test pattern threshold optimization."""
        # Set up mock to return sample pattern
        mock_memory_manager.get_all_fraud_patterns.return_value = [sample_fraud_pattern]
        
        # Set low threshold for testing
        pattern_learning_engine.pattern_update_threshold = 2
        
        # Add sufficient metrics for optimization
        pattern_id = sample_fraud_pattern.pattern_id
        pattern_learning_engine.pattern_metrics[pattern_id] = PatternMetrics(
            true_positives=8, false_positives=2, true_negatives=15, false_negatives=1
        )
        
        # Optimize thresholds
        optimized_thresholds = pattern_learning_engine.optimize_pattern_thresholds()
        
        # Should return optimized thresholds (may be empty if no improvement found)
        assert isinstance(optimized_thresholds, dict)
        
        # If optimization found improvements, check threshold is valid
        if pattern_id in optimized_thresholds:
            threshold = optimized_thresholds[pattern_id]
            assert 0.1 <= threshold <= 0.95
    
    def test_simulate_threshold_performance(self, pattern_learning_engine):
        """Test threshold performance simulation."""
        # Add some metrics for simulation
        pattern_id = "test_pattern"
        pattern_learning_engine.pattern_metrics[pattern_id] = PatternMetrics(
            true_positives=8, false_positives=2, true_negatives=15, false_negatives=1
        )
        
        # Simulate different thresholds
        f1_low = pattern_learning_engine._simulate_threshold_performance(pattern_id, 0.5)
        f1_high = pattern_learning_engine._simulate_threshold_performance(pattern_id, 0.9)
        
        # Both should return valid F1 scores
        assert 0 <= f1_low <= 1
        assert 0 <= f1_high <= 1
    
    def test_multiple_pattern_feedback(self, pattern_learning_engine):
        """Test feedback incorporation for multiple patterns."""
        # Create feedback that triggers multiple patterns
        feedback = LearningFeedback(
            transaction_id="tx_multi",
            actual_outcome="fraud",
            predicted_decision=FraudDecision.DECLINED,
            confidence_score=0.9,
            pattern_ids_triggered=["pattern_1", "pattern_2", "pattern_3"],
            timestamp=datetime.now(),
            feedback_source="manual_review"
        )
        
        # Incorporate feedback
        success = pattern_learning_engine.incorporate_feedback(feedback)
        assert success is True
        
        # Check that all patterns have updated metrics
        for pattern_id in feedback.pattern_ids_triggered:
            assert pattern_id in pattern_learning_engine.pattern_metrics
            metrics = pattern_learning_engine.pattern_metrics[pattern_id]
            assert metrics.true_positives == 1
    
    def test_error_handling_in_feedback(self, pattern_learning_engine):
        """Test error handling during feedback incorporation."""
        # Create invalid feedback
        invalid_feedback = LearningFeedback(
            transaction_id="",  # Empty transaction ID
            actual_outcome="invalid_outcome",  # Invalid outcome
            predicted_decision=FraudDecision.APPROVED,
            confidence_score=1.5,  # Invalid confidence score
            pattern_ids_triggered=[],  # Empty pattern list
            timestamp=datetime.now(),
            feedback_source=""
        )
        
        # Should handle gracefully
        success = pattern_learning_engine.incorporate_feedback(invalid_feedback)
        # Should still return True as it handles empty pattern list gracefully
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__])