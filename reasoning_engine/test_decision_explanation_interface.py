"""
Tests for Decision Explanation Interface
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from decision_explanation_interface import (
    DecisionExplanationInterface,
    ExportFormat,
    ExplanationStyle,
    ExplanationLevel
)


@pytest.fixture
def sample_reasoning_result():
    """Create sample reasoning result"""
    return {
        'transaction_id': 'txn_test_001',
        'reasoning_id': 'reasoning_001',
        'steps': [
            {
                'step_id': 'step_1',
                'step_type': 'observation',
                'description': 'Initial observation',
                'input_data': {'transaction': {'amount': 5000, 'currency': 'USD'}},
                'reasoning': 'Analyzing transaction amount and patterns',
                'output': {'risk_level': 'MEDIUM', 'key_findings': ['High amount']},
                'evidence': ['Amount exceeds average', 'Unusual time'],
                'confidence': 0.75,
                'processing_time_ms': 50.0,
                'dependencies': [],
                'timestamp': '2024-01-01T12:00:00'
            },
            {
                'step_id': 'step_2',
                'step_type': 'analysis',
                'description': 'Detailed analysis',
                'input_data': {},
                'reasoning': 'Comparing with historical patterns',
                'output': {'is_fraud': False, 'confidence': 0.85},
                'evidence': ['Matches user pattern', 'Verified merchant'],
                'confidence': 0.85,
                'processing_time_ms': 75.0,
                'dependencies': ['step_1'],
                'timestamp': '2024-01-01T12:00:01'
            }
        ],
        'final_decision': {
            'is_fraud': False,
            'confidence': 0.80,
            'risk_level': 'LOW',
            'recommended_action': 'APPROVE',
            'primary_concerns': []
        },
        'overall_confidence': 0.80,
        'total_processing_time_ms': 125.0
    }


@pytest.fixture
def interface():
    """Create interface instance"""
    return DecisionExplanationInterface()


class TestDecisionExplanationInterface:
    """Test decision explanation interface"""
    
    def test_initialization(self, interface):
        """Test interface initialization"""
        assert interface.explanation_generator is not None
        assert interface.trail_formatter is not None
        assert len(interface.explanations_cache) == 0
    
    def test_generate_complete_explanation(self, interface, sample_reasoning_result):
        """Test generating complete explanation"""
        explanation = interface.generate_complete_explanation(
            sample_reasoning_result,
            style=ExplanationStyle.BUSINESS,
            level=ExplanationLevel.DETAILED
        )
        
        assert explanation.transaction_id == 'txn_test_001'
        assert explanation.explanation_report is not None
        assert explanation.reasoning_trail is not None
        assert explanation.visual_data is not None
        assert 'txn_test_001' in interface.explanations_cache
    
    def test_generate_different_styles(self, interface, sample_reasoning_result):
        """Test generating explanations with different styles"""
        styles = [
            ExplanationStyle.TECHNICAL,
            ExplanationStyle.BUSINESS,
            ExplanationStyle.CUSTOMER,
            ExplanationStyle.REGULATORY
        ]
        
        for style in styles:
            # Modify transaction ID for each style
            result = sample_reasoning_result.copy()
            result['transaction_id'] = f'txn_{style.value}'
            
            explanation = interface.generate_complete_explanation(
                result,
                style=style
            )
            
            assert explanation.explanation_report.explanation_style == style
    
    def test_generate_different_levels(self, interface, sample_reasoning_result):
        """Test generating explanations with different detail levels"""
        levels = [
            ExplanationLevel.BRIEF,
            ExplanationLevel.DETAILED,
            ExplanationLevel.COMPREHENSIVE
        ]
        
        for level in levels:
            result = sample_reasoning_result.copy()
            result['transaction_id'] = f'txn_{level.value}'
            
            explanation = interface.generate_complete_explanation(
                result,
                level=level
            )
            
            assert explanation.explanation_report.explanation_level == level
    
    def test_visual_data_generation(self, interface, sample_reasoning_result):
        """Test visual data generation"""
        explanation = interface.generate_complete_explanation(sample_reasoning_result)
        
        visual_data = explanation.visual_data
        
        assert 'decision_flow' in visual_data
        assert 'confidence_progression' in visual_data
        assert 'risk_factors' in visual_data
        assert 'evidence_hierarchy' in visual_data
        assert 'final_decision' in visual_data
        
        # Check decision flow structure
        assert 'nodes' in visual_data['decision_flow']
        assert 'edges' in visual_data['decision_flow']
        assert len(visual_data['decision_flow']['nodes']) == 2
        
        # Check confidence progression
        assert len(visual_data['confidence_progression']) == 2
        assert visual_data['confidence_progression'][0]['step'] == 1
        assert visual_data['confidence_progression'][0]['confidence'] == 0.75


class TestInteractiveExplanation:
    """Test interactive explanation features"""
    
    def test_get_interactive_explanation(self, interface, sample_reasoning_result):
        """Test getting interactive explanation"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        interactive = interface.get_interactive_explanation('txn_test_001')
        
        assert interactive['transaction_id'] == 'txn_test_001'
        assert 'summary' in interactive
        assert 'decision' in interactive
        assert 'confidence' in interactive
        assert 'sections' in interactive
        assert len(interactive['sections']) > 0
    
    def test_drill_down_section(self, interface, sample_reasoning_result):
        """Test drilling down into section"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        interactive = interface.get_interactive_explanation(
            'txn_test_001',
            drill_down_path=['section_0']
        )
        
        assert 'drill_down' in interactive
        assert interactive['drill_down']['type'] == 'section_detail'
        assert 'title' in interactive['drill_down']
        assert 'content' in interactive['drill_down']
        assert 'evidence' in interactive['drill_down']
    
    def test_drill_down_reasoning_steps(self, interface, sample_reasoning_result):
        """Test drilling down into reasoning steps"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        interactive = interface.get_interactive_explanation(
            'txn_test_001',
            drill_down_path=['reasoning_steps']
        )
        
        assert 'drill_down' in interactive
        assert interactive['drill_down']['type'] == 'reasoning_detail'
        assert 'steps' in interactive['drill_down']
        assert len(interactive['drill_down']['steps']) == 2
    
    def test_drill_down_evidence(self, interface, sample_reasoning_result):
        """Test drilling down into evidence"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        interactive = interface.get_interactive_explanation(
            'txn_test_001',
            drill_down_path=['evidence']
        )
        
        assert 'drill_down' in interactive
        assert interactive['drill_down']['type'] == 'evidence_detail'
        assert 'evidence_items' in interactive['drill_down']
    
    def test_drill_down_visual(self, interface, sample_reasoning_result):
        """Test drilling down into visual data"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        interactive = interface.get_interactive_explanation(
            'txn_test_001',
            drill_down_path=['visual']
        )
        
        assert 'drill_down' in interactive
        assert interactive['drill_down']['type'] == 'visual_detail'
        assert 'visual_data' in interactive['drill_down']


class TestVisualRepresentations:
    """Test visual representation generation"""
    
    def test_generate_decision_tree(self, interface, sample_reasoning_result):
        """Test decision tree generation"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        tree = interface.generate_visual_representation(
            'txn_test_001',
            visualization_type='decision_tree'
        )
        
        assert 'graph TD' in tree
        assert 'Start' in tree
        assert 'Decision' in tree
    
    def test_generate_flow_chart(self, interface, sample_reasoning_result):
        """Test flow chart generation"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        chart = interface.generate_visual_representation(
            'txn_test_001',
            visualization_type='flow_chart'
        )
        
        assert 'flowchart LR' in chart
        assert 'Start' in chart
    
    def test_generate_confidence_graph(self, interface, sample_reasoning_result):
        """Test confidence graph generation"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        graph = interface.generate_visual_representation(
            'txn_test_001',
            visualization_type='confidence_graph'
        )
        
        assert 'graph LR' in graph
        assert 'C0' in graph
        assert 'C1' in graph


class TestExportFunctionality:
    """Test export functionality"""
    
    def test_export_as_json(self, interface, sample_reasoning_result):
        """Test JSON export"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name
        
        try:
            success = interface.export_explanation(
                'txn_test_001',
                ExportFormat.JSON,
                output_file
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # Verify JSON content
            with open(output_file, 'r') as f:
                data = json.load(f)
                assert data['transaction_id'] == 'txn_test_001'
                assert 'explanation_report' in data
                assert 'reasoning_trail' in data
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_export_as_text(self, interface, sample_reasoning_result):
        """Test text export"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            output_file = f.name
        
        try:
            success = interface.export_explanation(
                'txn_test_001',
                ExportFormat.TEXT,
                output_file
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # Verify text content
            with open(output_file, 'r') as f:
                content = f.read()
                assert 'FRAUD DETECTION DECISION EXPLANATION' in content
                assert 'txn_test_001' in content
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_export_as_markdown(self, interface, sample_reasoning_result):
        """Test Markdown export"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            output_file = f.name
        
        try:
            success = interface.export_explanation(
                'txn_test_001',
                ExportFormat.MARKDOWN,
                output_file,
                include_visuals=True
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # Verify markdown content
            with open(output_file, 'r') as f:
                content = f.read()
                assert '# Fraud Detection Decision Explanation' in content
                assert '## Executive Summary' in content
                assert '```mermaid' in content  # Visual included
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_export_as_html(self, interface, sample_reasoning_result):
        """Test HTML export"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
            output_file = f.name
        
        try:
            success = interface.export_explanation(
                'txn_test_001',
                ExportFormat.HTML,
                output_file
            )
            
            assert success
            assert os.path.exists(output_file)
            
            # Verify HTML content
            with open(output_file, 'r') as f:
                content = f.read()
                assert '<!DOCTYPE html>' in content
                assert '<title>Fraud Detection Explanation</title>' in content
                assert 'txn_test_001' in content
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_export_nonexistent_transaction(self, interface):
        """Test exporting nonexistent transaction"""
        success = interface.export_explanation(
            'nonexistent',
            ExportFormat.JSON,
            'output.json'
        )
        
        assert not success


class TestComparisonFeatures:
    """Test comparison features"""
    
    def test_compare_explanations(self, interface, sample_reasoning_result):
        """Test comparing multiple explanations"""
        # Generate multiple explanations
        for i in range(3):
            result = sample_reasoning_result.copy()
            result['transaction_id'] = f'txn_compare_{i}'
            interface.generate_complete_explanation(result)
        
        # Compare
        comparison = interface.compare_explanations([
            'txn_compare_0',
            'txn_compare_1',
            'txn_compare_2'
        ])
        
        assert len(comparison['transactions']) == 3
        assert 'common_factors' in comparison
        assert 'decision_distribution' in comparison
        assert 'confidence_comparison' in comparison
    
    def test_get_explanation_summary(self, interface, sample_reasoning_result):
        """Test getting explanation summary"""
        interface.generate_complete_explanation(sample_reasoning_result)
        
        summary = interface.get_explanation_summary('txn_test_001')
        
        assert summary['transaction_id'] == 'txn_test_001'
        assert 'decision' in summary
        assert 'confidence' in summary
        assert 'risk_level' in summary
        assert 'summary' in summary
        assert 'key_factors_count' in summary
        assert 'reasoning_steps_count' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
