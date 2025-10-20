"""
Integration test for BusinessMetricsCalculator with MetricsCollector.

This test verifies that the BusinessMetricsCalculator is properly integrated
into the MetricsCollector and works correctly in the stress testing context.
"""

import asyncio
import pytest

from src.metrics import MetricsCollector, BusinessMetricsCalculator


@pytest.mark.asyncio
async def test_metrics_collector_has_business_calculator():
    """Test that MetricsCollector has BusinessMetricsCalculator instance."""
    collector = MetricsCollector()
    
    assert hasattr(collector, 'business_calculator')
    assert isinstance(collector.business_calculator, BusinessMetricsCalculator)


@pytest.mark.asyncio
async def test_collect_business_metrics_integration():
    """Test that collect_business_metrics uses BusinessMetricsCalculator."""
    collector = MetricsCollector()
    
    # Simulate some transactions
    collector.total_transactions = 10000
    collector.total_fraud_detected = 190
    
    # Collect business metrics
    business_metrics = await collector.collect_business_metrics()
    
    # Verify metrics are calculated
    assert business_metrics is not None
    assert business_metrics.transactions_processed == 10000
    assert business_metrics.fraud_detected == 190
    assert business_metrics.fraud_detection_accuracy > 0
    assert business_metrics.cost_per_transaction > 0
    assert business_metrics.roi_percentage != 0
    assert len(business_metrics.aws_cost_breakdown) > 0


@pytest.mark.asyncio
async def test_get_competitive_benchmarks_integration():
    """Test that get_competitive_benchmarks works correctly."""
    collector = MetricsCollector()
    
    # Simulate some transactions
    collector.total_transactions = 10000
    collector.total_fraud_detected = 190
    
    # Get competitive benchmarks
    benchmarks = await collector.get_competitive_benchmarks()
    
    # Verify benchmarks are generated
    assert benchmarks is not None
    assert 'our_performance' in benchmarks
    assert 'competitor_avg' in benchmarks
    assert 'improvement_percentage' in benchmarks
    assert 'unique_advantages' in benchmarks
    assert 'market_position' in benchmarks
    
    # Verify structure
    assert isinstance(benchmarks['our_performance'], dict)
    assert isinstance(benchmarks['competitor_avg'], dict)
    assert isinstance(benchmarks['improvement_percentage'], dict)
    assert isinstance(benchmarks['unique_advantages'], list)
    assert len(benchmarks['unique_advantages']) > 0


@pytest.mark.asyncio
async def test_business_metrics_with_load_generator():
    """Test business metrics calculation with simulated load generator."""
from src.load_generator.load_generator import LoadGenerator
    
    collector = MetricsCollector()
    
    # Create and set load generator
    load_generator = LoadGenerator(target_tps=100, num_workers=2)
    collector.set_load_generator(load_generator)
    
    # Simulate some load
    load_generator.total_sent = 5000
    load_generator.current_tps = 100
    
    # Collect metrics
    business_metrics = await collector.collect_business_metrics()
    
    # Verify metrics reflect load generator data
    assert business_metrics.transactions_processed == 5000
    assert business_metrics.transactions_per_second == 100


@pytest.mark.asyncio
async def test_statistics_includes_business_calculator():
    """Test that statistics include business calculator info."""
    collector = MetricsCollector()
    
    stats = collector.get_statistics()
    
    assert stats is not None
    assert 'total_transactions' in stats
    assert 'total_fraud_detected' in stats
    assert 'total_cost' in stats
    assert 'test_duration_hours' in stats


@pytest.mark.asyncio
async def test_end_to_end_business_metrics_flow():
    """Test complete end-to-end flow of business metrics calculation."""
    collector = MetricsCollector()
    
    # Simulate a stress test scenario
    collector.total_transactions = 50000
    collector.total_fraud_detected = 950
    
    # Collect all metrics
    all_metrics = await collector.collect_all_metrics()
    
    # Verify all metrics are present
    assert 'system' in all_metrics
    assert 'agents' in all_metrics
    assert 'business' in all_metrics
    
    # Verify business metrics
    business = all_metrics['business']
    assert business.transactions_processed == 50000
    assert business.fraud_detected == 950
    assert business.fraud_detection_accuracy > 0
    assert business.cost_per_transaction > 0
    assert business.total_cost > 0
    assert business.roi_percentage != 0
    assert business.money_saved != 0
    
    # Get competitive benchmarks
    benchmarks = await collector.get_competitive_benchmarks()
    assert benchmarks['market_position'] in ['leader', 'challenger', 'follower']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
