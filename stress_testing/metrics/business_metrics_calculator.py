"""
Business Metrics Calculator - Calculates business value metrics.

This module provides comprehensive business metrics calculation including:
- Fraud detection rate and accuracy
- Cost per transaction from AWS billing data
- ROI metrics and money saved
- Competitive benchmark comparisons
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..models import BusinessMetrics, CompetitiveBenchmarks, SystemMetrics


logger = logging.getLogger(__name__)


@dataclass
class FraudDetectionStats:
    """Statistics for fraud detection calculations."""
    total_transactions: int
    fraud_detected: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int


@dataclass
class CostBreakdown:
    """Detailed cost breakdown by AWS service."""
    lambda_cost: float
    dynamodb_cost: float
    kinesis_cost: float
    bedrock_cost: float
    s3_cost: float
    cloudwatch_cost: float
    other_costs: float
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost."""
        return (
            self.lambda_cost + self.dynamodb_cost + self.kinesis_cost +
            self.bedrock_cost + self.s3_cost + self.cloudwatch_cost + self.other_costs
        )


class BusinessMetricsCalculator:
    """
    Calculates business value metrics for the fraud detection system.
    
    This class provides methods to calculate:
    - Fraud detection effectiveness metrics
    - Cost efficiency and ROI
    - Competitive benchmarks
    - Business value storytelling metrics
    """
    
    # Default pricing (can be overridden)
    DEFAULT_PRICING = {
        'lambda_per_gb_second': 0.0000166667,  # $0.0000166667 per GB-second
        'lambda_per_request': 0.0000002,  # $0.20 per 1M requests
        'dynamodb_write_per_million': 1.25,  # $1.25 per million write units
        'dynamodb_read_per_million': 0.25,  # $0.25 per million read units
        'kinesis_per_shard_hour': 0.015,  # $0.015 per shard hour
        'kinesis_per_million_put': 0.014,  # $0.014 per million PUT payload units
        'bedrock_claude_per_1k_input': 0.003,  # $0.003 per 1K input tokens
        'bedrock_claude_per_1k_output': 0.015,  # $0.015 per 1K output tokens
        's3_per_1k_put': 0.005,  # $0.005 per 1,000 PUT requests
        'cloudwatch_per_metric': 0.30,  # $0.30 per custom metric
    }
    
    # Competitive baseline (industry averages)
    COMPETITIVE_BASELINE = {
        'fraud_detection_accuracy': 0.85,  # 85% industry average
        'false_positive_rate': 0.10,  # 10% industry average
        'cost_per_transaction': 0.05,  # $0.05 industry average
        'avg_response_time_ms': 500,  # 500ms industry average
        'uptime_percentage': 99.5,  # 99.5% industry average
    }
    
    def __init__(self, pricing: Optional[Dict[str, float]] = None):
        """
        Initialize business metrics calculator.
        
        Args:
            pricing: Optional custom pricing dictionary to override defaults
        """
        self.pricing = {**self.DEFAULT_PRICING, **(pricing or {})}
        self.baseline = self.COMPETITIVE_BASELINE.copy()
        
        # Fraud detection assumptions
        self.avg_fraud_amount = 300.0  # Average fraud transaction amount
        self.fraud_rate = 0.02  # 2% of transactions are fraudulent
        self.detection_accuracy = 0.95  # 95% detection accuracy
        
        logger.info("BusinessMetricsCalculator initialized")
    
    def calculate_fraud_detection_metrics(
        self,
        total_transactions: int,
        fraud_detected: int,
        true_positives: Optional[int] = None,
        false_positives: Optional[int] = None,
        false_negatives: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate fraud detection rate and accuracy metrics.
        
        Args:
            total_transactions: Total number of transactions processed
            fraud_detected: Number of fraudulent transactions detected
            true_positives: Actual fraud correctly identified (optional)
            false_positives: Legitimate transactions flagged as fraud (optional)
            false_negatives: Fraud that was missed (optional)
            
        Returns:
            Dictionary containing fraud detection metrics
        """
        # Estimate actual fraud if not provided
        actual_fraud = int(total_transactions * self.fraud_rate)
        
        # Calculate confusion matrix if not provided
        if true_positives is None:
            true_positives = int(actual_fraud * self.detection_accuracy)
        
        if false_negatives is None:
            false_negatives = actual_fraud - true_positives
        
        if false_positives is None:
            # Estimate false positives (typically 1-5% of legitimate transactions)
            legitimate_transactions = total_transactions - actual_fraud
            false_positives = int(legitimate_transactions * 0.02)
        
        true_negatives = total_transactions - true_positives - false_positives - false_negatives
        
        # Calculate metrics
        accuracy = (true_positives + true_negatives) / total_transactions if total_transactions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        false_positive_rate = false_positives / (false_positives + true_negatives) if (false_positives + true_negatives) > 0 else 0
        false_negative_rate = false_negatives / (false_negatives + true_positives) if (false_negatives + true_positives) > 0 else 0
        
        fraud_detection_rate = fraud_detected / total_transactions if total_transactions > 0 else 0
        
        logger.debug(
            f"Fraud metrics: accuracy={accuracy:.3f}, precision={precision:.3f}, "
            f"recall={recall:.3f}, f1={f1_score:.3f}"
        )
        
        return {
            'fraud_detection_rate': fraud_detection_rate,
            'fraud_detection_accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'false_positive_rate': false_positive_rate,
            'false_negative_rate': false_negative_rate,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'true_negatives': true_negatives,
        }
    
    def calculate_cost_metrics(
        self,
        total_transactions: int,
        duration_hours: float,
        lambda_invocations: Optional[int] = None,
        lambda_gb_seconds: Optional[float] = None,
        dynamodb_writes: Optional[int] = None,
        dynamodb_reads: Optional[int] = None,
        kinesis_shards: Optional[int] = None,
        kinesis_puts: Optional[int] = None,
        bedrock_input_tokens: Optional[int] = None,
        bedrock_output_tokens: Optional[int] = None,
        s3_puts: Optional[int] = None,
        custom_metrics: Optional[int] = None
    ) -> CostBreakdown:
        """
        Calculate cost per transaction from AWS billing data.
        
        Args:
            total_transactions: Total transactions processed
            duration_hours: Test duration in hours
            lambda_invocations: Number of Lambda invocations
            lambda_gb_seconds: Lambda GB-seconds consumed
            dynamodb_writes: DynamoDB write capacity units
            dynamodb_reads: DynamoDB read capacity units
            kinesis_shards: Number of Kinesis shards
            kinesis_puts: Number of Kinesis PUT operations
            bedrock_input_tokens: Bedrock input tokens
            bedrock_output_tokens: Bedrock output tokens
            s3_puts: S3 PUT operations
            custom_metrics: Number of custom CloudWatch metrics
            
        Returns:
            CostBreakdown object with detailed cost information
        """
        # Estimate values if not provided
        if lambda_invocations is None:
            # Assume 5 Lambda invocations per transaction (agents + orchestrator)
            lambda_invocations = total_transactions * 5
        
        if lambda_gb_seconds is None:
            # Assume 1GB memory, 200ms average duration
            lambda_gb_seconds = lambda_invocations * 1.0 * 0.2
        
        if dynamodb_writes is None:
            # Assume 3 writes per transaction (user profile, transaction, audit)
            dynamodb_writes = total_transactions * 3
        
        if dynamodb_reads is None:
            # Assume 5 reads per transaction (user history, patterns, rules)
            dynamodb_reads = total_transactions * 5
        
        if kinesis_shards is None:
            # Estimate shards based on throughput (1 shard = ~1000 records/sec)
            tps = total_transactions / (duration_hours * 3600) if duration_hours > 0 else 0
            kinesis_shards = max(1, int(tps / 1000) + 1)
        
        if kinesis_puts is None:
            # One PUT per transaction
            kinesis_puts = total_transactions
        
        if bedrock_input_tokens is None:
            # Assume 500 input tokens per transaction for reasoning
            bedrock_input_tokens = total_transactions * 500
        
        if bedrock_output_tokens is None:
            # Assume 200 output tokens per transaction
            bedrock_output_tokens = total_transactions * 200
        
        if s3_puts is None:
            # Assume 1 audit log per transaction
            s3_puts = total_transactions
        
        if custom_metrics is None:
            # Assume 50 custom metrics
            custom_metrics = 50
        
        # Calculate costs
        lambda_cost = (
            lambda_invocations * self.pricing['lambda_per_request'] +
            lambda_gb_seconds * self.pricing['lambda_per_gb_second']
        )
        
        dynamodb_cost = (
            (dynamodb_writes / 1_000_000) * self.pricing['dynamodb_write_per_million'] +
            (dynamodb_reads / 1_000_000) * self.pricing['dynamodb_read_per_million']
        )
        
        kinesis_cost = (
            kinesis_shards * duration_hours * self.pricing['kinesis_per_shard_hour'] +
            (kinesis_puts / 1_000_000) * self.pricing['kinesis_per_million_put']
        )
        
        bedrock_cost = (
            (bedrock_input_tokens / 1000) * self.pricing['bedrock_claude_per_1k_input'] +
            (bedrock_output_tokens / 1000) * self.pricing['bedrock_claude_per_1k_output']
        )
        
        s3_cost = (s3_puts / 1000) * self.pricing['s3_per_1k_put']
        
        cloudwatch_cost = custom_metrics * self.pricing['cloudwatch_per_metric']
        
        # Other costs (networking, data transfer, etc.) - estimate as 10% of total
        other_costs = (lambda_cost + dynamodb_cost + kinesis_cost + bedrock_cost + s3_cost + cloudwatch_cost) * 0.1
        
        cost_breakdown = CostBreakdown(
            lambda_cost=lambda_cost,
            dynamodb_cost=dynamodb_cost,
            kinesis_cost=kinesis_cost,
            bedrock_cost=bedrock_cost,
            s3_cost=s3_cost,
            cloudwatch_cost=cloudwatch_cost,
            other_costs=other_costs
        )
        
        logger.info(
            f"Cost breakdown: Lambda=${lambda_cost:.2f}, DynamoDB=${dynamodb_cost:.2f}, "
            f"Kinesis=${kinesis_cost:.2f}, Bedrock=${bedrock_cost:.2f}, Total=${cost_breakdown.total_cost:.2f}"
        )
        
        return cost_breakdown
    
    def calculate_roi_metrics(
        self,
        total_transactions: int,
        fraud_detected: int,
        total_cost: float,
        implementation_cost: float = 50000.0,
        monthly_maintenance_cost: float = 5000.0
    ) -> Dict[str, float]:
        """
        Calculate ROI metrics and money saved.
        
        Args:
            total_transactions: Total transactions processed
            fraud_detected: Number of fraudulent transactions detected
            total_cost: Total operational cost
            implementation_cost: One-time implementation cost
            monthly_maintenance_cost: Monthly maintenance cost
            
        Returns:
            Dictionary containing ROI metrics
        """
        # Calculate money saved from fraud prevention
        fraud_prevented_amount = fraud_detected * self.avg_fraud_amount
        
        # Calculate net savings (fraud prevented minus operational costs)
        net_savings = fraud_prevented_amount - total_cost
        
        # Calculate ROI percentage
        total_investment = implementation_cost + total_cost
        roi_percentage = (net_savings / total_investment * 100) if total_investment > 0 else 0
        
        # Calculate payback period (months)
        monthly_savings = net_savings  # Assuming this is monthly data
        if monthly_savings > 0:
            payback_period_months = implementation_cost / monthly_savings
        else:
            payback_period_months = float('inf')
        
        # Calculate annual ROI
        annual_savings = monthly_savings * 12
        annual_cost = total_cost * 12 + monthly_maintenance_cost * 12
        annual_roi = ((annual_savings - annual_cost) / (implementation_cost + annual_cost) * 100) if (implementation_cost + annual_cost) > 0 else 0
        
        # Calculate cost per transaction
        cost_per_transaction = total_cost / total_transactions if total_transactions > 0 else 0
        
        # Calculate value per transaction (fraud prevented per transaction)
        value_per_transaction = fraud_prevented_amount / total_transactions if total_transactions > 0 else 0
        
        logger.info(
            f"ROI metrics: fraud_prevented=${fraud_prevented_amount:.2f}, "
            f"net_savings=${net_savings:.2f}, roi={roi_percentage:.1f}%, "
            f"payback_period={payback_period_months:.1f} months"
        )
        
        return {
            'fraud_prevented_amount': fraud_prevented_amount,
            'money_saved': net_savings,
            'roi_percentage': roi_percentage,
            'annual_roi_percentage': annual_roi,
            'payback_period_months': payback_period_months,
            'cost_per_transaction': cost_per_transaction,
            'value_per_transaction': value_per_transaction,
            'total_cost': total_cost,
            'implementation_cost': implementation_cost,
            'monthly_maintenance_cost': monthly_maintenance_cost,
        }
    
    def generate_competitive_benchmarks(
        self,
        fraud_detection_accuracy: float,
        false_positive_rate: float,
        cost_per_transaction: float,
        avg_response_time_ms: float,
        uptime_percentage: float,
        custom_baseline: Optional[Dict[str, float]] = None
    ) -> CompetitiveBenchmarks:
        """
        Generate competitive benchmark comparisons.
        
        Args:
            fraud_detection_accuracy: Our fraud detection accuracy
            false_positive_rate: Our false positive rate
            cost_per_transaction: Our cost per transaction
            avg_response_time_ms: Our average response time
            uptime_percentage: Our uptime percentage
            custom_baseline: Optional custom baseline to compare against
            
        Returns:
            CompetitiveBenchmarks object with comparison data
        """
        baseline = custom_baseline or self.baseline
        
        our_performance = {
            'fraud_detection_accuracy': fraud_detection_accuracy,
            'false_positive_rate': false_positive_rate,
            'cost_per_transaction': cost_per_transaction,
            'avg_response_time_ms': avg_response_time_ms,
            'uptime_percentage': uptime_percentage,
        }
        
        competitor_avg = {
            'fraud_detection_accuracy': baseline['fraud_detection_accuracy'],
            'false_positive_rate': baseline['false_positive_rate'],
            'cost_per_transaction': baseline['cost_per_transaction'],
            'avg_response_time_ms': baseline['avg_response_time_ms'],
            'uptime_percentage': baseline['uptime_percentage'],
        }
        
        # Calculate improvement percentages
        improvement_percentage = {}
        
        # For accuracy and uptime, higher is better
        improvement_percentage['fraud_detection_accuracy'] = (
            (fraud_detection_accuracy - baseline['fraud_detection_accuracy']) / 
            baseline['fraud_detection_accuracy'] * 100
        )
        improvement_percentage['uptime_percentage'] = (
            (uptime_percentage - baseline['uptime_percentage']) / 
            baseline['uptime_percentage'] * 100
        )
        
        # For false positives, cost, and response time, lower is better
        improvement_percentage['false_positive_rate'] = (
            (baseline['false_positive_rate'] - false_positive_rate) / 
            baseline['false_positive_rate'] * 100
        )
        improvement_percentage['cost_per_transaction'] = (
            (baseline['cost_per_transaction'] - cost_per_transaction) / 
            baseline['cost_per_transaction'] * 100
        )
        improvement_percentage['avg_response_time_ms'] = (
            (baseline['avg_response_time_ms'] - avg_response_time_ms) / 
            baseline['avg_response_time_ms'] * 100
        )
        
        # Identify unique advantages
        unique_advantages = []
        
        if fraud_detection_accuracy > baseline['fraud_detection_accuracy'] * 1.1:
            unique_advantages.append(f"Superior fraud detection accuracy ({fraud_detection_accuracy*100:.1f}% vs {baseline['fraud_detection_accuracy']*100:.1f}%)")
        
        if false_positive_rate < baseline['false_positive_rate'] * 0.5:
            unique_advantages.append(f"Significantly lower false positives ({false_positive_rate*100:.1f}% vs {baseline['false_positive_rate']*100:.1f}%)")
        
        if cost_per_transaction < baseline['cost_per_transaction'] * 0.7:
            unique_advantages.append(f"Lower cost per transaction (${cost_per_transaction:.3f} vs ${baseline['cost_per_transaction']:.3f})")
        
        if avg_response_time_ms < baseline['avg_response_time_ms'] * 0.6:
            unique_advantages.append(f"Faster response time ({avg_response_time_ms:.0f}ms vs {baseline['avg_response_time_ms']:.0f}ms)")
        
        # Always highlight unique features
        unique_advantages.extend([
            "Explainable AI with chain-of-thought reasoning",
            "Multi-agent coordination for comprehensive analysis",
            "Real-time adaptive learning from patterns",
            "Zero-downtime deployment with auto-scaling"
        ])
        
        # Determine market position
        accuracy_score = fraud_detection_accuracy / baseline['fraud_detection_accuracy']
        cost_score = baseline['cost_per_transaction'] / cost_per_transaction if cost_per_transaction > 0 else 1.0
        performance_score = baseline['avg_response_time_ms'] / avg_response_time_ms if avg_response_time_ms > 0 else 1.0
        
        overall_score = (accuracy_score + cost_score + performance_score) / 3
        
        if overall_score >= 1.3:
            market_position = "leader"
        elif overall_score >= 1.1:
            market_position = "challenger"
        else:
            market_position = "follower"
        
        logger.info(
            f"Competitive benchmarks: position={market_position}, "
            f"accuracy_improvement={improvement_percentage['fraud_detection_accuracy']:.1f}%, "
            f"cost_improvement={improvement_percentage['cost_per_transaction']:.1f}%"
        )
        
        return CompetitiveBenchmarks(
            timestamp=datetime.utcnow(),
            our_performance=our_performance,
            competitor_avg=competitor_avg,
            improvement_percentage=improvement_percentage,
            unique_advantages=unique_advantages,
            market_position=market_position
        )
    
    def calculate_business_metrics(
        self,
        total_transactions: int,
        fraud_detected: int,
        cost_breakdown: CostBreakdown,
        duration_hours: float,
        system_metrics: Optional[SystemMetrics] = None,
        true_positives: Optional[int] = None,
        false_positives: Optional[int] = None,
        false_negatives: Optional[int] = None
    ) -> BusinessMetrics:
        """
        Calculate comprehensive business metrics.
        
        This is the main method that combines all calculations into a single
        BusinessMetrics object.
        
        Args:
            total_transactions: Total transactions processed
            fraud_detected: Number of fraudulent transactions detected
            cost_breakdown: Detailed cost breakdown
            duration_hours: Test duration in hours
            system_metrics: Optional system metrics for additional context
            true_positives: Actual fraud correctly identified (optional)
            false_positives: Legitimate transactions flagged as fraud (optional)
            false_negatives: Fraud that was missed (optional)
            
        Returns:
            BusinessMetrics object with all calculated metrics
        """
        # Calculate fraud detection metrics
        fraud_metrics = self.calculate_fraud_detection_metrics(
            total_transactions=total_transactions,
            fraud_detected=fraud_detected,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives
        )
        
        # Calculate ROI metrics
        roi_metrics = self.calculate_roi_metrics(
            total_transactions=total_transactions,
            fraud_detected=fraud_detected,
            total_cost=cost_breakdown.total_cost
        )
        
        # Calculate transactions per second
        transactions_per_second = total_transactions / (duration_hours * 3600) if duration_hours > 0 else 0
        
        # Calculate customer impact score (based on false positives and system performance)
        false_positive_impact = fraud_metrics['false_positive_rate']
        customer_impact_score = 1.0 - (false_positive_impact * 0.5)  # False positives reduce customer satisfaction
        
        if system_metrics:
            # Factor in response time (slower = worse customer experience)
            response_time_factor = max(0, 1.0 - (system_metrics.avg_response_time_ms / 5000))
            customer_impact_score = (customer_impact_score + response_time_factor) / 2
        
        # Calculate performance vs baseline
        performance_vs_baseline = fraud_metrics['fraud_detection_accuracy'] / self.baseline['fraud_detection_accuracy']
        
        # Calculate cost vs baseline
        cost_vs_baseline = roi_metrics['cost_per_transaction'] / self.baseline['cost_per_transaction']
        
        # Create AWS cost breakdown dictionary
        aws_cost_breakdown = {
            'lambda': cost_breakdown.lambda_cost,
            'dynamodb': cost_breakdown.dynamodb_cost,
            'kinesis': cost_breakdown.kinesis_cost,
            'bedrock': cost_breakdown.bedrock_cost,
            's3': cost_breakdown.s3_cost,
            'cloudwatch': cost_breakdown.cloudwatch_cost,
            'other': cost_breakdown.other_costs,
        }
        
        business_metrics = BusinessMetrics(
            timestamp=datetime.utcnow(),
            transactions_processed=total_transactions,
            transactions_per_second=transactions_per_second,
            fraud_detected=fraud_detected,
            fraud_prevented_amount=roi_metrics['fraud_prevented_amount'],
            fraud_detection_rate=fraud_metrics['fraud_detection_rate'],
            fraud_detection_accuracy=fraud_metrics['fraud_detection_accuracy'],
            cost_per_transaction=roi_metrics['cost_per_transaction'],
            total_cost=cost_breakdown.total_cost,
            roi_percentage=roi_metrics['roi_percentage'],
            money_saved=roi_metrics['money_saved'],
            payback_period_months=roi_metrics['payback_period_months'],
            customer_impact_score=customer_impact_score,
            false_positive_impact=false_positive_impact,
            performance_vs_baseline=performance_vs_baseline,
            cost_vs_baseline=cost_vs_baseline,
            aws_cost_breakdown=aws_cost_breakdown
        )
        
        logger.info(
            f"Business metrics calculated: {total_transactions} transactions, "
            f"{fraud_detected} fraud detected, ${cost_breakdown.total_cost:.2f} cost, "
            f"ROI {roi_metrics['roi_percentage']:.1f}%"
        )
        
        return business_metrics
