#!/usr/bin/env python3
"""
Adaptive Reasoning Engine
Implements pattern-based reasoning adaptation and learning mechanisms
"""

import json
import logging
import pickle
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import statistics
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionType(Enum):
    """Different transaction types for adaptive reasoning"""
    ONLINE_PURCHASE = "online_purchase"
    ATM_WITHDRAWAL = "atm_withdrawal"
    WIRE_TRANSFER = "wire_transfer"
    CARD_PAYMENT = "card_payment"
    MOBILE_PAYMENT = "mobile_payment"
    INTERNATIONAL = "international"
    HIGH_VALUE = "high_value"
    RECURRING = "recurring"
    PEER_TO_PEER = "peer_to_peer"
    UNKNOWN = "unknown"

class ReasoningStrategy(Enum):
    """Different reasoning strategies"""
    CONSERVATIVE = "conservative"  # High scrutiny, low false positives
    BALANCED = "balanced"         # Standard approach
    AGGRESSIVE = "aggressive"     # High detection, higher false positives
    VELOCITY_FOCUSED = "velocity_focused"  # Focus on transaction patterns
    AMOUNT_FOCUSED = "amount_focused"      # Focus on amount anomalies
    LOCATION_FOCUSED = "location_focused"  # Focus on geographic patterns
    BEHAVIORAL = "behavioral"     # Focus on user behavior patterns
    HYBRID = "hybrid"            # Combination approach

class LearningMode(Enum):
    """Learning modes for adaptation"""
    SUPERVISED = "supervised"     # Learn from labeled feedback
    UNSUPERVISED = "unsupervised" # Learn from patterns
    REINFORCEMENT = "reinforcement" # Learn from outcomes
    HYBRID_LEARNING = "hybrid_learning" # Combination approach

@dataclass
class ReasoningPattern:
    """Represents a learned reasoning pattern"""
    pattern_id: str
    transaction_type: TransactionType
    strategy: ReasoningStrategy
    conditions: Dict[str, Any]
    success_rate: float
    confidence_threshold: float
    usage_count: int
    last_updated: str
    effectiveness_score: float
    false_positive_rate: float
    false_negative_rate: float

@dataclass
class AdaptationRule:
    """Rule for adapting reasoning based on conditions"""
    rule_id: str
    name: str
    conditions: Dict[str, Any]
    target_strategy: ReasoningStrategy
    priority: int
    active: bool
    success_count: int
    failure_count: int
    created_at: str
    last_applied: Optional[str]

@dataclass
class LearningFeedback:
    """Feedback for learning and adaptation"""
    feedback_id: str
    transaction_id: str
    reasoning_id: str
    original_decision: str
    actual_outcome: str  # 'fraud', 'legitimate', 'unknown'
    confidence_was_correct: bool
    strategy_used: ReasoningStrategy
    transaction_type: TransactionType
    feedback_timestamp: str
    feedback_source: str  # 'manual', 'automated', 'customer'

class AdaptiveReasoningEngine:
    """
    Implements adaptive reasoning capabilities with pattern learning
    """
    
    def __init__(self, learning_mode: LearningMode = LearningMode.HYBRID_LEARNING):
        """Initialize adaptive reasoning engine"""
        self.learning_mode = learning_mode
        self.reasoning_patterns: Dict[str, ReasoningPattern] = {}
        self.adaptation_rules: Dict[str, AdaptationRule] = {}
        self.learning_feedback: List[LearningFeedback] = []
        self.strategy_performance: Dict[ReasoningStrategy, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.transaction_type_classifier = TransactionTypeClassifier()
        self.strategy_selector = ReasoningStrategySelector()
        self.pattern_learner = PatternLearner()
        self.adaptation_history: deque = deque(maxlen=1000)  # Keep last 1000 adaptations
        
        # Initialize default strategies
        self._initialize_default_strategies()
        
        logger.info(f"AdaptiveReasoningEngine initialized with {learning_mode.value} learning mode")
    
    def _initialize_default_strategies(self):
        """Initialize default reasoning strategies for different transaction types"""
        
        default_strategies = {
            TransactionType.HIGH_VALUE: ReasoningStrategy.CONSERVATIVE,
            TransactionType.INTERNATIONAL: ReasoningStrategy.LOCATION_FOCUSED,
            TransactionType.WIRE_TRANSFER: ReasoningStrategy.CONSERVATIVE,
            TransactionType.ATM_WITHDRAWAL: ReasoningStrategy.VELOCITY_FOCUSED,
            TransactionType.ONLINE_PURCHASE: ReasoningStrategy.BALANCED,
            TransactionType.MOBILE_PAYMENT: ReasoningStrategy.BEHAVIORAL,
            TransactionType.PEER_TO_PEER: ReasoningStrategy.AGGRESSIVE,
            TransactionType.RECURRING: ReasoningStrategy.BEHAVIORAL,
            TransactionType.CARD_PAYMENT: ReasoningStrategy.BALANCED,
            TransactionType.UNKNOWN: ReasoningStrategy.BALANCED
        }
        
        for tx_type, strategy in default_strategies.items():
            pattern_id = f"default_{tx_type.value}_{strategy.value}"
            
            pattern = ReasoningPattern(
                pattern_id=pattern_id,
                transaction_type=tx_type,
                strategy=strategy,
                conditions={"is_default": True},
                success_rate=0.75,  # Initial assumption
                confidence_threshold=0.7,
                usage_count=0,
                last_updated=datetime.now().isoformat(),
                effectiveness_score=0.75,
                false_positive_rate=0.1,
                false_negative_rate=0.15
            )
            
            self.reasoning_patterns[pattern_id] = pattern
        
        logger.info(f"Initialized {len(default_strategies)} default reasoning strategies")
    
    def classify_transaction_type(self, transaction_data: Dict[str, Any]) -> TransactionType:
        """Classify transaction type for adaptive reasoning"""
        return self.transaction_type_classifier.classify(transaction_data)
    
    def select_reasoning_strategy(self, transaction_data: Dict[str, Any], 
                                context: Dict[str, Any] = None) -> Tuple[ReasoningStrategy, Dict[str, Any]]:
        """Select optimal reasoning strategy based on transaction and context"""
        
        # Classify transaction type
        tx_type = self.classify_transaction_type(transaction_data)
        
        # Get context information
        context = context or {}
        
        # Find applicable patterns
        applicable_patterns = self._find_applicable_patterns(tx_type, transaction_data, context)
        
        # Select best strategy
        if applicable_patterns:
            best_pattern = max(applicable_patterns, key=lambda p: p.effectiveness_score)
            selected_strategy = best_pattern.strategy
            strategy_config = self._get_strategy_configuration(selected_strategy, best_pattern)
            
            logger.info(f"Selected {selected_strategy.value} strategy for {tx_type.value} transaction")
        else:
            # Fallback to default strategy
            selected_strategy = self._get_default_strategy(tx_type)
            strategy_config = self._get_strategy_configuration(selected_strategy)
            
            logger.info(f"Using default {selected_strategy.value} strategy for {tx_type.value} transaction")
        
        # Record strategy selection
        self._record_strategy_selection(tx_type, selected_strategy, transaction_data)
        
        return selected_strategy, strategy_config
    
    def _find_applicable_patterns(self, tx_type: TransactionType, 
                                transaction_data: Dict[str, Any],
                                context: Dict[str, Any]) -> List[ReasoningPattern]:
        """Find reasoning patterns applicable to current transaction"""
        
        applicable_patterns = []
        
        for pattern in self.reasoning_patterns.values():
            if pattern.transaction_type == tx_type:
                # Check if pattern conditions are met
                if self._pattern_conditions_met(pattern, transaction_data, context):
                    applicable_patterns.append(pattern)
        
        return applicable_patterns
    
    def _pattern_conditions_met(self, pattern: ReasoningPattern, 
                              transaction_data: Dict[str, Any],
                              context: Dict[str, Any]) -> bool:
        """Check if pattern conditions are satisfied"""
        
        conditions = pattern.conditions
        
        # Check amount conditions
        if 'amount_range' in conditions:
            amount = transaction_data.get('amount', 0)
            min_amount, max_amount = conditions['amount_range']
            if not (min_amount <= amount <= max_amount):
                return False
        
        # Check time conditions
        if 'time_of_day' in conditions:
            current_hour = datetime.now().hour
            allowed_hours = conditions['time_of_day']
            if current_hour not in allowed_hours:
                return False
        
        # Check location conditions
        if 'location_type' in conditions:
            location_type = transaction_data.get('location_type', 'unknown')
            if location_type not in conditions['location_type']:
                return False
        
        # Check merchant conditions
        if 'merchant_category' in conditions:
            merchant_category = transaction_data.get('merchant_category', 'unknown')
            if merchant_category not in conditions['merchant_category']:
                return False
        
        # Check user behavior conditions
        if 'user_risk_level' in conditions:
            user_risk = context.get('user_risk_level', 'medium')
            if user_risk not in conditions['user_risk_level']:
                return False
        
        return True
    
    def _get_default_strategy(self, tx_type: TransactionType) -> ReasoningStrategy:
        """Get default strategy for transaction type"""
        
        # Find default pattern for transaction type
        for pattern in self.reasoning_patterns.values():
            if (pattern.transaction_type == tx_type and 
                pattern.conditions.get('is_default', False)):
                return pattern.strategy
        
        # Ultimate fallback
        return ReasoningStrategy.BALANCED
    
    def _get_strategy_configuration(self, strategy: ReasoningStrategy, 
                                  pattern: ReasoningPattern = None) -> Dict[str, Any]:
        """Get configuration parameters for selected strategy"""
        
        base_config = {
            'strategy': strategy.value,
            'confidence_threshold': 0.7,
            'max_steps': 10,
            'timeout_ms': 5000,
            'evidence_weight': 1.0,
            'pattern_weight': 1.0
        }
        
        # Strategy-specific configurations
        strategy_configs = {
            ReasoningStrategy.CONSERVATIVE: {
                'confidence_threshold': 0.85,
                'evidence_weight': 1.5,
                'false_positive_tolerance': 0.05,
                'require_multiple_evidence': True
            },
            ReasoningStrategy.AGGRESSIVE: {
                'confidence_threshold': 0.6,
                'evidence_weight': 1.2,
                'false_positive_tolerance': 0.15,
                'early_detection': True
            },
            ReasoningStrategy.VELOCITY_FOCUSED: {
                'velocity_window_hours': 24,
                'velocity_threshold': 5,
                'pattern_weight': 1.5,
                'time_series_analysis': True
            },
            ReasoningStrategy.AMOUNT_FOCUSED: {
                'amount_deviation_threshold': 2.0,
                'amount_history_days': 30,
                'statistical_analysis': True
            },
            ReasoningStrategy.LOCATION_FOCUSED: {
                'location_radius_km': 50,
                'travel_time_analysis': True,
                'geographic_risk_scoring': True
            },
            ReasoningStrategy.BEHAVIORAL: {
                'behavior_window_days': 90,
                'pattern_deviation_threshold': 1.5,
                'user_profiling': True
            }
        }
        
        # Apply strategy-specific config
        if strategy in strategy_configs:
            base_config.update(strategy_configs[strategy])
        
        # Apply pattern-specific overrides
        if pattern:
            base_config['confidence_threshold'] = pattern.confidence_threshold
            base_config['pattern_id'] = pattern.pattern_id
            base_config['expected_effectiveness'] = pattern.effectiveness_score
        
        return base_config
    
    def _record_strategy_selection(self, tx_type: TransactionType, 
                                 strategy: ReasoningStrategy,
                                 transaction_data: Dict[str, Any]):
        """Record strategy selection for learning"""
        
        selection_record = {
            'timestamp': datetime.now().isoformat(),
            'transaction_type': tx_type.value,
            'strategy': strategy.value,
            'transaction_amount': transaction_data.get('amount', 0),
            'merchant_category': transaction_data.get('merchant_category', 'unknown')
        }
        
        self.adaptation_history.append(selection_record)
    
    def adapt_reasoning_strategy(self, reasoning_result: Dict[str, Any], 
                               feedback: LearningFeedback) -> Dict[str, Any]:
        """Adapt reasoning strategy based on feedback"""
        
        logger.info(f"Adapting reasoning strategy based on feedback for {feedback.transaction_id}")
        
        # Record feedback
        self.learning_feedback.append(feedback)
        
        # Update strategy performance
        self._update_strategy_performance(feedback)
        
        # Learn new patterns if applicable
        if self.learning_mode in [LearningMode.UNSUPERVISED, LearningMode.HYBRID_LEARNING]:
            self._learn_from_patterns(reasoning_result, feedback)
        
        # Update existing patterns
        self._update_reasoning_patterns(feedback)
        
        # Generate adaptation recommendations
        adaptations = self._generate_adaptations(feedback)
        
        return {
            'adaptations_applied': len(adaptations),
            'strategy_updated': feedback.strategy_used.value,
            'learning_mode': self.learning_mode.value,
            'feedback_processed': feedback.feedback_id,
            'recommendations': adaptations
        }
    
    def _update_strategy_performance(self, feedback: LearningFeedback):
        """Update performance metrics for strategies"""
        
        strategy = feedback.strategy_used
        tx_type = feedback.transaction_type
        
        # Update overall performance
        if feedback.confidence_was_correct:
            self.strategy_performance[strategy]['correct_predictions'] += 1
        else:
            self.strategy_performance[strategy]['incorrect_predictions'] += 1
        
        # Update fraud detection performance
        if feedback.actual_outcome == 'fraud':
            if feedback.original_decision in ['BLOCK', 'FLAG']:
                self.strategy_performance[strategy]['true_positives'] += 1
            else:
                self.strategy_performance[strategy]['false_negatives'] += 1
        elif feedback.actual_outcome == 'legitimate':
            if feedback.original_decision == 'APPROVE':
                self.strategy_performance[strategy]['true_negatives'] += 1
            else:
                self.strategy_performance[strategy]['false_positives'] += 1
        
        # Calculate performance metrics
        tp = self.strategy_performance[strategy]['true_positives']
        tn = self.strategy_performance[strategy]['true_negatives']
        fp = self.strategy_performance[strategy]['false_positives']
        fn = self.strategy_performance[strategy]['false_negatives']
        
        if tp + fp > 0:
            precision = tp / (tp + fp)
            self.strategy_performance[strategy]['precision'] = precision
        
        if tp + fn > 0:
            recall = tp / (tp + fn)
            self.strategy_performance[strategy]['recall'] = recall
        
        if tp + tn + fp + fn > 0:
            accuracy = (tp + tn) / (tp + tn + fp + fn)
            self.strategy_performance[strategy]['accuracy'] = accuracy
    
    def _learn_from_patterns(self, reasoning_result: Dict[str, Any], 
                           feedback: LearningFeedback):
        """Learn new patterns from reasoning results and feedback"""
        
        # Extract pattern features
        transaction_features = self._extract_transaction_features(reasoning_result)
        
        # Check if this represents a new pattern
        pattern_signature = self._generate_pattern_signature(transaction_features)
        
        if pattern_signature not in [p.pattern_id for p in self.reasoning_patterns.values()]:
            # Create new pattern
            new_pattern = self._create_pattern_from_feedback(
                transaction_features, feedback, pattern_signature
            )
            
            if new_pattern:
                self.reasoning_patterns[new_pattern.pattern_id] = new_pattern
                logger.info(f"Learned new reasoning pattern: {new_pattern.pattern_id}")
    
    def _extract_transaction_features(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from transaction for pattern learning"""
        
        features = {}
        
        # Extract from reasoning steps
        steps = reasoning_result.get('steps', [])
        for step in steps:
            step_output = step.get('output', {})
            
            # Amount features
            if 'amount_analysis' in step_output:
                features['amount_category'] = step_output['amount_analysis'].get('category', 'normal')
            
            # Location features
            if 'location_analysis' in step_output:
                features['location_risk'] = step_output['location_analysis'].get('risk_level', 'medium')
            
            # Velocity features
            if 'velocity_analysis' in step_output:
                features['velocity_pattern'] = step_output['velocity_analysis'].get('pattern', 'normal')
            
            # Merchant features
            if 'merchant_analysis' in step_output:
                features['merchant_risk'] = step_output['merchant_analysis'].get('risk_level', 'medium')
        
        # Extract from final decision
        final_decision = reasoning_result.get('final_decision', {})
        features['risk_level'] = final_decision.get('risk_level', 'medium')
        features['confidence_level'] = final_decision.get('confidence', 0.5)
        
        return features
    
    def _generate_pattern_signature(self, features: Dict[str, Any]) -> str:
        """Generate unique signature for pattern"""
        
        # Create signature from key features
        signature_data = {
            'amount_category': features.get('amount_category', 'normal'),
            'location_risk': features.get('location_risk', 'medium'),
            'velocity_pattern': features.get('velocity_pattern', 'normal'),
            'merchant_risk': features.get('merchant_risk', 'medium')
        }
        
        signature_string = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_string.encode()).hexdigest()[:12]
    
    def _create_pattern_from_feedback(self, features: Dict[str, Any], 
                                    feedback: LearningFeedback,
                                    pattern_signature: str) -> Optional[ReasoningPattern]:
        """Create new reasoning pattern from feedback"""
        
        # Determine if pattern is worth creating
        if not self._is_pattern_worth_creating(features, feedback):
            return None
        
        # Create pattern conditions
        conditions = {}
        
        if features.get('amount_category') != 'normal':
            conditions['amount_category'] = features['amount_category']
        
        if features.get('location_risk') != 'medium':
            conditions['location_risk'] = features['location_risk']
        
        if features.get('velocity_pattern') != 'normal':
            conditions['velocity_pattern'] = features['velocity_pattern']
        
        if features.get('merchant_risk') != 'medium':
            conditions['merchant_risk'] = features['merchant_risk']
        
        # Determine initial success rate
        initial_success_rate = 0.6 if feedback.confidence_was_correct else 0.4
        
        # Create pattern
        pattern = ReasoningPattern(
            pattern_id=f"learned_{pattern_signature}",
            transaction_type=feedback.transaction_type,
            strategy=feedback.strategy_used,
            conditions=conditions,
            success_rate=initial_success_rate,
            confidence_threshold=features.get('confidence_level', 0.7),
            usage_count=1,
            last_updated=datetime.now().isoformat(),
            effectiveness_score=initial_success_rate,
            false_positive_rate=0.1,
            false_negative_rate=0.1
        )
        
        return pattern
    
    def _is_pattern_worth_creating(self, features: Dict[str, Any], 
                                 feedback: LearningFeedback) -> bool:
        """Determine if pattern is worth creating"""
        
        # Don't create patterns for normal/standard cases
        if (features.get('amount_category') == 'normal' and
            features.get('location_risk') == 'medium' and
            features.get('velocity_pattern') == 'normal' and
            features.get('merchant_risk') == 'medium'):
            return False
        
        # Create patterns for cases with clear signals
        if (features.get('location_risk') in ['high', 'low'] or
            features.get('amount_category') in ['high', 'low'] or
            features.get('velocity_pattern') in ['high', 'suspicious']):
            return True
        
        return False
    
    def _update_reasoning_patterns(self, feedback: LearningFeedback):
        """Update existing reasoning patterns based on feedback"""
        
        # Find patterns that might have been used
        for pattern in self.reasoning_patterns.values():
            if (pattern.transaction_type == feedback.transaction_type and
                pattern.strategy == feedback.strategy_used):
                
                # Update usage count
                pattern.usage_count += 1
                
                # Update success rate
                if feedback.confidence_was_correct:
                    pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1) + 1.0) / pattern.usage_count
                else:
                    pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1) + 0.0) / pattern.usage_count
                
                # Update effectiveness score
                pattern.effectiveness_score = pattern.success_rate
                
                # Update false positive/negative rates
                if feedback.actual_outcome == 'fraud' and feedback.original_decision == 'APPROVE':
                    pattern.false_negative_rate = min(1.0, pattern.false_negative_rate + 0.01)
                elif feedback.actual_outcome == 'legitimate' and feedback.original_decision in ['BLOCK', 'FLAG']:
                    pattern.false_positive_rate = min(1.0, pattern.false_positive_rate + 0.01)
                
                pattern.last_updated = datetime.now().isoformat()
    
    def _generate_adaptations(self, feedback: LearningFeedback) -> List[Dict[str, Any]]:
        """Generate adaptation recommendations"""
        
        adaptations = []
        
        # Strategy adaptation recommendations
        if not feedback.confidence_was_correct:
            if feedback.actual_outcome == 'fraud' and feedback.original_decision == 'APPROVE':
                # Missed fraud - recommend more conservative strategy
                adaptations.append({
                    'type': 'strategy_adjustment',
                    'recommendation': 'increase_sensitivity',
                    'target_strategy': ReasoningStrategy.CONSERVATIVE.value,
                    'reason': 'Missed fraud detection'
                })
            elif feedback.actual_outcome == 'legitimate' and feedback.original_decision in ['BLOCK', 'FLAG']:
                # False positive - recommend less aggressive strategy
                adaptations.append({
                    'type': 'strategy_adjustment',
                    'recommendation': 'decrease_sensitivity',
                    'target_strategy': ReasoningStrategy.BALANCED.value,
                    'reason': 'False positive reduction'
                })
        
        # Threshold adaptation recommendations
        current_performance = self.strategy_performance[feedback.strategy_used]
        if current_performance.get('false_positive_rate', 0) > 0.1:
            adaptations.append({
                'type': 'threshold_adjustment',
                'recommendation': 'increase_confidence_threshold',
                'current_threshold': 0.7,
                'suggested_threshold': 0.8,
                'reason': 'High false positive rate'
            })
        
        return adaptations
    
    def get_adaptation_statistics(self) -> Dict[str, Any]:
        """Get statistics about adaptive reasoning performance"""
        
        stats = {
            'total_patterns': len(self.reasoning_patterns),
            'total_feedback_items': len(self.learning_feedback),
            'learning_mode': self.learning_mode.value,
            'adaptation_history_size': len(self.adaptation_history)
        }
        
        # Pattern statistics
        pattern_by_type = defaultdict(int)
        pattern_by_strategy = defaultdict(int)
        
        for pattern in self.reasoning_patterns.values():
            pattern_by_type[pattern.transaction_type.value] += 1
            pattern_by_strategy[pattern.strategy.value] += 1
        
        stats['patterns_by_transaction_type'] = dict(pattern_by_type)
        stats['patterns_by_strategy'] = dict(pattern_by_strategy)
        
        # Strategy performance statistics
        strategy_stats = {}
        for strategy, performance in self.strategy_performance.items():
            if performance:
                strategy_stats[strategy.value] = {
                    'accuracy': performance.get('accuracy', 0.0),
                    'precision': performance.get('precision', 0.0),
                    'recall': performance.get('recall', 0.0),
                    'total_predictions': (
                        performance.get('true_positives', 0) +
                        performance.get('true_negatives', 0) +
                        performance.get('false_positives', 0) +
                        performance.get('false_negatives', 0)
                    )
                }
        
        stats['strategy_performance'] = strategy_stats
        
        # Recent adaptation trends
        if self.adaptation_history:
            recent_adaptations = list(self.adaptation_history)[-100:]  # Last 100
            strategy_usage = defaultdict(int)
            
            for adaptation in recent_adaptations:
                strategy_usage[adaptation['strategy']] += 1
            
            stats['recent_strategy_usage'] = dict(strategy_usage)
        
        return stats
    
    def export_learned_patterns(self, filepath: str):
        """Export learned patterns to file"""
        
        # Convert patterns to serializable format
        serializable_patterns = {}
        for pid, pattern in self.reasoning_patterns.items():
            pattern_dict = asdict(pattern)
            pattern_dict['transaction_type'] = pattern.transaction_type.value
            pattern_dict['strategy'] = pattern.strategy.value
            serializable_patterns[pid] = pattern_dict
        
        # Convert adaptation rules to serializable format
        serializable_rules = {}
        for rid, rule in self.adaptation_rules.items():
            rule_dict = asdict(rule)
            rule_dict['target_strategy'] = rule.target_strategy.value
            serializable_rules[rid] = rule_dict
        
        export_data = {
            'patterns': serializable_patterns,
            'adaptation_rules': serializable_rules,
            'strategy_performance': {
                strategy.value: dict(performance) 
                for strategy, performance in self.strategy_performance.items()
            },
            'export_timestamp': datetime.now().isoformat(),
            'learning_mode': self.learning_mode.value
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {len(self.reasoning_patterns)} patterns to {filepath}")
    
    def import_learned_patterns(self, filepath: str):
        """Import learned patterns from file"""
        
        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)
            
            # Import patterns
            for pid, pattern_data in import_data.get('patterns', {}).items():
                pattern_data['transaction_type'] = TransactionType(pattern_data['transaction_type'])
                pattern_data['strategy'] = ReasoningStrategy(pattern_data['strategy'])
                self.reasoning_patterns[pid] = ReasoningPattern(**pattern_data)
            
            # Import adaptation rules
            for rid, rule_data in import_data.get('adaptation_rules', {}).items():
                rule_data['target_strategy'] = ReasoningStrategy(rule_data['target_strategy'])
                self.adaptation_rules[rid] = AdaptationRule(**rule_data)
            
            # Import strategy performance
            for strategy_name, performance in import_data.get('strategy_performance', {}).items():
                strategy = ReasoningStrategy(strategy_name)
                self.strategy_performance[strategy] = defaultdict(float, performance)
            
            logger.info(f"Imported {len(self.reasoning_patterns)} patterns from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to import patterns: {str(e)}")
            raise


class TransactionTypeClassifier:
    """Classifies transactions into types for adaptive reasoning"""
    
    def __init__(self):
        """Initialize transaction type classifier"""
        self.classification_rules = self._load_classification_rules()
    
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load rules for transaction type classification"""
        return {
            'amount_thresholds': {
                'high_value': 10000,
                'medium_value': 1000,
                'low_value': 100
            },
            'merchant_categories': {
                'online': ['ecommerce', 'online_retail', 'digital_goods'],
                'financial': ['bank', 'atm', 'wire_transfer', 'money_transfer'],
                'travel': ['airline', 'hotel', 'car_rental', 'travel_agency'],
                'entertainment': ['restaurant', 'entertainment', 'gaming']
            },
            'location_indicators': {
                'international': ['foreign_country', 'international'],
                'high_risk': ['high_risk_country', 'sanctioned_region'],
                'domestic': ['domestic', 'local']
            }
        }
    
    def classify(self, transaction_data: Dict[str, Any]) -> TransactionType:
        """Classify transaction type"""
        
        amount = transaction_data.get('amount', 0)
        merchant_category = transaction_data.get('merchant_category', '').lower()
        location_type = transaction_data.get('location_type', '').lower()
        payment_method = transaction_data.get('payment_method', '').lower()
        
        # High value transactions
        if amount >= self.classification_rules['amount_thresholds']['high_value']:
            return TransactionType.HIGH_VALUE
        
        # International transactions
        if any(indicator in location_type for indicator in self.classification_rules['location_indicators']['international']):
            return TransactionType.INTERNATIONAL
        
        # Wire transfers
        if 'wire' in payment_method or 'transfer' in payment_method:
            return TransactionType.WIRE_TRANSFER
        
        # ATM withdrawals
        if 'atm' in payment_method or 'withdrawal' in merchant_category:
            return TransactionType.ATM_WITHDRAWAL
        
        # Online purchases
        if any(cat in merchant_category for cat in self.classification_rules['merchant_categories']['online']):
            return TransactionType.ONLINE_PURCHASE
        
        # Mobile payments
        if 'mobile' in payment_method or 'app' in payment_method:
            return TransactionType.MOBILE_PAYMENT
        
        # Peer-to-peer
        if 'p2p' in payment_method or 'peer' in payment_method:
            return TransactionType.PEER_TO_PEER
        
        # Card payments (default for many transactions)
        if 'card' in payment_method:
            return TransactionType.CARD_PAYMENT
        
        # Recurring transactions
        if transaction_data.get('is_recurring', False):
            return TransactionType.RECURRING
        
        return TransactionType.UNKNOWN


class ReasoningStrategySelector:
    """Selects optimal reasoning strategies"""
    
    def __init__(self):
        """Initialize strategy selector"""
        self.strategy_weights = self._initialize_strategy_weights()
    
    def _initialize_strategy_weights(self) -> Dict[ReasoningStrategy, float]:
        """Initialize weights for different strategies"""
        return {
            ReasoningStrategy.CONSERVATIVE: 1.0,
            ReasoningStrategy.BALANCED: 1.0,
            ReasoningStrategy.AGGRESSIVE: 1.0,
            ReasoningStrategy.VELOCITY_FOCUSED: 1.0,
            ReasoningStrategy.AMOUNT_FOCUSED: 1.0,
            ReasoningStrategy.LOCATION_FOCUSED: 1.0,
            ReasoningStrategy.BEHAVIORAL: 1.0,
            ReasoningStrategy.HYBRID: 1.0
        }
    
    def select_strategy(self, transaction_type: TransactionType, 
                       context: Dict[str, Any],
                       performance_history: Dict[ReasoningStrategy, Dict[str, float]]) -> ReasoningStrategy:
        """Select optimal strategy based on context and performance"""
        
        # Calculate strategy scores
        strategy_scores = {}
        
        for strategy in ReasoningStrategy:
            score = self._calculate_strategy_score(
                strategy, transaction_type, context, performance_history
            )
            strategy_scores[strategy] = score
        
        # Select strategy with highest score
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        
        return best_strategy
    
    def _calculate_strategy_score(self, strategy: ReasoningStrategy,
                                transaction_type: TransactionType,
                                context: Dict[str, Any],
                                performance_history: Dict[ReasoningStrategy, Dict[str, float]]) -> float:
        """Calculate score for a strategy"""
        
        base_score = self.strategy_weights[strategy]
        
        # Adjust based on transaction type compatibility
        type_compatibility = self._get_type_compatibility(strategy, transaction_type)
        base_score *= type_compatibility
        
        # Adjust based on historical performance
        if strategy in performance_history:
            performance = performance_history[strategy]
            accuracy = performance.get('accuracy', 0.5)
            base_score *= (0.5 + accuracy)  # Scale by performance
        
        # Adjust based on context
        context_adjustment = self._get_context_adjustment(strategy, context)
        base_score *= context_adjustment
        
        return base_score
    
    def _get_type_compatibility(self, strategy: ReasoningStrategy, 
                              transaction_type: TransactionType) -> float:
        """Get compatibility score between strategy and transaction type"""
        
        compatibility_matrix = {
            (ReasoningStrategy.CONSERVATIVE, TransactionType.HIGH_VALUE): 1.5,
            (ReasoningStrategy.CONSERVATIVE, TransactionType.WIRE_TRANSFER): 1.4,
            (ReasoningStrategy.LOCATION_FOCUSED, TransactionType.INTERNATIONAL): 1.5,
            (ReasoningStrategy.VELOCITY_FOCUSED, TransactionType.ATM_WITHDRAWAL): 1.3,
            (ReasoningStrategy.BEHAVIORAL, TransactionType.RECURRING): 1.4,
            (ReasoningStrategy.AGGRESSIVE, TransactionType.PEER_TO_PEER): 1.3,
            (ReasoningStrategy.BALANCED, TransactionType.CARD_PAYMENT): 1.2,
            (ReasoningStrategy.BALANCED, TransactionType.ONLINE_PURCHASE): 1.2
        }
        
        return compatibility_matrix.get((strategy, transaction_type), 1.0)
    
    def _get_context_adjustment(self, strategy: ReasoningStrategy, 
                              context: Dict[str, Any]) -> float:
        """Get context-based adjustment for strategy"""
        
        adjustment = 1.0
        
        # Risk level adjustments
        risk_level = context.get('risk_level', 'medium')
        if risk_level == 'high':
            if strategy == ReasoningStrategy.CONSERVATIVE:
                adjustment *= 1.3
            elif strategy == ReasoningStrategy.AGGRESSIVE:
                adjustment *= 0.8
        elif risk_level == 'low':
            if strategy == ReasoningStrategy.BALANCED:
                adjustment *= 1.2
        
        # Time pressure adjustments
        if context.get('time_critical', False):
            if strategy in [ReasoningStrategy.BALANCED, ReasoningStrategy.AGGRESSIVE]:
                adjustment *= 1.2
        
        return adjustment


class PatternLearner:
    """Learns patterns from transaction data and outcomes"""
    
    def __init__(self):
        """Initialize pattern learner"""
        self.learned_patterns: Dict[str, Dict[str, Any]] = {}
        self.pattern_confidence: Dict[str, float] = {}
    
    def learn_pattern(self, transaction_features: Dict[str, Any], 
                     outcome: str, confidence: float):
        """Learn a pattern from transaction features and outcome"""
        
        pattern_key = self._generate_pattern_key(transaction_features)
        
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = {
                'features': transaction_features,
                'outcomes': defaultdict(int),
                'total_count': 0
            }
        
        # Update pattern
        self.learned_patterns[pattern_key]['outcomes'][outcome] += 1
        self.learned_patterns[pattern_key]['total_count'] += 1
        
        # Update confidence
        pattern_data = self.learned_patterns[pattern_key]
        most_common_outcome = max(pattern_data['outcomes'], key=pattern_data['outcomes'].get)
        outcome_count = pattern_data['outcomes'][most_common_outcome]
        total_count = pattern_data['total_count']
        
        self.pattern_confidence[pattern_key] = outcome_count / total_count
    
    def _generate_pattern_key(self, features: Dict[str, Any]) -> str:
        """Generate unique key for pattern"""
        
        # Use key features to create pattern signature
        key_features = {
            'amount_category': features.get('amount_category', 'normal'),
            'location_risk': features.get('location_risk', 'medium'),
            'merchant_category': features.get('merchant_category', 'unknown'),
            'time_of_day': features.get('time_of_day', 'normal')
        }
        
        key_string = json.dumps(key_features, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()[:10]
    
    def get_pattern_prediction(self, transaction_features: Dict[str, Any]) -> Tuple[str, float]:
        """Get prediction for transaction based on learned patterns"""
        
        pattern_key = self._generate_pattern_key(transaction_features)
        
        if pattern_key in self.learned_patterns:
            pattern_data = self.learned_patterns[pattern_key]
            most_common_outcome = max(pattern_data['outcomes'], key=pattern_data['outcomes'].get)
            confidence = self.pattern_confidence[pattern_key]
            
            return most_common_outcome, confidence
        
        return 'unknown', 0.5