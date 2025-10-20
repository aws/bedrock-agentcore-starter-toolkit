"""
Decision Explanation Interface

Interactive interface for exploring fraud detection decisions with:
- Human-readable explanation generation
- Interactive drill-down capabilities
- Visual decision logic representation
- Export functionality for regulatory reporting
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from src.explanation_generator import ExplanationGenerator, ExplanationStyle, ExplanationLevel, ExplanationReport
from src.reasoning_trail import ReasoningTrailFormatter, TrailFormat, ReasoningTrail
from src.audit_trail import AuditTrailSystem, AuditEventType, AuditSeverity


class ExportFormat(Enum):
    """Export format options"""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass
class DecisionExplanation:
    """Complete decision explanation with all components"""
    transaction_id: str
    explanation_report: ExplanationReport
    reasoning_trail: ReasoningTrail
    audit_entries: List[Dict[str, Any]]
    visual_data: Dict[str, Any]
    generated_timestamp: str


class DecisionExplanationInterface:
    """
    Interactive interface for decision explanations with drill-down
    and export capabilities
    """
    
    def __init__(self, audit_system: Optional[AuditTrailSystem] = None):
        """
        Initialize decision explanation interface
        
        Args:
            audit_system: Optional audit trail system for logging
        """
        self.explanation_generator = ExplanationGenerator()
        self.trail_formatter = ReasoningTrailFormatter()
        self.audit_system = audit_system
        self.explanations_cache: Dict[str, DecisionExplanation] = {}
        
    def generate_complete_explanation(
        self,
        reasoning_result: Dict[str, Any],
        style: ExplanationStyle = ExplanationStyle.BUSINESS,
        level: ExplanationLevel = ExplanationLevel.DETAILED,
        include_audit: bool = True
    ) -> DecisionExplanation:
        """
        Generate complete explanation with all components
        
        Args:
            reasoning_result: Reasoning analysis result
            style: Explanation style for audience
            level: Detail level
            include_audit: Include audit trail entries
            
        Returns:
            Complete decision explanation
        """
        transaction_id = reasoning_result.get('transaction_id', 'unknown')
        
        # Generate explanation report
        explanation_report = self.explanation_generator.generate_explanation(
            reasoning_result, style, level
        )
        
        # Generate reasoning trail
        reasoning_trail = self.trail_formatter.create_reasoning_trail(
            reasoning_result, TrailFormat.NARRATIVE
        )
        
        # Get audit entries if available
        audit_entries = []
        if include_audit and self.audit_system:
            audit_entries = self.audit_system.search_entries(
                transaction_id=transaction_id
            )
        
        # Generate visual data
        visual_data = self._generate_visual_data(reasoning_result, explanation_report)
        
        # Create complete explanation
        explanation = DecisionExplanation(
            transaction_id=transaction_id,
            explanation_report=explanation_report,
            reasoning_trail=reasoning_trail,
            audit_entries=audit_entries,
            visual_data=visual_data,
            generated_timestamp=datetime.now().isoformat()
        )
        
        # Cache explanation
        self.explanations_cache[transaction_id] = explanation
        
        # Log to audit if available
        if self.audit_system:
            self.audit_system.log_event(
                event_type=AuditEventType.AGENT_ACTION,
                severity=AuditSeverity.INFO,
                action="Generated decision explanation",
                details={
                    "style": style.value,
                    "level": level.value,
                    "sections": len(explanation_report.sections)
                },
                transaction_id=transaction_id,
                agent_id="explanation_interface"
            )
        
        return explanation
    
    def _generate_visual_data(
        self,
        reasoning_result: Dict[str, Any],
        explanation_report: ExplanationReport
    ) -> Dict[str, Any]:
        """Generate data for visual representations"""
        
        steps = reasoning_result.get('steps', [])
        final_decision = reasoning_result.get('final_decision', {})
        
        # Decision flow data
        decision_flow = {
            "nodes": [],
            "edges": []
        }
        
        for i, step in enumerate(steps):
            node = {
                "id": f"step_{i}",
                "label": step.get('step_type', 'Analysis'),
                "confidence": step.get('confidence', 0.5),
                "output": step.get('output', {})
            }
            decision_flow["nodes"].append(node)
            
            if i > 0:
                edge = {
                    "from": f"step_{i-1}",
                    "to": f"step_{i}",
                    "label": "leads to"
                }
                decision_flow["edges"].append(edge)
        
        # Confidence progression
        confidence_progression = [
            {
                "step": i + 1,
                "confidence": step.get('confidence', 0.5),
                "step_type": step.get('step_type', 'unknown')
            }
            for i, step in enumerate(steps)
        ]
        
        # Risk factors breakdown
        risk_factors = []
        for step in steps:
            output = step.get('output', {})
            if 'risk_factors' in output:
                for factor in output['risk_factors']:
                    risk_factors.append({
                        "factor": factor,
                        "source_step": step.get('step_type', 'unknown')
                    })
        
        # Evidence hierarchy
        evidence_hierarchy = {
            "high_confidence": [],
            "medium_confidence": [],
            "low_confidence": []
        }
        
        for step in steps:
            confidence = step.get('confidence', 0.5)
            evidence = step.get('evidence', [])
            
            if confidence >= 0.8:
                evidence_hierarchy["high_confidence"].extend(evidence)
            elif confidence >= 0.5:
                evidence_hierarchy["medium_confidence"].extend(evidence)
            else:
                evidence_hierarchy["low_confidence"].extend(evidence)
        
        return {
            "decision_flow": decision_flow,
            "confidence_progression": confidence_progression,
            "risk_factors": risk_factors,
            "evidence_hierarchy": evidence_hierarchy,
            "final_decision": {
                "decision": final_decision.get('recommended_action', 'REVIEW'),
                "confidence": final_decision.get('confidence', 0.5),
                "risk_level": final_decision.get('risk_level', 'MEDIUM')
            }
        }
    
    def get_interactive_explanation(
        self,
        transaction_id: str,
        drill_down_path: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get interactive explanation with drill-down capability
        
        Args:
            transaction_id: Transaction ID
            drill_down_path: Path for drilling down (e.g., ['section_2', 'evidence'])
            
        Returns:
            Interactive explanation data
        """
        if transaction_id not in self.explanations_cache:
            return {"error": "Explanation not found"}
        
        explanation = self.explanations_cache[transaction_id]
        
        # Base interactive data
        interactive_data = {
            "transaction_id": transaction_id,
            "summary": explanation.explanation_report.executive_summary,
            "decision": explanation.explanation_report.decision,
            "confidence": explanation.explanation_report.confidence,
            "sections": []
        }
        
        # Add sections with drill-down capability
        for i, section in enumerate(explanation.explanation_report.sections):
            section_data = {
                "id": f"section_{i}",
                "title": section.title,
                "summary": section.content[:200] + "..." if len(section.content) > 200 else section.content,
                "full_content": section.content,
                "importance": section.importance,
                "confidence": section.confidence,
                "evidence_count": len(section.evidence),
                "can_drill_down": len(section.evidence) > 0
            }
            interactive_data["sections"].append(section_data)
        
        # Handle drill-down
        if drill_down_path:
            drill_down_data = self._handle_drill_down(explanation, drill_down_path)
            interactive_data["drill_down"] = drill_down_data
        
        return interactive_data
    
    def _handle_drill_down(
        self,
        explanation: DecisionExplanation,
        drill_down_path: List[str]
    ) -> Dict[str, Any]:
        """Handle drill-down into specific explanation components"""
        
        if not drill_down_path:
            return {}
        
        target = drill_down_path[0]
        
        # Drill into specific section
        if target.startswith("section_"):
            section_idx = int(target.split("_")[1])
            if section_idx < len(explanation.explanation_report.sections):
                section = explanation.explanation_report.sections[section_idx]
                return {
                    "type": "section_detail",
                    "title": section.title,
                    "content": section.content,
                    "evidence": section.evidence,
                    "confidence": section.confidence,
                    "importance": section.importance
                }
        
        # Drill into reasoning steps
        elif target == "reasoning_steps":
            return {
                "type": "reasoning_detail",
                "steps": [
                    {
                        "step_number": step.step_number,
                        "title": step.title,
                        "reasoning": step.reasoning_process,
                        "confidence": step.confidence,
                        "evidence": step.evidence
                    }
                    for step in explanation.reasoning_trail.steps
                ]
            }
        
        # Drill into evidence
        elif target == "evidence":
            all_evidence = []
            for section in explanation.explanation_report.sections:
                for evidence in section.evidence:
                    all_evidence.append({
                        "evidence": evidence,
                        "section": section.title,
                        "confidence": section.confidence
                    })
            return {
                "type": "evidence_detail",
                "evidence_items": all_evidence
            }
        
        # Drill into visual data
        elif target == "visual":
            return {
                "type": "visual_detail",
                "visual_data": explanation.visual_data
            }
        
        return {"error": "Invalid drill-down path"}
    
    def generate_visual_representation(
        self,
        transaction_id: str,
        visualization_type: str = "decision_tree"
    ) -> str:
        """
        Generate visual representation of decision logic
        
        Args:
            transaction_id: Transaction ID
            visualization_type: Type of visualization (decision_tree, flow_chart, confidence_graph)
            
        Returns:
            Visual representation (Mermaid diagram syntax)
        """
        if transaction_id not in self.explanations_cache:
            return "Error: Explanation not found"
        
        explanation = self.explanations_cache[transaction_id]
        
        if visualization_type == "decision_tree":
            return self._generate_decision_tree(explanation)
        elif visualization_type == "flow_chart":
            return self._generate_flow_chart(explanation)
        elif visualization_type == "confidence_graph":
            return self._generate_confidence_graph(explanation)
        else:
            return "Error: Unknown visualization type"
    
    def _generate_decision_tree(self, explanation: DecisionExplanation) -> str:
        """Generate Mermaid decision tree diagram"""
        
        lines = ["graph TD"]
        lines.append(f"    Start[Transaction Analysis] --> Decision{{Final Decision}}")
        
        for i, step in enumerate(explanation.reasoning_trail.steps):
            node_id = f"Step{i}"
            label = step.title.replace(" ", "_")
            confidence = f"{step.confidence:.0%}"
            
            lines.append(f"    Start --> {node_id}[{label}<br/>Confidence: {confidence}]")
            lines.append(f"    {node_id} --> Decision")
        
        decision = explanation.explanation_report.decision
        lines.append(f"    Decision --> Result[{decision}]")
        
        return "\n".join(lines)
    
    def _generate_flow_chart(self, explanation: DecisionExplanation) -> str:
        """Generate Mermaid flow chart"""
        
        lines = ["flowchart LR"]
        
        for i, step in enumerate(explanation.reasoning_trail.steps):
            node_id = f"S{i}"
            label = step.title[:30]
            
            if i == 0:
                lines.append(f"    Start([Start]) --> {node_id}[{label}]")
            else:
                prev_id = f"S{i-1}"
                lines.append(f"    {prev_id} --> {node_id}[{label}]")
        
        last_id = f"S{len(explanation.reasoning_trail.steps)-1}"
        decision = explanation.explanation_report.decision
        lines.append(f"    {last_id} --> End([{decision}])")
        
        return "\n".join(lines)
    
    def _generate_confidence_graph(self, explanation: DecisionExplanation) -> str:
        """Generate confidence progression visualization"""
        
        lines = ["graph LR"]
        
        for i, step in enumerate(explanation.reasoning_trail.steps):
            confidence = step.confidence
            node_id = f"C{i}"
            
            # Color based on confidence
            if confidence >= 0.8:
                style = "fill:#90EE90"
            elif confidence >= 0.5:
                style = "fill:#FFD700"
            else:
                style = "fill:#FFB6C1"
            
            lines.append(f"    {node_id}[Step {i+1}<br/>{confidence:.0%}]")
            lines.append(f"    style {node_id} {style}")
            
            if i > 0:
                prev_id = f"C{i-1}"
                lines.append(f"    {prev_id} --> {node_id}")
        
        return "\n".join(lines)

    def export_explanation(
        self,
        transaction_id: str,
        export_format: ExportFormat,
        output_file: Optional[str] = None,
        include_visuals: bool = True
    ) -> str:
        """
        Export explanation for regulatory reporting
        
        Args:
            transaction_id: Transaction ID
            export_format: Export format
            output_file: Optional output file path
            include_visuals: Include visual representations
            
        Returns:
            Exported content or file path
        """
        if transaction_id not in self.explanations_cache:
            return "Error: Explanation not found"
        
        explanation = self.explanations_cache[transaction_id]
        
        if export_format == ExportFormat.JSON:
            content = self._export_as_json(explanation)
        elif export_format == ExportFormat.HTML:
            content = self._export_as_html(explanation, include_visuals)
        elif export_format == ExportFormat.TEXT:
            content = self._export_as_text(explanation)
        elif export_format == ExportFormat.MARKDOWN:
            content = self._export_as_markdown(explanation, include_visuals)
        else:
            return "Error: Unsupported export format"
        
        # Write to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Exported to {output_file}"
        
        return content
    
    def _export_as_json(self, explanation: DecisionExplanation) -> str:
        """Export as JSON"""
        
        export_data = {
            "transaction_id": explanation.transaction_id,
            "generated_timestamp": explanation.generated_timestamp,
            "explanation": {
                "decision": explanation.explanation_report.decision,
                "confidence": explanation.explanation_report.confidence,
                "risk_level": explanation.explanation_report.risk_level,
                "executive_summary": explanation.explanation_report.executive_summary,
                "sections": [
                    {
                        "title": section.title,
                        "content": section.content,
                        "evidence": section.evidence,
                        "confidence": section.confidence,
                        "importance": section.importance
                    }
                    for section in explanation.explanation_report.sections
                ],
                "key_factors": explanation.explanation_report.key_factors,
                "recommendations": explanation.explanation_report.recommendations
            },
            "reasoning_trail": {
                "steps": [
                    {
                        "step_number": step.step_number,
                        "title": step.title,
                        "reasoning": step.reasoning_process,
                        "confidence": step.confidence,
                        "evidence": step.evidence
                    }
                    for step in explanation.reasoning_trail.steps
                ],
                "decision_summary": explanation.reasoning_trail.decision_summary
            },
            "visual_data": explanation.visual_data
        }
        
        return json.dumps(export_data, indent=2)
    
    def _export_as_html(self, explanation: DecisionExplanation, include_visuals: bool) -> str:
        """Export as HTML"""
        
        html_parts = []
        
        # HTML header
        html_parts.append("<!DOCTYPE html>")
        html_parts.append("<html>")
        html_parts.append("<head>")
        html_parts.append("<meta charset='UTF-8'>")
        html_parts.append("<title>Fraud Detection Explanation</title>")
        html_parts.append("<style>")
        html_parts.append("body { font-family: Arial, sans-serif; margin: 40px; }")
        html_parts.append("h1 { color: #333; }")
        html_parts.append("h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }")
        html_parts.append(".summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; }")
        html_parts.append(".decision { font-size: 24px; font-weight: bold; color: #2c3e50; }")
        html_parts.append(".confidence { color: #27ae60; }")
        html_parts.append(".section { margin: 30px 0; }")
        html_parts.append(".evidence { background: #e8f5e9; padding: 10px; margin: 10px 0; border-left: 4px solid #4caf50; }")
        html_parts.append(".evidence-item { margin: 5px 0; }")
        html_parts.append("</style>")
        html_parts.append("</head>")
        html_parts.append("<body>")
        
        # Title
        html_parts.append(f"<h1>Fraud Detection Explanation</h1>")
        html_parts.append(f"<p><strong>Transaction ID:</strong> {explanation.transaction_id}</p>")
        html_parts.append(f"<p><strong>Generated:</strong> {explanation.generated_timestamp}</p>")
        
        # Summary
        html_parts.append("<div class='summary'>")
        html_parts.append(f"<div class='decision'>Decision: {explanation.explanation_report.decision}</div>")
        html_parts.append(f"<p class='confidence'>Confidence: {explanation.explanation_report.confidence:.1%}</p>")
        html_parts.append(f"<p><strong>Risk Level:</strong> {explanation.explanation_report.risk_level}</p>")
        html_parts.append(f"<p>{explanation.explanation_report.executive_summary}</p>")
        html_parts.append("</div>")
        
        # Sections
        for section in explanation.explanation_report.sections:
            html_parts.append("<div class='section'>")
            html_parts.append(f"<h2>{section.title}</h2>")
            html_parts.append(f"<p>{section.content}</p>")
            
            if section.evidence:
                html_parts.append("<div class='evidence'>")
                html_parts.append("<strong>Evidence:</strong>")
                for evidence in section.evidence:
                    html_parts.append(f"<div class='evidence-item'>• {evidence}</div>")
                html_parts.append("</div>")
            
            html_parts.append("</div>")
        
        # Key Factors
        if explanation.explanation_report.key_factors:
            html_parts.append("<h2>Key Factors</h2>")
            html_parts.append("<ul>")
            for factor in explanation.explanation_report.key_factors:
                html_parts.append(f"<li>{factor}</li>")
            html_parts.append("</ul>")
        
        # Recommendations
        if explanation.explanation_report.recommendations:
            html_parts.append("<h2>Recommendations</h2>")
            html_parts.append("<ul>")
            for rec in explanation.explanation_report.recommendations:
                html_parts.append(f"<li>{rec}</li>")
            html_parts.append("</ul>")
        
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        return "\n".join(html_parts)
    
    def _export_as_text(self, explanation: DecisionExplanation) -> str:
        """Export as plain text"""
        
        text_parts = []
        
        # Header
        text_parts.append("=" * 80)
        text_parts.append("FRAUD DETECTION EXPLANATION")
        text_parts.append("=" * 80)
        text_parts.append(f"Transaction ID: {explanation.transaction_id}")
        text_parts.append(f"Generated: {explanation.generated_timestamp}")
        text_parts.append("")
        
        # Summary
        text_parts.append("DECISION SUMMARY")
        text_parts.append("-" * 80)
        text_parts.append(f"Decision: {explanation.explanation_report.decision}")
        text_parts.append(f"Confidence: {explanation.explanation_report.confidence:.1%}")
        text_parts.append(f"Risk Level: {explanation.explanation_report.risk_level}")
        text_parts.append("")
        text_parts.append(explanation.explanation_report.executive_summary)
        text_parts.append("")
        
        # Sections
        for section in explanation.explanation_report.sections:
            text_parts.append(section.title.upper())
            text_parts.append("-" * 80)
            text_parts.append(section.content)
            
            if section.evidence:
                text_parts.append("")
                text_parts.append("Evidence:")
                for evidence in section.evidence:
                    text_parts.append(f"  • {evidence}")
            
            text_parts.append("")
        
        # Key Factors
        if explanation.explanation_report.key_factors:
            text_parts.append("KEY FACTORS")
            text_parts.append("-" * 80)
            for factor in explanation.explanation_report.key_factors:
                text_parts.append(f"  • {factor}")
            text_parts.append("")
        
        # Recommendations
        if explanation.explanation_report.recommendations:
            text_parts.append("RECOMMENDATIONS")
            text_parts.append("-" * 80)
            for rec in explanation.explanation_report.recommendations:
                text_parts.append(f"  • {rec}")
            text_parts.append("")
        
        return "\n".join(text_parts)
    
    def _export_as_markdown(self, explanation: DecisionExplanation, include_visuals: bool) -> str:
        """Export as Markdown"""
        
        md_parts = []
        
        # Title
        md_parts.append("# Fraud Detection Explanation")
        md_parts.append("")
        md_parts.append(f"**Transaction ID:** {explanation.transaction_id}")
        md_parts.append(f"**Generated:** {explanation.generated_timestamp}")
        md_parts.append("")
        
        # Summary
        md_parts.append("## Decision Summary")
        md_parts.append("")
        md_parts.append(f"- **Decision:** {explanation.explanation_report.decision}")
        md_parts.append(f"- **Confidence:** {explanation.explanation_report.confidence:.1%}")
        md_parts.append(f"- **Risk Level:** {explanation.explanation_report.risk_level}")
        md_parts.append("")
        md_parts.append(explanation.explanation_report.executive_summary)
        md_parts.append("")
        
        # Sections
        for section in explanation.explanation_report.sections:
            md_parts.append(f"## {section.title}")
            md_parts.append("")
            md_parts.append(section.content)
            md_parts.append("")
            
            if section.evidence:
                md_parts.append("**Evidence:**")
                md_parts.append("")
                for evidence in section.evidence:
                    md_parts.append(f"- {evidence}")
                md_parts.append("")
        
        # Key Factors
        if explanation.explanation_report.key_factors:
            md_parts.append("## Key Factors")
            md_parts.append("")
            for factor in explanation.explanation_report.key_factors:
                md_parts.append(f"- {factor}")
            md_parts.append("")
        
        # Recommendations
        if explanation.explanation_report.recommendations:
            md_parts.append("## Recommendations")
            md_parts.append("")
            for rec in explanation.explanation_report.recommendations:
                md_parts.append(f"- {rec}")
            md_parts.append("")
        
        # Visual representations
        if include_visuals:
            md_parts.append("## Decision Flow")
            md_parts.append("")
            md_parts.append("```mermaid")
            md_parts.append(self._generate_flow_chart(explanation))
            md_parts.append("```")
            md_parts.append("")
        
        return "\n".join(md_parts)
    
    def compare_explanations(
        self,
        transaction_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare explanations across multiple transactions
        
        Args:
            transaction_ids: List of transaction IDs to compare
            
        Returns:
            Comparison data
        """
        comparisons = {
            "transactions": [],
            "common_factors": [],
            "decision_distribution": {},
            "confidence_comparison": []
        }
        
        all_factors = []
        
        for txn_id in transaction_ids:
            if txn_id in self.explanations_cache:
                explanation = self.explanations_cache[txn_id]
                
                comparisons["transactions"].append({
                    "transaction_id": txn_id,
                    "decision": explanation.explanation_report.decision,
                    "confidence": explanation.explanation_report.confidence,
                    "risk_level": explanation.explanation_report.risk_level,
                    "key_factors": explanation.explanation_report.key_factors
                })
                
                # Collect factors
                all_factors.extend(explanation.explanation_report.key_factors)
                
                # Decision distribution
                decision = explanation.explanation_report.decision
                comparisons["decision_distribution"][decision] = \
                    comparisons["decision_distribution"].get(decision, 0) + 1
                
                # Confidence comparison
                comparisons["confidence_comparison"].append({
                    "transaction_id": txn_id,
                    "confidence": explanation.explanation_report.confidence
                })
        
        # Find common factors
        from collections import Counter
        factor_counts = Counter(all_factors)
        comparisons["common_factors"] = [
            {"factor": factor, "count": count}
            for factor, count in factor_counts.most_common(10)
        ]
        
        return comparisons
    
    def get_explanation_summary(self) -> Dict[str, Any]:
        """Get summary of all generated explanations"""
        
        if not self.explanations_cache:
            return {"total_explanations": 0}
        
        total = len(self.explanations_cache)
        
        # Decision distribution
        decisions = {}
        risk_levels = {}
        avg_confidence = 0
        
        for explanation in self.explanations_cache.values():
            decision = explanation.explanation_report.decision
            decisions[decision] = decisions.get(decision, 0) + 1
            
            risk_level = explanation.explanation_report.risk_level
            risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
            
            avg_confidence += explanation.explanation_report.confidence
        
        avg_confidence /= total if total > 0 else 1
        
        return {
            "total_explanations": total,
            "decision_distribution": decisions,
            "risk_level_distribution": risk_levels,
            "average_confidence": avg_confidence,
            "cached_transactions": list(self.explanations_cache.keys())
        }

    
    def export_explanation(
        self,
        transaction_id: str,
        export_format: ExportFormat,
        output_file: str,
        include_visuals: bool = True
    ) -> bool:
        """
        Export explanation for regulatory reporting
        
        Args:
            transaction_id: Transaction ID
            export_format: Export format
            output_file: Output file path
            include_visuals: Include visual representations
            
        Returns:
            Success status
        """
        if transaction_id not in self.explanations_cache:
            return False
        
        explanation = self.explanations_cache[transaction_id]
        
        try:
            if export_format == ExportFormat.JSON:
                self._export_as_json(explanation, output_file)
            elif export_format == ExportFormat.TEXT:
                self._export_as_text(explanation, output_file)
            elif export_format == ExportFormat.MARKDOWN:
                self._export_as_markdown(explanation, output_file, include_visuals)
            elif export_format == ExportFormat.HTML:
                self._export_as_html(explanation, output_file, include_visuals)
            else:
                return False
            
            # Log export to audit
            if self.audit_system:
                self.audit_system.log_event(
                    event_type=AuditEventType.AGENT_ACTION,
                    severity=AuditSeverity.COMPLIANCE,
                    action="Exported decision explanation",
                    details={
                        "format": export_format.value,
                        "output_file": output_file,
                        "include_visuals": include_visuals
                    },
                    transaction_id=transaction_id,
                    agent_id="explanation_interface"
                )
            
            return True
            
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def _export_as_json(self, explanation: DecisionExplanation, output_file: str):
        """Export as JSON"""
        export_data = {
            "transaction_id": explanation.transaction_id,
            "generated_timestamp": explanation.generated_timestamp,
            "explanation_report": {
                "decision": explanation.explanation_report.decision,
                "confidence": explanation.explanation_report.confidence,
                "risk_level": explanation.explanation_report.risk_level,
                "executive_summary": explanation.explanation_report.executive_summary,
                "sections": [
                    {
                        "title": s.title,
                        "content": s.content,
                        "importance": s.importance,
                        "evidence": s.evidence,
                        "confidence": s.confidence
                    }
                    for s in explanation.explanation_report.sections
                ],
                "key_factors": explanation.explanation_report.key_factors,
                "recommendations": explanation.explanation_report.recommendations
            },
            "reasoning_trail": {
                "steps": [
                    {
                        "step_number": s.step_number,
                        "title": s.title,
                        "reasoning": s.reasoning_process,
                        "confidence": s.confidence
                    }
                    for s in explanation.reasoning_trail.steps
                ]
            },
            "visual_data": explanation.visual_data
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def _export_as_text(self, explanation: DecisionExplanation, output_file: str):
        """Export as plain text"""
        lines = []
        
        lines.append("=" * 80)
        lines.append("FRAUD DETECTION DECISION EXPLANATION")
        lines.append("=" * 80)
        lines.append(f"Transaction ID: {explanation.transaction_id}")
        lines.append(f"Generated: {explanation.generated_timestamp}")
        lines.append("")
        
        # Executive summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(explanation.explanation_report.executive_summary)
        lines.append("")
        
        # Decision
        lines.append("DECISION")
        lines.append("-" * 80)
        lines.append(f"Decision: {explanation.explanation_report.decision}")
        lines.append(f"Confidence: {explanation.explanation_report.confidence:.1%}")
        lines.append(f"Risk Level: {explanation.explanation_report.risk_level}")
        lines.append("")
        
        # Sections
        for section in explanation.explanation_report.sections:
            lines.append(section.title.upper())
            lines.append("-" * 80)
            lines.append(section.content)
            
            if section.evidence:
                lines.append("\nEvidence:")
                for evidence in section.evidence:
                    lines.append(f"  • {evidence}")
            lines.append("")
        
        # Key factors
        if explanation.explanation_report.key_factors:
            lines.append("KEY FACTORS")
            lines.append("-" * 80)
            for factor in explanation.explanation_report.key_factors:
                lines.append(f"  • {factor}")
            lines.append("")
        
        # Recommendations
        if explanation.explanation_report.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 80)
            for rec in explanation.explanation_report.recommendations:
                lines.append(f"  • {rec}")
            lines.append("")
        
        with open(output_file, 'w') as f:
            f.write("\n".join(lines))
    
    def _export_as_markdown(
        self,
        explanation: DecisionExplanation,
        output_file: str,
        include_visuals: bool
    ):
        """Export as Markdown"""
        lines = []
        
        lines.append("# Fraud Detection Decision Explanation")
        lines.append("")
        lines.append(f"**Transaction ID:** {explanation.transaction_id}")
        lines.append(f"**Generated:** {explanation.generated_timestamp}")
        lines.append("")
        
        # Executive summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(explanation.explanation_report.executive_summary)
        lines.append("")
        
        # Decision
        lines.append("## Decision")
        lines.append("")
        lines.append(f"- **Decision:** {explanation.explanation_report.decision}")
        lines.append(f"- **Confidence:** {explanation.explanation_report.confidence:.1%}")
        lines.append(f"- **Risk Level:** {explanation.explanation_report.risk_level}")
        lines.append("")
        
        # Sections
        for section in explanation.explanation_report.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            
            if section.evidence:
                lines.append("**Evidence:**")
                lines.append("")
                for evidence in section.evidence:
                    lines.append(f"- {evidence}")
                lines.append("")
        
        # Key factors
        if explanation.explanation_report.key_factors:
            lines.append("## Key Factors")
            lines.append("")
            for factor in explanation.explanation_report.key_factors:
                lines.append(f"- {factor}")
            lines.append("")
        
        # Recommendations
        if explanation.explanation_report.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for rec in explanation.explanation_report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        # Visual representations
        if include_visuals:
            lines.append("## Visual Representations")
            lines.append("")
            
            lines.append("### Decision Flow")
            lines.append("```mermaid")
            lines.append(self._generate_flow_chart(explanation))
            lines.append("```")
            lines.append("")
            
            lines.append("### Confidence Progression")
            lines.append("```mermaid")
            lines.append(self._generate_confidence_graph(explanation))
            lines.append("```")
            lines.append("")
        
        with open(output_file, 'w') as f:
            f.write("\n".join(lines))
    
    def _export_as_html(
        self,
        explanation: DecisionExplanation,
        output_file: str,
        include_visuals: bool
    ):
        """Export as HTML"""
        html_parts = []
        
        html_parts.append("<!DOCTYPE html>")
        html_parts.append("<html>")
        html_parts.append("<head>")
        html_parts.append("<title>Fraud Detection Explanation</title>")
        html_parts.append("<style>")
        html_parts.append("body { font-family: Arial, sans-serif; margin: 40px; }")
        html_parts.append("h1 { color: #333; }")
        html_parts.append("h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }")
        html_parts.append(".summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }")
        html_parts.append(".decision { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }")
        html_parts.append(".section { margin: 20px 0; }")
        html_parts.append(".evidence { background: #fff3e0; padding: 10px; margin: 10px 0; }")
        html_parts.append("ul { line-height: 1.8; }")
        html_parts.append("</style>")
        html_parts.append("</head>")
        html_parts.append("<body>")
        
        html_parts.append("<h1>Fraud Detection Decision Explanation</h1>")
        html_parts.append(f"<p><strong>Transaction ID:</strong> {explanation.transaction_id}</p>")
        html_parts.append(f"<p><strong>Generated:</strong> {explanation.generated_timestamp}</p>")
        
        # Executive summary
        html_parts.append("<div class='summary'>")
        html_parts.append("<h2>Executive Summary</h2>")
        html_parts.append(f"<p>{explanation.explanation_report.executive_summary}</p>")
        html_parts.append("</div>")
        
        # Decision
        html_parts.append("<div class='decision'>")
        html_parts.append("<h2>Decision</h2>")
        html_parts.append(f"<p><strong>Decision:</strong> {explanation.explanation_report.decision}</p>")
        html_parts.append(f"<p><strong>Confidence:</strong> {explanation.explanation_report.confidence:.1%}</p>")
        html_parts.append(f"<p><strong>Risk Level:</strong> {explanation.explanation_report.risk_level}</p>")
        html_parts.append("</div>")
        
        # Sections
        for section in explanation.explanation_report.sections:
            html_parts.append("<div class='section'>")
            html_parts.append(f"<h2>{section.title}</h2>")
            html_parts.append(f"<p>{section.content}</p>")
            
            if section.evidence:
                html_parts.append("<div class='evidence'>")
                html_parts.append("<strong>Evidence:</strong>")
                html_parts.append("<ul>")
                for evidence in section.evidence:
                    html_parts.append(f"<li>{evidence}</li>")
                html_parts.append("</ul>")
                html_parts.append("</div>")
            
            html_parts.append("</div>")
        
        # Key factors
        if explanation.explanation_report.key_factors:
            html_parts.append("<h2>Key Factors</h2>")
            html_parts.append("<ul>")
            for factor in explanation.explanation_report.key_factors:
                html_parts.append(f"<li>{factor}</li>")
            html_parts.append("</ul>")
        
        # Recommendations
        if explanation.explanation_report.recommendations:
            html_parts.append("<h2>Recommendations</h2>")
            html_parts.append("<ul>")
            for rec in explanation.explanation_report.recommendations:
                html_parts.append(f"<li>{rec}</li>")
            html_parts.append("</ul>")
        
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        with open(output_file, 'w') as f:
            f.write("\n".join(html_parts))
    
    def compare_explanations(
        self,
        transaction_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare explanations across multiple transactions
        
        Args:
            transaction_ids: List of transaction IDs to compare
            
        Returns:
            Comparison data
        """
        comparisons = {
            "transactions": [],
            "common_factors": [],
            "decision_distribution": {},
            "confidence_comparison": []
        }
        
        all_factors = []
        
        for txn_id in transaction_ids:
            if txn_id in self.explanations_cache:
                exp = self.explanations_cache[txn_id]
                
                comparisons["transactions"].append({
                    "transaction_id": txn_id,
                    "decision": exp.explanation_report.decision,
                    "confidence": exp.explanation_report.confidence,
                    "risk_level": exp.explanation_report.risk_level
                })
                
                # Track decision distribution
                decision = exp.explanation_report.decision
                comparisons["decision_distribution"][decision] = \
                    comparisons["decision_distribution"].get(decision, 0) + 1
                
                # Collect factors
                all_factors.extend(exp.explanation_report.key_factors)
                
                # Confidence comparison
                comparisons["confidence_comparison"].append({
                    "transaction_id": txn_id,
                    "confidence": exp.explanation_report.confidence
                })
        
        # Find common factors
        from collections import Counter
        factor_counts = Counter(all_factors)
        comparisons["common_factors"] = [
            {"factor": factor, "count": count}
            for factor, count in factor_counts.most_common(10)
        ]
        
        return comparisons
    
    def get_explanation_summary(self, transaction_id: str) -> Dict[str, Any]:
        """Get brief summary of explanation"""
        if transaction_id not in self.explanations_cache:
            return {"error": "Explanation not found"}
        
        exp = self.explanations_cache[transaction_id]
        
        return {
            "transaction_id": transaction_id,
            "decision": exp.explanation_report.decision,
            "confidence": exp.explanation_report.confidence,
            "risk_level": exp.explanation_report.risk_level,
            "summary": exp.explanation_report.executive_summary,
            "key_factors_count": len(exp.explanation_report.key_factors),
            "reasoning_steps_count": len(exp.reasoning_trail.steps),
            "generated_timestamp": exp.generated_timestamp
        }
