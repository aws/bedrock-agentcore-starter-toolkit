"""
DynamoDB configuration and table setup for the memory system.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DynamoDBConfig:
    """Configuration and setup for DynamoDB tables."""
    
    def __init__(self, region_name: str = 'us-east-1', endpoint_url: str = None):
        """
        Initialize DynamoDB configuration.
        
        Args:
            region_name: AWS region for DynamoDB
            endpoint_url: Optional endpoint URL for local DynamoDB
        """
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        
        # Initialize DynamoDB client and resource
        session = boto3.Session()
        
        if endpoint_url:
            # For local development
            self.dynamodb = session.resource(
                'dynamodb',
                region_name=region_name,
                endpoint_url=endpoint_url
            )
            self.client = session.client(
                'dynamodb',
                region_name=region_name,
                endpoint_url=endpoint_url
            )
        else:
            # For AWS deployment
            self.dynamodb = session.resource('dynamodb', region_name=region_name)
            self.client = session.client('dynamodb', region_name=region_name)
    
    def get_table_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get DynamoDB table definitions for the memory system."""
        return {
            'TransactionHistory': {
                'TableName': 'fraud-detection-transaction-history',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                    {'AttributeName': 'transaction_id', 'AttributeType': 'S'},
                    {'AttributeName': 'merchant', 'AttributeType': 'S'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'TransactionIdIndex',
                        'KeySchema': [
                            {'AttributeName': 'transaction_id', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    },
                    {
                        'IndexName': 'MerchantIndex',
                        'KeySchema': [
                            {'AttributeName': 'merchant', 'KeyType': 'HASH'},
                            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            
            'DecisionContext': {
                'TableName': 'fraud-detection-decision-context',
                'KeySchema': [
                    {'AttributeName': 'transaction_id', 'KeyType': 'HASH'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'transaction_id', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'UserDecisionIndex',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            
            'UserBehaviorProfiles': {
                'TableName': 'fraud-detection-user-profiles',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            
            'FraudPatterns': {
                'TableName': 'fraud-detection-patterns',
                'KeySchema': [
                    {'AttributeName': 'pattern_id', 'KeyType': 'HASH'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'pattern_id', 'AttributeType': 'S'},
                    {'AttributeName': 'pattern_type', 'AttributeType': 'S'},
                    {'AttributeName': 'last_seen', 'AttributeType': 'S'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'PatternTypeIndex',
                        'KeySchema': [
                            {'AttributeName': 'pattern_type', 'KeyType': 'HASH'},
                            {'AttributeName': 'last_seen', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'BillingMode': 'PAY_PER_REQUEST'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            
            'RiskProfiles': {
                'TableName': 'fraud-detection-risk-profiles',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            }
        }
    
    def create_tables(self) -> bool:
        """
        Create all required DynamoDB tables.
        
        Returns:
            bool: True if all tables created successfully
        """
        table_definitions = self.get_table_definitions()
        created_tables = []
        
        try:
            for table_name, table_config in table_definitions.items():
                try:
                    # Check if table already exists
                    existing_table = self.dynamodb.Table(table_config['TableName'])
                    existing_table.load()
                    logger.info(f"Table {table_config['TableName']} already exists")
                    continue
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        # Table doesn't exist, create it
                        logger.info(f"Creating table {table_config['TableName']}")
                        table = self.dynamodb.create_table(**table_config)
                        created_tables.append(table)
                        logger.info(f"Table {table_config['TableName']} created successfully")
                    else:
                        raise e
            
            # Wait for all tables to be active
            for table in created_tables:
                table.wait_until_exists()
                logger.info(f"Table {table.table_name} is now active")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating DynamoDB tables: {str(e)}")
            return False
    
    def delete_tables(self) -> bool:
        """
        Delete all tables (for testing/cleanup).
        
        Returns:
            bool: True if all tables deleted successfully
        """
        table_definitions = self.get_table_definitions()
        
        try:
            for table_name, table_config in table_definitions.items():
                try:
                    table = self.dynamodb.Table(table_config['TableName'])
                    table.delete()
                    logger.info(f"Table {table_config['TableName']} deleted")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        logger.info(f"Table {table_config['TableName']} does not exist")
                    else:
                        raise e
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting DynamoDB tables: {str(e)}")
            return False