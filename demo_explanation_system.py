#!/usr/bin/env python3
"""
Explanation System Demo
Demonstrates the complete explanation generation and validation system
"""

import json
import sys
import os
from datetime import datetime

# Add reasoning_engine to path
sys.path.append('reasoning_engine')

def demo_explanation_generation():
    """Demonstrate explanation generation for different audiences"""
    print("📝 Explanation Generation Demo")
    print("=" * 35)
    
    try:
        from explanation_generator import (
            ExplanationGenerator, 
            ExplanationStyle, 
            ExplanationLevel
        )
        
        generator = ExplanationGenerator()
        
        # Sample fraud case
        fraud_case = {
            'reasoning_id': 'demo_fraud_001',
            'transaction_id': 'demo_tx_fraud',
            'overall_confidence': 0.92,
            'total_processing_time_ms': 2800.0,
            'steps': [
                {
                    'step_id': 'obs_1',
                    'step_type': 'observation',
                    'description': 'Transaction observation',
                    'reasoning': 'Observed extremely high transaction amount at unknown merchant in high-risk location',
                    'output': {
                        'key_findings': ['Extremely high amount', 'Unknown merchant', 'High-risk location'],
                        'confidence': 0.95
                    },
                    'evidence': ['Amount: $25000', 'Merchant: UNKNOWN_MERCHANT', 'Location: HIGH_RISK_COUNTRY'],
                    'confidence': 0.95
                },
                {
                    'step_id': 'risk_1',
                    'step_type': 'risk_assessment',
                    'description': 'Risk factor analysis',
                    'reasoning': 'Multiple high-risk factors present including amount, merchant, and location',
                    'output': {
                        'risk_level': 'HIGH',
                        'primary_concerns': ['Amount threshold exceeded', 'Merchant verification failed', 'Geographic risk'],
                        'confidence': 0.90
                    },
                    'evidence': ['5x normal amount', 'Unverified merchant', 'Sanctioned region'],
                    'confidence': 0.90
                }
            ],
            'final_decision': {
                'is_fraud': True,
                'confidence': 0.92,
                'risk_level': 'HIGH',
                'recommended_action': 'BLOCK',
                'primary_concerns': ['Extremely high amount', 'Unknown merchant', 'High-risk location']
            }
        }
        
        # Generate explanations for different audiences
        audiences = [
            (ExplanationStyle.CUSTOMER, "Customer"),
            (ExplanationStyle.BUSINESS, "Business User"),
            (ExplanationStyle.TECHNICAL, "Technical Team"),
            (ExplanationStyle.REGULATORY, "Regulatory Authority")
        ]
        
        for style, audience_name in audiences:
            print(f"\n--- {audience_name} Explanation ---")
            
            explanation = generator.generate_explanation(
                fraud_case,
                style=style,
                level=ExplanationLevel.DETAILED
            )
            
            print(f"Style: {style.value}")
            print(f"Decision: {explanation.decision}")
            print(f"Confidence: {explanation.confidence:.1%}")
            print(f"Executive Summary:")
            print(f"  {explanation.executive_summary}")
            print(f"Key Factors: {', '.join(explanation.key_factors[:3])}")
            print(f"Sections: {len(explanation.sections)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_reasoning_trails():
    """Demonstrate reasoning trail formatting"""
    print("\n🛤️ Reasoning Trail Demo")
    print("=" * 25)
    
    try:
        from reasoning_trail import ReasoningTrailFormatter, TrailFormat
        
        formatter = ReasoningTrailFormatter()
        
        # Sample reasoning for trail demo
        reasoning_data = {
            'reasoning_id': 'trail_demo_001',
            'transaction_id': 'trail_tx_001',
            'overall_confidence': 0.78,
            'total_processing_time_ms': 2200.0,
            'steps': [
                {
                    'step_id': 'trail_step_1',
                    'step_type': 'observation',
                    'description': 'Initial observation',
                    'reasoning': 'Examined transaction for basic fraud indicators',
                    'output': {'initial_assessment': 'Requires further analysis'},
                    'evidence': ['Moderate amount', 'New merchant'],
                    'confidence': 0.6,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 800.0,
                    'dependencies': []
                },
                {
                    'step_id': 'trail_step_2',
                    'step_type': 'analysis',
                    'description': 'Detailed analysis',
                    'reasoning': 'Performed comprehensive pattern analysis',
                    'output': {'pattern_analysis': 'Consistent with user behavior'},
                    'evidence': ['Historical consistency', 'Normal timing'],
                    'confidence': 0.85,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 1000.0,
                    'dependencies': ['trail_step_1']
                },
                {
                    'step_id': 'trail_step_3',
                    'step_type': 'conclusion',
                    'description': 'Final decision',
                    'reasoning': 'Based on comprehensive analysis, transaction appears legitimate',
                    'output': {'is_fraud': False, 'recommended_action': 'APPROVE'},
                    'evidence': ['Consistent patterns', 'No major risk factors'],
                    'confidence': 0.78,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 400.0,
                    'dependencies': ['trail_step_1', 'trail_step_2']
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.78,
                'recommended_action': 'APPROVE'
            }
        }
        
        # Test different trail formats
        formats = [
            (TrailFormat.NARRATIVE, "Narrative Story"),
            (TrailFormat.STRUCTURED, "Structured Documentation"),
            (TrailFormat.TIMELINE, "Timeline View"),
            (TrailFormat.AUDIT, "Regulatory Audit")
        ]
        
        for trail_format, format_name in formats:
            print(f"\n--- {format_name} ---")
            
            trail = formatter.create_reasoning_trail(reasoning_data, trail_format)
            
            print(f"Trail ID: {trail.trail_id}")
            print(f"Steps: {len(trail.steps)}")
            print(f"Processing Time: {trail.total_processing_time_ms:.0f}ms")
            print(f"Decision: {trail.decision_summary}")
            
            # Show a snippet of the formatted trail
            if trail_format == TrailFormat.NARRATIVE:
                formatted = formatter.format_trail_as_narrative(trail)
            elif trail_format == TrailFormat.STRUCTURED:
                formatted = formatter.format_trail_as_structured(trail)
            elif trail_format == TrailFormat.TIMELINE:
                formatted = formatter.format_trail_as_timeline(trail)
            else:  # AUDIT
                formatted = formatter.format_trail_for_audit(trail)
            
            # Show first 200 characters
            print(f"Preview: {formatted[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_explanation_validation():
    """Demonstrate explanation quality validation"""
    print("\n✅ Explanation Validation Demo")
    print("=" * 32)
    
    try:
        from explanation_generator import ExplanationGenerator, ExplanationStyle
        from explanation_validator import ExplanationValidator
        
        generator = ExplanationGenerator()
        validator = ExplanationValidator()
        
        # Test cases: good and poor explanations
        test_cases = [
            {
                'name': 'High Quality Explanation',
                'reasoning_result': {
                    'reasoning_id': 'quality_test_good',
                    'transaction_id': 'quality_tx_good',
                    'overall_confidence': 0.88,
                    'steps': [
                        {
                            'step_type': 'observation',
                            'reasoning': 'Comprehensive analysis of transaction characteristics including amount, merchant verification, location assessment, and user behavior patterns',
                            'output': {'key_findings': ['Normal amount', 'Verified merchant', 'Expected location']},
                            'evidence': ['Amount within normal range: $150', 'Merchant verified: AMAZON', 'Location matches user profile: NEW_YORK'],
                            'confidence': 0.9
                        }
                    ],
                    'final_decision': {
                        'is_fraud': False,
                        'confidence': 0.88,
                        'risk_level': 'LOW',
                        'recommended_action': 'APPROVE',
                        'primary_concerns': []
                    }
                }
            },
            {
                'name': 'Poor Quality Explanation',
                'reasoning_result': {
                    'reasoning_id': 'quality_test_poor',
                    'transaction_id': 'quality_tx_poor',
                    'overall_confidence': 0.3,
                    'steps': [
                        {
                            'step_type': 'analysis',
                            'reasoning': 'Bad.',  # Too short
                            'output': {},  # No output
                            'evidence': [],  # No evidence
                            'confidence': 0.3
                        }
                    ],
                    'final_decision': {
                        'is_fraud': True,
                        'confidence': 0.3,
                        'risk_level': 'LOW',  # Inconsistent with fraud decision
                        'recommended_action': 'BLOCK'
                    }
                }
            }
        ]
        
        for test_case in test_cases:
            print(f"\n--- {test_case['name']} ---")
            
            # Generate explanation
            explanation = generator.generate_explanation(
                test_case['reasoning_result'],
                style=ExplanationStyle.BUSINESS
            )
            
            # Validate explanation
            explanation_dict = json.loads(generator.format_explanation_as_json(explanation))
            quality_report = validator.validate_explanation(explanation_dict)
            
            print(f"Quality Grade: {quality_report.quality_grade}")
            print(f"Overall Score: {quality_report.overall_quality_score:.2f}")
            print(f"Strengths: {', '.join(quality_report.strengths[:2])}")
            print(f"Weaknesses: {', '.join(quality_report.weaknesses[:2])}")
            
            if quality_report.improvement_recommendations:
                print(f"Improvements: {', '.join(quality_report.improvement_recommendations[:2])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_complete_explanation_workflow():
    """Demonstrate complete explanation workflow"""
    print("\n🔄 Complete Explanation Workflow Demo")
    print("=" * 40)
    
    try:
        from explanation_generator import ExplanationGenerator, ExplanationStyle, ExplanationLevel
        from reasoning_trail import ReasoningTrailFormatter, TrailFormat
        from explanation_validator import ExplanationValidator
        
        # Initialize components
        generator = ExplanationGenerator()
        formatter = ReasoningTrailFormatter()
        validator = ExplanationValidator()
        
        # Complex transaction scenario
        complex_scenario = {
            'reasoning_id': 'workflow_demo_001',
            'transaction_id': 'workflow_tx_001',
            'overall_confidence': 0.65,
            'total_processing_time_ms': 4200.0,
            'steps': [
                {
                    'step_id': 'wf_step_1',
                    'step_type': 'observation',
                    'description': 'Multi-currency transaction observation',
                    'reasoning': 'Large transaction in foreign currency from new location',
                    'output': {'key_findings': ['Large amount', 'Foreign currency', 'New location']},
                    'evidence': ['Amount: 5000000 NGN', 'Currency: Nigerian Naira', 'Location: Lagos'],
                    'confidence': 0.7
                },
                {
                    'step_id': 'wf_step_2',
                    'step_type': 'pattern_matching',
                    'description': 'Historical pattern comparison',
                    'reasoning': 'Compared against user historical spending patterns',
                    'output': {'pattern_deviation': 'Significant deviation from normal'},
                    'evidence': ['10x normal amount', 'First international transaction'],
                    'confidence': 0.8
                },
                {
                    'step_id': 'wf_step_3',
                    'step_type': 'risk_assessment',
                    'description': 'Comprehensive risk evaluation',
                    'reasoning': 'Assessed currency risk, location risk, and amount risk',
                    'output': {'risk_level': 'MEDIUM', 'mixed_signals': True},
                    'evidence': ['Currency risk: Medium', 'Location risk: High', 'Amount risk: High'],
                    'confidence': 0.6
                },
                {
                    'step_id': 'wf_step_4',
                    'step_type': 'conclusion',
                    'description': 'Final decision with uncertainty',
                    'reasoning': 'Mixed signals require human review for final determination',
                    'output': {'is_fraud': False, 'recommended_action': 'REVIEW', 'uncertainty_high': True},
                    'evidence': ['Mixed risk signals', 'Requires human judgment'],
                    'confidence': 0.65
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.65,
                'risk_level': 'MEDIUM',
                'recommended_action': 'REVIEW',
                'primary_concerns': ['Large foreign currency amount', 'New location', 'Pattern deviation']
            }
        }
        
        print("🎯 Scenario: Large Nigerian Naira transaction from new location")
        print(f"Amount: ₦5,000,000 (~$6,450 USD)")
        print(f"Decision: REVIEW (Mixed signals)")
        print(f"Confidence: 65%")
        
        # Generate explanations for different audiences
        print(f"\n📊 Generating explanations for different audiences...")
        
        # Business explanation
        business_explanation = generator.generate_explanation(
            complex_scenario,
            style=ExplanationStyle.BUSINESS,
            level=ExplanationLevel.DETAILED
        )
        
        print(f"\n--- Business Explanation ---")
        print(f"Executive Summary: {business_explanation.executive_summary}")
        print(f"Sections: {len(business_explanation.sections)}")
        print(f"Recommendations: {', '.join(business_explanation.recommendations[:2])}")
        
        # Customer explanation
        customer_explanation = generator.generate_explanation(
            complex_scenario,
            style=ExplanationStyle.CUSTOMER,
            level=ExplanationLevel.BRIEF
        )
        
        print(f"\n--- Customer Explanation ---")
        print(f"Customer Message: {customer_explanation.executive_summary}")
        
        # Technical explanation
        technical_explanation = generator.generate_explanation(
            complex_scenario,
            style=ExplanationStyle.TECHNICAL,
            level=ExplanationLevel.COMPREHENSIVE
        )
        
        print(f"\n--- Technical Explanation ---")
        print(f"Technical Summary: {technical_explanation.executive_summary}")
        print(f"Evidence Items: {len(technical_explanation.evidence_summary)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_trail_formatting():
    """Demonstrate reasoning trail formatting"""
    print("\n🛤️ Reasoning Trail Formatting Demo")
    print("=" * 38)
    
    try:
        from reasoning_trail import ReasoningTrailFormatter, TrailFormat
        
        formatter = ReasoningTrailFormatter()
        
        # Sample reasoning for trail
        trail_reasoning = {
            'reasoning_id': 'trail_demo_001',
            'transaction_id': 'trail_tx_001',
            'overall_confidence': 0.82,
            'total_processing_time_ms': 1800.0,
            'steps': [
                {
                    'step_id': 'trail_obs',
                    'step_type': 'observation',
                    'description': 'Transaction observation',
                    'reasoning': 'Initial assessment shows normal transaction characteristics',
                    'output': {'assessment': 'Normal patterns detected'},
                    'evidence': ['Amount: $200', 'Merchant: WALMART', 'Location: Chicago'],
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 600.0,
                    'dependencies': []
                },
                {
                    'step_id': 'trail_decision',
                    'step_type': 'conclusion',
                    'description': 'Final approval decision',
                    'reasoning': 'All indicators point to legitimate transaction',
                    'output': {'is_fraud': False, 'recommended_action': 'APPROVE'},
                    'evidence': ['Consistent with user patterns', 'Trusted merchant'],
                    'confidence': 0.85,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 1200.0,
                    'dependencies': ['trail_obs']
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.82,
                'recommended_action': 'APPROVE'
            }
        }
        
        # Create trails in different formats
        formats = [
            (TrailFormat.NARRATIVE, "Story Format"),
            (TrailFormat.TIMELINE, "Timeline Format"),
            (TrailFormat.AUDIT, "Audit Format")
        ]
        
        for trail_format, format_name in formats:
            print(f"\n--- {format_name} ---")
            
            trail = formatter.create_reasoning_trail(trail_reasoning, trail_format)
            
            print(f"Trail ID: {trail.trail_id}")
            print(f"Steps: {len(trail.steps)}")
            print(f"Decision: {trail.decision_summary}")
            
            # Show formatted preview
            if trail_format == TrailFormat.NARRATIVE:
                formatted = formatter.format_trail_as_narrative(trail)
                print(f"Preview: {formatted[:150]}...")
            elif trail_format == TrailFormat.TIMELINE:
                formatted = formatter.format_trail_as_timeline(trail)
                print(f"Preview: {formatted[:150]}...")
            else:  # AUDIT
                formatted = formatter.format_trail_for_audit(trail)
                print(f"Preview: {formatted[:150]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def demo_quality_validation():
    """Demonstrate explanation quality validation"""
    print("\n🔍 Quality Validation Demo")
    print("=" * 27)
    
    try:
        from explanation_generator import ExplanationGenerator, ExplanationStyle
        from explanation_validator import ExplanationValidator
        
        generator = ExplanationGenerator()
        validator = ExplanationValidator()
        
        # Create explanation to validate
        sample_reasoning = {
            'reasoning_id': 'validation_demo_001',
            'transaction_id': 'validation_tx_001',
            'overall_confidence': 0.75,
            'steps': [
                {
                    'step_type': 'analysis',
                    'reasoning': 'Comprehensive analysis of transaction patterns and risk factors',
                    'output': {'key_findings': ['Normal spending pattern', 'Trusted merchant']},
                    'evidence': ['Amount consistent with history', 'Merchant in whitelist'],
                    'confidence': 0.8
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.75,
                'risk_level': 'LOW',
                'recommended_action': 'APPROVE'
            }
        }
        
        # Generate explanation
        explanation = generator.generate_explanation(sample_reasoning)
        
        # Validate explanation
        explanation_dict = json.loads(generator.format_explanation_as_json(explanation))
        quality_report = validator.validate_explanation(explanation_dict)
        
        print(f"Explanation Quality Assessment:")
        print(f"Overall Grade: {quality_report.quality_grade}")
        print(f"Quality Score: {quality_report.overall_quality_score:.2f}")
        
        print(f"\nStrengths:")
        for strength in quality_report.strengths[:3]:
            print(f"  ✅ {strength}")
        
        if quality_report.weaknesses:
            print(f"\nWeaknesses:")
            for weakness in quality_report.weaknesses[:3]:
                print(f"  ⚠️ {weakness}")
        
        if quality_report.improvement_recommendations:
            print(f"\nImprovement Recommendations:")
            for rec in quality_report.improvement_recommendations[:3]:
                print(f"  💡 {rec}")
        
        # Show validation details
        print(f"\nValidation Details:")
        for result in quality_report.validation_results:
            score_emoji = "🟢" if result.score > 0.8 else "🟡" if result.score > 0.6 else "🔴"
            print(f"  {score_emoji} {result.criteria.value}: {result.score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main demo function"""
    print("🏦 Fraud Detection Explanation System Demo")
    print("=" * 45)
    
    demos = [
        ("Explanation Generation", demo_explanation_generation),
        ("Reasoning Trail Formatting", demo_trail_formatting),
        ("Quality Validation", demo_explanation_validation),
        ("Complete Workflow", demo_complete_explanation_workflow)
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
    print("\n" + "=" * 45)
    print("📋 EXPLANATION SYSTEM DEMO RESULTS")
    print("=" * 45)
    
    for demo_name, result in results.items():
        print(f"{result} {demo_name}")
    
    successful_demos = sum(1 for r in results.values() if "SUCCESS" in r)
    total_demos = len(results)
    
    print(f"\n🎯 Overall: {successful_demos}/{total_demos} demos successful")
    
    if successful_demos == total_demos:
        print("🎉 All explanation system demos completed successfully!")
        print("\n📚 System Capabilities Demonstrated:")
        print("  ✅ Multi-audience explanation generation")
        print("  ✅ Multiple reasoning trail formats")
        print("  ✅ Comprehensive quality validation")
        print("  ✅ Human-readable reasoning explanations")
        print("  ✅ Audit trail generation for compliance")
        print("  ✅ Interactive explanation quality scoring")
    else:
        print("⚠️ Some demos had issues. Check the errors above.")

if __name__ == "__main__":
    main()