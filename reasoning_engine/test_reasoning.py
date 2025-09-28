#!/usr/bin/env python3
"""
Unit Tests for Chain-of-Thought Reasoning Module
Comprehensive testing of reasoning logic and validation
"""

import unittest
import json
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the reasoning_engine directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chain_of_thought import (
    ChainOfThoughtReasoner, 
    ReasoningStep, 
    ReasoningResult, 
    ReasoningStepType,
    validate_reasoning_step
)
from confidence_scoring import (
    ConfidenceScorer, 
    ConfidenceFactor, 
    ConfidenceAssessment,
    ConfidenceFactorType
)
from step_tracker import (
    ReasoningStepTracker,
    StepDependency,
    StepMetrics,
    StepValidation
)

class TestChainOfThoughtReasoner(unittest.TestCase):
    """Test the main chain-of-thought reasoning functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.reasoner = ChainOfThoughtReasoner()
        
        # Mock Bedrock client to avoid AWS calls in tests
        self.reasoner.bedrock_runtime = Mock()
        
        # Sample transaction data
        self.sample_transaction = {
            'id': 'test_tx_001',
            'user_id': 'test_user_001',
            'amount': 1500.0,
            'currency': 'USD',
            'merchant': 'AMAZON',
            'category': 'SHOPPING',
            'location': 'NEW_YORK_NY',
            'timestamp': datetime.now().isoformat(),
            'card_type': 'CREDIT'
        }
        
        # Sample context data
        self.sample_context = {
            'user_history': [
                {'amount': 100, 'merchant': 'STARBUCKS'},
                {'amount': 50, 'merchant': 'SHELL'}
            ],
            'similar_transactions': [],
            'risk_context': {'location_risk': 'low'}
        }
    
    def test_reasoner_initialization(self):
        """Test reasoner initialization"""
        self.assertIsNotNone(self.reasoner)
        self.assertEqual(self.reasoner.model_id, "anthropic.claude-3-sonnet-20240229-v1:0")
        self.assertIsInstance(self.reasoner.reasoning_templates, dict)
        self.assertIn('fraud_analysis', self.reasoner.reasoning_templates)
    
    @patch('boto3.client')
    def test_bedrock_client_initialization(self, mock_boto_client):
        """Test Bedrock client initialization"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        reasoner = ChainOfThoughtReasoner()
        reasoner._initialize_bedrock_client()
        
        mock_boto_client.assert_called_with('bedrock-runtime', region_name='us-east-1')
        self.assertEqual(reasoner.bedrock_runtime, mock_client)
    
    def test_reasoning_step_creation(self):
        """Test creation of reasoning steps"""
        step = ReasoningStep(
            step_id="test_step_001",
            step_type=ReasoningStepType.OBSERVATION,
            description="Test observation step",
            input_data=self.sample_transaction,
            reasoning="This is a test reasoning",
            output={"test": "output"},
            confidence=0.8,
            evidence=["evidence1", "evidence2"],
            timestamp=datetime.now().isoformat(),
            processing_time_ms=100.0
        )
        
        self.assertEqual(step.step_id, "test_step_001")
        self.assertEqual(step.step_type, ReasoningStepType.OBSERVATION)
        self.assertEqual(step.confidence, 0.8)
        self.assertEqual(len(step.evidence), 2)
    
    def test_reasoning_step_validation(self):
        """Test reasoning step validation"""
        # Valid step
        valid_step = ReasoningStep(
            step_id="valid_step",
            step_type=ReasoningStepType.ANALYSIS,
            description="Valid analysis step",
            input_data={"test": "data"},
            reasoning="This is a comprehensive analysis of the transaction data",
            output={"confidence": 0.7, "result": "valid"},
            confidence=0.7,
            evidence=["evidence1", "evidence2", "evidence3"],
            timestamp=datetime.now().isoformat(),
            processing_time_ms=150.0
        )
        
        validation_result = validate_reasoning_step(valid_step)
        self.assertTrue(validation_result["is_valid"])
        self.assertGreater(validation_result["quality_score"], 0.5)
        
        # Invalid step (short reasoning)
        invalid_step = ReasoningStep(
            step_id="invalid_step",
            step_type=ReasoningStepType.ANALYSIS,
            description="Invalid step",
            input_data={"test": "data"},
            reasoning="Short",  # Too short
            output={"result": "invalid"},
            confidence=1.5,  # Invalid confidence
            evidence=[],  # No evidence
            timestamp=datetime.now().isoformat(),
            processing_time_ms=50.0
        )
        
        validation_result = validate_reasoning_step(invalid_step)
        self.assertFalse(validation_result["is_valid"])
        self.assertGreater(len(validation_result["issues"]), 0)
    
    def test_parse_reasoning_response(self):
        """Test parsing of model responses"""
        # Test JSON response
        json_response = json.dumps({
            "reasoning": "Test reasoning",
            "confidence": 0.8,
            "evidence": ["evidence1", "evidence2"]
        })
        
        parsed = self.reasoner._parse_reasoning_response(json_response, ReasoningStepType.ANALYSIS)
        self.assertEqual(parsed["reasoning"], "Test reasoning")
        self.assertEqual(parsed["confidence"], 0.8)
        self.assertEqual(len(parsed["evidence"]), 2)
        
        # Test non-JSON response
        text_response = "This is a plain text response"
        parsed = self.reasoner._parse_reasoning_response(text_response, ReasoningStepType.OBSERVATION)
        self.assertEqual(parsed["reasoning"], text_response)
        self.assertIn("parsed_successfully", parsed)
        self.assertFalse(parsed["parsed_successfully"])
    
    def test_confidence_calculation(self):
        """Test overall confidence calculation"""
        steps = [
            ReasoningStep(
                step_id="step1",
                step_type=ReasoningStepType.OBSERVATION,
                description="Observation",
                input_data={},
                reasoning="Test",
                output={},
                confidence=0.8,
                evidence=[],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=100.0
            ),
            ReasoningStep(
                step_id="step2",
                step_type=ReasoningStepType.CONCLUSION,
                description="Final decision",
                input_data={},
                reasoning="Test",
                output={},
                confidence=0.9,
                evidence=[],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=100.0
            )
        ]
        
        overall_confidence = self.reasoner._calculate_overall_confidence(steps)
        self.assertGreater(overall_confidence, 0.8)  # Should be weighted toward conclusion
        self.assertLessEqual(overall_confidence, 1.0)
    
    def test_evidence_synthesis(self):
        """Test evidence synthesis from multiple steps"""
        steps = [
            ReasoningStep(
                step_id="step1",
                step_type=ReasoningStepType.OBSERVATION,
                description="Observation",
                input_data={},
                reasoning="Test",
                output={"key_findings": ["finding1", "finding2"]},
                confidence=0.7,
                evidence=["evidence1", "evidence2"],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=100.0
            ),
            ReasoningStep(
                step_id="step2",
                step_type=ReasoningStepType.ANALYSIS,
                description="Analysis",
                input_data={},
                reasoning="Test",
                output={"key_findings": ["finding2", "finding3"]},
                confidence=0.8,
                evidence=["evidence2", "evidence3"],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=100.0
            )
        ]
        
        synthesis_step = self.reasoner._synthesize_evidence(self.sample_transaction, steps)
        
        self.assertEqual(synthesis_step.step_type, ReasoningStepType.EVIDENCE_GATHERING)
        self.assertIn("evidence_count", synthesis_step.output)
        self.assertIn("unique_evidence", synthesis_step.output)
        self.assertEqual(len(synthesis_step.dependencies), 2)
    
    def test_final_decision_making(self):
        """Test final decision making logic"""
        steps = [
            ReasoningStep(
                step_id="step1",
                step_type=ReasoningStepType.ANALYSIS,
                description="Analysis",
                input_data={},
                reasoning="Test",
                output={"is_fraud": True, "risk_level": "HIGH", "primary_concerns": ["high_amount"]},
                confidence=0.9,
                evidence=[],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=100.0
            ),
            ReasoningStep(
                step_id="step2",
                step_type=ReasoningStepType.RISK_ASSESSMENT,
                description="Risk Assessment",
                input_data={},
                reasoning="Test",
                output={"is_fraud": False, "risk_level": "LOW"},
                confidence=0.6,
                evidence=[],
                timestamp=datetime.now().isoformat(),
                processing_time_ms=100.0
            )
        ]
        
        decision_step = self.reasoner._make_final_decision(self.sample_transaction, steps)
        
        self.assertEqual(decision_step.step_type, ReasoningStepType.CONCLUSION)
        self.assertIn("is_fraud", decision_step.output)
        self.assertIn("fraud_probability", decision_step.output)
        self.assertIn("recommended_action", decision_step.output)
        self.assertIn("confidence", decision_step.output)

class TestConfidenceScorer(unittest.TestCase):
    """Test confidence scoring functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scorer = ConfidenceScorer()
        
        self.sample_reasoning_data = {
            'transaction': {
                'amount': 1000,
                'currency': 'USD',
                'merchant': 'AMAZON',
                'location': 'NEW_YORK_NY',
                'user_id': 'test_user'
            },
            'reasoning': 'This transaction shows normal patterns consistent with user behavior',
            'evidence': ['Normal amount', 'Trusted merchant', 'Usual location'],
            'confidence': 0.8
        }
    
    def test_scorer_initialization(self):
        """Test confidence scorer initialization"""
        self.assertIsNotNone(self.scorer)
        self.assertIsInstance(self.scorer.default_weights, dict)
        self.assertEqual(len(self.scorer.default_weights), 8)  # All factor types
    
    def test_data_quality_assessment(self):
        """Test data quality factor assessment"""
        factor = self.scorer._assess_data_quality(self.sample_reasoning_data)
        
        self.assertEqual(factor.factor_type, ConfidenceFactorType.DATA_QUALITY)
        self.assertGreater(factor.value, 0.5)  # Should be good quality
        self.assertGreater(factor.weight, 0.0)
        self.assertIsInstance(factor.evidence, list)
    
    def test_evidence_strength_assessment(self):
        """Test evidence strength factor assessment"""
        factor = self.scorer._assess_evidence_strength(self.sample_reasoning_data)
        
        self.assertEqual(factor.factor_type, ConfidenceFactorType.EVIDENCE_STRENGTH)
        self.assertGreater(factor.value, 0.5)  # 3 pieces of evidence should be good
        
        # Test with no evidence
        no_evidence_data = self.sample_reasoning_data.copy()
        no_evidence_data['evidence'] = []
        
        factor_no_evidence = self.scorer._assess_evidence_strength(no_evidence_data)
        self.assertLess(factor_no_evidence.value, 0.2)
    
    def test_model_certainty_assessment(self):
        """Test model certainty factor assessment"""
        factor = self.scorer._assess_model_certainty(self.sample_reasoning_data)
        
        self.assertEqual(factor.factor_type, ConfidenceFactorType.MODEL_CERTAINTY)
        self.assertEqual(factor.value, 0.8)  # Should match provided confidence
        
        # Test with uncertain language
        uncertain_data = self.sample_reasoning_data.copy()
        uncertain_data['reasoning'] = 'This transaction might possibly be fraudulent, but unclear'
        
        factor_uncertain = self.scorer._assess_model_certainty(uncertain_data)
        self.assertLess(factor_uncertain.value, 0.8)
    
    def test_overall_confidence_assessment(self):
        """Test complete confidence assessment"""
        assessment = self.scorer.assess_confidence(self.sample_reasoning_data)
        
        self.assertIsInstance(assessment, ConfidenceAssessment)
        self.assertGreater(assessment.overall_confidence, 0.0)
        self.assertLessEqual(assessment.overall_confidence, 1.0)
        self.assertIn(assessment.confidence_level, ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'])
        self.assertIsInstance(assessment.factors, list)
        self.assertEqual(len(assessment.factors), 8)  # All factor types
    
    def test_historical_accuracy_update(self):
        """Test historical accuracy tracking"""
        decision_type = "test_fraud_detection"
        
        # Update with correct decisions
        for _ in range(8):
            self.scorer.update_historical_accuracy(decision_type, True)
        
        # Update with incorrect decisions
        for _ in range(2):
            self.scorer.update_historical_accuracy(decision_type, False)
        
        # Check accuracy
        self.assertIn(decision_type, self.scorer.historical_accuracy)
        accuracy_data = self.scorer.historical_accuracy[decision_type]
        self.assertEqual(accuracy_data['accuracy'], 0.8)  # 8/10 correct
        self.assertEqual(accuracy_data['total_count'], 10)

class TestReasoningStepTracker(unittest.TestCase):
    """Test reasoning step tracking functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = ReasoningStepTracker()
        
        self.sample_step_data = {
            'step_type': 'observation',
            'description': 'Initial observation step',
            'input_data': {'transaction_id': 'test_001'},
            'reasoning': 'Observing transaction patterns'
        }
    
    def test_tracker_initialization(self):
        """Test step tracker initialization"""
        self.assertIsNotNone(self.tracker)
        self.assertEqual(len(self.tracker.steps), 0)
        self.assertEqual(len(self.tracker.execution_order), 0)
    
    def test_step_registration(self):
        """Test step registration"""
        step_id = "test_step_001"
        success = self.tracker.register_step(step_id, self.sample_step_data)
        
        self.assertTrue(success)
        self.assertIn(step_id, self.tracker.steps)
        self.assertEqual(self.tracker.steps[step_id]['status'], 'registered')
    
    def test_step_execution_lifecycle(self):
        """Test complete step execution lifecycle"""
        step_id = "test_step_002"
        
        # Register step
        self.tracker.register_step(step_id, self.sample_step_data)
        
        # Start execution
        success = self.tracker.start_step_execution(step_id)
        self.assertTrue(success)
        self.assertEqual(self.tracker.get_step_status(step_id), 'executing')
        self.assertIn(step_id, self.tracker.execution_order)
        
        # Complete execution
        result = {'confidence': 0.8, 'decision': 'approve'}
        metrics = StepMetrics(
            execution_time_ms=150.0,
            memory_usage_mb=10.0,
            api_calls_made=1,
            tokens_processed=100,
            cache_hits=0,
            cache_misses=1
        )
        
        success = self.tracker.complete_step_execution(step_id, result, metrics)
        self.assertTrue(success)
        self.assertEqual(self.tracker.get_step_status(step_id), 'completed')
        
        # Check result retrieval
        retrieved_result = self.tracker.get_step_result(step_id)
        self.assertEqual(retrieved_result, result)
        
        # Check metrics
        retrieved_metrics = self.tracker.get_step_metrics(step_id)
        self.assertEqual(retrieved_metrics.execution_time_ms, 150.0)
    
    def test_step_dependencies(self):
        """Test step dependency management"""
        step1_id = "step_001"
        step2_id = "step_002"
        
        # Register first step
        self.tracker.register_step(step1_id, self.sample_step_data)
        
        # Register second step with dependency
        step2_data = self.sample_step_data.copy()
        step2_data['description'] = 'Dependent step'
        self.tracker.register_step(step2_id, step2_data, dependencies=[step1_id])
        
        # Check dependencies
        prerequisites = self.tracker.get_prerequisite_steps(step2_id)
        self.assertIn(step1_id, prerequisites)
        
        dependents = self.tracker.get_dependent_steps(step1_id)
        self.assertIn(step2_id, dependents)
        
        # Try to execute dependent step before prerequisite
        success = self.tracker.start_step_execution(step2_id)
        self.assertFalse(success)  # Should fail due to unmet dependency
        
        # Complete prerequisite first
        self.tracker.start_step_execution(step1_id)
        self.tracker.complete_step_execution(step1_id, {'result': 'done'})
        
        # Now dependent step should execute
        success = self.tracker.start_step_execution(step2_id)
        self.assertTrue(success)
    
    def test_step_validation(self):
        """Test step validation"""
        step_id = "validation_test_step"
        
        # Register and complete a step
        self.tracker.register_step(step_id, self.sample_step_data)
        self.tracker.start_step_execution(step_id)
        self.tracker.complete_step_execution(step_id, {'confidence': 0.7})
        
        # Validate the step
        validation = self.tracker.validate_step(step_id)
        
        self.assertIsInstance(validation, StepValidation)
        self.assertTrue(validation.is_valid)
        self.assertGreater(validation.validation_score, 0.5)
    
    def test_execution_summary(self):
        """Test execution summary generation"""
        # Register and execute multiple steps
        for i in range(3):
            step_id = f"summary_test_step_{i}"
            self.tracker.register_step(step_id, self.sample_step_data)
            self.tracker.start_step_execution(step_id)
            self.tracker.complete_step_execution(step_id, {'confidence': 0.8})
        
        # Fail one step
        fail_step_id = "fail_step"
        self.tracker.register_step(fail_step_id, self.sample_step_data)
        self.tracker.start_step_execution(fail_step_id)
        self.tracker.fail_step_execution(fail_step_id, "Test error")
        
        summary = self.tracker.get_execution_summary()
        
        self.assertEqual(summary['total_steps'], 4)
        self.assertEqual(summary['completed_steps'], 3)
        self.assertEqual(summary['failed_steps'], 1)
        self.assertEqual(summary['success_rate'], 0.75)
    
    def test_dependency_graph(self):
        """Test dependency graph generation"""
        # Create a simple dependency chain
        steps = ['step_a', 'step_b', 'step_c']
        
        for i, step_id in enumerate(steps):
            deps = [steps[i-1]] if i > 0 else None
            self.tracker.register_step(step_id, self.sample_step_data, dependencies=deps)
        
        graph = self.tracker.get_step_dependency_graph()
        
        self.assertIn('nodes', graph)
        self.assertIn('edges', graph)
        self.assertEqual(len(graph['nodes']), 3)
        self.assertEqual(len(graph['edges']), 2)  # A->B, B->C

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete reasoning system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.reasoner = ChainOfThoughtReasoner()
        self.scorer = ConfidenceScorer()
        self.tracker = ReasoningStepTracker()
        
        # Mock Bedrock for integration tests
        self.reasoner.bedrock_runtime = Mock()
        
        # Sample transaction for integration testing
        self.integration_transaction = {
            'id': 'integration_test_001',
            'user_id': 'integration_user',
            'amount': 2500.0,
            'currency': 'USD',
            'merchant': 'UNKNOWN_MERCHANT',
            'category': 'OTHER',
            'location': 'FOREIGN_COUNTRY',
            'timestamp': datetime.now().isoformat(),
            'card_type': 'CREDIT'
        }
    
    def test_end_to_end_reasoning_flow(self):
        """Test complete end-to-end reasoning flow"""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': json.dumps({
                    'steps': [{
                        'step_type': 'observation',
                        'reasoning': 'High amount transaction at unknown merchant in foreign location',
                        'evidence': ['High amount: $2500', 'Unknown merchant', 'Foreign location'],
                        'confidence': 0.9,
                        'key_findings': ['Suspicious merchant', 'Unusual location']
                    }],
                    'final_assessment': {
                        'is_fraud': True,
                        'confidence': 0.85,
                        'risk_level': 'HIGH',
                        'primary_concerns': ['Unknown merchant', 'Foreign location'],
                        'recommended_action': 'BLOCK'
                    }
                })
            }]
        }).encode()
        
        self.reasoner.bedrock_runtime.invoke_model.return_value = mock_response
        
        # Execute reasoning
        result = self.reasoner.analyze_transaction_with_reasoning(
            self.integration_transaction,
            {'test_context': True}
        )
        
        # Verify result structure
        self.assertIsInstance(result, ReasoningResult)
        self.assertEqual(result.transaction_id, 'integration_test_001')
        self.assertGreater(len(result.steps), 0)
        self.assertIn('is_fraud', result.final_decision)
        self.assertGreater(result.overall_confidence, 0.0)
        
        # Test confidence assessment on the result
        reasoning_data = {
            'transaction': self.integration_transaction,
            'reasoning': result.reasoning_summary,
            'evidence': result.evidence_summary,
            'confidence': result.overall_confidence
        }
        
        confidence_assessment = self.scorer.assess_confidence(reasoning_data)
        self.assertIsInstance(confidence_assessment, ConfidenceAssessment)
        self.assertGreater(confidence_assessment.overall_confidence, 0.0)

def run_all_tests():
    """Run all reasoning engine tests"""
    print("🧪 Running Chain-of-Thought Reasoning Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestChainOfThoughtReasoner,
        TestConfidenceScorer,
        TestReasoningStepTracker,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    if not result.failures and not result.errors:
        print("🎉 All tests passed!")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)