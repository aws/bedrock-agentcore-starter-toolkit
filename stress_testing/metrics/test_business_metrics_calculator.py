"""
Tests for BusinessMetricsCalculator.

This module tests all business metrics calculation functionality including:
- Fraud detection rate and accuracy
- Cost per transaction from AWS billing data
- ROI metrics and money saved
- Competitive benchmark comparisons
"""

import pytest
from datetime import datetime

from src.metrics.business_metrics_calculator import (
    BusinessMetricsCalculator,
    FraudDetectionStats,
    CostBreakdown
)
from src.models import SystemMetrics


class TestBusinessMetricsCalculator:
    """Test suite for BusinessMetricsCalculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = BusinessMetricsCalculator()
    
    def test_initialization(self):
        """Test calculator initialization with default pricing."""
        assert self.calculator is not None
        assert self.calculator.pricing is not None
        assert self.calculator.baseline is not None
        assert self.calculator.avg_fraud_amount == 300.0
        assert self.calculator.fraud_rate == 0.02
        assert self.calculator.detection_accuracy == 0.95
    
    def test_initialization_with_custom_pricing(self):
        """Test calculator initialization with custom pricing."""
        custom_pricing = {
            'lambda_per_request': 0.0000003,
            'dynamodb_write_per_million': 2.0
        }
        calculator = BusinessMetricsCalculator(pricing=custom_pricing)
        
        assert calculator.pricing['lambda_per_request'] == 0.0000003
        assert calculator.pricing['dynamodb_write_per_million'] == 2.0
        # Other defaults should still be present
        assert 'kinesis_per_shard_hour' in calculator.pricing
    
    def test_calculate_fraud_detection_metrics_basic(self):
        """Test basic fraud detection metrics calculation."""
        metrics = self.calculator.calculate_fraud_detection_metrics(
            total_transactions=10000,
            fraud_detected=190
        )
        
        assert 'fraud_detection_rate' in metrics
        assert 'fraud_detection_accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'false_positive_rate' in metrics
        assert 'false_negative_rate' in metrics
        
        # Check reasonable values
        assert 0 <= metrics['fraud_detection_accuracy'] <= 1
        assert 0 <= metrics['precision'] <= 1
        assert 0 <= metrics['recall'] <= 1
        assert 0 <= metrics['f1_score'] <= 1
    
    def test_calculate_fraud_detection_metrics_with_confusion_matrix(self):
        """Test fraud detection metrics with explicit confusion matrix."""
        metrics = self.calculator.calculate_fraud_detection_metrics(
            total_transactions=10000,
            fraud_detected=200,
            true_positives=190,
            false_positives=10,
            false_negatives=10
        )
        
        assert metrics['true_positives'] == 190
        assert metrics['false_positives'] == 10
        assert metrics['false_negatives'] == 10
        
        # Verify accuracy calculation
        true_negatives = metrics['true_negatives']
        accuracy = (190 + true_negatives) / 10000
        assert abs(metrics['fraud_detection_accuracy'] - accuracy) < 0.001
    
    def test_calculate_fraud_detection_metrics_perfect_accuracy(self):
        """Test fraud detection with perfect accuracy."""
        metrics = self.calculator.calculate_fraud_detection_metrics(
            total_transactions=10000,
            fraud_detected=200,
            true_positives=200,
            false_positives=0,
            false_negatives=0
        )
        
        assert metrics['precision'] == 1.0
        assert metrics['recall'] == 1.0
        assert metrics['f1_score'] == 1.0
        assert metrics['false_positive_rate'] == 0.0
        assert metrics['false_negative_rate'] == 0.0
    
    def test_calculate_cost_metrics_with_estimates(self):
        """Test cost calculation with estimated AWS usage."""
        cost_breakdown = self.calculator.calculate_cost_metrics(
            total_transactions=10000,
            duration_hours=1.0
        )
        
        assert isinstance(cost_breakdown, CostBreakdown)
        assert cost_breakdown.lambda_cost > 0
        assert cost_breakdown.dynamodb_cost > 0
        assert cost_breakdown.kinesis_cost > 0
        assert cost_breakdown.bedrock_cost > 0
        assert cost_breakdown.s3_cost > 0
        assert cost_breakdown.cloudwatch_cost > 0
        assert cost_breakdown.total_cost > 0
        
        # Verify total cost is sum of components
        expected_total = (
            cost_breakdown.lambda_cost +
            cost_breakdown.dynamodb_cost +
            cost_breakdown.kinesis_cost +
            cost_breakdown.bedrock_cost +
            cost_breakdown.s3_cost +
            cost_breakdown.cloudwatch_cost +
            cost_breakdown.other_costs
        )
        assert abs(cost_breakdown.total_cost - expected_total) < 0.01
    
    def test_calculate_cost_metrics_with_explicit_usage(self):
        """Test cost calculation with explicit AWS usage data."""
        cost_breakdown = self.calculator.calculate_cost_metrics(
            total_transactions=10000,
            duration_hours=1.0,
            lambda_invocations=50000,
            lambda_gb_seconds=10000.0,
            dynamodb_writes=30000,
            dynamodb_reads=50000,
            kinesis_shards=2,
            kinesis_puts=10000,
            bedrock_input_tokens=5000000,
            bedrock_output_tokens=2000000,
            s3_puts=10000,
            custom_metrics=50
        )
        
        assert cost_breakdown.lambda_cost > 0
        assert cost_breakdown.dynamodb_cost > 0
        assert cost_breakdown.kinesis_cost > 0
        assert cost_breakdown.bedrock_cost > 0
        
        # Bedrock should be significant cost component
        assert cost_breakdown.bedrock_cost > cost_breakdown.s3_cost
    
    def test_calculate_cost_metrics_scaling(self):
        """Test that costs scale appropriately with transaction volume."""
        cost_1k = self.calculator.calculate_cost_metrics(
            total_transactions=1000,
            duration_hours=1.0
        )
        
        cost_10k = self.calculator.calculate_cost_metrics(
            total_transactions=10000,
            duration_hours=1.0
        )
        
        # Cost should increase with transactions, but not necessarily linearly
        # due to fixed costs (Kinesis shards, CloudWatch metrics, etc.)
        ratio = cost_10k.total_cost / cost_1k.total_cost
        assert ratio > 2  # Should at least double
        assert cost_10k.total_cost > cost_1k.total_cost  # Should increase
    
    def test_calculate_roi_metrics_basic(self):
        """Test basic ROI metrics calculation."""
        roi_metrics = self.calculator.calculate_roi_metrics(
            total_transactions=10000,
            fraud_detected=190,
            total_cost=250.0
        )
        
        assert 'fraud_prevented_amount' in roi_metrics
        assert 'money_saved' in roi_metrics
        assert 'roi_percentage' in roi_metrics
        assert 'payback_period_months' in roi_metrics
        assert 'cost_per_transaction' in roi_metrics
        
        # Verify fraud prevented calculation
        expected_fraud_prevented = 190 * 300.0  # 190 fraud * $300 avg
        assert roi_metrics['fraud_prevented_amount'] == expected_fraud_prevented
        
        # Verify cost per transaction
        assert abs(roi_metrics['cost_per_transaction'] - 0.025) < 0.001
    
    def test_calculate_roi_metrics_positive_roi(self):
        """Test ROI calculation with positive returns."""
        roi_metrics = self.calculator.calculate_roi_metrics(
            total_transactions=100000,
            fraud_detected=1900,  # 2% fraud rate, 95% detected
            total_cost=2500.0,
            implementation_cost=50000.0
        )
        
        # Should have positive ROI
        assert roi_metrics['money_saved'] > 0
        assert roi_metrics['roi_percentage'] > 0
        
        # Fraud prevented should exceed costs
        assert roi_metrics['fraud_prevented_amount'] > roi_metrics['total_cost']
    
    def test_calculate_roi_metrics_payback_period(self):
        """Test payback period calculation."""
        roi_metrics = self.calculator.calculate_roi_metrics(
            total_transactions=100000,
            fraud_detected=1900,
            total_cost=2500.0,
            implementation_cost=50000.0
        )
        
        # Payback period should be reasonable (< 24 months for good ROI)
        assert roi_metrics['payback_period_months'] > 0
        assert roi_metrics['payback_period_months'] < 24
    
    def test_generate_competitive_benchmarks_superior_performance(self):
        """Test competitive benchmarks with superior performance."""
        benchmarks = self.calculator.generate_competitive_benchmarks(
            fraud_detection_accuracy=0.95,
            false_positive_rate=0.02,
            cost_per_transaction=0.025,
            avg_response_time_ms=250,
            uptime_percentage=99.97
        )
        
        assert benchmarks.our_performance is not None
        assert benchmarks.competitor_avg is not None
        assert benchmarks.improvement_percentage is not None
        assert len(benchmarks.unique_advantages) > 0
        
        # Should show improvements
        assert benchmarks.improvement_percentage['fraud_detection_accuracy'] > 0
        assert benchmarks.improvement_percentage['cost_per_transaction'] > 0
        assert benchmarks.improvement_percentage['avg_response_time_ms'] > 0
        
        # Should be market leader
        assert benchmarks.market_position in ['leader', 'challenger']
    
    def test_generate_competitive_benchmarks_custom_baseline(self):
        """Test competitive benchmarks with custom baseline."""
        custom_baseline = {
            'fraud_detection_accuracy': 0.90,
            'false_positive_rate': 0.08,
            'cost_per_transaction': 0.04,
            'avg_response_time_ms': 400,
            'uptime_percentage': 99.0,
        }
        
        benchmarks = self.calculator.generate_competitive_benchmarks(
            fraud_detection_accuracy=0.95,
            false_positive_rate=0.02,
            cost_per_transaction=0.025,
            avg_response_time_ms=250,
            uptime_percentage=99.97,
            custom_baseline=custom_baseline
        )
        
        # Should show significant improvements vs custom baseline
        assert benchmarks.improvement_percentage['fraud_detection_accuracy'] > 5
        assert benchmarks.improvement_percentage['cost_per_transaction'] > 30
    
    def test_generate_competitive_benchmarks_unique_advantages(self):
        """Test that unique advantages are identified."""
        benchmarks = self.calculator.generate_competitive_benchmarks(
            fraud_detection_accuracy=0.95,
            false_positive_rate=0.02,
            cost_per_transaction=0.025,
            avg_response_time_ms=250,
            uptime_percentage=99.97
        )
        
        # Should always include core unique features
        advantages_text = ' '.join(benchmarks.unique_advantages)
        assert 'Explainable AI' in advantages_text or 'explainable' in advantages_text.lower()
        assert 'Multi-agent' in advantages_text or 'multi-agent' in advantages_text.lower()
    
    def test_calculate_business_metrics_comprehensive(self):
        """Test comprehensive business metrics calculation."""
        cost_breakdown = CostBreakdown(
            lambda_cost=50.0,
            dynamodb_cost=30.0,
            kinesis_cost=20.0,
            bedrock_cost=100.0,
            s3_cost=5.0,
            cloudwatch_cost=10.0,
            other_costs=25.0
        )
        
        system_metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            throughput_tps=100.0,
            requests_total=10000,
            requests_successful=9950,
            requests_failed=50,
            avg_response_time_ms=250.0,
            p50_response_time_ms=200.0,
            p95_response_time_ms=400.0,
            p99_response_time_ms=600.0,
            max_response_time_ms=1000.0,
            error_rate=0.005,
            timeout_rate=0.001,
            cpu_utilization=0.65,
            memory_utilization=0.70,
            network_throughput_mbps=50.0
        )
        
        business_metrics = self.calculator.calculate_business_metrics(
            total_transactions=10000,
            fraud_detected=190,
            cost_breakdown=cost_breakdown,
            duration_hours=1.0,
            system_metrics=system_metrics
        )
        
        assert business_metrics.transactions_processed == 10000
        assert business_metrics.fraud_detected == 190
        assert business_metrics.total_cost == cost_breakdown.total_cost
        assert business_metrics.fraud_detection_accuracy > 0
        assert business_metrics.roi_percentage > 0
        assert business_metrics.money_saved > 0
        assert business_metrics.customer_impact_score > 0
        assert len(business_metrics.aws_cost_breakdown) > 0
    
    def test_calculate_business_metrics_with_confusion_matrix(self):
        """Test business metrics with explicit confusion matrix."""
        cost_breakdown = CostBreakdown(
            lambda_cost=50.0,
            dynamodb_cost=30.0,
            kinesis_cost=20.0,
            bedrock_cost=100.0,
            s3_cost=5.0,
            cloudwatch_cost=10.0,
            other_costs=25.0
        )
        
        business_metrics = self.calculator.calculate_business_metrics(
            total_transactions=10000,
            fraud_detected=200,
            cost_breakdown=cost_breakdown,
            duration_hours=1.0,
            true_positives=190,
            false_positives=10,
            false_negatives=10
        )
        
        # Should use provided confusion matrix
        assert business_metrics.fraud_detection_accuracy > 0.95
        assert business_metrics.false_positive_impact < 0.05
    
    def test_calculate_business_metrics_aws_cost_breakdown(self):
        """Test that AWS cost breakdown is properly included."""
        cost_breakdown = CostBreakdown(
            lambda_cost=50.0,
            dynamodb_cost=30.0,
            kinesis_cost=20.0,
            bedrock_cost=100.0,
            s3_cost=5.0,
            cloudwatch_cost=10.0,
            other_costs=25.0
        )
        
        business_metrics = self.calculator.calculate_business_metrics(
            total_transactions=10000,
            fraud_detected=190,
            cost_breakdown=cost_breakdown,
            duration_hours=1.0
        )
        
        assert 'lambda' in business_metrics.aws_cost_breakdown
        assert 'dynamodb' in business_metrics.aws_cost_breakdown
        assert 'kinesis' in business_metrics.aws_cost_breakdown
        assert 'bedrock' in business_metrics.aws_cost_breakdown
        
        assert business_metrics.aws_cost_breakdown['lambda'] == 50.0
        assert business_metrics.aws_cost_breakdown['bedrock'] == 100.0
    
    def test_zero_transactions_handling(self):
        """Test handling of zero transactions edge case."""
        metrics = self.calculator.calculate_fraud_detection_metrics(
            total_transactions=0,
            fraud_detected=0
        )
        
        assert metrics['fraud_detection_rate'] == 0
        assert metrics['fraud_detection_accuracy'] == 0
    
    def test_high_volume_transactions(self):
        """Test with high volume of transactions."""
        cost_breakdown = self.calculator.calculate_cost_metrics(
            total_transactions=1000000,  # 1 million transactions
            duration_hours=10.0
        )
        
        assert cost_breakdown.total_cost > 0
        
        # Cost per transaction should be reasonable even at scale
        cost_per_txn = cost_breakdown.total_cost / 1000000
        assert cost_per_txn < 0.10  # Should be less than $0.10 per transaction


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
