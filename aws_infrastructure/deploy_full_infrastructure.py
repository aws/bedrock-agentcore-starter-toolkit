#!/usr/bin/env python3
"""
Complete Infrastructure Deployment Orchestrator

Orchestrates deployment of all AWS infrastructure components:
1. IAM roles and permissions
2. Data storage (DynamoDB, S3)
3. Streaming infrastructure (Kinesis, EventBridge, Lambda)
4. Bedrock Agent configuration
5. Monitoring and observability (CloudWatch, X-Ray)
"""

import sys
import time
import argparse
import logging
from typing import Dict

from iam_roles import IAMRoleManager
from data_storage_config import DataStorageConfigurator
from streaming_config import StreamingInfrastructureConfigurator
from monitoring_config import MonitoringConfigurator
from deploy_bedrock_agent import BedrockAgentDeployer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FullInfrastructureDeployer:
    """Orchestrates complete infrastructure deployment."""
    
    def __init__(self, region_name: str = "us-east-1", environment: str = "dev"):
        """Initialize full infrastructure deployer."""
        self.region_name = region_name
        self.environment = environment
        
        logger.info(f"Initialized Full Infrastructure Deployer for {environment} in {region_name}")
    
    def deploy_all(self) -> Dict:
        """
        Deploy all infrastructure components.
        
        Returns:
            Complete deployment details
        """
        logger.info("="*80)
        logger.info("STARTING FULL INFRASTRUCTURE DEPLOYMENT")
        logger.info("="*80)
        
        deployment_results = {
            'environment': self.environment,
            'region': self.region_name,
            'components': {}
        }
        
        try:
            # Step 1: Deploy IAM roles
            logger.info("\n[1/5] Deploying IAM roles...")
            iam_manager = IAMRoleManager(region_name=self.region_name)
            iam_roles = iam_manager.setup_all_roles()
            deployment_results['components']['iam_roles'] = iam_roles
            logger.info("✓ IAM roles deployed successfully")
            
            # Wait for IAM propagation
            logger.info("Waiting for IAM roles to propagate...")
            time.sleep(10)
            
            # Step 2: Deploy data storage infrastructure
            logger.info("\n[2/5] Deploying data storage infrastructure...")
            storage_configurator = DataStorageConfigurator(
                region_name=self.region_name,
                environment=self.environment
            )
            storage_resources = storage_configurator.setup_all_storage()
            deployment_results['components']['storage'] = storage_resources
            logger.info("✓ Data storage infrastructure deployed successfully")
            
            # Step 3: Deploy streaming infrastructure
            logger.info("\n[3/5] Deploying streaming infrastructure...")
            streaming_configurator = StreamingInfrastructureConfigurator(
                region_name=self.region_name,
                environment=self.environment
            )
            streaming_resources = streaming_configurator.setup_all_streaming_infrastructure(
                lambda_role_arn=iam_roles['lambda_role_arn']
            )
            deployment_results['components']['streaming'] = streaming_resources
            logger.info("✓ Streaming infrastructure deployed successfully")
            
            # Step 4: Deploy Bedrock Agent
            logger.info("\n[4/5] Deploying AWS Bedrock Agent...")
            bedrock_deployer = BedrockAgentDeployer(
                region_name=self.region_name,
                environment=self.environment
            )
            bedrock_deployment = bedrock_deployer.full_deployment()
            deployment_results['components']['bedrock_agent'] = bedrock_deployment
            logger.info("✓ Bedrock Agent deployed successfully")
            
            # Step 5: Set up monitoring and observability
            logger.info("\n[5/5] Setting up monitoring and observability...")
            monitoring_configurator = MonitoringConfigurator(
                region_name=self.region_name,
                environment=self.environment
            )
            
            # Collect resource names for monitoring
            lambda_functions = [
                func['function_name'] 
                for func in streaming_resources['lambda_functions'].values()
            ]
            
            kinesis_streams = [
                stream['stream_name'] 
                for stream in streaming_resources['kinesis_streams'].values()
            ]
            
            dynamodb_tables = [
                table['TableName'] 
                for table in storage_resources['dynamodb_tables'].values()
            ]
            
            monitoring_resources = monitoring_configurator.setup_all_monitoring(
                lambda_function_names=lambda_functions,
                kinesis_stream_names=kinesis_streams,
                dynamodb_table_names=dynamodb_tables
            )
            deployment_results['components']['monitoring'] = monitoring_resources
            logger.info("✓ Monitoring and observability configured successfully")
            
            logger.info("\n" + "="*80)
            logger.info("FULL INFRASTRUCTURE DEPLOYMENT COMPLETED SUCCESSFULLY")
            logger.info("="*80)
            
            return deployment_results
            
        except Exception as e:
            logger.error(f"\n✗ Deployment failed: {str(e)}")
            raise
    
    def print_deployment_summary(self, deployment_results: Dict):
        """Print comprehensive deployment summary."""
        print("\n" + "="*80)
        print("DEPLOYMENT SUMMARY")
        print("="*80)
        
        print(f"\nEnvironment: {deployment_results['environment']}")
        print(f"Region: {deployment_results['region']}")
        
        components = deployment_results['components']
        
        # IAM Roles
        if 'iam_roles' in components:
            print("\n--- IAM Roles ---")
            for role_type, role_arn in components['iam_roles'].items():
                print(f"  {role_type}: {role_arn}")
        
        # Data Storage
        if 'storage' in components:
            print("\n--- Data Storage ---")
            print("  DynamoDB Tables:")
            for name, table in components['storage']['dynamodb_tables'].items():
                print(f"    - {name}: {table['TableName']}")
            print("  S3 Buckets:")
            for name, bucket in components['storage']['s3_buckets'].items():
                print(f"    - {name}: {bucket['bucket_name']}")
        
        # Streaming Infrastructure
        if 'streaming' in components:
            print("\n--- Streaming Infrastructure ---")
            print("  Kinesis Streams:")
            for name, stream in components['streaming']['kinesis_streams'].items():
                print(f"    - {name}: {stream['stream_name']}")
            print("  Lambda Functions:")
            for name, func in components['streaming']['lambda_functions'].items():
                print(f"    - {name}: {func['function_name']}")
            print("  EventBridge Rules:")
            for name, rule in components['streaming']['eventbridge_rules'].items():
                print(f"    - {name}: {rule['rule_name']}")
        
        # Bedrock Agent
        if 'bedrock_agent' in components:
            print("\n--- AWS Bedrock Agent ---")
            agent = components['bedrock_agent']['agent_details']
            print(f"  Agent ID: {agent['agent_id']}")
            print(f"  Agent Name: {agent['agent_name']}")
            print(f"  Knowledge Base ID: {agent['knowledge_base_id']}")
            print("  Action Groups:")
            for ag in agent['action_groups']:
                print(f"    - {ag}")
            print("  Aliases:")
            for env, alias_id in agent['aliases'].items():
                print(f"    - {env}: {alias_id}")
        
        # Monitoring
        if 'monitoring' in components:
            print("\n--- Monitoring & Observability ---")
            monitoring = components['monitoring']
            print(f"  SNS Topics: {len(monitoring['sns_topics'])}")
            total_alarms = sum(len(alarms) for alarms in monitoring['alarms'].values())
            print(f"  CloudWatch Alarms: {total_alarms}")
            print(f"  Dashboards: {len(monitoring['dashboards'])}")
            print(f"  X-Ray Enabled Functions: {len(monitoring['xray_enabled'])}")
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("\n1. Subscribe to SNS topic for alarm notifications:")
        if 'monitoring' in components and 'alarms' in components['monitoring']['sns_topics']:
            print(f"   aws sns subscribe --topic-arn {components['monitoring']['sns_topics']['alarms']} \\")
            print(f"     --protocol email --notification-endpoint your-email@example.com")
        
        print("\n2. View CloudWatch dashboard:")
        print(f"   https://console.aws.amazon.com/cloudwatch/home?region={self.region_name}#dashboards:")
        
        print("\n3. Test the fraud detection system:")
        print("   python demo_transaction_stream.py")
        
        print("\n4. Monitor system health:")
        print(f"   https://console.aws.amazon.com/cloudwatch/home?region={self.region_name}")
        
        print("\n" + "="*80 + "\n")


def main():
    """Main deployment script."""
    parser = argparse.ArgumentParser(
        description='Deploy complete AWS infrastructure for fraud detection system'
    )
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
    parser.add_argument(
        '--skip-bedrock',
        action='store_true',
        help='Skip Bedrock Agent deployment (useful for testing)'
    )
    
    args = parser.parse_args()
    
    try:
        deployer = FullInfrastructureDeployer(
            region_name=args.region,
            environment=args.environment
        )
        
        deployment_results = deployer.deploy_all()
        deployer.print_deployment_summary(deployment_results)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\nDeployment interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\nDeployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
