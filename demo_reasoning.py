#!/usr/bin/env python3
"""
Chain-of-Thought Reasoning Demo
Demonstrates the advanced reasoning capabilities for fraud detection
"""

import json
import sys
import os
from datetime import datetime

# Add reasoning_engine to path
sys.path.append('reasoning_engine')

def demo_chain_of_thought_reasoning():
    """Demonstrate chain-of-thought reasoning with sample transactions"""
    print("🧠 Chain-of-Thought Reasoning Demo")
    print("=" * 50)
    
    try:
        from chain_of_thought import ChainOfThoughtReasoner, ReasoningStepType
        from confidence_scoring import ConfidenceScorer
        from step_tracker import ReasoningStepTracker
        
        print("✅ Successfully imported reasoning modules")
        
        # Create reasoner (will use mock for demo without AWS)
        reasoner = ChainOfThoughtReasoner()
        scorer = ConfidenceScorer()
        tracker = ReasoningStepTracker()
        
        print("✅ Initialized reasoning components")
        
        # Sample transactions for demo
        transactions = [
            {
                'id': 'demo_tx_001',
                'user_id': 'demo_user_001',
                'amount': 50.0,
                'currency': 'USD',
                'merchant': 'STARBUCKS',
                'category': 'RESTAURANT',
                'location': 'NEW_YORK_NY',
                'timestamp': datetime.now().isoformat(),
                'card_type': 'CREDIT'
            },
            {
                'id': 'demo_tx_002',
                'user_id': 'demo_user_002',
                'amount': 15000.0,
                'currency': 'USD',
                'merchant': 'UNKNOWN_MERCHANT',
                'category': 'OTHER',
                'location': 'FOREIGN_COUNTRY',
                'timestamp': datetime.now().isoformat(),
                'card_type': 'CREDIT'
            },
            {
                'id': 'demo_tx_003',
                'user_id': 'demo_user_003',
                'amount': 2000000.0,
                'currency': 'UGX',
                'merchant': 'SHELL',
                'category': 'GAS',
                'location': 'HIGH_RISK_COUNTRY',
                'timestamp': datetime.now().isoformat(),
                'card_type': 'DEBIT'
            }
        ]
        
        print(f"\n🔍 Analyzing {len(transactions)} sample transactions...")
        
        for i, transaction in enumerate(transactions, 1):
            print(f"\n--- Transaction {i}: {transaction['id']} ---")
            print(f"Amount: {transaction['amount']} {transaction['currency']}")
            print(f"Merchant: {transaction['merchant']}")
            print(f"Location: {transaction['location']}")
            
            # Demo reasoning step creation
            step_id = f"demo_step_{i}"
            step_data = {
                'step_type': 'observation',
                'description': f'Analyzing transaction {transaction["id"]}',
                'input_data': transaction,
                'reasoning': f'Observing transaction patterns for {transaction["merchant"]}'
            }
            
            # Register with tracker
            tracker.register_step(step_id, step_data)
            tracker.start_step_execution(step_id)
            
            # Simulate reasoning result
            if transaction['amount'] > 10000 or 'UNKNOWN' in transaction['merchant']:
                result = {
                    'is_fraud': True,
                    'confidence': 0.85,
                    'risk_level': 'HIGH',
                    'reasoning': 'High amount or unknown merchant detected',
                    'evidence': [f"Amount: {transaction['amount']}", f"Merchant: {transaction['merchant']}"]
                }
            elif transaction['currency'] != 'USD' and transaction['amount'] > 1000000:
                result = {
                    'is_fraud': True,
                    'confidence': 0.75,
                    'risk_level': 'MEDIUM',
                    'reasoning': 'Large foreign currency transaction',
                    'evidence': [f"Currency: {transaction['currency']}", f"Amount: {transaction['amount']}"]
                }
            else:
                result = {
                    'is_fraud': False,
                    'confidence': 0.90,
                    'risk_level': 'LOW',
                    'reasoning': 'Normal transaction pattern',
                    'evidence': [f"Trusted merchant: {transaction['merchant']}", "Normal amount range"]
                }
            
            # Complete step execution
            tracker.complete_step_execution(step_id, result)
            
            # Demo confidence assessment
            reasoning_data = {
                'transaction': transaction,
                'reasoning': result['reasoning'],
                'evidence': result['evidence'],
                'confidence': result['confidence']
            }
            
            confidence_assessment = scorer.assess_confidence(reasoning_data)
            
            # Display results
            fraud_status = "🚨 FRAUD DETECTED" if result['is_fraud'] else "✅ APPROVED"
            print(f"Result: {fraud_status}")
            print(f"Confidence: {result['confidence']:.2f} ({confidence_assessment.confidence_level})")
            print(f"Risk Level: {result['risk_level']}")
            print(f"Reasoning: {result['reasoning']}")
            print(f"Evidence: {', '.join(result['evidence'])}")
            
            # Show confidence factors
            print("Confidence Factors:")
            for factor in confidence_assessment.factors[:3]:  # Show top 3
                print(f"  - {factor.factor_type.value}: {factor.value:.2f}")
        
        # Show tracker summary
        print(f"\n📊 Reasoning Execution Summary:")
        summary = tracker.get_execution_summary()
        print(f"Total Steps: {summary['total_steps']}")
        print(f"Completed: {summary['completed_steps']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Average Confidence: {summary['average_confidence']:.2f}")
        
        # Show reasoning templates
        print(f"\n📝 Available Reasoning Templates:")
        for template_name in reasoner.reasoning_templates.keys():
            print(f"  - {template_name}")
        
        print(f"\n🎯 Chain-of-Thought Reasoning Demo Complete!")
        print("This demonstrates:")
        print("  ✅ Multi-step reasoning analysis")
        print("  ✅ Confidence scoring with multiple factors")
        print("  ✅ Step tracking and dependency management")
        print("  ✅ Evidence synthesis and validation")
        print("  ✅ Comprehensive fraud decision making")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure the reasoning_engine modules are available")
        return False
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return False

def demo_reasoning_step_types():
    """Demonstrate different reasoning step types"""
    print("\n🔄 Reasoning Step Types Demo")
    print("=" * 30)
    
    try:
        from chain_of_thought import ReasoningStepType
        
        print("Available reasoning step types:")
        for step_type in ReasoningStepType:
            print(f"  - {step_type.value}: {step_type.name}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_confidence_factors():
    """Demonstrate confidence factor types"""
    print("\n📊 Confidence Factor Types Demo")
    print("=" * 35)
    
    try:
        from confidence_scoring import ConfidenceFactorType
        
        print("Available confidence factors:")
        for factor_type in ConfidenceFactorType:
            print(f"  - {factor_type.value}: {factor_type.name}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_reasoning_tests():
    """Run the reasoning engine tests"""
    print("\n🧪 Running Reasoning Engine Tests")
    print("=" * 35)
    
    try:
        from test_reasoning import run_all_tests
        success = run_all_tests()
        return success
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main demo function"""
    print("🏦 Advanced Fraud Detection Reasoning System")
    print("=" * 50)
    
    demos = [
        ("Chain-of-Thought Reasoning", demo_chain_of_thought_reasoning),
        ("Reasoning Step Types", demo_reasoning_step_types),
        ("Confidence Factors", demo_confidence_factors),
        ("Unit Tests", run_reasoning_tests)
    ]
    
    results = {}
    
    for demo_name, demo_function in demos:
        print(f"\n🚀 Running: {demo_name}")
        try:
            success = demo_function()
            results[demo_name] = "✅ SUCCESS" if success else "❌ FAILED"
        except Exception as e:
            results[demo_name] = f"💥 ERROR: {str(e)}"
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 DEMO RESULTS SUMMARY")
    print("=" * 50)
    
    for demo_name, result in results.items():
        print(f"{result} {demo_name}")
    
    successful_demos = sum(1 for r in results.values() if "SUCCESS" in r)
    total_demos = len(results)
    
    print(f"\n🎯 Overall: {successful_demos}/{total_demos} demos successful")
    
    if successful_demos == total_demos:
        print("🎉 All reasoning demos completed successfully!")
        print("\n📚 Next Steps:")
        print("  1. Integrate with AWS Bedrock for real LLM reasoning")
        print("  2. Connect to the fraud detection agent orchestrator")
        print("  3. Implement explanation generation system (Task 2.2)")
        print("  4. Add adaptive reasoning capabilities (Task 2.3)")
    else:
        print("⚠️ Some demos had issues. Check the errors above.")

if __name__ == "__main__":
    main()