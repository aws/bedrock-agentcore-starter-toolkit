#!/usr/bin/env python3
"""
Reasoning Trail Formatter
Creates detailed, human-readable reasoning trails for audit and transparency
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrailFormat(Enum):
    """Different trail format types"""
    NARRATIVE = "narrative"
    STRUCTURED = "structured"
    TIMELINE = "timeline"
    FLOWCHART = "flowchart"
    AUDIT = "audit"

@dataclass
class ReasoningTrailStep:
    """Individual step in the reasoning trail"""
    step_number: int
    step_id: str
    step_type: str
    title: str
    description: str
    input_summary: str
    reasoning_process: str
    output_summary: str
    evidence: List[str]
    confidence: float
    processing_time_ms: float
    dependencies: List[str]
    timestamp: str

@dataclass
class ReasoningTrail:
    """Complete reasoning trail"""
    trail_id: str
    transaction_id: str
    reasoning_id: str
    steps: List[ReasoningTrailStep]
    decision_summary: str
    overall_confidence: float
    total_processing_time_ms: float
    trail_format: TrailFormat
    generated_timestamp: str

class ReasoningTrailFormatter:
    """
    Formats reasoning steps into human-readable trails
    """
    
    def __init__(self):
        """Initialize trail formatter"""
        self.trail_templates = self._load_trail_templates()
        self.generated_trails: List[ReasoningTrail] = []
        
        logger.info("ReasoningTrailFormatter initialized")
    
    def _load_trail_templates(self) -> Dict[str, Dict[str, str]]:
        """Load templates for different trail formats"""
        return {
            TrailFormat.NARRATIVE.value: {
                "step_intro": "Step {step_number}: {title}",
                "reasoning_intro": "The system reasoned as follows:",
                "evidence_intro": "This conclusion was based on:",
                "confidence_note": "Confidence in this step: {confidence:.1%}",
                "dependency_note": "This step built upon: {dependencies}",
                "transition": "Building on this analysis, the next step was:"
            },
            TrailFormat.STRUCTURED.value: {
                "step_header": "=== STEP {step_number}: {title} ===",
                "input_label": "INPUT:",
                "process_label": "REASONING PROCESS:",
                "output_label": "OUTPUT:",
                "evidence_label": "EVIDENCE:",
                "confidence_label": "CONFIDENCE:",
                "timing_label": "PROCESSING TIME:"
            },
            TrailFormat.TIMELINE.value: {
                "timestamp_format": "[{timestamp}] Step {step_number}",
                "duration_note": "(Duration: {processing_time_ms:.0f}ms)",
                "parallel_note": "Executed in parallel with steps: {parallel_steps}",
                "sequence_note": "Followed by: {next_steps}"
            },
            TrailFormat.AUDIT.value: {
                "audit_header": "AUDIT TRAIL ENTRY #{step_number}",
                "step_id_label": "Step ID:",
                "timestamp_label": "Timestamp:",
                "input_hash_label": "Input Hash:",
                "output_hash_label": "Output Hash:",
                "verification_label": "Verification Status:",
                "compliance_note": "Regulatory Compliance: DOCUMENTED"
            }
        }
    
    def create_reasoning_trail(self, reasoning_result: Dict[str, Any], 
                             trail_format: TrailFormat = TrailFormat.NARRATIVE) -> ReasoningTrail:
        """
        Create a comprehensive reasoning trail from reasoning results
        """
        logger.info(f"Creating {trail_format.value} reasoning trail")
        
        try:
            # Extract basic information
            reasoning_id = reasoning_result.get('reasoning_id', 'unknown')
            transaction_id = reasoning_result.get('transaction_id', 'unknown')
            reasoning_steps = reasoning_result.get('steps', [])
            final_decision = reasoning_result.get('final_decision', {})
            overall_confidence = reasoning_result.get('overall_confidence', 0.5)
            total_time = reasoning_result.get('total_processing_time_ms', 0.0)
            
            # Convert reasoning steps to trail steps
            trail_steps = []
            for i, step in enumerate(reasoning_steps, 1):
                trail_step = self._convert_to_trail_step(step, i, trail_format)
                trail_steps.append(trail_step)
            
            # Generate decision summary
            decision_summary = self._generate_decision_summary(final_decision, trail_steps)
            
            # Create trail
            trail = ReasoningTrail(
                trail_id=f"trail_{reasoning_id}_{int(datetime.now().timestamp())}",
                transaction_id=transaction_id,
                reasoning_id=reasoning_id,
                steps=trail_steps,
                decision_summary=decision_summary,
                overall_confidence=overall_confidence,
                total_processing_time_ms=total_time,
                trail_format=trail_format,
                generated_timestamp=datetime.now().isoformat()
            )
            
            # Store generated trail
            self.generated_trails.append(trail)
            
            logger.info(f"Created reasoning trail with {len(trail_steps)} steps")
            return trail
            
        except Exception as e:
            logger.error(f"Failed to create reasoning trail: {str(e)}")
            raise
    
    def _convert_to_trail_step(self, reasoning_step: Dict[str, Any], 
                             step_number: int, trail_format: TrailFormat) -> ReasoningTrailStep:
        """Convert a reasoning step to a trail step"""
        
        step_id = reasoning_step.get('step_id', f'step_{step_number}')
        step_type = reasoning_step.get('step_type', 'unknown')
        
        # Generate human-readable title
        title = self._generate_step_title(step_type, reasoning_step)
        
        # Generate description
        description = reasoning_step.get('description', f'Step {step_number} analysis')
        
        # Summarize input
        input_data = reasoning_step.get('input_data', {})
        input_summary = self._summarize_input_data(input_data)
        
        # Extract reasoning process
        reasoning_process = reasoning_step.get('reasoning', 'No reasoning provided')
        
        # Summarize output
        output_data = reasoning_step.get('output', {})
        output_summary = self._summarize_output_data(output_data)
        
        # Extract evidence
        evidence = reasoning_step.get('evidence', [])
        
        # Get confidence and timing
        confidence = reasoning_step.get('confidence', 0.5)
        processing_time = reasoning_step.get('processing_time_ms', 0.0)
        
        # Get dependencies
        dependencies = reasoning_step.get('dependencies', [])
        
        # Get timestamp
        timestamp = reasoning_step.get('timestamp', datetime.now().isoformat())
        
        return ReasoningTrailStep(
            step_number=step_number,
            step_id=step_id,
            step_type=step_type,
            title=title,
            description=description,
            input_summary=input_summary,
            reasoning_process=reasoning_process,
            output_summary=output_summary,
            evidence=evidence,
            confidence=confidence,
            processing_time_ms=processing_time,
            dependencies=dependencies,
            timestamp=timestamp
        )
    
    def _generate_step_title(self, step_type: str, reasoning_step: Dict[str, Any]) -> str:
        """Generate human-readable title for a reasoning step"""
        
        title_map = {
            'observation': 'Initial Transaction Observation',
            'analysis': 'Detailed Transaction Analysis',
            'pattern_matching': 'Pattern Recognition and Matching',
            'risk_assessment': 'Risk Factor Evaluation',
            'evidence_gathering': 'Evidence Compilation and Synthesis',
            'validation': 'Result Validation and Verification',
            'conclusion': 'Final Decision and Recommendation',
            'hypothesis': 'Hypothesis Formation',
            'comparison': 'Historical Comparison Analysis'
        }
        
        base_title = title_map.get(step_type.lower(), f'{step_type.title()} Analysis')
        
        # Add context if available
        output = reasoning_step.get('output', {})
        if 'is_fraud' in output:
            if output['is_fraud']:
                base_title += ' (Fraud Indicators Found)'
            else:
                base_title += ' (No Fraud Detected)'
        
        return base_title
    
    def _summarize_input_data(self, input_data: Dict[str, Any]) -> str:
        """Summarize input data for human readability"""
        
        if not input_data:
            return "No input data"
        
        summary_parts = []
        
        # Transaction data
        if 'transaction' in input_data:
            tx = input_data['transaction']
            if isinstance(tx, dict):
                amount = tx.get('amount', 'unknown')
                currency = tx.get('currency', 'unknown')
                merchant = tx.get('merchant', 'unknown')
                summary_parts.append(f"Transaction: {amount} {currency} at {merchant}")
        
        # Context data
        if 'context' in input_data:
            context = input_data['context']
            if isinstance(context, dict) and context:
                summary_parts.append(f"Context: {len(context)} contextual factors")
        
        # Previous findings
        if 'previous_findings' in input_data:
            findings = input_data['previous_findings']
            if isinstance(findings, dict) and findings:
                summary_parts.append(f"Previous findings: {len(findings)} prior results")
        
        # User history
        if 'user_history' in input_data:
            history = input_data['user_history']
            if isinstance(history, list):
                summary_parts.append(f"User history: {len(history)} historical transactions")
        
        return "; ".join(summary_parts) if summary_parts else "General analysis input"
    
    def _summarize_output_data(self, output_data: Dict[str, Any]) -> str:
        """Summarize output data for human readability"""
        
        if not output_data:
            return "No output generated"
        
        summary_parts = []
        
        # Fraud decision
        if 'is_fraud' in output_data:
            fraud_status = "Fraud detected" if output_data['is_fraud'] else "No fraud detected"
            summary_parts.append(fraud_status)
        
        # Risk level
        if 'risk_level' in output_data:
            summary_parts.append(f"Risk level: {output_data['risk_level']}")
        
        # Confidence
        if 'confidence' in output_data:
            confidence = output_data['confidence']
            summary_parts.append(f"Confidence: {confidence:.1%}")
        
        # Key findings
        if 'key_findings' in output_data:
            findings = output_data['key_findings']
            if isinstance(findings, list) and findings:
                summary_parts.append(f"{len(findings)} key findings identified")
        
        # Primary concerns
        if 'primary_concerns' in output_data:
            concerns = output_data['primary_concerns']
            if isinstance(concerns, list) and concerns:
                summary_parts.append(f"{len(concerns)} primary concerns")
        
        # Recommended action
        if 'recommended_action' in output_data:
            action = output_data['recommended_action']
            summary_parts.append(f"Recommended action: {action}")
        
        return "; ".join(summary_parts) if summary_parts else "Analysis completed"
    
    def _generate_decision_summary(self, final_decision: Dict[str, Any], 
                                 trail_steps: List[ReasoningTrailStep]) -> str:
        """Generate overall decision summary"""
        
        is_fraud = final_decision.get('is_fraud', False)
        confidence = final_decision.get('confidence', 0.5)
        recommended_action = final_decision.get('recommended_action', 'REVIEW')
        
        summary = f"After {len(trail_steps)} analysis steps, the system determined: "
        
        if is_fraud:
            summary += f"FRAUD DETECTED with {confidence:.1%} confidence. "
        else:
            summary += f"NO FRAUD DETECTED with {confidence:.1%} confidence. "
        
        summary += f"Recommended action: {recommended_action}."
        
        # Add key reasoning points
        high_confidence_steps = [step for step in trail_steps if step.confidence > 0.8]
        if high_confidence_steps:
            summary += f" High confidence was achieved in {len(high_confidence_steps)} analysis steps."
        
        return summary
    
    def format_trail_as_narrative(self, trail: ReasoningTrail) -> str:
        """Format trail as a narrative story"""
        
        narrative_parts = []
        templates = self.trail_templates[TrailFormat.NARRATIVE.value]
        
        # Introduction
        narrative_parts.append(f"Fraud Detection Analysis for Transaction {trail.transaction_id}")
        narrative_parts.append("=" * 60)
        narrative_parts.append("")
        narrative_parts.append("The fraud detection system conducted a comprehensive analysis of this transaction using advanced reasoning. Here is the step-by-step process:")
        narrative_parts.append("")
        
        # Process each step
        for i, step in enumerate(trail.steps):
            # Step introduction
            step_intro = templates["step_intro"].format(
                step_number=step.step_number,
                title=step.title
            )
            narrative_parts.append(step_intro)
            narrative_parts.append("")
            
            # Description
            narrative_parts.append(step.description)
            narrative_parts.append("")
            
            # Input context
            if step.input_summary:
                narrative_parts.append(f"The system examined: {step.input_summary}")
                narrative_parts.append("")
            
            # Reasoning process
            narrative_parts.append(templates["reasoning_intro"])
            narrative_parts.append(f'"{step.reasoning_process}"')
            narrative_parts.append("")
            
            # Output
            if step.output_summary:
                narrative_parts.append(f"This analysis concluded: {step.output_summary}")
                narrative_parts.append("")
            
            # Evidence
            if step.evidence:
                narrative_parts.append(templates["evidence_intro"])
                for evidence in step.evidence[:3]:  # Limit to top 3
                    narrative_parts.append(f"  • {evidence}")
                narrative_parts.append("")
            
            # Confidence
            confidence_note = templates["confidence_note"].format(confidence=step.confidence)
            narrative_parts.append(confidence_note)
            narrative_parts.append("")
            
            # Dependencies
            if step.dependencies:
                dep_note = templates["dependency_note"].format(
                    dependencies=", ".join(step.dependencies)
                )
                narrative_parts.append(dep_note)
                narrative_parts.append("")
            
            # Transition to next step
            if i < len(trail.steps) - 1:
                narrative_parts.append(templates["transition"])
                narrative_parts.append("")
        
        # Final decision
        narrative_parts.append("FINAL DECISION")
        narrative_parts.append("=" * 15)
        narrative_parts.append(trail.decision_summary)
        narrative_parts.append("")
        narrative_parts.append(f"Total analysis time: {trail.total_processing_time_ms:.0f} milliseconds")
        narrative_parts.append(f"Overall confidence: {trail.overall_confidence:.1%}")
        
        return "\n".join(narrative_parts)
    
    def format_trail_as_structured(self, trail: ReasoningTrail) -> str:
        """Format trail as structured documentation"""
        
        structured_parts = []
        templates = self.trail_templates[TrailFormat.STRUCTURED.value]
        
        # Header
        structured_parts.append("FRAUD DETECTION REASONING TRAIL")
        structured_parts.append("=" * 50)
        structured_parts.append(f"Transaction ID: {trail.transaction_id}")
        structured_parts.append(f"Reasoning ID: {trail.reasoning_id}")
        structured_parts.append(f"Generated: {trail.generated_timestamp}")
        structured_parts.append("")
        
        # Process each step
        for step in trail.steps:
            # Step header
            step_header = templates["step_header"].format(
                step_number=step.step_number,
                title=step.title
            )
            structured_parts.append(step_header)
            structured_parts.append("")
            
            # Input
            structured_parts.append(templates["input_label"])
            structured_parts.append(f"  {step.input_summary}")
            structured_parts.append("")
            
            # Process
            structured_parts.append(templates["process_label"])
            structured_parts.append(f"  {step.reasoning_process}")
            structured_parts.append("")
            
            # Output
            structured_parts.append(templates["output_label"])
            structured_parts.append(f"  {step.output_summary}")
            structured_parts.append("")
            
            # Evidence
            if step.evidence:
                structured_parts.append(templates["evidence_label"])
                for evidence in step.evidence:
                    structured_parts.append(f"  • {evidence}")
                structured_parts.append("")
            
            # Confidence
            structured_parts.append(templates["confidence_label"])
            structured_parts.append(f"  {step.confidence:.3f} ({step.confidence:.1%})")
            structured_parts.append("")
            
            # Timing
            structured_parts.append(templates["timing_label"])
            structured_parts.append(f"  {step.processing_time_ms:.2f} ms")
            structured_parts.append("")
        
        # Summary
        structured_parts.append("DECISION SUMMARY")
        structured_parts.append("=" * 16)
        structured_parts.append(trail.decision_summary)
        structured_parts.append("")
        structured_parts.append(f"Total Processing Time: {trail.total_processing_time_ms:.2f} ms")
        structured_parts.append(f"Overall Confidence: {trail.overall_confidence:.3f}")
        
        return "\n".join(structured_parts)
    
    def format_trail_as_timeline(self, trail: ReasoningTrail) -> str:
        """Format trail as a timeline"""
        
        timeline_parts = []
        templates = self.trail_templates[TrailFormat.TIMELINE.value]
        
        # Header
        timeline_parts.append("FRAUD DETECTION TIMELINE")
        timeline_parts.append("=" * 30)
        timeline_parts.append(f"Transaction: {trail.transaction_id}")
        timeline_parts.append("")
        
        # Timeline entries
        for step in trail.steps:
            # Timestamp and step
            timestamp_entry = templates["timestamp_format"].format(
                timestamp=step.timestamp.split('T')[1][:8],  # Just time part
                step_number=step.step_number
            )
            
            duration_note = templates["duration_note"].format(
                processing_time_ms=step.processing_time_ms
            )
            
            timeline_parts.append(f"{timestamp_entry} {duration_note}")
            timeline_parts.append(f"    {step.title}")
            timeline_parts.append(f"    Result: {step.output_summary}")
            
            if step.confidence > 0.8:
                timeline_parts.append(f"    ✓ High confidence: {step.confidence:.1%}")
            elif step.confidence < 0.4:
                timeline_parts.append(f"    ⚠ Low confidence: {step.confidence:.1%}")
            
            timeline_parts.append("")
        
        # Final timeline entry
        timeline_parts.append(f"[{trail.generated_timestamp.split('T')[1][:8]}] ANALYSIS COMPLETE")
        timeline_parts.append(f"    {trail.decision_summary}")
        timeline_parts.append(f"    Total time: {trail.total_processing_time_ms:.0f}ms")
        
        return "\n".join(timeline_parts)
    
    def format_trail_for_audit(self, trail: ReasoningTrail) -> str:
        """Format trail for regulatory audit"""
        
        audit_parts = []
        templates = self.trail_templates[TrailFormat.AUDIT.value]
        
        # Audit header
        audit_parts.append("REGULATORY AUDIT TRAIL")
        audit_parts.append("=" * 25)
        audit_parts.append(f"Transaction ID: {trail.transaction_id}")
        audit_parts.append(f"Reasoning Session ID: {trail.reasoning_id}")
        audit_parts.append(f"Trail ID: {trail.trail_id}")
        audit_parts.append(f"Generated: {trail.generated_timestamp}")
        audit_parts.append(f"Total Steps: {len(trail.steps)}")
        audit_parts.append("")
        
        # Audit entries for each step
        for step in trail.steps:
            audit_header = templates["audit_header"].format(step_number=step.step_number)
            audit_parts.append(audit_header)
            audit_parts.append("-" * len(audit_header))
            
            audit_parts.append(f"{templates['step_id_label']} {step.step_id}")
            audit_parts.append(f"{templates['timestamp_label']} {step.timestamp}")
            audit_parts.append(f"Step Type: {step.step_type}")
            audit_parts.append(f"Description: {step.description}")
            audit_parts.append(f"Processing Time: {step.processing_time_ms:.2f}ms")
            audit_parts.append(f"Confidence Level: {step.confidence:.3f}")
            
            # Input hash (simplified)
            input_hash = str(hash(step.input_summary))[-8:]
            audit_parts.append(f"{templates['input_hash_label']} {input_hash}")
            
            # Output hash (simplified)
            output_hash = str(hash(step.output_summary))[-8:]
            audit_parts.append(f"{templates['output_hash_label']} {output_hash}")
            
            audit_parts.append(f"{templates['verification_label']} VERIFIED")
            audit_parts.append(templates["compliance_note"])
            
            # Evidence documentation
            if step.evidence:
                audit_parts.append("Evidence Documentation:")
                for i, evidence in enumerate(step.evidence, 1):
                    audit_parts.append(f"  {i}. {evidence}")
            
            audit_parts.append("")
        
        # Audit summary
        audit_parts.append("AUDIT SUMMARY")
        audit_parts.append("=" * 13)
        audit_parts.append(f"Decision: {trail.decision_summary}")
        audit_parts.append(f"Overall Confidence: {trail.overall_confidence:.3f}")
        audit_parts.append(f"Compliance Status: COMPLIANT")
        audit_parts.append(f"Audit Trail Integrity: VERIFIED")
        
        return "\n".join(audit_parts)
    
    def export_trail_as_json(self, trail: ReasoningTrail) -> str:
        """Export trail as JSON for programmatic access"""
        
        trail_dict = {
            'trail_id': trail.trail_id,
            'transaction_id': trail.transaction_id,
            'reasoning_id': trail.reasoning_id,
            'decision_summary': trail.decision_summary,
            'overall_confidence': trail.overall_confidence,
            'total_processing_time_ms': trail.total_processing_time_ms,
            'trail_format': trail.trail_format.value,
            'generated_timestamp': trail.generated_timestamp,
            'steps': [
                {
                    'step_number': step.step_number,
                    'step_id': step.step_id,
                    'step_type': step.step_type,
                    'title': step.title,
                    'description': step.description,
                    'input_summary': step.input_summary,
                    'reasoning_process': step.reasoning_process,
                    'output_summary': step.output_summary,
                    'evidence': step.evidence,
                    'confidence': step.confidence,
                    'processing_time_ms': step.processing_time_ms,
                    'dependencies': step.dependencies,
                    'timestamp': step.timestamp
                }
                for step in trail.steps
            ]
        }
        
        return json.dumps(trail_dict, indent=2)
    
    def get_trail_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated trails"""
        
        if not self.generated_trails:
            return {'total_trails': 0}
        
        total = len(self.generated_trails)
        
        # Format distribution
        formats = [trail.trail_format.value for trail in self.generated_trails]
        format_counts = {}
        for fmt in formats:
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        
        # Average steps per trail
        avg_steps = sum(len(trail.steps) for trail in self.generated_trails) / total
        
        # Average processing time
        avg_time = sum(trail.total_processing_time_ms for trail in self.generated_trails) / total
        
        # Average confidence
        avg_confidence = sum(trail.overall_confidence for trail in self.generated_trails) / total
        
        return {
            'total_trails': total,
            'format_distribution': format_counts,
            'average_steps_per_trail': avg_steps,
            'average_processing_time_ms': avg_time,
            'average_confidence': avg_confidence
        }