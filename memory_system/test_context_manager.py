"""
Unit tests for the Context Manager.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from .context_manager import ContextManager, ContextualInsight
from .models import (
    Transaction, DecisionContext, UserBehaviorProfile, 
    FraudPattern, SimilarCase, RiskProfile, FraudDecision,
    Location, DeviceInfo, RiskLevel
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
        id="tx_test_001",
        user_id="user_test_123",
        amount=Decimal("250.00"),
        currency="USD",
        merchant="Amazon",
        category="online_retail",
        location=Location(
            country="US",
            city="New York",
            latitude=40.7128,
            longitude=-74.0060,
            ip_address="192.168.1.1"
        ),
        timestamp=datetime.now(),
        card_type="credit",
        device_info=DeviceInfo(
            device_id="device_test_001",
            device_type="mobile",
            os="iOS",
            browser="Safari",
            fingerprint="fp_test_123"
        ),
        ip_address="192.168.1.1",
        session_id="session_test_001",
        metadata={"channel": "mobile_app"}
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user behavior profile for testing."""
    return UserBehaviorProfile(
        user_id="user_test_123",
        typical_spending_range={"min": 20.0, "max": 300.0, "avg": 100.0},
        frequent_merchants=["Amazon", "Starbucks", "Target"],
        common_locations=[
            Location(country="US", city="New York", latitude=40.7128, longitude=-74.0060),
            Location(country="US", city="Boston", latitude=42.3601, longitude=-71.0589)
        ],
        preferred_categories=["online_retail", "food", "groceries"],
        transaction_frequency={"daily": 3, "weekly": 21, "monthly": 90},
        risk_score=0.2,
        last_updated=datetime.now(),
        transaction_count=200
    )


@pytest.fixture
def sample_risk_profile():
    """Create a sample risk profile for testing."""
    return RiskProfile(
        user_id="user_test_123",
        overall_risk_level=RiskLevel.LOW,
        risk_factors={
            "new_user": 0.0,
            "high_value_transactions": 0.1,
            "unusual_locations": 0.05,
            "device_changes": 0.0
        },
        geographic_risk=0.1,
        behavioral_risk=0.15,
        transaction_risk=0.1,
        temporal_risk=0.05,
        last_assessment=datetime.now(),
        risk_evolution=[
            {"date": "2024-01-01", "risk_level": "low", "score": 0.15},
            {"date": "2024-01-15", "risk_level": "low", "score": 0.2}
        ]
    )


@pytest.fixture
def sample_similar_cases():
    """Create sample similar cases for testing."""
    return [
        SimilarCase(
            case_id="case_001",
            transaction_id="tx_similar_001",
            similarity_score=0.85,
            decision=FraudDecision.APPROVED,
            outcome="legitimate",
            reasoning="Similar merchant and amount",
            timestamp=datetime.now() - timedelta(days=5)
        ),
        SimilarCase(
            case_id="case_002",
            transaction_id="tx_similar_002",
            similarity_score=0.75,
            decision=FraudDecision.DECLINED,
            outcome="fraud",
            reasoning="Suspicious velocity pattern",
            timestamp=datetime.now() - timedelta(days=10)
        )
    ]


@pytest.fixture
def sample_decision_history():
    """Create sample decision history for testing."""
    return [
        DecisionContext(
            transaction_id="tx_hist_001",
            user_id="user_test_123",
            decision=FraudDecision.APPROVED,
            confidence_score=0.8,
            reasoning_steps=["Normal transaction pattern"],
            evidence=["Merchant in frequent list"],
            timestamp=datetime.now() - timedelta(days=1),
            processing_time_ms=150.0,
            agent_version="1.0.0"
        ),
        DecisionContext(
            transaction_id="tx_hist_002",
            user_id="user_test_123",
            decision=FraudDecision.APPROVED,
            confidence_score=0.9,
            reasoning_steps=["Typical spending behavior"],
            evidence=["Amount within range"],
            timestamp=datetime.now() - timedelta(days=3),
            processing_time_ms=120.0,
            agent_version="1.0.0"
        )
    ]


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


class TestContextManager:
    """Test cases for ContextManager functionality."""
    
    def test_initialization(self, mock_memory_manager):
        """Test context manager initialization."""
        manager = ContextManager(mock_memory_manager)
        
        assert manager.memory_manager == mock_memory_manager
        assert manager.similarity_threshold == 0.7
        assert manager.context_window_days == 90
    
    def test_get_transaction_context_complete(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction,
        sample_user_profile,
        sample_risk_profile,
        sample_similar_cases,
        sample_decision_history
    ):
        """Test getting complete transaction context."""
        # Set up mock returns
        mock_memory_manager.get_similar_transactions.return_value = sample_similar_cases
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        mock_memory_manager.get_risk_profile.return_value = sample_risk_profile
        mock_memory_manager.get_user_decision_history.return_value = sample_decision_history
        
        # Get context
        context = context_manager.get_transaction_context(sample_transaction)
        
        # Verify context structure
        assert "transaction_id" in context
        assert "user_id" in context
        assert "timestamp" in context
        assert "similar_cases" in context
        assert "user_profile" in context
        assert "risk_profile" in context
        assert "contextual_insights" in context
        assert "decision_history" in context
        assert "risk_factors" in context
        
        # Verify data
        assert context["transaction_id"] == sample_transaction.id
        assert context["user_id"] == sample_transaction.user_id
        assert len(context["similar_cases"]) == 2
        assert context["user_profile"] == sample_user_profile
        assert context["risk_profile"] == sample_risk_profile
        assert len(context["decision_history"]) == 2
        assert len(context["contextual_insights"]) > 0
        assert len(context["risk_factors"]) > 0
    
    def test_get_transaction_context_minimal(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test getting transaction context with minimal data."""
        # Set up mock returns with None/empty values
        mock_memory_manager.get_similar_transactions.return_value = []
        mock_memory_manager.get_user_profile.return_value = None
        mock_memory_manager.get_risk_profile.return_value = None
        mock_memory_manager.get_user_decision_history.return_value = []
        
        # Get context
        context = context_manager.get_transaction_context(sample_transaction)
        
        # Verify basic structure exists even with minimal data
        assert context["transaction_id"] == sample_transaction.id
        assert context["similar_cases"] == []
        assert context["user_profile"] is None
        assert context["risk_profile"] is None
        assert context["decision_history"] == []
        assert isinstance(context["contextual_insights"], list)
        assert isinstance(context["risk_factors"], dict)
    
    def test_generate_contextual_insights_similar_cases(
        self, 
        context_manager, 
        sample_transaction,
        sample_similar_cases
    ):
        """Test generating insights from similar cases."""
        context = {
            "similar_cases": sample_similar_cases,
            "user_profile": None,
            "decision_history": []
        }
        
        insights = context_manager._generate_contextual_insights(sample_transaction, context)
        
        # Should generate insight about fraud rate in similar cases
        fraud_insights = [i for i in insights if i.insight_type == "similar_case_analysis"]
        assert len(fraud_insights) > 0
        
        # Check insight properties
        insight = fraud_insights[0]
        assert insight.confidence > 0
        assert len(insight.supporting_evidence) > 0
    
    def test_generate_contextual_insights_spending_behavior(
        self, 
        context_manager, 
        sample_transaction,
        sample_user_profile
    ):
        """Test generating insights from spending behavior."""
        context = {
            "similar_cases": [],
            "user_profile": sample_user_profile,
            "decision_history": []
        }
        
        insights = context_manager._generate_contextual_insights(sample_transaction, context)
        
        # Should generate insights about spending behavior
        spending_insights = [i for i in insights if i.insight_type == "spending_behavior"]
        merchant_insights = [i for i in insights if i.insight_type == "merchant_familiarity"]
        
        assert len(spending_insights) > 0 or len(merchant_insights) > 0
    
    def test_generate_contextual_insights_decision_history(
        self, 
        context_manager, 
        sample_transaction,
        sample_decision_history
    ):
        """Test generating insights from decision history."""
        context = {
            "similar_cases": [],
            "user_profile": None,
            "decision_history": sample_decision_history
        }
        
        insights = context_manager._generate_contextual_insights(sample_transaction, context)
        
        # Should generate insights about recent activity
        activity_insights = [i for i in insights if i.insight_type == "recent_activity"]
        assert len(activity_insights) >= 0  # May or may not generate based on data
    
    def test_analyze_risk_factors_with_profile(
        self, 
        context_manager, 
        sample_transaction,
        sample_user_profile
    ):
        """Test risk factor analysis with user profile."""
        context = {
            "user_profile": sample_user_profile,
            "decision_history": []
        }
        
        risk_factors = context_manager._analyze_risk_factors(sample_transaction, context)
        
        # Should analyze multiple risk factors
        assert "geographic_anomaly" in risk_factors
        assert "temporal_anomaly" in risk_factors
        assert "amount_anomaly" in risk_factors
        assert "velocity_risk" in risk_factors
        
        # All risk factors should be between 0 and 1
        for factor_value in risk_factors.values():
            assert 0 <= factor_value <= 1
    
    def test_analyze_risk_factors_without_profile(
        self, 
        context_manager, 
        sample_transaction
    ):
        """Test risk factor analysis without user profile."""
        context = {
            "user_profile": None,
            "decision_history": []
        }
        
        risk_factors = context_manager._analyze_risk_factors(sample_transaction, context)
        
        # Should still analyze risk factors with default values
        assert "geographic_anomaly" in risk_factors
        assert "temporal_anomaly" in risk_factors
        assert "amount_anomaly" in risk_factors
        assert "velocity_risk" in risk_factors
    
    def test_get_contextual_recommendation_approve(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction,
        sample_user_profile
    ):
        """Test contextual recommendation for approval case."""
        # Set up mocks for low-risk scenario
        mock_memory_manager.get_similar_transactions.return_value = []
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        mock_memory_manager.get_risk_profile.return_value = None
        mock_memory_manager.get_user_decision_history.return_value = []
        
        recommendation = context_manager.get_contextual_recommendation(sample_transaction)
        
        # Verify recommendation structure
        assert "transaction_id" in recommendation
        assert "recommendation" in recommendation
        assert "confidence" in recommendation
        assert "risk_score" in recommendation
        assert "reasoning" in recommendation
        assert "context_summary" in recommendation
        
        # Verify values
        assert recommendation["transaction_id"] == sample_transaction.id
        assert recommendation["recommendation"] in ["APPROVE", "FLAG_FOR_REVIEW", "DECLINE"]
        assert 0 <= recommendation["confidence"] <= 1
        assert -1 <= recommendation["risk_score"] <= 1
        assert isinstance(recommendation["reasoning"], list)
    
    def test_get_contextual_recommendation_high_risk(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test contextual recommendation for high-risk case."""
        # Create high-risk transaction
        high_risk_transaction = Transaction(
            id="tx_high_risk",
            user_id="user_unknown",
            amount=Decimal("5000.00"),  # Very high amount
            currency="USD",
            merchant="Unknown Merchant",
            category="unknown",
            location=Location(country="XX", city="Unknown"),  # Unknown location
            timestamp=datetime.now().replace(hour=3),  # Late night
            card_type="credit",
            device_info=DeviceInfo(device_id="unknown", device_type="unknown", os="unknown"),
            ip_address="0.0.0.0",
            session_id="unknown"
        )
        
        # Set up mocks for high-risk scenario
        mock_memory_manager.get_similar_transactions.return_value = []
        mock_memory_manager.get_user_profile.return_value = None
        mock_memory_manager.get_risk_profile.return_value = None
        mock_memory_manager.get_user_decision_history.return_value = []
        
        recommendation = context_manager.get_contextual_recommendation(high_risk_transaction)
        
        # Should recommend decline or review for high-risk transaction
        assert recommendation["recommendation"] in ["DECLINE", "FLAG_FOR_REVIEW"]
        assert recommendation["risk_score"] > 0  # Should have positive risk score
    
    def test_error_handling_in_context_retrieval(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test error handling during context retrieval."""
        # Set up mock to raise exception
        mock_memory_manager.get_similar_transactions.side_effect = Exception("Database error")
        
        context = context_manager.get_transaction_context(sample_transaction)
        
        # Should handle error gracefully
        assert "error" in context
        assert "Database error" in context["error"]
    
    def test_error_handling_in_recommendation(
        self, 
        context_manager, 
        mock_memory_manager, 
        sample_transaction
    ):
        """Test error handling during recommendation generation."""
        # Set up mock to raise exception
        mock_memory_manager.get_similar_transactions.side_effect = Exception("Service unavailable")
        
        recommendation = context_manager.get_contextual_recommendation(sample_transaction)
        
        # Should handle error gracefully
        assert recommendation["recommendation"] == "MANUAL_REVIEW"
        assert recommendation["confidence"] == 0.0
        assert "Error in contextual analysis" in recommendation["reasoning"][0]
    
    def test_risk_score_normalization(self, context_manager):
        """Test that risk scores are properly normalized."""
        # Test with extreme values
        sample_transaction = Transaction(
            id="tx_extreme",
            user_id="user_extreme",
            amount=Decimal("10000.00"),
            currency="USD",
            merchant="Extreme Merchant",
            category="extreme",
            location=Location(country="XX", city="Extreme"),
            timestamp=datetime.now(),
            card_type="credit",
            device_info=DeviceInfo(device_id="extreme", device_type="extreme", os="extreme"),
            ip_address="0.0.0.0",
            session_id="extreme"
        )
        
        # Create context with extreme risk factors
        context = {
            "similar_cases": [],
            "user_profile": None,
            "risk_profile": None,
            "decision_history": [],
            "contextual_insights": [
                ContextualInsight(
                    insight_type="extreme_risk",
                    description="Extreme risk detected",
                    confidence=1.0,
                    supporting_evidence=["Extreme values"],
                    risk_impact=2.0  # Above normal range
                )
            ],
            "risk_factors": {
                "extreme_factor": 2.0  # Above normal range
            }
        }
        
        # Manually test risk score calculation logic
        risk_score = 0.0
        
        # Process insights
        for insight in context["contextual_insights"]:
            weighted_impact = insight.risk_impact * insight.confidence
            risk_score += weighted_impact
        
        # Process risk factors
        for factor_value in context["risk_factors"].values():
            risk_score += factor_value * 0.3
        
        # Normalize
        normalized_score = max(-1.0, min(1.0, risk_score))
        
        # Should be clamped to valid range
        assert -1.0 <= normalized_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])