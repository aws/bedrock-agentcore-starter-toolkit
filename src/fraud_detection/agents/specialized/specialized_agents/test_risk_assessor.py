"""
Unit tests for the Risk Assessment Agent.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from .risk_assessor import (
    RiskAssessor, RiskFactor, GeographicRisk, TemporalRisk, 
    CrossReferenceResult, RiskAssessmentResult
)
from .base_agent import AgentConfiguration, AgentCapability
from src.models import Transaction, Location, DeviceInfo, UserBehaviorProfile, RiskLevel
from src.memory_manager import MemoryManager


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager for testing."""
    return Mock(spec=MemoryManager)


@pytest.fixture
def risk_assessor(mock_memory_manager):
    """Create a risk assessor for testing."""
    return RiskAssessor(mock_memory_manager)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return Transaction(
        id="tx_risk_test_001",
        user_id="user_risk_test_123",
        amount=Decimal("250.00"),
        currency="USD",
        merchant="Test Electronics Store",
        category="electronics",
        location=Location(
            country="US",
            city="Seattle",
            latitude=47.6062,
            longitude=-122.3321,
            ip_address="192.168.1.100"
        ),
        timestamp=datetime.now(),
        card_type="credit",
        device_info=DeviceInfo(
            device_id="device_risk_test_001",
            device_type="mobile",
            os="iOS",
            browser="Safari",
            fingerprint="fp_risk_test_123"
        ),
        ip_address="192.168.1.100",
        session_id="session_risk_test_001",
        metadata={"channel": "mobile_app"}
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user behavior profile for testing."""
    return UserBehaviorProfile(
        user_id="user_risk_test_123",
        typical_spending_range={"min": 20.0, "max": 500.0, "avg": 150.0},
        frequent_merchants=["Amazon", "Target", "Starbucks"],
        common_locations=[
            Location(country="US", city="Seattle", latitude=47.6062, longitude=-122.3321)
        ],
        preferred_categories=["electronics", "groceries", "food"],
        transaction_frequency={"daily": 2, "weekly": 14, "monthly": 60},
        risk_score=0.2,
        last_updated=datetime.now(),
        transaction_count=200
    )


@pytest.fixture
def sample_request_data():
    """Create sample request data for testing."""
    return {
        "transaction": {
            "id": "tx_risk_request_001",
            "user_id": "user_risk_request_123",
            "amount": "350.00",
            "currency": "USD",
            "merchant": "Online Store",
            "category": "retail",
            "location": {
                "country": "US",
                "city": "Portland",
                "latitude": 45.5152,
                "longitude": -122.6784,
                "ip_address": "10.0.0.1"
            },
            "timestamp": datetime.now().isoformat(),
            "card_type": "credit",
            "device_info": {
                "device_id": "device_risk_request_001",
                "device_type": "desktop",
                "os": "Windows",
                "browser": "Chrome",
                "fingerprint": "fp_risk_request_123"
            },
            "ip_address": "10.0.0.1",
            "session_id": "session_risk_request_001",
            "metadata": {"source": "web"}
        },
        "assessment_type": "comprehensive"
    }


class TestRiskAssessor:
    """Test cases for RiskAssessor functionality."""
    
    def test_initialization(self, mock_memory_manager):
        """Test risk assessor initialization."""
        assessor = RiskAssessor(mock_memory_manager)
        
        assert assessor.memory_manager == mock_memory_manager
        assert assessor.config.agent_name == "RiskAssessor"
        assert AgentCapability.RISK_ASSESSMENT in assessor.config.capabilities
        assert "risk_thresholds" in assessor.config.custom_parameters
        assert len(assessor.risk_weights) > 0
        assert len(assessor.country_risk_scores) > 0
    
    def test_custom_configuration(self, mock_memory_manager):
        """Test risk assessor with custom configuration."""
        custom_config = AgentConfiguration(
            agent_id="custom_risk_assessor",
            agent_name="CustomRiskAssessor",
            version="2.0.0",
            capabilities=[AgentCapability.RISK_ASSESSMENT],
            custom_parameters={
                "risk_thresholds": {"low": 0.2, "medium": 0.5, "high": 0.7}
            }
        )
        
        assessor = RiskAssessor(mock_memory_manager, custom_config)
        
        assert assessor.config.agent_id == "custom_risk_assessor"
        assert assessor.config.custom_parameters["risk_thresholds"]["low"] == 0.2
    
    def test_extract_transaction_valid(self, risk_assessor, sample_request_data):
        """Test extracting valid transaction from request data."""
        transaction = risk_assessor._extract_transaction(sample_request_data)
        
        assert transaction is not None
        assert transaction.id == "tx_risk_request_001"
        assert transaction.user_id == "user_risk_request_123"
        assert transaction.amount == Decimal("350.00")
        assert transaction.merchant == "Online Store"
        assert transaction.location.city == "Portland"
    
    def test_extract_transaction_invalid(self, risk_assessor):
        """Test extracting transaction from invalid request data."""
        invalid_data = {"invalid": "data"}
        
        transaction = risk_assessor._extract_transaction(invalid_data)
        
        # Should handle gracefully and return a transaction with default values
        assert transaction is not None
        assert transaction.id == ""
        assert transaction.amount == Decimal("0")
    
    def test_assess_amount_risk_high(self, risk_assessor, sample_transaction, sample_user_profile, mock_memory_manager):
        """Test amount risk assessment for high-risk transaction."""
        # Set up mock to return user profile
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        
        # Create high amount transaction
        sample_transaction.amount = Decimal("2000.00")  # 4x typical max
        
        amount_risk = risk_assessor._assess_amount_risk(sample_transaction)
        
        assert amount_risk is not None
        assert amount_risk.factor_name == "amount_risk"
        assert amount_risk.risk_score > 0.5
        assert "significantly exceeds" in amount_risk.description
    
    def test_assess_amount_risk_normal(self, risk_assessor, sample_transaction, sample_user_profile, mock_memory_manager):
        """Test amount risk assessment for normal transaction."""
        # Set up mock to return user profile
        mock_memory_manager.get_user_profile.return_value = sample_user_profile
        
        # Normal amount within typical range
        sample_transaction.amount = Decimal("300.00")
        
        amount_risk = risk_assessor._assess_amount_risk(sample_transaction)
        
        # Should return None for normal amounts
        assert amount_risk is None
    
    def test_assess_amount_risk_no_profile(self, risk_assessor, sample_transaction, mock_memory_manager):
        """Test amount risk assessment with no user profile."""
        # Set up mock to return None (no profile)
        mock_memory_manager.get_user_profile.return_value = None
        
        # High amount transaction
        sample_transaction.amount = Decimal("6000.00")
        
        amount_risk = risk_assessor._assess_amount_risk(sample_transaction)
        
        assert amount_risk is not None
        assert amount_risk.factor_name == "amount_risk"
        assert "no user baseline" in amount_risk.description
    
    def test_assess_merchant_risk_high_risk_keywords(self, risk_assessor, sample_transaction):
        """Test merchant risk assessment for high-risk merchants."""
        # Test various high-risk merchant names
        high_risk_merchants = [
            "Crypto Casino Online",
            "Bitcoin Exchange Pro", 
            "Adult Entertainment Store",
            "Offshore Gambling Site"
        ]
        
        for merchant in high_risk_merchants:
            sample_transaction.merchant = merchant
            
            merchant_risk = risk_assessor._assess_merchant_risk(sample_transaction)
            
            assert merchant_risk is not None
            assert merchant_risk.factor_name == "merchant_risk"
            assert merchant_risk.risk_score >= 0.5
            assert "High-risk merchant category" in merchant_risk.description
    
    def test_assess_merchant_risk_normal(self, risk_assessor, sample_transaction):
        """Test merchant risk assessment for normal merchants."""
        sample_transaction.merchant = "Regular Electronics Store"
        
        merchant_risk = risk_assessor._assess_merchant_risk(sample_transaction)
        
        # Should return None for normal merchants
        assert merchant_risk is None
    
    def test_assess_device_risk_suspicious(self, risk_assessor, sample_transaction):
        """Test device risk assessment for suspicious devices."""
        # Create suspicious device info
        sample_transaction.device_info.device_type = "unknown"
        sample_transaction.device_info.os = "custom"
        sample_transaction.device_info.fingerprint = ""  # Missing fingerprint
        
        device_risk = risk_assessor._assess_device_risk(sample_transaction)
        
        assert device_risk is not None
        assert device_risk.factor_name == "device_risk"
        assert device_risk.risk_score > 0.5
        assert "Suspicious device characteristics" in device_risk.description
    
    def test_assess_device_risk_normal(self, risk_assessor, sample_transaction):
        """Test device risk assessment for normal devices."""
        # Normal device info (already set in fixture)
        device_risk = risk_assessor._assess_device_risk(sample_transaction)
        
        # Should return None for normal devices
        assert device_risk is None
    
    def test_assess_behavioral_risk_new_user(self, risk_assessor, sample_transaction, mock_memory_manager):
        """Test behavioral risk assessment for new user."""
        # Set up mock to return minimal transaction history
        mock_memory_manager.get_user_transaction_history.return_value = []
        
        behavioral_risk = risk_assessor._assess_behavioral_risk(sample_transaction)
        
        assert behavioral_risk is not None
        assert behavioral_risk.factor_name == "behavioral_risk"
        assert "Insufficient transaction history" in behavioral_risk.description
    
    def test_assess_behavioral_risk_deviations(self, risk_assessor, sample_transaction, mock_memory_manager):
        """Test behavioral risk assessment with behavioral deviations."""
        # Create mock transaction history with different patterns
        mock_transactions = []
        for i in range(10):
            mock_tx = Transaction(
                id=f"mock_tx_{i}",
                user_id=sample_transaction.user_id,
                amount=Decimal("100.00"),
                currency="USD",
                merchant="Regular Store",  # Different from test transaction
                category="groceries",  # Different from test transaction
                location=sample_transaction.location,
                timestamp=datetime.now() - timedelta(days=i),
                card_type="credit",
                device_info=sample_transaction.device_info,
                ip_address="192.168.1.100",
                session_id=f"session_{i}"
            )
            mock_transactions.append(mock_tx)
        
        mock_memory_manager.get_user_transaction_history.return_value = mock_transactions
        
        behavioral_risk = risk_assessor._assess_behavioral_risk(sample_transaction)
        
        assert behavioral_risk is not None
        assert behavioral_risk.factor_name == "behavioral_risk"
        assert "Behavioral deviations" in behavioral_risk.description
    
    def test_assess_velocity_risk_high(self, risk_assessor, sample_transaction, mock_memory_manager):
        """Test velocity risk assessment for high velocity."""
        # Create recent transactions for high velocity
        recent_transactions = []
        base_time = sample_transaction.timestamp
        
        for i in range(4):  # 4 transactions in recent history
            tx = Transaction(
                id=f"velocity_tx_{i}",
                user_id=sample_transaction.user_id,
                amount=Decimal("100.00"),
                currency="USD",
                merchant="Store",
                category="retail",
                location=sample_transaction.location,
                timestamp=base_time - timedelta(minutes=i * 2),  # Every 2 minutes
                card_type="credit",
                device_info=sample_transaction.device_info,
                ip_address="192.168.1.100",
                session_id=f"velocity_session_{i}"
            )
            recent_transactions.append(tx)
        
        mock_memory_manager.get_user_transaction_history.return_value = recent_transactions
        
        velocity_risk = risk_assessor._assess_velocity_risk(sample_transaction)
        
        assert velocity_risk is not None
        assert velocity_risk.factor_name == "velocity_risk"
        assert velocity_risk.risk_score > 0.5
        assert "High transaction velocity" in velocity_risk.description
    
    def test_assess_velocity_risk_normal(self, risk_assessor, sample_transaction, mock_memory_manager):
        """Test velocity risk assessment for normal velocity."""
        # Set up mock to return minimal recent transactions
        mock_memory_manager.get_user_transaction_history.return_value = []
        
        velocity_risk = risk_assessor._assess_velocity_risk(sample_transaction)
        
        # Should return None for normal velocity
        assert velocity_risk is None
    
    def test_assess_geographic_risk(self, risk_assessor, sample_transaction):
        """Test geographic risk assessment."""
        geographic_risk = risk_assessor._assess_geographic_risk(sample_transaction)
        
        assert geographic_risk is not None
        assert isinstance(geographic_risk.location_risk_score, float)
        assert 0 <= geographic_risk.location_risk_score <= 1
        assert geographic_risk.country_risk_level in ["low", "medium", "high", "critical"]
        assert isinstance(geographic_risk.distance_from_home, float)
    
    def test_assess_geographic_risk_high_risk_country(self, risk_assessor, sample_transaction):
        """Test geographic risk assessment for high-risk country."""
        # Set transaction location to high-risk country
        sample_transaction.location.country = "XX"  # High-risk country in test data
        
        geographic_risk = risk_assessor._assess_geographic_risk(sample_transaction)
        
        assert geographic_risk.location_risk_score > 0.5
        assert geographic_risk.country_risk_level in ["high", "critical"]
        assert any("High-risk country" in factor for factor in geographic_risk.risk_factors)
    
    def test_assess_temporal_risk(self, risk_assessor, sample_transaction):
        """Test temporal risk assessment."""
        temporal_risk = risk_assessor._assess_temporal_risk(sample_transaction)
        
        assert temporal_risk is not None
        assert isinstance(temporal_risk.time_risk_score, float)
        assert 0 <= temporal_risk.time_risk_score <= 1
        assert isinstance(temporal_risk.unusual_hour_risk, float)
        assert isinstance(temporal_risk.frequency_risk, float)
    
    def test_assess_temporal_risk_unusual_hour(self, risk_assessor, sample_transaction):
        """Test temporal risk assessment for unusual hours."""
        # Set transaction time to late night
        sample_transaction.timestamp = sample_transaction.timestamp.replace(hour=3)
        
        temporal_risk = risk_assessor._assess_temporal_risk(sample_transaction)
        
        assert temporal_risk.unusual_hour_risk >= 0.7
        assert temporal_risk.time_risk_score > 0.2
        assert any("unusual hour" in factor for factor in temporal_risk.risk_factors)
    
    def test_perform_cross_reference_checks(self, risk_assessor, sample_transaction):
        """Test cross-reference checks."""
        cross_ref_results = risk_assessor._perform_cross_reference_checks(sample_transaction)
        
        # Should return a list (may be empty for clean transaction)
        assert isinstance(cross_ref_results, list)
    
    def test_cross_reference_blacklisted_ip(self, risk_assessor, sample_transaction):
        """Test cross-reference check for blacklisted IP."""
        # Set IP to a blacklisted one
        sample_transaction.ip_address = "192.0.2.1"  # In test blacklist
        
        cross_ref_results = risk_assessor._perform_cross_reference_checks(sample_transaction)
        
        # Should find IP blacklist match
        ip_matches = [cr for cr in cross_ref_results if cr.reference_type == "ip_blacklist"]
        assert len(ip_matches) > 0
        assert ip_matches[0].match_found is True
        assert ip_matches[0].risk_impact > 0.5
    
    def test_cross_reference_watchlist_user(self, risk_assessor, sample_transaction):
        """Test cross-reference check for watchlist user."""
        # Set user to a watchlisted one
        sample_transaction.user_id = "suspicious_user_001"  # In test watchlist
        
        cross_ref_results = risk_assessor._perform_cross_reference_checks(sample_transaction)
        
        # Should find user watchlist match
        user_matches = [cr for cr in cross_ref_results if cr.reference_type == "user_watchlist"]
        assert len(user_matches) > 0
        assert user_matches[0].match_found is True
        assert user_matches[0].risk_impact > 0.5
    
    def test_calculate_overall_risk_score(self, risk_assessor):
        """Test overall risk score calculation."""
        # Create a risk assessment result with various risk factors
        result = RiskAssessmentResult(
            transaction_id="test_tx",
            overall_risk_score=0.0,
            risk_level="low",
            confidence=0.0
        )
        
        # Add risk factors
        result.risk_factors = [
            RiskFactor(
                factor_name="amount_risk",
                risk_score=0.7,
                confidence=0.8,
                description="High amount",
                weight=0.25
            ),
            RiskFactor(
                factor_name="merchant_risk",
                risk_score=0.5,
                confidence=0.9,
                description="Suspicious merchant",
                weight=0.2
            )
        ]
        
        # Add geographic risk
        result.geographic_risk = GeographicRisk(
            location_risk_score=0.6,
            country_risk_level="medium",
            travel_pattern_risk=0.3,
            ip_location_mismatch=False,
            distance_from_home=100.0
        )
        
        overall_score = risk_assessor._calculate_overall_risk_score(result)
        
        assert 0 <= overall_score <= 1
        assert overall_score > 0.4  # Should be elevated due to risk factors
    
    def test_determine_risk_level(self, risk_assessor):
        """Test risk level determination."""
        # Test different risk scores
        assert risk_assessor._determine_risk_level(0.1) == "minimal"
        assert risk_assessor._determine_risk_level(0.4) == "low"
        assert risk_assessor._determine_risk_level(0.65) == "medium"
        assert risk_assessor._determine_risk_level(0.85) == "high"
        assert risk_assessor._determine_risk_level(0.95) == "critical"
    
    def test_process_request_success(self, risk_assessor, mock_memory_manager, sample_request_data):
        """Test successful request processing."""
        # Set up mock memory manager
        mock_memory_manager.get_user_profile.return_value = None
        mock_memory_manager.get_user_transaction_history.return_value = []
        
        result = risk_assessor.process_request(sample_request_data)
        
        assert result.success is True
        assert "risk_assessment" in result.result_data
        assert result.confidence_score >= 0
    
    def test_process_request_invalid_data(self, risk_assessor):
        """Test request processing with invalid data."""
        invalid_request = {"invalid": "data"}
        
        result = risk_assessor.process_request(invalid_request)
        
        assert result.success is False
        assert "Invalid transaction data" in result.error_message
    
    def test_check_threshold_breaches(self, risk_assessor):
        """Test threshold breach detection."""
        # Create result with high risk scores
        result = RiskAssessmentResult(
            transaction_id="test_tx",
            overall_risk_score=0.85,  # Above high threshold
            risk_level="high",
            confidence=0.8
        )
        
        # Add high-risk factor
        result.risk_factors = [
            RiskFactor(
                factor_name="amount_risk",
                risk_score=0.9,  # Above critical threshold
                confidence=0.8,
                description="Very high amount",
                weight=0.25
            )
        ]
        
        breaches = risk_assessor._check_threshold_breaches(result)
        
        assert len(breaches) > 0
        assert any("Overall risk score" in breach for breach in breaches)
        assert any("amount_risk" in breach for breach in breaches)
    
    def test_generate_risk_recommendations(self, risk_assessor):
        """Test risk recommendation generation."""
        # Create high-risk result
        result = RiskAssessmentResult(
            transaction_id="test_tx",
            overall_risk_score=0.85,
            risk_level="high",
            confidence=0.8
        )
        
        recommendations = risk_assessor._generate_risk_recommendations(result)
        
        assert len(recommendations) > 0
        assert any("DECLINE" in rec for rec in recommendations)
    
    def test_generate_mitigation_suggestions(self, risk_assessor):
        """Test risk mitigation suggestion generation."""
        # Create result with various risk factors
        result = RiskAssessmentResult(
            transaction_id="test_tx",
            overall_risk_score=0.6,
            risk_level="medium",
            confidence=0.7
        )
        
        # Add high amount risk
        result.risk_factors = [
            RiskFactor(
                factor_name="amount_risk",
                risk_score=0.8,
                confidence=0.8,
                description="High amount",
                weight=0.25
            )
        ]
        
        suggestions = risk_assessor._generate_mitigation_suggestions(result)
        
        assert len(suggestions) > 0
        assert any("authentication" in sug.lower() for sug in suggestions)
    
    def test_update_risk_thresholds(self, risk_assessor):
        """Test risk threshold updates."""
        new_thresholds = {"low": 0.25, "medium": 0.55, "high": 0.75}
        
        success = risk_assessor.update_risk_thresholds(new_thresholds)
        
        assert success is True
        assert risk_assessor.risk_thresholds["low"] == 0.25
        assert risk_assessor.risk_thresholds["medium"] == 0.55
        assert risk_assessor.risk_thresholds["high"] == 0.75
    
    def test_get_risk_statistics(self, risk_assessor):
        """Test risk statistics retrieval."""
        stats = risk_assessor.get_risk_statistics()
        
        assert "risk_thresholds" in stats
        assert "risk_weights" in stats
        assert "fraud_indicators_count" in stats
        assert "country_risk_levels" in stats
        
        # Verify structure
        assert isinstance(stats["risk_thresholds"], dict)
        assert isinstance(stats["fraud_indicators_count"], dict)
        assert isinstance(stats["country_risk_levels"], int)
    
    def test_agent_status_and_health(self, risk_assessor):
        """Test agent status and health check functionality."""
        # Get status
        status = risk_assessor.get_status()
        
        assert status["agent_name"] == "RiskAssessor"
        assert status["status"] == "ready"
        assert "risk_assessment" in [cap for cap in status["capabilities"]]
        
        # Get health check
        health = risk_assessor.get_health_check()
        
        assert health["health_status"] == "healthy"
        assert len(health["issues"]) == 0


if __name__ == "__main__":
    pytest.main([__file__])