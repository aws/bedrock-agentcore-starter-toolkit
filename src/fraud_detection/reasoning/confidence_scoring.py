#!/usr/bin/env python3
"""
Confidence Scoring System
Advanced confidence assessment for reasoning steps and decisions
"""

import math
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfidenceFactorType(Enum):
    """Types of factors that influence confidence"""
    DATA_QUALITY = "data_quality"
    EVIDENCE_STRENGTH = "evidence_strength"
    MODEL_CERTAINTY = "model_certainty"
    HISTORICAL_ACCURACY = "historical_accuracy"
    CONSENSUS_AGREEMENT = "consensus_agreement"
    COMPLEXITY_PENALTY = "complexity_penalty"
    TIME_PRESSURE = "time_pressure"
    EXTERNAL_VALIDATION = "external_validation"

@dataclass
class ConfidenceFactor:
    """Individual factor contributing to confidence score"""
    factor_type: ConfidenceFactorType
    value: float  # 0.0 to 1.0
    weight: float  # Importance weight
    description: str
    evidence: List[str]

@dataclass
class ConfidenceAssessment:
    """Complete confidence assessment"""
    overall_confidence: float
    factors: List[ConfidenceFactor]
    confidence_level: str  # VERY_LOW, LOW, MEDIUM, HIGH, VERY_HIGH
    reliability_score: float
    uncertainty_sources: List[str]
    confidence_explanation: str
    timestamp: str

class ConfidenceScorer:
    """
    Calculates confidence scores for reasoning steps and decisions
    """
    
    def __init__(self):
        """Initialize confidence scorer"""
        self.historical_accuracy = {}  # Track accuracy by decision type
        self.confidence_calibration = {}  # Calibration data
        
        # Default factor weights
        self.default_weights = {
            ConfidenceFactorType.DATA_QUALITY: 0.20,
            ConfidenceFactorType.EVIDENCE_STRENGTH: 0.25,
            ConfidenceFactorType.MODEL_CERTAINTY: 0.15,
            ConfidenceFactorType.HISTORICAL_ACCURACY: 0.15,
            ConfidenceFactorType.CONSENSUS_AGREEMENT: 0.10,
            ConfidenceFactorType.COMPLEXITY_PENALTY: 0.05,
            ConfidenceFactorType.TIME_PRESSURE: 0.05,
            ConfidenceFactorType.EXTERNAL_VALIDATION: 0.05
        }
        
        logger.info("ConfidenceScorer initialized")
    
    def assess_confidence(self, reasoning_data: Dict[str, Any], 
                         context: Optional[Dict[str, Any]] = None) -> ConfidenceAssessment:
        """
        Assess confidence for a reasoning step or decision
        """
        logger.debug("Assessing confidence for reasoning data")
        
        if context is None:
            context = {}
        
        # Calculate individual confidence factors
        factors = []
        
        # Data Quality Factor
        data_quality_factor = self._assess_data_quality(reasoning_data)
        factors.append(data_quality_factor)
        
        # Evidence Strength Factor
        evidence_strength_factor = self._assess_evidence_strength(reasoning_data)
        factors.append(evidence_strength_factor)
        
        # Model Certainty Factor
        model_certainty_factor = self._assess_model_certainty(reasoning_data)
        factors.append(model_certainty_factor)
        
        # Historical Accuracy Factor
        historical_accuracy_factor = self._assess_historical_accuracy(reasoning_data, context)
        factors.append(historical_accuracy_factor)
        
        # Consensus Agreement Factor
        consensus_factor = self._assess_consensus_agreement(reasoning_data, context)
        factors.append(consensus_factor)
        
        # Complexity Penalty Factor
        complexity_factor = self._assess_complexity_penalty(reasoning_data)
        factors.append(complexity_factor)
        
        # Time Pressure Factor
        time_pressure_factor = self._assess_time_pressure(context)
        factors.append(time_pressure_factor)
        
        # External Validation Factor
        external_validation_factor = self._assess_external_validation(reasoning_data, context)
        factors.append(external_validation_factor)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_weighted_confidence(factors)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(overall_confidence)
        
        # Calculate reliability score
        reliability_score = self._calculate_reliability_score(factors, overall_confidence)
        
        # Identify uncertainty sources
        uncertainty_sources = self._identify_uncertainty_sources(factors)
        
        # Generate explanation
        confidence_explanation = self._generate_confidence_explanation(factors, overall_confidence)
        
        assessment = ConfidenceAssessment(
            overall_confidence=overall_confidence,
            factors=factors,
            confidence_level=confidence_level,
            reliability_score=reliability_score,
            uncertainty_sources=uncertainty_sources,
            confidence_explanation=confidence_explanation,
            timestamp=datetime.now().isoformat()
        )
        
        logger.debug(f"Confidence assessment completed: {confidence_level} ({overall_confidence:.3f})")
        return assessment
    
    def _assess_data_quality(self, reasoning_data: Dict[str, Any]) -> ConfidenceFactor:
        """Assess the quality of input data"""
        quality_score = 1.0
        evidence = []
        
        # Check for missing data
        required_fields = ['transaction', 'reasoning', 'evidence']
        missing_fields = [field for field in required_fields if field not in reasoning_data or not reasoning_data[field]]
        
        if missing_fields:
            quality_score -= 0.2 * len(missing_fields)
            evidence.append(f"Missing fields: {missing_fields}")
        
        # Check data completeness
        if 'transaction' in reasoning_data:
            transaction = reasoning_data['transaction']
            if isinstance(transaction, dict):
                expected_fields = ['amount', 'currency', 'merchant', 'location', 'user_id']
                present_fields = sum(1 for field in expected_fields if field in transaction and transaction[field])
                completeness = present_fields / len(expected_fields)
                quality_score *= completeness
                evidence.append(f"Transaction data completeness: {completeness:.2f}")
        
        # Check for data consistency
        if 'evidence' in reasoning_data and isinstance(reasoning_data['evidence'], list):
            if len(reasoning_data['evidence']) == 0:
                quality_score *= 0.7
                evidence.append("No evidence provided")
            elif len(reasoning_data['evidence']) > 10:
                quality_score *= 0.9  # Too much evidence might indicate uncertainty
                evidence.append("Very high evidence count")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.DATA_QUALITY,
            value=max(0.0, min(1.0, quality_score)),
            weight=self.default_weights[ConfidenceFactorType.DATA_QUALITY],
            description="Quality and completeness of input data",
            evidence=evidence
        )
    
    def _assess_evidence_strength(self, reasoning_data: Dict[str, Any]) -> ConfidenceFactor:
        """Assess the strength of evidence provided"""
        evidence_score = 0.5  # Default neutral score
        evidence_items = []
        
        if 'evidence' in reasoning_data and isinstance(reasoning_data['evidence'], list):
            evidence_list = reasoning_data['evidence']
            
            # Score based on evidence count (optimal range: 3-7 pieces)
            evidence_count = len(evidence_list)
            if evidence_count == 0:
                evidence_score = 0.1
                evidence_items.append("No evidence provided")
            elif 1 <= evidence_count <= 2:
                evidence_score = 0.4
                evidence_items.append("Limited evidence")
            elif 3 <= evidence_count <= 7:
                evidence_score = 0.9
                evidence_items.append("Good evidence coverage")
            elif 8 <= evidence_count <= 15:
                evidence_score = 0.7
                evidence_items.append("Extensive evidence")
            else:
                evidence_score = 0.5
                evidence_items.append("Excessive evidence count")
            
            # Assess evidence quality
            quality_indicators = 0
            for evidence_item in evidence_list:
                if isinstance(evidence_item, str):
                    # Look for specific, quantitative evidence
                    if any(indicator in evidence_item.lower() for indicator in ['amount', 'time', 'location', 'pattern']):
                        quality_indicators += 1
                    # Look for vague evidence
                    if any(vague in evidence_item.lower() for vague in ['maybe', 'possibly', 'unclear', 'unknown']):
                        quality_indicators -= 0.5
            
            # Adjust score based on evidence quality
            if evidence_count > 0:
                quality_ratio = quality_indicators / evidence_count
                evidence_score *= (0.5 + 0.5 * max(0, min(1, quality_ratio)))
                evidence_items.append(f"Evidence quality ratio: {quality_ratio:.2f}")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.EVIDENCE_STRENGTH,
            value=max(0.0, min(1.0, evidence_score)),
            weight=self.default_weights[ConfidenceFactorType.EVIDENCE_STRENGTH],
            description="Strength and quality of supporting evidence",
            evidence=evidence_items
        )
    
    def _assess_model_certainty(self, reasoning_data: Dict[str, Any]) -> ConfidenceFactor:
        """Assess model's certainty in its reasoning"""
        certainty_score = 0.5
        evidence = []
        
        # Check if model provided explicit confidence
        if 'confidence' in reasoning_data:
            model_confidence = reasoning_data['confidence']
            if isinstance(model_confidence, (int, float)) and 0 <= model_confidence <= 1:
                certainty_score = model_confidence
                evidence.append(f"Model confidence: {model_confidence:.3f}")
            else:
                evidence.append("Invalid model confidence value")
        
        # Analyze reasoning text for certainty indicators
        if 'reasoning' in reasoning_data and isinstance(reasoning_data['reasoning'], str):
            reasoning_text = reasoning_data['reasoning'].lower()
            
            # Positive certainty indicators
            certain_phrases = ['clearly', 'definitely', 'obviously', 'certainly', 'undoubtedly']
            certain_count = sum(1 for phrase in certain_phrases if phrase in reasoning_text)
            
            # Uncertainty indicators
            uncertain_phrases = ['maybe', 'possibly', 'might', 'could', 'uncertain', 'unclear', 'ambiguous']
            uncertain_count = sum(1 for phrase in uncertain_phrases if phrase in reasoning_text)
            
            # Adjust certainty based on language
            if certain_count > uncertain_count:
                certainty_score = min(1.0, certainty_score + 0.1 * (certain_count - uncertain_count))
                evidence.append(f"Certain language indicators: {certain_count}")
            elif uncertain_count > certain_count:
                certainty_score = max(0.0, certainty_score - 0.1 * (uncertain_count - certain_count))
                evidence.append(f"Uncertain language indicators: {uncertain_count}")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.MODEL_CERTAINTY,
            value=max(0.0, min(1.0, certainty_score)),
            weight=self.default_weights[ConfidenceFactorType.MODEL_CERTAINTY],
            description="Model's certainty in its reasoning",
            evidence=evidence
        )
    
    def _assess_historical_accuracy(self, reasoning_data: Dict[str, Any], 
                                  context: Dict[str, Any]) -> ConfidenceFactor:
        """Assess based on historical accuracy of similar decisions"""
        accuracy_score = 0.7  # Default assuming good historical performance
        evidence = []
        
        # Get decision type for historical lookup
        decision_type = context.get('decision_type', 'fraud_detection')
        
        if decision_type in self.historical_accuracy:
            historical_data = self.historical_accuracy[decision_type]
            accuracy_score = historical_data.get('accuracy', 0.7)
            sample_size = historical_data.get('sample_size', 0)
            
            evidence.append(f"Historical accuracy: {accuracy_score:.3f}")
            evidence.append(f"Sample size: {sample_size}")
            
            # Adjust confidence based on sample size
            if sample_size < 10:
                accuracy_score *= 0.8  # Reduce confidence for small samples
                evidence.append("Small historical sample")
            elif sample_size > 100:
                accuracy_score = min(1.0, accuracy_score * 1.1)  # Boost for large samples
                evidence.append("Large historical sample")
        else:
            evidence.append("No historical data available")
            accuracy_score = 0.5  # Neutral when no history
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.HISTORICAL_ACCURACY,
            value=max(0.0, min(1.0, accuracy_score)),
            weight=self.default_weights[ConfidenceFactorType.HISTORICAL_ACCURACY],
            description="Historical accuracy of similar decisions",
            evidence=evidence
        )
    
    def _assess_consensus_agreement(self, reasoning_data: Dict[str, Any], 
                                  context: Dict[str, Any]) -> ConfidenceFactor:
        """Assess agreement between multiple reasoning sources"""
        consensus_score = 0.5  # Default neutral
        evidence = []
        
        # Check for multiple agent opinions
        if 'agent_responses' in context:
            agent_responses = context['agent_responses']
            if isinstance(agent_responses, list) and len(agent_responses) > 1:
                # Calculate agreement on fraud decision
                fraud_decisions = []
                for response in agent_responses:
                    if 'is_fraud' in response:
                        fraud_decisions.append(response['is_fraud'])
                
                if fraud_decisions:
                    agreement_ratio = max(fraud_decisions.count(True), fraud_decisions.count(False)) / len(fraud_decisions)
                    consensus_score = agreement_ratio
                    evidence.append(f"Agent agreement: {agreement_ratio:.3f} ({len(fraud_decisions)} agents)")
                
                # Calculate confidence agreement
                confidences = [r.get('confidence', 0.5) for r in agent_responses if 'confidence' in r]
                if len(confidences) > 1:
                    confidence_std = math.sqrt(sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences))
                    # Lower standard deviation = higher consensus
                    confidence_consensus = max(0, 1 - confidence_std * 2)
                    consensus_score = (consensus_score + confidence_consensus) / 2
                    evidence.append(f"Confidence consensus: {confidence_consensus:.3f}")
        
        # Check for external validation
        if 'external_validation' in context:
            external_validation = context['external_validation']
            if external_validation.get('validated', False):
                consensus_score = min(1.0, consensus_score + 0.2)
                evidence.append("External validation confirmed")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.CONSENSUS_AGREEMENT,
            value=max(0.0, min(1.0, consensus_score)),
            weight=self.default_weights[ConfidenceFactorType.CONSENSUS_AGREEMENT],
            description="Agreement between multiple reasoning sources",
            evidence=evidence
        )
    
    def _assess_complexity_penalty(self, reasoning_data: Dict[str, Any]) -> ConfidenceFactor:
        """Apply penalty for overly complex reasoning"""
        complexity_score = 1.0  # Start with no penalty
        evidence = []
        
        # Count reasoning steps
        if 'steps' in reasoning_data:
            step_count = len(reasoning_data['steps'])
            if step_count > 10:
                complexity_score = max(0.5, 1.0 - (step_count - 10) * 0.05)
                evidence.append(f"High step count penalty: {step_count} steps")
            elif step_count < 3:
                complexity_score = 0.8  # Too simple might miss important factors
                evidence.append(f"Low step count: {step_count} steps")
        
        # Assess reasoning length
        if 'reasoning' in reasoning_data and isinstance(reasoning_data['reasoning'], str):
            reasoning_length = len(reasoning_data['reasoning'])
            if reasoning_length > 5000:  # Very long reasoning
                complexity_score *= 0.9
                evidence.append("Very long reasoning text")
            elif reasoning_length < 100:  # Very short reasoning
                complexity_score *= 0.8
                evidence.append("Very short reasoning text")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.COMPLEXITY_PENALTY,
            value=max(0.0, min(1.0, complexity_score)),
            weight=self.default_weights[ConfidenceFactorType.COMPLEXITY_PENALTY],
            description="Penalty for excessive complexity",
            evidence=evidence
        )
    
    def _assess_time_pressure(self, context: Dict[str, Any]) -> ConfidenceFactor:
        """Assess impact of time pressure on decision quality"""
        time_score = 1.0  # Default no time pressure
        evidence = []
        
        if 'processing_time_ms' in context:
            processing_time = context['processing_time_ms']
            
            # Optimal processing time range: 1000-5000ms
            if processing_time < 500:
                time_score = 0.7  # Too fast, might miss details
                evidence.append(f"Very fast processing: {processing_time}ms")
            elif processing_time > 30000:  # 30 seconds
                time_score = 0.8  # Too slow, might indicate uncertainty
                evidence.append(f"Slow processing: {processing_time}ms")
            else:
                evidence.append(f"Normal processing time: {processing_time}ms")
        
        if 'urgency' in context:
            urgency = context['urgency']
            if urgency == 'high':
                time_score *= 0.9
                evidence.append("High urgency request")
            elif urgency == 'critical':
                time_score *= 0.8
                evidence.append("Critical urgency request")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.TIME_PRESSURE,
            value=max(0.0, min(1.0, time_score)),
            weight=self.default_weights[ConfidenceFactorType.TIME_PRESSURE],
            description="Impact of time pressure on decision quality",
            evidence=evidence
        )
    
    def _assess_external_validation(self, reasoning_data: Dict[str, Any], 
                                  context: Dict[str, Any]) -> ConfidenceFactor:
        """Assess external validation of the decision"""
        validation_score = 0.5  # Default neutral
        evidence = []
        
        # Check for external data sources
        external_sources = context.get('external_sources', [])
        if external_sources:
            validation_score = min(1.0, 0.5 + 0.1 * len(external_sources))
            evidence.append(f"External sources: {len(external_sources)}")
        
        # Check for database confirmations
        if 'database_matches' in context:
            matches = context['database_matches']
            if matches > 0:
                validation_score = min(1.0, validation_score + 0.2)
                evidence.append(f"Database matches: {matches}")
        
        # Check for API validations
        if 'api_validations' in context:
            validations = context['api_validations']
            successful_validations = sum(1 for v in validations if v.get('success', False))
            if successful_validations > 0:
                validation_score = min(1.0, validation_score + 0.1 * successful_validations)
                evidence.append(f"API validations: {successful_validations}")
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.EXTERNAL_VALIDATION,
            value=max(0.0, min(1.0, validation_score)),
            weight=self.default_weights[ConfidenceFactorType.EXTERNAL_VALIDATION],
            description="External validation of the decision",
            evidence=evidence
        )
    
    def _calculate_weighted_confidence(self, factors: List[ConfidenceFactor]) -> float:
        """Calculate weighted average confidence from all factors"""
        if not factors:
            return 0.5
        
        weighted_sum = sum(factor.value * factor.weight for factor in factors)
        total_weight = sum(factor.weight for factor in factors)
        
        if total_weight == 0:
            return 0.5
        
        return weighted_sum / total_weight
    
    def _determine_confidence_level(self, confidence: float) -> str:
        """Determine confidence level category"""
        if confidence >= 0.9:
            return "VERY_HIGH"
        elif confidence >= 0.7:
            return "HIGH"
        elif confidence >= 0.5:
            return "MEDIUM"
        elif confidence >= 0.3:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _calculate_reliability_score(self, factors: List[ConfidenceFactor], 
                                   overall_confidence: float) -> float:
        """Calculate reliability score based on factor consistency"""
        if not factors:
            return 0.5
        
        # Calculate variance in factor values
        factor_values = [f.value for f in factors]
        mean_value = sum(factor_values) / len(factor_values)
        variance = sum((v - mean_value) ** 2 for v in factor_values) / len(factor_values)
        
        # Lower variance = higher reliability
        consistency_score = max(0, 1 - variance)
        
        # Combine with overall confidence
        reliability = (consistency_score + overall_confidence) / 2
        
        return reliability
    
    def _identify_uncertainty_sources(self, factors: List[ConfidenceFactor]) -> List[str]:
        """Identify main sources of uncertainty"""
        uncertainty_sources = []
        
        for factor in factors:
            if factor.value < 0.5:  # Low confidence factors
                uncertainty_sources.append(f"{factor.factor_type.value}: {factor.description}")
        
        return uncertainty_sources
    
    def _generate_confidence_explanation(self, factors: List[ConfidenceFactor], 
                                       overall_confidence: float) -> str:
        """Generate human-readable confidence explanation"""
        confidence_level = self._determine_confidence_level(overall_confidence)
        
        explanation_parts = [f"Overall confidence: {confidence_level} ({overall_confidence:.3f})"]
        
        # Highlight top contributing factors
        sorted_factors = sorted(factors, key=lambda f: f.value * f.weight, reverse=True)
        top_factors = sorted_factors[:3]
        
        for factor in top_factors:
            contribution = factor.value * factor.weight
            explanation_parts.append(f"{factor.factor_type.value}: {factor.value:.3f} (weight: {factor.weight:.2f})")
        
        # Mention main uncertainty sources
        low_factors = [f for f in factors if f.value < 0.5]
        if low_factors:
            explanation_parts.append(f"Main uncertainties: {', '.join(f.factor_type.value for f in low_factors[:2])}")
        
        return "; ".join(explanation_parts)
    
    def update_historical_accuracy(self, decision_type: str, was_correct: bool):
        """Update historical accuracy tracking"""
        if decision_type not in self.historical_accuracy:
            self.historical_accuracy[decision_type] = {
                'correct_count': 0,
                'total_count': 0,
                'accuracy': 0.5
            }
        
        data = self.historical_accuracy[decision_type]
        data['total_count'] += 1
        if was_correct:
            data['correct_count'] += 1
        
        data['accuracy'] = data['correct_count'] / data['total_count']
        data['sample_size'] = data['total_count']
        
        logger.info(f"Updated historical accuracy for {decision_type}: {data['accuracy']:.3f} ({data['total_count']} samples)")
    
    def get_confidence_stats(self) -> Dict[str, Any]:
        """Get confidence scoring statistics"""
        return {
            "historical_accuracy": self.historical_accuracy,
            "default_weights": self.default_weights,
            "calibration_data": self.confidence_calibration
        }