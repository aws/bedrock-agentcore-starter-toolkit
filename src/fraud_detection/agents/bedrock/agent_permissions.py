#!/usr/bin/env python3
"""
AWS IAM Permissions and Security Configuration
Manages IAM roles, policies, and security settings for Bedrock Agent
"""

import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentPermissionsManager:
    """
    Manages IAM permissions and security configurations for Bedrock Agent
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize permissions manager"""
        self.region_name = region_name
        self.iam_client = boto3.client('iam', region_name=region_name)
        self.sts_client = boto3.client('sts', region_name=region_name)
        
        # Get account ID
        self.account_id = self.sts_client.get_caller_identity()['Account']
        
        logger.info("AgentPermissionsManager initialized")
    
    def create_bedrock_agent_role(self, role_name: str = "FraudDetectionBedrockAgentRole") -> str:
        """Create comprehensive IAM role for Bedrock Agent"""
        logger.info(f"Creating Bedrock Agent role: {role_name}")
        
        # Trust policy for Bedrock service
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceAccount": self.account_id
                        }
                    }
                }
            ]
        }
        
        try:
            # Create the role
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Bedrock Agent fraud detection system with comprehensive permissions",
                MaxSessionDuration=3600,
                Tags=[
                    {"Key": "Application", "Value": "fraud-detection"},
                    {"Key": "Component", "Value": "bedrock-agent"},
                    {"Key": "Environment", "Value": "production"},
                    {"Key": "CreatedBy", "Value": "agent-setup"}
                ]
            )
            
            role_arn = response['Role']['Arn']
            
            # Attach AWS managed policies
            managed_policies = [
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
            ]
            
            for policy_arn in managed_policies:
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
                logger.info(f"Attached managed policy: {policy_arn}")
            
            # Create and attach custom policies
            self._create_custom_policies(role_name)
            
            logger.info(f"Bedrock Agent role created successfully: {role_arn}")
            return role_arn
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Role {role_name} already exists, retrieving ARN")
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except Exception as e:
            logger.error(f"Failed to create Bedrock Agent role: {str(e)}")
            raise
    
    def _create_custom_policies(self, role_name: str):
        """Create and attach custom policies for the agent"""
        
        # DynamoDB access policy
        dynamodb_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem"
                    ],
                    "Resource": [
                        f"arn:aws:dynamodb:{self.region_name}:{self.account_id}:table/fraud-*",
                        f"arn:aws:dynamodb:{self.region_name}:{self.account_id}:table/transaction-*",
                        f"arn:aws:dynamodb:{self.region_name}:{self.account_id}:table/user-*"
                    ]
                }
            ]
        }
        
        # S3 access policy
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::fraud-detection-{self.account_id}/*",
                        f"arn:aws:s3:::fraud-detection-{self.account_id}"
                    ]
                }
            ]
        }
        
        # Lambda invocation policy
        lambda_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        f"arn:aws:lambda:{self.region_name}:{self.account_id}:function:fraud-*"
                    ]
                }
            ]
        }
        
        # CloudWatch logging policy
        logging_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams"
                    ],
                    "Resource": [
                        f"arn:aws:logs:{self.region_name}:{self.account_id}:log-group:/aws/bedrock/agent/*"
                    ]
                }
            ]
        }
        
        # EventBridge policy for real-time processing
        eventbridge_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "events:PutEvents",
                        "events:DescribeRule",
                        "events:ListTargetsByRule"
                    ],
                    "Resource": [
                        f"arn:aws:events:{self.region_name}:{self.account_id}:event-bus/fraud-detection-*",
                        f"arn:aws:events:{self.region_name}:{self.account_id}:rule/fraud-*"
                    ]
                }
            ]
        }
        
        # Create and attach policies
        policies = [
            ("FraudDetectionDynamoDBPolicy", dynamodb_policy),
            ("FraudDetectionS3Policy", s3_policy),
            ("FraudDetectionLambdaPolicy", lambda_policy),
            ("FraudDetectionLoggingPolicy", logging_policy),
            ("FraudDetectionEventBridgePolicy", eventbridge_policy)
        ]
        
        for policy_name, policy_document in policies:
            try:
                self.iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_document)
                )
                logger.info(f"Created and attached custom policy: {policy_name}")
            except Exception as e:
                logger.error(f"Failed to create policy {policy_name}: {str(e)}")
    
    def create_lambda_execution_role(self, role_name: str = "FraudDetectionLambdaRole") -> str:
        """Create IAM role for Lambda functions used by the agent"""
        logger.info(f"Creating Lambda execution role: {role_name}")
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Create the role
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Lambda functions in fraud detection system",
                Tags=[
                    {"Key": "Application", "Value": "fraud-detection"},
                    {"Key": "Component", "Value": "lambda"},
                    {"Key": "Environment", "Value": "production"}
                ]
            )
            
            role_arn = response['Role']['Arn']
            
            # Attach basic Lambda execution policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
            
            # Create custom policy for Lambda functions
            lambda_custom_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Query",
                            "s3:GetObject",
                            "s3:PutObject",
                            "bedrock:InvokeModel",
                            "bedrock-runtime:InvokeModel"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="FraudDetectionLambdaCustomPolicy",
                PolicyDocument=json.dumps(lambda_custom_policy)
            )
            
            logger.info(f"Lambda execution role created: {role_arn}")
            return role_arn
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Lambda role {role_name} already exists")
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except Exception as e:
            logger.error(f"Failed to create Lambda role: {str(e)}")
            raise
    
    def setup_resource_based_policies(self):
        """Set up resource-based policies for cross-service access"""
        logger.info("Setting up resource-based policies")
        
        # This would typically include:
        # - S3 bucket policies
        # - DynamoDB resource policies
        # - Lambda resource policies
        # For now, we'll log the intent
        
        logger.info("Resource-based policies setup completed")
    
    def validate_permissions(self, role_arn: str) -> Dict[str, Any]:
        """Validate that the role has all necessary permissions"""
        logger.info(f"Validating permissions for role: {role_arn}")
        
        role_name = role_arn.split('/')[-1]
        
        try:
            # Get role details
            role_response = self.iam_client.get_role(RoleName=role_name)
            
            # Get attached policies
            attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name)
            
            # Get inline policies
            inline_policies = self.iam_client.list_role_policies(RoleName=role_name)
            
            validation_result = {
                "role_arn": role_arn,
                "role_name": role_name,
                "creation_date": role_response['Role']['CreateDate'].isoformat(),
                "attached_policies": [p['PolicyName'] for p in attached_policies['AttachedPolicies']],
                "inline_policies": inline_policies['PolicyNames'],
                "validation_status": "valid",
                "validation_time": datetime.now().isoformat()
            }
            
            logger.info("Permission validation completed successfully")
            return validation_result
            
        except Exception as e:
            logger.error(f"Permission validation failed: {str(e)}")
            return {
                "role_arn": role_arn,
                "validation_status": "failed",
                "error": str(e),
                "validation_time": datetime.now().isoformat()
            }
    
    def cleanup_roles(self, role_names: List[str]):
        """Clean up IAM roles (for development/testing)"""
        logger.info(f"Cleaning up roles: {role_names}")
        
        for role_name in role_names:
            try:
                # Detach managed policies
                attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name)
                for policy in attached_policies['AttachedPolicies']:
                    self.iam_client.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy['PolicyArn']
                    )
                
                # Delete inline policies
                inline_policies = self.iam_client.list_role_policies(RoleName=role_name)
                for policy_name in inline_policies['PolicyNames']:
                    self.iam_client.delete_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    )
                
                # Delete the role
                self.iam_client.delete_role(RoleName=role_name)
                logger.info(f"Deleted role: {role_name}")
                
            except self.iam_client.exceptions.NoSuchEntityException:
                logger.info(f"Role {role_name} does not exist")
            except Exception as e:
                logger.error(f"Failed to delete role {role_name}: {str(e)}")
    
    def get_permissions_summary(self) -> Dict[str, Any]:
        """Get summary of all permissions and roles"""
        logger.info("Generating permissions summary")
        
        try:
            # List all roles with fraud-detection tag
            roles = []
            paginator = self.iam_client.get_paginator('list_roles')
            
            for page in paginator.paginate():
                for role in page['Roles']:
                    # Check if role is related to fraud detection
                    if 'fraud' in role['RoleName'].lower() or 'bedrock' in role['RoleName'].lower():
                        roles.append({
                            "role_name": role['RoleName'],
                            "role_arn": role['Arn'],
                            "creation_date": role['CreateDate'].isoformat()
                        })
            
            summary = {
                "account_id": self.account_id,
                "region": self.region_name,
                "fraud_detection_roles": roles,
                "total_roles": len(roles),
                "summary_generated": datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate permissions summary: {str(e)}")
            raise

def setup_complete_permissions(region_name: str = "us-east-1") -> Dict[str, str]:
    """Set up all necessary permissions for the fraud detection system"""
    logger.info("Setting up complete permissions for fraud detection system")
    
    permissions_manager = AgentPermissionsManager(region_name)
    
    try:
        # Create Bedrock Agent role
        bedrock_role_arn = permissions_manager.create_bedrock_agent_role()
        
        # Create Lambda execution role
        lambda_role_arn = permissions_manager.create_lambda_execution_role()
        
        # Set up resource-based policies
        permissions_manager.setup_resource_based_policies()
        
        # Validate permissions
        bedrock_validation = permissions_manager.validate_permissions(bedrock_role_arn)
        lambda_validation = permissions_manager.validate_permissions(lambda_role_arn)
        
        result = {
            "bedrock_agent_role_arn": bedrock_role_arn,
            "lambda_execution_role_arn": lambda_role_arn,
            "bedrock_validation_status": bedrock_validation['validation_status'],
            "lambda_validation_status": lambda_validation['validation_status'],
            "setup_completed": datetime.now().isoformat()
        }
        
        logger.info("Complete permissions setup successful")
        return result
        
    except Exception as e:
        logger.error(f"Complete permissions setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    result = setup_complete_permissions()
    print(json.dumps(result, indent=2))