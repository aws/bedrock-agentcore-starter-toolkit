"""
Demo: Decision Explanation Interface

Showcases interactive explanation capabilities with:
- Multiple explanation styles and levels
- Interactive drill-down
- Visual representations
- Export functionality
"""

from src.decision_explanation_interface import (
    DecisionExplanationInterface,
    ExportFormat,
    ExplanationStyle,
    ExplanationLevel
)


def create_sample_reasoning_result(transaction_id: str, is_fraud: bool = False):
    """Create sample reasoning result for demo"""
    return {
        'transaction_id': transaction_id,
        'reasoning_id': f'reasoning_{transaction_id}',
        'steps': [
            {
                'step_id': 'step_1',
                'step_type': 'observation',
                'description': 'Initial transaction observation and data collection',
                'input_data': {
                    'transaction': {
                        'amount': 7500 if is_fraud else 250,
                        'currency': 'USD',
                        'merchant': 'Luxury Goods Store' if is_fraud else 'Coffee Shop',
                        'location': 'Unknown Location' if is_fraud else 'New York, USA'
                    }
                },
                'reasoning': 'Examining transaction details including amount, merchant, and location patterns',
                'output': {
                    'risk_level': 'HIGH' if is_fraud else 'LOW',
                    'key_findings': ['Unusual amount'] if is_fraud else ['Normal amount'],
                    'primary_concerns': ['High value transaction'] if is_fraud else []
                },
                'evidence': [
                    'Amount significantly exceeds user average' if is_fraud else 'Amount within normal range',
                    'Unfamiliar merchant category' if is_fraud else 'Familiar merchant',
                    'Location mismatch' if is_fraud else 'Expected location'
                ],
                'confidence': 0.65 if is_fraud else 0.90,
                'processing_time_ms': 45.0,
                'dependencies': [],
                'timestamp': '2024-01-01T12:00:00'
            },
            {
                'step_id': 'step_2',
                'step_type': 'pattern_matching',
                'description': 'Historical pattern analysis and comparison',
                'input_data': {'user_history': []},
                'reasoning': 'Comparing current transaction with historical user behavior patterns',
                'output': {
                    'is_fraud': is_fraud,
                    'confidence': 0.75 if is_fraud else 0.88,
                    'key_findings': [
                        'Pattern deviation detected' if is_fraud else 'Consistent with history'
                    ]
                },
                'evidence': [
                    'No similar transactions in history' if is_fraud else 'Similar transactions found',
                    'Velocity anomaly detected' if is_fraud else 'Normal velocity pattern'
                ],
                'confidence': 0.75 if is_fraud else 0.88,
                'processing_time_ms': 62.0,
                'dependencies': ['step_1'],
                'timestamp': '2024-01-01T12:00:01'
            },
            {
                'step_id': 'step_3',
                'step_type': 'risk_assessment',
                'description': 'Comprehensive risk evaluation',
                'input_data': {},
                'reasoning': 'Calculating overall risk score based on multiple factors',
                'output': {
                    'risk_level': 'HIGH' if is_fraud else 'LOW',
                    'risk_factors': [
                        'High transaction amount',
                        'Unusual merchant',
                        'Location anomaly'
                    ] if is_fraud else [],
                    'recommended_action': 'BLOCK' if is_fraud else 'APPROVE'
                },
                'evidence': [
                    'Multiple risk indicators present' if is_fraud else 'No significant risk indicators',
                    'Fraud probability: 85%' if is_fraud else 'Fraud probability: 5%'
                ],
                'confidence': 0.85 if is_fraud else 0.92,
                'processing_time_ms': 58.0,
                'dependencies': ['step_1', 'step_2'],
                'timestamp': '2024-01-01T12:00:02'
            }
        ],
        'final_decision': {
            'is_fraud': is_fraud,
            'confidence': 0.82 if is_fraud else 0.90,
            'risk_level': 'HIGH' if is_fraud else 'LOW',
            'recommended_action': 'BLOCK' if is_fraud else 'APPROVE',
            'primary_concerns': [
                'Unusual transaction amount',
                'Unfamiliar merchant',
                'Location mismatch'
            ] if is_fraud else []
        },
        'overall_confidence': 0.82 if is_fraud else 0.90,
        'total_processing_time_ms': 165.0
    }


def demo_basic_explanation():
    """Demonstrate basic explanation generation"""
    print("=" * 80)
    print("DEMO: Basic Explanation Generation")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    
    # Generate explanation for approved transaction
    print("\n1. Generating explanation for APPROVED transaction...")
    result = create_sample_reasoning_result('txn_demo_001', is_fraud=False)
    
    explanation = interface.generate_complete_explanation(
        result,
        style=ExplanationStyle.BUSINESS,
        level=ExplanationLevel.DETAILED
    )
    
    print(f"   ✓ Generated explanation for {explanation.transaction_id}")
    print(f"   Decision: {explanation.explanation_report.decision}")
    print(f"   Confidence: {explanation.explanation_report.confidence:.1%}")
    print(f"   Risk Level: {explanation.explanation_report.risk_level}")
    print(f"\n   Executive Summary:")
    print(f"   {explanation.explanation_report.executive_summary}")
    
    # Generate explanation for blocked transaction
    print("\n2. Generating explanation for BLOCKED transaction...")
    result = create_sample_reasoning_result('txn_demo_002', is_fraud=True)
    
    explanation = interface.generate_complete_explanation(
        result,
        style=ExplanationStyle.BUSINESS,
        level=ExplanationLevel.DETAILED
    )
    
    print(f"   ✓ Generated explanation for {explanation.transaction_id}")
    print(f"   Decision: {explanation.explanation_report.decision}")
    print(f"   Confidence: {explanation.explanation_report.confidence:.1%}")
    print(f"   Risk Level: {explanation.explanation_report.risk_level}")
    print(f"\n   Executive Summary:")
    print(f"   {explanation.explanation_report.executive_summary}")


def demo_different_styles():
    """Demonstrate different explanation styles"""
    print("\n" + "=" * 80)
    print("DEMO: Different Explanation Styles")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    result = create_sample_reasoning_result('txn_style_demo', is_fraud=True)
    
    styles = [
        (ExplanationStyle.TECHNICAL, "Technical (for engineers)"),
        (ExplanationStyle.BUSINESS, "Business (for managers)"),
        (ExplanationStyle.CUSTOMER, "Customer (for end users)"),
        (ExplanationStyle.REGULATORY, "Regulatory (for compliance)")
    ]
    
    for style, description in styles:
        print(f"\n{description}:")
        print("-" * 60)
        
        result_copy = result.copy()
        result_copy['transaction_id'] = f'txn_{style.value}'
        
        explanation = interface.generate_complete_explanation(
            result_copy,
            style=style,
            level=ExplanationLevel.BRIEF
        )
        
        print(f"{explanation.explanation_report.executive_summary[:200]}...")


def demo_interactive_drill_down():
    """Demonstrate interactive drill-down"""
    print("\n" + "=" * 80)
    print("DEMO: Interactive Drill-Down")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    result = create_sample_reasoning_result('txn_interactive', is_fraud=True)
    
    interface.generate_complete_explanation(result)
    
    # Get base interactive explanation
    print("\n1. Base interactive view:")
    interactive = interface.get_interactive_explanation('txn_interactive')
    
    print(f"   Transaction: {interactive['transaction_id']}")
    print(f"   Decision: {interactive['decision']}")
    print(f"   Sections available: {len(interactive['sections'])}")
    
    for section in interactive['sections']:
        drill_status = "✓ Can drill down" if section['can_drill_down'] else "○ No drill-down"
        print(f"   - {section['title']} ({drill_status})")
    
    # Drill into first section
    print("\n2. Drilling into first section...")
    interactive = interface.get_interactive_explanation(
        'txn_interactive',
        drill_down_path=['section_0']
    )
    
    if 'drill_down' in interactive:
        drill = interactive['drill_down']
        print(f"   Section: {drill['title']}")
        print(f"   Evidence items: {len(drill['evidence'])}")
        for evidence in drill['evidence'][:3]:
            print(f"   - {evidence}")
    
    # Drill into reasoning steps
    print("\n3. Drilling into reasoning steps...")
    interactive = interface.get_interactive_explanation(
        'txn_interactive',
        drill_down_path=['reasoning_steps']
    )
    
    if 'drill_down' in interactive:
        steps = interactive['drill_down']['steps']
        print(f"   Total reasoning steps: {len(steps)}")
        for step in steps:
            print(f"   Step {step['step_number']}: {step['title']}")
            print(f"      Confidence: {step['confidence']:.1%}")


def demo_visual_representations():
    """Demonstrate visual representations"""
    print("\n" + "=" * 80)
    print("DEMO: Visual Representations")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    result = create_sample_reasoning_result('txn_visual', is_fraud=True)
    
    explanation = interface.generate_complete_explanation(result)
    
    print("\n1. Visual Data Generated:")
    visual = explanation.visual_data
    
    print(f"   Decision Flow Nodes: {len(visual['decision_flow']['nodes'])}")
    print(f"   Decision Flow Edges: {len(visual['decision_flow']['edges'])}")
    print(f"   Confidence Progression Steps: {len(visual['confidence_progression'])}")
    print(f"   Risk Factors: {len(visual['risk_factors'])}")
    
    print("\n2. Confidence Progression:")
    for step in visual['confidence_progression']:
        bar = "█" * int(step['confidence'] * 20)
        print(f"   Step {step['step']}: {bar} {step['confidence']:.1%}")
    
    print("\n3. Evidence Hierarchy:")
    for level, evidence_list in visual['evidence_hierarchy'].items():
        print(f"   {level.replace('_', ' ').title()}: {len(evidence_list)} items")
    
    # Generate Mermaid diagrams
    print("\n4. Generating Mermaid Diagrams...")
    
    print("\n   Decision Tree:")
    tree = interface.generate_visual_representation('txn_visual', 'decision_tree')
    print("   " + "\n   ".join(tree.split('\n')[:5]) + "\n   ...")
    
    print("\n   Flow Chart:")
    chart = interface.generate_visual_representation('txn_visual', 'flow_chart')
    print("   " + "\n   ".join(chart.split('\n')[:5]) + "\n   ...")


def demo_export_functionality():
    """Demonstrate export functionality"""
    print("\n" + "=" * 80)
    print("DEMO: Export Functionality")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    result = create_sample_reasoning_result('txn_export', is_fraud=True)
    
    interface.generate_complete_explanation(result)
    
    exports = [
        (ExportFormat.JSON, "demo_explanation.json", "JSON format for APIs"),
        (ExportFormat.TEXT, "demo_explanation.txt", "Plain text for reading"),
        (ExportFormat.MARKDOWN, "demo_explanation.md", "Markdown with visuals"),
        (ExportFormat.HTML, "demo_explanation.html", "HTML for web viewing")
    ]
    
    print("\nExporting explanation in multiple formats:")
    
    for export_format, filename, description in exports:
        success = interface.export_explanation(
            'txn_export',
            export_format,
            filename,
            include_visuals=True
        )
        
        status = "✓" if success else "✗"
        print(f"   {status} {filename} - {description}")


def demo_comparison():
    """Demonstrate explanation comparison"""
    print("\n" + "=" * 80)
    print("DEMO: Explanation Comparison")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    
    # Generate multiple explanations
    print("\n1. Generating explanations for multiple transactions...")
    transaction_ids = []
    
    for i in range(5):
        txn_id = f'txn_compare_{i}'
        is_fraud = i % 2 == 0  # Alternate between fraud and non-fraud
        result = create_sample_reasoning_result(txn_id, is_fraud)
        interface.generate_complete_explanation(result)
        transaction_ids.append(txn_id)
        
        decision = "BLOCKED" if is_fraud else "APPROVED"
        print(f"   ✓ {txn_id}: {decision}")
    
    # Compare explanations
    print("\n2. Comparing explanations...")
    comparison = interface.compare_explanations(transaction_ids)
    
    print(f"\n   Transactions Analyzed: {len(comparison['transactions'])}")
    
    print("\n   Decision Distribution:")
    for decision, count in comparison['decision_distribution'].items():
        print(f"   - {decision}: {count}")
    
    print("\n   Common Factors:")
    for factor_data in comparison['common_factors'][:5]:
        print(f"   - {factor_data['factor']} (appears {factor_data['count']} times)")
    
    print("\n   Confidence Range:")
    confidences = [t['confidence'] for t in comparison['confidence_comparison']]
    print(f"   - Highest: {max(confidences):.1%}")
    print(f"   - Lowest: {min(confidences):.1%}")
    print(f"   - Average: {sum(confidences)/len(confidences):.1%}")


def demo_explanation_summary():
    """Demonstrate explanation summaries"""
    print("\n" + "=" * 80)
    print("DEMO: Explanation Summaries")
    print("=" * 80)
    
    interface = DecisionExplanationInterface()
    
    # Generate explanations
    for i in range(3):
        txn_id = f'txn_summary_{i}'
        result = create_sample_reasoning_result(txn_id, is_fraud=(i == 1))
        interface.generate_complete_explanation(result)
    
    print("\nQuick summaries of all explanations:")
    
    for i in range(3):
        txn_id = f'txn_summary_{i}'
        summary = interface.get_explanation_summary(txn_id)
        
        print(f"\n   {summary['transaction_id']}:")
        print(f"   - Decision: {summary['decision']}")
        print(f"   - Confidence: {summary['confidence']:.1%}")
        print(f"   - Risk Level: {summary['risk_level']}")
        print(f"   - Key Factors: {summary['key_factors_count']}")
        print(f"   - Reasoning Steps: {summary['reasoning_steps_count']}")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "DECISION EXPLANATION INTERFACE DEMO" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")
    
    demo_basic_explanation()
    demo_different_styles()
    demo_interactive_drill_down()
    demo_visual_representations()
    demo_export_functionality()
    demo_comparison()
    demo_explanation_summary()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("✓ Human-readable explanation generation")
    print("✓ Multiple explanation styles (Technical, Business, Customer, Regulatory)")
    print("✓ Interactive drill-down capabilities")
    print("✓ Visual decision logic representations (Mermaid diagrams)")
    print("✓ Export functionality (JSON, Text, Markdown, HTML)")
    print("✓ Explanation comparison across transactions")
    print("✓ Quick summaries for dashboard views")
    print("\n")


if __name__ == "__main__":
    main()
