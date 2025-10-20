#!/usr/bin/env python3
"""
IAM Roles and Policies for AWS Bedrock Agent

Creates necessary IAM roles and policies for:
- Bedrock Agent execution
- Knowledge base access
- Lambda function execution
- Service integrations
"""

import json
import boto3
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IAMRoleManager:
    """Manages IAM roles and policies for Bedrock Agent."""
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize IAM role manager."""
        self.iam_client = boto3.client('iam', region_name=region_name)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        self.region_name = region_name
        
        logger.info("Initialized IAM Role Manager")
    
    def create_bedrock_agent_role(self) -> str:
        """
        Create IAM role for Bedrock Agent.
        
        Returns:
            Role ARN
        """
        role_name = "BedrockAgentFraudDetectionRole"
        
        # Trust policy for Bedrock Agent
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
                        },
                        "ArnLike": {
                            "aws:SourceArn": f"arn:aws:bedrock:{self.region_name}:{self.account_id}:agent/*"
                        }
                    }
                }
            ]
        }
        
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Bedrock Agent fraud detection",
                MaxSessionDuration=3600
            )
            
            role_arn = response['Role']['Arn']
            logger.info(f"Created Bedrock Agent role: {role_arn}")
            
            # Attach policies
            self._attach_bedrock_agent_policies(role_name)
            
            return role_arn
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Role {role_name} already exists")
            role_arn = f"arn:aws:iam::{self.account_id}:role/{role_name}"
            return role_arn
        except Exception as e:
            logger.error(f"Error creating Bedrock Agent role: {str(e)}")
            raise
    
    def _attach_bedrock_agent_policies(self, role_name: str):
        """Attach necessary policies to Bedrock Agent role."""
        
        # Policy for Bedrock model invocation
        bedrock_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/anthropic.claude-*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:Retrieve",
                        "bedrock:RetrieveAndGenerate"
                    ],
                    "Resource": f"arn:aws:bedrock:{self.region_name}:{self.account_id}:knowledge-base/*"
                }
            ]
        }
        
        policy_name = "BedrockAgentModelInvocationPolicy"
        
        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(bedrock_policy)
            )
            logger.info(f"Attached policy {policy_name} to role {role_name}")
        except Exception as e:
            logger.error(f"Error attaching policy: {str(e)}")
            raise
    
    def create_knowledge_base_role(self) -> str:
        """
        Create IAM role for Bedrock Knowledge Base.
        
        Returns:
            Role ARN
        """
        role_name = "BedrockKnowledgeBaseFraudPatternsRole"
        
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
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Bedrock Knowledge Base",
                MaxSessionDuration=3600
            )
            
            role_arn = response['Role']['Arn']
            logger.info(f"Created Knowledge Base role: {role_arn}")
            
            # Attach policies
            self._attach_knowledge_base_policies(role_name)
            
            return role_arn
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Role {role_name} already exists")
            role_arn = f"arn:aws:iam::{self.account_id}:role/{role_name}"
            return role_arn
        except Exception as e:
            logger.error(f"Error creating Knowledge Base role: {str(e)}")
            raise
    
    def _attach_knowledge_base_policies(self, role_name: str):
        """Attach necessary policies to Knowledge Base role."""
        
        kb_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel"
                    ],
                    "Resource": f"arn:aws:bedrock:{self.region_name}::foundation-model/amazon.titan-embed-text-v1"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        "arn:aws:s3:::fraud-detection-knowledge-base/*",
                        "arn:aws:s3:::fraud-detection-knowledge-base"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "aoss:APIAccessAll"
                    ],
                    "Resource": f"arn:aws:aoss:{self.region_name}:{self.account_id}:collection/*"
                }
            ]
        }
        
        policy_name = "BedrockKnowledgeBaseAccessPolicy"
        
        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(kb_policy)
            )
            logger.info(f"Attached policy {policy_name} to role {role_name}")
        except Exception as e:
            logger.error(f"Error attaching policy: {str(e)}")
            raise
    
    def create_lambda_execution_role(self) -> str:
        """
        Create IAM role for Lambda functions (action group executors).
        
        Returns:
            Role ARN
        """
        role_name = "BedrockAgentActionGroupLambdaRole"
        
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
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Bedrock Agent action group Lambda functions",
                MaxSessionDuration=3600
            )
            
            role_arn = response['Role']['Arn']
            logger.info(f"Created Lambda execution role: {role_arn}")
            
            # Attach AWS managed policy for Lambda basic execution
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
            
            # Attach custom policies
            self._attach_lambda_policies(role_name)
            
            return role_arn
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Role {role_name} already exists")
            role_arn = f"arn:aws:iam::{self.account_id}:role/{role_name}"
            return role_arn
        except Exception as e:
            logger.error(f"Error creating Lambda execution role: {str(e)}")
            raise
    
    def _attach_lambda_policies(self, role_name: str):
        """Attach necessary policies to Lambda execution role."""
        
        lambda_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:Scan"
                    ],
                    "Resource": f"arn:aws:dynamodb:{self.region_name}:{self.account_id}:table/fraud-detection-*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Resource": "arn:aws:s3:::fraud-detection-*/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": f"arn:aws:logs:{self.region_name}:{self.account_id}:log-group:/aws/lambda/bedrock-agent-*"
                }
            ]
        }
        
        policy_name = "BedrockAgentLambdaAccessPolicy"
        
        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(lambda_policy)
            )
            logger.info(f"Attached policy {policy_name} to role {role_name}")
        except Exception as e:
            logger.error(f"Error attaching policy: {str(e)}")
            raise
    
    def setup_all_roles(self) -> Dict[str, str]:
        """
        Create all necessary IAM roles.
        
        Returns:
            Dictionary of role ARNs
        """
        logger.info("Setting up all IAM roles")
        
        roles = {
            'agent_role_arn': self.create_bedrock_agent_role(),
            'knowledge_base_role_arn': self.create_knowledge_base_role(),
            'lambda_role_arn': self.create_lambda_execution_role()
        }
        
        logger.info("All IAM roles created successfully")
        return roles


def main():
    """Setup IAM roles for Bedrock Agent."""
    manager = IAMRoleManager()
    roles = manager.setup_all_roles()
    
    print("\nCreated IAM Roles:")
    for role_type, role_arn in roles.items():
        print(f"  {role_type}: {role_arn}")


if __name__ == "__main__":
    main()
