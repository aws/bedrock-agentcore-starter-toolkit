"""
Test Results Store - Persists and manages stress test results.

This module implements storage, retrieval, and comparison of stress test results,
including detailed metrics, reports, and historical data.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from ..models import (
    TestResults,
    TestStatus,
    SystemMetrics,
    BusinessMetrics,
    AgentMetrics
)


logger = logging.getLogger(__name__)


class TestResultsStore:
    """
    Manages storage and retrieval of stress test results.
    
    Provides functionality for persisting test results, generating reports,
    and comparing multiple test runs.
    """
    
    def __init__(self, storage_dir: str = "stress_testing/results"):
        """
        Initialize test results store.
        
        Args:
            storage_dir: Directory for storing test results
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.results_dir = self.storage_dir / "test_results"
        self.reports_dir = self.storage_dir / "reports"
        self.metrics_dir = self.storage_dir / "metrics"
        
        self.results_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.metrics_dir.mkdir(exist_ok=True)
        
        logger.info(f"TestResultsStore initialized at {self.storage_dir}")
    
    def save_test_results(self, results: TestResults) -> str:
        """
        Save test results to storage.
        
        Args:
            results: Test results to save
            
        Returns:
            Path to saved results file
        """
        try:
            # Create filename
            filename = f"{results.test_id}_results.json"
            filepath = self.results_dir / filename
            
            # Convert to dictionary
            results_dict = self._test_results_to_dict(results)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(results_dict, f, indent=2, default=str)
            
            logger.info(f"Saved test results: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
            raise
    
    def load_test_results(self, test_id: str) -> Optional[TestResults]:
        """
        Load test results from storage.
        
        Args:
            test_id: Test ID to load
            
        Returns:
            TestResults object or None if not found
        """
        try:
            filename = f"{test_id}_results.json"
            filepath = self.results_dir / filename
            
            if not filepath.exists():
                logger.warning(f"Test results not found: {test_id}")
                return None
            
            with open(filepath, 'r') as f:
                results_dict = json.load(f)
            
            # Convert back to TestResults
            results = self._dict_to_test_results(results_dict)
            
            logger.info(f"Loaded test results: {test_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error loading test results: {e}")
            return None
    
    def list_test_results(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all stored test results.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of test result summaries
        """
        try:
            results = []
            
            # Get all result files
            result_files = sorted(
                self.results_dir.glob("*_results.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Apply limit
            if limit:
                result_files = result_files[:limit]
            
            # Load summaries
            for filepath in result_files:
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    # Create summary
                    summary = {
                        'test_id': data.get('test_id'),
                        'test_name': data.get('test_name'),
                        'status': data.get('status'),
                        'start_time': data.get('start_time'),
                        'end_time': data.get('end_time'),
                        'duration_seconds': data.get('duration_seconds'),
                        'success_criteria_met': data.get('success_criteria_met'),
                        'scenario_id': data.get('scenario', {}).get('scenario_id')
                    }
                    results.append(summary)
                    
                except Exception as e:
                    logger.error(f"Error loading summary from {filepath}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error listing test results: {e}")
            return []
    
    def delete_test_results(self, test_id: str) -> bool:
        """
        Delete test results from storage.
        
        Args:
            test_id: Test ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            filename = f"{test_id}_results.json"
            filepath = self.results_dir / filename
            
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted test results: {test_id}")
                return True
            else:
                logger.warning(f"Test results not found: {test_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting test results: {e}")
            return False
    
    def generate_report(self, results: TestResults, format: str = 'json') -> str:
        """
        Generate a detailed report from test results.
        
        Args:
            results: Test results to generate report from
            format: Report format ('json', 'html', 'markdown')
            
        Returns:
            Path to generated report
        """
        try:
            if format == 'json':
                return self._generate_json_report(results)
            elif format == 'html':
                return self._generate_html_report(results)
            elif format == 'markdown':
                return self._generate_markdown_report(results)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
    
    def _generate_json_report(self, results: TestResults) -> str:
        """Generate JSON format report."""
        filename = f"{results.test_id}_report.json"
        filepath = self.reports_dir / filename
        
        report = {
            'test_id': results.test_id,
            'test_name': results.test_name,
            'generated_at': datetime.utcnow().isoformat(),
            'summary': self._create_summary(results),
            'metrics': self._create_metrics_summary(results),
            'success_criteria': results.criteria_results,
            'issues': results.issues_detected,
            'recommendations': results.recommendations
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Generated JSON report: {filepath}")
        return str(filepath)
    
    def _generate_markdown_report(self, results: TestResults) -> str:
        """Generate Markdown format report."""
        filename = f"{results.test_id}_report.md"
        filepath = self.reports_dir / filename
        
        # Build markdown content
        lines = [
            f"# Stress Test Report: {results.test_name}",
            "",
            f"**Test ID:** {results.test_id}",
            f"**Status:** {results.status.value}",
            f"**Duration:** {results.duration_seconds:.2f} seconds",
            f"**Start Time:** {results.start_time.isoformat()}",
            f"**End Time:** {results.end_time.isoformat() if results.end_time else 'N/A'}",
            "",
            "## Summary",
            ""
        ]
        
        summary = self._create_summary(results)
        for key, value in summary.items():
            lines.append(f"- **{key}:** {value}")
        
        lines.extend([
            "",
            "## Metrics Summary",
            ""
        ])
        
        metrics_summary = self._create_metrics_summary(results)
        
        if 'system' in metrics_summary:
            lines.append("### System Metrics")
            lines.append("")
            for key, value in metrics_summary['system'].items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        if 'business' in metrics_summary:
            lines.append("### Business Metrics")
            lines.append("")
            for key, value in metrics_summary['business'].items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        # Success criteria
        lines.extend([
            "## Success Criteria",
            ""
        ])
        
        for criterion, met in results.criteria_results.items():
            status = "✓" if met else "✗"
            lines.append(f"- {status} {criterion}")
        
        lines.append("")
        
        # Issues
        if results.issues_detected:
            lines.extend([
                "## Issues Detected",
                ""
            ])
            for issue in results.issues_detected:
                lines.append(f"- {issue}")
            lines.append("")
        
        # Recommendations
        if results.recommendations:
            lines.extend([
                "## Recommendations",
                ""
            ])
            for rec in results.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        # Write to file
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Generated Markdown report: {filepath}")
        return str(filepath)
    
    def _generate_html_report(self, results: TestResults) -> str:
        """Generate HTML format report."""
        filename = f"{results.test_id}_report.html"
        filepath = self.reports_dir / filename
        
        summary = self._create_summary(results)
        metrics_summary = self._create_metrics_summary(results)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Stress Test Report: {results.test_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .metric {{ margin: 10px 0; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Stress Test Report: {results.test_name}</h1>
    
    <div class="summary">
        <p><strong>Test ID:</strong> {results.test_id}</p>
        <p><strong>Status:</strong> <span class="{'success' if results.status == TestStatus.COMPLETED else 'failure'}">{results.status.value}</span></p>
        <p><strong>Duration:</strong> {results.duration_seconds:.2f} seconds</p>
        <p><strong>Start Time:</strong> {results.start_time.isoformat()}</p>
        <p><strong>End Time:</strong> {results.end_time.isoformat() if results.end_time else 'N/A'}</p>
    </div>
    
    <h2>Summary</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in summary.items())}
    </table>
    
    <h2>Success Criteria</h2>
    <ul>
        {''.join(f'<li class="{'success' if met else 'failure'}">{"✓" if met else "✗"} {criterion}</li>' for criterion, met in results.criteria_results.items())}
    </ul>
    
    {f'<h2>Issues Detected</h2><ul>{"".join(f"<li>{issue}</li>" for issue in results.issues_detected)}</ul>' if results.issues_detected else ''}
    
    {f'<h2>Recommendations</h2><ul>{"".join(f"<li>{rec}</li>" for rec in results.recommendations)}</ul>' if results.recommendations else ''}
    
    <p><em>Generated at {datetime.utcnow().isoformat()}</em></p>
</body>
</html>
"""
        
        with open(filepath, 'w') as f:
            f.write(html)
        
        logger.info(f"Generated HTML report: {filepath}")
        return str(filepath)
    
    def compare_test_runs(self, test_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple test runs.
        
        Args:
            test_ids: List of test IDs to compare
            
        Returns:
            Comparison results
        """
        try:
            # Load all test results
            results_list = []
            for test_id in test_ids:
                results = self.load_test_results(test_id)
                if results:
                    results_list.append(results)
            
            if len(results_list) < 2:
                logger.warning("Need at least 2 test results to compare")
                return {}
            
            # Build comparison
            comparison = {
                'test_count': len(results_list),
                'test_ids': test_ids,
                'comparison_date': datetime.utcnow().isoformat(),
                'metrics_comparison': self._compare_metrics(results_list),
                'performance_trends': self._analyze_trends(results_list),
                'recommendations': self._generate_comparison_recommendations(results_list)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing test runs: {e}")
            return {}
    
    def _compare_metrics(self, results_list: List[TestResults]) -> Dict[str, Any]:
        """Compare metrics across test runs."""
        comparison = {
            'throughput': [],
            'response_time': [],
            'error_rate': [],
            'success_rate': []
        }
        
        for results in results_list:
            if results.final_system_metrics:
                metrics = results.final_system_metrics
                comparison['throughput'].append({
                    'test_id': results.test_id,
                    'value': metrics.throughput_tps
                })
                comparison['response_time'].append({
                    'test_id': results.test_id,
                    'p95': metrics.p95_response_time_ms,
                    'p99': metrics.p99_response_time_ms
                })
                comparison['error_rate'].append({
                    'test_id': results.test_id,
                    'value': metrics.error_rate
                })
                
                success_rate = metrics.requests_successful / metrics.requests_total if metrics.requests_total > 0 else 0
                comparison['success_rate'].append({
                    'test_id': results.test_id,
                    'value': success_rate
                })
        
        return comparison
    
    def _analyze_trends(self, results_list: List[TestResults]) -> Dict[str, Any]:
        """Analyze performance trends."""
        # Sort by start time
        sorted_results = sorted(results_list, key=lambda r: r.start_time)
        
        trends = {
            'improving': [],
            'degrading': [],
            'stable': []
        }
        
        # Analyze throughput trend
        if len(sorted_results) >= 2:
            throughputs = [r.final_system_metrics.throughput_tps for r in sorted_results if r.final_system_metrics]
            if len(throughputs) >= 2:
                if throughputs[-1] > throughputs[0] * 1.1:
                    trends['improving'].append('throughput')
                elif throughputs[-1] < throughputs[0] * 0.9:
                    trends['degrading'].append('throughput')
                else:
                    trends['stable'].append('throughput')
        
        return trends
    
    def _generate_comparison_recommendations(self, results_list: List[TestResults]) -> List[str]:
        """Generate recommendations based on comparison."""
        recommendations = []
        
        # Check for performance degradation
        sorted_results = sorted(results_list, key=lambda r: r.start_time)
        if len(sorted_results) >= 2:
            latest = sorted_results[-1]
            previous = sorted_results[-2]
            
            if latest.final_system_metrics and previous.final_system_metrics:
                # Compare throughput
                if latest.final_system_metrics.throughput_tps < previous.final_system_metrics.throughput_tps * 0.9:
                    recommendations.append("Throughput has decreased by >10%. Investigate recent changes.")
                
                # Compare error rate
                if latest.final_system_metrics.error_rate > previous.final_system_metrics.error_rate * 1.5:
                    recommendations.append("Error rate has increased significantly. Review error logs.")
        
        return recommendations
    
    def _create_summary(self, results: TestResults) -> Dict[str, Any]:
        """Create summary from test results."""
        summary = {
            'Status': results.status.value,
            'Duration': f"{results.duration_seconds:.2f}s",
            'Success Criteria Met': results.success_criteria_met
        }
        
        if results.final_system_metrics:
            metrics = results.final_system_metrics
            summary.update({
                'Throughput': f"{metrics.throughput_tps:.2f} TPS",
                'Total Requests': metrics.requests_total,
                'Successful Requests': metrics.requests_successful,
                'Failed Requests': metrics.requests_failed,
                'Error Rate': f"{metrics.error_rate * 100:.2f}%",
                'Avg Response Time': f"{metrics.avg_response_time_ms:.2f}ms",
                'P95 Response Time': f"{metrics.p95_response_time_ms:.2f}ms",
                'P99 Response Time': f"{metrics.p99_response_time_ms:.2f}ms"
            })
        
        return summary
    
    def _create_metrics_summary(self, results: TestResults) -> Dict[str, Any]:
        """Create metrics summary."""
        summary = {}
        
        if results.final_system_metrics:
            metrics = results.final_system_metrics
            summary['system'] = {
                'throughput_tps': metrics.throughput_tps,
                'requests_total': metrics.requests_total,
                'error_rate': metrics.error_rate,
                'avg_response_time_ms': metrics.avg_response_time_ms,
                'p95_response_time_ms': metrics.p95_response_time_ms,
                'p99_response_time_ms': metrics.p99_response_time_ms,
                'cpu_utilization': metrics.cpu_utilization,
                'memory_utilization': metrics.memory_utilization
            }
        
        if results.final_business_metrics:
            metrics = results.final_business_metrics
            summary['business'] = {
                'transactions_processed': metrics.transactions_processed,
                'fraud_detected': metrics.fraud_detected,
                'fraud_prevented_amount': metrics.fraud_prevented_amount,
                'cost_per_transaction': metrics.cost_per_transaction,
                'roi_percentage': metrics.roi_percentage
            }
        
        return summary
    
    def _test_results_to_dict(self, results: TestResults) -> Dict[str, Any]:
        """Convert TestResults to dictionary."""
        return {
            'test_id': results.test_id,
            'test_name': results.test_name,
            'config': asdict(results.config),
            'scenario': asdict(results.scenario),
            'start_time': results.start_time.isoformat(),
            'end_time': results.end_time.isoformat() if results.end_time else None,
            'duration_seconds': results.duration_seconds,
            'status': results.status.value,
            'final_system_metrics': asdict(results.final_system_metrics) if results.final_system_metrics else None,
            'final_business_metrics': asdict(results.final_business_metrics) if results.final_business_metrics else None,
            'agent_metrics_summary': {k: asdict(v) for k, v in results.agent_metrics_summary.items()},
            'success_criteria_met': results.success_criteria_met,
            'criteria_results': results.criteria_results,
            'issues_detected': results.issues_detected,
            'recommendations': results.recommendations,
            'report_path': results.report_path,
            'logs_path': results.logs_path
        }
    
    def _dict_to_test_results(self, data: Dict[str, Any]) -> TestResults:
        """Convert dictionary to TestResults (simplified)."""
        # This is a simplified conversion - full implementation would need
        # to properly reconstruct all nested objects
        from ..config import ConfigurationManager
        
        config_manager = ConfigurationManager()
        
        # Note: This is a basic implementation
        # Full implementation would reconstruct all objects properly
        return TestResults(
            test_id=data['test_id'],
            test_name=data['test_name'],
            config=config_manager.create_default_config(data['test_name']),
            scenario=None,  # Would need to reconstruct
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            duration_seconds=data['duration_seconds'],
            status=TestStatus(data['status']),
            success_criteria_met=data['success_criteria_met'],
            criteria_results=data['criteria_results'],
            issues_detected=data['issues_detected'],
            recommendations=data['recommendations']
        )
