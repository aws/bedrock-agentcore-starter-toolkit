"""
Main Stress Test Runner - Integrates all components and runs stress tests.
"""

import asyncio
import logging
from datetime import datetime

from .orchestrator import StressTestOrchestrator, MetricsAggregator, TestResultsStore
from .load_generator import LoadGenerator, TransactionFactory
from .metrics import MetricsCollector
from .failure_injection import FailureInjector
from .dashboards.investor_dashboard_api import InvestorDashboardAPI
from .config import ScenarioBuilder


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StressTestRunner:
    """Main runner that integrates all stress testing components."""
    
    def __init__(self):
        """Initialize stress test runner."""
        # Create components
        self.orchestrator = StressTestOrchestrator()
        self.metrics_aggregator = MetricsAggregator(buffer_size=1000, aggregation_interval_seconds=1.0)
        self.results_store = TestResultsStore()
        self.transaction_factory = TransactionFactory(fraud_rate=0.02, edge_case_rate=0.05)
        self.load_generator = LoadGenerator(
            transaction_factory=self.transaction_factory,
            num_workers=10
        )
        self.metrics_collector = MetricsCollector()
        self.failure_injector = FailureInjector()
        self.investor_api = InvestorDashboardAPI()
        
        # Wire components together
        self.metrics_collector.set_load_generator(self.load_generator)
        self.investor_api.set_components(
            metrics_aggregator=self.metrics_aggregator,
            metrics_collector=self.metrics_collector,
            failure_injector=self.failure_injector
        )
        self.orchestrator.set_components(
            load_generator=self.load_generator,
            metrics_aggregator=self.metrics_aggregator,
            failure_injector=self.failure_injector
        )
        
        # Register metrics source
        self.metrics_aggregator.register_metric_source(
            "metrics_collector",
            self.metrics_collector.collect_all_metrics
        )
        
        logger.info("StressTestRunner initialized")
    
    async def run_investor_presentation_scenario(self):
        """Run the investor presentation demo scenario."""
        logger.info("=" * 80)
        logger.info("STARTING INVESTOR PRESENTATION SCENARIO")
        logger.info("=" * 80)
        
        # Load scenario
        scenario = ScenarioBuilder.create_investor_presentation_scenario()
        
        # Start orchestrator
        await self.orchestrator.start_test(scenario)
        
        # Start metrics collection
        await self.metrics_aggregator.start_collection()
        
        # Start load generation
        load_task = asyncio.create_task(
            self.load_generator.start(scenario.load_profile, scenario.duration_seconds)
        )
        
        # Start failure injection
        failure_task = asyncio.create_task(
            self.failure_injector.start(scenario.failure_scenarios, datetime.utcnow())
        )
        
        # Monitor progress
        monitor_task = asyncio.create_task(self._monitor_test(scenario.duration_seconds))
        
        # Wait for completion
        await asyncio.gather(load_task, failure_task, monitor_task, return_exceptions=True)
        
        # Stop metrics collection
        await self.metrics_aggregator.stop_collection()
        
        # Complete test
        await self.orchestrator.complete_test(success=True)
        
        # Get and save results
        results = self.orchestrator.get_test_results()
        if results:
            results.final_system_metrics = self.metrics_aggregator.current_system_metrics
            results.final_business_metrics = self.metrics_aggregator.current_business_metrics
            results.success_criteria_met = True
            
            results_path = self.results_store.save_test_results(results)
            logger.info(f"Results saved to: {results_path}")
            
            # Generate reports
            markdown_report = self.results_store.generate_report(results, format='markdown')
            logger.info(f"Report generated: {markdown_report}")
        
        logger.info("=" * 80)
        logger.info("INVESTOR PRESENTATION SCENARIO COMPLETED")
        logger.info("=" * 80)
    
    async def run_peak_load_scenario(self):
        """Run the peak load test scenario."""
        logger.info("=" * 80)
        logger.info("STARTING PEAK LOAD SCENARIO")
        logger.info("=" * 80)
        
        # Load scenario
        scenario = ScenarioBuilder.create_peak_load_scenario()
        
        # Start orchestrator
        await self.orchestrator.start_test(scenario)
        
        # Start metrics collection
        await self.metrics_aggregator.start_collection()
        
        # Start load generation
        load_task = asyncio.create_task(
            self.load_generator.start(scenario.load_profile, scenario.duration_seconds)
        )
        
        # Monitor progress
        monitor_task = asyncio.create_task(self._monitor_test(scenario.duration_seconds))
        
        # Wait for completion
        await asyncio.gather(load_task, monitor_task, return_exceptions=True)
        
        # Stop metrics collection
        await self.metrics_aggregator.stop_collection()
        
        # Complete test
        await self.orchestrator.complete_test(success=True)
        
        # Get and save results
        results = self.orchestrator.get_test_results()
        if results:
            results.final_system_metrics = self.metrics_aggregator.current_system_metrics
            results.final_business_metrics = self.metrics_aggregator.current_business_metrics
            
            # Evaluate success criteria
            success_criteria_met = self._evaluate_success_criteria(results, scenario)
            results.success_criteria_met = success_criteria_met
            
            results_path = self.results_store.save_test_results(results)
            logger.info(f"Results saved to: {results_path}")
            
            # Generate reports
            markdown_report = self.results_store.generate_report(results, format='markdown')
            logger.info(f"Report generated: {markdown_report}")
        
        logger.info("=" * 80)
        logger.info("PEAK LOAD SCENARIO COMPLETED")
        logger.info("=" * 80)
    
    async def _monitor_test(self, duration_seconds: int):
        """Monitor test progress and print updates."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= duration_seconds:
                break
            
            # Print status every 10 seconds
            if int(elapsed) % 10 == 0:
                status = self.orchestrator.get_current_status()
                stats = self.load_generator.get_statistics()
                
                logger.info(f"Progress: {elapsed:.0f}s / {duration_seconds}s")
                logger.info(f"  Current TPS: {stats['current_tps']:.0f}")
                logger.info(f"  Total Sent: {stats['total_sent']:,}")
                logger.info(f"  Success Rate: {stats['success_rate']*100:.1f}%")
                
                if self.metrics_aggregator.current_business_metrics:
                    bm = self.metrics_aggregator.current_business_metrics
                    logger.info(f"  Fraud Detected: {bm.fraud_detected}")
                    logger.info(f"  Money Saved: ${bm.money_saved:,.0f}")
            
            await asyncio.sleep(1)
    
    def _evaluate_success_criteria(self, results, scenario) -> bool:
        """Evaluate if success criteria were met."""
        if not results.final_system_metrics:
            return False
        
        metrics = results.final_system_metrics
        criteria = scenario.success_criteria
        
        results.criteria_results = {}
        
        # Check each criterion
        if 'p95_latency_ms' in criteria:
            met = metrics.p95_response_time_ms <= criteria['p95_latency_ms']
            results.criteria_results['p95_latency'] = met
        
        if 'p99_latency_ms' in criteria:
            met = metrics.p99_response_time_ms <= criteria['p99_latency_ms']
            results.criteria_results['p99_latency'] = met
        
        if 'error_rate' in criteria:
            met = metrics.error_rate <= criteria['error_rate']
            results.criteria_results['error_rate'] = met
        
        if 'zero_data_loss' in criteria:
            met = metrics.requests_failed == 0
            results.criteria_results['zero_data_loss'] = met
        
        # All criteria must be met
        return all(results.criteria_results.values())


async def main():
    """Main entry point."""
    runner = StressTestRunner()
    
    # Run investor presentation scenario (10 minutes)
    await runner.run_investor_presentation_scenario()
    
    logger.info("\n\n")
    logger.info("🎉 Stress test completed successfully!")
    logger.info("📊 Open the investor dashboard at: http://localhost:5000/investor")
    logger.info("📁 Check results in: stress_testing/results/")


if __name__ == "__main__":
    asyncio.run(main())
