#!/usr/bin/env python3
"""
Streaming Infrastructure Configuration

Sets up:
- AWS Kinesis Data Streams for transaction ingestion
- EventBridge for event-driven responses
- Lambda functions for stream processing
- Dead letter queues for failed processing
"""

import json
import boto3
import zipfile
import io
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class KinesisStreamConfig:
    """Configuration for Kinesis Data Stream."""
    stream_name: str
    shard_count: int = 1
    retention_hours: int = 24
    encryption_type: str = 'KMS'
    stream_mode: str = 'PROVISIONED'  # or 'ON_DEMAND'


@dataclass
class EventBridgeRuleConfig:
    """Configuration for EventBridge rule."""
    rule_name: str
    description: str
    event_pattern: Dict
    targets: List[Dict]
    state: str = 'ENABLED'


@dataclass
class LambdaFunctionConfig:
    """Configuration for Lambda function."""
    function_name: str
    description: str
    handler: str
    runtime: str = 'python3.11'
    timeout: int = 60
    memory_size: int = 512
    environment_variables: Dict[str, str] = None
    dead_letter_queue_arn: Optional[str] = None


class StreamingInfrastructureConfigurator:
    """Manages streaming infrastructure configuration."""
    
    def __init__(self, region_name: str = "us-east-1", environment: str = "dev"):
        """Initialize streaming infrastructure configurator."""
        self.region_name = region_name
        self.environment = environment
        self.kinesis_client = boto3.client('kinesis', region_name=region_name)
        self.events_client = boto3.client('events', region_name=region_name)
        self.lambda_client = boto3.client('lambda', region_name=region_name)
        self.sqs_client = boto3.client('sqs', region_name=region_name)
        self.iam_client = boto3.client('iam', region_name=region_name)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        logger.info(f"Initialized Streaming Infrastructure Configurator for {environment} in {region_name}")
    
    def create_kinesis_stream(self, config: KinesisStreamConfig) -> Dict:
        """
        Create Kinesis Data Stream.
        
        Args:
            config: Stream configuration
            
        Returns:
            Stream details
        """
        logger.info(f"Creating Kinesis stream: {config.stream_name}")
        
        try:
            if config.stream_mode == 'PROVISIONED':
                response = self.kinesis_client.create_stream(
                    StreamName=config.stream_name,
                    ShardCount=config.shard_count,
                    StreamModeDetails={'StreamMode': 'PROVISIONED'}
                )
            else:
                response = self.kinesis_client.create_stream(
                    StreamName=config.stream_name,
                    StreamModeDetails={'StreamMode': 'ON_DEMAND'}
                )
            
            # Wait for stream to be active
            logger.info(f"Waiting for stream {config.stream_name} to be active...")
            waiter = self.kinesis_client.get_waiter('stream_exists')
            waiter.wait(StreamName=config.stream_name)
            
            # Enable encryption
            if config.encryption_type == 'KMS':
                self.kinesis_client.start_stream_encryption(
                    StreamName=config.stream_name,
                    EncryptionType='KMS',
                    KeyId='alias/aws/kinesis'
                )
                logger.info(f"Enabled KMS encryption for {config.stream_name}")
            
            # Set retention period
            self.kinesis_client.increase_stream_retention_period(
                StreamName=config.stream_name,
                RetentionPeriodHours=config.retention_hours
            )
            
            # Add tags
            self.kinesis_client.add_tags_to_stream(
                StreamName=config.stream_name,
                Tags={
                    'Environment': self.environment,
                    'Application': 'FraudDetection'
                }
            )
            
            logger.info(f"Created Kinesis stream: {config.stream_name}")
            
            stream_arn = f"arn:aws:kinesis:{self.region_name}:{self.account_id}:stream/{config.stream_name}"
            return {
                'stream_name': config.stream_name,
                'stream_arn': stream_arn,
                'shard_count': config.shard_count
            }
            
        except self.kinesis_client.exceptions.ResourceInUseException:
            logger.info(f"Stream {config.stream_name} already exists")
            stream_arn = f"arn:aws:kinesis:{self.region_name}:{self.account_id}:stream/{config.stream_name}"
            return {
                'stream_name': config.stream_name,
                'stream_arn': stream_arn
            }
        except Exception as e:
            logger.error(f"Error creating Kinesis stream: {str(e)}")
            raise
    
    def create_dead_letter_queue(self, queue_name: str) -> Dict:
        """
        Create SQS dead letter queue.
        
        Args:
            queue_name: Queue name
            
        Returns:
            Queue details
        """
        logger.info(f"Creating dead letter queue: {queue_name}")
        
        try:
            response = self.sqs_client.create_queue(
                QueueName=queue_name,
                Attributes={
                    'MessageRetentionPeriod': '1209600',  # 14 days
                    'VisibilityTimeout': '300',
                    'KmsMasterKeyId': 'alias/aws/sqs',
                    'KmsDataKeyReusePeriodSeconds': '300'
                },
                tags={
                    'Environment': self.environment,
                    'Application': 'FraudDetection'
                }
            )
            
            queue_url = response['QueueUrl']
            
            # Get queue ARN
            attrs = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['QueueArn']
            )
            queue_arn = attrs['Attributes']['QueueArn']
            
            logger.info(f"Created dead letter queue: {queue_name}")
            return {
                'queue_name': queue_name,
                'queue_url': queue_url,
                'queue_arn': queue_arn
            }
            
        except self.sqs_client.exceptions.QueueNameExists:
            logger.info(f"Queue {queue_name} already exists")
            queue_url = self.sqs_client.get_queue_url(QueueName=queue_name)['QueueUrl']
            attrs = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['QueueArn']
            )
            return {
                'queue_name': queue_name,
                'queue_url': queue_url,
                'queue_arn': attrs['Attributes']['QueueArn']
            }
        except Exception as e:
            logger.error(f"Error creating dead letter queue: {str(e)}")
            raise
    
    def create_lambda_function(
        self,
        config: LambdaFunctionConfig,
        role_arn: str,
        code: str
    ) -> Dict:
        """
        Create Lambda function for stream processing.
        
        Args:
            config: Function configuration
            role_arn: IAM role ARN
            code: Function code
            
        Returns:
            Function details
        """
        logger.info(f"Creating Lambda function: {config.function_name}")
        
        # Create deployment package
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', code)
        
        zip_buffer.seek(0)
        
        function_config = {
            'FunctionName': config.function_name,
            'Runtime': config.runtime,
            'Role': role_arn,
            'Handler': config.handler,
            'Code': {'ZipFile': zip_buffer.read()},
            'Description': config.description,
            'Timeout': config.timeout,
            'MemorySize': config.memory_size,
            'Environment': {
                'Variables': config.environment_variables or {}
            },
            'Tags': {
                'Environment': self.environment,
                'Application': 'FraudDetection'
            }
        }
        
        # Add dead letter queue if specified
        if config.dead_letter_queue_arn:
            function_config['DeadLetterConfig'] = {
                'TargetArn': config.dead_letter_queue_arn
            }
        
        try:
            response = self.lambda_client.create_function(**function_config)
            
            logger.info(f"Created Lambda function: {config.function_name}")
            return {
                'function_name': config.function_name,
                'function_arn': response['FunctionArn']
            }
            
        except self.lambda_client.exceptions.ResourceConflictException:
            logger.info(f"Function {config.function_name} already exists, updating...")
            
            # Update function code
            self.lambda_client.update_function_code(
                FunctionName=config.function_name,
                ZipFile=zip_buffer.getvalue()
            )
            
            # Update function configuration
            self.lambda_client.update_function_configuration(
                FunctionName=config.function_name,
                Runtime=config.runtime,
                Role=role_arn,
                Handler=config.handler,
                Description=config.description,
                Timeout=config.timeout,
                MemorySize=config.memory_size,
                Environment={'Variables': config.environment_variables or {}}
            )
            
            response = self.lambda_client.get_function(FunctionName=config.function_name)
            return {
                'function_name': config.function_name,
                'function_arn': response['Configuration']['FunctionArn']
            }
        except Exception as e:
            logger.error(f"Error creating Lambda function: {str(e)}")
            raise
    
    def create_kinesis_event_source_mapping(
        self,
        function_name: str,
        stream_arn: str,
        batch_size: int = 100,
        starting_position: str = 'LATEST'
    ) -> Dict:
        """
        Create event source mapping between Kinesis and Lambda.
        
        Args:
            function_name: Lambda function name
            stream_arn: Kinesis stream ARN
            batch_size: Batch size for processing
            starting_position: Starting position (LATEST or TRIM_HORIZON)
            
        Returns:
            Mapping details
        """
        logger.info(f"Creating event source mapping for {function_name}")
        
        try:
            response = self.lambda_client.create_event_source_mapping(
                EventSourceArn=stream_arn,
                FunctionName=function_name,
                Enabled=True,
                BatchSize=batch_size,
                StartingPosition=starting_position,
                MaximumBatchingWindowInSeconds=5,
                ParallelizationFactor=1,
                MaximumRecordAgeInSeconds=3600,
                BisectBatchOnFunctionError=True,
                MaximumRetryAttempts=3
            )
            
            logger.info(f"Created event source mapping: {response['UUID']}")
            return {
                'uuid': response['UUID'],
                'function_name': function_name,
                'stream_arn': stream_arn
            }
            
        except Exception as e:
            logger.error(f"Error creating event source mapping: {str(e)}")
            raise
    
    def create_eventbridge_rule(self, config: EventBridgeRuleConfig) -> Dict:
        """
        Create EventBridge rule for event-driven responses.
        
        Args:
            config: Rule configuration
            
        Returns:
            Rule details
        """
        logger.info(f"Creating EventBridge rule: {config.rule_name}")
        
        try:
            # Create rule
            response = self.events_client.put_rule(
                Name=config.rule_name,
                Description=config.description,
                EventPattern=json.dumps(config.event_pattern),
                State=config.state,
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Application', 'Value': 'FraudDetection'}
                ]
            )
            
            rule_arn = response['RuleArn']
            
            # Add targets
            if config.targets:
                self.events_client.put_targets(
                    Rule=config.rule_name,
                    Targets=config.targets
                )
            
            logger.info(f"Created EventBridge rule: {config.rule_name}")
            return {
                'rule_name': config.rule_name,
                'rule_arn': rule_arn
            }
            
        except Exception as e:
            logger.error(f"Error creating EventBridge rule: {str(e)}")
            raise
    
    def setup_transaction_ingestion_stream(self) -> Dict:
        """Set up Kinesis stream for transaction ingestion."""
        config = KinesisStreamConfig(
            stream_name=f"fraud-detection-transactions-{self.environment}",
            shard_count=2,
            retention_hours=48,
            stream_mode='ON_DEMAND'
        )
        
        return self.create_kinesis_stream(config)
    
    def setup_fraud_events_stream(self) -> Dict:
        """Set up Kinesis stream for fraud events."""
        config = KinesisStreamConfig(
            stream_name=f"fraud-detection-events-{self.environment}",
            shard_count=1,
            retention_hours=24,
            stream_mode='ON_DEMAND'
        )
        
        return self.create_kinesis_stream(config)
    
    def setup_stream_processor_lambda(self, role_arn: str, dlq_arn: str) -> Dict:
        """Set up Lambda function for stream processing."""
        
        code = '''
import json
import base64
import boto3
import os

dynamodb = boto3.resource('dynamodb')
events = boto3.client('events')

def lambda_handler(event, context):
    """Process Kinesis stream records."""
    
    processed_records = 0
    failed_records = 0
    
    for record in event['Records']:
        try:
            # Decode Kinesis data
            payload = base64.b64decode(record['kinesis']['data'])
            transaction = json.loads(payload)
            
            # Process transaction
            process_transaction(transaction)
            processed_records += 1
            
        except Exception as e:
            print(f"Error processing record: {str(e)}")
            failed_records += 1
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_records,
            'failed': failed_records
        })
    }

def process_transaction(transaction):
    """Process individual transaction."""
    
    # Store in DynamoDB
    table_name = os.environ.get('TRANSACTIONS_TABLE')
    if table_name:
        table = dynamodb.Table(table_name)
        table.put_item(Item=transaction)
    
    # Emit event for fraud detection
    events.put_events(
        Entries=[
            {
                'Source': 'fraud-detection.transaction-processor',
                'DetailType': 'TransactionReceived',
                'Detail': json.dumps(transaction)
            }
        ]
    )
'''
        
        config = LambdaFunctionConfig(
            function_name=f"fraud-detection-stream-processor-{self.environment}",
            description="Process transaction stream from Kinesis",
            handler="lambda_function.lambda_handler",
            timeout=60,
            memory_size=512,
            environment_variables={
                'ENVIRONMENT': self.environment,
                'TRANSACTIONS_TABLE': f"fraud-detection-transactions-{self.environment}"
            },
            dead_letter_queue_arn=dlq_arn
        )
        
        return self.create_lambda_function(config, role_arn, code)
    
    def setup_fraud_alert_lambda(self, role_arn: str, dlq_arn: str) -> Dict:
        """Set up Lambda function for fraud alerts."""
        
        code = '''
import json
import boto3
import os

sns = boto3.client('sns')

def lambda_handler(event, context):
    """Handle fraud detection events and send alerts."""
    
    for record in event['Records']:
        try:
            # Parse event
            detail = json.loads(record['body']) if 'body' in record else record
            
            # Check if fraud detected
            if detail.get('fraud_detected'):
                send_alert(detail)
        
        except Exception as e:
            print(f"Error processing alert: {str(e)}")
            raise
    
    return {'statusCode': 200}

def send_alert(fraud_event):
    """Send fraud alert notification."""
    
    topic_arn = os.environ.get('ALERT_TOPIC_ARN')
    if topic_arn:
        sns.publish(
            TopicArn=topic_arn,
            Subject='Fraud Alert',
            Message=json.dumps(fraud_event, indent=2)
        )
'''
        
        config = LambdaFunctionConfig(
            function_name=f"fraud-detection-alert-handler-{self.environment}",
            description="Handle fraud alerts and notifications",
            handler="lambda_function.lambda_handler",
            timeout=30,
            memory_size=256,
            environment_variables={
                'ENVIRONMENT': self.environment
            },
            dead_letter_queue_arn=dlq_arn
        )
        
        return self.create_lambda_function(config, role_arn, code)
    
    def setup_fraud_detection_eventbridge_rule(self, lambda_arn: str) -> Dict:
        """Set up EventBridge rule for fraud detection events."""
        
        config = EventBridgeRuleConfig(
            rule_name=f"fraud-detection-events-{self.environment}",
            description="Route fraud detection events to processing",
            event_pattern={
                "source": ["fraud-detection.transaction-processor"],
                "detail-type": ["TransactionReceived", "FraudDetected"]
            },
            targets=[
                {
                    'Id': '1',
                    'Arn': lambda_arn
                }
            ]
        )
        
        return self.create_eventbridge_rule(config)
    
    def setup_all_streaming_infrastructure(self, lambda_role_arn: str) -> Dict:
        """
        Set up all streaming infrastructure.
        
        Args:
            lambda_role_arn: IAM role ARN for Lambda functions
            
        Returns:
            Dictionary with all created resources
        """
        logger.info("Setting up all streaming infrastructure")
        
        resources = {
            'kinesis_streams': {},
            'lambda_functions': {},
            'eventbridge_rules': {},
            'dead_letter_queues': {}
        }
        
        # Create dead letter queues
        logger.info("Creating dead letter queues...")
        dlq = self.create_dead_letter_queue(
            f"fraud-detection-dlq-{self.environment}"
        )
        resources['dead_letter_queues']['main'] = dlq
        
        # Create Kinesis streams
        logger.info("Creating Kinesis streams...")
        resources['kinesis_streams']['transactions'] = self.setup_transaction_ingestion_stream()
        resources['kinesis_streams']['events'] = self.setup_fraud_events_stream()
        
        # Create Lambda functions
        logger.info("Creating Lambda functions...")
        resources['lambda_functions']['stream_processor'] = self.setup_stream_processor_lambda(
            lambda_role_arn,
            dlq['queue_arn']
        )
        resources['lambda_functions']['alert_handler'] = self.setup_fraud_alert_lambda(
            lambda_role_arn,
            dlq['queue_arn']
        )
        
        # Create event source mappings
        logger.info("Creating event source mappings...")
        self.create_kinesis_event_source_mapping(
            resources['lambda_functions']['stream_processor']['function_name'],
            resources['kinesis_streams']['transactions']['stream_arn']
        )
        
        # Create EventBridge rules
        logger.info("Creating EventBridge rules...")
        resources['eventbridge_rules']['fraud_detection'] = self.setup_fraud_detection_eventbridge_rule(
            resources['lambda_functions']['alert_handler']['function_arn']
        )
        
        # Add Lambda permissions for EventBridge
        try:
            self.lambda_client.add_permission(
                FunctionName=resources['lambda_functions']['alert_handler']['function_name'],
                StatementId='AllowEventBridgeInvoke',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=resources['eventbridge_rules']['fraud_detection']['rule_arn']
            )
        except self.lambda_client.exceptions.ResourceConflictException:
            logger.info("EventBridge permission already exists")
        
        logger.info("All streaming infrastructure created successfully")
        return resources


def main():
    """Setup streaming infrastructure."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Streaming Infrastructure')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--environment', type=str, default='dev', choices=['dev', 'staging', 'prod'])
    parser.add_argument('--lambda-role-arn', type=str, required=True, help='Lambda execution role ARN')
    
    args = parser.parse_args()
    
    configurator = StreamingInfrastructureConfigurator(
        region_name=args.region,
        environment=args.environment
    )
    
    resources = configurator.setup_all_streaming_infrastructure(args.lambda_role_arn)
    
    print("\n" + "="*80)
    print("STREAMING INFRASTRUCTURE SETUP COMPLETE")
    print("="*80)
    
    print("\n--- Kinesis Streams ---")
    for name, stream in resources['kinesis_streams'].items():
        print(f"  {name}: {stream['stream_name']}")
    
    print("\n--- Lambda Functions ---")
    for name, func in resources['lambda_functions'].items():
        print(f"  {name}: {func['function_name']}")
    
    print("\n--- EventBridge Rules ---")
    for name, rule in resources['eventbridge_rules'].items():
        print(f"  {name}: {rule['rule_name']}")
    
    print("\n--- Dead Letter Queues ---")
    for name, queue in resources['dead_letter_queues'].items():
        print(f"  {name}: {queue['queue_name']}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
