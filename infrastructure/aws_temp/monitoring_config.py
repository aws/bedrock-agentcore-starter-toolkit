#!/usr/bin/env python3
"""
Monitoring and Observability Configuration

Sets up:
- CloudWatch dashboards for system metrics
- CloudWatch Alarms for critical thresholds
- X-Ray tracing for distributed system visibility
- Custom metrics for fraud detection performance
"""

import json
import boto3
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CloudWatchAlarmConfig:
    """Configuration for CloudWatch alarm."""
    alarm_name: str
    description: str
    metric_name: str
    namespace: str
    statistic: str = 'Average'
    period: int = 300
    evaluation_periods: int = 2
    threshold: float = 80.0
    comparison_operator: str = 'GreaterThanThreshold'
    treat_missing_data: str = 'notBreaching'
    dimensions: List[Dict] = field(default_factory=list)
    alarm_actions: List[str] = field(default_factory=list)


@dataclass
class DashboardWidgetConfig:
    """Configuration for dashboard widget."""
    widget_type: str
    title: str
    metrics: List[List]
    width: int = 12
    height: int = 6
    period: int = 300
    stat: str = 'Average'
    region: str = 'us-east-1'


class MonitoringConfigurator:
    """Manages monitoring and observability configuration."""
    
    def __init__(self, region_name: str = "us-east-1", environment: str = "dev"):
        """Initialize monitoring configurator."""
        self.region_name = region_name
        self.environment = environment
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
        self.logs_client = boto3.client('logs', region_name=region_name)
        self.xray_client = boto3.client('xray', region_name=region_name)
        self.sns_client = boto3.client('sns', region_name=region_name)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        logger.info(f"Initialized Monitoring Configurator for {environment} in {region_name}")
    
    def create_sns_topic_for_alarms(self) -> str:
        """
        Create SNS topic for alarm notifications.
        
        Returns:
            Topic ARN
        """
        topic_name = f"fraud-detection-alarms-{self.environment}"
        logger.info(f"Creating SNS topic: {topic_name}")
        
        try:
            response = self.sns_client.create_topic(
                Name=topic_name,
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Application', 'Value': 'FraudDetection'}
                ]
            )
            
            topic_arn = response['TopicArn']
            logger.info(f"Created SNS topic: {topic_arn}")
            return topic_arn
            
        except Exception as e:
            logger.error(f"Error creating SNS topic: {str(e)}")
            raise
    
    def create_cloudwatch_alarm(self, config: CloudWatchAlarmConfig) -> Dict:
        """
        Create CloudWatch alarm.
        
        Args:
            config: Alarm configuration
            
        Returns:
            Alarm details
        """
        logger.info(f"Creating CloudWatch alarm: {config.alarm_name}")
        
        try:
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=config.alarm_name,
                AlarmDescription=config.description,
                MetricName=config.metric_name,
                Namespace=config.namespace,
                Statistic=config.statistic,
                Period=config.period,
                EvaluationPeriods=config.evaluation_periods,
                Threshold=config.threshold,
                ComparisonOperator=config.comparison_operator,
                TreatMissingData=config.treat_missing_data,
                Dimensions=config.dimensions,
                AlarmActions=config.alarm_actions,
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Application', 'Value': 'FraudDetection'}
                ]
            )
            
            logger.info(f"Created CloudWatch alarm: {config.alarm_name}")
            return {
                'alarm_name': config.alarm_name,
                'metric_name': config.metric_name,
                'namespace': config.namespace
            }
            
        except Exception as e:
            logger.error(f"Error creating CloudWatch alarm: {str(e)}")
            raise
    
    def create_dashboard(self, dashboard_name: str, widgets: List[Dict]) -> Dict:
        """
        Create CloudWatch dashboard.
        
        Args:
            dashboard_name: Dashboard name
            widgets: List of widget configurations
            
        Returns:
            Dashboard details
        """
        logger.info(f"Creating CloudWatch dashboard: {dashboard_name}")
        
        dashboard_body = {
            'widgets': widgets
        }
        
        try:
            self.cloudwatch_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            return {
                'dashboard_name': dashboard_name,
                'widget_count': len(widgets)
            }
            
        except Exception as e:
            logger.error(f"Error creating CloudWatch dashboard: {str(e)}")
            raise
    
    def create_custom_metric(
        self,
        namespace: str,
        metric_name: str,
        value: float,
        unit: str = 'None',
        dimensions: List[Dict] = None
    ):
        """
        Put custom metric data to CloudWatch.
        
        Args:
            namespace: Metric namespace
            metric_name: Metric name
            value: Metric value
            unit: Metric unit
            dimensions: Metric dimensions
        """
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit
            }
            
            if dimensions:
                metric_data['Dimensions'] = dimensions
            
            self.cloudwatch_client.put_metric_data(
                Namespace=namespace,
                MetricData=[metric_data]
            )
            
        except Exception as e:
            logger.error(f"Error putting custom metric: {str(e)}")
    
    def enable_xray_tracing(self, lambda_function_names: List[str]):
        """
        Enable X-Ray tracing for Lambda functions.
        
        Args:
            lambda_function_names: List of Lambda function names
        """
        logger.info("Enabling X-Ray tracing for Lambda functions")
        
        lambda_client = boto3.client('lambda', region_name=self.region_name)
        
        for function_name in lambda_function_names:
            try:
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    TracingConfig={'Mode': 'Active'}
                )
                logger.info(f"Enabled X-Ray tracing for {function_name}")
            except Exception as e:
                logger.warning(f"Could not enable X-Ray for {function_name}: {str(e)}")
    
    def create_log_metric_filter(
        self,
        log_group_name: str,
        filter_name: str,
        filter_pattern: str,
        metric_namespace: str,
        metric_name: str,
        metric_value: str = '1'
    ):
        """
        Create CloudWatch Logs metric filter.
        
        Args:
            log_group_name: Log group name
            filter_name: Filter name
            filter_pattern: Filter pattern
            metric_namespace: Metric namespace
            metric_name: Metric name
            metric_value: Metric value
        """
        logger.info(f"Creating log metric filter: {filter_name}")
        
        try:
            self.logs_client.put_metric_filter(
                logGroupName=log_group_name,
                filterName=filter_name,
                filterPattern=filter_pattern,
                metricTransformations=[
                    {
                        'metricName': metric_name,
                        'metricNamespace': metric_namespace,
                        'metricValue': metric_value,
                        'defaultValue': 0
                    }
                ]
            )
            logger.info(f"Created log metric filter: {filter_name}")
        except Exception as e:
            logger.error(f"Error creating log metric filter: {str(e)}")
    
    def setup_lambda_alarms(self, function_names: List[str], alarm_topic_arn: str) -> List[Dict]:
        """Set up alarms for Lambda functions."""
        alarms = []
        
        for function_name in function_names:
            # Error rate alarm
            error_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{function_name}-errors-{self.environment}",
                description=f"High error rate for {function_name}",
                metric_name="Errors",
                namespace="AWS/Lambda",
                statistic="Sum",
                period=300,
                evaluation_periods=2,
                threshold=10,
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(error_alarm))
            
            # Duration alarm
            duration_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{function_name}-duration-{self.environment}",
                description=f"High duration for {function_name}",
                metric_name="Duration",
                namespace="AWS/Lambda",
                statistic="Average",
                period=300,
                evaluation_periods=2,
                threshold=30000,  # 30 seconds
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(duration_alarm))
            
            # Throttle alarm
            throttle_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{function_name}-throttles-{self.environment}",
                description=f"Throttling detected for {function_name}",
                metric_name="Throttles",
                namespace="AWS/Lambda",
                statistic="Sum",
                period=300,
                evaluation_periods=1,
                threshold=1,
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(throttle_alarm))
        
        return alarms
    
    def setup_kinesis_alarms(self, stream_names: List[str], alarm_topic_arn: str) -> List[Dict]:
        """Set up alarms for Kinesis streams."""
        alarms = []
        
        for stream_name in stream_names:
            # Iterator age alarm
            iterator_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{stream_name}-iterator-age-{self.environment}",
                description=f"High iterator age for {stream_name}",
                metric_name="GetRecords.IteratorAgeMilliseconds",
                namespace="AWS/Kinesis",
                statistic="Maximum",
                period=300,
                evaluation_periods=2,
                threshold=60000,  # 1 minute
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'StreamName', 'Value': stream_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(iterator_alarm))
            
            # Write throughput alarm
            write_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{stream_name}-write-throttle-{self.environment}",
                description=f"Write throttling for {stream_name}",
                metric_name="WriteProvisionedThroughputExceeded",
                namespace="AWS/Kinesis",
                statistic="Sum",
                period=300,
                evaluation_periods=1,
                threshold=1,
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'StreamName', 'Value': stream_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(write_alarm))
        
        return alarms
    
    def setup_dynamodb_alarms(self, table_names: List[str], alarm_topic_arn: str) -> List[Dict]:
        """Set up alarms for DynamoDB tables."""
        alarms = []
        
        for table_name in table_names:
            # Read throttle alarm
            read_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{table_name}-read-throttle-{self.environment}",
                description=f"Read throttling for {table_name}",
                metric_name="ReadThrottleEvents",
                namespace="AWS/DynamoDB",
                statistic="Sum",
                period=300,
                evaluation_periods=1,
                threshold=1,
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'TableName', 'Value': table_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(read_alarm))
            
            # Write throttle alarm
            write_alarm = CloudWatchAlarmConfig(
                alarm_name=f"{table_name}-write-throttle-{self.environment}",
                description=f"Write throttling for {table_name}",
                metric_name="WriteThrottleEvents",
                namespace="AWS/DynamoDB",
                statistic="Sum",
                period=300,
                evaluation_periods=1,
                threshold=1,
                comparison_operator="GreaterThanThreshold",
                dimensions=[{'Name': 'TableName', 'Value': table_name}],
                alarm_actions=[alarm_topic_arn]
            )
            alarms.append(self.create_cloudwatch_alarm(write_alarm))
        
        return alarms
    
    def create_fraud_detection_dashboard(self) -> Dict:
        """Create comprehensive fraud detection dashboard."""
        
        dashboard_name = f"fraud-detection-{self.environment}"
        
        widgets = [
            # Transaction processing metrics
            {
                'type': 'metric',
                'x': 0,
                'y': 0,
                'width': 12,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['FraudDetection', 'TransactionsProcessed', {'stat': 'Sum'}],
                        ['.', 'FraudDetected', {'stat': 'Sum'}],
                        ['.', 'FalsePositives', {'stat': 'Sum'}]
                    ],
                    'period': 300,
                    'stat': 'Sum',
                    'region': self.region_name,
                    'title': 'Transaction Processing',
                    'yAxis': {'left': {'label': 'Count'}}
                }
            },
            # Detection accuracy
            {
                'type': 'metric',
                'x': 12,
                'y': 0,
                'width': 12,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['FraudDetection', 'DetectionAccuracy', {'stat': 'Average'}],
                        ['.', 'ConfidenceScore', {'stat': 'Average'}]
                    ],
                    'period': 300,
                    'stat': 'Average',
                    'region': self.region_name,
                    'title': 'Detection Accuracy',
                    'yAxis': {'left': {'min': 0, 'max': 100}}
                }
            },
            # Processing latency
            {
                'type': 'metric',
                'x': 0,
                'y': 6,
                'width': 12,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['FraudDetection', 'ProcessingLatency', {'stat': 'Average'}],
                        ['...', {'stat': 'p99'}]
                    ],
                    'period': 300,
                    'stat': 'Average',
                    'region': self.region_name,
                    'title': 'Processing Latency (ms)',
                    'yAxis': {'left': {'label': 'Milliseconds'}}
                }
            },
            # Lambda function errors
            {
                'type': 'metric',
                'x': 12,
                'y': 6,
                'width': 12,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['AWS/Lambda', 'Errors', {'stat': 'Sum'}],
                        ['.', 'Throttles', {'stat': 'Sum'}]
                    ],
                    'period': 300,
                    'stat': 'Sum',
                    'region': self.region_name,
                    'title': 'Lambda Errors & Throttles'
                }
            },
            # Kinesis stream metrics
            {
                'type': 'metric',
                'x': 0,
                'y': 12,
                'width': 12,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['AWS/Kinesis', 'IncomingRecords', {'stat': 'Sum'}],
                        ['.', 'GetRecords.IteratorAgeMilliseconds', {'stat': 'Maximum'}]
                    ],
                    'period': 300,
                    'stat': 'Average',
                    'region': self.region_name,
                    'title': 'Kinesis Stream Health'
                }
            },
            # DynamoDB metrics
            {
                'type': 'metric',
                'x': 12,
                'y': 12,
                'width': 12,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['AWS/DynamoDB', 'ConsumedReadCapacityUnits', {'stat': 'Sum'}],
                        ['.', 'ConsumedWriteCapacityUnits', {'stat': 'Sum'}]
                    ],
                    'period': 300,
                    'stat': 'Sum',
                    'region': self.region_name,
                    'title': 'DynamoDB Capacity'
                }
            }
        ]
        
        return self.create_dashboard(dashboard_name, widgets)
    
    def setup_custom_fraud_metrics(self):
        """Set up custom metric filters for fraud detection."""
        
        log_groups = [
            f"/aws/lambda/fraud-detection-stream-processor-{self.environment}",
            f"/aws/lambda/fraud-detection-alert-handler-{self.environment}"
        ]
        
        for log_group in log_groups:
            # Fraud detected metric
            self.create_log_metric_filter(
                log_group_name=log_group,
                filter_name="FraudDetected",
                filter_pattern='[time, request_id, level = "INFO", msg = "Fraud detected*"]',
                metric_namespace="FraudDetection",
                metric_name="FraudDetected"
            )
            
            # Processing errors metric
            self.create_log_metric_filter(
                log_group_name=log_group,
                filter_name="ProcessingErrors",
                filter_pattern='[time, request_id, level = "ERROR", ...]',
                metric_namespace="FraudDetection",
                metric_name="ProcessingErrors"
            )
    
    def setup_all_monitoring(
        self,
        lambda_function_names: List[str],
        kinesis_stream_names: List[str],
        dynamodb_table_names: List[str]
    ) -> Dict:
        """
        Set up all monitoring and observability.
        
        Args:
            lambda_function_names: List of Lambda function names
            kinesis_stream_names: List of Kinesis stream names
            dynamodb_table_names: List of DynamoDB table names
            
        Returns:
            Dictionary with all created monitoring resources
        """
        logger.info("Setting up all monitoring and observability")
        
        resources = {
            'sns_topics': {},
            'alarms': {},
            'dashboards': {},
            'xray_enabled': []
        }
        
        # Create SNS topic for alarms
        logger.info("Creating SNS topic for alarms...")
        alarm_topic_arn = self.create_sns_topic_for_alarms()
        resources['sns_topics']['alarms'] = alarm_topic_arn
        
        # Set up alarms
        logger.info("Creating CloudWatch alarms...")
        resources['alarms']['lambda'] = self.setup_lambda_alarms(
            lambda_function_names,
            alarm_topic_arn
        )
        resources['alarms']['kinesis'] = self.setup_kinesis_alarms(
            kinesis_stream_names,
            alarm_topic_arn
        )
        resources['alarms']['dynamodb'] = self.setup_dynamodb_alarms(
            dynamodb_table_names,
            alarm_topic_arn
        )
        
        # Create dashboard
        logger.info("Creating CloudWatch dashboard...")
        resources['dashboards']['main'] = self.create_fraud_detection_dashboard()
        
        # Enable X-Ray tracing
        logger.info("Enabling X-Ray tracing...")
        self.enable_xray_tracing(lambda_function_names)
        resources['xray_enabled'] = lambda_function_names
        
        # Set up custom metrics
        logger.info("Setting up custom metric filters...")
        self.setup_custom_fraud_metrics()
        
        logger.info("All monitoring and observability configured successfully")
        return resources


def main():
    """Setup monitoring and observability."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Monitoring and Observability')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--environment', type=str, default='dev', choices=['dev', 'staging', 'prod'])
    
    args = parser.parse_args()
    
    configurator = MonitoringConfigurator(
        region_name=args.region,
        environment=args.environment
    )
    
    # Example resource names (should be passed from infrastructure setup)
    lambda_functions = [
        f"fraud-detection-stream-processor-{args.environment}",
        f"fraud-detection-alert-handler-{args.environment}"
    ]
    
    kinesis_streams = [
        f"fraud-detection-transactions-{args.environment}",
        f"fraud-detection-events-{args.environment}"
    ]
    
    dynamodb_tables = [
        f"fraud-detection-transactions-{args.environment}",
        f"fraud-detection-decisions-{args.environment}",
        f"fraud-detection-user-profiles-{args.environment}",
        f"fraud-detection-patterns-{args.environment}"
    ]
    
    resources = configurator.setup_all_monitoring(
        lambda_functions,
        kinesis_streams,
        dynamodb_tables
    )
    
    print("\n" + "="*80)
    print("MONITORING AND OBSERVABILITY SETUP COMPLETE")
    print("="*80)
    
    print("\n--- SNS Topics ---")
    for name, arn in resources['sns_topics'].items():
        print(f"  {name}: {arn}")
    
    print("\n--- CloudWatch Alarms ---")
    for category, alarms in resources['alarms'].items():
        print(f"  {category}: {len(alarms)} alarms created")
    
    print("\n--- Dashboards ---")
    for name, dashboard in resources['dashboards'].items():
        print(f"  {name}: {dashboard['dashboard_name']}")
    
    print("\n--- X-Ray Tracing ---")
    print(f"  Enabled for {len(resources['xray_enabled'])} Lambda functions")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
