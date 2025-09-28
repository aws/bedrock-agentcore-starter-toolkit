"""
Integration tests for Context-Aware Decision Making.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from .context_manager import ContextManager, ContextualInsight
from .models import (
    Transaction, DecisionContext, UserBehaviorProfile, RiskProfile,
    FraudDecision, RiskLevel, Location, DeviceInfo, SimilarCase
)
from .memory_manager import MemoryManager


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager for testing."""
    return Mock(spec=MemoryManager)


@pytest.fixture
def context_manager(mock_memory_manager):
    """Create a context manager for testing."""
    return ContextManager(mock_memory_manager)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return Transaction(
        id="tx_context_001",
        user_id="user_context_123",
        amount=Decimal("250.00"),
        currency="USD",
        merchant="TestMerchant",
        category="retail",
        location=Location(
            country="US",
            city="New York",
            latitude=40.7128,
            longitude=-74.0060,
            ip_address="192.168.1.100"
        ),
        timestamp=datetime.now(),
        card_type="credit",
        device_info=DeviceInfo(
            device_id="device_context_001",
            device_type="mobile",
            os="iOS",
            browser="Safari"
        ),
        ip_address="192.168.1.100",
        session_id="session_context_001"
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user behavior profile."""
    return UserBehaviorProfile(
        user_id="user_context_123",
        typical_spending_range={"min": 20.0, "max": 300.0, "avg": 125.0},
        frequent_merchants=["TestMerchant", "Amazon", "Starbucks"],
        common_locations=[
            Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
            Location(country="US", city="Boston", latitude=42.3601, longitude=-71.0589)
        ],
        preferred_categories=["retail", "food", "online"],
        transaction_frequency={"daily": 3, "weekly": 21, "monthly": 90},
        risk_score=0.25,
        last_updated=datetime.now(),
        transaction_count=500
    )


@pytest.fixture
def sample_risk_profile():
    """Create a sample risk profile."""
    return RiskProfile(
        user_id="user_context_123",
        overall_risk_level=RiskLevel.LOW,
        risk_factors={
            "new_user": 0.0,
            "high_value_transactions": 0.2,
            "unusual_locations": 0.1,
            "device_changes": 0.0
        },
        geographic_risk=0.15,
        behavioral_risk=0.20,
        transaction_risk=0.10,
        temporal_risk=0.05,
        last_assessment=datetime.now(),
        risk_evolution=[
            {"date": "2024-01-01", "risk_level": "low", "score": 0.2},
            {"date": "2024-01-15", "risk_level": "low", "score": 0.25}
        ]
    )


@pytest.fixture
def sample_decision_history():
    """Create sample decision history."""
    decisions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(20):
        decision = DecisionContext(
            transaction_id=f"tx_hist_{i:03d}",
            user_id="user_context_123",
            decision=FraudDecision.APPROVED if i % 4 != 0 else FraudDecision.FLAGGED,
            confidence_score=0.7 + (i % 3) * 0.1,
            reasoning_steps=[
                f"Transaction {i} analysis",
                "Amount within normal range" if i % 4 != 0 else "Velocity concern detected",
                "Location verified" if i % 3 != 0 else "Geographic anomaly noted"
            ],
            evidence=[f"Evidence for transaction {i}"],
            timestamp=base_time + timedelta(days=i),
            processing_time_ms=150.0 + i * 5,
            agent_version="1.0.0"
        )
        decisions.append(decision)
    
    return decisions


@pytest.fixture
def sample_similar_cases():
    """Create sample similar cases."""
    cases = []
    for i in range(5):
        case = SimilarCase(
            case_id=f"similar_{i}",
            transaction_id=f"tx_similar_{i}",
            similarity_score=0.8 - i * 0.1,
            decision=FraudDecision.APPROVED if i % 2 == 0 else FraudDecision.DECLINED,
            outcome="legitimate" if i % 2 == 0 else "fraud",
            reasoning=f"Similar case {i} reasoning",
            timestamp=datetime.now() - timedelta(hours=i)
        )
        cases.append(case)
    
    return cases


class TestContextManager:
    """Test cases for ContextManager functionality."""
    
    def test_initialization(self, mock_memory_manager):
        """Test context manager initialization."""
        context_manager = ContextManager(mock_memory_manager)
        
        assert context_manager.memory_manager == mock_memory_manager
        assert context_manager.similarity_threshold == 0.7
        assert context_manager.context_window_days == 90
        assert context_manager.risk_evolution_cache == {}
    
    def test_get_transaction_context_complete(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction,
        sample_user_profile,
        sample_risk_profile,
        sample_decision_history,
        sample_similar_cases
    ):
        """Test getting complete transaction context."""
        # Set up mock returns
        mock_memory_manager.get_similar_transactions.return_value = sample_similar_cases
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        mock_memory_manager.get_risk_profile.return_value = sample_risk_profile
        mock_memory_manager.get_user_decision_history.return_value = sample_decision_history
        
        # Get transaction context
        context = context_manager.get_transaction_context(sample_transaction)
        
        # Verify context structure
        assert context["transaction_id"] == sample_transaction.id
        assert context["user_id"] == sample_transaction.user_id
        assert len(context["similar_cases"]) == 5
        assert context["user_profile"] == sample_user_profile
        assert context["risk_profile"] == sample_risk_profile
        assert len(context["decision_history"]) == 20
        assert "contextual_insights" in context
        assert "risk_factors" in context
        
        # Verify insights were generated
        insights = context["contextual_insights"]
        assert len(insights) > 0
        assert all(isinstance(insight, ContextualInsight) for insight in insights)
        
        # Verify risk factors were calculated
        risk_factors = context["risk_factors"]
        assert "geographic_anomaly" in risk_factors
        assert "temporal_anomaly" in risk_factors
        assert "amount_anomaly" in risk_factors
        assert "velocity_risk" in risk_factors
    
    def test_get_transaction_context_missing_data(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test getting transaction context with missing data."""
        # Set up mock to return None/empty for missing data
        mock_memory_manager.get_similar_transactions.return_value = []
        mock_memory_manager.get_user_profile.return_value = None
        mock_memory_manager.get_risk_profile.return_value = None
        mock_memory_manager.get_user_decision_history.return_value = []
        
        # Get transaction context
        context = context_manager.get_transaction_context(sample_transaction)
        
        # Verify context handles missing data gracefully
        assert context["transaction_id"] == sample_transaction.id
        assert context["similar_cases"] == []
        assert context["user_profile"] is None
        assert context["risk_profile"] is None
        assert context["decision_history"] == []
        assert "contextual_insights" in context
        assert "risk_factors" in context
    
    def test_get_contextual_recommendation_approve(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction,
        sample_user_profile
    ):
        """Test contextual recommendation for approval case."""
        # Set up favorable context
        mock_memory_manager.get_similar_transactions.return_value = []
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        mock_memory_manager.get_risk_profile.return_value = None
        mock_memory_manager.get_user_decision_history.return_value = []
        
        # Get recommendation
        recommendation = context_manager.get_contextual_recommendation(sample_transaction)
        
        # Verify recommendation structure
        assert recommendation["transaction_id"] == sample_transaction.id
        assert recommendation["recommendation"] in ["APPROVE", "FLAG_FOR_REVIEW", "DECLINE"]
        assert 0 <= recommendation["confidence"] <= 1
        assert isinstance(recommendation["risk_score"], float)
        assert isinstance(recommendation["reasoning"], list)
        assert "context_summary" in recommendation
    
    def test_get_contextual_recommendation_decline(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test contextual recommendation for decline case."""
        # Create high-risk transaction
        high_risk_transaction = Transaction(
            id="tx_high_risk",
            user_id="user_high_risk",
            amount=Decimal("5000.00"),  # Very high amount
            currency="USD",
            merchant="UnknownMerchant",
            category="unknown",
            location=Location(country="XX", city="Unknown"),  # Suspicious location
            timestamp=datetime.now().replace(hour=3),  # Late night
            card_type="credit",
            device_info=DeviceInfo(device_id="unknown_device", device_type="unknown", os="unknown"),
            ip_address="0.0.0.0",
            session_id="suspicious_session"
        )
        
        # Set up unfavorable context
        mock_memory_manager.get_similar_transactions.return_value = []
        mock_memory_manager.get_user_profile.return_value = None  # No profile = higher risk
        mock_memory_manager.get_risk_profile.return_value = None
        mock_memory_manager.get_user_decision_history.return_value = []
        
        # Get recommendation
        recommendation = context_manager.get_contextual_recommendation(high_risk_transaction)
        
        # Should recommend decline or review due to high risk factors
        assert recommendation["recommendation"] in ["DECLINE", "FLAG_FOR_REVIEW"]
        assert recommendation["risk_score"] > 0  # Should have positive risk score
    
    def test_track_risk_profile_evolution(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_risk_profile,
        sample_decision_history
    ):
        """Test risk profile evolution tracking."""
        user_id = "user_context_123"
        
        # Set up mock returns
        mock_memory_manager.get_risk_profile.return_value = sample_risk_profile
        mock_memory_manager.get_user_decision_history.return_value = sample_decision_history
        
        # Track evolution
        evolution = context_manager.track_risk_profile_evolution(user_id)
        
        # Verify evolution analysis
        assert evolution["user_id"] == user_id
        assert evolution["current_risk_level"] == sample_risk_profile.overall_risk_level.value
        assert "current_risk_factors" in evolution
        assert "risk_evolution" in evolution
        assert "risk_trend" in evolution
        assert "evolution_summary" in evolution
        assert "recommendations" in evolution
        
        # Verify caching
        assert user_id in context_manager.risk_evolution_cache
    
    def test_track_risk_profile_evolution_no_profile(
        self, 
        context_manager, 
        mock_memory_manager
    ):
        """Test risk profile evolution tracking with no existing profile."""
        user_id = "nonexistent_user"
        
        # Set up mock to return None
        mock_memory_manager.get_risk_profile.return_value = None
        
        # Track evolution
        evolution = context_manager.track_risk_profile_evolution(user_id)
        
        # Should return error
        assert "error" in evolution
        assert evolution["error"] == "No risk profile found for user"
    
    def test_get_historical_decision_patterns(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_decision_history
    ):
        """Test historical decision pattern analysis."""
        user_id = "user_context_123"
        
        # Set up mock return
        mock_memory_manager.get_user_decision_history.return_value = sample_decision_history
        
        # Get patterns
        patterns = context_manager.get_historical_decision_patterns(user_id)
        
        # Verify pattern analysis
        assert patterns["user_id"] == user_id
        assert patterns["analysis_period_days"] == 90
        assert patterns["total_decisions"] == 20
        assert "decision_distribution" in patterns
        assert "fraud_rate" in patterns
        assert "avg_confidence_by_decision" in patterns
        assert "common_reasoning_patterns" in patterns
        assert "pattern_insights" in patterns
        
        # Verify calculations
        assert 0 <= patterns["fraud_rate"] <= 1
        assert isinstance(patterns["decision_distribution"], dict)
        assert isinstance(patterns["pattern_insights"], list)
    
    def test_get_historical_decision_patterns_no_history(
        self, 
        context_manager, 
        mock_memory_manager
    ):
        """Test historical decision patterns with no history."""
        user_id = "new_user"
        
        # Set up mock to return empty list
        mock_memory_manager.get_user_decision_history.return_value = []
        
        # Get patterns
        patterns = context_manager.get_historical_decision_patterns(user_id)
        
        # Should return error
        assert "error" in patterns
        assert patterns["error"] == "No decision history found for user"
    
    def test_compare_with_similar_users(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction,
        sample_user_profile
    ):
        """Test comparison with similar users."""
        user_id = "user_context_123"
        
        # Set up mock return
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        
        # Compare with similar users
        comparison = context_manager.compare_with_similar_users(user_id, sample_transaction)
        
        # Verify comparison structure
        assert comparison["user_id"] == user_id
        assert "comparison_metrics" in comparison
        assert "peer_group_insights" in comparison
        assert "relative_risk_assessment" in comparison
        
        # Verify metrics
        metrics = comparison["comparison_metrics"]
        assert "spending_percentile" in metrics
        assert "risk_percentile" in metrics
        assert "activity_percentile" in metrics
        
        # Verify percentiles are valid
        for percentile in metrics.values():
            assert 0 <= percentile <= 100
    
    def test_compare_with_similar_users_no_profile(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test comparison with similar users when no profile exists."""
        user_id = "new_user"
        
        # Set up mock to return None
        mock_memory_manager.get_user_profile.return_value = None
        
        # Compare with similar users
        comparison = context_manager.compare_with_similar_users(user_id, sample_transaction)
        
        # Should return error
        assert "error" in comparison
        assert comparison["error"] == "No user profile found"
    
    def test_contextual_insights_generation(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction,
        sample_user_profile,
        sample_similar_cases,
        sample_decision_history
    ):
        """Test contextual insights generation."""
        # Set up context with fraud cases in similar transactions
        fraud_cases = [
            case for case in sample_similar_cases 
            if case.decision == FraudDecision.DECLINED
        ]
        
        # Mock context data
        context = {
            "similar_cases": sample_similar_cases,
            "user_profile": sample_user_profile,
            "decision_history": sample_decision_history
        }
        
        # Generate insights
        insights = context_manager._generate_contextual_insights(sample_transaction, context)
        
        # Verify insights
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        for insight in insights:
            assert isinstance(insight, ContextualInsight)
            assert insight.insight_type is not None
            assert insight.description is not None
            assert 0 <= insight.confidence <= 1
            assert -1 <= insight.risk_impact <= 1
            assert isinstance(insight.supporting_evidence, list)
    
    def test_risk_factors_analysis(
        self, 
        context_manager, 
        sample_transaction,
        sample_user_profile
    ):
        """Test risk factors analysis."""
        context = {
            "user_profile": sample_user_profile,
            "decision_history": []
        }
        
        # Analyze risk factors
        risk_factors = context_manager._analyze_risk_factors(sample_transaction, context)
        
        # Verify risk factors
        assert isinstance(risk_factors, dict)
        assert "geographic_anomaly" in risk_factors
        assert "temporal_anomaly" in risk_factors
        assert "amount_anomaly" in risk_factors
        assert "velocity_risk" in risk_factors
        
        # Verify risk factor values are valid
        for factor_value in risk_factors.values():
            assert 0 <= factor_value <= 1
    
    def test_error_handling(self, context_manager, mock_memory_manager, sample_transaction):
        """Test error handling in context operations."""
        # Set up mock to raise exception
        mock_memory_manager.get_similar_transactions.side_effect = Exception("Database error")
        
        # Get transaction context (should handle error gracefully)
        context = context_manager.get_transaction_context(sample_transaction)
        
        # Should return error information
        assert "error" in context
        assert "Database error" in context["error"]


class TestContextualInsight:
    """Test cases for ContextualInsight class."""
    
    def test_contextual_insight_creation(self):
        """Test creating a contextual insight."""
        insight = ContextualInsight(
            insight_type="test_insight",
            description="Test description",
            confidence=0.8,
            supporting_evidence=["Evidence 1", "Evidence 2"],
            risk_impact=0.5
        )
        
        assert insight.insight_type == "test_insight"
        assert insight.description == "Test description"
        assert insight.confidence == 0.8
        assert len(insight.supporting_evidence) == 2
        assert insight.risk_impact == 0.5


if __name__ == "__main__":
    pytest.main([__file__])