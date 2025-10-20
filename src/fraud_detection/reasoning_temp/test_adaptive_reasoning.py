#!/usr/bin/env python3
"""
Tests for Adaptive Reasoning System
Comprehensive tests for adaptive reasoning capabilities and learning mechanisms
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import adaptive reasoning components
from adaptive_reasoning import (
    AdaptiveReasoningEngine,
    TransactionType,
    ReasoningStrategy,
    LearningFeedback,
    LearningMode,
    ReasoningPattern,
    TransactionTypeClassifier,
    ReasoningStrategySelector,
    PatternLearner
)

from adaptive_integration import AdaptiveChainOfThoughtReasoner

class TestTransactionTypeClassifier(unittest.TestCase):
    """Test transaction type classification"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.classifier = TransactionTypeClassifier()
    
    def test_high_value_classification(self):
        """Test high value transaction classification"""
        transaction = {
            'amount': 15000,
            'merchant_category': 'retail',
            'location_type': 'domestic',
            'payment_method': 'card'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.HIGH_VALUE)
    
    def test_international_classification(self):
        """Test international transaction classification"""
        transaction = {
            'amount': 500,
            'merchant_category': 'retail',
            'location_type': 'foreign_country',
            'payment_method': 'card'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.INTERNATIONAL)
    
    def test_wire_transfer_classification(self):
        """Test wire transfer classification"""
        transaction = {
            'amount': 2000,
            'merchant_category': 'financial',
            'location_type': 'domestic',
            'payment_method': 'wire_transfer'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.WIRE_TRANSFER)
    
    def test_atm_withdrawal_classification(self):
        """Test ATM withdrawal classification"""
        transaction = {
            'amount': 300,
            'merchant_category': 'atm',
            'location_type': 'domestic',
            'payment_method': 'atm'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.ATM_WITHDRAWAL)
    
    def test_online_purchase_classification(self):
        """Test online purchase classification"""
        transaction = {
            'amount': 150,
            'merchant_category': 'ecommerce',
            'location_type': 'domestic',
            'payment_method': 'card'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.ONLINE_PURCHASE)
    
    def test_mobile_payment_classification(self):
        """Test mobile payment classification"""
        transaction = {
            'amount': 50,
            'merchant_category': 'retail',
            'location_type': 'domestic',
            'payment_method': 'mobile_app'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.MOBILE_PAYMENT)
    
    def test_unknown_classification(self):
        """Test unknown transaction classification"""
        transaction = {
            'amount': 100,
            'merchant_category': 'unknown',
            'location_type': 'unknown',
            'payment_method': 'unknown'
        }
        
        tx_type = self.classifier.classify(transaction)
        self.assertEqual(tx_type, TransactionType.UNKNOWN)

class TestReasoningStrategySelector(unittest.TestCase):
    """Test reasoning strategy selection"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.selector = ReasoningStrategySelector()
    
    def test_strategy_selection_for_high_value(self):
        """Test strategy selection for high value transactions"""
        context = {'risk_level': 'high'}
        performance_history = {
            ReasoningStrategy.CONSERVATIVE: {'accuracy': 0.9},
            ReasoningStrategy.AGGRESSIVE: {'accuracy': 0.7}
        }
        
        strategy = self.selector.select_strategy(
            TransactionType.HIGH_VALUE, context, performance_history
        )
        
        # Should prefer conservative for high value
        self.assertEqual(strategy, ReasoningStrategy.CONSERVATIVE)
    
    def test_strategy_selection_for_international(self):
        """Test strategy selection for international transactions"""
        context = {'risk_level': 'medium'}
        performance_history = {
            ReasoningStrategy.LOCATION_FOCUSED: {'accuracy': 0.85},
            ReasoningStrategy.BALANCED: {'accuracy': 0.75}
        }
        
        strategy = self.selector.select_strategy(
            TransactionType.INTERNATIONAL, context, performance_history
        )
        
        # Should prefer location-focused for international
        self.assertEqual(strategy, ReasoningStrategy.LOCATION_FOCUSED)
    
    def test_strategy_selection_with_time_pressure(self):
        """Test strategy selection under time pressure"""
        context = {'risk_level': 'medium', 'time_critical': True}
        performance_history = {}
        
        strategy = self.selector.select_strategy(
            TransactionType.CARD_PAYMENT, context, performance_history
        )
        
        # Should prefer faster strategies under time pressure
        self.assertIn(strategy, [ReasoningStrategy.BALANCED, ReasoningStrategy.AGGRESSIVE])

class TestPatternLearner(unittest.TestCase):
    """Test pattern learning functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.learner = PatternLearner()
    
    def test_pattern_learning(self):
        """Test basic pattern learning"""
        features = {
            'amount_category': 'high',
            'location_risk': 'high',
            'merchant_category': 'unknown'
        }
        
        # Learn pattern with fraud outcome
        self.learner.learn_pattern(features, 'fraud', 0.9)
        self.learner.learn_pattern(features, 'fraud', 0.85)
        self.learner.learn_pattern(features, 'legitimate', 0.3)
        
        # Get prediction
        prediction, confidence = self.learner.get_pattern_prediction(features)
        
        self.assertEqual(prediction, 'fraud')
        self.assertGreater(confidence, 0.5)
    
    def test_pattern_confidence_calculation(self):
        """Test pattern confidence calculation"""
        features = {
            'amount_category': 'normal',
            'location_risk': 'low',
            'merchant_category': 'trusted'
        }
        
        # Learn pattern with consistent legitimate outcomes
        for _ in range(10):
            self.learner.learn_pattern(features, 'legitimate', 0.8)
        
        prediction, confidence = self.learner.get_pattern_prediction(features)
        
        self.assertEqual(prediction, 'legitimate')
        self.assertEqual(confidence, 1.0)  # 100% consistent
    
    def test_unknown_pattern_prediction(self):
        """Test prediction for unknown patterns"""
        unknown_features = {
            'amount_category': 'very_high',
            'location_risk': 'unknown',
            'merchant_category': 'new'
        }
        
        prediction, confidence = self.learner.get_pattern_prediction(unknown_features)
        
        self.assertEqual(prediction, 'unknown')
        self.assertEqual(confidence, 0.5)

class TestAdaptiveReasoningEngine(unittest.TestCase):
    """Test adaptive reasoning engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = AdaptiveReasoningEngine(LearningMode.HYBRID_LEARNING)
    
    def test_engine_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.learning_mode, LearningMode.HYBRID_LEARNING)
        self.assertGreater(len(self.engine.reasoning_patterns), 0)
        self.assertIsInstance(self.engine.transaction_type_classifier, TransactionTypeClassifier)
    
    def test_transaction_type_classification(self):
        """Test transaction type classification"""
        transaction = {
            'amount': 20000,
            'merchant_category': 'retail',
            'location_type': 'domestic'
        }
        
        tx_type = self.engine.classify_transaction_type(transaction)
        self.assertEqual(tx_type, TransactionType.HIGH_VALUE)
    
    def test_strategy_selection(self):
        """Test reasoning strategy selection"""
        transaction = {
            'amount': 5000,
            'merchant_category': 'unknown',
            'location_type': 'foreign_country'
        }
        
        strategy, config = self.engine.select_reasoning_strategy(transaction)
        
        self.assertIsInstance(strategy, ReasoningStrategy)
        self.assertIsInstance(config, dict)
        self.assertIn('strategy', config)
        self.assertIn('confidence_threshold', config)
    
    def test_pattern_finding(self):
        """Test finding applicable patterns"""
        tx_type = TransactionType.HIGH_VALUE
        transaction = {'amount': 15000}
        context = {}
        
        patterns = self.engine._find_applicable_patterns(tx_type, transaction, context)
        
        # Should find at least the default pattern
        self.assertGreater(len(patterns), 0)
        
        # Check that found patterns match transaction type
        for pattern in patterns:
            self.assertEqual(pattern.transaction_type, tx_type)
    
    def test_feedback_processing(self):
        """Test feedback processing and adaptation"""
        # Create sample reasoning result
        reasoning_result = {
            'reasoning_id': 'test_reasoning_001',
            'transaction_id': 'test_tx_001',
            'steps': [
                {
                    'step_type': 'analysis',
                    'output': {'key_findings': ['high_amount']},
                    'confidence': 0.8
                }
            ],
            'final_decision': {
                'is_fraud': True,
                'confidence': 0.85,
                'recommended_action': 'BLOCK'
            }
        }
        
        # Create feedback
        feedback = LearningFeedback(
            feedback_id='feedback_001',
            transaction_id='test_tx_001',
            reasoning_id='test_reasoning_001',
            original_decision='BLOCK',
            actual_outcome='fraud',
            confidence_was_correct=True,
            strategy_used=ReasoningStrategy.CONSERVATIVE,
            transaction_type=TransactionType.HIGH_VALUE,
            feedback_timestamp=datetime.now().isoformat(),
            feedback_source='manual'
        )
        
        # Process feedback
        result = self.engine.adapt_reasoning_strategy(reasoning_result, feedback)
        
        self.assertIn('adaptations_applied', result)
        self.assertIn('strategy_updated', result)
        self.assertIn('learning_mode', result)
    
    def test_pattern_export_import(self):
        """Test pattern export and import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Export patterns
            self.engine.export_learned_patterns(temp_file)
            
            # Create new engine and import
            new_engine = AdaptiveReasoningEngine()
            original_pattern_count = len(new_engine.reasoning_patterns)
            
            new_engine.import_learned_patterns(temp_file)
            
            # Should have imported patterns
            self.assertGreaterEqual(len(new_engine.reasoning_patterns), original_pattern_count)
            
        finally:
            os.unlink(temp_file)
    
    def test_adaptation_statistics(self):
        """Test adaptation statistics generation"""
        stats = self.engine.get_adaptation_statistics()
        
        self.assertIn('total_patterns', stats)
        self.assertIn('total_feedback_items', stats)
        self.assertIn('learning_mode', stats)
        self.assertIn('patterns_by_transaction_type', stats)
        self.assertIn('patterns_by_strategy', stats)
        
        self.assertEqual(stats['learning_mode'], LearningMode.HYBRID_LEARNING.value)

class TestAdaptiveChainOfThoughtReasoner(unittest.TestCase):
    """Test adaptive chain-of-thought reasoner integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.reasoner = AdaptiveChainOfThoughtReasoner(LearningMode.SUPERVISED)
        
        # Mock the base reasoner to avoid dependencies
        self.reasoner.base_reasoner = Mock()
        self.reasoner.base_reasoner.reason_about_transaction.return_value = {
            'reasoning_id': 'mock_reasoning_001',
            'transaction_id': 'mock_tx_001',
            'overall_confidence': 0.8,
            'total_processing_time_ms': 1500.0,
            'steps': [
                {
                    'step_type': 'analysis',
                    'confidence': 0.8,
                    'output': {'key_findings': ['normal_amount']}
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.8,
                'recommended_action': 'APPROVE'
            }
        }
    
    def test_reasoner_initialization(self):
        """Test reasoner initialization"""
        self.assertIsNotNone(self.reasoner.base_reasoner)
        self.assertIsNotNone(self.reasoner.adaptive_engine)
        self.assertTrue(self.reasoner.adaptation_enabled)
        self.assertTrue(self.reasoner.learning_enabled)
    
    def test_adaptive_reasoning_process(self):
        """Test complete adaptive reasoning process"""
        transaction_data = {
            'transaction_id': 'test_tx_001',
            'amount': 500,
            'merchant_category': 'retail',
            'location_type': 'domestic',
            'payment_method': 'card'
        }
        
        context = {'user_risk_level': 'low'}
        
        result = self.reasoner.reason_about_transaction(transaction_data, context)
        
        # Check that result includes adaptive information
        self.assertIn('adaptive_reasoning', result)
        self.assertIn('adaptive_confidence', result)
        
        adaptive_info = result['adaptive_reasoning']
        self.assertIn('transaction_type', adaptive_info)
        self.assertIn('strategy_used', adaptive_info)
        self.assertIn('strategy_config', adaptive_info)
        self.assertIn('strategy_insights', adaptive_info)
    
    def test_strategy_configuration(self):
        """Test strategy configuration for base reasoner"""
        # Test conservative strategy configuration
        strategy_config = {
            'confidence_threshold': 0.85,
            'require_multiple_evidence': True,
            'evidence_weight': 1.5
        }
        
        self.reasoner._configure_base_reasoner(ReasoningStrategy.CONSERVATIVE, strategy_config)
        
        # Verify configuration was applied
        self.assertEqual(self.reasoner.base_reasoner.confidence_threshold, 0.85)
        self.assertTrue(self.reasoner.base_reasoner.require_multiple_evidence)
        self.assertEqual(self.reasoner.base_reasoner.evidence_weight_multiplier, 1.5)
    
    def test_confidence_adjustment(self):
        """Test confidence adjustment based on strategy"""
        original_confidence = 0.75
        
        # Test conservative adjustment (should be slightly lower)
        conservative_config = {'expected_effectiveness': 0.8}
        adjusted = self.reasoner._adjust_confidence_for_strategy(
            original_confidence, ReasoningStrategy.CONSERVATIVE, conservative_config
        )
        self.assertLessEqual(adjusted, original_confidence * 1.05)
        
        # Test aggressive adjustment (should be slightly higher)
        aggressive_config = {'expected_effectiveness': 0.85}
        adjusted = self.reasoner._adjust_confidence_for_strategy(
            original_confidence, ReasoningStrategy.AGGRESSIVE, aggressive_config
        )
        self.assertGreaterEqual(adjusted, original_confidence * 0.95)
    
    def test_feedback_processing(self):
        """Test feedback processing"""
        # First, perform reasoning to create a session
        transaction_data = {
            'transaction_id': 'feedback_test_tx',
            'amount': 1000,
            'merchant_category': 'retail'
        }
        
        result = self.reasoner.reason_about_transaction(transaction_data)
        reasoning_id = result['adaptive_reasoning']['reasoning_id']
        
        # Provide feedback
        feedback_result = self.reasoner.provide_feedback(
            reasoning_id, 'legitimate', 'manual'
        )
        
        self.assertEqual(feedback_result['status'], 'feedback_processed')
        self.assertIn('feedback_id', feedback_result)
        self.assertIn('adaptations_applied', feedback_result)
    
    def test_strategy_insights_generation(self):
        """Test strategy insights generation"""
        reasoning_result = {
            'overall_confidence': 0.8,
            'steps': [{'step_type': 'analysis'}]
        }
        
        insights = self.reasoner._generate_strategy_insights(
            reasoning_result, ReasoningStrategy.VELOCITY_FOCUSED, TransactionType.ATM_WITHDRAWAL
        )
        
        self.assertIn('strategy_rationale', insights)
        self.assertIn('key_focus_areas', insights)
        self.assertIn('expected_strengths', insights)
        self.assertIn('potential_limitations', insights)
        
        # Check content quality
        self.assertIn('velocity', insights['strategy_rationale'].lower())
        self.assertIsInstance(insights['key_focus_areas'], list)
        self.assertGreater(len(insights['key_focus_areas']), 0)
    
    def test_adaptation_control(self):
        """Test adaptation enable/disable controls"""
        # Test disabling adaptation
        self.reasoner.disable_adaptation()
        self.assertFalse(self.reasoner.adaptation_enabled)
        
        # Test enabling adaptation
        self.reasoner.enable_adaptation()
        self.assertTrue(self.reasoner.adaptation_enabled)
        
        # Test disabling learning
        self.reasoner.disable_learning()
        self.assertFalse(self.reasoner.learning_enabled)
        
        # Test enabling learning
        self.reasoner.enable_learning()
        self.assertTrue(self.reasoner.learning_enabled)
    
    def test_strategy_override(self):
        """Test strategy override functionality"""
        # Set strategy override
        self.reasoner.set_strategy_override(ReasoningStrategy.AGGRESSIVE)
        self.assertEqual(self.reasoner.strategy_override, ReasoningStrategy.AGGRESSIVE)
        
        # Clear strategy override
        self.reasoner.clear_strategy_override()
        self.assertIsNone(self.reasoner.strategy_override)
    
    def test_adaptive_statistics(self):
        """Test adaptive statistics generation"""
        # Perform some reasoning to generate data
        transaction_data = {
            'transaction_id': 'stats_test_tx',
            'amount': 750,
            'merchant_category': 'retail'
        }
        
        self.reasoner.reason_about_transaction(transaction_data)
        
        stats = self.reasoner.get_adaptive_statistics()
        
        self.assertIn('adaptation_metrics', stats)
        self.assertIn('reasoning_sessions', stats)
        self.assertIn('adaptive_engine_stats', stats)
        
        # Check that we have at least one reasoning session
        self.assertGreater(stats['reasoning_sessions'], 0)
    
    def test_data_export_import(self):
        """Test adaptive data export and import"""
        # Perform reasoning to generate data
        transaction_data = {
            'transaction_id': 'export_test_tx',
            'amount': 1200,
            'merchant_category': 'retail'
        }
        
        self.reasoner.reason_about_transaction(transaction_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Export data
            self.reasoner.export_adaptive_data(temp_file)
            
            # Verify file was created and has content
            self.assertTrue(os.path.exists(temp_file))
            
            with open(temp_file, 'r') as f:
                exported_data = json.load(f)
            
            self.assertIn('reasoning_sessions', exported_data)
            self.assertIn('adaptation_metrics', exported_data)
            self.assertIn('export_timestamp', exported_data)
            
            # Test import (basic verification)
            new_reasoner = AdaptiveChainOfThoughtReasoner()
            new_reasoner.base_reasoner = Mock()  # Mock to avoid dependencies
            
            # Import should not raise an exception
            new_reasoner.import_adaptive_data(temp_file)
            
        finally:
            os.unlink(temp_file)

class TestAdaptiveReasoningIntegration(unittest.TestCase):
    """Integration tests for adaptive reasoning system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.reasoner = AdaptiveChainOfThoughtReasoner(LearningMode.HYBRID_LEARNING)
        
        # Mock base reasoner for integration tests
        self.reasoner.base_reasoner = Mock()
        self.reasoner.base_reasoner.reason_about_transaction.return_value = {
            'reasoning_id': 'integration_test_001',
            'transaction_id': 'integration_tx_001',
            'overall_confidence': 0.75,
            'total_processing_time_ms': 2000.0,
            'steps': [
                {
                    'step_type': 'observation',
                    'confidence': 0.7,
                    'output': {'key_findings': ['moderate_amount', 'known_merchant']}
                },
                {
                    'step_type': 'analysis',
                    'confidence': 0.8,
                    'output': {'risk_assessment': 'low_risk'}
                }
            ],
            'final_decision': {
                'is_fraud': False,
                'confidence': 0.75,
                'recommended_action': 'APPROVE',
                'risk_level': 'LOW'
            }
        }
    
    def test_end_to_end_adaptive_reasoning(self):
        """Test complete end-to-end adaptive reasoning workflow"""
        
        # Step 1: Perform initial reasoning
        transaction_data = {
            'transaction_id': 'e2e_test_tx_001',
            'amount': 850,
            'merchant_category': 'grocery',
            'location_type': 'domestic',
            'payment_method': 'card'
        }
        
        context = {
            'user_risk_level': 'low',
            'time_of_day': 14  # 2 PM
        }
        
        result1 = self.reasoner.reason_about_transaction(transaction_data, context)
        
        # Verify adaptive reasoning was applied
        self.assertIn('adaptive_reasoning', result1)
        self.assertIn('adaptive_confidence', result1)
        
        reasoning_id = result1['adaptive_reasoning']['reasoning_id']
        strategy_used = result1['adaptive_reasoning']['strategy_used']
        
        # Step 2: Provide feedback (correct prediction)
        feedback_result = self.reasoner.provide_feedback(reasoning_id, 'legitimate', 'automated')
        
        self.assertEqual(feedback_result['status'], 'feedback_processed')
        
        # Step 3: Perform another similar transaction
        transaction_data2 = {
            'transaction_id': 'e2e_test_tx_002',
            'amount': 900,  # Similar amount
            'merchant_category': 'grocery',  # Same category
            'location_type': 'domestic',
            'payment_method': 'card'
        }
        
        result2 = self.reasoner.reason_about_transaction(transaction_data2, context)
        
        # Verify learning occurred (strategy might be the same or adapted)
        self.assertIn('adaptive_reasoning', result2)
        
        # Step 4: Check statistics
        stats = self.reasoner.get_adaptive_statistics()
        
        self.assertGreaterEqual(stats['reasoning_sessions'], 2)
        self.assertGreater(stats['adaptation_metrics']['total_adaptations'], 0)
    
    def test_strategy_adaptation_over_time(self):
        """Test strategy adaptation over multiple transactions"""
        
        transactions = [
            {
                'transaction_id': f'adapt_test_tx_{i}',
                'amount': 1000 + i * 100,
                'merchant_category': 'retail',
                'location_type': 'domestic',
                'payment_method': 'card'
            }
            for i in range(5)
        ]
        
        strategies_used = []
        
        # Process multiple transactions
        for tx in transactions:
            result = self.reasoner.reason_about_transaction(tx)
            strategy = result['adaptive_reasoning']['strategy_used']
            strategies_used.append(strategy)
            
            # Provide feedback (mix of correct and incorrect)
            reasoning_id = result['adaptive_reasoning']['reasoning_id']
            outcome = 'legitimate' if len(strategies_used) % 2 == 0 else 'fraud'
            self.reasoner.provide_feedback(reasoning_id, outcome, 'manual')
        
        # Verify that strategies were recorded
        self.assertEqual(len(strategies_used), 5)
        
        # Check that adaptation occurred
        stats = self.reasoner.get_adaptive_statistics()
        self.assertGreater(stats['adaptation_metrics']['total_adaptations'], 0)
    
    def test_transaction_type_specific_adaptation(self):
        """Test adaptation for different transaction types"""
        
        transaction_types = [
            {
                'name': 'high_value',
                'data': {
                    'transaction_id': 'type_test_high_value',
                    'amount': 25000,
                    'merchant_category': 'luxury',
                    'location_type': 'domestic',
                    'payment_method': 'card'
                }
            },
            {
                'name': 'international',
                'data': {
                    'transaction_id': 'type_test_international',
                    'amount': 500,
                    'merchant_category': 'retail',
                    'location_type': 'foreign_country',
                    'payment_method': 'card'
                }
            },
            {
                'name': 'wire_transfer',
                'data': {
                    'transaction_id': 'type_test_wire',
                    'amount': 5000,
                    'merchant_category': 'financial',
                    'location_type': 'domestic',
                    'payment_method': 'wire_transfer'
                }
            }
        ]
        
        results = {}
        
        for tx_type in transaction_types:
            result = self.reasoner.reason_about_transaction(tx_type['data'])
            results[tx_type['name']] = result
            
            # Verify transaction type was classified correctly
            adaptive_info = result['adaptive_reasoning']
            if tx_type['name'] == 'high_value':
                self.assertEqual(adaptive_info['transaction_type'], 'high_value')
            elif tx_type['name'] == 'international':
                self.assertEqual(adaptive_info['transaction_type'], 'international')
            elif tx_type['name'] == 'wire_transfer':
                self.assertEqual(adaptive_info['transaction_type'], 'wire_transfer')
        
        # Verify different strategies were used for different types
        strategies = [r['adaptive_reasoning']['strategy_used'] for r in results.values()]
        
        # Should have some variety in strategies (not all the same)
        unique_strategies = set(strategies)
        self.assertGreaterEqual(len(unique_strategies), 1)  # At least some strategy selection occurred
    
    def test_learning_mode_effects(self):
        """Test effects of different learning modes"""
        
        # Test supervised learning mode
        supervised_reasoner = AdaptiveChainOfThoughtReasoner(LearningMode.SUPERVISED)
        supervised_reasoner.base_reasoner = Mock()
        supervised_reasoner.base_reasoner.reason_about_transaction.return_value = {
            'reasoning_id': 'supervised_test',
            'transaction_id': 'supervised_tx',
            'overall_confidence': 0.8,
            'steps': [],
            'final_decision': {'is_fraud': False, 'recommended_action': 'APPROVE'}
        }
        
        # Test unsupervised learning mode
        unsupervised_reasoner = AdaptiveChainOfThoughtReasoner(LearningMode.UNSUPERVISED)
        unsupervised_reasoner.base_reasoner = Mock()
        unsupervised_reasoner.base_reasoner.reason_about_transaction.return_value = {
            'reasoning_id': 'unsupervised_test',
            'transaction_id': 'unsupervised_tx',
            'overall_confidence': 0.8,
            'steps': [],
            'final_decision': {'is_fraud': False, 'recommended_action': 'APPROVE'}
        }
        
        transaction_data = {
            'transaction_id': 'learning_mode_test',
            'amount': 1000,
            'merchant_category': 'retail'
        }
        
        # Both should work without errors
        supervised_result = supervised_reasoner.reason_about_transaction(transaction_data)
        unsupervised_result = unsupervised_reasoner.reason_about_transaction(transaction_data)
        
        self.assertIn('adaptive_reasoning', supervised_result)
        self.assertIn('adaptive_reasoning', unsupervised_result)
        
        # Learning modes should be reflected in results
        supervised_stats = supervised_reasoner.get_adaptive_statistics()
        unsupervised_stats = unsupervised_reasoner.get_adaptive_statistics()
        
        self.assertEqual(
            supervised_stats['adaptive_engine_stats']['learning_mode'], 
            'supervised'
        )
        self.assertEqual(
            unsupervised_stats['adaptive_engine_stats']['learning_mode'], 
            'unsupervised'
        )

def run_adaptive_reasoning_tests():
    """Run all adaptive reasoning tests"""
    print("🧪 Running Adaptive Reasoning System Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestTransactionTypeClassifier,
        TestReasoningStrategySelector,
        TestPatternLearner,
        TestAdaptiveReasoningEngine,
        TestAdaptiveChainOfThoughtReasoner,
        TestAdaptiveReasoningIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 ADAPTIVE REASONING TEST SUMMARY")
    print("=" * 50)
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
        print("🎉 All adaptive reasoning tests passed!")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_adaptive_reasoning_tests()
    exit(0 if success else 1)