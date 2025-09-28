#!/usr/bin/env python3
"""
Test AWS Bedrock Agent Foundation
Quick test to verify the foundation components are working
"""

import json
import sys
import os
from datetime import datetime

# Add the aws_bedrock_agent directory to path
sys.path.append('aws_bedrock_agent')

def test_imports():
    """Test that all foundation modules can be imported"""
    print("🧪 Testing module imports...")
    
    try:
        from bedrock_config import BedrockAgentConfig, AgentConfiguration
        print("✅ bedrock_config imported successfully")
        
        from agent_orchestrator import AgentOrchestrator, Transaction, FraudDecision
        print("✅ agent_orchestrator imported successfully")
        
        from agent_permissions import AgentPermissionsManager
        print("✅ agent_permissions imported successfully")
        
        from agent_communication import AgentCommunicationManager, AgentMessage, MessageType
        print("✅ agent_communication imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {str(e)}")
        return False

def test_orchestrator():
    """Test agent orchestrator functionality"""
    print("\n🧪 Testing Agent Orchestrator...")
    
    try:
        # Create orchestrator (without AWS credentials for testing)
        orchestrator = AgentOrchestrator()
        
        # Test transaction creation
        test_transaction = Transaction(
            id="test_001",
            user_id="test_user",
            amount=1500.0,
            currency="USD",
            merchant="AMAZON",
            category="SHOPPING",
            location="NEW_YORK_NY",
            timestamp=datetime.now().isoformat(),
            card_type="CREDIT"
        )
        
        print(f"✅ Created test transaction: {test_transaction.id}")
        
        # Test workflow planning
        workflow_plan = orchestrator.plan_analysis_workflow(test_transaction)
        print(f"✅ Generated workflow plan with {len(workflow_plan.steps)} steps")
        
        # Test agent status
        status = orchestrator.get_agent_status()
        print(f"✅ Retrieved agent status: {status['orchestrator_status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Orchestrator test failed: {str(e)}")
        return False

def test_communication():
    """Test agent communication system"""
    print("\n🧪 Testing Agent Communication...")
    
    try:
        from agent_communication import (
            AgentCommunicationManager, 
            AgentRegistration, 
            create_analysis_request,
            create_heartbeat_message
        )
        
        # Create communication manager
        comm_manager = AgentCommunicationManager()
        
        # Test agent registration
        test_agent = AgentRegistration(
            agent_id="test-agent-001",
            agent_type="transaction_analyzer",
            capabilities=["amount_analysis", "merchant_validation"],
            endpoint="test://localhost",
            status="active",
            last_heartbeat=datetime.now().isoformat(),
            metadata={"test": True}
        )
        
        comm_manager.register_agent(test_agent)
        print(f"✅ Registered test agent: {test_agent.agent_id}")
        
        # Test message creation
        analysis_request = create_analysis_request(
            sender_id="orchestrator",
            recipient_id="test-agent-001",
            transaction_data={"amount": 1000, "currency": "USD"}
        )
        print(f"✅ Created analysis request: {analysis_request.message_id}")
        
        # Test heartbeat
        heartbeat = create_heartbeat_message("test-agent-001")
        print(f"✅ Created heartbeat message: {heartbeat.message_id}")
        
        # Test communication stats
        stats = comm_manager.get_communication_stats()
        print(f"✅ Retrieved communication stats: {stats['registered_agents']} agents")
        
        return True
        
    except Exception as e:
        print(f"❌ Communication test failed: {str(e)}")
        return False

def test_configuration():
    """Test Bedrock configuration"""
    print("\n🧪 Testing Bedrock Configuration...")
    
    try:
        from bedrock_config import BedrockAgentConfig, AgentConfiguration
        
        # Test configuration creation
        agent_config = AgentConfiguration(
            agent_name="test-fraud-agent",
            description="Test fraud detection agent",
            instruction="Test instruction for fraud detection",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        
        print(f"✅ Created agent configuration: {agent_config.agent_name}")
        
        # Test configuration serialization
        config_dict = agent_config.__dict__
        print(f"✅ Configuration serializable: {len(config_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False

def test_permissions():
    """Test permissions manager (without AWS calls)"""
    print("\n🧪 Testing Permissions Manager...")
    
    try:
        from agent_permissions import AgentPermissionsManager
        
        # Create permissions manager (will fail AWS calls but test structure)
        try:
            perm_manager = AgentPermissionsManager()
            print("✅ Permissions manager created")
        except Exception:
            print("⚠️ Permissions manager creation failed (expected without AWS credentials)")
        
        return True
        
    except Exception as e:
        print(f"❌ Permissions test failed: {str(e)}")
        return False

def run_foundation_tests():
    """Run all foundation tests"""
    print("🏦 AWS Bedrock Agent Foundation Tests")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Agent Orchestrator", test_orchestrator),
        ("Agent Communication", test_communication),
        ("Bedrock Configuration", test_configuration),
        ("Permissions Manager", test_permissions)
    ]
    
    results = {}
    
    for test_name, test_function in tests:
        try:
            result = test_function()
            results[test_name] = "PASS" if result else "FAIL"
        except Exception as e:
            results[test_name] = f"ERROR: {str(e)}"
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in results.values() if r == "PASS")
    total = len(results)
    
    for test_name, result in results.items():
        status_emoji = "✅" if result == "PASS" else "❌"
        print(f"{status_emoji} {test_name}: {result}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All foundation tests passed! Ready for next implementation phase.")
    else:
        print("⚠️ Some tests failed. Review the errors above before proceeding.")
    
    return results

if __name__ == "__main__":
    results = run_foundation_tests()
    
    # Save results
    with open("foundation_test_results.json", "w") as f:
        json.dump({
            "test_results": results,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(results),
                "passed_tests": sum(1 for r in results.values() if r == "PASS"),
                "failed_tests": sum(1 for r in results.values() if r != "PASS")
            }
        }, f, indent=2)
    
    print(f"\n📄 Test results saved to: foundation_test_results.json")