"""
Integration Test Suite for Fraud Detection System

Tests agent coordination workflows, external tool integrations,
memory system persistence, and streaming pipeline end-to-end.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List

# Import system components
from src.fraud_detection.core.unified_fraud_detection_system import UnifiedFraudDetectionSystem
from agent_orchestrator import AgentOrchestrator
from memory_manager import MemoryManager
from src.fraud_detection.core.transaction_processing_pipeline import TransactionProcessingPipeline


class TestAgentCoordination:
    """Test agent coordination workflows."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create agent orchestrator for testing."""
        return AgentOrchestrator()
    
    @pytest.fixture
    def sample_transaction(self):
        """Create sample transaction for testing."""
        return {
            "transaction_id": "test_tx_001",
            "user_id": "user_123",
            "amount": 5000.00,
            "currency": "USD",
            "merchant": "Online Store",
            "location": "New York, US",
            "timestamp": datetime.now().isoformat(),
            "device_id": "device_456",
            "ip_address": "192.168.1.1"
        }
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, orchestrator, sample_transaction):
        """Test coordination between multiple specialized agents."""
        # Process transaction through orchestrator
        result = await orchestrator.process_transaction(sample_transaction)
        
        # Verify all agents participated
        assert result is not None
        assert "decision" in result
        assert "agent_results" in result
        assert len(result["agent_results"]) >= 3  # At least 3 agents
        
        # Verify agent types
        agent_types = [r["agent_type"] for r in result["agent_results"]]
        assert "transaction_analyzer" in agent_types
        assert "pattern_detector" in agent_types
        assert "risk_assessor" in agent_types
    
    @pytest.mark.asyncio
    async def test_agent_communication_protocol(self, orchestrator, sample_transaction):
        """Test standardized message format between agents."""
        result = await orchestrator.process_transaction(sample_transaction)
        
        # Verify message format
        for agent_result in result["agent_results"]:
            assert "agent_type" in agent_result
            assert "decision" in agent_result
            assert "confidence" in agent_result
            assert "reasoning" in agent_result
            assert isinstance(agent_result["confidence"], (int, float))
            assert 0 <= agent_result["confidence"] <= 1
    
    @pytest.mark.asyncio
    async def test_decision_aggregation(self, orchestrator, sample_transaction):
        """Test decision aggregation from multiple agents."""
        result = await orchestrator.process_transaction(sample_transaction)
        
        # Verify aggregated decision
        assert "decision" in result
        assert result["decision"] in ["APPROVE", "DECLINE", "FLAG", "REVIEW"]
        assert "confidence" in result
        assert "aggregation_method" in result
        
        # Verify weighted voting was applied
        assert result["aggregation_method"] in ["weighted_voting", "consensus", "majority"]
    
    @pytest.mark.asyncio
    async def test_conflict_resolution(self, orchestrator):
        """Test conflict resolution when agents disagree."""
        # Create transaction that might cause disagreement
        conflicting_transaction = {
            "transaction_id": "test_tx_conflict",
            "user_id": "user_789",
            "amount": 100.00,  # Small amount (low risk)
            "currency": "USD",
            "merchant": "Known Fraud Merchant",  # High risk
            "location": "Russia",  # High risk location
            "timestamp": datetime.now().isoformat()
        }
        
        result = await orchestrator.process_transaction(conflicting_transaction)
        
        # Verify conflict was resolved
        assert result["decision"] is not None
        assert "conflict_resolution" in result or "aggregation_method" in result
    
    @pytest.mark.asyncio
    async def test_workload_distribution(self, orchestrator):
        """Test intelligent task routing and load balancing."""
        # Submit multiple transactions concurrently
        transactions = [
            {
                "transaction_id": f"test_tx_{i}",
                "user_id": f"user_{i}",
                "amount": 1000.00 + i * 100,
                "currency": "USD",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(10)
        ]
        
        # Process concurrently
        results = await asyncio.gather(*[
            orchestrator.process_transaction(tx) for tx in transactions
        ])
        
        # Verify all processed successfully
        assert len(results) == 10
        assert all(r["decision"] is not None for r in results)


class TestExternalToolIntegrations:
    """Test external tool integrations with mock services."""
    
    @pytest.fixture
    def unified_system(self):
        """Create unified system for testing."""
        return UnifiedFraudDetectionSystem()
    
    @pytest.mark.asyncio
    @patch('tool_integrator.IdentityVerificationService')
    async def test_identity_verification_integration(self, mock_identity_service, unified_system):
        """Test identity verification service integration."""
        # Mock identity verification response
        mock_identity_service.return_value.verify_identity = AsyncMock(return_value={
            "verified": True,
            "confidence": 0.95,
            "risk_indicators": []
        })
        
        transaction = {
            "transaction_id": "test_tx_identity",
            "user_id": "user_123",
            "amount": 5000.00,
            "currency": "USD"
        }
        
        result = await unified_system.process_transaction(transaction)
        
        # Verify identity verification was called
        assert result is not None
        assert "identity_verification" in result.get("tool_results", {})
    
    @pytest.mark.asyncio
    @patch('tool_integrator.FraudDatabaseService')
    async def test_fraud_database_integration(self, mock_fraud_db, unified_system):
        """Test fraud database service integration."""
        # Mock fraud database response
        mock_fraud_db.return_value.check_fraud_database = AsyncMock(return_value={
            "matches_found": 2,
            "similar_cases": [
                {"case_id": "fraud_001", "similarity": 0.85},
                {"case_id": "fraud_002", "similarity": 0.72}
            ]
        })
        
        transaction = {
            "transaction_id": "test_tx_fraud_db",
            "user_id": "user_456",
            "amount": 10000.00,
            "currency": "USD"
        }
        
        result = await unified_system.process_transaction(transaction)
        
        # Verify fraud database was queried
        assert result is not None
        tool_results = result.get("tool_results", {})
        assert "fraud_database" in tool_results or "similar_cases" in result
    
    @pytest.mark.asyncio
    @patch('tool_integrator.GeolocationService')
    async def test_geolocation_integration(self, mock_geo_service, unified_system):
        """Test geolocation service integration."""
        # Mock geolocation response
        mock_geo_service.return_value.assess_location_risk = AsyncMock(return_value={
            "risk_score": 0.3,
            "country": "US",
            "is_high_risk": False,
            "travel_pattern_anomaly": False
        })
        
        transaction = {
            "transaction_id": "test_tx_geo",
            "user_id": "user_789",
            "amount": 2000.00,
            "currency": "USD",
            "location": "New York, US"
        }
        
        result = await unified_system.process_transaction(transaction)
        
        # Verify geolocation was assessed
        assert result is not None
        assert "location_risk" in result or "geolocation" in result.get("tool_results", {})
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, unified_system):
        """Test error handling when external tools fail."""
        with patch('tool_integrator.IdentityVerificationService') as mock_service:
            # Simulate service failure
            mock_service.return_value.verify_identity = AsyncMock(
                side_effect=Exception("Service unavailable")
            )
            
            transaction = {
                "transaction_id": "test_tx_error",
                "user_id": "user_error",
                "amount": 1000.00,
                "currency": "USD"
            }
            
            # Should not raise exception, should use fallback
            result = await unified_system.process_transaction(transaction)
            
            # Verify system handled error gracefully
            assert result is not None
            assert result["decision"] is not None
            assert "errors" in result or "warnings" in result


class TestMemorySystemPersistence:
    """Test memory system persistence and retrieval."""
    
    @pytest.fixture
    def memory_manager(self):
        """Create memory manager for testing."""
        return MemoryManager(use_mock=True)  # Use mock DynamoDB for testing
    
    @pytest.mark.asyncio
    async def test_transaction_history_storage(self, memory_manager):
        """Test storing and retrieving transaction history."""
        # Store transaction
        transaction = {
            "transaction_id": "test_tx_memory_001",
            "user_id": "user_123",
            "amount": 5000.00,
            "timestamp": datetime.now().isoformat(),
            "decision": "APPROVE"
        }
        
        await memory_manager.store_transaction(transaction)
        
        # Retrieve transaction
        retrieved = await memory_manager.get_transaction("test_tx_memory_001")
        
        assert retrieved is not None
        assert retrieved["transaction_id"] == transaction["transaction_id"]
        assert retrieved["user_id"] == transaction["user_id"]
    
    @pytest.mark.asyncio
    async def test_user_behavior_profiling(self, memory_manager):
        """Test user behavior profile storage and updates."""
        user_id = "user_profile_test"
        
        # Create initial profile
        profile = {
            "user_id": user_id,
            "average_transaction_amount": 1000.00,
            "transaction_count": 10,
            "typical_locations": ["New York", "Boston"],
            "risk_score": 0.2
        }
        
        await memory_manager.store_user_profile(profile)
        
        # Retrieve profile
        retrieved = await memory_manager.get_user_profile(user_id)
        
        assert retrieved is not None
        assert retrieved["user_id"] == user_id
        assert retrieved["average_transaction_amount"] == 1000.00
    
    @pytest.mark.asyncio
    async def test_decision_context_retrieval(self, memory_manager):
        """Test retrieving historical decision context."""
        user_id = "user_context_test"
        
        # Store multiple transactions
        for i in range(5):
            transaction = {
                "transaction_id": f"tx_context_{i}",
                "user_id": user_id,
                "amount": 1000.00 + i * 100,
                "timestamp": (datetime.now() - timedelta(days=i)).isoformat(),
                "decision": "APPROVE"
            }
            await memory_manager.store_transaction(transaction)
        
        # Retrieve context
        context = await memory_manager.get_user_transaction_history(user_id, limit=5)
        
        assert len(context) == 5
        assert all(tx["user_id"] == user_id for tx in context)
    
    @pytest.mark.asyncio
    async def test_pattern_storage_and_learning(self, memory_manager):
        """Test fraud pattern storage and retrieval."""
        pattern = {
            "pattern_id": "pattern_001",
            "pattern_type": "velocity_fraud",
            "description": "Multiple transactions in short time",
            "indicators": ["high_frequency", "increasing_amounts"],
            "confidence": 0.85
        }
        
        await memory_manager.store_fraud_pattern(pattern)
        
        # Retrieve pattern
        retrieved = await memory_manager.get_fraud_pattern("pattern_001")
        
        assert retrieved is not None
        assert retrieved["pattern_id"] == pattern["pattern_id"]
        assert retrieved["pattern_type"] == pattern["pattern_type"]


class TestStreamingPipeline:
    """Test streaming pipeline end-to-end."""
    
    @pytest.fixture
    def pipeline(self):
        """Create transaction processing pipeline."""
        return TransactionProcessingPipeline(use_mock_stream=True)
    
    @pytest.mark.asyncio
    async def test_stream_ingestion(self, pipeline):
        """Test transaction ingestion into stream."""
        transaction = {
            "transaction_id": "test_stream_001",
            "user_id": "user_stream",
            "amount": 5000.00,
            "currency": "USD",
            "timestamp": datetime.now().isoformat()
        }
        
        # Ingest transaction
        result = await pipeline.ingest_transaction(transaction)
        
        assert result["success"] is True
        assert "sequence_number" in result or "message_id" in result
    
    @pytest.mark.asyncio
    async def test_stream_processing(self, pipeline):
        """Test processing transactions from stream."""
        # Ingest multiple transactions
        transactions = [
            {
                "transaction_id": f"test_stream_{i}",
                "user_id": f"user_{i}",
                "amount": 1000.00 + i * 100,
                "currency": "USD",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(5)
        ]
        
        for tx in transactions:
            await pipeline.ingest_transaction(tx)
        
        # Process stream
        processed = await pipeline.process_stream_batch(batch_size=5)
        
        assert len(processed) > 0
        assert all("decision" in result for result in processed)
    
    @pytest.mark.asyncio
    async def test_event_driven_response(self, pipeline):
        """Test event-driven response to fraud detection."""
        # Create high-risk transaction
        fraud_transaction = {
            "transaction_id": "test_fraud_event",
            "user_id": "user_fraud",
            "amount": 50000.00,
            "currency": "USD",
            "location": "Unknown Location",
            "timestamp": datetime.now().isoformat()
        }
        
        # Process and check for event emission
        result = await pipeline.process_transaction_with_events(fraud_transaction)
        
        assert result is not None
        if result["decision"] in ["DECLINE", "FLAG"]:
            assert "events_emitted" in result
            assert len(result["events_emitted"]) > 0
    
    @pytest.mark.asyncio
    async def test_stream_error_recovery(self, pipeline):
        """Test stream processing error recovery."""
        # Create invalid transaction
        invalid_transaction = {
            "transaction_id": "test_invalid",
            # Missing required fields
        }
        
        # Should handle gracefully
        result = await pipeline.ingest_transaction(invalid_transaction)
        
        # Verify error handling
        assert "error" in result or result["success"] is False


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete end-to-end workflow."""
    system = UnifiedFraudDetectionSystem()
    
    # Create realistic transaction
    transaction = {
        "transaction_id": "e2e_test_001",
        "user_id": "user_e2e",
        "amount": 5000.00,
        "currency": "USD",
        "merchant": "Online Store",
        "location": "New York, US",
        "device_id": "device_123",
        "ip_address": "192.168.1.1",
        "timestamp": datetime.now().isoformat()
    }
    
    # Process through complete system
    result = await system.process_transaction(transaction)
    
    # Verify complete result structure
    assert result is not None
    assert "transaction_id" in result
    assert "decision" in result
    assert "confidence" in result
    assert "reasoning" in result
    assert "agent_results" in result
    assert "timestamp" in result
    
    # Verify decision is valid
    assert result["decision"] in ["APPROVE", "DECLINE", "FLAG", "REVIEW"]
    assert 0 <= result["confidence"] <= 1
    
    # Verify reasoning is provided
    assert len(result["reasoning"]) > 0
    
    # Verify agents participated
    assert len(result["agent_results"]) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
