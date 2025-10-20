#!/usr/bin/env python3
"""
Deployment Script for AWS Bedrock Agent

Orchestrates the complete deployment:
1. Create IAM roles
2. Deploy CloudFormation stack
3. Configure Bedrock Agent
4. Set up action groups and knowledge base
5. Create agent aliases
"""

import sys
import time
import boto3
from typing import Dict, Optional
import logging

from iam_roles import IAMRoleManager
from bedrock_agent_config import BedrockAgentConfigurator, BedrockAgentConfig, setup_fraud_detection_agent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BedrockAgentDeployer:
    """Orchestrates Bedrock Agent deployment."""
    
    def __init__(self, region_name: str = "us-east-1", environment: str = "dev"):
        """Initialize deployer."""
        self.region_name = region_name
        self.environment = environment
        self.cfn_client = boto3.client('cloudformation', region_name=region_name)
        self.iam_manager = IAMRoleManager(region_name=region_name)
        
        logger.info(f"Initialized Bedrock Agent Deployer for {environment} environment in {region_name}")
    
    def deploy_cloudformation_stack(self, stack_name: str) -> Dict[str, str]:
        """
        Deploy CloudFormation stack.
        
        Args:
            stack_name: Name of the CloudFormation stack
            
        Returns:
            Stack outputs
        """
        logger.info(f"Deploying CloudFormation stack: {stack_name}")
        
        # Read template file
        with open('cloudformation_template.yaml', 'r') as f:
            template_body = f.read()
        
        try:
            # Create stack
            response = self.cfn_client.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=[
                    {
                        'ParameterKey': 'Environment',
                        'ParameterValue': self.environment
                    }
                ],
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Application', 'Value': 'FraudDetection'}
                ]
            )
            
            stack_id = response['StackId']
            logger.info(f"Stack creation initiated: {stack_id}")
            
            # Wait for stack creation
            logger.info("Waiting for stack creation to complete...")
            waiter = self.cfn_client.get_waiter('stack_create_complete')
            waiter.wait(StackName=stack_name)
            
            logger.info("Stack created successfully")
            
            # Get stack outputs
            outputs = self._get_stack_outputs(stack_name)
            return outputs
            
        except self.cfn_client.exceptions.AlreadyExistsException:
            logger.info(f"Stack {stack_name} already exists, updating...")
            return self._update_stack(stack_name, template_body)
        except Exception as e:
            logger.error(f"Error deploying CloudFormation stack: {str(e)}")
            raise
    
    def _update_stack(self, stack_name: str, template_body: str) -> Dict[str, str]:
        """Update existing CloudFormation stack."""
        try:
            self.cfn_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=[
                    {
                        'ParameterKey': 'Environment',
                        'ParameterValue': self.environment
                    }
                ],
                Capabilities=['CAPABILITY_NAMED_IAM']
            )
            
            logger.info("Waiting for stack update to complete...")
            waiter = self.cfn_client.get_waiter('stack_update_complete')
            waiter.wait(StackName=stack_name)
            
            logger.info("Stack updated successfully")
            
            outputs = self._get_stack_outputs(stack_name)
            return outputs
            
        except self.cfn_client.exceptions.ClientError as e:
            if 'No updates are to be performed' in str(e):
                logger.info("No updates needed for stack")
                return self._get_stack_outputs(stack_name)
            raise
    
    def _get_stack_outputs(self, stack_name: str) -> Dict[str, str]:
        """Get CloudFormation stack outputs."""
        response = self.cfn_client.describe_stacks(StackName=stack_name)
        
        outputs = {}
        if 'Stacks' in response and len(response['Stacks']) > 0:
            stack = response['Stacks'][0]
            if 'Outputs' in stack:
                for output in stack['Outputs']:
                    outputs[output['OutputKey']] = output['OutputValue']
        
        return outputs
    
    def deploy_bedrock_agent(self, stack_outputs: Dict[str, str]) -> Dict[str, any]:
        """
        Deploy Bedrock Agent with configuration.
        
        Args:
            stack_outputs: CloudFormation stack outputs
            
        Returns:
            Agent deployment details
        """
        logger.info("Deploying Bedrock Agent")
        
        agent_role_arn = stack_outputs.get('BedrockAgentRoleArn')
        kb_role_arn = stack_outputs.get('KnowledgeBaseRoleArn')
        
        if not agent_role_arn or not kb_role_arn:
            raise ValueError("Missing required IAM role ARNs from stack outputs")
        
        # Setup agent with all configurations
        agent_details = setup_fraud_detection_agent(
            region_name=self.region_name,
            agent_role_arn=agent_role_arn,
            knowledge_base_role_arn=kb_role_arn
        )
        
        logger.info(f"Bedrock Agent deployed successfully: {agent_details['agent_id']}")
        return agent_details
    
    def full_deployment(self) -> Dict[str, any]:
        """
        Execute full deployment workflow.
        
        Returns:
            Complete deployment details
        """
        logger.info("Starting full Bedrock Agent deployment")
        
        stack_name = f"fraud-detection-bedrock-agent-{self.environment}"
        
        # Step 1: Deploy CloudFormation stack
        logger.info("Step 1: Deploying CloudFormation stack")
        stack_outputs = self.deploy_cloudformation_stack(stack_name)
        
        # Wait for IAM roles to propagate
        logger.info("Waiting for IAM roles to propagate...")
        time.sleep(10)
        
        # Step 2: Deploy Bedrock Agent
        logger.info("Step 2: Deploying Bedrock Agent")
        agent_details = self.deploy_bedrock_agent(stack_outputs)
        
        # Combine results
        deployment_details = {
            'environment': self.environment,
            'region': self.region_name,
            'stack_name': stack_name,
            'stack_outputs': stack_outputs,
            'agent_details': agent_details
        }
        
        logger.info("Full deployment completed successfully")
        return deployment_details
    
    def print_deployment_summary(self, deployment_details: Dict[str, any]):
        """Print deployment summary."""
        print("\n" + "="*80)
        print("BEDROCK AGENT DEPLOYMENT SUMMARY")
        print("="*80)
        print(f"\nEnvironment: {deployment_details['environment']}")
        print(f"Region: {deployment_details['region']}")
        print(f"Stack Name: {deployment_details['stack_name']}")
        
        print("\n--- Agent Details ---")
        agent = deployment_details['agent_details']
        print(f"Agent ID: {agent['agent_id']}")
        print(f"Agent Name: {agent['agent_name']}")
        print(f"Knowledge Base ID: {agent['knowledge_base_id']}")
        
        print("\n--- Action Groups ---")
        for ag in agent['action_groups']:
            print(f"  - {ag}")
        
        print("\n--- Agent Aliases ---")
        for env, alias_id in agent['aliases'].items():
            print(f"  {env}: {alias_id}")
        
        print("\n--- Stack Outputs ---")
        for key, value in deployment_details['stack_outputs'].items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*80)
        print("Deployment completed successfully!")
        print("="*80 + "\n")


def main():
    """Main deployment script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy AWS Bedrock Agent for Fraud Detection')
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--environment',
        type=str,
        default='dev',
        choices=['dev', 'staging', 'prod'],
        help='Environment (default: dev)'
    )
    
    args = parser.parse_args()
    
    try:
        deployer = BedrockAgentDeployer(
            region_name=args.region,
            environment=args.environment
        )
        
        deployment_details = deployer.full_deployment()
        deployer.print_deployment_summary(deployment_details)
        
        return 0
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
