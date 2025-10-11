#!/usr/bin/env python3
"""
Data Storage Infrastructure Configuration

Sets up:
- DynamoDB tables for transaction history and memory
- S3 buckets for audit logs and decision trails
- Data lifecycle policies and retention rules
- Encryption at rest and in transit
"""

import json
import boto3
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DynamoDBTableConfig:
    """Configuration for DynamoDB table."""
    table_name: str
    partition_key: str
    partition_key_type: str = 'S'  # S=String, N=Number, B=Binary
    sort_key: Optional[str] = None
    sort_key_type: str = 'S'
    billing_mode: str = 'PAY_PER_REQUEST'  # or 'PROVISIONED'
    read_capacity: int = 5
    write_capacity: int = 5
    ttl_attribute: Optional[str] = None
    stream_enabled: bool = False
    stream_view_type: str = 'NEW_AND_OLD_IMAGES'
    global_secondary_indexes: List[Dict] = None


@dataclass
class S3BucketConfig:
    """Configuration for S3 bucket."""
    bucket_name: str
    versioning_enabled: bool = True
    lifecycle_rules: List[Dict] = None
    encryption_type: str = 'AES256'  # or 'aws:kms'
    kms_key_id: Optional[str] = None
    public_access_blocked: bool = True
    logging_enabled: bool = True
    logging_target_bucket: Optional[str] = None


class DataStorageConfigurator:
    """Manages data storage infrastructure configuration."""
    
    def __init__(self, region_name: str = "us-east-1", environment: str = "dev"):
        """Initialize data storage configurator."""
        self.region_name = region_name
        self.environment = environment
        self.dynamodb_client = boto3.client('dynamodb', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        logger.info(f"Initialized Data Storage Configurator for {environment} in {region_name}")
    
    def create_dynamodb_table(self, config: DynamoDBTableConfig) -> Dict:
        """
        Create DynamoDB table with encryption and streams.
        
        Args:
            config: Table configuration
            
        Returns:
            Table details
        """
        logger.info(f"Creating DynamoDB table: {config.table_name}")
        
        # Key schema
        key_schema = [
            {'AttributeName': config.partition_key, 'KeyType': 'HASH'}
        ]
        
        attribute_definitions = [
            {'AttributeName': config.partition_key, 'AttributeType': config.partition_key_type}
        ]
        
        if config.sort_key:
            key_schema.append({'AttributeName': config.sort_key, 'KeyType': 'RANGE'})
            attribute_definitions.append(
                {'AttributeName': config.sort_key, 'AttributeType': config.sort_key_type}
            )
        
        # Table creation parameters
        table_params = {
            'TableName': config.table_name,
            'KeySchema': key_schema,
            'AttributeDefinitions': attribute_definitions,
            'BillingMode': config.billing_mode,
            'SSESpecification': {
                'Enabled': True,
                'SSEType': 'KMS'
            },
            'Tags': [
                {'Key': 'Environment', 'Value': self.environment},
                {'Key': 'Application', 'Value': 'FraudDetection'}
            ]
        }
        
        # Add provisioned throughput if needed
        if config.billing_mode == 'PROVISIONED':
            table_params['ProvisionedThroughput'] = {
                'ReadCapacityUnits': config.read_capacity,
                'WriteCapacityUnits': config.write_capacity
            }
        
        # Add stream configuration
        if config.stream_enabled:
            table_params['StreamSpecification'] = {
                'StreamEnabled': True,
                'StreamViewType': config.stream_view_type
            }
        
        # Add global secondary indexes
        if config.global_secondary_indexes:
            table_params['GlobalSecondaryIndexes'] = config.global_secondary_indexes
        
        try:
            response = self.dynamodb_client.create_table(**table_params)
            
            # Wait for table to be active
            logger.info(f"Waiting for table {config.table_name} to be active...")
            waiter = self.dynamodb_client.get_waiter('table_exists')
            waiter.wait(TableName=config.table_name)
            
            # Enable TTL if specified
            if config.ttl_attribute:
                self._enable_ttl(config.table_name, config.ttl_attribute)
            
            logger.info(f"Created DynamoDB table: {config.table_name}")
            return response['TableDescription']
            
        except self.dynamodb_client.exceptions.ResourceInUseException:
            logger.info(f"Table {config.table_name} already exists")
            response = self.dynamodb_client.describe_table(TableName=config.table_name)
            return response['Table']
        except Exception as e:
            logger.error(f"Error creating DynamoDB table: {str(e)}")
            raise
    
    def _enable_ttl(self, table_name: str, ttl_attribute: str):
        """Enable TTL on DynamoDB table."""
        try:
            self.dynamodb_client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': ttl_attribute
                }
            )
            logger.info(f"Enabled TTL on {table_name} with attribute {ttl_attribute}")
        except Exception as e:
            logger.warning(f"Could not enable TTL: {str(e)}")
    
    def create_s3_bucket(self, config: S3BucketConfig) -> Dict:
        """
        Create S3 bucket with encryption and lifecycle policies.
        
        Args:
            config: Bucket configuration
            
        Returns:
            Bucket details
        """
        logger.info(f"Creating S3 bucket: {config.bucket_name}")
        
        try:
            # Create bucket
            if self.region_name == 'us-east-1':
                self.s3_client.create_bucket(Bucket=config.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=config.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region_name}
                )
            
            logger.info(f"Created S3 bucket: {config.bucket_name}")
            
            # Configure bucket
            self._configure_bucket_encryption(config)
            self._configure_bucket_versioning(config)
            self._configure_bucket_lifecycle(config)
            self._configure_bucket_public_access(config)
            
            if config.logging_enabled:
                self._configure_bucket_logging(config)
            
            # Add tags
            self.s3_client.put_bucket_tagging(
                Bucket=config.bucket_name,
                Tagging={
                    'TagSet': [
                        {'Key': 'Environment', 'Value': self.environment},
                        {'Key': 'Application', 'Value': 'FraudDetection'}
                    ]
                }
            )
            
            return {'bucket_name': config.bucket_name, 'region': self.region_name}
            
        except self.s3_client.exceptions.BucketAlreadyOwnedByYou:
            logger.info(f"Bucket {config.bucket_name} already exists")
            return {'bucket_name': config.bucket_name, 'region': self.region_name}
        except Exception as e:
            logger.error(f"Error creating S3 bucket: {str(e)}")
            raise
    
    def _configure_bucket_encryption(self, config: S3BucketConfig):
        """Configure bucket encryption."""
        encryption_config = {
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': config.encryption_type
                    },
                    'BucketKeyEnabled': True
                }
            ]
        }
        
        if config.encryption_type == 'aws:kms' and config.kms_key_id:
            encryption_config['Rules'][0]['ApplyServerSideEncryptionByDefault']['KMSMasterKeyID'] = config.kms_key_id
        
        self.s3_client.put_bucket_encryption(
            Bucket=config.bucket_name,
            ServerSideEncryptionConfiguration=encryption_config
        )
        logger.info(f"Configured encryption for {config.bucket_name}")
    
    def _configure_bucket_versioning(self, config: S3BucketConfig):
        """Configure bucket versioning."""
        if config.versioning_enabled:
            self.s3_client.put_bucket_versioning(
                Bucket=config.bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            logger.info(f"Enabled versioning for {config.bucket_name}")
    
    def _configure_bucket_lifecycle(self, config: S3BucketConfig):
        """Configure bucket lifecycle policies."""
        if not config.lifecycle_rules:
            # Default lifecycle rules
            config.lifecycle_rules = [
                {
                    'Id': 'DeleteOldVersions',
                    'Status': 'Enabled',
                    'NoncurrentVersionExpiration': {'NoncurrentDays': 90}
                },
                {
                    'Id': 'TransitionToIA',
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ]
                }
            ]
        
        self.s3_client.put_bucket_lifecycle_configuration(
            Bucket=config.bucket_name,
            LifecycleConfiguration={'Rules': config.lifecycle_rules}
        )
        logger.info(f"Configured lifecycle policies for {config.bucket_name}")
    
    def _configure_bucket_public_access(self, config: S3BucketConfig):
        """Configure bucket public access block."""
        if config.public_access_blocked:
            self.s3_client.put_public_access_block(
                Bucket=config.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            logger.info(f"Configured public access block for {config.bucket_name}")
    
    def _configure_bucket_logging(self, config: S3BucketConfig):
        """Configure bucket logging."""
        target_bucket = config.logging_target_bucket or f"{config.bucket_name}-logs"
        
        try:
            self.s3_client.put_bucket_logging(
                Bucket=config.bucket_name,
                BucketLoggingStatus={
                    'LoggingEnabled': {
                        'TargetBucket': target_bucket,
                        'TargetPrefix': f'{config.bucket_name}/'
                    }
                }
            )
            logger.info(f"Configured logging for {config.bucket_name}")
        except Exception as e:
            logger.warning(f"Could not configure logging: {str(e)}")
    
    def setup_transaction_history_table(self) -> Dict:
        """Create DynamoDB table for transaction history."""
        config = DynamoDBTableConfig(
            table_name=f"fraud-detection-transactions-{self.environment}",
            partition_key="transaction_id",
            sort_key="timestamp",
            sort_key_type="N",
            stream_enabled=True,
            ttl_attribute="expiration_time",
            global_secondary_indexes=[
                {
                    'IndexName': 'UserIdIndex',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        )
        
        # Add user_id to attribute definitions for GSI
        table = self.create_dynamodb_table(config)
        return table
    
    def setup_decision_context_table(self) -> Dict:
        """Create DynamoDB table for decision context and memory."""
        config = DynamoDBTableConfig(
            table_name=f"fraud-detection-decisions-{self.environment}",
            partition_key="decision_id",
            sort_key="timestamp",
            sort_key_type="N",
            stream_enabled=True,
            ttl_attribute="expiration_time"
        )
        
        return self.create_dynamodb_table(config)
    
    def setup_user_profiles_table(self) -> Dict:
        """Create DynamoDB table for user behavior profiles."""
        config = DynamoDBTableConfig(
            table_name=f"fraud-detection-user-profiles-{self.environment}",
            partition_key="user_id",
            stream_enabled=True
        )
        
        return self.create_dynamodb_table(config)
    
    def setup_fraud_patterns_table(self) -> Dict:
        """Create DynamoDB table for learned fraud patterns."""
        config = DynamoDBTableConfig(
            table_name=f"fraud-detection-patterns-{self.environment}",
            partition_key="pattern_id",
            sort_key="version",
            sort_key_type="N",
            stream_enabled=True
        )
        
        return self.create_dynamodb_table(config)
    
    def setup_audit_logs_bucket(self) -> Dict:
        """Create S3 bucket for audit logs."""
        config = S3BucketConfig(
            bucket_name=f"fraud-detection-audit-logs-{self.environment}-{self.account_id}",
            versioning_enabled=True,
            encryption_type='aws:kms',
            lifecycle_rules=[
                {
                    'Id': 'RetainAuditLogs',
                    'Status': 'Enabled',
                    'Transitions': [
                        {'Days': 90, 'StorageClass': 'GLACIER'},
                        {'Days': 365, 'StorageClass': 'DEEP_ARCHIVE'}
                    ]
                }
            ]
        )
        
        return self.create_s3_bucket(config)
    
    def setup_decision_trails_bucket(self) -> Dict:
        """Create S3 bucket for decision trails."""
        config = S3BucketConfig(
            bucket_name=f"fraud-detection-decision-trails-{self.environment}-{self.account_id}",
            versioning_enabled=True,
            lifecycle_rules=[
                {
                    'Id': 'TransitionDecisionTrails',
                    'Status': 'Enabled',
                    'Transitions': [
                        {'Days': 30, 'StorageClass': 'STANDARD_IA'},
                        {'Days': 180, 'StorageClass': 'GLACIER'}
                    ]
                }
            ]
        )
        
        return self.create_s3_bucket(config)
    
    def setup_model_artifacts_bucket(self) -> Dict:
        """Create S3 bucket for ML model artifacts."""
        config = S3BucketConfig(
            bucket_name=f"fraud-detection-models-{self.environment}-{self.account_id}",
            versioning_enabled=True
        )
        
        return self.create_s3_bucket(config)
    
    def setup_all_storage(self) -> Dict:
        """
        Set up all data storage infrastructure.
        
        Returns:
            Dictionary with all created resources
        """
        logger.info("Setting up all data storage infrastructure")
        
        resources = {
            'dynamodb_tables': {},
            's3_buckets': {}
        }
        
        # Create DynamoDB tables
        logger.info("Creating DynamoDB tables...")
        resources['dynamodb_tables']['transactions'] = self.setup_transaction_history_table()
        resources['dynamodb_tables']['decisions'] = self.setup_decision_context_table()
        resources['dynamodb_tables']['user_profiles'] = self.setup_user_profiles_table()
        resources['dynamodb_tables']['fraud_patterns'] = self.setup_fraud_patterns_table()
        
        # Create S3 buckets
        logger.info("Creating S3 buckets...")
        resources['s3_buckets']['audit_logs'] = self.setup_audit_logs_bucket()
        resources['s3_buckets']['decision_trails'] = self.setup_decision_trails_bucket()
        resources['s3_buckets']['model_artifacts'] = self.setup_model_artifacts_bucket()
        
        logger.info("All data storage infrastructure created successfully")
        return resources


def main():
    """Setup data storage infrastructure."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Data Storage Infrastructure')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--environment', type=str, default='dev', choices=['dev', 'staging', 'prod'])
    
    args = parser.parse_args()
    
    configurator = DataStorageConfigurator(
        region_name=args.region,
        environment=args.environment
    )
    
    resources = configurator.setup_all_storage()
    
    print("\n" + "="*80)
    print("DATA STORAGE INFRASTRUCTURE SETUP COMPLETE")
    print("="*80)
    
    print("\n--- DynamoDB Tables ---")
    for name, table in resources['dynamodb_tables'].items():
        print(f"  {name}: {table['TableName']}")
    
    print("\n--- S3 Buckets ---")
    for name, bucket in resources['s3_buckets'].items():
        print(f"  {name}: {bucket['bucket_name']}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
