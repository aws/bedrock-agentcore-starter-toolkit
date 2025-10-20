#!/usr/bin/env python3
"""
Explanation Quality Validator
Validates and scores the quality of generated explanations
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationCriteria(Enum):
    """Criteria for explanation validation"""
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    CONSISTENCY = "consistency"
    COMPREHENSIVENESS = "comprehensiveness"
    ACTIONABILITY = "actionability"

@dataclass
class ValidationResult:
    """Result of explanation validation"""
    criteria: ValidationCriteria
    score: float  # 0.0 to 1.0
    issues: List[str]
    suggestions: List[str]
    evidence: List[str]

@dataclass
class ExplanationQualityReport:
    """Complete quality assessment report"""
    explanation_id: str
    overall_quality_score: float
    validation_results: List[ValidationResult]
    quality_grade: str  # A, B, C, D, F
    strengths: List[str]
    weaknesses: List[str]
    improvement_recommendations: List[str]
    validation_timestamp: str

class ExplanationValidator:
    """
    Validates explanation quality across multiple criteria
    """
    
    def __init__(self):
        """Initialize explanation validator"""
        self.validation_rules = self._load_validation_rules()
        self.quality_thresholds = self._load_quality_thresholds()
        self.validation_history: List[ExplanationQualityReport] = []
        
        logger.info("ExplanationValidator initialized")
    
    def _load_validation_rules(self) -> Dict[ValidationCriteria, Dict[str, Any]]:
        """Load validation rules for each criteria"""
        return {
            ValidationCriteria.COMPLETENESS: {
                "required_sections": ["executive_summary", "sections", "recommendations"],
                "min_sections": 3,
                "min_evidence_items": 2,
                "min_content_length": 200
            },
            ValidationCriteria.CLARITY: {
                "max_sentence_length": 30,
                "min_readability_score": 0.6,
                "avoid_jargon": True,
                "clear_structure": True
            },
            ValidationCriteria.ACCURACY: {
                "confidence_consistency": True,
                "evidence_support": True,
                "logical_consistency": True,
                "fact_verification": True
            },
            ValidationCriteria.RELEVANCE: {
                "decision_alignment": True,
                "context_appropriate": True,
                "audience_suitable": True,
                "actionable_insights": True
            },
            ValidationCriteria.CONSISTENCY: {
                "internal_consistency": True,
                "confidence_alignment": True,
                "evidence_consistency": True,
                "recommendation_alignment": True
            },
            ValidationCriteria.COMPREHENSIVENESS: {
                "covers_all_factors": True,
                "addresses_uncertainties": True,
                "includes_alternatives": True,
                "sufficient_detail": True
            },
            ValidationCriteria.ACTIONABILITY: {
                "clear_recommendations": True,
                "specific_actions": True,
                "prioritized_steps": True,
                "implementation_guidance": True
            }
        }
    
    def _load_quality_thresholds(self) -> Dict[str, float]:
        """Load quality score thresholds"""
        return {
            "excellent": 0.9,
            "good": 0.8,
            "satisfactory": 0.7,
            "needs_improvement": 0.6,
            "poor": 0.0
        }
    
    def validate_explanation(self, explanation_report: Dict[str, Any]) -> ExplanationQualityReport:
        """
        Validate explanation quality across all criteria
        """
        logger.info("Validating explanation quality")
        
        try:
            explanation_id = explanation_report.get('reasoning_id', 'unknown')
            
            # Validate each criteria
            validation_results = []
            
            for criteria in ValidationCriteria:
                result = self._validate_criteria(explanation_report, criteria)
                validation_results.append(result)
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_score(validation_results)
            
            # Determine quality grade
            quality_grade = self._determine_quality_grade(overall_score)
            
            # Identify strengths and weaknesses
            strengths = self._identify_strengths(validation_results)
            weaknesses = self._identify_weaknesses(validation_results)
            
            # Generate improvement recommendations
            recommendations = self._generate_improvement_recommendations(validation_results)
            
            # Create quality report
            quality_report = ExplanationQualityReport(
                explanation_id=explanation_id,
                overall_quality_score=overall_score,
                validation_results=validation_results,
                quality_grade=quality_grade,
                strengths=strengths,
                weaknesses=weaknesses,
                improvement_recommendations=recommendations,
                validation_timestamp=datetime.now().isoformat()
            )
            
            # Store validation history
            self.validation_history.append(quality_report)
            
            logger.info(f"Explanation validation completed: Grade {quality_grade} ({overall_score:.2f})")
            return quality_report
            
        except Exception as e:
            logger.error(f"Explanation validation failed: {str(e)}")
            raise
    
    def _validate_criteria(self, explanation_report: Dict[str, Any], 
                          criteria: ValidationCriteria) -> ValidationResult:
        """Validate a specific criteria"""
        
        if criteria == ValidationCriteria.COMPLETENESS:
            return self._validate_completeness(explanation_report)
        elif criteria == ValidationCriteria.CLARITY:
            return self._validate_clarity(explanation_report)
        elif criteria == ValidationCriteria.ACCURACY:
            return self._validate_accuracy(explanation_report)
        elif criteria == ValidationCriteria.RELEVANCE:
            return self._validate_relevance(explanation_report)
        elif criteria == ValidationCriteria.CONSISTENCY:
            return self._validate_consistency(explanation_report)
        elif criteria == ValidationCriteria.COMPREHENSIVENESS:
            return self._validate_comprehensiveness(explanation_report)
        elif criteria == ValidationCriteria.ACTIONABILITY:
            return self._validate_actionability(explanation_report)
        else:
            return ValidationResult(
                criteria=criteria,
                score=0.5,
                issues=["Unknown validation criteria"],
                suggestions=["Review validation criteria"],
                evidence=[]
            )
    
    def _validate_completeness(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate explanation completeness"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        rules = self.validation_rules[ValidationCriteria.COMPLETENESS]
        
        # Check required sections
        required_sections = rules["required_sections"]
        for section in required_sections:
            if section not in explanation_report or not explanation_report[section]:
                score -= 0.3
                issues.append(f"Missing required section: {section}")
                suggestions.append(f"Add {section} section")
            else:
                evidence.append(f"Has {section} section")
        
        # Check minimum sections
        sections = explanation_report.get('sections', [])
        if len(sections) < rules["min_sections"]:
            score -= 0.2
            issues.append(f"Insufficient sections: {len(sections)} < {rules['min_sections']}")
            suggestions.append("Add more detailed analysis sections")
        else:
            evidence.append(f"Has {len(sections)} sections")
        
        # Check evidence items
        evidence_summary = explanation_report.get('evidence_summary', [])
        if len(evidence_summary) < rules["min_evidence_items"]:
            score -= 0.2
            issues.append(f"Insufficient evidence: {len(evidence_summary)} items")
            suggestions.append("Include more supporting evidence")
        else:
            evidence.append(f"Has {len(evidence_summary)} evidence items")
        
        # Check content length
        total_content = explanation_report.get('executive_summary', '')
        for section in sections:
            if isinstance(section, dict) and 'content' in section:
                total_content += section['content']
        
        if len(total_content) < rules["min_content_length"]:
            score -= 0.1
            issues.append("Content too brief")
            suggestions.append("Provide more detailed explanations")
        else:
            evidence.append(f"Content length: {len(total_content)} characters")
        
        return ValidationResult(
            criteria=ValidationCriteria.COMPLETENESS,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _validate_clarity(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate explanation clarity"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        # Collect all text content
        all_text = explanation_report.get('executive_summary', '')
        sections = explanation_report.get('sections', [])
        for section in sections:
            if isinstance(section, dict) and 'content' in section:
                all_text += ' ' + section['content']
        
        if not all_text:
            return ValidationResult(
                criteria=ValidationCriteria.CLARITY,
                score=0.0,
                issues=["No text content to evaluate"],
                suggestions=["Add text content"],
                evidence=[]
            )
        
        # Check sentence length
        sentences = re.split(r'[.!?]+', all_text)
        long_sentences = [s for s in sentences if len(s.split()) > 30]
        if long_sentences:
            score -= 0.2
            issues.append(f"{len(long_sentences)} sentences are too long")
            suggestions.append("Break down complex sentences")
        else:
            evidence.append("Sentence lengths are appropriate")
        
        # Check for jargon and technical terms
        jargon_terms = ['algorithm', 'heuristic', 'optimization', 'vectorization', 'tokenization']
        jargon_count = sum(1 for term in jargon_terms if term.lower() in all_text.lower())
        if jargon_count > 3:
            score -= 0.1
            issues.append("Contains excessive technical jargon")
            suggestions.append("Use simpler language for broader audience")
        else:
            evidence.append("Appropriate use of technical terms")
        
        # Check structure clarity
        if len(sections) > 0:
            sections_with_titles = sum(1 for s in sections if isinstance(s, dict) and s.get('title'))
            if sections_with_titles < len(sections):
                score -= 0.2
                issues.append("Some sections lack clear titles")
                suggestions.append("Add descriptive titles to all sections")
            else:
                evidence.append("All sections have clear titles")
        
        # Check readability (simplified)
        words = all_text.split()
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        if avg_word_length > 6:
            score -= 0.1
            issues.append("Average word length is high")
            suggestions.append("Use simpler vocabulary")
        else:
            evidence.append(f"Good readability (avg word length: {avg_word_length:.1f})")
        
        return ValidationResult(
            criteria=ValidationCriteria.CLARITY,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _validate_accuracy(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate explanation accuracy"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        # Check confidence consistency
        overall_confidence = explanation_report.get('confidence', 0.5)
        sections = explanation_report.get('sections', [])
        
        section_confidences = []
        for section in sections:
            if isinstance(section, dict) and 'confidence' in section:
                section_confidences.append(section['confidence'])
        
        if section_confidences:
            confidence_variance = sum((c - overall_confidence) ** 2 for c in section_confidences) / len(section_confidences)
            if confidence_variance > 0.1:
                score -= 0.2
                issues.append("Inconsistent confidence levels across sections")
                suggestions.append("Review and align confidence assessments")
            else:
                evidence.append("Consistent confidence levels")
        
        # Check evidence support
        evidence_summary = explanation_report.get('evidence_summary', [])
        decision = explanation_report.get('decision', 'REVIEW')
        
        if decision in ['BLOCK', 'FLAG'] and len(evidence_summary) < 3:
            score -= 0.3
            issues.append("Insufficient evidence for high-risk decision")
            suggestions.append("Provide more supporting evidence for fraud decisions")
        elif decision == 'APPROVE' and len(evidence_summary) < 1:
            score -= 0.1
            issues.append("No evidence provided for approval decision")
            suggestions.append("Include evidence supporting approval")
        else:
            evidence.append(f"Adequate evidence for {decision} decision")
        
        # Check logical consistency
        risk_level = explanation_report.get('risk_level', 'MEDIUM')
        if decision == 'APPROVE' and risk_level == 'HIGH':
            score -= 0.4
            issues.append("Logical inconsistency: APPROVE decision with HIGH risk")
            suggestions.append("Review decision logic for consistency")
        elif decision == 'BLOCK' and risk_level == 'LOW':
            score -= 0.4
            issues.append("Logical inconsistency: BLOCK decision with LOW risk")
            suggestions.append("Review decision logic for consistency")
        else:
            evidence.append("Decision aligns with risk level")
        
        return ValidationResult(
            criteria=ValidationCriteria.ACCURACY,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _validate_relevance(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate explanation relevance"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        # Check decision alignment
        decision = explanation_report.get('decision', 'REVIEW')
        executive_summary = explanation_report.get('executive_summary', '')
        
        if decision.upper() not in executive_summary.upper():
            score -= 0.2
            issues.append("Executive summary doesn't mention the decision")
            suggestions.append("Clearly state the decision in the summary")
        else:
            evidence.append("Decision clearly stated in summary")
        
        # Check context appropriateness
        explanation_style = explanation_report.get('explanation_style', 'business')
        sections = explanation_report.get('sections', [])
        
        if explanation_style == 'customer':
            # Customer explanations should be simple
            technical_terms = ['algorithm', 'heuristic', 'model', 'confidence score']
            all_content = executive_summary
            for section in sections:
                if isinstance(section, dict) and 'content' in section:
                    all_content += ' ' + section['content']
            
            technical_count = sum(1 for term in technical_terms if term in all_content.lower())
            if technical_count > 1:
                score -= 0.3
                issues.append("Too technical for customer audience")
                suggestions.append("Simplify language for customer communication")
            else:
                evidence.append("Appropriate language for customer audience")
        
        # Check actionable insights
        recommendations = explanation_report.get('recommendations', [])
        if not recommendations:
            score -= 0.2
            issues.append("No actionable recommendations provided")
            suggestions.append("Include specific recommendations")
        else:
            evidence.append(f"Provides {len(recommendations)} recommendations")
        
        return ValidationResult(
            criteria=ValidationCriteria.RELEVANCE,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _validate_consistency(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate internal consistency"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        # Check recommendation alignment with decision
        decision = explanation_report.get('decision', 'REVIEW')
        recommendations = explanation_report.get('recommendations', [])
        
        decision_keywords = {
            'APPROVE': ['approve', 'process', 'allow'],
            'BLOCK': ['block', 'deny', 'prevent'],
            'FLAG': ['flag', 'monitor', 'watch'],
            'REVIEW': ['review', 'examine', 'investigate']
        }
        
        expected_keywords = decision_keywords.get(decision, [])
        recommendation_text = ' '.join(recommendations).lower()
        
        keyword_found = any(keyword in recommendation_text for keyword in expected_keywords)
        if not keyword_found and recommendations:
            score -= 0.3
            issues.append(f"Recommendations don't align with {decision} decision")
            suggestions.append("Ensure recommendations match the decision")
        elif keyword_found:
            evidence.append("Recommendations align with decision")
        
        # Check evidence consistency
        evidence_summary = explanation_report.get('evidence_summary', [])
        key_factors = explanation_report.get('key_factors', [])
        
        # Look for contradictory evidence
        positive_indicators = ['normal', 'typical', 'expected', 'legitimate']
        negative_indicators = ['suspicious', 'unusual', 'anomalous', 'fraudulent']
        
        evidence_text = ' '.join(evidence_summary + key_factors).lower()
        positive_count = sum(1 for indicator in positive_indicators if indicator in evidence_text)
        negative_count = sum(1 for indicator in negative_indicators if indicator in evidence_text)
        
        if positive_count > 0 and negative_count > 0 and decision in ['APPROVE', 'BLOCK']:
            # Mixed signals should result in REVIEW, not definitive decision
            if abs(positive_count - negative_count) < 2:
                score -= 0.2
                issues.append("Mixed evidence signals for definitive decision")
                suggestions.append("Consider REVIEW decision for mixed signals")
        
        evidence.append(f"Evidence analysis: {positive_count} positive, {negative_count} negative indicators")
        
        return ValidationResult(
            criteria=ValidationCriteria.CONSISTENCY,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _validate_comprehensiveness(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate explanation comprehensiveness"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        # Check coverage of key areas
        sections = explanation_report.get('sections', [])
        section_types = []
        
        for section in sections:
            if isinstance(section, dict) and 'section_type' in section:
                section_types.append(section['section_type'])
        
        expected_types = ['analysis', 'evidence', 'recommendation']
        missing_types = [t for t in expected_types if t not in section_types]
        
        if missing_types:
            score -= 0.2 * len(missing_types)
            issues.append(f"Missing section types: {missing_types}")
            suggestions.append("Include all key analysis areas")
        else:
            evidence.append("Covers all key analysis areas")
        
        # Check uncertainty handling
        confidence = explanation_report.get('confidence', 1.0)
        if confidence < 0.8:
            # Low confidence should be addressed
            executive_summary = explanation_report.get('executive_summary', '')
            uncertainty_terms = ['uncertain', 'unclear', 'ambiguous', 'mixed', 'review']
            
            uncertainty_mentioned = any(term in executive_summary.lower() for term in uncertainty_terms)
            if not uncertainty_mentioned:
                score -= 0.2
                issues.append("Low confidence not adequately addressed")
                suggestions.append("Acknowledge and explain uncertainties")
            else:
                evidence.append("Uncertainties appropriately addressed")
        
        # Check detail sufficiency
        total_content_length = len(explanation_report.get('executive_summary', ''))
        for section in sections:
            if isinstance(section, dict) and 'content' in section:
                total_content_length += len(section['content'])
        
        if total_content_length < 500:
            score -= 0.1
            issues.append("Explanation lacks sufficient detail")
            suggestions.append("Provide more comprehensive analysis")
        else:
            evidence.append(f"Comprehensive detail ({total_content_length} characters)")
        
        return ValidationResult(
            criteria=ValidationCriteria.COMPREHENSIVENESS,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _validate_actionability(self, explanation_report: Dict[str, Any]) -> ValidationResult:
        """Validate explanation actionability"""
        
        score = 1.0
        issues = []
        suggestions = []
        evidence = []
        
        recommendations = explanation_report.get('recommendations', [])
        
        if not recommendations:
            score = 0.0
            issues.append("No recommendations provided")
            suggestions.append("Include specific actionable recommendations")
            return ValidationResult(
                criteria=ValidationCriteria.ACTIONABILITY,
                score=score,
                issues=issues,
                suggestions=suggestions,
                evidence=evidence
            )
        
        # Check for specific actions
        action_verbs = ['block', 'approve', 'review', 'investigate', 'monitor', 'verify', 'contact']
        specific_actions = 0
        
        for rec in recommendations:
            if any(verb in rec.lower() for verb in action_verbs):
                specific_actions += 1
        
        if specific_actions == 0:
            score -= 0.4
            issues.append("Recommendations lack specific actions")
            suggestions.append("Use action verbs in recommendations")
        else:
            evidence.append(f"{specific_actions} specific actions identified")
        
        # Check for vague language
        vague_terms = ['consider', 'maybe', 'possibly', 'might', 'could']
        vague_count = 0
        
        for rec in recommendations:
            vague_count += sum(1 for term in vague_terms if term in rec.lower())
        
        if vague_count > len(recommendations) // 2:
            score -= 0.2
            issues.append("Recommendations contain vague language")
            suggestions.append("Use more definitive language in recommendations")
        else:
            evidence.append("Recommendations use clear, definitive language")
        
        # Check prioritization
        if len(recommendations) > 3:
            # Look for priority indicators
            priority_terms = ['first', 'immediately', 'urgent', 'priority', 'critical']
            has_prioritization = any(term in ' '.join(recommendations).lower() for term in priority_terms)
            
            if not has_prioritization:
                score -= 0.1
                issues.append("Multiple recommendations lack prioritization")
                suggestions.append("Prioritize recommendations by importance")
            else:
                evidence.append("Recommendations include prioritization")
        
        return ValidationResult(
            criteria=ValidationCriteria.ACTIONABILITY,
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            evidence=evidence
        )
    
    def _calculate_overall_score(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall quality score"""
        
        if not validation_results:
            return 0.0
        
        # Weight different criteria
        weights = {
            ValidationCriteria.COMPLETENESS: 0.20,
            ValidationCriteria.CLARITY: 0.15,
            ValidationCriteria.ACCURACY: 0.25,
            ValidationCriteria.RELEVANCE: 0.15,
            ValidationCriteria.CONSISTENCY: 0.10,
            ValidationCriteria.COMPREHENSIVENESS: 0.10,
            ValidationCriteria.ACTIONABILITY: 0.05
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for result in validation_results:
            weight = weights.get(result.criteria, 0.1)
            weighted_sum += result.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _determine_quality_grade(self, overall_score: float) -> str:
        """Determine quality grade based on score"""
        
        if overall_score >= self.quality_thresholds["excellent"]:
            return "A"
        elif overall_score >= self.quality_thresholds["good"]:
            return "B"
        elif overall_score >= self.quality_thresholds["satisfactory"]:
            return "C"
        elif overall_score >= self.quality_thresholds["needs_improvement"]:
            return "D"
        else:
            return "F"
    
    def _identify_strengths(self, validation_results: List[ValidationResult]) -> List[str]:
        """Identify explanation strengths"""
        
        strengths = []
        
        for result in validation_results:
            if result.score >= 0.8:
                strengths.append(f"Strong {result.criteria.value}")
                strengths.extend(result.evidence[:2])  # Add top evidence
        
        return strengths[:5]  # Limit to top 5
    
    def _identify_weaknesses(self, validation_results: List[ValidationResult]) -> List[str]:
        """Identify explanation weaknesses"""
        
        weaknesses = []
        
        for result in validation_results:
            if result.score < 0.6:
                weaknesses.append(f"Weak {result.criteria.value}")
                weaknesses.extend(result.issues[:2])  # Add top issues
        
        return weaknesses[:5]  # Limit to top 5
    
    def _generate_improvement_recommendations(self, validation_results: List[ValidationResult]) -> List[str]:
        """Generate improvement recommendations"""
        
        recommendations = []
        
        # Sort by lowest scores first (highest priority)
        sorted_results = sorted(validation_results, key=lambda x: x.score)
        
        for result in sorted_results[:3]:  # Top 3 areas needing improvement
            if result.score < 0.8:
                recommendations.extend(result.suggestions[:2])
        
        return list(dict.fromkeys(recommendations))[:7]  # Remove duplicates, limit to 7
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        
        if not self.validation_history:
            return {'total_validations': 0}
        
        total = len(self.validation_history)
        
        # Grade distribution
        grades = [report.quality_grade for report in self.validation_history]
        grade_counts = {}
        for grade in grades:
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Average scores by criteria
        criteria_scores = {}
        for criteria in ValidationCriteria:
            scores = []
            for report in self.validation_history:
                for result in report.validation_results:
                    if result.criteria == criteria:
                        scores.append(result.score)
            
            if scores:
                criteria_scores[criteria.value] = sum(scores) / len(scores)
        
        # Overall average
        avg_overall_score = sum(report.overall_quality_score for report in self.validation_history) / total
        
        return {
            'total_validations': total,
            'grade_distribution': grade_counts,
            'average_overall_score': avg_overall_score,
            'average_scores_by_criteria': criteria_scores
        }