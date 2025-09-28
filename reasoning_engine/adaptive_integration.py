#!/usr/bin/env python3
"""
Adaptive Integration Layer
Integrates adaptive reasoning capabilities with the existing chain-of-thought system
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Import existing components
from chain_of_thought import ChainOfThoughtReasoner
from adaptive_reasoning import (
    AdaptiveReasoningEngine, 
    TransactionType, 
    ReasoningStrategy,
    LearningFeedback,
    LearningMode
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveChainOfThoughtReasoner:
    """
    Enhanced Chain-of-Thought Reasoner with adaptive capabilities
    """
    
    def __init__(self, learning_mode: LearningMode = LearningMode.HYBRID_LEARNING):
        """Initialize adaptive chain-of-thought reasoner"""
        
        # Initialize core components
        self.base_reasoner = ChainOfThoughtReasoner()
        self.adaptive_engine = AdaptiveReasoningEngine(learning_mode)
        
        # Integration settings
        self.adaptation_enabled = True
        self.learning_enabled = True
        self.strategy_override = None
        
        # Performance tracking
        self.reasoning_sessions: List[Dict[str, Any]] = []
        self.adaptation_metrics = {
            'total_adaptations': 0,
            'successful_adaptations': 0,
            'strategy_changes': 0,
            'patterns_learned': 0
        }
        
        logger.info("AdaptiveChainOfThoughtReasoner initialized")
    
    def reason_about_transaction(self, transaction_data: Dict[str, Any], 
                               context: Dict[str, Any] = None,
                               user_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform adaptive reasoning about a transaction
        """
        
        reasoning_id = f"adaptive_reasoning_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        logger.info(f"Starting adaptive reasoning for transaction: {transaction_data.get('transaction_id', 'unknown')}")
        
        try:
            # Step 1: Classify transaction type
            tx_type = self.adaptive_engine.classify_transaction_type(transaction_data)
            
            # Step 2: Select optimal reasoning strategy
            strategy, strategy_config = self.adaptive_engine.select_reasoning_strategy(
                transaction_data, context
            )
            
            # Step 3: Configure base reasoner with adaptive strategy
            self._configure_base_reasoner(strategy, strategy_config)
            
            # Step 4: Perform reasoning with adaptive configuration
            reasoning_result = self.base_reasoner.reason_about_transaction(
                transaction_data, context, user_history
            )
            
            # Step 5: Enhance result with adaptive information
            enhanced_result = self._enhance_reasoning_result(
                reasoning_result, tx_type, strategy, strategy_config, reasoning_id
            )
            
            # Step 6: Record reasoning session
            self._record_reasoning_session(
                enhanced_result, tx_type, strategy, start_time
            )
            
            logger.info(f"Completed adaptive reasoning with {strategy.value} strategy")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Adaptive reasoning failed: {str(e)}")
            
            # Fallback to base reasoning
            fallback_result = self.base_reasoner.reason_about_transaction(
                transaction_data, context, user_history
            )
            
            fallback_result['adaptive_reasoning'] = {
                'status': 'fallback',
                'error': str(e),
                'strategy_used': 'balanced_fallback'
            }
            
            return fallback_result
    
    def _configure_base_reasoner(self, strategy: ReasoningStrategy, 
                               strategy_config: Dict[str, Any]):
        """Configure base reasoner with adaptive strategy"""
        
        # Apply strategy-specific configurations
        if strategy == ReasoningStrategy.CONSERVATIVE:
            self.base_reasoner.confidence_threshold = strategy_config.get('confidence_threshold', 0.85)
            self.base_reasoner.require_multiple_evidence = strategy_config.get('require_multiple_evidence', True)
            self.base_reasoner.evidence_weight_multiplier = strategy_config.get('evidence_weight', 1.5)
            
        elif strategy == ReasoningStrategy.AGGRESSIVE:
            self.base_reasoner.confidence_threshold = strategy_config.get('confidence_threshold', 0.6)
            self.base_reasoner.early_detection_enabled = strategy_config.get('early_detection', True)
            self.base_reasoner.evidence_weight_multiplier = strategy_config.get('evidence_weight', 1.2)
            
        elif strategy == ReasoningStrategy.VELOCITY_FOCUSED:
            self.base_reasoner.velocity_analysis_enabled = True
            self.base_reasoner.velocity_window_hours = strategy_config.get('velocity_window_hours', 24)
            self.base_reasoner.velocity_threshold = strategy_config.get('velocity_threshold', 5)
            
        elif strategy == ReasoningStrategy.AMOUNT_FOCUSED:
            self.base_reasoner.amount_analysis_enhanced = True
            self.base_reasoner.amount_deviation_threshold = strategy_config.get('amount_deviation_threshold', 2.0)
            self.base_reasoner.statistical_analysis_enabled = strategy_config.get('statistical_analysis', True)
            
        elif strategy == ReasoningStrategy.LOCATION_FOCUSED:
            self.base_reasoner.location_analysis_enhanced = True
            self.base_reasoner.location_radius_km = strategy_config.get('location_radius_km', 50)
            self.base_reasoner.geographic_risk_scoring = strategy_config.get('geographic_risk_scoring', True)
            
        elif strategy == ReasoningStrategy.BEHAVIORAL:
            self.base_reasoner.behavioral_analysis_enabled = True
            self.base_reasoner.behavior_window_days = strategy_config.get('behavior_window_days', 90)
            self.base_reasoner.user_profiling_enabled = strategy_config.get('user_profiling', True)
            
        else:  # BALANCED or HYBRID
            self.base_reasoner.reset_to_defaults()
        
        # Apply common configurations
        self.base_reasoner.max_reasoning_steps = strategy_config.get('max_steps', 10)
        self.base_reasoner.reasoning_timeout_ms = strategy_config.get('timeout_ms', 5000)
    
    def _enhance_reasoning_result(self, reasoning_result: Dict[str, Any],
                                tx_type: TransactionType,
                                strategy: ReasoningStrategy,
                                strategy_config: Dict[str, Any],
                                reasoning_id: str) -> Dict[str, Any]:
        """Enhance reasoning result with adaptive information"""
        
        # Add adaptive reasoning metadata
        reasoning_result['adaptive_reasoning'] = {
            'reasoning_id': reasoning_id,
            'transaction_type': tx_type.value,
            'strategy_used': strategy.value,
            'strategy_config': strategy_config,
            'adaptation_enabled': self.adaptation_enabled,
            'learning_enabled': self.learning_enabled,
            'expected_effectiveness': strategy_config.get('expected_effectiveness', 0.75)
        }
        
        # Add strategy-specific insights
        strategy_insights = self._generate_strategy_insights(
            reasoning_result, strategy, tx_type
        )
        reasoning_result['adaptive_reasoning']['strategy_insights'] = strategy_insights
        
        # Add confidence adjustments based on strategy
        original_confidence = reasoning_result.get('overall_confidence', 0.5)
        adjusted_confidence = self._adjust_confidence_for_strategy(
            original_confidence, strategy, strategy_config
        )
        reasoning_result['adaptive_confidence'] = adjusted_confidence
        
        return reasoning_result
    
    def _generate_strategy_insights(self, reasoning_result: Dict[str, Any],
                                  strategy: ReasoningStrategy,
                                  tx_type: TransactionType) -> Dict[str, Any]:
        """Generate insights about the strategy used"""
        
        insights = {
            'strategy_rationale': self._get_strategy_rationale(strategy, tx_type),
            'key_focus_areas': self._get_strategy_focus_areas(strategy),
            'expected_strengths': self._get_strategy_strengths(strategy),
            'potential_limitations': self._get_strategy_limitations(strategy)
        }
        
        # Add performance expectations
        strategy_performance = self.adaptive_engine.strategy_performance.get(strategy, {})
        if strategy_performance:
            insights['historical_performance'] = {
                'accuracy': strategy_performance.get('accuracy', 0.0),
                'precision': strategy_performance.get('precision', 0.0),
                'recall': strategy_performance.get('recall', 0.0)
            }
        
        return insights
    
    def _get_strategy_rationale(self, strategy: ReasoningStrategy, 
                              tx_type: TransactionType) -> str:
        """Get rationale for strategy selection"""
        
        rationales = {
            ReasoningStrategy.CONSERVATIVE: f"Conservative approach selected for {tx_type.value} to minimize false positives and ensure thorough analysis",
            ReasoningStrategy.AGGRESSIVE: f"Aggressive detection strategy chosen for {tx_type.value} to maximize fraud detection sensitivity",
            ReasoningStrategy.VELOCITY_FOCUSED: f"Velocity-focused analysis selected for {tx_type.value} to detect transaction pattern anomalies",
            ReasoningStrategy.AMOUNT_FOCUSED: f"Amount-focused strategy chosen for {tx_type.value} to analyze spending pattern deviations",
            ReasoningStrategy.LOCATION_FOCUSED: f"Location-focused approach selected for {tx_type.value} to assess geographic risk factors",
            ReasoningStrategy.BEHAVIORAL: f"Behavioral analysis strategy chosen for {tx_type.value} to evaluate user pattern consistency",
            ReasoningStrategy.BALANCED: f"Balanced approach selected for {tx_type.value} providing comprehensive analysis across all factors",
            ReasoningStrategy.HYBRID: f"Hybrid strategy chosen for {tx_type.value} combining multiple analytical approaches"
        }
        
        return rationales.get(strategy, "Standard reasoning approach applied")
    
    def _get_strategy_focus_areas(self, strategy: ReasoningStrategy) -> List[str]:
        """Get key focus areas for strategy"""
        
        focus_areas = {
            ReasoningStrategy.CONSERVATIVE: ["Evidence validation", "Multiple confirmation", "Risk minimization"],
            ReasoningStrategy.AGGRESSIVE: ["Early detection", "Pattern sensitivity", "Anomaly identification"],
            ReasoningStrategy.VELOCITY_FOCUSED: ["Transaction frequency", "Time patterns", "Velocity analysis"],
            ReasoningStrategy.AMOUNT_FOCUSED: ["Amount analysis", "Spending patterns", "Statistical deviation"],
            ReasoningStrategy.LOCATION_FOCUSED: ["Geographic analysis", "Location patterns", "Travel analysis"],
            ReasoningStrategy.BEHAVIORAL: ["User behavior", "Pattern consistency", "Behavioral profiling"],
            ReasoningStrategy.BALANCED: ["Comprehensive analysis", "Multi-factor assessment", "Balanced evaluation"],
            ReasoningStrategy.HYBRID: ["Combined approaches", "Multi-strategy analysis", "Adaptive focus"]
        }
        
        return focus_areas.get(strategy, ["General analysis"])
    
    def _get_strategy_strengths(self, strategy: ReasoningStrategy) -> List[str]:
        """Get expected strengths of strategy"""
        
        strengths = {
            ReasoningStrategy.CONSERVATIVE: ["Low false positive rate", "High precision", "Thorough analysis"],
            ReasoningStrategy.AGGRESSIVE: ["High detection rate", "Early fraud identification", "Sensitive to anomalies"],
            ReasoningStrategy.VELOCITY_FOCUSED: ["Excellent pattern detection", "Time-based analysis", "Velocity anomaly detection"],
            ReasoningStrategy.AMOUNT_FOCUSED: ["Amount anomaly detection", "Statistical accuracy", "Spending pattern analysis"],
            ReasoningStrategy.LOCATION_FOCUSED: ["Geographic risk assessment", "Location anomaly detection", "Travel pattern analysis"],
            ReasoningStrategy.BEHAVIORAL: ["User behavior modeling", "Pattern consistency", "Personalized analysis"],
            ReasoningStrategy.BALANCED: ["Well-rounded analysis", "Stable performance", "Comprehensive coverage"],
            ReasoningStrategy.HYBRID: ["Adaptive capabilities", "Multi-dimensional analysis", "Flexible approach"]
        }
        
        return strengths.get(strategy, ["Standard analysis capabilities"])
    
    def _get_strategy_limitations(self, strategy: ReasoningStrategy) -> List[str]:
        """Get potential limitations of strategy"""
        
        limitations = {
            ReasoningStrategy.CONSERVATIVE: ["May miss subtle fraud", "Slower detection", "Higher false negative risk"],
            ReasoningStrategy.AGGRESSIVE: ["Higher false positive rate", "May over-flag", "Less precision"],
            ReasoningStrategy.VELOCITY_FOCUSED: ["Limited to pattern-based fraud", "Requires transaction history", "Time-dependent"],
            ReasoningStrategy.AMOUNT_FOCUSED: ["Limited to amount-based fraud", "Requires spending history", "Statistical dependency"],
            ReasoningStrategy.LOCATION_FOCUSED: ["Limited to location-based fraud", "GPS dependency", "Travel complexity"],
            ReasoningStrategy.BEHAVIORAL: ["Requires user history", "Behavior change adaptation", "Profile dependency"],
            ReasoningStrategy.BALANCED: ["May lack specialization", "Average performance", "No specific strengths"],
            ReasoningStrategy.HYBRID: ["Complexity overhead", "Configuration dependency", "Resource intensive"]
        }
        
        return limitations.get(strategy, ["Standard limitations"])
    
    def _adjust_confidence_for_strategy(self, original_confidence: float,
                                      strategy: ReasoningStrategy,
                                      strategy_config: Dict[str, Any]) -> float:
        """Adjust confidence based on strategy characteristics"""
        
        # Strategy-specific confidence adjustments
        adjustments = {
            ReasoningStrategy.CONSERVATIVE: 0.95,  # Slightly lower confidence due to caution
            ReasoningStrategy.AGGRESSIVE: 1.05,    # Slightly higher confidence due to sensitivity
            ReasoningStrategy.VELOCITY_FOCUSED: 1.0,
            ReasoningStrategy.AMOUNT_FOCUSED: 1.0,
            ReasoningStrategy.LOCATION_FOCUSED: 1.0,
            ReasoningStrategy.BEHAVIORAL: 0.98,    # Slightly lower due to behavior complexity
            ReasoningStrategy.BALANCED: 1.0,
            ReasoningStrategy.HYBRID: 1.02         # Slightly higher due to multiple approaches
        }
        
        adjustment_factor = adjustments.get(strategy, 1.0)
        adjusted_confidence = min(1.0, original_confidence * adjustment_factor)
        
        # Apply pattern-based adjustments if available
        expected_effectiveness = strategy_config.get('expected_effectiveness', 0.75)
        if expected_effectiveness > 0.8:
            adjusted_confidence *= 1.05
        elif expected_effectiveness < 0.6:
            adjusted_confidence *= 0.95
        
        return max(0.0, min(1.0, adjusted_confidence))
    
    def _record_reasoning_session(self, reasoning_result: Dict[str, Any],
                                tx_type: TransactionType,
                                strategy: ReasoningStrategy,
                                start_time: datetime):
        """Record reasoning session for analysis"""
        
        session_record = {
            'session_id': reasoning_result['adaptive_reasoning']['reasoning_id'],
            'transaction_id': reasoning_result.get('transaction_id', 'unknown'),
            'transaction_type': tx_type.value,
            'strategy_used': strategy.value,
            'original_confidence': reasoning_result.get('overall_confidence', 0.5),
            'adaptive_confidence': reasoning_result.get('adaptive_confidence', 0.5),
            'decision': reasoning_result.get('final_decision', {}).get('recommended_action', 'UNKNOWN'),
            'processing_time_ms': reasoning_result.get('total_processing_time_ms', 0),
            'steps_count': len(reasoning_result.get('steps', [])),
            'timestamp': start_time.isoformat(),
            'duration_ms': (datetime.now() - start_time).total_seconds() * 1000
        }
        
        self.reasoning_sessions.append(session_record)
        
        # Keep only recent sessions (last 1000)
        if len(self.reasoning_sessions) > 1000:
            self.reasoning_sessions = self.reasoning_sessions[-1000:]
    
    def provide_feedback(self, reasoning_id: str, actual_outcome: str, 
                        feedback_source: str = 'manual') -> Dict[str, Any]:
        """Provide feedback for learning and adaptation"""
        
        if not self.learning_enabled:
            return {'status': 'learning_disabled'}
        
        # Find the reasoning session
        session = None
        for s in self.reasoning_sessions:
            if s['session_id'] == reasoning_id:
                session = s
                break
        
        if not session:
            return {'status': 'session_not_found', 'reasoning_id': reasoning_id}
        
        # Create feedback object
        feedback = LearningFeedback(
            feedback_id=f"feedback_{int(datetime.now().timestamp())}",
            transaction_id=session['transaction_id'],
            reasoning_id=reasoning_id,
            original_decision=session['decision'],
            actual_outcome=actual_outcome,
            confidence_was_correct=self._evaluate_confidence_accuracy(session, actual_outcome),
            strategy_used=ReasoningStrategy(session['strategy_used']),
            transaction_type=TransactionType(session['transaction_type']),
            feedback_timestamp=datetime.now().isoformat(),
            feedback_source=feedback_source
        )
        
        # Apply feedback to adaptive engine
        adaptation_result = self.adaptive_engine.adapt_reasoning_strategy(
            {'session_data': session}, feedback
        )
        
        # Update metrics
        self.adaptation_metrics['total_adaptations'] += 1
        if adaptation_result.get('adaptations_applied', 0) > 0:
            self.adaptation_metrics['successful_adaptations'] += 1
        
        logger.info(f"Processed feedback for reasoning session {reasoning_id}")
        
        return {
            'status': 'feedback_processed',
            'feedback_id': feedback.feedback_id,
            'adaptations_applied': adaptation_result.get('adaptations_applied', 0),
            'learning_mode': self.adaptive_engine.learning_mode.value
        }
    
    def _evaluate_confidence_accuracy(self, session: Dict[str, Any], 
                                    actual_outcome: str) -> bool:
        """Evaluate if confidence level was appropriate"""
        
        confidence = session['adaptive_confidence']
        decision = session['decision']
        
        # High confidence should correlate with correct decisions
        if confidence > 0.8:
            if actual_outcome == 'fraud' and decision in ['BLOCK', 'FLAG']:
                return True
            elif actual_outcome == 'legitimate' and decision == 'APPROVE':
                return True
            else:
                return False
        
        # Low confidence should correlate with uncertain cases
        elif confidence < 0.6:
            if decision == 'REVIEW':
                return True
            else:
                return False
        
        # Medium confidence - more lenient evaluation
        else:
            return True
    
    def get_adaptive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive adaptive reasoning statistics"""
        
        stats = {
            'adaptation_metrics': self.adaptation_metrics.copy(),
            'reasoning_sessions': len(self.reasoning_sessions),
            'adaptive_engine_stats': self.adaptive_engine.get_adaptation_statistics()
        }
        
        # Session statistics
        if self.reasoning_sessions:
            recent_sessions = self.reasoning_sessions[-100:]  # Last 100 sessions
            
            # Strategy usage
            strategy_usage = {}
            for session in recent_sessions:
                strategy = session['strategy_used']
                strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
            
            stats['recent_strategy_usage'] = strategy_usage
            
            # Transaction type distribution
            tx_type_distribution = {}
            for session in recent_sessions:
                tx_type = session['transaction_type']
                tx_type_distribution[tx_type] = tx_type_distribution.get(tx_type, 0) + 1
            
            stats['transaction_type_distribution'] = tx_type_distribution
            
            # Performance metrics
            avg_confidence = sum(s['adaptive_confidence'] for s in recent_sessions) / len(recent_sessions)
            avg_processing_time = sum(s['processing_time_ms'] for s in recent_sessions) / len(recent_sessions)
            avg_steps = sum(s['steps_count'] for s in recent_sessions) / len(recent_sessions)
            
            stats['performance_metrics'] = {
                'average_confidence': avg_confidence,
                'average_processing_time_ms': avg_processing_time,
                'average_steps_per_session': avg_steps
            }
        
        return stats
    
    def enable_adaptation(self):
        """Enable adaptive reasoning"""
        self.adaptation_enabled = True
        logger.info("Adaptive reasoning enabled")
    
    def disable_adaptation(self):
        """Disable adaptive reasoning"""
        self.adaptation_enabled = False
        logger.info("Adaptive reasoning disabled")
    
    def enable_learning(self):
        """Enable learning from feedback"""
        self.learning_enabled = True
        logger.info("Learning from feedback enabled")
    
    def disable_learning(self):
        """Disable learning from feedback"""
        self.learning_enabled = False
        logger.info("Learning from feedback disabled")
    
    def set_strategy_override(self, strategy: ReasoningStrategy):
        """Override strategy selection with fixed strategy"""
        self.strategy_override = strategy
        logger.info(f"Strategy override set to {strategy.value}")
    
    def clear_strategy_override(self):
        """Clear strategy override"""
        self.strategy_override = None
        logger.info("Strategy override cleared")
    
    def export_adaptive_data(self, filepath: str):
        """Export adaptive reasoning data"""
        
        export_data = {
            'reasoning_sessions': self.reasoning_sessions,
            'adaptation_metrics': self.adaptation_metrics,
            'adaptive_engine_patterns': self.adaptive_engine.reasoning_patterns,
            'export_timestamp': datetime.now().isoformat()
        }
        
        # Convert patterns to serializable format
        serializable_patterns = {}
        for pid, pattern in export_data['adaptive_engine_patterns'].items():
            pattern_dict = {
                'pattern_id': pattern.pattern_id,
                'transaction_type': pattern.transaction_type.value,
                'strategy': pattern.strategy.value,
                'conditions': pattern.conditions,
                'success_rate': pattern.success_rate,
                'confidence_threshold': pattern.confidence_threshold,
                'usage_count': pattern.usage_count,
                'last_updated': pattern.last_updated,
                'effectiveness_score': pattern.effectiveness_score,
                'false_positive_rate': pattern.false_positive_rate,
                'false_negative_rate': pattern.false_negative_rate
            }
            serializable_patterns[pid] = pattern_dict
        
        export_data['adaptive_engine_patterns'] = serializable_patterns
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported adaptive reasoning data to {filepath}")
    
    def import_adaptive_data(self, filepath: str):
        """Import adaptive reasoning data"""
        
        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)
            
            # Import reasoning sessions
            self.reasoning_sessions = import_data.get('reasoning_sessions', [])
            
            # Import adaptation metrics
            self.adaptation_metrics.update(import_data.get('adaptation_metrics', {}))
            
            # Import patterns to adaptive engine (patterns are already in dict format)
            patterns_data = import_data.get('adaptive_engine_patterns', {})
            if patterns_data:
                # Convert back to pattern objects
                for pid, pattern_data in patterns_data.items():
                    from adaptive_reasoning import ReasoningPattern, TransactionType, ReasoningStrategy
                    pattern_data['transaction_type'] = TransactionType(pattern_data['transaction_type'])
                    pattern_data['strategy'] = ReasoningStrategy(pattern_data['strategy'])
                    self.adaptive_engine.reasoning_patterns[pid] = ReasoningPattern(**pattern_data)
            
            logger.info(f"Imported adaptive reasoning data from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to import adaptive data: {str(e)}")
            raise