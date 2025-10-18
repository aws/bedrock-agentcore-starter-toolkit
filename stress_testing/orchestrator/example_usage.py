"""
Example usage of the Stress Test Orchestrator components.

This script demonstrates how to use the orchestrator, metrics aggregator,
and test results store together.
"""

import asyncio
import logging
from datetime import datetime

from ..models import SystemMetrics, AgentMetrics, BusinessMetrics, TestStatus
from ..config import ScenarioBuilder
from .stress_test_orchestrator import StressTestOrchestrator
from .metrics_aggregator import MetricsAggregator
from .test_results_store import TestResultsStore


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_metric_source():
    """Example metric source that generates dummy metrics."""
    return {
        'system': SystemMetrics(
            timestamp=datetime.utcnow(),
            throughput_tps=1000.0,
            requests_total=10000,
            requests_successful=9950,
            requests_failed=50,
            avg_response_time_ms=150.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=250.0,
            p99_response_time_ms=400.0,
            max_response_time_ms=800.0,
            error_rate=0.005,
            timeout_rate=0.001,
            cpu_utilization=0.65,
            memory_utilization=0.55,
            network_throughput_mbps=100.0
        ),
        'agents': [
            AgentMetrics(
                agent_id="agent_1",
                agent_name="Transaction Analyzer",
                timestamp=datetime.utcnow(),
                requests_processed=2500,
                avg_response_time_ms=140.0,
                p95_response_time_ms=230.0,
                p99_response_time_ms=380.0,
                success_rate=0.995,
                error_count=12,
                timeout_count=3,
                current_load=0.62,
                concurrent_requests=15,
                health_score=0.98,
                status="healthy"
            )
        ],
        'business': BusinessMetrics(
            timestamp=datetime.utcnow(),
            transactions_processed=10000,
            transactions_per_second=1000.0,
            fraud_detected=150,
            fraud_prevented_amount=45000.0,
            fraud_detection_rate=0.015,
            fraud_detection_accuracy=0.94,
            cost_per_transaction=0.025,
            total_cost=250.0,
            roi_percentage=180.0,
            money_saved=45000.0,
            payback_period_months=6.0,
            customer_impact_score=0.92,
            false_positive_impact=0.05,
            performance_vs_baseline=1.5,
            cost_vs_baseline=0.6
        )
    }


async def metrics_subscriber(metrics):
    """Example subscriber that receives real-time metrics."""
    logger.info(f"Received metrics update: TPS={metrics.current_tps:.2f}, Status={metrics.test_status.value}")


async def main():
    """Main example demonstrating orchestrator usage."""
    
    logger.info("=== Stress Test Orchestrator Example ===")
    
    # 1. Create components
    logger.info("\n1. Creating components...")
    orchestrator = StressTestOrchestrator()
    metrics_aggregator = MetricsAggregator(buffer_size=100, aggregation_interval_seconds=1.0)
    results_store = TestResultsStore()
    
    # 2. Set up metrics aggregator
    logger.info("\n2. Setting up metrics aggregator...")
    metrics_aggregator.register_metric_source("example_source", example_metric_source)
    metrics_aggregator.subscribe(metrics_subscriber)
    
    # 3. Load a test scenario
    logger.info("\n3. Loading test scenario...")
    scenario = ScenarioBuilder.create_peak_load_scenario()
    orchestrator.load_scenario(scenario)
    
    # 4. Register lifecycle callbacks
    logger.info("\n4. Registering lifecycle callbacks...")
    
    async def on_start_callback(test_id, scenario):
        logger.info(f"✓ Test started: {test_id}")
    
    async def on_complete_callback(test_id, success, results):
        logger.info(f"✓ Test completed: {test_id}, Success: {success}")
    
    orchestrator.register_lifecycle_callback('on_start', on_start_callback)
    orchestrator.register_lifecycle_callback('on_complete', on_complete_callback)
    
    # 5. Start the test
    logger.info("\n5. Starting test...")
    success = await orchestrator.start_test()
    
    if not success:
        logger.error("Failed to start test")
        return
    
    # 6. Start metrics collection
    logger.info("\n6. Starting metrics collection...")
    await metrics_aggregator.start_collection()
    
    # 7. Simulate test execution for a few seconds
    logger.info("\n7. Simulating test execution (5 seconds)...")
    await asyncio.sleep(5)
    
    # 8. Get current status
    logger.info("\n8. Getting current status...")
    status = orchestrator.get_current_status()
    logger.info(f"Current status: {status}")
    
    # 9. Get aggregated metrics
    logger.info("\n9. Getting aggregated metrics...")
    aggregated = metrics_aggregator.calculate_aggregated_metrics(window_seconds=5)
    logger.info(f"Aggregated metrics: {aggregated}")
    
    # 10. Pause the test
    logger.info("\n10. Pausing test...")
    await orchestrator.pause_test()
    await asyncio.sleep(2)
    
    # 11. Resume the test
    logger.info("\n11. Resuming test...")
    await orchestrator.resume_test()
    await asyncio.sleep(2)
    
    # 12. Complete the test
    logger.info("\n12. Completing test...")
    await orchestrator.complete_test(success=True)
    
    # 13. Stop metrics collection
    logger.info("\n13. Stopping metrics collection...")
    await metrics_aggregator.stop_collection()
    
    # 14. Get test results
    logger.info("\n14. Getting test results...")
    results = orchestrator.get_test_results()
    
    if results:
        # Update results with final metrics
        results.final_system_metrics = metrics_aggregator.current_system_metrics
        results.final_business_metrics = metrics_aggregator.current_business_metrics
        results.success_criteria_met = True
        results.criteria_results = {
            'zero_data_loss': True,
            'p95_latency_ms': True,
            'error_rate': True
        }
        
        # 15. Save test results
        logger.info("\n15. Saving test results...")
        results_path = results_store.save_test_results(results)
        logger.info(f"Results saved to: {results_path}")
        
        # 16. Generate reports
        logger.info("\n16. Generating reports...")
        json_report = results_store.generate_report(results, format='json')
        logger.info(f"JSON report: {json_report}")
        
        markdown_report = results_store.generate_report(results, format='markdown')
        logger.info(f"Markdown report: {markdown_report}")
        
        html_report = results_store.generate_report(results, format='html')
        logger.info(f"HTML report: {html_report}")
        
        # 17. List all test results
        logger.info("\n17. Listing all test results...")
        all_results = results_store.list_test_results(limit=5)
        logger.info(f"Found {len(all_results)} test results")
        for result_summary in all_results:
            logger.info(f"  - {result_summary['test_id']}: {result_summary['test_name']} ({result_summary['status']})")
    
    # 18. Get aggregator statistics
    logger.info("\n18. Aggregator statistics...")
    stats = metrics_aggregator.get_statistics()
    logger.info(f"Metrics collected: {stats['total_metrics_collected']}")
    logger.info(f"System metrics count: {stats['system_metrics_count']}")
    logger.info(f"Business metrics count: {stats['business_metrics_count']}")
    
    logger.info("\n=== Example completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(main())
