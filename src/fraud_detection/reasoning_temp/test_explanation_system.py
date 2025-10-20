#!/usr/bin/env python3
"""
Integration Tests for Explanation Generation System
Tests the complete explanation generation and validation pipeline
"""

import unittest
import json
import sys
import os
from datetime import datetime

# Add reasoning_engine to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from explanation_generator import (
    ExplanationGenerator, 
    ExplanationReport, 
    ExplanationStyle, 
    ExplanationLevel
)
from reasoning_trail import (
    ReasoningTrailFormatter,
    ReasoningTrail,
    TrailFormat
)
from explanation_validator import (
    ExplanationValidator,
    ExplanationQualityReport,
    ValidationCriteria
)

class TestExplanationGenerator(unittest.TestCase):
    """Test explanation generation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.generator = ExplanationGenerator()
        
        # Sample reasoning result
        self.sample_reasoning_result = {
            'reasoning_id': 'test_reasoning_001',
            'transaction_id': 'test_tx_001',
            'overall_confidence': 0.85,
            'total_processing_time_ms': 1500.0,
            'steps': [
                {
                    'step_id': 'step_1',
                    'step_type': 'observation',
                    'description': 'Initial transaction observation',
                    'reasoning': 'Analyzed transaction amount and merchant patterns',
                    'output': {
                        'key_findings': ['High amount', 'Unknown merchant'],
                        'confidence': 0.8
                    },
                    'evidence': ['Amount: $15000', 'Merchant: UNKNOWN_MERCHANT'],
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 500.0
                },
                {
                    'step_id': 'step_2',
                    'step_type': 'risk_assessment',
                    'description': 'Risk factor evaluation',
                    'reasoning': 'Evaluated location and transaction patterns',
                    'output': {
                        'risk_level': 'HIGH',
                        'primary_concerns': ['Foreign location', 'High amount'],
                        'confidence': 0.9
                    },
                    'evidence': ['Location: FOREIGN_COUNTRY', 'Amount exceeds threshold'],
                    'confidence': 0.9,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 700.0
                }
            ],
            'final_decision': {
                'is_fraud': True,
                'confidence': 0.85,
                'risk_level': 'HIGH',
                'recommended_action': 'BLOCK',
                'primary_concerns': ['High amount', 'Unknown merchant', 'Foreign location']
            }
        }
    
    def test_generator_initialization(self):
        """Test explanation generator initialization"""
        self.assertIsNotNone(self.generator)
        self.assertIsInstance(self.generator.explanation_templates, dict)
        self.assertIsInstance(self.generator.style_configurations, dict)
    
    def test_business_explanation_generation(self):
        """Test business style explanation generation"""
        explanation = self.generator.generate_explanation(
            self.sample_reasoning_result,
            style=ExplanationStyle.BUSINESS,
            level=ExplanationLevel.DETAILED
        )
        
        self.assertIsInstance(explanation, ExplanationReport)
        self.assertEqual(explanation.transaction_id, 'test_tx_001')
        self.assertEqual(explanation.decision, 'BLOCK')
        self.assertEqual(explanation.explanation_style, ExplanationStyle.BUSINESS)
        self.assertGreater(len(explanation.sections), 0)
        self.assertGreater(len(explanation.key_factors), 0)
        self.assertIn('BLOCK', explanation.executive_summary)
    
    def test_customer_explanation_generation(self):
        """Test customer style explanation generation"""
        explanation = self.generator.generate_explanation(
            self.sample_reasoning_result,
            style=ExplanationStyle.CUSTOMER,
            level=ExplanationLevel.BRIEF
        )
        
        self.assertEqual(explanation.explanation_style, ExplanationStyle.CUSTOMER)
        self.assertEqual(explanation.explanation_level, ExplanationLevel.BRIEF)
        
        # Customer explanations should be simpler
        summary = explanation.executive_summary.lower()
        self.assertNotIn('algorithm', summary)
        self.assertNotIn('heuristic', summary)
    
    def test_technical_explanation_generation(self):
        """Test technical style explanation generation"""
        explanation = self.generator.generate_explanation(
            self.sample_reasoning_result,
            style=ExplanationStyle.TECHNICAL,
            level=ExplanationLevel.COMPREHENSIVE
        )
        
        self.assertEqual(explanation.explanation_style, ExplanationStyle.TECHNICAL)
        self.assertEqual(explanation.explanation_level, ExplanationLevel.COMPREHENSIVE)
        
        # Technical explanations should include more detail
        self.assertGreater(len(explanation.sections), 3)
    
    def test_regulatory_explanation_generation(self):
        """Test regulatory style explanation generation"""
        explanation = self.generator.generate_explanation(
            self.sample_reasoning_result,
            style=ExplanationStyle.REGULATORY,
            level=ExplanationLevel.COMPREHENSIVE
        )
        
        self.assertEqual(explanation.explanation_style, ExplanationStyle.REGULATORY)
        
        # Regulatory explanations should be comprehensive
        self.assertGreater(len(explanation.evidence_summary), 0)
        self.assertGreater(len(explanation.recommendations), 0)
    
    def test_explanation_formatting(self):
        """Test different explanation formats"""
        explanation = self.generator.generate_explanation(self.sample_reasoning_result)
        
        # Test text format
        text_format = self.generator.format_explanation_as_text(explanation)
        self.assertIn('FRAUD DETECTION EXPLANATION', text_format)
        self.assertIn(explanation.transaction_id, text_format)
        
        # Test HTML format
        html_format = self.generator.format_explanation_as_html(explanation)
        self.assertIn('<html>', html_format)
        self.assertIn('explanation-report', html_format)
        
        # Test JSON format
        json_format = self.generator.format_explanation_as_json(explanation)
        parsed_json = json.loads(json_format)
        self.assertEqual(parsed_json['transaction_id'], explanation.transaction_id)
        
        # Test audit trail format
        audit_format = self.generator.generate_audit_trail(explanation)
        self.assertIn('FRAUD DETECTION AUDIT TRAIL', audit_format)
        self.assertIn('DECISION RATIONALE', audit_format)
    
    def test_explanation_quality_scoring(self):
        """Test explanation quality scoring"""
        explanation = self.generator.generate_explanation(self.sample_reasoning_result)
        
        quality_scores = self.generator.get_explanation_quality_score(explanation)
        
        self.assertIn('completeness', quality_scores)
        self.assertIn('detail', quality_scores)
        self.assertIn('evidence', quality_scores)
        self.assertIn('overall', quality_scores)
        
        for score in quality_scores.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

class TestReasoningTrailFormatter(unittest.TestCase):
    """Test reasoning trail formatting functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.formatter = ReasoningTrailFormatter()
        
        # Use same sample data as explanation generator
        self.sample_reasoning_result = {
            'reasoning_id': 'test_reasoning_002',
            'transaction_id': 'test_tx_002',
            'overall_confidence': 0.75,
            'total_processing_time_ms': 2000.0,
            'steps': [
                {
                    'step_id': 'step_1',
                    'step_type': 'observation',
                    'description': 'Transaction observation',
                    'reasoning': 'Observed normal transaction patterns',
                    'output': {'confidence': 0.7},
                    'evidence': ['Normal amount', 'Trusted merchant'],
                    'confidence': 0.7,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 800.0,
                    'dependencies': []
                },
                {
                    'step_id': 'step_2',
                    'step_type': 'conclusion',
                    'description': 'Final decision',
                    'reasoning': 'Based on analysis, transaction appears legitimate',
                    'output': {'is_fraud': False, 'recommended_action': 'APPROVE'},
                    'evidence': ['Consistent patterns', 'No risk factors'],
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 1200.0,
                    'dependencies': ['step_1']
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.75,
                'recommended_action': 'APPROVE'
            }
        }
    
    def test_formatter_initialization(self):
        """Test trail formatter initialization"""
        self.assertIsNotNone(self.formatter)
        self.assertIsInstance(self.formatter.trail_templates, dict)
    
    def test_narrative_trail_creation(self):
        """Test narrative trail creation"""
        trail = self.formatter.create_reasoning_trail(
            self.sample_reasoning_result,
            TrailFormat.NARRATIVE
        )
        
        self.assertIsInstance(trail, ReasoningTrail)
        self.assertEqual(trail.transaction_id, 'test_tx_002')
        self.assertEqual(trail.trail_format, TrailFormat.NARRATIVE)
        self.assertEqual(len(trail.steps), 2)
        
        # Test narrative formatting
        narrative = self.formatter.format_trail_as_narrative(trail)
        self.assertIn('Step 1:', narrative)
        self.assertIn('Step 2:', narrative)
        self.assertIn('FINAL DECISION', narrative)
    
    def test_structured_trail_creation(self):
        """Test structured trail creation"""
        trail = self.formatter.create_reasoning_trail(
            self.sample_reasoning_result,
            TrailFormat.STRUCTURED
        )
        
        structured = self.formatter.format_trail_as_structured(trail)
        self.assertIn('FRAUD DETECTION REASONING TRAIL', structured)
        self.assertIn('INPUT:', structured)
        self.assertIn('REASONING PROCESS:', structured)
        self.assertIn('OUTPUT:', structured)
    
    def test_timeline_trail_creation(self):
        """Test timeline trail creation"""
        trail = self.formatter.create_reasoning_trail(
            self.sample_reasoning_result,
            TrailFormat.TIMELINE
        )
        
        timeline = self.formatter.format_trail_as_timeline(trail)
        self.assertIn('FRAUD DETECTION TIMELINE', timeline)
        self.assertIn('Step 1', timeline)
        self.assertIn('ANALYSIS COMPLETE', timeline)
    
    def test_audit_trail_creation(self):
        """Test audit trail creation"""
        trail = self.formatter.create_reasoning_trail(
            self.sample_reasoning_result,
            TrailFormat.AUDIT
        )
        
        audit = self.formatter.format_trail_for_audit(trail)
        self.assertIn('REGULATORY AUDIT TRAIL', audit)
        self.assertIn('AUDIT TRAIL ENTRY', audit)
        self.assertIn('COMPLIANCE', audit)
    
    def test_trail_json_export(self):
        """Test trail JSON export"""
        trail = self.formatter.create_reasoning_trail(self.sample_reasoning_result)
        
        json_export = self.formatter.export_trail_as_json(trail)
        parsed = json.loads(json_export)
        
        self.assertEqual(parsed['transaction_id'], trail.transaction_id)
        self.assertEqual(len(parsed['steps']), len(trail.steps))

class TestExplanationValidator(unittest.TestCase):
    """Test explanation validation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ExplanationValidator()
        
        # Sample explanation report for validation
        self.sample_explanation = {
            'reasoning_id': 'test_validation_001',
            'transaction_id': 'test_tx_003',
            'decision': 'BLOCK',
            'confidence': 0.9,
            'risk_level': 'HIGH',
            'executive_summary': 'Transaction flagged as fraudulent due to high amount and unknown merchant with 90% confidence.',
            'sections': [
                {
                    'title': 'Analysis Overview',
                    'content': 'Comprehensive analysis identified multiple risk factors including unusual transaction amount and unrecognized merchant.',
                    'importance': 1.0,
                    'evidence': ['High amount: $15000', 'Unknown merchant'],
                    'confidence': 0.9,
                    'section_type': 'analysis'
                },
                {
                    'title': 'Supporting Evidence',
                    'content': 'Evidence includes transaction amount exceeding normal patterns and merchant not in trusted list.',
                    'importance': 0.8,
                    'evidence': ['Amount threshold exceeded', 'Merchant verification failed'],
                    'confidence': 0.85,
                    'section_type': 'evidence'
                },
                {
                    'title': 'Recommendations',
                    'content': 'Block transaction immediately and notify customer of security concern.',
                    'importance': 1.0,
                    'evidence': ['Block action required', 'Customer notification needed'],
                    'confidence': 0.9,
                    'section_type': 'recommendation'
                }
            ],
            'key_factors': ['High amount', 'Unknown merchant', 'Risk threshold exceeded'],
            'evidence_summary': ['Amount: $15000', 'Merchant: UNKNOWN', 'Location: FOREIGN'],
            'recommendations': ['Block transaction immediately', 'Notify customer', 'Flag account for monitoring'],
            'explanation_style': 'business',
            'explanation_level': 'detailed'
        }
    
    def test_validator_initialization(self):
        """Test validator initialization"""
        self.assertIsNotNone(self.validator)
        self.assertIsInstance(self.validator.validation_rules, dict)
        self.assertIsInstance(self.validator.quality_thresholds, dict)
    
    def test_explanation_validation(self):
        """Test complete explanation validation"""
        quality_report = self.validator.validate_explanation(self.sample_explanation)
        
        self.assertIsInstance(quality_report, ExplanationQualityReport)
        self.assertEqual(quality_report.explanation_id, 'test_validation_001')
        self.assertGreaterEqual(quality_report.overall_quality_score, 0.0)
        self.assertLessEqual(quality_report.overall_quality_score, 1.0)
        self.assertIn(quality_report.quality_grade, ['A', 'B', 'C', 'D', 'F'])
        
        # Should have validation results for all criteria
        self.assertEqual(len(quality_report.validation_results), len(ValidationCriteria))
    
    def test_completeness_validation(self):
        """Test completeness validation"""
        result = self.validator._validate_completeness(self.sample_explanation)
        
        self.assertEqual(result.criteria, ValidationCriteria.COMPLETENESS)
        self.assertGreaterEqual(result.score, 0.7)  # Should score well on completeness
    
    def test_clarity_validation(self):
        """Test clarity validation"""
        result = self.validator._validate_clarity(self.sample_explanation)
        
        self.assertEqual(result.criteria, ValidationCriteria.CLARITY)
        self.assertGreaterEqual(result.score, 0.0)
    
    def test_accuracy_validation(self):
        """Test accuracy validation"""
        result = self.validator._validate_accuracy(self.sample_explanation)
        
        self.assertEqual(result.criteria, ValidationCriteria.ACCURACY)
        self.assertGreaterEqual(result.score, 0.0)
    
    def test_poor_quality_explanation(self):
        """Test validation of poor quality explanation"""
        poor_explanation = {
            'reasoning_id': 'poor_test',
            'decision': 'BLOCK',
            'confidence': 0.3,
            'executive_summary': 'Bad.',  # Too short
            'sections': [],  # No sections
            'recommendations': [],  # No recommendations
            'evidence_summary': []  # No evidence
        }
        
        quality_report = self.validator.validate_explanation(poor_explanation)
        
        self.assertLess(quality_report.overall_quality_score, 0.5)
        self.assertIn(quality_report.quality_grade, ['D', 'F'])
        self.assertGreater(len(quality_report.weaknesses), 0)
        self.assertGreater(len(quality_report.improvement_recommendations), 0)

class TestIntegratedExplanationSystem(unittest.TestCase):
    """Integration tests for the complete explanation system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.generator = ExplanationGenerator()
        self.formatter = ReasoningTrailFormatter()
        self.validator = ExplanationValidator()
        
        # Complex reasoning result for integration testing
        self.complex_reasoning_result = {
            'reasoning_id': 'integration_test_001',
            'transaction_id': 'integration_tx_001',
            'overall_confidence': 0.82,
            'total_processing_time_ms': 3500.0,
            'steps': [
                {
                    'step_id': 'step_1',
                    'step_type': 'observation',
                    'description': 'Initial transaction observation',
                    'reasoning': 'Analyzed transaction characteristics and context',
                    'output': {
                        'key_findings': ['Large amount', 'International transaction'],
                        'confidence': 0.8
                    },
                    'evidence': ['Amount: $8500', 'Location: International'],
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 1000.0,
                    'dependencies': []
                },
                {
                    'step_id': 'step_2',
                    'step_type': 'pattern_matching',
                    'description': 'Pattern analysis',
                    'reasoning': 'Compared against historical user patterns',
                    'output': {
                        'pattern_match': 'Unusual for user',
                        'confidence': 0.75
                    },
                    'evidence': ['Deviates from normal spending', 'New merchant type'],
                    'confidence': 0.75,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 1200.0,
                    'dependencies': ['step_1']
                },
                {
                    'step_id': 'step_3',
                    'step_type': 'risk_assessment',
                    'description': 'Risk evaluation',
                    'reasoning': 'Assessed multiple risk factors',
                    'output': {
                        'risk_level': 'MEDIUM',
                        'primary_concerns': ['Amount deviation', 'Location risk'],
                        'confidence': 0.85
                    },
                    'evidence': ['Amount 3x normal', 'High-risk country'],
                    'confidence': 0.85,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 800.0,
                    'dependencies': ['step_1', 'step_2']
                },
                {
                    'step_id': 'step_4',
                    'step_type': 'conclusion',
                    'description': 'Final decision',
                    'reasoning': 'Synthesized all analysis results',
                    'output': {
                        'is_fraud': False,
                        'recommended_action': 'REVIEW',
                        'confidence': 0.82
                    },
                    'evidence': ['Mixed signals', 'Requires human judgment'],
                    'confidence': 0.82,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 500.0,
                    'dependencies': ['step_1', 'step_2', 'step_3']
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.82,
                'risk_level': 'MEDIUM',
                'recommended_action': 'REVIEW',
                'primary_concerns': ['Amount deviation', 'Location risk', 'Pattern mismatch']
            }
        }
    
    def test_end_to_end_explanation_pipeline(self):
        """Test complete explanation generation and validation pipeline"""
        
        # Step 1: Generate explanation
        explanation = self.generator.generate_explanation(
            self.complex_reasoning_result,
            style=ExplanationStyle.BUSINESS,
            level=ExplanationLevel.DETAILED
        )
        
        self.assertIsInstance(explanation, ExplanationReport)
        self.assertEqual(explanation.decision, 'REVIEW')
        
        # Step 2: Create reasoning trail
        trail = self.formatter.create_reasoning_trail(
            self.complex_reasoning_result,
            TrailFormat.NARRATIVE
        )
        
        self.assertIsInstance(trail, ReasoningTrail)
        self.assertEqual(len(trail.steps), 4)
        
        # Step 3: Validate explanation quality
        explanation_dict = json.loads(self.generator.format_explanation_as_json(explanation))
        quality_report = self.validator.validate_explanation(explanation_dict)
        
        self.assertIsInstance(quality_report, ExplanationQualityReport)
        self.assertGreater(quality_report.overall_quality_score, 0.5)
        
        # Step 4: Test different formats
        text_format = self.generator.format_explanation_as_text(explanation)
        html_format = self.generator.format_explanation_as_html(explanation)
        audit_format = self.generator.generate_audit_trail(explanation)
        
        self.assertIn('REVIEW', text_format)
        self.assertIn('<html>', html_format)
        self.assertIn('AUDIT TRAIL', audit_format)
        
        # Step 5: Test trail formats
        narrative = self.formatter.format_trail_as_narrative(trail)
        structured = self.formatter.format_trail_as_structured(trail)
        timeline = self.formatter.format_trail_as_timeline(trail)
        
        self.assertIn('Step 1:', narrative)
        self.assertIn('INPUT:', structured)
        self.assertIn('TIMELINE', timeline)
    
    def test_multi_style_explanation_generation(self):
        """Test generating explanations in multiple styles"""
        
        styles_to_test = [
            ExplanationStyle.BUSINESS,
            ExplanationStyle.TECHNICAL,
            ExplanationStyle.CUSTOMER,
            ExplanationStyle.REGULATORY
        ]
        
        explanations = {}
        
        for style in styles_to_test:
            explanation = self.generator.generate_explanation(
                self.complex_reasoning_result,
                style=style,
                level=ExplanationLevel.DETAILED
            )
            explanations[style] = explanation
            
            # Validate each explanation
            explanation_dict = json.loads(self.generator.format_explanation_as_json(explanation))
            quality_report = self.validator.validate_explanation(explanation_dict)
            
            # All explanations should meet minimum quality standards
            self.assertGreaterEqual(quality_report.overall_quality_score, 0.4)
        
        # Customer explanation should be simpler than technical
        customer_text = self.generator.format_explanation_as_text(explanations[ExplanationStyle.CUSTOMER])
        technical_text = self.generator.format_explanation_as_text(explanations[ExplanationStyle.TECHNICAL])
        
        # Technical should be longer and more detailed
        self.assertGreater(len(technical_text), len(customer_text))
    
    def test_explanation_system_statistics(self):
        """Test statistics collection across the explanation system"""
        
        # Generate multiple explanations
        for i in range(3):
            explanation = self.generator.generate_explanation(self.complex_reasoning_result)
            trail = self.formatter.create_reasoning_trail(self.complex_reasoning_result)
            
            explanation_dict = json.loads(self.generator.format_explanation_as_json(explanation))
            self.validator.validate_explanation(explanation_dict)
        
        # Check generator statistics
        gen_stats = self.generator.get_explanation_statistics()
        self.assertEqual(gen_stats['total_explanations'], 3)
        
        # Check formatter statistics
        formatter_stats = self.formatter.get_trail_statistics()
        self.assertEqual(formatter_stats['total_trails'], 3)
        
        # Check validator statistics
        validator_stats = self.validator.get_validation_statistics()
        self.assertEqual(validator_stats['total_validations'], 3)

def run_explanation_tests():
    """Run all explanation system tests"""
    print("🧪 Running Explanation Generation System Tests")
    print("=" * 55)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestExplanationGenerator,
        TestReasoningTrailFormatter,
        TestExplanationValidator,
        TestIntegratedExplanationSystem
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 55)
    print("📊 EXPLANATION SYSTEM TEST SUMMARY")
    print("=" * 55)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if not result.failures and not result.errors:
        print("🎉 All explanation system tests passed!")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_explanation_tests()
    exit(0 if success else 1)