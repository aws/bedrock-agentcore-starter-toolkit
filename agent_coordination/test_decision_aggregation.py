"""
Unit tests for Decision Aggregation System.
"""

import pytest
from datetime import datetime, timedelta
from agent_coordination.decision_aggregation import (
    DecisionAggregator, AgentDecision, DecisionRequest, AggregatedDecision,
    DecisionType, AggregationMethod, ConflictResolutionStrategy
)


@pytest.fixture
def decision_aggregator():
    """Create decision aggregator for testing."""
    return DecisionAggregator()


@pytest.fixture
def sample_agent_decisions():
    """Create sample agent decisions for testing."""
    return [
        AgentDecision(
            agent_id="agent_1",
            agent_type="transaction_analyzer",
            decision=DecisionType.APPROVE,
            confidence_score=0.9,
            reasoning=["Low risk transaction", "Known merchant"],
            evidence={"risk_score": 0.1, "merchant_verified": True},
            processing_time_ms=150.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="agent_2",
            agent_type="pattern_detector",
            decision=DecisionType.APPROVE,
            confidence_score=0.8,
            reasoning=["Normal pattern", "User behavior consistent"],
            evidence={"pattern_match": 0.95, "anomaly_score": 0.05},
            processing_time_ms=200.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="agent_3",
            agent_type="risk_assessor",
            decision=DecisionType.FLAG,
            confidence_score=0.7,
            reasoning=["Unusual location", "High velocity"],
            evidence={"location_risk": 0.6, "velocity_score": 0.8},
            processing_time_ms=180.0,
            timestamp=datetime.now()
        )
    ]


class TestDecisionAggregator:
    """Test cases for DecisionAggregator."""
    
    def test_aggregator_initialization(self, decision_aggregator):
        """Test decision aggregator initialization."""
        assert len(decision_aggregator.pending_decisions) == 0
        assert len(decision_aggregator.completed_decisions) == 0
        assert len(decision_aggregator.agent_weights) == 0
    
    def test_set_agent_weight(self, decision_aggregator):
        """Test setting agent weights."""
        decision_aggregator.set_agent_weight("agent_1", 1.5)
        decision_aggregator.set_agent_weight("agent_2", 0.5)
        
        assert decision_aggregator.agent_weights["agent_1"] == 1.5
        assert decision_aggregator.agent_weights["agent_2"] == 0.5
    
    def test_majority_vote_aggregation(self, decision_aggregator, sample_agent_decisions):
        """Test majority vote aggregation."""
        # Create decision request
        request = DecisionRequest(
            request_id="test_request_1",
            transaction_data={"amount": 100.0, "merchant": "Test Store"},
            context_data={},
            required_agents=["agent_1", "agent_2", "agent_3"],
            optional_agents=[],
            timeout_seconds=30,
            aggregation_method=AggregationMethod.MAJORITY_VOTE,
            conflict_resolution=ConflictResolutionStrategy.MOST_CONSERVATIVE
        )
        
        # Request decision
        request_id = decision_aggregator.request_decision(request)
        assert request_id == "test_request_1"
        
        # Submit agent decisions
        for decision in sample_agent_decisions:
            success = decision_aggregator.submit_agent_decision(request_id, decision)
            assert success is True
        
        # Get aggregated decision
        aggregated = decision_aggregator.get_aggregated_decision(request_id)
        assert aggregated is not None
        assert aggregated.final_decision == DecisionType.APPROVE  # Majority
        assert len(aggregated.agent_decisions) == 3
    
    def test_weighted_vote_aggregation(self, decision_aggregator, sample_agent_decisions):
        """Test weighted vote aggregation."""
        # Set different weights for agents
        decision_aggregator.set_agent_weight("agent_1", 2.0)
        decision_aggregator.set_agent_weight("agent_2", 1.5)
        decision_aggregator.set_agent_weight("agent_3", 0.5)
        
        request = DecisionRequest(
            request_id="test_request_2",
            transaction_data={"amount": 100.0},
            context_data={},
            required_agents=["agent_1", "agent_2", "agent_3"],
            optional_agents=[],
            timeout_seconds=30,
            aggregation_method=AggregationMethod.WEIGHTED_VOTE,
            conflict_resolution=ConflictResolutionStrategy.WEIGHTED_AVERAGE
        )
        
        request_id = decision_aggregator.request_decision(request)
        
        for decision in sample_agent_decisions:
            decision_aggregator.submit_agent_decision(request_id, decision)
        
        aggregated = decision_aggregator.get_aggregated_decision(request_id)
        assert aggregated is not None
        assert aggregated.aggregation_method == AggregationMethod.WEIGHTED_VOTE
    
    def test_consensus_aggregation(self, decision_aggregator):
        """Test consensus aggregation."""
        # Create unanimous decisions
        unanimous_decisions = [
            AgentDecision(
                agent_id=f"agent_{i}",
                agent_type="test",
                decision=DecisionType.APPROVE,
                confidence_score=0.9,
                reasoning=["Test reason"],
                evidence={"test": True},
                processing_time_ms=100.0,
                timestamp=datetime.now()
            )
            for i in range(3)
        ]
        
        request = DecisionRequest(
            request_id="test_consensus",
            transaction_data={},
            context_data={},
            required_agents=["agent_0", "agent_1", "agent_2"],
            optional_agents=[],
            timeout_seconds=30,
            aggregation_method=AggregationMethod.CONSENSUS,
            conflict_resolution=ConflictResolutionStrategy.ESCALATE_TO_HUMAN
        )
        
        request_id = decision_aggregator.request_decision(request)
        
        for decision in unanimous_decisions:
            decision_aggregator.submit_agent_decision(request_id, decision)
        
        aggregated = decision_aggregator.get_aggregated_decision(request_id)
        assert aggregated is not None
        assert aggregated.final_decision == DecisionType.APPROVE
        assert aggregated.consensus_level == 1.0  # Perfect consensus
    
    def test_conflict_resolution(self, decision_aggregator):
        """Test conflict resolution strategies."""
        conflicting_decisions = [
            AgentDecision(
                agent_id="agent_1",
                agent_type="test",
                decision=DecisionType.APPROVE,
                confidence_score=0.6,
                reasoning=["Low risk"],
                evidence={},
                processing_time_ms=100.0,
                timestamp=datetime.now()
            ),
            AgentDecision(
                agent_id="agent_2",
                agent_type="test",
                decision=DecisionType.DECLINE,
                confidence_score=0.8,
                reasoning=["High risk"],
                evidence={},
                processing_time_ms=100.0,
                timestamp=datetime.now()
            )
        ]
        
        request = DecisionRequest(
            request_id="test_conflict",
            transaction_data={},
            context_data={},
            required_agents=["agent_1", "agent_2"],
            optional_agents=[],
            timeout_seconds=30,
            aggregation_method=AggregationMethod.MAJORITY_VOTE,
            conflict_resolution=ConflictResolutionStrategy.MOST_CONSERVATIVE
        )
        
        request_id = decision_aggregator.request_decision(request)
        
        for decision in conflicting_decisions:
            decision_aggregator.submit_agent_decision(request_id, decision)
        
        aggregated = decision_aggregator.get_aggregated_decision(request_id)
        assert aggregated is not None
        assert aggregated.final_decision == DecisionType.DECLINE  # Most conservative
        assert aggregated.conflict_resolution == ConflictResolutionStrategy.MOST_CONSERVATIVE
    
    def test_force_aggregation(self, decision_aggregator, sample_agent_decisions):
        """Test forcing aggregation before timeout."""
        request = DecisionRequest(
            request_id="test_force",
            transaction_data={},
            context_data={},
            required_agents=["agent_1", "agent_2", "agent_3", "agent_4"],  # Missing agent_4
            optional_agents=[],
            timeout_seconds=60,
            aggregation_method=AggregationMethod.MAJORITY_VOTE,
            conflict_resolution=ConflictResolutionStrategy.WEIGHTED_AVERAGE
        )
        
        request_id = decision_aggregator.request_decision(request)
        
        # Submit only 3 out of 4 required decisions
        for decision in sample_agent_decisions:
            decision_aggregator.submit_agent_decision(request_id, decision)
        
        # Should not be ready yet
        aggregated = decision_aggregator.get_aggregated_decision(request_id)
        assert aggregated is None
        
        # Force aggregation
        forced_aggregated = decision_aggregator.force_aggregation(request_id)
        assert forced_aggregated is not None
        assert len(forced_aggregated.agent_decisions) == 3
    
    def test_decision_statistics(self, decision_aggregator, sample_agent_decisions):
        """Test decision statistics generation."""
        # Process a few decisions
        for i in range(3):
            request = DecisionRequest(
                request_id=f"stats_test_{i}",
                transaction_data={},
                context_data={},
                required_agents=["agent_1", "agent_2"],
                optional_agents=[],
                timeout_seconds=30,
                aggregation_method=AggregationMethod.MAJORITY_VOTE,
                conflict_resolution=ConflictResolutionStrategy.WEIGHTED_AVERAGE
            )
            
            request_id = decision_aggregator.request_decision(request)
            
            for decision in sample_agent_decisions[:2]:  # Use first 2 decisions
                decision_aggregator.submit_agent_decision(request_id, decision)
        
        stats = decision_aggregator.get_decision_statistics()
        assert stats["total_decisions"] == 3
        assert "decision_distribution" in stats
        assert "average_confidence" in stats
        assert "average_consensus" in stats


class TestAgentDecision:
    """Test cases for AgentDecision."""
    
    def test_confidence_level_property(self):
        """Test confidence level calculation."""
        decision = AgentDecision(
            agent_id="test_agent",
            agent_type="test",
            decision=DecisionType.APPROVE,
            confidence_score=0.95,
            reasoning=["Test"],
            evidence={},
            processing_time_ms=100.0,
            timestamp=datetime.now()
        )
        
        assert decision.confidence_level.value == "very_high"
        
        decision.confidence_score = 0.75
        assert decision.confidence_level.value == "high"
        
        decision.confidence_score = 0.55
        assert decision.confidence_level.value == "medium"
        
        decision.confidence_score = 0.35
        assert decision.confidence_level.value == "low"
        
        decision.confidence_score = 0.15
        assert decision.confidence_level.value == "very_low"


class TestAggregatedDecision:
    """Test cases for AggregatedDecision."""
    
    def test_decision_properties(self, sample_agent_decisions):
        """Test aggregated decision properties."""
        aggregated = AggregatedDecision(
            decision_id="test_agg",
            final_decision=DecisionType.APPROVE,
            confidence_score=0.8,
            aggregation_method=AggregationMethod.MAJORITY_VOTE,
            conflict_resolution=None,
            agent_decisions=sample_agent_decisions,
            decision_weights={"agent_1": 1.0, "agent_2": 1.0, "agent_3": 1.0},
            reasoning_summary=["Test reasoning"],
            evidence_summary={"test": "evidence"},
            consensus_level=0.67,
            processing_time_ms=200.0,
            timestamp=datetime.now()
        )
        
        assert len(aggregated.participating_agents) == 3
        assert "agent_1" in aggregated.participating_agents
        
        distribution = aggregated.decision_distribution
        assert distribution[DecisionType.APPROVE] == 2
        assert distribution[DecisionType.FLAG] == 1
        
        avg_confidence = aggregated.average_confidence
        assert 0.7 <= avg_confidence <= 0.9  # Should be around 0.8


if __name__ == "__main__":
    pytest.main([__file__])