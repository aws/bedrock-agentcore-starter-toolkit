#!/usr/bin/env python3
"""
Explanation Generation System
Creates human-readable explanations for fraud detection decisions
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExplanationStyle(Enum):
    """Different explanation styles for different audiences"""
    TECHNICAL = "technical"
    BUSINESS = "business"
    REGULATORY = "regulatory"
    CUSTOMER = "customer"
    EXECUTIVE = "executive"

class ExplanationLevel(Enum):
    """Level of detail in explanations"""
    BRIEF = "brief"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"

@dataclass
class ExplanationSection:
    """Individual section of an explanation"""
    title: str
    content: str
    importance: float  # 0.0 to 1.0
    evidence: List[str]
    confidence: float
    section_type: str  # 'summary', 'analysis', 'evidence', 'recommendation'

@dataclass
class ExplanationReport:
    """Complete explanation report"""
    transaction_id: str
    decision: str  # 'APPROVE', 'FLAG', 'REVIEW', 'BLOCK'
    confidence: float
    risk_level: str
    executive_summary: str
    sections: List[ExplanationSection]
    key_factors: List[str]
    evidence_summary: List[str]
    recommendations: List[str]
    explanation_style: ExplanationStyle
    explanation_level: ExplanationLevel
    generated_timestamp: str
    reasoning_id: str

class ExplanationGenerator:
    """
    Generates human-readable explanations for fraud detection decisions
    """
    
    def __init__(self):
        """Initialize explanation generator"""
        self.explanation_templates = self._load_explanation_templates()
        self.style_configurations = self._load_style_configurations()
        self.generated_explanations: List[ExplanationReport] = []
        
        logger.info("ExplanationGenerator initialized")
    
    def _load_explanation_templates(self) -> Dict[str, str]:
        """Load explanation templates for different scenarios"""
        return {
            "fraud_detected": {
                "executive_summary": "Transaction flagged as fraudulent based on {risk_factors} with {confidence:.0%} confidence.",
                "analysis_intro": "Our fraud detection system analyzed this transaction using advanced AI reasoning and identified several concerning patterns:",
                "evidence_intro": "The following evidence supports this fraud determination:",
                "recommendation_intro": "Based on this analysis, we recommend:",
                "confidence_explanation": "This decision has {confidence:.0%} confidence based on {factor_count} analysis factors."
            },
            "approved_transaction": {
                "executive_summary": "Transaction approved as legitimate with {confidence:.0%} confidence.",
                "analysis_intro": "Our analysis indicates this transaction follows normal patterns:",
                "evidence_intro": "Supporting evidence for approval:",
                "recommendation_intro": "Recommended action:",
                "confidence_explanation": "This approval has {confidence:.0%} confidence based on comprehensive analysis."
            },
            "review_required": {
                "executive_summary": "Transaction requires manual review due to {uncertainty_factors}.",
                "analysis_intro": "Our analysis identified mixed signals requiring human judgment:",
                "evidence_intro": "Factors requiring review:",
                "recommendation_intro": "Manual review should focus on:",
                "confidence_explanation": "Confidence level of {confidence:.0%} indicates need for human oversight."
            }
        }
    
    def _load_style_configurations(self) -> Dict[ExplanationStyle, Dict[str, Any]]:
        """Load style configurations for different audiences"""
        return {
            ExplanationStyle.TECHNICAL: {
                "vocabulary": "technical",
                "include_metrics": True,
                "include_algorithms": True,
                "detail_level": "high",
                "format": "structured"
            },
            ExplanationStyle.BUSINESS: {
                "vocabulary": "business",
                "include_metrics": True,
                "include_algorithms": False,
                "detail_level": "medium",
                "format": "narrative"
            },
            ExplanationStyle.REGULATORY: {
                "vocabulary": "formal",
                "include_metrics": True,
                "include_algorithms": True,
                "detail_level": "comprehensive",
                "format": "audit_trail"
            },
            ExplanationStyle.CUSTOMER: {
                "vocabulary": "simple",
                "include_metrics": False,
                "include_algorithms": False,
                "detail_level": "low",
                "format": "friendly"
            },
            ExplanationStyle.EXECUTIVE: {
                "vocabulary": "business",
                "include_metrics": False,
                "include_algorithms": False,
                "detail_level": "summary",
                "format": "executive"
            }
        }    

    def generate_explanation(self, reasoning_result: Dict[str, Any], 
                           style: ExplanationStyle = ExplanationStyle.BUSINESS,
                           level: ExplanationLevel = ExplanationLevel.DETAILED) -> ExplanationReport:
        """
        Generate comprehensive explanation for a fraud detection decision
        """
        logger.info(f"Generating {style.value} explanation at {level.value} level")
        
        try:
            # Extract key information
            transaction_id = reasoning_result.get('transaction_id', 'unknown')
            final_decision = reasoning_result.get('final_decision', {})
            reasoning_steps = reasoning_result.get('steps', [])
            overall_confidence = reasoning_result.get('overall_confidence', 0.5)
            
            # Determine decision type
            is_fraud = final_decision.get('is_fraud', False)
            risk_level = final_decision.get('risk_level', 'MEDIUM')
            recommended_action = final_decision.get('recommended_action', 'REVIEW')
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                final_decision, overall_confidence, reasoning_steps, style
            )
            
            # Generate explanation sections
            sections = self._generate_explanation_sections(
                reasoning_steps, final_decision, style, level
            )
            
            # Extract key factors and evidence
            key_factors = self._extract_key_factors(reasoning_steps, final_decision)
            evidence_summary = self._compile_evidence_summary(reasoning_steps)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                final_decision, reasoning_steps, style
            )
            
            # Create explanation report
            explanation_report = ExplanationReport(
                transaction_id=transaction_id,
                decision=recommended_action,
                confidence=overall_confidence,
                risk_level=risk_level,
                executive_summary=executive_summary,
                sections=sections,
                key_factors=key_factors,
                evidence_summary=evidence_summary,
                recommendations=recommendations,
                explanation_style=style,
                explanation_level=level,
                generated_timestamp=datetime.now().isoformat(),
                reasoning_id=reasoning_result.get('reasoning_id', 'unknown')
            )
            
            # Store generated explanation
            self.generated_explanations.append(explanation_report)
            
            logger.info(f"Generated explanation with {len(sections)} sections")
            return explanation_report
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {str(e)}")
            raise
    
    def _generate_executive_summary(self, final_decision: Dict[str, Any], 
                                  confidence: float, reasoning_steps: List[Dict[str, Any]],
                                  style: ExplanationStyle) -> str:
        """Generate executive summary based on decision and style"""
        
        is_fraud = final_decision.get('is_fraud', False)
        risk_level = final_decision.get('risk_level', 'MEDIUM')
        primary_concerns = final_decision.get('primary_concerns', [])
        
        # Determine template based on decision
        if is_fraud:
            template_key = "fraud_detected"
            risk_factors = ", ".join(primary_concerns[:3]) if primary_concerns else "multiple risk indicators"
        elif confidence < 0.6:
            template_key = "review_required"
            uncertainty_factors = "mixed risk signals and moderate confidence"
        else:
            template_key = "approved_transaction"
            risk_factors = "normal transaction patterns"
        
        # Get template
        template = self.explanation_templates[template_key]["executive_summary"]
        
        # Format based on style
        if style == ExplanationStyle.EXECUTIVE:
            return template.format(
                confidence=confidence,
                risk_factors=risk_factors,
                uncertainty_factors=uncertainty_factors if 'uncertainty_factors' in locals() else ""
            )
        elif style == ExplanationStyle.TECHNICAL:
            return f"Fraud Detection Result: {final_decision.get('recommended_action', 'REVIEW')} " + \
                   f"(Confidence: {confidence:.3f}, Risk Level: {risk_level}, " + \
                   f"Analysis Steps: {len(reasoning_steps)})"
        elif style == ExplanationStyle.CUSTOMER:
            if is_fraud:
                return f"We've temporarily blocked this transaction for your security. " + \
                       f"We detected unusual patterns that suggest potential fraud."
            else:
                return f"Your transaction has been approved and processed successfully."
        else:
            return template.format(
                confidence=confidence,
                risk_factors=risk_factors,
                uncertainty_factors=uncertainty_factors if 'uncertainty_factors' in locals() else ""
            )
    
    def _generate_explanation_sections(self, reasoning_steps: List[Dict[str, Any]], 
                                     final_decision: Dict[str, Any],
                                     style: ExplanationStyle, 
                                     level: ExplanationLevel) -> List[ExplanationSection]:
        """Generate detailed explanation sections"""
        
        sections = []
        
        # Analysis Overview Section
        analysis_section = self._create_analysis_overview_section(
            reasoning_steps, final_decision, style, level
        )
        sections.append(analysis_section)
        
        # Key Findings Section
        if level in [ExplanationLevel.DETAILED, ExplanationLevel.COMPREHENSIVE]:
            findings_section = self._create_key_findings_section(
                reasoning_steps, style
            )
            sections.append(findings_section)
        
        # Evidence Section
        evidence_section = self._create_evidence_section(
            reasoning_steps, style, level
        )
        sections.append(evidence_section)
        
        # Risk Assessment Section
        if level == ExplanationLevel.COMPREHENSIVE or style == ExplanationStyle.REGULATORY:
            risk_section = self._create_risk_assessment_section(
                reasoning_steps, final_decision, style
            )
            sections.append(risk_section)
        
        # Confidence Analysis Section
        if style in [ExplanationStyle.TECHNICAL, ExplanationStyle.REGULATORY]:
            confidence_section = self._create_confidence_analysis_section(
                reasoning_steps, final_decision, style
            )
            sections.append(confidence_section)
        
        # Recommendations Section
        recommendations_section = self._create_recommendations_section(
            final_decision, reasoning_steps, style
        )
        sections.append(recommendations_section)
        
        return sections
    
    def _create_analysis_overview_section(self, reasoning_steps: List[Dict[str, Any]], 
                                        final_decision: Dict[str, Any],
                                        style: ExplanationStyle, 
                                        level: ExplanationLevel) -> ExplanationSection:
        """Create analysis overview section"""
        
        is_fraud = final_decision.get('is_fraud', False)
        
        if style == ExplanationStyle.TECHNICAL:
            content = f"Executed {len(reasoning_steps)} reasoning steps using chain-of-thought analysis. "
            content += f"Primary analysis types: {', '.join(set(step.get('step_type', 'unknown') for step in reasoning_steps))}. "
            content += f"Decision confidence: {final_decision.get('confidence', 0.5):.3f}"
            
        elif style == ExplanationStyle.CUSTOMER:
            if is_fraud:
                content = "We carefully reviewed your transaction using our security systems and found patterns that don't match your usual spending behavior."
            else:
                content = "We reviewed your transaction and confirmed it matches your normal spending patterns."
                
        elif style == ExplanationStyle.REGULATORY:
            content = f"Comprehensive fraud analysis conducted using {len(reasoning_steps)} systematic evaluation steps. "
            content += f"Analysis included pattern recognition, risk assessment, and evidence validation. "
            content += f"All steps documented for audit compliance."
            
        else:  # Business style
            content = f"Our fraud detection system performed a comprehensive analysis of this transaction. "
            content += f"The analysis examined transaction patterns, user behavior, and risk indicators "
            content += f"to determine the likelihood of fraudulent activity."
        
        # Compile evidence from reasoning steps
        evidence = []
        for step in reasoning_steps[:3]:  # Top 3 steps
            if 'evidence' in step and step['evidence']:
                evidence.extend(step['evidence'][:2])  # Top 2 pieces of evidence per step
        
        return ExplanationSection(
            title="Analysis Overview",
            content=content,
            importance=1.0,
            evidence=evidence[:5],  # Limit to 5 pieces of evidence
            confidence=final_decision.get('confidence', 0.5),
            section_type='analysis'
        )
    
    def _create_key_findings_section(self, reasoning_steps: List[Dict[str, Any]], 
                                   style: ExplanationStyle) -> ExplanationSection:
        """Create key findings section"""
        
        findings = []
        evidence = []
        
        for step in reasoning_steps:
            step_output = step.get('output', {})
            
            # Extract key findings from step output
            if 'key_findings' in step_output:
                findings.extend(step_output['key_findings'])
            
            # Extract primary concerns
            if 'primary_concerns' in step_output:
                findings.extend(step_output['primary_concerns'])
            
            # Add evidence
            if 'evidence' in step:
                evidence.extend(step['evidence'])
        
        # Remove duplicates and limit
        unique_findings = list(dict.fromkeys(findings))[:5]
        unique_evidence = list(dict.fromkeys(evidence))[:7]
        
        if style == ExplanationStyle.TECHNICAL:
            content = "Key algorithmic findings: " + "; ".join(unique_findings)
        elif style == ExplanationStyle.CUSTOMER:
            content = "Main points from our review: " + "; ".join(unique_findings)
        else:
            content = "Key findings from the analysis: " + "; ".join(unique_findings)
        
        return ExplanationSection(
            title="Key Findings",
            content=content,
            importance=0.9,
            evidence=unique_evidence,
            confidence=0.8,
            section_type='analysis'
        )
    
    def _create_evidence_section(self, reasoning_steps: List[Dict[str, Any]], 
                               style: ExplanationStyle, 
                               level: ExplanationLevel) -> ExplanationSection:
        """Create evidence section"""
        
        all_evidence = []
        high_confidence_evidence = []
        
        for step in reasoning_steps:
            if 'evidence' in step:
                all_evidence.extend(step['evidence'])
                
                # Collect high-confidence evidence
                if step.get('confidence', 0) > 0.7:
                    high_confidence_evidence.extend(step['evidence'])
        
        # Choose evidence based on level
        if level == ExplanationLevel.BRIEF:
            selected_evidence = high_confidence_evidence[:3]
        elif level == ExplanationLevel.DETAILED:
            selected_evidence = list(dict.fromkeys(all_evidence))[:7]
        else:  # Comprehensive
            selected_evidence = list(dict.fromkeys(all_evidence))[:12]
        
        if style == ExplanationStyle.TECHNICAL:
            content = f"Evidence analysis identified {len(selected_evidence)} key indicators: "
            content += "; ".join(selected_evidence)
        elif style == ExplanationStyle.CUSTOMER:
            content = "Here's what we found: " + "; ".join(selected_evidence[:3])
        elif style == ExplanationStyle.REGULATORY:
            content = f"Documentary evidence supporting this determination includes {len(selected_evidence)} factors: "
            content += "; ".join(selected_evidence)
        else:
            content = "Supporting evidence: " + "; ".join(selected_evidence)
        
        return ExplanationSection(
            title="Supporting Evidence",
            content=content,
            importance=0.8,
            evidence=selected_evidence,
            confidence=0.85,
            section_type='evidence'
        )
    
    def _create_risk_assessment_section(self, reasoning_steps: List[Dict[str, Any]], 
                                      final_decision: Dict[str, Any],
                                      style: ExplanationStyle) -> ExplanationSection:
        """Create risk assessment section"""
        
        risk_level = final_decision.get('risk_level', 'MEDIUM')
        risk_factors = []
        
        # Extract risk-related information
        for step in reasoning_steps:
            step_output = step.get('output', {})
            
            if 'risk_level' in step_output:
                risk_factors.append(f"{step.get('step_type', 'Analysis')}: {step_output['risk_level']} risk")
            
            if 'risk_factors' in step_output:
                risk_factors.extend(step_output['risk_factors'])
        
        unique_risk_factors = list(dict.fromkeys(risk_factors))[:5]
        
        if style == ExplanationStyle.TECHNICAL:
            content = f"Risk assessment: {risk_level} overall risk level. "
            content += f"Contributing factors: {'; '.join(unique_risk_factors)}"
        elif style == ExplanationStyle.REGULATORY:
            content = f"Risk evaluation determined {risk_level} risk classification based on "
            content += f"systematic assessment of {len(unique_risk_factors)} risk factors."
        else:
            content = f"Risk level: {risk_level}. "
            content += f"Risk factors: {'; '.join(unique_risk_factors)}"
        
        return ExplanationSection(
            title="Risk Assessment",
            content=content,
            importance=0.9,
            evidence=unique_risk_factors,
            confidence=final_decision.get('confidence', 0.5),
            section_type='analysis'
        )
    
    def _create_confidence_analysis_section(self, reasoning_steps: List[Dict[str, Any]], 
                                          final_decision: Dict[str, Any],
                                          style: ExplanationStyle) -> ExplanationSection:
        """Create confidence analysis section"""
        
        overall_confidence = final_decision.get('confidence', 0.5)
        step_confidences = [step.get('confidence', 0.5) for step in reasoning_steps]
        
        avg_step_confidence = sum(step_confidences) / len(step_confidences) if step_confidences else 0.5
        confidence_variance = sum((c - avg_step_confidence) ** 2 for c in step_confidences) / len(step_confidences) if step_confidences else 0
        
        content = f"Overall confidence: {overall_confidence:.1%}. "
        content += f"Average step confidence: {avg_step_confidence:.1%}. "
        
        if confidence_variance < 0.01:
            content += "High consistency across analysis steps."
        elif confidence_variance < 0.05:
            content += "Moderate consistency across analysis steps."
        else:
            content += "Variable confidence across analysis steps, indicating complexity."
        
        # Add confidence factors if available
        confidence_factors = []
        for step in reasoning_steps:
            if step.get('confidence', 0) > 0.8:
                confidence_factors.append(f"High confidence in {step.get('step_type', 'analysis')}")
            elif step.get('confidence', 0) < 0.4:
                confidence_factors.append(f"Low confidence in {step.get('step_type', 'analysis')}")
        
        return ExplanationSection(
            title="Confidence Analysis",
            content=content,
            importance=0.6,
            evidence=confidence_factors,
            confidence=overall_confidence,
            section_type='analysis'
        )
    
    def _create_recommendations_section(self, final_decision: Dict[str, Any], 
                                      reasoning_steps: List[Dict[str, Any]],
                                      style: ExplanationStyle) -> ExplanationSection:
        """Create recommendations section"""
        
        recommended_action = final_decision.get('recommended_action', 'REVIEW')
        is_fraud = final_decision.get('is_fraud', False)
        confidence = final_decision.get('confidence', 0.5)
        
        recommendations = []
        
        if recommended_action == 'BLOCK':
            if style == ExplanationStyle.CUSTOMER:
                recommendations.append("Transaction blocked for your security")
                recommendations.append("Contact customer service if this was a legitimate transaction")
            else:
                recommendations.append("Block transaction immediately")
                recommendations.append("Flag account for additional monitoring")
                recommendations.append("Consider fraud investigation")
        
        elif recommended_action == 'REVIEW':
            recommendations.append("Manual review required")
            recommendations.append("Examine transaction context and user history")
            if confidence < 0.6:
                recommendations.append("Consider additional verification steps")
        
        elif recommended_action == 'FLAG':
            recommendations.append("Flag for monitoring")
            recommendations.append("Track for pattern analysis")
            recommendations.append("Allow transaction to proceed with monitoring")
        
        else:  # APPROVE
            if style == ExplanationStyle.CUSTOMER:
                recommendations.append("Transaction approved and processed")
            else:
                recommendations.append("Approve transaction")
                recommendations.append("Continue normal monitoring")
        
        content = "; ".join(recommendations)
        
        return ExplanationSection(
            title="Recommendations",
            content=content,
            importance=1.0,
            evidence=recommendations,
            confidence=confidence,
            section_type='recommendation'
        ) 
   
    def _extract_key_factors(self, reasoning_steps: List[Dict[str, Any]], 
                           final_decision: Dict[str, Any]) -> List[str]:
        """Extract key factors that influenced the decision"""
        
        key_factors = []
        
        # Add primary concerns from final decision
        if 'primary_concerns' in final_decision:
            key_factors.extend(final_decision['primary_concerns'])
        
        # Add high-confidence findings from steps
        for step in reasoning_steps:
            if step.get('confidence', 0) > 0.8:
                step_output = step.get('output', {})
                
                if 'key_findings' in step_output:
                    key_factors.extend(step_output['key_findings'])
                
                if 'primary_concerns' in step_output:
                    key_factors.extend(step_output['primary_concerns'])
        
        # Remove duplicates and limit
        return list(dict.fromkeys(key_factors))[:7]
    
    def _compile_evidence_summary(self, reasoning_steps: List[Dict[str, Any]]) -> List[str]:
        """Compile evidence summary from all reasoning steps"""
        
        all_evidence = []
        
        for step in reasoning_steps:
            if 'evidence' in step:
                all_evidence.extend(step['evidence'])
        
        # Remove duplicates and limit
        return list(dict.fromkeys(all_evidence))[:10]
    
    def _generate_recommendations(self, final_decision: Dict[str, Any], 
                                reasoning_steps: List[Dict[str, Any]],
                                style: ExplanationStyle) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        recommended_action = final_decision.get('recommended_action', 'REVIEW')
        confidence = final_decision.get('confidence', 0.5)
        
        # Primary recommendation based on decision
        if recommended_action == 'BLOCK':
            recommendations.append("Block transaction immediately")
            recommendations.append("Notify customer of security concern")
            recommendations.append("Initiate fraud investigation")
        elif recommended_action == 'REVIEW':
            recommendations.append("Conduct manual review")
            recommendations.append("Verify transaction with customer")
        elif recommended_action == 'FLAG':
            recommendations.append("Allow transaction with monitoring")
            recommendations.append("Add to watchlist for pattern analysis")
        else:  # APPROVE
            recommendations.append("Process transaction normally")
        
        # Additional recommendations based on confidence
        if confidence < 0.6:
            recommendations.append("Consider additional verification")
        
        # Recommendations based on reasoning steps
        for step in reasoning_steps:
            step_output = step.get('output', {})
            if 'recommendations' in step_output:
                recommendations.extend(step_output['recommendations'])
        
        return list(dict.fromkeys(recommendations))[:5]
    
    def format_explanation_as_text(self, explanation: ExplanationReport) -> str:
        """Format explanation as plain text"""
        
        text_parts = []
        
        # Header
        text_parts.append(f"FRAUD DETECTION EXPLANATION")
        text_parts.append(f"Transaction ID: {explanation.transaction_id}")
        text_parts.append(f"Decision: {explanation.decision}")
        text_parts.append(f"Confidence: {explanation.confidence:.1%}")
        text_parts.append(f"Risk Level: {explanation.risk_level}")
        text_parts.append("")
        
        # Executive Summary
        text_parts.append("EXECUTIVE SUMMARY")
        text_parts.append(explanation.executive_summary)
        text_parts.append("")
        
        # Sections
        for section in explanation.sections:
            text_parts.append(section.title.upper())
            text_parts.append(section.content)
            
            if section.evidence and explanation.explanation_level != ExplanationLevel.BRIEF:
                text_parts.append("Evidence:")
                for evidence in section.evidence[:3]:
                    text_parts.append(f"  - {evidence}")
            
            text_parts.append("")
        
        # Key Factors
        if explanation.key_factors:
            text_parts.append("KEY FACTORS")
            for factor in explanation.key_factors:
                text_parts.append(f"  - {factor}")
            text_parts.append("")
        
        # Recommendations
        if explanation.recommendations:
            text_parts.append("RECOMMENDATIONS")
            for rec in explanation.recommendations:
                text_parts.append(f"  - {rec}")
        
        return "\n".join(text_parts)
    
    def format_explanation_as_html(self, explanation: ExplanationReport) -> str:
        """Format explanation as HTML"""
        
        html_parts = []
        
        # CSS styles
        styles = """
        <style>
        .explanation-report { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .decision-approved { color: #28a745; }
        .decision-flagged { color: #ffc107; }
        .decision-blocked { color: #dc3545; }
        .section { margin-bottom: 20px; padding: 15px; border-left: 4px solid #007bff; }
        .evidence-list { margin: 10px 0; padding-left: 20px; }
        .confidence-high { color: #28a745; }
        .confidence-medium { color: #ffc107; }
        .confidence-low { color: #dc3545; }
        </style>
        """
        
        html_parts.append(f"<html><head>{styles}</head><body>")
        html_parts.append('<div class="explanation-report">')
        
        # Header
        decision_class = f"decision-{explanation.decision.lower()}"
        confidence_class = "confidence-high" if explanation.confidence > 0.7 else "confidence-medium" if explanation.confidence > 0.4 else "confidence-low"
        
        html_parts.append('<div class="header">')
        html_parts.append('<h1>Fraud Detection Explanation</h1>')
        html_parts.append(f'<p><strong>Transaction ID:</strong> {explanation.transaction_id}</p>')
        html_parts.append(f'<p><strong>Decision:</strong> <span class="{decision_class}">{explanation.decision}</span></p>')
        html_parts.append(f'<p><strong>Confidence:</strong> <span class="{confidence_class}">{explanation.confidence:.1%}</span></p>')
        html_parts.append(f'<p><strong>Risk Level:</strong> {explanation.risk_level}</p>')
        html_parts.append('</div>')
        
        # Executive Summary
        html_parts.append('<div class="section">')
        html_parts.append('<h2>Executive Summary</h2>')
        html_parts.append(f'<p>{explanation.executive_summary}</p>')
        html_parts.append('</div>')
        
        # Sections
        for section in explanation.sections:
            html_parts.append('<div class="section">')
            html_parts.append(f'<h3>{section.title}</h3>')
            html_parts.append(f'<p>{section.content}</p>')
            
            if section.evidence and explanation.explanation_level != ExplanationLevel.BRIEF:
                html_parts.append('<div class="evidence-list">')
                html_parts.append('<strong>Evidence:</strong>')
                html_parts.append('<ul>')
                for evidence in section.evidence[:5]:
                    html_parts.append(f'<li>{evidence}</li>')
                html_parts.append('</ul>')
                html_parts.append('</div>')
            
            html_parts.append('</div>')
        
        html_parts.append('</div></body></html>')
        
        return "\n".join(html_parts)
    
    def format_explanation_as_json(self, explanation: ExplanationReport) -> str:
        """Format explanation as JSON"""
        
        # Convert to dictionary with serializable types
        explanation_dict = {
            'transaction_id': explanation.transaction_id,
            'decision': explanation.decision,
            'confidence': explanation.confidence,
            'risk_level': explanation.risk_level,
            'executive_summary': explanation.executive_summary,
            'sections': [
                {
                    'title': section.title,
                    'content': section.content,
                    'importance': section.importance,
                    'evidence': section.evidence,
                    'confidence': section.confidence,
                    'section_type': section.section_type
                }
                for section in explanation.sections
            ],
            'key_factors': explanation.key_factors,
            'evidence_summary': explanation.evidence_summary,
            'recommendations': explanation.recommendations,
            'explanation_style': explanation.explanation_style.value,
            'explanation_level': explanation.explanation_level.value,
            'generated_timestamp': explanation.generated_timestamp,
            'reasoning_id': explanation.reasoning_id
        }
        
        return json.dumps(explanation_dict, indent=2)
    
    def generate_audit_trail(self, explanation: ExplanationReport) -> str:
        """Generate audit trail format for regulatory compliance"""
        
        audit_parts = []
        
        # Audit header
        audit_parts.append("FRAUD DETECTION AUDIT TRAIL")
        audit_parts.append("=" * 50)
        audit_parts.append(f"Transaction ID: {explanation.transaction_id}")
        audit_parts.append(f"Analysis Timestamp: {explanation.generated_timestamp}")
        audit_parts.append(f"Reasoning ID: {explanation.reasoning_id}")
        audit_parts.append(f"Decision: {explanation.decision}")
        audit_parts.append(f"Confidence Level: {explanation.confidence:.3f}")
        audit_parts.append(f"Risk Classification: {explanation.risk_level}")
        audit_parts.append("")
        
        # Decision rationale
        audit_parts.append("DECISION RATIONALE")
        audit_parts.append("-" * 20)
        audit_parts.append(explanation.executive_summary)
        audit_parts.append("")
        
        # Analysis steps
        audit_parts.append("ANALYSIS STEPS")
        audit_parts.append("-" * 15)
        for i, section in enumerate(explanation.sections, 1):
            audit_parts.append(f"{i}. {section.title}")
            audit_parts.append(f"   Content: {section.content}")
            audit_parts.append(f"   Confidence: {section.confidence:.3f}")
            audit_parts.append(f"   Importance: {section.importance:.3f}")
            if section.evidence:
                audit_parts.append("   Evidence:")
                for evidence in section.evidence:
                    audit_parts.append(f"     - {evidence}")
            audit_parts.append("")
        
        # Key factors
        audit_parts.append("KEY DECISION FACTORS")
        audit_parts.append("-" * 20)
        for factor in explanation.key_factors:
            audit_parts.append(f"  - {factor}")
        audit_parts.append("")
        
        # Recommendations
        audit_parts.append("RECOMMENDED ACTIONS")
        audit_parts.append("-" * 18)
        for rec in explanation.recommendations:
            audit_parts.append(f"  - {rec}")
        
        # Footer
        audit_parts.append("")
        audit_parts.append("=" * 50)
        audit_parts.append("End of Audit Trail")
        
        return "\n".join(audit_parts)
    
    def get_explanation_quality_score(self, explanation: ExplanationReport) -> Dict[str, float]:
        """Calculate quality score for an explanation"""
        
        scores = {}
        
        # Completeness score
        completeness = 0.0
        if explanation.executive_summary:
            completeness += 0.2
        if explanation.sections:
            completeness += 0.3
        if explanation.key_factors:
            completeness += 0.2
        if explanation.evidence_summary:
            completeness += 0.2
        if explanation.recommendations:
            completeness += 0.1
        
        scores['completeness'] = completeness
        
        # Detail score
        total_content_length = len(explanation.executive_summary)
        total_content_length += sum(len(section.content) for section in explanation.sections)
        
        if total_content_length > 1000:
            scores['detail'] = 1.0
        elif total_content_length > 500:
            scores['detail'] = 0.8
        elif total_content_length > 200:
            scores['detail'] = 0.6
        else:
            scores['detail'] = 0.4
        
        # Evidence score
        total_evidence = len(explanation.evidence_summary)
        total_evidence += sum(len(section.evidence) for section in explanation.sections)
        
        scores['evidence'] = min(1.0, total_evidence / 10.0)
        
        # Confidence consistency score
        section_confidences = [section.confidence for section in explanation.sections]
        if section_confidences:
            confidence_variance = sum((c - explanation.confidence) ** 2 for c in section_confidences) / len(section_confidences)
            scores['consistency'] = max(0.0, 1.0 - confidence_variance * 5)
        else:
            scores['consistency'] = 0.5
        
        # Overall quality score
        scores['overall'] = sum(scores.values()) / len(scores)
        
        return scores
    
    def get_explanation_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated explanations"""
        
        if not self.generated_explanations:
            return {'total_explanations': 0}
        
        total = len(self.generated_explanations)
        
        # Decision distribution
        decisions = [exp.decision for exp in self.generated_explanations]
        decision_counts = {}
        for decision in decisions:
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        # Style distribution
        styles = [exp.explanation_style.value for exp in self.generated_explanations]
        style_counts = {}
        for style in styles:
            style_counts[style] = style_counts.get(style, 0) + 1
        
        # Average confidence
        avg_confidence = sum(exp.confidence for exp in self.generated_explanations) / total
        
        # Average sections per explanation
        avg_sections = sum(len(exp.sections) for exp in self.generated_explanations) / total
        
        return {
            'total_explanations': total,
            'decision_distribution': decision_counts,
            'style_distribution': style_counts,
            'average_confidence': avg_confidence,
            'average_sections_per_explanation': avg_sections
        }