#!/usr/bin/env python3
"""
AWS Bedrock Agent Configuration
Configuration management for Bedrock Agent setup and deployment
"""

import json
import os
import boto3
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AgentConfiguration:
    """Configuration for a Bedrock Agent"""
    agent_name: str
    agent_id: Optional[str] = None
    description: str = ""
    instruction: str = ""
    foundation_model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    idle_session_ttl: int = 3600
    agent_resource_role_arn: Optional[str] = None
    customer_encryption_key_arn: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

@dataclass
class ActionGroupConfiguration:
    """Configuration for agent action groups"""
    action_group_name: str
    description: str
    action_group_executor: Dict[str, Any]
    api_schema: Dict[str, Any]
    parent_action_signature: str = "AMAZON.UserInput"

@dataclass
class KnowledgeBaseConfiguration:
    """Configuration for knowledge base integration"""
    knowledge_base_id: str
    description: str
    knowledge_base_state: str = "ENABLED"

class BedrockAgentConfig:
    """
    Manages AWS Bedrock Agent configuration and deployment
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize Bedrock Agent configuration manager"""
        self.region_name = region_name
        self.bedrock_agent_client = None
        self.iam_client = None
        self.lambda_client = None
        
        # Initialize AWS clients
        self._initialize_clients()
        
        # Default configurations
        self.default_agent_config = self._get_default_agent_config()
        self.action_groups_config = self._get_action_groups_config()
        
        logger.info("BedrockAgentConfig initialized successfully")
    
    def _initialize_clients(self):
        """Initialize AWS service clients"""
        try:
            self.bedrock_agent_client = boto3.client(
                'bedrock-agent',
                region_name=self.region_name
            )
            
            self.iam_client = boto3.client(
                'iam',
                region_name=self.region_name
            )
            
            self.lambda_client = boto3.client(
                'lambda',
                region_name=self.region_name
            )
            
            logger.info("AWS clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise
    
    def _get_default_agent_config(self) -> AgentConfiguration:
        """Get default agent configuration"""
        return AgentConfiguration(
            agent_name="fraud-detection-agent",
            description="Multi-currency fraud detection AI agent with advanced reasoning capabilities",
            instruction="""You are an expert fraud detection agent specializing in multi-currency transaction analysis.

Your primary responsibilities:
1. Analyze transactions for fraud indicators using advanced reasoning
2. Consider historical patterns, user behavior, and contextual factors
3. Provide detailed explanations for all decisions
4. Coordinate with specialized agents for comprehensive analysis
5. Ensure compliance with regulatory requirements

When analyzing transactions:
- Use chain-of-thought reasoning to break down complex patterns
- Consider currency risks, location anomalies, and velocity patterns
- Cross-reference with known fraud databases and patterns
- Provide confidence scores and detailed evidence
- Recommend appropriate actions (APPROVE, FLAG, REVIEW, BLOCK)

Always explain your reasoning clearly and provide actionable insights.""",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            idle_session_ttl=3600,
            tags={
                "Environment": "production",
                "Application": "fraud-detection",
                "Version": "1.0.0"
            }
        )
    
    def _get_action_groups_config(self) -> List[ActionGroupConfiguration]:
        """Get action groups configuration"""
        return [
            ActionGroupConfiguration(
                action_group_name="transaction-analyzer",
                description="Analyze individual transactions for fraud indicators",
                action_group_executor={
                    "lambda": {
                        "lambdaArn": f"arn:aws:lambda:{self.region_name}:{{account_id}}:function:fraud-transaction-analyzer"
                    }
                },
                api_schema={
                    "openapi": "3.0.0",
                    "info": {
                        "title": "Transaction Analyzer API",
                        "version": "1.0.0"
                    },
                    "paths": {
                        "/analyze-transaction": {
                            "post": {
                                "summary": "Analyze a transaction for fraud indicators",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "transaction_id": {"type": "string"},
                                                    "amount": {"type": "number"},
                                                    "currency": {"type": "string"},
                                                    "merchant": {"type": "string"},
                                                    "location": {"type": "string"},
                                                    "user_id": {"type": "string"}
                                                },
                                                "required": ["transaction_id", "amount", "currency", "merchant"]
                                            }
                                        }
                                    }
                                },
                                "responses": {
                                    "200": {
                                        "description": "Analysis result",
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "type": "object",
                                                    "properties": {
                                                        "is_fraud": {"type": "boolean"},
                                                        "confidence": {"type": "number"},
                                                        "risk_factors": {"type": "array", "items": {"type": "string"}},
                                                        "recommendation": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            ActionGroupConfiguration(
                action_group_name="pattern-detector",
                description="Detect fraud patterns and anomalies",
                action_group_executor={
                    "lambda": {
                        "lambdaArn": f"arn:aws:lambda:{self.region_name}:{{account_id}}:function:fraud-pattern-detector"
                    }
                },
                api_schema={
                    "openapi": "3.0.0",
                    "info": {
                        "title": "Pattern Detector API",
                        "version": "1.0.0"
                    },
                    "paths": {
                        "/detect-patterns": {
                            "post": {
                                "summary": "Detect fraud patterns in transaction data",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "transaction": {"type": "object"},
                                                    "user_history": {"type": "array"},
                                                    "time_window": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                },
                                "responses": {
                                    "200": {
                                        "description": "Pattern analysis result",
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "type": "object",
                                                    "properties": {
                                                        "patterns_detected": {"type": "array"},
                                                        "anomaly_score": {"type": "number"},
                                                        "similar_cases": {"type": "array"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            ActionGroupConfiguration(
                action_group_name="external-tools",
                description="Access external APIs and databases",
                action_group_executor={
                    "lambda": {
                        "lambdaArn": f"arn:aws:lambda:{self.region_name}:{{account_id}}:function:fraud-external-tools"
                    }
                },
                api_schema={
                    "openapi": "3.0.0",
                    "info": {
                        "title": "External Tools API",
                        "version": "1.0.0"
                    },
                    "paths": {
                        "/verify-identity": {
                            "post": {
                                "summary": "Verify user identity",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "user_id": {"type": "string"},
                                                    "verification_data": {"type": "object"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "/check-fraud-database": {
                            "post": {
                                "summary": "Check fraud database for similar cases",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "transaction_hash": {"type": "string"},
                                                    "search_criteria": {"type": "object"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "/get-location-risk": {
                            "post": {
                                "summary": "Get location-based risk assessment",
                                "requestBody": {
                                    "required": True,
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "location": {"type": "string"},
                                                    "ip_address": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            )
        ]
    
    def create_agent_role(self, role_name: str = "BedrockAgentRole") -> str:
        """Create IAM role for Bedrock Agent"""
        logger.info(f"Creating IAM role: {role_name}")
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Create role
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Bedrock Agent fraud detection system",
                Tags=[
                    {"Key": "Application", "Value": "fraud-detection"},
                    {"Key": "Component", "Value": "bedrock-agent"}
                ]
            )
            
            role_arn = response['Role']['Arn']
            
            # Attach necessary policies
            policies = [
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
                "arn:aws:iam::aws:policy/AWSLambdaRole"
            ]
            
            for policy_arn in policies:
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            # Create custom policy for additional permissions
            custom_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                            "s3:GetObject",
                            "s3:PutObject",
                            "lambda:InvokeFunction"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="BedrockAgentCustomPolicy",
                PolicyDocument=json.dumps(custom_policy)
            )
            
            logger.info(f"IAM role created successfully: {role_arn}")
            return role_arn
            
        except Exception as e:
            logger.error(f"Failed to create IAM role: {str(e)}")
            raise
    
    def create_agent(self, agent_config: Optional[AgentConfiguration] = None) -> Dict[str, Any]:
        """Create Bedrock Agent"""
        if agent_config is None:
            agent_config = self.default_agent_config
        
        logger.info(f"Creating Bedrock Agent: {agent_config.agent_name}")
        
        try:
            # Create agent role if not provided
            if not agent_config.agent_resource_role_arn:
                agent_config.agent_resource_role_arn = self.create_agent_role()
            
            # Prepare agent creation parameters
            create_params = {
                "agentName": agent_config.agent_name,
                "description": agent_config.description,
                "instruction": agent_config.instruction,
                "foundationModel": agent_config.foundation_model,
                "idleSessionTTLInSeconds": agent_config.idle_session_ttl,
                "agentResourceRoleArn": agent_config.agent_resource_role_arn
            }
            
            if agent_config.customer_encryption_key_arn:
                create_params["customerEncryptionKeyArn"] = agent_config.customer_encryption_key_arn
            
            if agent_config.tags:
                create_params["tags"] = agent_config.tags
            
            # Create the agent
            response = self.bedrock_agent_client.create_agent(**create_params)
            
            agent_id = response['agent']['agentId']
            agent_config.agent_id = agent_id
            
            logger.info(f"Agent created successfully with ID: {agent_id}")
            
            # Create action groups
            for action_group_config in self.action_groups_config:
                self.create_action_group(agent_id, action_group_config)
            
            # Prepare the agent
            self.prepare_agent(agent_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise
    
    def create_action_group(self, agent_id: str, action_group_config: ActionGroupConfiguration):
        """Create action group for the agent"""
        logger.info(f"Creating action group: {action_group_config.action_group_name}")
        
        try:
            # Replace account_id placeholder in Lambda ARN
            account_id = boto3.client('sts').get_caller_identity()['Account']
            
            if 'lambda' in action_group_config.action_group_executor:
                lambda_arn = action_group_config.action_group_executor['lambda']['lambdaArn']
                lambda_arn = lambda_arn.replace('{account_id}', account_id)
                action_group_config.action_group_executor['lambda']['lambdaArn'] = lambda_arn
            
            response = self.bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupName=action_group_config.action_group_name,
                description=action_group_config.description,
                actionGroupExecutor=action_group_config.action_group_executor,
                apiSchema={
                    "payload": json.dumps(action_group_config.api_schema)
                },
                parentActionSignature=action_group_config.parent_action_signature
            )
            
            logger.info(f"Action group created: {action_group_config.action_group_name}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create action group {action_group_config.action_group_name}: {str(e)}")
            # Don't raise - continue with other action groups
    
    def prepare_agent(self, agent_id: str) -> Dict[str, Any]:
        """Prepare the agent for use"""
        logger.info(f"Preparing agent: {agent_id}")
        
        try:
            response = self.bedrock_agent_client.prepare_agent(
                agentId=agent_id
            )
            
            logger.info(f"Agent prepared successfully: {agent_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to prepare agent: {str(e)}")
            raise
    
    def create_agent_alias(self, agent_id: str, alias_name: str = "production") -> Dict[str, Any]:
        """Create agent alias for production use"""
        logger.info(f"Creating agent alias: {alias_name}")
        
        try:
            response = self.bedrock_agent_client.create_agent_alias(
                agentId=agent_id,
                agentAliasName=alias_name,
                description=f"Production alias for fraud detection agent",
                tags={
                    "Environment": "production",
                    "Application": "fraud-detection"
                }
            )
            
            logger.info(f"Agent alias created: {alias_name}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create agent alias: {str(e)}")
            raise
    
    def get_agent_configuration(self) -> Dict[str, Any]:
        """Get current agent configuration"""
        return {
            "default_agent_config": asdict(self.default_agent_config),
            "action_groups": [asdict(ag) for ag in self.action_groups_config],
            "region": self.region_name,
            "timestamp": datetime.now().isoformat()
        }
    
    def deploy_complete_agent(self) -> Dict[str, Any]:
        """Deploy complete agent with all configurations"""
        logger.info("Starting complete agent deployment")
        
        try:
            # Create the agent
            agent_response = self.create_agent()
            agent_id = agent_response['agent']['agentId']
            
            # Create production alias
            alias_response = self.create_agent_alias(agent_id)
            
            deployment_info = {
                "agent_id": agent_id,
                "agent_name": self.default_agent_config.agent_name,
                "alias_id": alias_response['agentAlias']['agentAliasId'],
                "alias_name": alias_response['agentAlias']['agentAliasName'],
                "status": "deployed",
                "deployment_time": datetime.now().isoformat(),
                "region": self.region_name
            }
            
            logger.info("Complete agent deployment successful")
            return deployment_info
            
        except Exception as e:
            logger.error(f"Complete agent deployment failed: {str(e)}")
            raise

# Configuration constants
SUPPORTED_MODELS = [
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-instant-v1",
    "amazon.titan-text-express-v1"
]

DEFAULT_REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "ap-southeast-1"
]

def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {str(e)}")
        raise

def save_config_to_file(config: Dict[str, Any], config_path: str):
    """Save configuration to JSON file"""
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {str(e)}")
        raise