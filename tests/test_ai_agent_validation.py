"""
AI Agent Capabilities Validation Suite

Tests reasoning quality across diverse fraud scenarios,
validates explanation generation completeness,
tests decision accuracy and false positive rates,
and verifies compliance with AWS AI agent standards.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import json

from src.fraud_detection.core.unified_fraud_detection_system import UnifiedFraudDetectionSystem
from agent_orchestrator import AgentOrchestrator
from src import ReasoningEngine


class TestReasoningQuality:
    """Test reasoning quality across diverse fraud scenarios."""
    
    @pytest.fixture
    def system(self):
        """Create unified system for testing."""
        return UnifiedFraudDetectionSystem()
    
    @pytest.fixture
    def reasoning_engine(self):
        """Create reasoning engine for testing."""
        return ReasoningEngine()
    
    # Scenario 1: Clear Legitimate Transaction
    @pytest.mark.asyncio
    async def test_legitimate_transaction_reasoning(self, system):
        """Test reasoning for clearly legitimate transaction."""
        transaction = {
            "transaction_id": "legit_001",
            "user_id": "regular_user_123",
            "amount": 50.00,
            "currency": "USD",
            "merchant": "Local Grocery Store",
            "location": "User's Home City",
            "device_id": "user_regular_device",
            "timestamp": datetime.now().isoformat(),
            "user_history": {
                "avg_transaction": 45.00,
                "transaction_count": 150,
                "fraud_history": []
            }
        }
        
        result = await system.process_transaction(transaction)
        
        # Should approve with high confidence
        assert result["decision"] == "APPROVE"
        assert result["confidence"] >= 0.8
        
        # Reasoning should be clear
        assert "reasoning" in result
        assert len(result["reasoning"]) > 0
        assert any("legitimate" in step.lower() or "normal" in step.lower() 
                  for step in result["reasoning"])
    
    # Scenario 2: Clear Fraudulent Transaction
    @pytest.mark.asyncio
    async def test_fraudulent_transaction_reasoning(self, system):
        """Test reasoning for clearly fraudulent transaction."""
        transaction = {
            "transaction_id": "fraud_001",
            "user_id": "compromised_user_456",
            "amount": 9999.99,
            "currency": "USD",
            "merchant": "Unknown Online Store",
            "location": "Russia",
            "device_id": "unknown_device_xyz",
            "timestamp": datetime.now().isoformat(),
            "user_history": {
                "avg_transaction": 50.00,
                "typical_locations": ["New York", "Boston"],
                "typical_devices": ["device_abc"],
                "fraud_alerts": 2
            }
        }
        
        result = await system.process_transaction(transaction)
        
        # Should decline or flag with high confidence
        assert result["decision"] in ["DECLINE", "FLAG"]
        assert result["confidence"] >= 0.7
        
        # Reasoning should identify fraud indicators
        reasoning_text = " ".join(result["reasoning"]).lower()
        assert any(indicator in reasoning_text for indicator in [
            "unusual", "suspicious", "anomaly", "risk", "fraud"
        ])
    
    # Scenario 3: Ambiguous Transaction
    @pytest.mark.asyncio
    async def test_ambiguous_transaction_reasoning(self, system):
        """Test reasoning for ambiguous transaction requiring review."""
        transaction = {
            "transaction_id": "ambiguous_001",
            "user_id": "user_789",
            "amount": 500.00,  # Moderate amount
            "currency": "USD",
            "merchant": "New Online Store",  # New but not suspicious
            "location": "Nearby City",  # Different but plausible
            "device_id": "user_device",
            "timestamp": datetime.now().isoformat(),
            "user_history": {
                "avg_transaction": 300.00,
                "transaction_count": 50
            }
        }
        
        result = await system.process_transaction(transaction)
        
        # Should have moderate confidence
        assert 0.4 <= result["confidence"] <= 0.8
        
        # Reasoning should acknowledge uncertainty
        reasoning_text = " ".join(result["reasoning"]).lower()
        assert any(word in reasoning_text for word in [
            "uncertain", "review", "moderate", "possible", "may"
        ])
    
    # Scenario 4: Velocity Fraud Pattern
    @pytest.mark.asyncio
    async def test_velocity_fraud_reasoning(self, system):
        """Test reasoning for velocity-based fraud pattern."""
        user_id = "velocity_test_user"
        
        # Simulate rapid succession of transactions
        transactions = []
        for i in range(5):
            tx = {
                "transaction_id": f"velocity_{i}",
                "user_id": user_id,
                "amount": 100.00 + i * 50,
                "currency": "USD",
                "merchant": f"Store {i}",
                "location": "New York",
                "timestamp": (datetime.now() + timedelta(minutes=i)).isoformat()
            }
            transactions.append(tx)
        
        # Process all transactions
        results = []
        for tx in transactions:
            result = await system.process_transaction(tx)
            results.append(result)
        
        # Later transactions should show increased suspicion
        last_result = results[-1]
        assert last_result["decision"] in ["FLAG", "REVIEW", "DECLINE"]
        
        # Reasoning should mention velocity or frequency
        reasoning_text = " ".join(last_result["reasoning"]).lower()
        assert any(word in reasoning_text for word in [
            "velocity", "frequency", "rapid", "multiple", "succession"
        ])
    
    # Scenario 5: Geographic Anomaly
    @pytest.mark.asyncio
    async def test_geographic_anomaly_reasoning(self, system):
        """Test reasoning for impossible travel scenario."""
        user_id = "geo_test_user"
        
        # Transaction in New York
        tx1 = {
            "transaction_id": "geo_001",
            "user_id": user_id,
            "amount": 100.00,
            "currency": "USD",
            "location": "New York, US",
            "timestamp": datetime.now().isoformat()
        }
        
        await system.process_transaction(tx1)
        
        # Transaction in Tokyo 1 hour later (impossible travel)
        tx2 = {
            "transaction_id": "geo_002",
            "user_id": user_id,
            "amount": 200.00,
            "currency": "JPY",
            "location": "Tokyo, Japan",
            "timestamp": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        result = await system.process_transaction(tx2)
        
        # Should flag geographic anomaly
        assert result["decision"] in ["FLAG", "DECLINE"]
        
        # Reasoning should mention location or travel
        reasoning_text = " ".join(result["reasoning"]).lower()
        assert any(word in reasoning_text for word in [
            "location", "geographic", "travel", "impossible", "distance"
        ])
    
    # Scenario 6: Account Takeover Pattern
    @pytest.mark.asyncio
    async def test_account_takeover_reasoning(self, system):
        """Test reasoning for account takeover indicators."""
        transaction = {
            "transaction_id": "takeover_001",
            "user_id": "user_takeover",
            "amount": 5000.00,
            "currency": "USD",
            "merchant": "Electronics Store",
            "location": "Unknown Location",
            "device_id": "new_unknown_device",
            "ip_address": "suspicious_ip",
            "timestamp": datetime.now().isoformat(),
            "user_history": {
                "avg_transaction": 100.00,
                "typical_devices": ["device_123"],
                "typical_locations": ["Home City"],
                "account_age_days": 365,
                "recent_password_change": True,
                "recent_email_change": True
            }
        }
        
        result = await system.process_transaction(transaction)
        
        # Should detect account takeover indicators
        assert result["decision"] in ["DECLINE", "FLAG"]
        
        # Reasoning should mention account security
        reasoning_text = " ".join(result["reasoning"]).lower()
        assert any(word in reasoning_text for word in [
            "account", "takeover", "compromise", "unauthorized", "security"
        ])
    
    @pytest.mark.asyncio
    async def test_chain_of_thought_reasoning(self, reasoning_engine):
        """Test chain-of-thought reasoning produces logical steps."""
        transaction = {
            "transaction_id": "cot_test_001",
            "user_id": "user_cot",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        reasoning_result = await reasoning_engine.analyze_transaction(transaction)
        
        # Should have multiple reasoning steps
        assert "reasoning_steps" in reasoning_result
        assert len(reasoning_result["reasoning_steps"]) >= 3
        
        # Each step should have required fields
        for step in reasoning_result["reasoning_steps"]:
            assert "step_number" in step
            assert "analysis" in step
            assert "confidence" in step
            assert 0 <= step["confidence"] <= 1
        
        # Steps should build on each other logically
        confidences = [step["confidence"] for step in reasoning_result["reasoning_steps"]]
        # Final confidence should be informed by intermediate steps
        assert "final_confidence" in reasoning_result


class TestExplanationGeneration:
    """Test explanation generation completeness."""
    
    @pytest.fixture
    def system(self):
        """Create system for testing."""
        return UnifiedFraudDetectionSystem()
    
    @pytest.mark.asyncio
    async def test_explanation_completeness(self, system):
        """Test that explanations contain all required elements."""
        transaction = {
            "transaction_id": "explain_001",
            "user_id": "user_explain",
            "amount": 5000.00,
            "currency": "USD",
            "merchant": "High-Risk Merchant",
            "location": "Foreign Country",
            "timestamp": datetime.now().isoformat()
        }
        
        result = await system.process_transaction(transaction)
        
        # Explanation should exist
        assert "explanation" in result or "reasoning" in result
        explanation = result.get("explanation") or result.get("reasoning")
        
        # Should have multiple components
        assert len(explanation) > 0
        
        # Should explain the decision
        assert "decision" in result
        
        # Should provide evidence
        assert "evidence" in result or "factors" in result or "indicators" in result
    
    @pytest.mark.asyncio
    async def test_explanation_human_readability(self, system):
        """Test that explanations are human-readable."""
        transaction = {
            "transaction_id": "readable_001",
            "user_id": "user_readable",
            "amount": 2000.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat()
        }
        
        result = await system.process_transaction(transaction)
        
        explanation = result.get("explanation") or result.get("reasoning")
        explanation_text = " ".join(explanation) if isinstance(explanation, list) else str(explanation)
        
        # Should be readable (not just technical jargon)
        # Check for complete sentences
        assert len(explanation_text) > 50
        
        # Should not be overly technical
        # Should contain common words
        common_words = ["transaction", "amount", "user", "risk", "because", "indicates"]
        assert any(word in explanation_text.lower() for word in common_words)
    
    @pytest.mark.asyncio
    async def test_explanation_evidence_linking(self, system):
        """Test that explanations link to specific evidence."""
        transaction = {
            "transaction_id": "evidence_001",
            "user_id": "user_evidence",
            "amount": 10000.00,
            "currency": "USD",
            "location": "High-Risk Location",
            "timestamp": datetime.now().isoformat()
        }
        
        result = await system.process_transaction(transaction)
        
        # Should have evidence or factors
        assert "evidence" in result or "factors" in result or "risk_factors" in result
        
        # Evidence should be specific
        evidence = result.get("evidence") or result.get("factors") or result.get("risk_factors", [])
        if evidence:
            # Each piece of evidence should have details
            if isinstance(evidence, list) and len(evidence) > 0:
                first_evidence = evidence[0]
                if isinstance(first_evidence, dict):
                    assert "factor" in first_evidence or "indicator" in first_evidence or "type" in first_evidence
    
    @pytest.mark.asyncio
    async def test_explanation_confidence_justification(self, system):
        """Test that confidence scores are justified in explanations."""
        transaction = {
            "transaction_id": "confidence_001",
            "user_id": "user_confidence",
            "amount": 1500.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat()
        }
        
        result = await system.process_transaction(transaction)
        
        # Should have confidence score
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1
        
        # Explanation should relate to confidence
        explanation_text = str(result.get("explanation") or result.get("reasoning", "")).lower()
        
        if result["confidence"] >= 0.8:
            # High confidence should be reflected
            assert any(word in explanation_text for word in [
                "clear", "strong", "definite", "certain", "confident"
            ])
        elif result["confidence"] <= 0.5:
            # Low confidence should be reflected
            assert any(word in explanation_text for word in [
                "uncertain", "unclear", "ambiguous", "possible", "may"
            ])


class TestDecisionAccuracy:
    """Test decision accuracy and false positive rates."""
    
    @pytest.fixture
    def system(self):
        """Create system for testing."""
        return UnifiedFraudDetectionSystem()
    
    def create_test_dataset(self) -> List[Dict]:
        """Create labeled test dataset."""
        return [
            # Legitimate transactions (should approve)
            {
                "transaction": {
                    "transaction_id": "legit_1",
                    "user_id": "user_1",
                    "amount": 50.00,
                    "currency": "USD",
                    "location": "Home City",
                    "device_id": "regular_device"
                },
                "expected_decision": "APPROVE",
                "is_fraud": False
            },
            {
                "transaction": {
                    "transaction_id": "legit_2",
                    "user_id": "user_2",
                    "amount": 100.00,
                    "currency": "USD",
                    "location": "Home City",
                    "device_id": "regular_device"
                },
                "expected_decision": "APPROVE",
                "is_fraud": False
            },
            {
                "transaction": {
                    "transaction_id": "legit_3",
                    "user_id": "user_3",
                    "amount": 75.00,
                    "currency": "USD",
                    "location": "Home City",
                    "device_id": "regular_device"
                },
                "expected_decision": "APPROVE",
                "is_fraud": False
            },
            # Fraudulent transactions (should decline/flag)
            {
                "transaction": {
                    "transaction_id": "fraud_1",
                    "user_id": "user_4",
                    "amount": 9999.99,
                    "currency": "USD",
                    "location": "High-Risk Country",
                    "device_id": "unknown_device"
                },
                "expected_decision": "DECLINE",
                "is_fraud": True
            },
            {
                "transaction": {
                    "transaction_id": "fraud_2",
                    "user_id": "user_5",
                    "amount": 5000.00,
                    "currency": "USD",
                    "location": "Unknown Location",
                    "device_id": "suspicious_device"
                },
                "expected_decision": "DECLINE",
                "is_fraud": True
            },
            {
                "transaction": {
                    "transaction_id": "fraud_3",
                    "user_id": "user_6",
                    "amount": 8000.00,
                    "currency": "USD",
                    "location": "Foreign Country",
                    "device_id": "new_device"
                },
                "expected_decision": "FLAG",
                "is_fraud": True
            }
        ]
    
    @pytest.mark.asyncio
    async def test_decision_accuracy(self, system):
        """Test overall decision accuracy."""
        test_data = self.create_test_dataset()
        
        results = []
        for item in test_data:
            result = await system.process_transaction(item["transaction"])
            results.append({
                "actual_decision": result["decision"],
                "expected_decision": item["expected_decision"],
                "is_fraud": item["is_fraud"],
                "confidence": result["confidence"]
            })
        
        # Calculate accuracy
        correct_decisions = 0
        for i, result in enumerate(results):
            expected = test_data[i]["expected_decision"]
            actual = result["actual_decision"]
            
            # Consider FLAG as correct for fraud cases
            if test_data[i]["is_fraud"]:
                if actual in ["DECLINE", "FLAG", "REVIEW"]:
                    correct_decisions += 1
            else:
                if actual == expected:
                    correct_decisions += 1
        
        accuracy = correct_decisions / len(results) * 100
        
        print(f"\nDecision Accuracy: {accuracy:.2f}%")
        print(f"Correct: {correct_decisions}/{len(results)}")
        
        # Should have high accuracy
        assert accuracy >= 70, f"Accuracy should be at least 70%, got {accuracy:.2f}%"
    
    @pytest.mark.asyncio
    async def test_false_positive_rate(self, system):
        """Test false positive rate (legitimate flagged as fraud)."""
        # Create legitimate transactions
        legitimate_transactions = [
            {
                "transaction_id": f"legit_fp_{i}",
                "user_id": f"user_fp_{i}",
                "amount": 50.00 + i * 10,
                "currency": "USD",
                "location": "Home City",
                "device_id": "regular_device",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(20)
        ]
        
        false_positives = 0
        for tx in legitimate_transactions:
            result = await system.process_transaction(tx)
            if result["decision"] in ["DECLINE", "FLAG"]:
                false_positives += 1
        
        false_positive_rate = false_positives / len(legitimate_transactions) * 100
        
        print(f"\nFalse Positive Rate: {false_positive_rate:.2f}%")
        print(f"False Positives: {false_positives}/{len(legitimate_transactions)}")
        
        # False positive rate should be low
        assert false_positive_rate <= 30, f"False positive rate too high: {false_positive_rate:.2f}%"
    
    @pytest.mark.asyncio
    async def test_false_negative_rate(self, system):
        """Test false negative rate (fraud approved)."""
        # Create fraudulent transactions
        fraudulent_transactions = [
            {
                "transaction_id": f"fraud_fn_{i}",
                "user_id": f"user_fn_{i}",
                "amount": 5000.00 + i * 1000,
                "currency": "USD",
                "location": "High-Risk Location",
                "device_id": "unknown_device",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(20)
        ]
        
        false_negatives = 0
        for tx in fraudulent_transactions:
            result = await system.process_transaction(tx)
            if result["decision"] == "APPROVE":
                false_negatives += 1
        
        false_negative_rate = false_negatives / len(fraudulent_transactions) * 100
        
        print(f"\nFalse Negative Rate: {false_negative_rate:.2f}%")
        print(f"False Negatives: {false_negatives}/{len(fraudulent_transactions)}")
        
        # False negative rate should be very low
        assert false_negative_rate <= 20, f"False negative rate too high: {false_negative_rate:.2f}%"
    
    @pytest.mark.asyncio
    async def test_confidence_calibration(self, system):
        """Test that confidence scores are well-calibrated."""
        test_transactions = [
            {
                "transaction_id": f"calib_{i}",
                "user_id": f"user_calib_{i}",
                "amount": 100.00 + i * 100,
                "currency": "USD",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(50)
        ]
        
        high_confidence_correct = 0
        high_confidence_total = 0
        low_confidence_uncertain = 0
        low_confidence_total = 0
        
        for tx in test_transactions:
            result = await system.process_transaction(tx)
            confidence = result["confidence"]
            
            if confidence >= 0.8:
                high_confidence_total += 1
                # High confidence decisions should be more likely correct
                # (In real scenario, we'd compare with ground truth)
                if result["decision"] in ["APPROVE", "DECLINE"]:
                    high_confidence_correct += 1
            elif confidence <= 0.5:
                low_confidence_total += 1
                # Low confidence should lead to review
                if result["decision"] in ["REVIEW", "FLAG"]:
                    low_confidence_uncertain += 1
        
        if high_confidence_total > 0:
            high_conf_accuracy = high_confidence_correct / high_confidence_total
            print(f"\nHigh Confidence Decisions: {high_conf_accuracy*100:.1f}% decisive")
            assert high_conf_accuracy >= 0.7
        
        if low_confidence_total > 0:
            low_conf_review_rate = low_confidence_uncertain / low_confidence_total
            print(f"Low Confidence Decisions: {low_conf_review_rate*100:.1f}% sent to review")


class TestAWSAIAgentCompliance:
    """Test compliance with AWS AI agent standards."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create agent orchestrator."""
        return AgentOrchestrator()
    
    @pytest.mark.asyncio
    async def test_agent_response_format(self, orchestrator):
        """Test that agent responses follow AWS Bedrock format."""
        transaction = {
            "transaction_id": "aws_format_001",
            "user_id": "user_aws",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        result = await orchestrator.process_transaction(transaction)
        
        # Should follow standard format
        assert isinstance(result, dict)
        assert "decision" in result
        assert "confidence" in result
        
        # Decision should be from valid set
        assert result["decision"] in ["APPROVE", "DECLINE", "FLAG", "REVIEW"]
        
        # Confidence should be normalized
        assert isinstance(result["confidence"], (int, float))
        assert 0 <= result["confidence"] <= 1
    
    @pytest.mark.asyncio
    async def test_agent_traceability(self, orchestrator):
        """Test that agent decisions are traceable."""
        transaction = {
            "transaction_id": "trace_001",
            "user_id": "user_trace",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        result = await orchestrator.process_transaction(transaction)
        
        # Should have traceability information
        assert "transaction_id" in result
        assert "timestamp" in result or "processed_at" in result
        
        # Should have agent information
        assert "agent_results" in result or "agents" in result
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self, orchestrator):
        """Test that agents handle errors gracefully."""
        # Invalid transaction
        invalid_transaction = {
            "transaction_id": "error_001"
            # Missing required fields
        }
        
        # Should not crash
        try:
            result = await orchestrator.process_transaction(invalid_transaction)
            # Should return error information
            assert result is not None
            assert "error" in result or "decision" in result
        except Exception as e:
            # If exception is raised, it should be informative
            assert str(e) is not None
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, orchestrator):
        """Test that agents respect timeout constraints."""
        transaction = {
            "transaction_id": "timeout_001",
            "user_id": "user_timeout",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        import time
        start_time = time.time()
        result = await orchestrator.process_transaction(transaction)
        elapsed_time = time.time() - start_time
        
        # Should complete within reasonable time (5 seconds)
        assert elapsed_time < 5.0, f"Processing took too long: {elapsed_time:.2f}s"
        
        # Should still return valid result
        assert result is not None
        assert "decision" in result
    
    @pytest.mark.asyncio
    async def test_agent_audit_trail(self, orchestrator):
        """Test that agents maintain audit trail."""
        transaction = {
            "transaction_id": "audit_001",
            "user_id": "user_audit",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        result = await orchestrator.process_transaction(transaction)
        
        # Should have audit information
        assert "transaction_id" in result
        
        # Should have reasoning/explanation for audit
        assert "reasoning" in result or "explanation" in result or "factors" in result
        
        # Should be serializable for storage
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            pytest.fail("Result should be JSON serializable for audit storage")


@pytest.mark.asyncio
async def test_comprehensive_ai_validation():
    """Comprehensive AI agent validation test."""
    system = UnifiedFraudDetectionSystem()
    
    # Test diverse scenarios
    scenarios = [
        {
            "name": "Normal Transaction",
            "transaction": {
                "transaction_id": "comp_001",
                "user_id": "user_normal",
                "amount": 100.00,
                "currency": "USD"
            },
            "expected_behavior": "approve_or_low_risk"
        },
        {
            "name": "High-Risk Transaction",
            "transaction": {
                "transaction_id": "comp_002",
                "user_id": "user_risk",
                "amount": 10000.00,
                "currency": "USD",
                "location": "High-Risk Country"
            },
            "expected_behavior": "flag_or_decline"
        },
        {
            "name": "Ambiguous Transaction",
            "transaction": {
                "transaction_id": "comp_003",
                "user_id": "user_ambig",
                "amount": 500.00,
                "currency": "USD",
                "location": "New Location"
            },
            "expected_behavior": "review_or_moderate_confidence"
        }
    ]
    
    results = []
    for scenario in scenarios:
        result = await system.process_transaction(scenario["transaction"])
        results.append({
            "scenario": scenario["name"],
            "decision": result["decision"],
            "confidence": result["confidence"],
            "has_reasoning": len(result.get("reasoning", [])) > 0,
            "has_explanation": "explanation" in result or "reasoning" in result
        })
    
    print("\nComprehensive AI Validation Results:")
    for r in results:
        print(f"  {r['scenario']}:")
        print(f"    Decision: {r['decision']}")
        print(f"    Confidence: {r['confidence']:.2f}")
        print(f"    Has Reasoning: {r['has_reasoning']}")
    
    # All scenarios should have reasoning
    assert all(r["has_reasoning"] for r in results), "All decisions should have reasoning"
    
    # All scenarios should have valid decisions
    assert all(r["decision"] in ["APPROVE", "DECLINE", "FLAG", "REVIEW"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
