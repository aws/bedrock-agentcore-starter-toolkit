#!/usr/bin/env python3
"""
Adaptive Reasoning System Demo
Demonstrates adaptive reasoning capabilities, pattern learning, and strategy adaptation
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add reasoning_engine to path
sys.path.append('reasoning_engine')

def demo_transaction_type_classification():
    """Demonstrate transaction type classification"""
    print("🏷️ Transaction Type Classification Demo")
    print("=" * 42)
    
    try:
        from adaptive_reasoning import TransactionTypeClassifier, TransactionType
        
        classifier = TransactionTypeClassifier()
        
        # Test various transaction types
        test_transactions = [
            {
                'name': 'High Value Purchase',
                'data': {
                    'amount': 15000,
                    'merchant_category': 'electronics',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                }
            },
            {
                'name': 'International Transaction',
                'data': {
                    'amount': 500,
                    'merchant_category': 'retail',
                    'location_type': 'foreign_country',
                    'payment_method': 'card'
                }
            },
            {
                'name': 'Wire Transfer',
                'data': {
                    'amount': 3000,
                    'merchant_category': 'financial',
                    'location_type': 'domestic',
                    'payment_method': 'wire_transfer'
                }
            },
            {
                'name': 'ATM Withdrawal',
                'data': {
                    'amount': 300,
                    'merchant_category': 'atm',
                    'location_type': 'domestic',
                    'payment_method': 'atm'
                }
            },
            {
                'name': 'Online Purchase',
                'data': {
                    'amount': 150,
                    'merchant_category': 'ecommerce',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                }
            },
            {
                'name': 'Mobile Payment',
                'data': {
                    'amount': 25,
                    'merchant_category': 'coffee_shop',
                    'location_type': 'domestic',
                    'payment_method': 'mobile_app'
                }
            }
        ]
        
        for transaction in test_transactions:
            tx_type = classifier.classify(transaction['data'])
            print(f"\n--- {transaction['name']} ---")
            print(f"Amount: ${transaction['data']['amount']:,}")
            print(f"Merchant: {transaction['data']['merchant_category']}")
            print(f"Payment Method: {transaction['data']['payment_method']}")
            print(f"🏷️ Classified as: {tx_type.value.upper()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_strategy_selection():
    """Demonstrate reasoning strategy selection"""
    print("\n🎯 Reasoning Strategy Selection Demo")
    print("=" * 40)
    
    try:
        from adaptive_reasoning import (
            AdaptiveReasoningEngine, 
            TransactionType, 
            ReasoningStrategy,
            LearningMode
        )
        
        engine = AdaptiveReasoningEngine(LearningMode.HYBRID_LEARNING)
        
        # Test strategy selection for different scenarios
        test_scenarios = [
            {
                'name': 'High Value Domestic',
                'transaction': {
                    'amount': 20000,
                    'merchant_category': 'jewelry',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                },
                'context': {'user_risk_level': 'medium'}
            },
            {
                'name': 'International Small Amount',
                'transaction': {
                    'amount': 50,
                    'merchant_category': 'restaurant',
                    'location_type': 'foreign_country',
                    'payment_method': 'card'
                },
                'context': {'user_risk_level': 'low'}
            },
            {
                'name': 'Frequent ATM Usage',
                'transaction': {
                    'amount': 200,
                    'merchant_category': 'atm',
                    'location_type': 'domestic',
                    'payment_method': 'atm'
                },
                'context': {'user_risk_level': 'high', 'recent_velocity': 'high'}
            },
            {
                'name': 'Unknown Merchant',
                'transaction': {
                    'amount': 1500,
                    'merchant_category': 'unknown',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                },
                'context': {'user_risk_level': 'medium'}
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n--- {scenario['name']} ---")
            
            # Classify transaction type
            tx_type = engine.classify_transaction_type(scenario['transaction'])
            
            # Select strategy
            strategy, config = engine.select_reasoning_strategy(
                scenario['transaction'], scenario['context']
            )
            
            print(f"Transaction Type: {tx_type.value}")
            print(f"Selected Strategy: {strategy.value}")
            print(f"Confidence Threshold: {config.get('confidence_threshold', 'N/A')}")
            print(f"Key Config: {', '.join([f'{k}: {v}' for k, v in list(config.items())[:3]])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_pattern_learning():
    """Demonstrate pattern learning capabilities"""
    print("\n🧠 Pattern Learning Demo")
    print("=" * 27)
    
    try:
        from adaptive_reasoning import PatternLearner
        
        learner = PatternLearner()
        
        print("Training pattern learner with sample data...")
        
        # Train with fraud patterns
        fraud_patterns = [
            {
                'features': {
                    'amount_category': 'high',
                    'location_risk': 'high',
                    'merchant_category': 'unknown',
                    'time_of_day': 'unusual'
                },
                'outcome': 'fraud',
                'confidence': 0.9
            },
            {
                'features': {
                    'amount_category': 'high',
                    'location_risk': 'high',
                    'merchant_category': 'unknown',
                    'time_of_day': 'unusual'
                },
                'outcome': 'fraud',
                'confidence': 0.85
            },
            {
                'features': {
                    'amount_category': 'high',
                    'location_risk': 'high',
                    'merchant_category': 'unknown',
                    'time_of_day': 'unusual'
                },
                'outcome': 'fraud',
                'confidence': 0.92
            }
        ]
        
        # Train with legitimate patterns
        legitimate_patterns = [
            {
                'features': {
                    'amount_category': 'normal',
                    'location_risk': 'low',
                    'merchant_category': 'trusted',
                    'time_of_day': 'normal'
                },
                'outcome': 'legitimate',
                'confidence': 0.8
            },
            {
                'features': {
                    'amount_category': 'normal',
                    'location_risk': 'low',
                    'merchant_category': 'trusted',
                    'time_of_day': 'normal'
                },
                'outcome': 'legitimate',
                'confidence': 0.85
            }
        ]
        
        # Train the learner
        all_patterns = fraud_patterns + legitimate_patterns
        for pattern in all_patterns:
            learner.learn_pattern(
                pattern['features'], 
                pattern['outcome'], 
                pattern['confidence']
            )
        
        print(f"✅ Trained with {len(all_patterns)} patterns")
        
        # Test predictions
        test_cases = [
            {
                'name': 'High Risk Transaction',
                'features': {
                    'amount_category': 'high',
                    'location_risk': 'high',
                    'merchant_category': 'unknown',
                    'time_of_day': 'unusual'
                }
            },
            {
                'name': 'Normal Transaction',
                'features': {
                    'amount_category': 'normal',
                    'location_risk': 'low',
                    'merchant_category': 'trusted',
                    'time_of_day': 'normal'
                }
            },
            {
                'name': 'Unknown Pattern',
                'features': {
                    'amount_category': 'very_high',
                    'location_risk': 'unknown',
                    'merchant_category': 'new',
                    'time_of_day': 'midnight'
                }
            }
        ]
        
        print("\n🔮 Pattern Predictions:")
        for test_case in test_cases:
            prediction, confidence = learner.get_pattern_prediction(test_case['features'])
            
            print(f"\n--- {test_case['name']} ---")
            print(f"Features: {test_case['features']}")
            print(f"Prediction: {prediction}")
            print(f"Confidence: {confidence:.2f}")
            
            if prediction == 'fraud':
                print("🚨 High fraud risk detected")
            elif prediction == 'legitimate':
                print("✅ Appears legitimate")
            else:
                print("❓ Unknown pattern - requires analysis")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_adaptive_reasoning_engine():
    """Demonstrate complete adaptive reasoning engine"""
    print("\n🔄 Adaptive Reasoning Engine Demo")
    print("=" * 38)
    
    try:
        from adaptive_reasoning import (
            AdaptiveReasoningEngine,
            LearningFeedback,
            LearningMode,
            TransactionType,
            ReasoningStrategy
        )
        
        engine = AdaptiveReasoningEngine(LearningMode.HYBRID_LEARNING)
        
        print("🎯 Testing adaptive reasoning workflow...")
        
        # Simulate reasoning session
        transaction_data = {
            'transaction_id': 'demo_tx_001',
            'amount': 5000,
            'merchant_category': 'electronics',
            'location_type': 'foreign_country',
            'payment_method': 'card'
        }
        
        context = {
            'user_risk_level': 'medium',
            'time_of_day': 22,  # 10 PM
            'recent_transactions': 3
        }
        
        # Step 1: Classify and select strategy
        tx_type = engine.classify_transaction_type(transaction_data)
        strategy, config = engine.select_reasoning_strategy(transaction_data, context)
        
        print(f"\n--- Initial Analysis ---")
        print(f"Transaction Type: {tx_type.value}")
        print(f"Selected Strategy: {strategy.value}")
        print(f"Strategy Config: {json.dumps(config, indent=2)[:200]}...")
        
        # Step 2: Simulate reasoning result
        reasoning_result = {
            'reasoning_id': 'demo_reasoning_001',
            'transaction_id': transaction_data['transaction_id'],
            'steps': [
                {
                    'step_type': 'observation',
                    'output': {
                        'key_findings': ['international_transaction', 'moderate_amount'],
                        'confidence': 0.8
                    },
                    'evidence': ['Location: foreign_country', 'Amount: $5000'],
                    'confidence': 0.8
                },
                {
                    'step_type': 'risk_assessment',
                    'output': {
                        'risk_level': 'MEDIUM',
                        'primary_concerns': ['Location risk', 'Evening transaction'],
                        'confidence': 0.75
                    },
                    'evidence': ['International location', 'Late hour transaction'],
                    'confidence': 0.75
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.72,
                'risk_level': 'MEDIUM',
                'recommended_action': 'REVIEW',
                'primary_concerns': ['International location', 'Evening transaction']
            }
        }
        
        print(f"\n--- Reasoning Result ---")
        print(f"Decision: {reasoning_result['final_decision']['recommended_action']}")
        print(f"Confidence: {reasoning_result['final_decision']['confidence']:.2f}")
        print(f"Risk Level: {reasoning_result['final_decision']['risk_level']}")
        
        # Step 3: Provide feedback and adapt
        feedback = LearningFeedback(
            feedback_id='demo_feedback_001',
            transaction_id=transaction_data['transaction_id'],
            reasoning_id=reasoning_result['reasoning_id'],
            original_decision=reasoning_result['final_decision']['recommended_action'],
            actual_outcome='legitimate',  # Transaction was actually legitimate
            confidence_was_correct=True,  # Confidence was appropriate for REVIEW
            strategy_used=strategy,
            transaction_type=tx_type,
            feedback_timestamp=datetime.now().isoformat(),
            feedback_source='manual'
        )
        
        adaptation_result = engine.adapt_reasoning_strategy(reasoning_result, feedback)
        
        print(f"\n--- Adaptation Result ---")
        print(f"Adaptations Applied: {adaptation_result['adaptations_applied']}")
        print(f"Strategy Updated: {adaptation_result['strategy_updated']}")
        print(f"Learning Mode: {adaptation_result['learning_mode']}")
        
        if adaptation_result.get('recommendations'):
            print("Recommendations:")
            for rec in adaptation_result['recommendations'][:3]:
                print(f"  • {rec.get('recommendation', 'N/A')}: {rec.get('reason', 'N/A')}")
        
        # Step 4: Show statistics
        stats = engine.get_adaptation_statistics()
        
        print(f"\n--- Engine Statistics ---")
        print(f"Total Patterns: {stats['total_patterns']}")
        print(f"Total Feedback Items: {stats['total_feedback_items']}")
        print(f"Learning Mode: {stats['learning_mode']}")
        
        if stats.get('patterns_by_transaction_type'):
            print("Patterns by Transaction Type:")
            for tx_type, count in stats['patterns_by_transaction_type'].items():
                print(f"  • {tx_type}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_adaptive_integration():
    """Demonstrate adaptive integration with chain-of-thought"""
    print("\n🔗 Adaptive Integration Demo")
    print("=" * 32)
    
    try:
        from adaptive_integration import AdaptiveChainOfThoughtReasoner
        from adaptive_reasoning import LearningMode
        
        # Create adaptive reasoner
        reasoner = AdaptiveChainOfThoughtReasoner(LearningMode.SUPERVISED)
        
        # Mock the base reasoner for demo purposes
        class MockBaseReasoner:
            def __init__(self):
                self.confidence_threshold = 0.7
                self.require_multiple_evidence = False
                self.evidence_weight_multiplier = 1.0
                self.velocity_analysis_enabled = False
                self.amount_analysis_enhanced = False
                self.location_analysis_enhanced = False
                self.behavioral_analysis_enabled = False
                self.max_reasoning_steps = 10
                self.reasoning_timeout_ms = 5000
            
            def reason_about_transaction(self, transaction_data, context=None, user_history=None):
                return {
                    'reasoning_id': f'mock_reasoning_{int(datetime.now().timestamp())}',
                    'transaction_id': transaction_data.get('transaction_id', 'unknown'),
                    'overall_confidence': 0.78,
                    'total_processing_time_ms': 1800.0,
                    'steps': [
                        {
                            'step_type': 'observation',
                            'confidence': 0.8,
                            'output': {'key_findings': ['normal_amount', 'trusted_merchant']}
                        },
                        {
                            'step_type': 'conclusion',
                            'confidence': 0.76,
                            'output': {'is_fraud': False, 'recommended_action': 'APPROVE'}
                        }
                    ],
                    'final_decision': {
                        'is_fraud': False,
                        'confidence': 0.78,
                        'recommended_action': 'APPROVE',
                        'risk_level': 'LOW'
                    }
                }
            
            def reset_to_defaults(self):
                pass
        
        reasoner.base_reasoner = MockBaseReasoner()
        
        print("🎯 Testing adaptive chain-of-thought integration...")
        
        # Test different transaction scenarios
        test_scenarios = [
            {
                'name': 'Regular Purchase',
                'transaction': {
                    'transaction_id': 'integration_tx_001',
                    'amount': 250,
                    'merchant_category': 'grocery',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                },
                'context': {'user_risk_level': 'low'}
            },
            {
                'name': 'High Value Purchase',
                'transaction': {
                    'transaction_id': 'integration_tx_002',
                    'amount': 12000,
                    'merchant_category': 'electronics',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                },
                'context': {'user_risk_level': 'medium'}
            },
            {
                'name': 'International Transaction',
                'transaction': {
                    'transaction_id': 'integration_tx_003',
                    'amount': 800,
                    'merchant_category': 'hotel',
                    'location_type': 'foreign_country',
                    'payment_method': 'card'
                },
                'context': {'user_risk_level': 'low'}
            }
        ]
        
        reasoning_sessions = []
        
        for scenario in test_scenarios:
            print(f"\n--- {scenario['name']} ---")
            
            # Perform adaptive reasoning
            result = reasoner.reason_about_transaction(
                scenario['transaction'], 
                scenario['context']
            )
            
            reasoning_sessions.append(result)
            
            # Display results
            adaptive_info = result['adaptive_reasoning']
            print(f"Transaction Type: {adaptive_info['transaction_type']}")
            print(f"Strategy Used: {adaptive_info['strategy_used']}")
            print(f"Original Confidence: {result['overall_confidence']:.2f}")
            print(f"Adaptive Confidence: {result['adaptive_confidence']:.2f}")
            print(f"Decision: {result['final_decision']['recommended_action']}")
            
            # Show strategy insights
            insights = adaptive_info['strategy_insights']
            print(f"Strategy Rationale: {insights['strategy_rationale'][:100]}...")
            print(f"Key Focus Areas: {', '.join(insights['key_focus_areas'][:2])}")
        
        # Demonstrate feedback processing
        print(f"\n--- Feedback Processing ---")
        
        # Provide feedback for first session
        first_session = reasoning_sessions[0]
        reasoning_id = first_session['adaptive_reasoning']['reasoning_id']
        
        feedback_result = reasoner.provide_feedback(reasoning_id, 'legitimate', 'automated')
        
        print(f"Feedback Status: {feedback_result['status']}")
        print(f"Feedback ID: {feedback_result.get('feedback_id', 'N/A')}")
        print(f"Adaptations Applied: {feedback_result.get('adaptations_applied', 0)}")
        
        # Show adaptive statistics
        stats = reasoner.get_adaptive_statistics()
        
        print(f"\n--- Adaptive Statistics ---")
        print(f"Reasoning Sessions: {stats['reasoning_sessions']}")
        print(f"Total Adaptations: {stats['adaptation_metrics']['total_adaptations']}")
        
        if stats.get('recent_strategy_usage'):
            print("Recent Strategy Usage:")
            for strategy, count in stats['recent_strategy_usage'].items():
                print(f"  • {strategy}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_learning_and_adaptation():
    """Demonstrate learning and adaptation over time"""
    print("\n📈 Learning and Adaptation Over Time Demo")
    print("=" * 46)
    
    try:
        from adaptive_integration import AdaptiveChainOfThoughtReasoner
        from adaptive_reasoning import LearningMode
        
        reasoner = AdaptiveChainOfThoughtReasoner(LearningMode.HYBRID_LEARNING)
        
        # Mock base reasoner
        class MockLearningReasoner:
            def __init__(self):
                self.confidence_threshold = 0.7
                self.require_multiple_evidence = False
                self.evidence_weight_multiplier = 1.0
                self.max_reasoning_steps = 10
                self.reasoning_timeout_ms = 5000
            
            def reason_about_transaction(self, transaction_data, context=None, user_history=None):
                # Simulate varying confidence based on transaction characteristics
                amount = transaction_data.get('amount', 0)
                location = transaction_data.get('location_type', 'domestic')
                
                base_confidence = 0.75
                if amount > 10000:
                    base_confidence -= 0.1
                if location == 'foreign_country':
                    base_confidence -= 0.05
                
                is_fraud = base_confidence < 0.6
                action = 'BLOCK' if is_fraud else 'APPROVE' if base_confidence > 0.8 else 'REVIEW'
                
                return {
                    'reasoning_id': f'learning_reasoning_{int(datetime.now().timestamp())}',
                    'transaction_id': transaction_data.get('transaction_id', 'unknown'),
                    'overall_confidence': base_confidence,
                    'total_processing_time_ms': 1500.0,
                    'steps': [
                        {
                            'step_type': 'analysis',
                            'confidence': base_confidence,
                            'output': {'risk_assessment': 'completed'}
                        }
                    ],
                    'final_decision': {
                        'is_fraud': is_fraud,
                        'confidence': base_confidence,
                        'recommended_action': action,
                        'risk_level': 'HIGH' if is_fraud else 'LOW'
                    }
                }
            
            def reset_to_defaults(self):
                pass
        
        reasoner.base_reasoner = MockLearningReasoner()
        
        print("🎯 Simulating learning over multiple transactions...")
        
        # Simulate a series of transactions with feedback
        transaction_series = [
            {
                'transaction': {
                    'transaction_id': f'learning_tx_{i:03d}',
                    'amount': 1000 + (i * 500),
                    'merchant_category': 'retail' if i % 2 == 0 else 'online',
                    'location_type': 'domestic' if i < 5 else 'foreign_country',
                    'payment_method': 'card'
                },
                'actual_outcome': 'legitimate' if i % 3 != 0 else 'fraud'
            }
            for i in range(10)
        ]
        
        results = []
        
        print(f"\nProcessing {len(transaction_series)} transactions...")
        
        for i, tx_data in enumerate(transaction_series):
            # Perform reasoning
            result = reasoner.reason_about_transaction(tx_data['transaction'])
            results.append(result)
            
            # Provide feedback after a short delay
            reasoning_id = result['adaptive_reasoning']['reasoning_id']
            feedback_result = reasoner.provide_feedback(
                reasoning_id, 
                tx_data['actual_outcome'], 
                'automated'
            )
            
            # Show progress every few transactions
            if (i + 1) % 3 == 0:
                decision = result['final_decision']['recommended_action']
                confidence = result['adaptive_confidence']
                strategy = result['adaptive_reasoning']['strategy_used']
                
                print(f"Transaction {i+1:2d}: {decision:6s} (conf: {confidence:.2f}) [{strategy}]")
        
        # Show learning progress
        print(f"\n--- Learning Progress ---")
        
        stats = reasoner.get_adaptive_statistics()
        
        print(f"Total Reasoning Sessions: {stats['reasoning_sessions']}")
        print(f"Total Adaptations: {stats['adaptation_metrics']['total_adaptations']}")
        print(f"Successful Adaptations: {stats['adaptation_metrics']['successful_adaptations']}")
        
        if stats.get('performance_metrics'):
            perf = stats['performance_metrics']
            print(f"Average Confidence: {perf['average_confidence']:.3f}")
            print(f"Average Processing Time: {perf['average_processing_time_ms']:.0f}ms")
            print(f"Average Steps per Session: {perf['average_steps_per_session']:.1f}")
        
        # Show strategy evolution
        if stats.get('recent_strategy_usage'):
            print(f"\nStrategy Usage Distribution:")
            total_usage = sum(stats['recent_strategy_usage'].values())
            for strategy, count in stats['recent_strategy_usage'].items():
                percentage = (count / total_usage) * 100
                print(f"  • {strategy:20s}: {count:2d} ({percentage:4.1f}%)")
        
        # Show transaction type distribution
        if stats.get('transaction_type_distribution'):
            print(f"\nTransaction Type Distribution:")
            total_types = sum(stats['transaction_type_distribution'].values())
            for tx_type, count in stats['transaction_type_distribution'].items():
                percentage = (count / total_types) * 100
                print(f"  • {tx_type:20s}: {count:2d} ({percentage:4.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main demo function"""
    print("🤖 Adaptive Reasoning System Demo")
    print("=" * 40)
    
    demos = [
        ("Transaction Type Classification", demo_transaction_type_classification),
        ("Strategy Selection", demo_strategy_selection),
        ("Pattern Learning", demo_pattern_learning),
        ("Adaptive Reasoning Engine", demo_adaptive_reasoning_engine),
        ("Adaptive Integration", demo_adaptive_integration),
        ("Learning and Adaptation", demo_learning_and_adaptation)
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
    print("\n" + "=" * 40)
    print("📋 ADAPTIVE REASONING DEMO RESULTS")
    print("=" * 40)
    
    for demo_name, result in results.items():
        print(f"{result} {demo_name}")
    
    successful_demos = sum(1 for r in results.values() if "SUCCESS" in r)
    total_demos = len(results)
    
    print(f"\n🎯 Overall: {successful_demos}/{total_demos} demos successful")
    
    if successful_demos == total_demos:
        print("🎉 All adaptive reasoning demos completed successfully!")
        print("\n📚 System Capabilities Demonstrated:")
        print("  ✅ Intelligent transaction type classification")
        print("  ✅ Dynamic reasoning strategy selection")
        print("  ✅ Pattern learning from transaction data")
        print("  ✅ Adaptive reasoning engine with feedback loops")
        print("  ✅ Seamless integration with chain-of-thought")
        print("  ✅ Continuous learning and adaptation over time")
        print("  ✅ Performance tracking and optimization")
        print("  ✅ Multi-mode learning (supervised, unsupervised, hybrid)")
    else:
        print("⚠️ Some demos had issues. Check the errors above.")

if __name__ == "__main__":
    main()