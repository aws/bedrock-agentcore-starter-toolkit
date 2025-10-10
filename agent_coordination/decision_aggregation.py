"""
Decision Aggregation System

Provides multi-agent decision collection, analysis, conflict resolution,
and weighted voting for coordinated fraud detection decisions.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import math

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions that can be made."""
    APPROVE = "approve"
    DECLINE = "decline"
    FLAG = "flag"
    REVIEW = "review"
    ESCALATE = "escalate"


class ConfidenceLevel(Enum):
    """Confidence levels for decisions."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AggregationMethod(Enum):
    """Methods for aggregating decisions."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    CONSENSUS = "consensus"
    EXPERT_OVERRIDE = "expert_override"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    HYBRID = "hybrid"


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving decision conflicts."""
    MOST_CONSERVATIVE = "most_conservative"
    HIGHEST_CONFIDENCE = "highest_confidence"
    EXPERT_PRIORITY = "expert_priority"
    WEIGHTED_AVERAGE = "weighted_average"
    ESCALATE_TO_HUMAN = "escalate_to_human"


@dataclass
class AgentDecision:
    """Individual agent decision with metadata."""
    agent_id: str
    agent_type: str
    decision: DecisionType
    confidence_score: float
    reasoning: List[str]
    evidence: Dict[str, Any]
    processing_time_ms: float
    timestamp: datetime
    agent_weight: float = 1.0
    expertise_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level based on score."""
        if self.confidence_score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence_score >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.confidence_score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class AggregatedDecision:
    """Final aggregated decision from multiple agents."""
    decision_id: str
    final_decision: DecisionType
    confidence_score: float
    aggregation_method: AggregationMethod
    conflict_resolution: Optional[ConflictResolutionStrategy]
    agent_decisions: List[AgentDecision]
    decision_weights: Dict[str, float]
    reasoning_summary: List[str]
    evidence_summary: Dict[str, Any]
    consensus_level: float
    processing_time_ms: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def participating_agents(self) -> List[str]:
        """Get list of participating agent IDs."""
        return [decision.agent_id for decision in self.agent_decisions]
    
    @property
    def decision_distribution(self) -> Dict[DecisionType, int]:
        """Get distribution of decisions across agents."""
        distribution = {}
        for decision in self.agent_decisions:
            if decision.decision not in distribution:
                distribution[decision.decision] = 0
            distribution[decision.decision] += 1
        return distribution
    
    @property
    def average_confidence(self) -> float:
        """Get average confidence across all decisions."""
        if not self.agent_decisions:
            return 0.0
        return sum(d.confidence_score for d in self.agent_decisions) / len(self.agent_decisions)


@dataclass
class DecisionRequest:
    """Request for multi-agent decision making."""
    request_id: str
    transaction_data: Dict[str, Any]
    context_data: Dict[str, Any]
    required_agents: List[str]
    optional_agents: List[str]
    timeout_seconds: int
    aggregation_method: AggregationMethod
    conflict_resolution: ConflictResolutionStrategy
    minimum_agents: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionAggregator:
    """
    Multi-agent decision aggregation system.
    
    Collects decisions from multiple agents, resolves conflicts,
    and produces final aggregated decisions for fraud detection.
    """
    
    def __init__(self):
        """Initialize decision aggregator."""
        self.pending_decisions: Dict[str, Dict[str, Any]] = {}
        self.completed_decisions: Dict[str, AggregatedDecision] = {}
        
        # Agent expertise and weights
        self.agent_weights: Dict[str, float] = {}
        self.agent_expertise: Dict[str, Dict[str, float]] = {}
        
        # Decision history for learning
        self.decision_history: List[AggregatedDecision] = []
        
        # Configuration
        self.default_timeout = 30  # seconds
        self.max_decision_age = 3600  # 1 hour
        
        logger.info("Decision aggregator initialized")
    
    def set_agent_weight(self, agent_id: str, weight: float) -> None:
        """
        Set weight for an agent in decision aggregation.
        
        Args:
            agent_id: Agent identifier
            weight: Weight factor (0.0 to 2.0, default 1.0)
        """
        self.agent_weights[agent_id] = max(0.0, min(2.0, weight))
        logger.debug(f"Set weight for agent {agent_id}: {weight}")
    
    def set_agent_expertise(self, agent_id: str, expertise_areas: Dict[str, float]) -> None:
        """
        Set expertise scores for an agent in different areas.
        
        Args:
            agent_id: Agent identifier
            expertise_areas: Dictionary of area -> expertise score (0.0 to 1.0)
        """
        self.agent_expertise[agent_id] = {
            area: max(0.0, min(1.0, score))
            for area, score in expertise_areas.items()
        }
        logger.debug(f"Set expertise for agent {agent_id}: {expertise_areas}")
    
    def request_decision(self, decision_request: DecisionRequest) -> str:
        """
        Request decision from multiple agents.
        
        Args:
            decision_request: Decision request details
            
        Returns:
            Request ID for tracking
        """
        request_id = decision_request.request_id
        
        # Initialize pending decision tracking
        self.pending_decisions[request_id] = {
            "request": decision_request,
            "decisions": {},
            "start_time": datetime.now(),
            "status": "pending"
        }
        
        logger.info(f"Decision request {request_id} initiated for {len(decision_request.required_agents)} agents")
        return request_id
    
    def submit_agent_decision(self, request_id: str, agent_decision: AgentDecision) -> bool:
        """
        Submit decision from an agent.
        
        Args:
            request_id: Decision request ID
            agent_decision: Agent's decision
            
        Returns:
            True if decision was accepted
        """
        if request_id not in self.pending_decisions:
            logger.warning(f"Decision submission for unknown request: {request_id}")
            return False
        
        pending = self.pending_decisions[request_id]
        
        # Check if request has timed out
        elapsed = (datetime.now() - pending["start_time"]).total_seconds()
        if elapsed > pending["request"].timeout_seconds:
            logger.warning(f"Decision submission after timeout for request: {request_id}")
            return False
        
        # Add agent weight and expertise
        agent_decision.agent_weight = self.agent_weights.get(agent_decision.agent_id, 1.0)
        
        # Calculate expertise score for this decision context
        expertise_score = self._calculate_expertise_score(
            agent_decision.agent_id,
            pending["request"].transaction_data
        )
        agent_decision.expertise_score = expertise_score
        
        # Store decision
        pending["decisions"][agent_decision.agent_id] = agent_decision
        
        logger.debug(f"Received decision from {agent_decision.agent_id} for request {request_id}")
        
        # Check if we have enough decisions to aggregate
        self._check_aggregation_ready(request_id)
        
        return True
    
    def get_aggregated_decision(self, request_id: str) -> Optional[AggregatedDecision]:
        """
        Get aggregated decision if available.
        
        Args:
            request_id: Decision request ID
            
        Returns:
            Aggregated decision or None if not ready
        """
        return self.completed_decisions.get(request_id)
    
    def force_aggregation(self, request_id: str) -> Optional[AggregatedDecision]:
        """
        Force aggregation with available decisions.
        
        Args:
            request_id: Decision request ID
            
        Returns:
            Aggregated decision or None if no decisions available
        """
        if request_id not in self.pending_decisions:
            return None
        
        return self._aggregate_decisions(request_id, force=True)
    
    def _check_aggregation_ready(self, request_id: str) -> None:
        """Check if decision aggregation can be performed."""
        pending = self.pending_decisions[request_id]
        request = pending["request"]
        decisions = pending["decisions"]
        
        # Check if we have all required agents
        required_received = all(
            agent_id in decisions for agent_id in request.required_agents
        )
        
        # Check if we have minimum number of agents
        has_minimum = len(decisions) >= request.minimum_agents
        
        # Check timeout
        elapsed = (datetime.now() - pending["start_time"]).total_seconds()
        timed_out = elapsed >= request.timeout_seconds
        
        # Aggregate if ready
        if required_received or (has_minimum and timed_out):
            self._aggregate_decisions(request_id)
    
    def _aggregate_decisions(self, request_id: str, force: bool = False) -> Optional[AggregatedDecision]:
        """Aggregate decisions from multiple agents."""
        if request_id not in self.pending_decisions:
            return None
        
        start_time = datetime.now()
        pending = self.pending_decisions[request_id]
        request = pending["request"]
        agent_decisions = list(pending["decisions"].values())
        
        if not agent_decisions and not force:
            return None
        
        logger.info(f"Aggregating {len(agent_decisions)} decisions for request {request_id}")
        
        # Apply aggregation method
        final_decision, confidence_score, decision_weights = self._apply_aggregation_method(
            agent_decisions, request.aggregation_method
        )
        
        # Check for conflicts and apply resolution
        conflict_resolution = None
        if self._has_conflicts(agent_decisions):
            final_decision, confidence_score, conflict_resolution = self._resolve_conflicts(
                agent_decisions, request.conflict_resolution, final_decision, confidence_score
            )
        
        # Generate reasoning and evidence summaries
        reasoning_summary = self._generate_reasoning_summary(agent_decisions)
        evidence_summary = self._generate_evidence_summary(agent_decisions)
        
        # Calculate consensus level
        consensus_level = self._calculate_consensus_level(agent_decisions, final_decision)
        
        # Create aggregated decision
        aggregated_decision = AggregatedDecision(
            decision_id=request_id,
            final_decision=final_decision,
            confidence_score=confidence_score,
            aggregation_method=request.aggregation_method,
            conflict_resolution=conflict_resolution,
            agent_decisions=agent_decisions,
            decision_weights=decision_weights,
            reasoning_summary=reasoning_summary,
            evidence_summary=evidence_summary,
            consensus_level=consensus_level,
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            timestamp=datetime.now()
        )
        
        # Store completed decision
        self.completed_decisions[request_id] = aggregated_decision
        self.decision_history.append(aggregated_decision)
        
        # Clean up pending decision
        del self.pending_decisions[request_id]
        
        logger.info(f"Decision aggregation completed for {request_id}: {final_decision.value} (confidence: {confidence_score:.2f})")
        
        return aggregated_decision
    
    def _apply_aggregation_method(
        self, 
        decisions: List[AgentDecision], 
        method: AggregationMethod
    ) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Apply specified aggregation method."""
        if method == AggregationMethod.MAJORITY_VOTE:
            return self._majority_vote(decisions)
        elif method == AggregationMethod.WEIGHTED_VOTE:
            return self._weighted_vote(decisions)
        elif method == AggregationMethod.CONSENSUS:
            return self._consensus_decision(decisions)
        elif method == AggregationMethod.EXPERT_OVERRIDE:
            return self._expert_override(decisions)
        elif method == AggregationMethod.CONFIDENCE_WEIGHTED:
            return self._confidence_weighted(decisions)
        elif method == AggregationMethod.HYBRID:
            return self._hybrid_aggregation(decisions)
        else:
            # Default to majority vote
            return self._majority_vote(decisions)
    
    def _majority_vote(self, decisions: List[AgentDecision]) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Simple majority vote aggregation."""
        if not decisions:
            return DecisionType.REVIEW, 0.0, {}
        
        # Count votes
        vote_counts = {}
        for decision in decisions:
            if decision.decision not in vote_counts:
                vote_counts[decision.decision] = 0
            vote_counts[decision.decision] += 1
        
        # Find majority decision
        majority_decision = max(vote_counts.items(), key=lambda x: x[1])[0]
        
        # Calculate confidence as percentage of majority
        confidence = vote_counts[majority_decision] / len(decisions)
        
        # Equal weights for all agents
        weights = {d.agent_id: 1.0 for d in decisions}
        
        return majority_decision, confidence, weights
    
    def _weighted_vote(self, decisions: List[AgentDecision]) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Weighted vote based on agent weights and expertise."""
        if not decisions:
            return DecisionType.REVIEW, 0.0, {}
        
        # Calculate weighted votes
        weighted_votes = {}
        total_weight = 0.0
        
        for decision in decisions:
            weight = decision.agent_weight * decision.expertise_score
            total_weight += weight
            
            if decision.decision not in weighted_votes:
                weighted_votes[decision.decision] = 0.0
            weighted_votes[decision.decision] += weight
        
        # Find decision with highest weighted vote
        if total_weight == 0:
            return self._majority_vote(decisions)
        
        weighted_decision = max(weighted_votes.items(), key=lambda x: x[1])[0]
        confidence = weighted_votes[weighted_decision] / total_weight
        
        # Return actual weights used
        weights = {
            d.agent_id: d.agent_weight * d.expertise_score 
            for d in decisions
        }
        
        return weighted_decision, confidence, weights
    
    def _consensus_decision(self, decisions: List[AgentDecision]) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Consensus-based decision requiring agreement."""
        if not decisions:
            return DecisionType.REVIEW, 0.0, {}
        
        # Check if all decisions are the same
        first_decision = decisions[0].decision
        if all(d.decision == first_decision for d in decisions):
            # Perfect consensus
            avg_confidence = sum(d.confidence_score for d in decisions) / len(decisions)
            weights = {d.agent_id: 1.0 for d in decisions}
            return first_decision, avg_confidence, weights
        
        # No consensus - escalate to review
        weights = {d.agent_id: 1.0 for d in decisions}
        return DecisionType.REVIEW, 0.5, weights
    
    def _expert_override(self, decisions: List[AgentDecision]) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Expert agent can override other decisions."""
        if not decisions:
            return DecisionType.REVIEW, 0.0, {}
        
        # Find decision with highest expertise score
        expert_decision = max(decisions, key=lambda d: d.expertise_score)
        
        # If expert has high confidence, use their decision
        if expert_decision.confidence_score >= 0.8 and expert_decision.expertise_score >= 0.8:
            weights = {d.agent_id: 1.0 if d == expert_decision else 0.1 for d in decisions}
            return expert_decision.decision, expert_decision.confidence_score, weights
        
        # Otherwise fall back to weighted vote
        return self._weighted_vote(decisions)
    
    def _confidence_weighted(self, decisions: List[AgentDecision]) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Weight decisions by confidence scores."""
        if not decisions:
            return DecisionType.REVIEW, 0.0, {}
        
        # Calculate confidence-weighted votes
        confidence_votes = {}
        total_confidence = 0.0
        
        for decision in decisions:
            confidence = decision.confidence_score
            total_confidence += confidence
            
            if decision.decision not in confidence_votes:
                confidence_votes[decision.decision] = 0.0
            confidence_votes[decision.decision] += confidence
        
        if total_confidence == 0:
            return self._majority_vote(decisions)
        
        # Find decision with highest confidence-weighted vote
        final_decision = max(confidence_votes.items(), key=lambda x: x[1])[0]
        final_confidence = confidence_votes[final_decision] / total_confidence
        
        weights = {d.agent_id: d.confidence_score for d in decisions}
        
        return final_decision, final_confidence, weights
    
    def _hybrid_aggregation(self, decisions: List[AgentDecision]) -> Tuple[DecisionType, float, Dict[str, float]]:
        """Hybrid approach combining multiple methods."""
        if not decisions:
            return DecisionType.REVIEW, 0.0, {}
        
        # Try consensus first
        consensus_result = self._consensus_decision(decisions)
        if consensus_result[0] != DecisionType.REVIEW:
            return consensus_result
        
        # Check for expert override
        expert_result = self._expert_override(decisions)
        if expert_result[1] >= 0.8:  # High confidence expert decision
            return expert_result
        
        # Fall back to confidence-weighted decision
        return self._confidence_weighted(decisions)
    
    def _has_conflicts(self, decisions: List[AgentDecision]) -> bool:
        """Check if there are conflicting decisions."""
        if len(decisions) <= 1:
            return False
        
        first_decision = decisions[0].decision
        return not all(d.decision == first_decision for d in decisions)
    
    def _resolve_conflicts(
        self, 
        decisions: List[AgentDecision], 
        strategy: ConflictResolutionStrategy,
        current_decision: DecisionType,
        current_confidence: float
    ) -> Tuple[DecisionType, float, ConflictResolutionStrategy]:
        """Resolve conflicts between agent decisions."""
        if strategy == ConflictResolutionStrategy.MOST_CONSERVATIVE:
            return self._most_conservative_decision(decisions), current_confidence, strategy
        
        elif strategy == ConflictResolutionStrategy.HIGHEST_CONFIDENCE:
            highest_conf_decision = max(decisions, key=lambda d: d.confidence_score)
            return highest_conf_decision.decision, highest_conf_decision.confidence_score, strategy
        
        elif strategy == ConflictResolutionStrategy.EXPERT_PRIORITY:
            expert_decision = max(decisions, key=lambda d: d.expertise_score)
            return expert_decision.decision, expert_decision.confidence_score, strategy
        
        elif strategy == ConflictResolutionStrategy.WEIGHTED_AVERAGE:
            # Use weighted vote result
            return current_decision, current_confidence, strategy
        
        elif strategy == ConflictResolutionStrategy.ESCALATE_TO_HUMAN:
            return DecisionType.ESCALATE, 0.5, strategy
        
        else:
            return current_decision, current_confidence, strategy
    
    def _most_conservative_decision(self, decisions: List[AgentDecision]) -> DecisionType:
        """Choose the most conservative decision."""
        # Decision conservatism order (most to least conservative)
        conservatism_order = [
            DecisionType.DECLINE,
            DecisionType.ESCALATE,
            DecisionType.REVIEW,
            DecisionType.FLAG,
            DecisionType.APPROVE
        ]
        
        decision_types = [d.decision for d in decisions]
        
        for conservative_decision in conservatism_order:
            if conservative_decision in decision_types:
                return conservative_decision
        
        return DecisionType.REVIEW  # Default fallback
    
    def _calculate_expertise_score(self, agent_id: str, transaction_data: Dict[str, Any]) -> float:
        """Calculate expertise score for agent based on transaction context."""
        if agent_id not in self.agent_expertise:
            return 1.0  # Default expertise
        
        expertise_areas = self.agent_expertise[agent_id]
        
        # Determine relevant expertise areas based on transaction
        relevant_areas = []
        
        # Transaction amount-based expertise
        amount = transaction_data.get("amount", 0)
        if amount > 10000:
            relevant_areas.append("high_value_transactions")
        elif amount < 100:
            relevant_areas.append("micro_transactions")
        
        # Category-based expertise
        category = transaction_data.get("category", "")
        if category:
            relevant_areas.append(f"category_{category}")
        
        # Location-based expertise
        location = transaction_data.get("location", {})
        if location.get("country") != "US":
            relevant_areas.append("international_transactions")
        
        # Calculate weighted expertise score
        if not relevant_areas:
            return 1.0
        
        total_expertise = 0.0
        matched_areas = 0
        
        for area in relevant_areas:
            if area in expertise_areas:
                total_expertise += expertise_areas[area]
                matched_areas += 1
        
        if matched_areas == 0:
            return 1.0
        
        return total_expertise / matched_areas
    
    def _generate_reasoning_summary(self, decisions: List[AgentDecision]) -> List[str]:
        """Generate summary of reasoning from all agents."""
        all_reasoning = []
        
        for decision in decisions:
            for reason in decision.reasoning:
                if reason not in all_reasoning:
                    all_reasoning.append(reason)
        
        # Sort by frequency (most common first)
        reason_counts = {}
        for decision in decisions:
            for reason in decision.reasoning:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        sorted_reasoning = sorted(all_reasoning, key=lambda r: reason_counts.get(r, 0), reverse=True)
        
        return sorted_reasoning[:10]  # Top 10 reasons
    
    def _generate_evidence_summary(self, decisions: List[AgentDecision]) -> Dict[str, Any]:
        """Generate summary of evidence from all agents."""
        evidence_summary = {}
        
        # Collect all evidence keys
        all_keys = set()
        for decision in decisions:
            all_keys.update(decision.evidence.keys())
        
        # Aggregate evidence by key
        for key in all_keys:
            values = []
            for decision in decisions:
                if key in decision.evidence:
                    values.append(decision.evidence[key])
            
            if values:
                # Try to aggregate numerically if possible
                try:
                    numeric_values = [float(v) for v in values if isinstance(v, (int, float))]
                    if numeric_values:
                        evidence_summary[key] = {
                            "average": statistics.mean(numeric_values),
                            "min": min(numeric_values),
                            "max": max(numeric_values),
                            "count": len(numeric_values)
                        }
                    else:
                        evidence_summary[key] = {"values": values, "count": len(values)}
                except (ValueError, TypeError):
                    evidence_summary[key] = {"values": values, "count": len(values)}
        
        return evidence_summary
    
    def _calculate_consensus_level(self, decisions: List[AgentDecision], final_decision: DecisionType) -> float:
        """Calculate level of consensus among agents."""
        if not decisions:
            return 0.0
        
        # Count agents that agree with final decision
        agreeing_agents = sum(1 for d in decisions if d.decision == final_decision)
        
        # Basic consensus percentage
        basic_consensus = agreeing_agents / len(decisions)
        
        # Weight by confidence scores
        total_confidence = sum(d.confidence_score for d in decisions if d.decision == final_decision)
        max_possible_confidence = len(decisions)
        
        confidence_consensus = total_confidence / max_possible_confidence if max_possible_confidence > 0 else 0
        
        # Combine basic and confidence-weighted consensus
        return (basic_consensus + confidence_consensus) / 2
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about decision aggregation performance."""
        if not self.decision_history:
            return {"total_decisions": 0}
        
        # Basic statistics
        total_decisions = len(self.decision_history)
        
        # Decision distribution
        decision_counts = {}
        for decision in self.decision_history:
            decision_type = decision.final_decision
            decision_counts[decision_type] = decision_counts.get(decision_type, 0) + 1
        
        # Confidence statistics
        confidences = [d.confidence_score for d in self.decision_history]
        avg_confidence = statistics.mean(confidences)
        
        # Consensus statistics
        consensus_levels = [d.consensus_level for d in self.decision_history]
        avg_consensus = statistics.mean(consensus_levels)
        
        # Processing time statistics
        processing_times = [d.processing_time_ms for d in self.decision_history]
        avg_processing_time = statistics.mean(processing_times)
        
        # Aggregation method usage
        method_counts = {}
        for decision in self.decision_history:
            method = decision.aggregation_method
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            "total_decisions": total_decisions,
            "decision_distribution": {k.value: v for k, v in decision_counts.items()},
            "average_confidence": avg_confidence,
            "average_consensus": avg_consensus,
            "average_processing_time_ms": avg_processing_time,
            "aggregation_methods": {k.value: v for k, v in method_counts.items()},
            "confidence_range": {"min": min(confidences), "max": max(confidences)},
            "consensus_range": {"min": min(consensus_levels), "max": max(consensus_levels)}
        }
    
    def cleanup_old_decisions(self, max_age_hours: int = 24) -> int:
        """Clean up old completed decisions."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean completed decisions
        old_decisions = [
            decision_id for decision_id, decision in self.completed_decisions.items()
            if decision.timestamp < cutoff_time
        ]
        
        for decision_id in old_decisions:
            del self.completed_decisions[decision_id]
        
        # Clean decision history
        self.decision_history = [
            decision for decision in self.decision_history
            if decision.timestamp >= cutoff_time
        ]
        
        logger.info(f"Cleaned up {len(old_decisions)} old decisions")
        return len(old_decisions)