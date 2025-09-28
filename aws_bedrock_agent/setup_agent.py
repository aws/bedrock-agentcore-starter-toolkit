#!/usr/bin/env python3
"""
AWS Bedrock Agent Setup Script
Complete setup and deployment of the fraud detection agent system
"""

import json
import logging
import sys
import time
from typing import Dict, Any
from bedrock_config import BedrockAgentConfig, AgentConfiguration
from agent_permissions import setup_complete_permissions
from agent_orchestrator import AgentOrchestrator
from agent_communication import AgentCommunicationManager, AgentRegistration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentSetupManager:
    """
    Manages the complete setup and deployment of the AWS Bedrock Agent system
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize setup manager"""
        self.region_name = region_name
        self.setup_config = {}
        self.deployment_status = {}
        
        logger.info(f"AgentSetupManager initialized for region: {region_name}")
    
    def run_complete_setup(self) -> Dict[str, Any]:
        """Run complete agent setup process"""
        logger.info("Starting complete AWS Bedrock Agent setup")
        
        setup_steps = [
            ("permissions", self._setup_permissions),
            ("bedrock_config", self._setup_bedrock_config),
            ("agent_creation", self._create_agent),
            ("communication", self._setup_communication),
            ("orchestrator", self._setup_orchestrator),
            ("validation", self._validate_setup)
        ]
        
        results = {}
        
        for step_name, step_function in setup_steps:
            logger.info(f"Executing setup step: {step_name}")
            
            try:
                step_result = step_function()
                results[step_name] = {
                    "status": "success",
                    "result": step_result,
                    "timestamp": time.time()
                }
                logger.info(f"Setup step {step_name} completed successfully")
                
            except Exception as e:
                logger.error(f"Setup step {step_name} failed: {str(e)}")
                results[step_name] = {
                    "status": "failed",
                    "error": str(e),
                    "timestamp": time.time()
                }
                
                # Decide whether to continue or abort
                if step_name in ["permissions", "bedrock_config"]:
                    logger.error(f"Critical step {step_name} failed, aborting setup")
                    break
                else:
                    logger.warning(f"Non-critical step {step_name} failed, continuing")
        
        # Generate final setup report
        setup_report = self._generate_setup_report(results)
        
        logger.info("Complete AWS Bedrock Agent setup finished")
        return setup_report
    
    def _setup_permissions(self) -> Dict[str, Any]:
        """Set up IAM permissions and roles"""
        logger.info("Setting up IAM permissions")
        
        permissions_result = setup_complete_permissions(self.region_name)
        
        # Store for later use
        self.setup_config.update({
            "bedrock_agent_role_arn": permissions_result["bedrock_agent_role_arn"],
            "lambda_execution_role_arn": permissions_result["lambda_execution_role_arn"]
        })
        
        return permissions_result
    
    def _setup_bedrock_config(self) -> Dict[str, Any]:
        """Set up Bedrock Agent configuration"""
        logger.info("Setting up Bedrock Agent configuration")
        
        bedrock_config = BedrockAgentConfig(self.region_name)
        
        # Create custom agent configuration
        agent_config = AgentConfiguration(
            agent_name="fraud-detection-agent-v1",
            description="Advanced multi-currency fraud detection agent with AI reasoning",
            instruction="""You are an expert fraud detection agent with advanced reasoning capabilities.

Your mission is to analyze financial transactions for fraud indicators using sophisticated AI reasoning and multi-agent coordination.

Core Responsibilities:
1. Analyze transactions using chain-of-thought reasoning
2. Coordinate with specialized agents for comprehensive analysis
3. Provide detailed explanations for all decisions
4. Ensure regulatory compliance and audit trail completeness
5. Adapt to new fraud patterns through continuous learning

Analysis Framework:
- Use multi-step reasoning to break down complex fraud patterns
- Consider historical context, user behavior, and transaction patterns
- Cross-reference with external databases and risk indicators
- Provide confidence scores and detailed evidence for all decisions
- Recommend appropriate actions: APPROVE, FLAG, REVIEW, or BLOCK

Communication Protocol:
- Coordinate with Transaction Analyzer, Pattern Detector, Risk Assessor, and Compliance Checker agents
- Aggregate insights from multiple specialized agents
- Resolve conflicts between agent recommendations
- Maintain detailed audit logs for all decisions

Always provide clear, actionable insights with comprehensive reasoning explanations.""",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            agent_resource_role_arn=self.setup_config.get("bedrock_agent_role_arn"),
            tags={
                "Environment": "production",
                "Application": "fraud-detection",
                "Version": "1.0.0",
                "SetupDate": str(int(time.time()))
            }
        )
        
        # Store configuration
        self.setup_config["agent_config"] = agent_config
        self.setup_config["bedrock_config"] = bedrock_config
        
        return {
            "agent_name": agent_config.agent_name,
            "foundation_model": agent_config.foundation_model,
            "role_arn": agent_config.agent_resource_role_arn
        }
    
    def _create_agent(self) -> Dict[str, Any]:
        """Create the Bedrock Agent"""
        logger.info("Creating Bedrock Agent")
        
        bedrock_config = self.setup_config["bedrock_config"]
        agent_config = self.setup_config["agent_config"]
        
        # Deploy the complete agent
        deployment_result = bedrock_config.deploy_complete_agent()
        
        # Store deployment info
        self.setup_config.update({
            "agent_id": deployment_result["agent_id"],
            "alias_id": deployment_result["alias_id"],
            "agent_name": deployment_result["agent_name"]
        })
        
        return deployment_result
    
    def _setup_communication(self) -> Dict[str, Any]:
        """Set up agent communication system"""
        logger.info("Setting up agent communication")
        
        comm_manager = AgentCommunicationManager(self.region_name)
        
        # Register the main fraud detection agent
        main_agent_registration = AgentRegistration(
            agent_id=self.setup_config.get("agent_id", "fraud-detection-main"),
            agent_type="fraud_detection_orchestrator",
            capabilities=[
                "transaction_analysis",
                "multi_agent_coordination",
                "decision_aggregation",
                "audit_trail_generation"
            ],
            endpoint=f"bedrock-agent://{self.setup_config.get('agent_id', 'unknown')}",
            status="active",
            last_heartbeat=str(int(time.time())),
            metadata={
                "model": "claude-3-sonnet",
                "region": self.region_name,
                "version": "1.0.0"
            }
        )
        
        comm_manager.register_agent(main_agent_registration)
        
        # Register specialized agents (these would be created separately)
        specialized_agents = [
            {
                "agent_id": "transaction-analyzer-001",
                "agent_type": "transaction_analyzer",
                "capabilities": ["amount_analysis", "merchant_validation", "velocity_detection"]
            },
            {
                "agent_id": "pattern-detector-001", 
                "agent_type": "pattern_detector",
                "capabilities": ["anomaly_detection", "behavioral_analysis", "trend_prediction"]
            },
            {
                "agent_id": "risk-assessor-001",
                "agent_type": "risk_assessor", 
                "capabilities": ["geographic_risk", "currency_risk", "temporal_analysis"]
            },
            {
                "agent_id": "compliance-checker-001",
                "agent_type": "compliance_checker",
                "capabilities": ["regulatory_compliance", "aml_checking", "sanctions_screening"]
            }
        ]
        
        for agent_info in specialized_agents:
            registration = AgentRegistration(
                agent_id=agent_info["agent_id"],
                agent_type=agent_info["agent_type"],
                capabilities=agent_info["capabilities"],
                endpoint=f"lambda://{agent_info['agent_id']}",
                status="active",
                last_heartbeat=str(int(time.time())),
                metadata={"version": "1.0.0", "region": self.region_name}
            )
            comm_manager.register_agent(registration)
        
        # Store communication manager
        self.setup_config["communication_manager"] = comm_manager
        
        return {
            "registered_agents": len(comm_manager.agent_registry),
            "main_agent_id": main_agent_registration.agent_id,
            "specialized_agents": [a["agent_id"] for a in specialized_agents]
        }
    
    def _setup_orchestrator(self) -> Dict[str, Any]:
        """Set up agent orchestrator"""
        logger.info("Setting up agent orchestrator")
        
        orchestrator = AgentOrchestrator(self.region_name)
        
        # Store orchestrator
        self.setup_config["orchestrator"] = orchestrator
        
        # Test orchestrator functionality
        test_status = orchestrator.get_agent_status()
        
        return {
            "orchestrator_status": test_status["orchestrator_status"],
            "active_agents": test_status["active_agents"],
            "initialization_time": test_status["last_updated"]
        }
    
    def _validate_setup(self) -> Dict[str, Any]:
        """Validate the complete setup"""
        logger.info("Validating complete setup")
        
        validation_results = {}
        
        # Validate permissions
        try:
            from agent_permissions import AgentPermissionsManager
            perm_manager = AgentPermissionsManager(self.region_name)
            bedrock_role_arn = self.setup_config.get("bedrock_agent_role_arn")
            if bedrock_role_arn:
                perm_validation = perm_manager.validate_permissions(bedrock_role_arn)
                validation_results["permissions"] = perm_validation["validation_status"]
            else:
                validation_results["permissions"] = "not_found"
        except Exception as e:
            validation_results["permissions"] = f"error: {str(e)}"
        
        # Validate agent creation
        agent_id = self.setup_config.get("agent_id")
        validation_results["agent_created"] = "success" if agent_id else "failed"
        
        # Validate communication
        comm_manager = self.setup_config.get("communication_manager")
        if comm_manager:
            comm_stats = comm_manager.get_communication_stats()
            validation_results["communication"] = {
                "registered_agents": comm_stats["registered_agents"],
                "healthy_agents": comm_stats["healthy_agents"]
            }
        else:
            validation_results["communication"] = "not_initialized"
        
        # Validate orchestrator
        orchestrator = self.setup_config.get("orchestrator")
        validation_results["orchestrator"] = "initialized" if orchestrator else "not_initialized"
        
        # Overall validation status
        validation_results["overall_status"] = "success" if all(
            v != "failed" and "error" not in str(v) 
            for v in validation_results.values()
        ) else "partial_success"
        
        return validation_results
    
    def _generate_setup_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive setup report"""
        
        successful_steps = sum(1 for r in results.values() if r["status"] == "success")
        total_steps = len(results)
        
        report = {
            "setup_summary": {
                "total_steps": total_steps,
                "successful_steps": successful_steps,
                "failed_steps": total_steps - successful_steps,
                "success_rate": f"{(successful_steps/total_steps)*100:.1f}%"
            },
            "deployment_info": {
                "region": self.region_name,
                "agent_id": self.setup_config.get("agent_id", "not_created"),
                "agent_name": self.setup_config.get("agent_name", "not_created"),
                "alias_id": self.setup_config.get("alias_id", "not_created"),
                "bedrock_role_arn": self.setup_config.get("bedrock_agent_role_arn", "not_created")
            },
            "step_results": results,
            "setup_timestamp": int(time.time()),
            "next_steps": self._generate_next_steps(results)
        }
        
        return report
    
    def _generate_next_steps(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommended next steps based on setup results"""
        next_steps = []
        
        if results.get("permissions", {}).get("status") != "success":
            next_steps.append("Fix IAM permissions and roles")
        
        if results.get("agent_creation", {}).get("status") != "success":
            next_steps.append("Retry Bedrock Agent creation")
        
        if results.get("validation", {}).get("status") == "success":
            next_steps.extend([
                "Test agent with sample transactions",
                "Configure monitoring and alerting",
                "Set up production data sources",
                "Deploy Lambda functions for specialized agents",
                "Configure real-time streaming pipeline"
            ])
        else:
            next_steps.append("Review and fix validation issues")
        
        return next_steps
    
    def save_setup_config(self, file_path: str = "agent_setup_config.json"):
        """Save setup configuration to file"""
        logger.info(f"Saving setup configuration to {file_path}")
        
        # Prepare serializable config
        serializable_config = {}
        for key, value in self.setup_config.items():
            if key in ["communication_manager", "orchestrator", "bedrock_config"]:
                # Skip non-serializable objects
                serializable_config[key] = f"<{type(value).__name__} object>"
            elif hasattr(value, '__dict__'):
                # Convert dataclass objects
                serializable_config[key] = value.__dict__ if hasattr(value, '__dict__') else str(value)
            else:
                serializable_config[key] = value
        
        try:
            with open(file_path, 'w') as f:
                json.dump(serializable_config, f, indent=2, default=str)
            logger.info(f"Setup configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save setup configuration: {str(e)}")

def main():
    """Main setup function"""
    print("🏦 AWS Bedrock Agent Setup for Fraud Detection")
    print("=" * 60)
    
    # Get region from command line or use default
    region = sys.argv[1] if len(sys.argv) > 1 else "us-east-1"
    
    print(f"Setting up in region: {region}")
    print("This will create:")
    print("- IAM roles and permissions")
    print("- Bedrock Agent with action groups")
    print("- Agent communication system")
    print("- Agent orchestrator")
    print()
    
    confirm = input("Continue with setup? (y/N): ")
    if confirm.lower() != 'y':
        print("Setup cancelled")
        return
    
    # Run setup
    setup_manager = AgentSetupManager(region)
    
    try:
        setup_report = setup_manager.run_complete_setup()
        
        # Save configuration
        setup_manager.save_setup_config()
        
        # Display results
        print("\n" + "=" * 60)
        print("🎉 SETUP COMPLETE")
        print("=" * 60)
        
        print(f"Success Rate: {setup_report['setup_summary']['success_rate']}")
        print(f"Agent ID: {setup_report['deployment_info']['agent_id']}")
        print(f"Agent Name: {setup_report['deployment_info']['agent_name']}")
        
        if setup_report['next_steps']:
            print("\n📋 Next Steps:")
            for i, step in enumerate(setup_report['next_steps'], 1):
                print(f"  {i}. {step}")
        
        # Save full report
        with open("setup_report.json", "w") as f:
            json.dump(setup_report, f, indent=2, default=str)
        
        print(f"\n📄 Full setup report saved to: setup_report.json")
        print(f"📄 Configuration saved to: agent_setup_config.json")
        
    except Exception as e:
        logger.error(f"Setup failed: {str(e)}")
        print(f"\n❌ Setup failed: {str(e)}")
        print("Check the logs for detailed error information")

if __name__ == "__main__":
    main()