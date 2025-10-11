#!/usr/bin/env python3
"""
AWS CDK Application for Fraud Detection System

Defines complete infrastructure as code using AWS CDK.
"""

from aws_cdk import (
    App, Stack, Environment,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_kinesis as kinesis,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sqs as sqs,
    Duration, RemovalPolicy
)
from constructs import Construct


class FraudDetectionStack(Stack):
    """Main stack for fraud detection system."""
    
    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = env_name
        
        # Create resources
        self.create_dynamodb_tables()
        self.create_s3_buckets()
        self.create_kinesis_streams()
        self.create_lambda_functions()
        self.create_event_rules()
        self.create_monitoring()
    
    def create_dynamodb_tables(self):
        """Create DynamoDB tables."""
        
        # Transactions table
        self.transactions_table = dynamodb.Table(
            self, f"TransactionsTable-{self.env_name}",
            table_name=f"fraud-detection-transactions-{self.env_name}",
            partition_key=dynamodb.Attribute(
                name="transaction_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            time_to_live_attribute="expiration_time",
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
        
        # Add GSI for user_id
        self.transactions_table.add_global_secondary_index(
            index_name="UserIdIndex",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            )
        )
        
        # Decisions table
        self.decisions_table = dynamodb.Table(
            self, f"DecisionsTable-{self.env_name}",
            table_name=f"fraud-detection-decisions-{self.env_name}",
            partition_key=dynamodb.Attribute(
                name="decision_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            time_to_live_attribute="expiration_time",
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
        
        # User profiles table
        self.user_profiles_table = dynamodb.Table(
            self, f"UserProfilesTable-{self.env_name}",
            table_name=f"fraud-detection-user-profiles-{self.env_name}",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
        
        # Fraud patterns table
        self.fraud_patterns_table = dynamodb.Table(
            self, f"FraudPatternsTable-{self.env_name}",
            table_name=f"fraud-detection-patterns-{self.env_name}",
            partition_key=dynamodb.Attribute(
                name="pattern_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="version",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
    
    def create_s3_buckets(self):
        """Create S3 buckets."""
        
        # Audit logs bucket
        self.audit_logs_bucket = s3.Bucket(
            self, f"AuditLogsBucket-{self.env_name}",
            bucket_name=f"fraud-detection-audit-logs-{self.env_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
        
        # Decision trails bucket
        self.decision_trails_bucket = s3.Bucket(
            self, f"DecisionTrailsBucket-{self.env_name}",
            bucket_name=f"fraud-detection-decision-trails-{self.env_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.STANDARD_IA,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(180)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
        
        # Model artifacts bucket
        self.model_artifacts_bucket = s3.Bucket(
            self, f"ModelArtifactsBucket-{self.env_name}",
            bucket_name=f"fraud-detection-models-{self.env_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
    
    def create_kinesis_streams(self):
        """Create Kinesis streams."""
        
        # Transactions stream
        self.transactions_stream = kinesis.Stream(
            self, f"TransactionsStream-{self.env_name}",
            stream_name=f"fraud-detection-transactions-{self.env_name}",
            stream_mode=kinesis.StreamMode.ON_DEMAND,
            encryption=kinesis.StreamEncryption.MANAGED,
            retention_period=Duration.hours(48)
        )
        
        # Events stream
        self.events_stream = kinesis.Stream(
            self, f"EventsStream-{self.env_name}",
            stream_name=f"fraud-detection-events-{self.env_name}",
            stream_mode=kinesis.StreamMode.ON_DEMAND,
            encryption=kinesis.StreamEncryption.MANAGED,
            retention_period=Duration.hours(24)
        )
    
    def create_lambda_functions(self):
        """Create Lambda functions."""
        
        # Create Lambda execution role
        lambda_role = iam.Role(
            self, f"LambdaExecutionRole-{self.env_name}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Grant permissions
        self.transactions_table.grant_read_write_data(lambda_role)
        self.decisions_table.grant_read_write_data(lambda_role)
        self.user_profiles_table.grant_read_write_data(lambda_role)
        self.fraud_patterns_table.grant_read_write_data(lambda_role)
        self.audit_logs_bucket.grant_read_write(lambda_role)
        self.decision_trails_bucket.grant_read_write(lambda_role)
        
        # Stream processor Lambda
        self.stream_processor = lambda_.Function(
            self, f"StreamProcessor-{self.env_name}",
            function_name=f"fraud-detection-stream-processor-{self.env_name}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/stream_processor"),
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.env_name,
                "TRANSACTIONS_TABLE": self.transactions_table.table_name,
                "DECISIONS_TABLE": self.decisions_table.table_name
            },
            tracing=lambda_.Tracing.ACTIVE
        )
        
        # Add Kinesis event source
        self.stream_processor.add_event_source_mapping(
            f"KinesisEventSource-{self.env_name}",
            event_source_arn=self.transactions_stream.stream_arn,
            batch_size=100,
            starting_position=lambda_.StartingPosition.LATEST,
            max_batching_window=Duration.seconds(5)
        )
        
        # Alert handler Lambda
        self.alert_handler = lambda_.Function(
            self, f"AlertHandler-{self.env_name}",
            function_name=f"fraud-detection-alert-handler-{self.env_name}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/alert_handler"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.env_name
            },
            tracing=lambda_.Tracing.ACTIVE
        )
    
    def create_event_rules(self):
        """Create EventBridge rules."""
        
        # Fraud detection events rule
        fraud_events_rule = events.Rule(
            self, f"FraudEventsRule-{self.env_name}",
            rule_name=f"fraud-detection-events-{self.env_name}",
            event_pattern=events.EventPattern(
                source=["fraud-detection.transaction-processor"],
                detail_type=["TransactionReceived", "FraudDetected"]
            )
        )
        
        # Add Lambda target
        fraud_events_rule.add_target(
            targets.LambdaFunction(self.alert_handler)
        )
    
    def create_monitoring(self):
        """Create monitoring resources."""
        
        # SNS topic for alarms
        self.alarm_topic = sns.Topic(
            self, f"AlarmTopic-{self.env_name}",
            topic_name=f"fraud-detection-alarms-{self.env_name}",
            display_name="Fraud Detection System Alarms"
        )
        
        # Dead letter queue
        self.dlq = sqs.Queue(
            self, f"DeadLetterQueue-{self.env_name}",
            queue_name=f"fraud-detection-dlq-{self.env_name}",
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            retention_period=Duration.days(14)
        )
        
        # CloudWatch alarms
        self.create_alarms()
    
    def create_alarms(self):
        """Create CloudWatch alarms."""
        
        # Lambda errors alarm
        cloudwatch.Alarm(
            self, f"StreamProcessorErrorsAlarm-{self.env_name}",
            alarm_name=f"fraud-detection-stream-processor-errors-{self.env_name}",
            metric=self.stream_processor.metric_errors(),
            threshold=10,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        ).add_alarm_action(
            cloudwatch_actions.SnsAction(self.alarm_topic)
        )
        
        # Lambda duration alarm
        cloudwatch.Alarm(
            self, f"StreamProcessorDurationAlarm-{self.env_name}",
            alarm_name=f"fraud-detection-stream-processor-duration-{self.env_name}",
            metric=self.stream_processor.metric_duration(),
            threshold=30000,  # 30 seconds
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        ).add_alarm_action(
            cloudwatch_actions.SnsAction(self.alarm_topic)
        )
        
        # Kinesis iterator age alarm
        cloudwatch.Alarm(
            self, f"TransactionsStreamIteratorAgeAlarm-{self.env_name}",
            alarm_name=f"fraud-detection-transactions-iterator-age-{self.env_name}",
            metric=cloudwatch.Metric(
                namespace="AWS/Kinesis",
                metric_name="GetRecords.IteratorAgeMilliseconds",
                dimensions_map={
                    "StreamName": self.transactions_stream.stream_name
                },
                statistic="Maximum"
            ),
            threshold=60000,  # 1 minute
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        ).add_alarm_action(
            cloudwatch_actions.SnsAction(self.alarm_topic)
        )


# CDK App
app = App()

# Get environment from context
env_name = app.node.try_get_context("environment") or "dev"
aws_env = Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
)

# Create stack
FraudDetectionStack(
    app,
    f"FraudDetectionStack-{env_name}",
    env_name=env_name,
    env=aws_env,
    description=f"Fraud Detection System Infrastructure ({env_name})"
)

app.synth()
