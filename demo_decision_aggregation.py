#!/usr/bin/env python3
"""
Demo: Decision Aggregation System

Demonstrates multi-agent decision collection, conflict resolution,
and weighted voting for coordinated fraud detection decisions.
"""

import logging
from datetime import datetime
from agent_coordination.decision_aggregation import (
    DecisionAggregator, AgentDecision, DecisionRequest, 
    DecisionType, AggregationMethod, ConflictResolutionStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_decision(decision: AgentDecision, indent: str = ""):
    """Print agent decision details."""
    print(f"{indent}Agent: {decision.agent_id} ({decision.agent_type})")
    print(f"{indent}Decision: {decision.decision.value.upper()}")
    print(f"{indent}Confidence: {decision.confidence_score:.2f} ({decision.confidence_level.value})")
    print(f"{indent}Reasoning: {', '.join(decision.reasoning)}")
    print(f"{indent}Processing Time: {decision.processing_time_ms:.1f}ms")
    print()


def print_aggregated_decision(aggregated):
    """Print aggregated decision details."""
    print(f"Final Decision: {aggregated.final_decision.value.upper()}")
    print(f"Confidence: {aggregated.confidence_score:.2f}")
    print(f"Consensus Level: {aggregated.consensus_level:.2f}")
    print(f"Aggregation Method: {aggregated.aggregation_method.value}")
    if aggregated.conflict_resolution:
        print(f"Conflict Resolution: {aggregated.conflict_resolution.value}")
    print(f"Processing Time: {aggregated.processing_time_ms:.1f}ms")
    print(f"\nParticipating Agents: {', '.join(aggregated.participating_agents)}")
    print(f"\nDecision Distribution:")
    for decision_type, count in aggregated.decision_distribution.items():
        print(f"  {decision_type.value}: {count}")
    print(f"\nReasoning Summary:")
    for i, reason in enumerate(aggregated.reasoning_summary[:5], 1):
        print(f"  {i}. {reason}")


def demo_scenario_1_unanimous_approval():
    """Scenario 1: All agents agree - unanimous approval."""
    print_section("Scenario 1: Unanimous Approval")
    
    aggregator = DecisionAggregator()
    
    # Create transaction data
    transaction_data = {
        "transaction_id": "TXN-001",
        "amount": 50.00,
        "merchant": "Starbucks",
        "location": {"city": "New York", "state": "NY", "country": "US"},
        "user_id": "USER-123"
    }
    
    print("Transaction Details:")
    print(f"  Amount: ${transaction_data['amount']}")
    print(f"  Merchant: {transaction_data['merchant']}")
    location = transaction_data['location']
    location_str = f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    print(f"  Location: {location_str}")
    print()
    
    # Create decision request
    request = DecisionRequest(
        request_id="REQ-001",
        transaction_data=transaction_data,
        context_data={},
        required_agents=["transaction_analyzer", "pattern_detector", "risk_assessor"],
        optional_agents=[],
        timeout_seconds=30,
        aggregation_method=AggregationMethod.CONSENSUS,
        conflict_resolution=ConflictResolutionStrategy.WEIGHTED_AVERAGE
    )
    
    request_id = aggregator.request_decision(request)
    
    # All agents approve
    agent_decisions = [
        AgentDecision(
            agent_id="transaction_analyzer",
            agent_type="transaction_analyzer",
            decision=DecisionType.APPROVE,
            confidence_score=0.95,
            reasoning=["Low transaction amount", "Known merchant", "Normal time of day"],
            evidence={"amount_risk": 0.05, "merchant_verified": True, "time_risk": 0.1},
            processing_time_ms=120.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="pattern_detector",
            agent_type="pattern_detector",
            decision=DecisionType.APPROVE,
            confidence_score=0.92,
            reasoning=["Consistent with user pattern", "No anomalies detected"],
            evidence={"pattern_match": 0.98, "anomaly_score": 0.02},
            processing_time_ms=180.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="risk_assessor",
            agent_type="risk_assessor",
            decision=DecisionType.APPROVE,
            confidence_score=0.90,
            reasoning=["Low-risk location", "Normal velocity"],
            evidence={"location_risk": 0.1, "velocity_score": 0.15},
            processing_time_ms=150.0,
            timestamp=datetime.now()
        )
    ]
    
    print("Agent Decisions:")
    print("-" * 80)
    for decision in agent_decisions:
        aggregator.submit_agent_decision(request_id, decision)
        print_decision(decision, "  ")
    
    # Get aggregated decision
    aggregated = aggregator.get_aggregated_decision(request_id)
    
    print("Aggregated Decision:")
    print("-" * 80)
    print_aggregated_decision(aggregated)


def demo_scenario_2_conflicting_decisions():
    """Scenario 2: Agents disagree - conflict resolution needed."""
    print_section("Scenario 2: Conflicting Decisions - High-Value Transaction")
    
    aggregator = DecisionAggregator()
    
    # Set agent weights
    aggregator.set_agent_weight("transaction_analyzer", 1.5)
    aggregator.set_agent_weight("pattern_detector", 1.2)
    aggregator.set_agent_weight("risk_assessor", 1.8)
    aggregator.set_agent_weight("compliance_checker", 2.0)
    
    transaction_data = {
        "transaction_id": "TXN-002",
        "amount": 15000.00,
        "merchant": "Electronics Store",
        "location": {"city": "Tokyo", "country": "JP"},
        "user_id": "USER-456"
    }
    
    print("Transaction Details:")
    print(f"  Amount: ${transaction_data['amount']:,.2f}")
    print(f"  Merchant: {transaction_data['merchant']}")
    location = transaction_data['location']
    location_str = f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    print(f"  Location: {location_str}")
    print()
    
    request = DecisionRequest(
        request_id="REQ-002",
        transaction_data=transaction_data,
        context_data={},
        required_agents=["transaction_analyzer", "pattern_detector", "risk_assessor", "compliance_checker"],
        optional_agents=[],
        timeout_seconds=30,
        aggregation_method=AggregationMethod.WEIGHTED_VOTE,
        conflict_resolution=ConflictResolutionStrategy.MOST_CONSERVATIVE
    )
    
    request_id = aggregator.request_decision(request)
    
    # Mixed decisions
    agent_decisions = [
        AgentDecision(
            agent_id="transaction_analyzer",
            agent_type="transaction_analyzer",
            decision=DecisionType.FLAG,
            confidence_score=0.75,
            reasoning=["High transaction amount", "Unusual merchant category"],
            evidence={"amount_risk": 0.8, "merchant_risk": 0.6},
            processing_time_ms=140.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="pattern_detector",
            agent_type="pattern_detector",
            decision=DecisionType.REVIEW,
            confidence_score=0.82,
            reasoning=["Deviation from normal pattern", "First foreign transaction"],
            evidence={"pattern_match": 0.45, "anomaly_score": 0.75},
            processing_time_ms=220.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="risk_assessor",
            agent_type="risk_assessor",
            decision=DecisionType.DECLINE,
            confidence_score=0.88,
            reasoning=["High-risk foreign location", "Unusual amount for user"],
            evidence={"location_risk": 0.9, "amount_deviation": 0.85},
            processing_time_ms=190.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="compliance_checker",
            agent_type="compliance_checker",
            decision=DecisionType.REVIEW,
            confidence_score=0.80,
            reasoning=["AML threshold exceeded", "Additional verification required"],
            evidence={"aml_flag": True, "verification_needed": True},
            processing_time_ms=250.0,
            timestamp=datetime.now()
        )
    ]
    
    print("Agent Decisions:")
    print("-" * 80)
    for decision in agent_decisions:
        aggregator.submit_agent_decision(request_id, decision)
        print_decision(decision, "  ")
    
    aggregated = aggregator.get_aggregated_decision(request_id)
    
    print("Aggregated Decision:")
    print("-" * 80)
    print_aggregated_decision(aggregated)
    
    print("\nAgent Weights Applied:")
    for agent_id, weight in aggregated.decision_weights.items():
        print(f"  {agent_id}: {weight:.2f}")


def demo_scenario_3_expert_override():
    """Scenario 3: Expert agent overrides others."""
    print_section("Scenario 3: Expert Override - Compliance Agent Priority")
    
    aggregator = DecisionAggregator()
    
    # Set expertise scores
    aggregator.set_agent_expertise("compliance_checker", {
        "high_value_transactions": 0.95,
        "regulatory_compliance": 0.98,
        "international_transactions": 0.90
    })
    
    transaction_data = {
        "transaction_id": "TXN-003",
        "amount": 25000.00,
        "merchant": "Wire Transfer",
        "location": {"city": "Unknown", "country": "XX"},
        "user_id": "USER-789"
    }
    
    print("Transaction Details:")
    print(f"  Amount: ${transaction_data['amount']:,.2f}")
    print(f"  Merchant: {transaction_data['merchant']}")
    location = transaction_data['location']
    location_str = f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    print(f"  Location: {location_str}")
    print()
    
    request = DecisionRequest(
        request_id="REQ-003",
        transaction_data=transaction_data,
        context_data={},
        required_agents=["transaction_analyzer", "risk_assessor", "compliance_checker"],
        optional_agents=[],
        timeout_seconds=30,
        aggregation_method=AggregationMethod.EXPERT_OVERRIDE,
        conflict_resolution=ConflictResolutionStrategy.EXPERT_PRIORITY
    )
    
    request_id = aggregator.request_decision(request)
    
    agent_decisions = [
        AgentDecision(
            agent_id="transaction_analyzer",
            agent_type="transaction_analyzer",
            decision=DecisionType.REVIEW,
            confidence_score=0.70,
            reasoning=["High amount", "Wire transfer category"],
            evidence={"amount_risk": 0.85},
            processing_time_ms=130.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="risk_assessor",
            agent_type="risk_assessor",
            decision=DecisionType.FLAG,
            confidence_score=0.75,
            reasoning=["High-risk country", "Large amount"],
            evidence={"location_risk": 0.95, "amount_risk": 0.85},
            processing_time_ms=170.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="compliance_checker",
            agent_type="compliance_checker",
            decision=DecisionType.DECLINE,
            confidence_score=0.92,
            reasoning=["Sanctions list match", "AML violation risk", "Regulatory block required"],
            evidence={"sanctions_match": True, "aml_risk": 0.95, "regulatory_block": True},
            processing_time_ms=280.0,
            timestamp=datetime.now(),
            expertise_score=0.95  # High expertise
        )
    ]
    
    print("Agent Decisions:")
    print("-" * 80)
    for decision in agent_decisions:
        aggregator.submit_agent_decision(request_id, decision)
        print_decision(decision, "  ")
        if decision.agent_id == "compliance_checker":
            print(f"  ⭐ Expert Agent (Expertise: {decision.expertise_score:.2f})\n")
    
    aggregated = aggregator.get_aggregated_decision(request_id)
    
    print("Aggregated Decision:")
    print("-" * 80)
    print_aggregated_decision(aggregated)
    print("\n⚠️  Expert agent (compliance_checker) decision took priority due to high expertise and confidence.")


def demo_scenario_4_confidence_weighted():
    """Scenario 4: Confidence-weighted aggregation."""
    print_section("Scenario 4: Confidence-Weighted Aggregation")
    
    aggregator = DecisionAggregator()
    
    transaction_data = {
        "transaction_id": "TXN-004",
        "amount": 500.00,
        "merchant": "Online Retailer",
        "location": {"city": "Los Angeles", "state": "CA", "country": "US"},
        "user_id": "USER-321"
    }
    
    print("Transaction Details:")
    print(f"  Amount: ${transaction_data['amount']}")
    print(f"  Merchant: {transaction_data['merchant']}")
    location = transaction_data['location']
    location_str = f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    print(f"  Location: {location_str}")
    print()
    
    request = DecisionRequest(
        request_id="REQ-004",
        transaction_data=transaction_data,
        context_data={},
        required_agents=["transaction_analyzer", "pattern_detector", "risk_assessor"],
        optional_agents=[],
        timeout_seconds=30,
        aggregation_method=AggregationMethod.CONFIDENCE_WEIGHTED,
        conflict_resolution=ConflictResolutionStrategy.HIGHEST_CONFIDENCE
    )
    
    request_id = aggregator.request_decision(request)
    
    # Varying confidence levels
    agent_decisions = [
        AgentDecision(
            agent_id="transaction_analyzer",
            agent_type="transaction_analyzer",
            decision=DecisionType.APPROVE,
            confidence_score=0.65,  # Medium confidence
            reasoning=["Moderate amount", "Known merchant type"],
            evidence={"amount_risk": 0.35},
            processing_time_ms=110.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="pattern_detector",
            agent_type="pattern_detector",
            decision=DecisionType.APPROVE,
            confidence_score=0.95,  # Very high confidence
            reasoning=["Perfect pattern match", "Consistent behavior", "Historical approval"],
            evidence={"pattern_match": 0.99, "historical_approval_rate": 0.98},
            processing_time_ms=200.0,
            timestamp=datetime.now()
        ),
        AgentDecision(
            agent_id="risk_assessor",
            agent_type="risk_assessor",
            decision=DecisionType.FLAG,
            confidence_score=0.55,  # Low confidence
            reasoning=["Slightly elevated velocity"],
            evidence={"velocity_score": 0.45},
            processing_time_ms=160.0,
            timestamp=datetime.now()
        )
    ]
    
    print("Agent Decisions:")
    print("-" * 80)
    for decision in agent_decisions:
        aggregator.submit_agent_decision(request_id, decision)
        print_decision(decision, "  ")
    
    aggregated = aggregator.get_aggregated_decision(request_id)
    
    print("Aggregated Decision:")
    print("-" * 80)
    print_aggregated_decision(aggregated)
    print("\n💡 High-confidence pattern_detector decision had more weight in final outcome.")


def demo_statistics():
    """Demo: Decision statistics and analytics."""
    print_section("Decision Statistics and Analytics")
    
    aggregator = DecisionAggregator()
    
    # Process multiple decisions
    print("Processing 10 sample decisions...")
    print()
    
    for i in range(10):
        request = DecisionRequest(
            request_id=f"STATS-{i:03d}",
            transaction_data={"amount": 100.0 * (i + 1)},
            context_data={},
            required_agents=["agent_1", "agent_2"],
            optional_agents=[],
            timeout_seconds=30,
            aggregation_method=AggregationMethod.MAJORITY_VOTE,
            conflict_resolution=ConflictResolutionStrategy.WEIGHTED_AVERAGE
        )
        
        request_id = aggregator.request_decision(request)
        
        # Vary decisions based on amount
        decision_type = DecisionType.APPROVE if i < 6 else DecisionType.DECLINE
        
        decisions = [
            AgentDecision(
                agent_id="agent_1",
                agent_type="test",
                decision=decision_type,
                confidence_score=0.7 + (i * 0.02),
                reasoning=["Test reasoning"],
                evidence={"test": True},
                processing_time_ms=100.0 + (i * 10),
                timestamp=datetime.now()
            ),
            AgentDecision(
                agent_id="agent_2",
                agent_type="test",
                decision=decision_type,
                confidence_score=0.75 + (i * 0.015),
                reasoning=["Test reasoning"],
                evidence={"test": True},
                processing_time_ms=120.0 + (i * 8),
                timestamp=datetime.now()
            )
        ]
        
        for decision in decisions:
            aggregator.submit_agent_decision(request_id, decision)
    
    # Get statistics
    stats = aggregator.get_decision_statistics()
    
    print("Decision Aggregation Statistics:")
    print("-" * 80)
    print(f"Total Decisions Processed: {stats['total_decisions']}")
    print(f"Average Confidence: {stats['average_confidence']:.2f}")
    print(f"Average Consensus: {stats['average_consensus']:.2f}")
    print(f"Average Processing Time: {stats['average_processing_time_ms']:.1f}ms")
    print()
    
    print("Decision Distribution:")
    for decision_type, count in stats['decision_distribution'].items():
        percentage = (count / stats['total_decisions']) * 100
        print(f"  {decision_type}: {count} ({percentage:.1f}%)")
    print()
    
    print("Confidence Range:")
    print(f"  Min: {stats['confidence_range']['min']:.2f}")
    print(f"  Max: {stats['confidence_range']['max']:.2f}")
    print()
    
    print("Consensus Range:")
    print(f"  Min: {stats['consensus_range']['min']:.2f}")
    print(f"  Max: {stats['consensus_range']['max']:.2f}")


def main():
    """Run all demo scenarios."""
    print("\n" + "="*80)
    print("  DECISION AGGREGATION SYSTEM DEMO")
    print("  Multi-Agent Fraud Detection Decision Coordination")
    print("="*80)
    
    try:
        # Run scenarios
        demo_scenario_1_unanimous_approval()
        demo_scenario_2_conflicting_decisions()
        demo_scenario_3_expert_override()
        demo_scenario_4_confidence_weighted()
        demo_statistics()
        
        print_section("Demo Complete")
        print("✅ All scenarios executed successfully!")
        print()
        print("Key Features Demonstrated:")
        print("  • Unanimous decision consensus")
        print("  • Conflict resolution strategies")
        print("  • Weighted voting with agent priorities")
        print("  • Expert agent override capabilities")
        print("  • Confidence-weighted aggregation")
        print("  • Decision statistics and analytics")
        print()
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}", exc_info=True)
        print(f"\n❌ Demo failed: {str(e)}")


if __name__ == "__main__":
    main()
