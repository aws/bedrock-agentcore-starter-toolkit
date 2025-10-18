"""
Tests for Competitive Benchmark Calculator.
"""

import pytest
from datetime import datetime

from .competitive_benchmark_calculator import (
    CompetitiveBenchmarkCalculator,
    CompetitorType,
    BenchmarkCategory,
    CompetitorProfile,
    BenchmarkComparison
)
from ..models import CompetitiveBenchmarks


class TestCompetitiveBenchmarkCalculator:
    """Test suite for CompetitiveBenchmarkCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return CompetitiveBenchmarkCalculator()
    
    @pytest.fixture
    def our_metrics(self):
        """Sample metrics for our system."""
        return {
            'fraud_detection_accuracy': 0.95,
            'false_positive_rate': 0.05,
            'cost_per_transaction': 0.02,
            'avg_response_time_ms': 200,
            'uptime_percentage': 99.9,
            'max_tps': 5000
        }
    
    def test_calculator_initialization(self, calculator):
        """Test calculator initializes with default competitors."""
        assert len(calculator.competitors) == 4
        assert CompetitorType.INDUSTRY_AVERAGE in calculator.competitors
        assert CompetitorType.TRADITIONAL_RULES in calculator.competitors
    
    def test_calculate_improvement_percentage_higher_is_better(self, calculator):
        """Test improvement calculation for metrics where higher is better."""
        # Our accuracy is 95%, competitor is 85%
        improvement = calculator.calculate_improvement_percentage(
            our_value=0.95,
            competitor_value=0.85,
            higher_is_better=True
        )
        
        # Should be approximately 11.76% improvement
        assert improvement > 11
        assert improvement < 12
    
    def test_calculate_improvement_percentage_lower_is_better(self, calculator):
        """Test improvement calculation for metrics where lower is better."""
        # Our cost is $0.02, competitor is $0.05
        improvement = calculator.calculate_improvement_percentage(
            our_value=0.02,
            competitor_value=0.05,
            higher_is_better=False
        )
        
        # Should be 60% improvement (we're 60% cheaper)
        assert improvement == 60.0

    
    def test_compare_against_competitor(self, calculator, our_metrics):
        """Test comparison against a specific competitor."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        # Should have 6 comparisons (accuracy, FPR, cost, latency, uptime, TPS)
        assert len(comparisons) == 6
        
        # All comparisons should be BenchmarkComparison objects
        for comp in comparisons:
            assert isinstance(comp, BenchmarkComparison)
            assert comp.metric_name
            assert comp.category in BenchmarkCategory
    
    def test_compare_accuracy_improvement(self, calculator, our_metrics):
        """Test accuracy comparison shows improvement."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        # Find accuracy comparison
        accuracy_comp = next(
            c for c in comparisons 
            if c.metric_name == "Fraud Detection Accuracy"
        )
        
        # Our accuracy (95%) should be better than industry average (85%)
        assert accuracy_comp.is_better
        assert accuracy_comp.improvement_percentage > 10
        assert accuracy_comp.category == BenchmarkCategory.ACCURACY
    
    def test_compare_cost_improvement(self, calculator, our_metrics):
        """Test cost comparison shows improvement."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        # Find cost comparison
        cost_comp = next(
            c for c in comparisons 
            if c.metric_name == "Cost per Transaction"
        )
        
        # Our cost ($0.02) should be better than industry average ($0.05)
        assert cost_comp.is_better
        assert cost_comp.improvement_percentage > 50  # 60% cheaper
        assert cost_comp.category == BenchmarkCategory.COST
    
    def test_generate_unique_advantages(self, calculator, our_metrics):
        """Test unique advantages generation."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        advantages = calculator.generate_unique_advantages(comparisons)
        
        # Should have multiple advantages
        assert len(advantages) > 0
        
        # Should include feature-based advantages
        assert any("multi-agent" in adv.lower() for adv in advantages)
    
    def test_calculate_market_position_leader(self, calculator, our_metrics):
        """Test market position calculation for strong performance."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        position, score = calculator.calculate_market_position(comparisons)
        
        # With superior metrics, should be market leader or strong challenger
        assert position in ["market_leader", "strong_challenger"]
        assert score > 1.0

    
    def test_generate_competitive_benchmarks(self, calculator, our_metrics):
        """Test complete competitive benchmarks generation."""
        benchmarks = calculator.generate_competitive_benchmarks(
            **our_metrics,
            competitor_type=CompetitorType.INDUSTRY_AVERAGE
        )
        
        # Should return CompetitiveBenchmarks object
        assert isinstance(benchmarks, CompetitiveBenchmarks)
        
        # Should have all required fields
        assert benchmarks.our_performance
        assert benchmarks.competitor_avg
        assert benchmarks.improvement_percentage
        assert benchmarks.unique_advantages
        assert benchmarks.market_position
        
        # Performance dictionaries should have expected keys
        assert 'fraud_detection_accuracy' in benchmarks.our_performance
        assert 'cost_per_transaction' in benchmarks.our_performance
        
        # Should have improvement percentages
        assert len(benchmarks.improvement_percentage) > 0
        
        # Should have unique advantages
        assert len(benchmarks.unique_advantages) > 0
    
    def test_compare_against_all_competitors(self, calculator, our_metrics):
        """Test comparison against all competitor types."""
        all_comparisons = calculator.compare_against_all_competitors(**our_metrics)
        
        # Should have comparisons for all competitor types
        assert len(all_comparisons) == 4
        
        # Each competitor should have comparisons
        for competitor_type, comparisons in all_comparisons.items():
            assert len(comparisons) == 6  # 6 metrics compared
            assert all(isinstance(c, BenchmarkComparison) for c in comparisons)
    
    def test_get_category_summary(self, calculator, our_metrics):
        """Test category summary generation."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        summary = calculator.get_category_summary(comparisons)
        
        # Should have summaries for multiple categories
        assert len(summary) > 0
        
        # Each category should have expected fields
        for category, stats in summary.items():
            assert 'count' in stats
            assert 'wins' in stats
            assert 'win_rate' in stats
            assert 'avg_improvement' in stats
    
    def test_format_comparison_report(self, calculator, our_metrics):
        """Test comparison report formatting."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **our_metrics
        )
        
        report = calculator.format_comparison_report(
            comparisons,
            competitor_name="Industry Average"
        )
        
        # Report should be a non-empty string
        assert isinstance(report, str)
        assert len(report) > 0
        
        # Should contain key information
        assert "Industry Average" in report
        assert "ACCURACY" in report or "COST" in report
    
    def test_custom_competitor_profile(self):
        """Test adding custom competitor profile."""
        custom_competitor = CompetitorProfile(
            name="Custom Competitor",
            competitor_type=CompetitorType.MODERN_AI,
            fraud_detection_accuracy=0.90,
            false_positive_rate=0.07,
            cost_per_transaction=0.03,
            avg_response_time_ms=300,
            uptime_percentage=99.8,
            max_tps=4000,
            features=["Custom feature"]
        )
        
        calculator = CompetitiveBenchmarkCalculator(
            custom_competitors={"custom": custom_competitor}
        )
        
        # Should have default + custom competitors
        assert len(calculator.competitors) == 5
        assert "custom" in calculator.competitors
    
    def test_comparison_against_traditional_rules(self, calculator, our_metrics):
        """Test comparison shows significant improvement vs traditional systems."""
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.TRADITIONAL_RULES,
            **our_metrics
        )
        
        # Should show significant improvements across all metrics
        accuracy_comp = next(c for c in comparisons if "Accuracy" in c.metric_name)
        assert accuracy_comp.improvement_percentage > 20  # Much better than 75%
        
        cost_comp = next(c for c in comparisons if "Cost" in c.metric_name)
        assert cost_comp.improvement_percentage > 70  # Much cheaper than $0.08
    
    def test_market_position_with_poor_metrics(self, calculator):
        """Test market position with below-average metrics."""
        poor_metrics = {
            'fraud_detection_accuracy': 0.70,
            'false_positive_rate': 0.20,
            'cost_per_transaction': 0.10,
            'avg_response_time_ms': 1000,
            'uptime_percentage': 98.0,
            'max_tps': 500
        }
        
        comparisons = calculator.compare_against_competitor(
            competitor_type=CompetitorType.INDUSTRY_AVERAGE,
            **poor_metrics
        )
        
        position, score = calculator.calculate_market_position(comparisons)
        
        # With poor metrics, should not be market leader
        assert position != "market_leader"
        assert score < 1.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
