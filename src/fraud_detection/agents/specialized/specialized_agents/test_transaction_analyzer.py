"""
Unit tests for the Transaction Analyzer Agent.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from .transaction_analyzer import (
    TransactionAnalyzer, VelocityPattern, ValidationResult, 
    TransactionAnalysis
)
from .base_agent import AgentConfiguration, AgentCapability
from memory_system.models import Transaction, Location, DeviceInfo, FraudDecision
from memory_system.memory_manager import MemoryManager
from memory_system.context_manager import ContextManager


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager for testing."""
    return Mock(spec=MemoryManager)


@pytest.fixture
def mock_context_manager():
    """Create a mock context manager for testing."""
    return Mock(spec=ContextManager)


@pytest.fixture
def transaction_analyzer(mock_memory_manager, mock_context_manager):
    """Create a transaction analyzer for testing."""
    return TransactionAnalyzer(mock_memory_manager, mock_context_manager)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return Transaction(
        id="tx_test_001",
        user_id="user_test_123",
        amount=Decimal("150.00"),
        currency="USD",
        merchant="Test Store",
        category="retail",
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
def sample_request_data():
    """Create sample request data for testing."""
    return {
        "transaction": {
            "id": "tx_request_001",
            "user_id": "user_request_123",
            "amount": "250.00",
            "currency": "USD",
            "merchant": "Amazon",
            "category": "online_retail",
            "location": {
                "country": "US",
                "city": "Seattle",
                "latitude": 47.6062,
                "longitude": -122.3321,
                "ip_address": "10.0.0.1"
            },
            "timestamp": datetime.now().isoformat(),
            "card_type": "credit",
            "device_info": {
                "device_id": "device_request_001",
                "device_type": "desktop",
                "os": "Windows",
                "browser": "Chrome",
                "fingerprint": "fp_request_123"
            },
            "ip_address": "10.0.0.1",
            "session_id": "session_request_001",
            "metadata": {"source": "web"}
        }
    }


class TestTransactionAnalyzer:
    """Test cases for TransactionAnalyzer functionality."""
    
    def test_initialization(self, mock_memory_manager, mock_context_manager):
        """Test transaction analyzer initialization."""
        analyzer = TransactionAnalyzer(mock_memory_manager, mock_context_manager)
        
        assert analyzer.memory_manager == mock_memory_manager
        assert analyzer.context_manager == mock_context_manager
        assert analyzer.config.agent_name == "TransactionAnalyzer"
        assert AgentCapability.TRANSACTION_ANALYSIS in analyzer.config.capabilities
        assert AgentCapability.REAL_TIME_PROCESSING in analyzer.config.capabilities
        assert analyzer.velocity_cache == {}
    
    def test_custom_configuration(self, mock_memory_manager, mock_context_manager):
        """Test transaction analyzer with custom configuration."""
        custom_config = AgentConfiguration(
            agent_id="custom_analyzer",
            agent_name="CustomTransactionAnalyzer",
            version="2.0.0",
            capabilities=[AgentCapability.TRANSACTION_ANALYSIS],
            max_concurrent_requests=100,
            custom_parameters={"high_risk_threshold": 0.8}
        )
        
        analyzer = TransactionAnalyzer(
            mock_memory_manager, 
            mock_context_manager, 
            custom_config
        )
        
        assert analyzer.config.agent_id == "custom_analyzer"
        assert analyzer.config.max_concurrent_requests == 100
        assert analyzer.config.custom_parameters["high_risk_threshold"] == 0.8
    
    def test_extract_transaction_valid(self, transaction_analyzer, sample_request_data):
        """Test extracting valid transaction from request data."""
        transaction = transaction_analyzer._extract_transaction(sample_request_data)
        
        assert transaction is not None
        assert transaction.id == "tx_request_001"
        assert transaction.user_id == "user_request_123"
        assert transaction.amount == Decimal("250.00")
        assert transaction.merchant == "Amazon"
        assert transaction.location.city == "Seattle"
        assert transaction.device_info.device_type == "desktop"
    
    def test_extract_transaction_invalid(self, transaction_analyzer):
        """Test extracting transaction from invalid request data."""
        invalid_data = {"invalid": "data"}
        
        transaction = transaction_analyzer._extract_transaction(invalid_data)
        
        # Should handle gracefully and return a transaction with default values
        assert transaction is not None
        assert transaction.id == ""
        assert transaction.amount == Decimal("0")
    
    def test_validate_transaction_valid(self, transaction_analyzer, sample_transaction):
        """Test validation of a valid transaction."""
        result = transaction_analyzer._validate_transaction(sample_transaction)
        
        assert result.is_valid is True
        assert len(result.validation_errors) == 0
    
    def test_validate_transaction_invalid_amount(self, transaction_analyzer, sample_transaction):
        """Test validation of transaction with invalid amount."""
        sample_transaction.amount = Decimal("0")
        
        result = transaction_analyzer._validate_transaction(sample_transaction)
        
        assert result.is_valid is False
        assert "Invalid transaction amount" in result.validation_errors
    
    def test_validate_transaction_missing_fields(self, transaction_analyzer, sample_transaction):
        """Test validation of transaction with missing fields."""
        sample_transaction.id = ""
        sample_transaction.user_id = ""
        
        result = transaction_analyzer._validate_transaction(sample_transaction)
        
        assert result.is_valid is False
        assert "Missing transaction ID" in result.validation_errors
        assert "Missing user ID" in result.validation_errors
    
    def test_validate_transaction_high_amount(self, transaction_analyzer, sample_transaction):
        """Test validation of high-amount transaction."""
        sample_transaction.amount = Decimal("15000.00")
        
        result = transaction_analyzer._validate_transaction(sample_transaction)
        
        assert result.is_valid is True  # Still valid, but has risk indicators
        assert "High transaction amount" in result.risk_indicators
    
    def test_validate_transaction_late_night(self, transaction_analyzer, sample_transaction):
        """Test validation of late night transaction."""
        sample_transaction.timestamp = sample_transaction.timestamp.replace(hour=3)
        
        result = transaction_analyzer._validate_transaction(sample_transaction)
        
        assert result.is_valid is True
        assert "Late night transaction" in result.risk_indicators
    
    def test_detect_rapid_fire_pattern(self, transaction_analyzer, sample_transaction):
        """Test detection of rapid-fire velocity pattern."""
        # Create multiple transactions in short time
        transactions = []
        base_time = datetime.now()
        
        for i in range(5):
            tx = Transaction(
                id=f"tx_rapid_{i}",
                user_id=sample_transaction.user_id,
                amount=Decimal(f"{100 + i * 50}.00"),
                currency="USD",
                merchant=f"Store_{i}",
                category="retail",
                location=sample_transaction.location,
                timestamp=base_time + timedelta(minutes=i * 2),
                card_type="credit",
                device_info=sample_transaction.device_info,
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            transactions.append(tx)
        
        pattern = transaction_analyzer._detect_rapid_fire_pattern(transactions)
        
        assert pattern is not None
        assert pattern.pattern_type == "rapid_fire"
        assert pattern.transaction_count == 5
        assert pattern.time_window_minutes <= 10
        assert pattern.risk_score > 0
    
    def test_detect_escalating_amounts_pattern(self, transaction_analyzer, sample_transaction):
        """Test detection of escalating amounts pattern."""
        # Create transactions with escalating amounts
        transactions = []
        base_time = datetime.now()
        amounts = [100, 150, 200, 300, 500]
        
        for i, amount in enumerate(amounts):
            tx = Transaction(
                id=f"tx_escalate_{i}",
                user_id=sample_transaction.user_id,
                amount=Decimal(f"{amount}.00"),
                currency="USD",
                merchant="Test Store",
                category="retail",
                location=sample_transaction.location,
                timestamp=base_time + timedelta(minutes=i * 10),
                card_type="credit",
                device_info=sample_transaction.device_info,
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            transactions.append(tx)
        
        pattern = transaction_analyzer._detect_escalating_amounts_pattern(transactions)
        
        assert pattern is not None
        assert pattern.pattern_type == "escalating_amounts"
        assert pattern.risk_score > 0
        assert "Escalating amounts" in pattern.description
    
    def test_detect_geographic_velocity_pattern(self, transaction_analyzer, sample_transaction):
        """Test detection of geographic velocity pattern."""
        # Create transactions in different locations with impossible travel time
        tx1 = sample_transaction
        tx1.location = Location(country="US", city="New York")
        tx1.timestamp = datetime.now()
        
        tx2 = Transaction(
            id="tx_geo_2",
            user_id=sample_transaction.user_id,
            amount=Decimal("200.00"),
            currency="USD",
            merchant="Paris Store",
            category="retail",
            location=Location(country="FR", city="Paris"),
            timestamp=datetime.now() + timedelta(minutes=30),  # 30 minutes later
            card_type="credit",
            device_info=sample_transaction.device_info,
            ip_address="82.45.123.45",
            session_id="session_geo_2"
        )
        
        transactions = [tx1, tx2]
        pattern = transaction_analyzer._detect_geographic_velocity_pattern(transactions)
        
        assert pattern is not None
        assert pattern.pattern_type == "geographic_velocity"
        assert "Impossible travel" in pattern.description
        assert pattern.risk_score > 0
    
    def test_calculate_risk_score_low_risk(self, transaction_analyzer, sample_transaction):
        """Test risk score calculation for low-risk transaction."""
        validation_result = ValidationResult(is_valid=True)
        velocity_patterns = []
        contextual_factors = {"contextual_risk_score": 0.1}
        
        risk_score = transaction_analyzer._calculate_risk_score(
            sample_transaction, validation_result, velocity_patterns, contextual_factors
        )
        
        assert 0.0 <= risk_score <= 0.3  # Should be low risk
    
    def test_calculate_risk_score_high_risk(self, transaction_analyzer, sample_transaction):
        """Test risk score calculation for high-risk transaction."""
        # High amount transaction
        sample_transaction.amount = Decimal("5000.00")
        sample_transaction.timestamp = sample_transaction.timestamp.replace(hour=3)  # Late night
        
        validation_result = ValidationResult(
            is_valid=True,
            risk_indicators=["High transaction amount", "Late night transaction"]
        )
        
        velocity_patterns = [
            VelocityPattern(
                pattern_type="rapid_fire",
                transaction_count=5,
                time_window_minutes=10,
                total_amount=Decimal("2000.00"),
                risk_score=0.8,
                description="Rapid fire pattern"
            )
        ]
        
        contextual_factors = {"contextual_risk_score": 0.7}
        
        risk_score = transaction_analyzer._calculate_risk_score(
            sample_transaction, validation_result, velocity_patterns, contextual_factors
        )
        
        assert risk_score >= 0.5  # Should be high risk
    
    def test_generate_recommendation_approve(self, transaction_analyzer):
        """Test recommendation generation for approval."""
        validation_result = ValidationResult(is_valid=True)
        
        recommendation, confidence = transaction_analyzer._generate_recommendation(0.2, validation_result)
        
        assert recommendation == "APPROVE"
        assert confidence > 0.8
    
    def test_generate_recommendation_decline(self, transaction_analyzer):
        """Test recommendation generation for decline."""
        validation_result = ValidationResult(is_valid=True)
        
        recommendation, confidence = transaction_analyzer._generate_recommendation(0.8, validation_result)
        
        assert recommendation == "DECLINE"
        assert confidence > 0.7
    
    def test_generate_recommendation_flag(self, transaction_analyzer):
        """Test recommendation generation for flagging."""
        validation_result = ValidationResult(is_valid=True)
        
        recommendation, confidence = transaction_analyzer._generate_recommendation(0.5, validation_result)
        
        assert recommendation == "FLAG_FOR_REVIEW"
        assert confidence > 0.7
    
    def test_generate_recommendation_invalid_transaction(self, transaction_analyzer):
        """Test recommendation for invalid transaction."""
        validation_result = ValidationResult(
            is_valid=False,
            validation_errors=["Missing required fields"]
        )
        
        recommendation, confidence = transaction_analyzer._generate_recommendation(0.3, validation_result)
        
        assert recommendation == "DECLINE"
        assert confidence >= 0.95
    
    def test_process_request_success(self, transaction_analyzer, mock_memory_manager, mock_context_manager, sample_request_data):
        """Test successful request processing."""
        # Mock context manager response
        mock_context_manager.get_contextual_recommendation.return_value = {
            "risk_score": 0.2,
            "recommendation": "APPROVE",
            "confidence": 0.8,
            "context_summary": {"similar_cases_count": 3, "has_user_profile": True}
        }
        
        # Mock memory manager
        mock_memory_manager.store_transaction.return_value = True
        
        result = transaction_analyzer.process_request(sample_request_data)
        
        assert result.success is True
        assert "analysis" in result.result_data
        assert result.confidence_score > 0
        assert mock_memory_manager.store_transaction.called
    
    def test_process_request_invalid_data(self, transaction_analyzer):
        """Test request processing with invalid data."""
        invalid_request = {"invalid": "data"}
        
        result = transaction_analyzer.process_request(invalid_request)
        
        assert result.success is False
        assert "Invalid transaction data" in result.error_message
    
    def test_velocity_cache_update(self, transaction_analyzer, sample_transaction):
        """Test velocity cache update functionality."""
        # Initially empty
        assert len(transaction_analyzer.velocity_cache) == 0
        
        # Update cache
        transaction_analyzer._update_velocity_cache(sample_transaction)
        
        # Should have entry for user
        assert sample_transaction.user_id in transaction_analyzer.velocity_cache
        assert len(transaction_analyzer.velocity_cache[sample_transaction.user_id]) == 1
        
        # Add another transaction
        tx2 = sample_transaction
        tx2.id = "tx_test_002"
        tx2.timestamp = datetime.now()
        
        transaction_analyzer._update_velocity_cache(tx2)
        
        # Should have 2 transactions for user
        assert len(transaction_analyzer.velocity_cache[sample_transaction.user_id]) == 2
    
    def test_velocity_cache_cleanup(self, transaction_analyzer, sample_transaction):
        """Test velocity cache cleanup functionality."""
        # Add old transaction
        old_transaction = sample_transaction
        old_transaction.timestamp = datetime.now() - timedelta(hours=3)
        transaction_analyzer._update_velocity_cache(old_transaction)
        
        # Add recent transaction
        recent_transaction = sample_transaction
        recent_transaction.id = "tx_recent"
        recent_transaction.timestamp = datetime.now()
        transaction_analyzer._update_velocity_cache(recent_transaction)
        
        # Force cleanup
        transaction_analyzer._cleanup_velocity_cache()
        
        # Should only have recent transaction
        user_transactions = transaction_analyzer.velocity_cache.get(sample_transaction.user_id, [])
        assert len(user_transactions) == 1
        assert user_transactions[0].id == "tx_recent"
    
    def test_high_risk_merchant_detection(self, transaction_analyzer):
        """Test high-risk merchant detection."""
        assert transaction_analyzer._is_high_risk_merchant("Casino Royal") is True
        assert transaction_analyzer._is_high_risk_merchant("Bitcoin Exchange") is True
        assert transaction_analyzer._is_high_risk_merchant("Regular Store") is False
        assert transaction_analyzer._is_high_risk_merchant("Starbucks") is False
    
    def test_distance_estimation(self, transaction_analyzer):
        """Test distance estimation between locations."""
        loc1 = Location(country="US", city="New York")
        loc2 = Location(country="FR", city="Paris")
        loc3 = Location(country="US", city="Boston")
        loc4 = Location(country="US", city="New York")
        
        # Different countries
        distance1 = transaction_analyzer._estimate_distance(loc1, loc2)
        assert distance1 == 1000.0
        
        # Same country, different cities
        distance2 = transaction_analyzer._estimate_distance(loc1, loc3)
        assert distance2 == 200.0
        
        # Same city
        distance3 = transaction_analyzer._estimate_distance(loc1, loc4)
        assert distance3 == 0.0
    
    def test_get_velocity_statistics(self, transaction_analyzer, sample_transaction):
        """Test velocity statistics retrieval."""
        # Add some transactions to cache
        transaction_analyzer._update_velocity_cache(sample_transaction)
        
        tx2 = sample_transaction
        tx2.id = "tx_stats_2"
        tx2.user_id = "user_stats_2"
        transaction_analyzer._update_velocity_cache(tx2)
        
        stats = transaction_analyzer.get_velocity_statistics()
        
        assert "cached_users" in stats
        assert "cached_transactions" in stats
        assert "cache_size_mb" in stats
        assert "last_cleanup" in stats
        assert stats["cached_users"] >= 1
        assert stats["cached_transactions"] >= 2
    
    def test_agent_status_and_health(self, transaction_analyzer):
        """Test agent status and health check functionality."""
        # Get status
        status = transaction_analyzer.get_status()
        
        assert status["agent_name"] == "TransactionAnalyzer"
        assert status["status"] == "ready"
        assert "transaction_analysis" in [cap for cap in status["capabilities"]]
        
        # Get health check
        health = transaction_analyzer.get_health_check()
        
        assert health["health_status"] == "healthy"
        assert len(health["issues"]) == 0
        assert "uptime_seconds" in health


if __name__ == "__main__":
    pytest.main([__file__])