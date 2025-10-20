#!/usr/bin/env python3
"""
AWS Bedrock Agent Configuration

Configures AWS Bedrock Agent with:
- Model selection (Claude)
- Action groups for tool integrations
- Knowledge bases for fraud patterns
- Agent aliases for different environments
"""

import json
import boto3
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BedrockAgentConfig:
    """Configuration for AWS Bedrock Agent."""
    agent_name: str
    agent_description: str
    foundation_model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    instruction: str = ""
    idle_session_ttl: int = 600
    region_name: str = "us-east-1"


@dataclass
class ActionGroupConfig:
    """Configuration for Bedrock Agent Action Group."""
    action_group_name: str
    description: str
    api_schema: Dict[str, Any]
    lambda_arn: Optional[str] = None


@dataclass
class KnowledgeBaseConfig:
    """Configuration for Bedrock Knowledge Base."""
    knowledge_base_name: str
    description: str
    s3_bucket: str
    s3_prefix: str
    embedding_model: str = "amazon.titan-embed-text-v1"


class BedrockAgentConfigurator:
    """Manages AWS Bedrock Agent configuration."""
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize Bedrock Agent configurator."""
        self.region_name = region_name
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region_name)
        self.iam_client = boto3.client('iam', region_name=region_name)
        
        logger.info(f"Initialized Bedrock Agent Configurator for region {region_name}")
    
    def create_agent(self, config: BedrockAgentConfig, agent_role_arn: str) -> Dict[str, Any]:
        """
        Create AWS Bedrock Agent.
        
        Args:
            config: Agent configuration
            agent_role_arn: IAM role ARN for the agent
            
        Returns:
            Agent details
        """
        logger.info(f"Creating Bedrock Agent: {config.agent_name}")
        
        instruction = config.instruction or self._get_default_instruction()
        
        try:
            response = self.bedrock_agent_client.create_agent(
                agentName=config.agent_name,
                agentResourceRoleArn=agent_role_arn,
                description=config.agent_description,
                foundationModel=config.foundation_model,
                instruction=instruction,
                idleSessionTTLInSeconds=config.idle_session_ttl
            )
            
            agent_id = response['agent']['agentId']
            logger.info(f"Created Bedrock Agent with ID: {agent_id}")
            
            return response['agent']
            
        except Exception as e:
            logger.error(f"Error creating Bedrock Agent: {str(e)}")
            raise
    
    def create_action_group(
        self,
        agent_id: str,
        agent_version: str,
        action_group_config: ActionGroupConfig
    ) -> Dict[str, Any]:
        """
        Create action group for Bedrock Agent.
        
        Args:
            agent_id: Agent ID
            agent_version: Agent version
            action_group_config: Action group configuration
            
        Returns:
            Action group details
        """
        logger.info(f"Creating action group: {action_group_config.action_group_name}")
        
        try:
            response = self.bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion=agent_version,
                actionGroupName=action_group_config.action_group_name,
                description=action_group_config.description,
                actionGroupExecutor={
                    'lambda': action_group_config.lambda_arn
                } if action_group_config.lambda_arn else {},
                apiSchema={
                    'payload': json.dumps(action_group_config.api_schema)
                }
            )
            
            logger.info(f"Created action group: {action_group_config.action_group_name}")
            return response['agentActionGroup']
            
        except Exception as e:
            logger.error(f"Error creating action group: {str(e)}")
            raise
    
    def create_knowledge_base(
        self,
        config: KnowledgeBaseConfig,
        role_arn: str
    ) -> Dict[str, Any]:
        """
        Create knowledge base for fraud patterns.
        
        Args:
            config: Knowledge base configuration
            role_arn: IAM role ARN for knowledge base
            
        Returns:
            Knowledge base details
        """
        logger.info(f"Creating knowledge base: {config.knowledge_base_name}")
        
        try:
            response = self.bedrock_agent_client.create_knowledge_base(
                name=config.knowledge_base_name,
                description=config.description,
                roleArn=role_arn,
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': f"arn:aws:bedrock:{self.region_name}::foundation-model/{config.embedding_model}"
                    }
                },
                storageConfiguration={
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': '',  # Will be set after creating collection
                        'vectorIndexName': 'fraud-patterns-index',
                        'fieldMapping': {
                            'vectorField': 'embedding',
                            'textField': 'text',
                            'metadataField': 'metadata'
                        }
                    }
                }
            )
            
            knowledge_base_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"Created knowledge base with ID: {knowledge_base_id}")
            
            return response['knowledgeBase']
            
        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise
    
    def associate_knowledge_base(
        self,
        agent_id: str,
        agent_version: str,
        knowledge_base_id: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Associate knowledge base with agent.
        
        Args:
            agent_id: Agent ID
            agent_version: Agent version
            knowledge_base_id: Knowledge base ID
            description: Association description
            
        Returns:
            Association details
        """
        logger.info(f"Associating knowledge base {knowledge_base_id} with agent {agent_id}")
        
        try:
            response = self.bedrock_agent_client.associate_agent_knowledge_base(
                agentId=agent_id,
                agentVersion=agent_version,
                knowledgeBaseId=knowledge_base_id,
                description=description,
                knowledgeBaseState='ENABLED'
            )
            
            logger.info("Knowledge base associated successfully")
            return response['agentKnowledgeBase']
            
        except Exception as e:
            logger.error(f"Error associating knowledge base: {str(e)}")
            raise
    
    def create_agent_alias(
        self,
        agent_id: str,
        alias_name: str,
        description: str,
        agent_version: str = "DRAFT"
    ) -> Dict[str, Any]:
        """
        Create agent alias for environment.
        
        Args:
            agent_id: Agent ID
            alias_name: Alias name (e.g., 'dev', 'staging', 'prod')
            description: Alias description
            agent_version: Agent version to alias
            
        Returns:
            Alias details
        """
        logger.info(f"Creating agent alias: {alias_name}")
        
        try:
            response = self.bedrock_agent_client.create_agent_alias(
                agentId=agent_id,
                agentAliasName=alias_name,
                description=description,
                routingConfiguration=[
                    {
                        'agentVersion': agent_version
                    }
                ]
            )
            
            alias_id = response['agentAlias']['agentAliasId']
            logger.info(f"Created agent alias with ID: {alias_id}")
            
            return response['agentAlias']
            
        except Exception as e:
            logger.error(f"Error creating agent alias: {str(e)}")
            raise
    
    def prepare_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Prepare agent for use (builds the agent).
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Preparation status
        """
        logger.info(f"Preparing agent {agent_id}")
        
        try:
            response = self.bedrock_agent_client.prepare_agent(agentId=agent_id)
            
            logger.info(f"Agent preparation initiated: {response['agentStatus']}")
            return response
            
        except Exception as e:
            logger.error(f"Error preparing agent: {str(e)}")
            raise
    
    def _get_default_instruction(self) -> str:
        """Get default instruction for fraud detection agent."""
        return """You are an advanced fraud detection AI agent specialized in analyzing financial transactions.

Your responsibilities:
1. Analyze transactions for fraud indicators using multi-step reasoning
2. Coordinate with specialized agents for comprehensive analysis
3. Use external tools to gather additional verification data
4. Provide detailed explanations for all decisions
5. Escalate uncertain cases to human review

When analyzing transactions:
- Consider historical patterns and user behavior
- Evaluate location, device, and timing anomalies
- Check for velocity patterns and unusual amounts
- Cross-reference with known fraud databases
- Assess compliance and regulatory requirements

Always provide:
- Clear decision (APPROVE, DECLINE, FLAG, REVIEW)
- Confidence score (0-1)
- Risk level (LOW, MEDIUM, HIGH, CRITICAL)
- Detailed reasoning with evidence
- Actionable recommendations

Prioritize security while minimizing false positives."""
    
    def get_fraud_detection_action_groups(self) -> List[ActionGroupConfig]:
        """Get action group configurations for fraud detection tools."""
        return [
            ActionGroupConfig(
                action_group_name="identity_verification",
                description="Verify user identity and check for account compromise",
                api_schema={
                    "openapi": "3.0.0",
                    "info": {
                        "title": "Identity Verification API",
                        "version": "1.0.0"
                    },
                    "paths": {
                        "/verify_identity": {
                            "post": {
                                "description": "Verify user identity",
                                "parameters": [
                                    {
                                        "name": "user_id",
                                        "in": "query",
                                        "required": True,
                                        "schema": {"type": "string"}
                                    }
                                ],
                                "responses": {
                                    "200": {
                                        "description": "Identity verification result"
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            ActionGroupConfig(
                action_group_name="fraud_database",
                description="Query fraud database for similar cases",
                api_schema={
                    "openapi": "3.0.0",
                    "info": {
                        "title": "Fraud Database API",
                        "version": "1.0.0"
                    },
                    "paths": {
                        "/check_fraud_database": {
                            "post": {
                                "description": "Check transaction against fraud database",
                                "parameters": [
                                    {
                                        "name": "transaction_id",
                                        "in": "query",
                                        "required": True,
                                        "schema": {"type": "string"}
                                    }
                                ],
                                "responses": {
                                    "200": {
                                        "description": "Fraud database check result"
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            ActionGroupConfig(
                action_group_name="geolocation",
                description="Assess location risk and verify travel patterns",
                api_schema={
                    "openapi": "3.0.0",
                    "info": {
                        "title": "Geolocation API",
                        "version": "1.0.0"
                    },
                    "paths": {
                        "/assess_location_risk": {
                            "post": {
                                "description": "Assess risk based on location",
                                "parameters": [
                                    {
                                        "name": "location",
                                        "in": "query",
                                        "required": True,
                                        "schema": {"type": "string"}
                                    }
                                ],
                                "responses": {
                                    "200": {
                                        "description": "Location risk assessment"
                                    }
                                }
                            }
                        }
                    }
                }
            )
        ]


def setup_fraud_detection_agent(
    region_name: str = "us-east-1",
    agent_role_arn: str = None,
    knowledge_base_role_arn: str = None
) -> Dict[str, Any]:
    """
    Complete setup of fraud detection Bedrock Agent.
    
    Args:
        region_name: AWS region
        agent_role_arn: IAM role ARN for agent
        knowledge_base_role_arn: IAM role ARN for knowledge base
        
    Returns:
        Setup details including agent ID, alias IDs, etc.
    """
    configurator = BedrockAgentConfigurator(region_name=region_name)
    
    # Agent configuration
    agent_config = BedrockAgentConfig(
        agent_name="fraud-detection-agent",
        agent_description="Advanced AI agent for real-time fraud detection",
        foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name=region_name
    )
    
    # Create agent
    agent = configurator.create_agent(agent_config, agent_role_arn)
    agent_id = agent['agentId']
    
    # Create action groups
    action_groups = configurator.get_fraud_detection_action_groups()
    created_action_groups = []
    
    for action_group_config in action_groups:
        action_group = configurator.create_action_group(
            agent_id=agent_id,
            agent_version="DRAFT",
            action_group_config=action_group_config
        )
        created_action_groups.append(action_group)
    
    # Create knowledge base
    kb_config = KnowledgeBaseConfig(
        knowledge_base_name="fraud-patterns-kb",
        description="Knowledge base for fraud patterns and rules",
        s3_bucket="fraud-detection-knowledge-base",
        s3_prefix="fraud-patterns/"
    )
    
    knowledge_base = configurator.create_knowledge_base(kb_config, knowledge_base_role_arn)
    kb_id = knowledge_base['knowledgeBaseId']
    
    # Associate knowledge base with agent
    configurator.associate_knowledge_base(
        agent_id=agent_id,
        agent_version="DRAFT",
        knowledge_base_id=kb_id,
        description="Fraud patterns and detection rules"
    )
    
    # Prepare agent
    configurator.prepare_agent(agent_id)
    
    # Create aliases for different environments
    aliases = {}
    for env in ['dev', 'staging', 'prod']:
        alias = configurator.create_agent_alias(
            agent_id=agent_id,
            alias_name=env,
            description=f"Alias for {env} environment"
        )
        aliases[env] = alias['agentAliasId']
    
    return {
        'agent_id': agent_id,
        'agent_name': agent_config.agent_name,
        'knowledge_base_id': kb_id,
        'action_groups': [ag['actionGroupName'] for ag in created_action_groups],
        'aliases': aliases,
        'region': region_name
    }


if __name__ == "__main__":
    # Example usage
    logger.info("Bedrock Agent Configuration Script")
    logger.info("This script configures AWS Bedrock Agent for fraud detection")
    logger.info("Note: Requires appropriate IAM roles to be created first")
