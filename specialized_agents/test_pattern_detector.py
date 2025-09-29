"""
Unit tests for the Pattern Detection Agent.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from .pattern_detector import (
    PatternDetector, AnomalyScore, BehavioralPattern, 
    TrendAnalysis, PatternDetectionResult
)
from .base_agent import AgentConfiguration, AgentCapability
from memory_system.models import Transaction, Location, DeviceInfo, FraudPattern
from memory_system.memory_manager import MemoryManager
from memory_system.pattern_learning import PatternLearningEngine


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager for testing."""
    return Mock(spec=MemoryManager)


@pytest.fixture
def mock_pattern_learning_engine():
    """Create a mock pattern learning engine for testing."""
    return Mock(spec=PatternLearningEngine)


@pytest.fixture
def pattern_detector(mock_memory_manager, mock_pattern_learning_engine):
    """Create a pattern detector for testing."""
    return PatternDetector(mock_memory_manager, mock_pattern_learning_engine)


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return Transaction(
        id="tx_pattern_001",
        user_id="user_pattern_123",
        amount=Decimal("200.00"),
        currency="USD",
        merchant="Test Merchant",
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
            device_id="device_pattern_001",
            device_type="mobile",
            os="iOS",
            browser="Safari",
            fingerprint="fp_pattern_123"
        ),
        ip_address="192.168.1.1",
        session_id="session_pattern_001",
        metadata={"channel": "mobile_app"}
    )


@pytest.fixture
def sample_request_data():
    """Create sample request data for testing."""
    return {
        "transaction": {
            "id": "tx_pattern_request_001",
            "user_id": "user_pattern_request_123",
            "amount": "350.00",
            "currency": "USD",
            "merchant": "Electronics Store",
            "category": "electronics",
            "location": {
                "country": "US",
                "city": "Boston",
                "latitude": 42.3601,
                "longitude": -71.0589,
                "ip_address": "10.0.0.1"
            },
            "timestamp": datetime.now().isoformat(),
            "card_type": "credit",
            "device_info": {
                "device_id": "device_pattern_request_001",
                "device_type": "desktop",
                "os": "Windows",
                "browser": "Chrome",
                "fingerprint": "fp_pattern_request_123"
            },
            "ip_address": "10.0.0.1",
            "session_id": "session_pattern_request_001",
            "metadata": {"source": "web"}
        },
        "analysis_type": "full"
    }


class TestAnomalyScore:
    """Test cases for AnomalyScore dataclass."""
    
    def test_anomaly_score_creation(self):
        """Test creating an anomaly score."""
        score = AnomalyScore(
            anomaly_type="amount_anomaly",
            score=0.8,
            confidence=0.9,
            description="High amount anomaly",
            statistical_evidence={"z_score": 3.2},
            threshold_used=2.5
        )
        
        assert score.anomaly_type == "amount_anomaly"
        assert score.score == 0.8
        assert score.confidence == 0.9
        assert score.description == "High amount anomaly"
        assert score.statistical_evidence["z_score"] == 3.2
        assert score.threshold_used == 2.5


class TestBehavioralPattern:
    """Test cases for BehavioralPattern dataclass."""
    
    def test_behavioral_pattern_creation(self):
        """Test creating a behavioral pattern."""
        pattern = BehavioralPattern(
            pattern_id="pattern_001",
            pattern_type="escalating_spending",
            description="User shows escalating spending",
            strength=0.7,
            frequency=5,
            last_seen=datetime.now(),
            trend_direction="increasing",
            risk_level="medium"
        )
        
        assert pattern.pattern_id == "pattern_001"
        assert pattern.pattern_type == "escalating_spending"
        assert pattern.strength == 0.7
        assert pattern.risk_level == "medium"


class TestTrendAnalysis:
    """Test cases for TrendAnalysis dataclass."""
    
    def test_trend_analysis_creation(self):
        """Test creating a trend analysis."""
        trend = TrendAnalysis(
            metric_name="transaction_amount",
            trend_direction="increasing",
            trend_strength=0.6,
            prediction_confidence=0.8,
            current_value=200.0,
            predicted_next_value=220.0,
            time_window_days=30,
            data_points=25
        )
        
        assert trend.metric_name == "transaction_amount"
        assert trend.trend_direction == "increasing"
        assert trend.trend_strength == 0.6
        assert trend.prediction_confidence == 0.8


class TestPatternDetector:
    """Test cases for PatternDetector functionality."""
    
    def test_initialization(self, mock_memory_manager, mock_pattern_learning_engine):
        """Test pattern detector initialization."""
        detector = PatternDetector(mock_memory_manager, mock_pattern_learning_engine)
        
        assert detector.memory_manager == mock_memory_manager
        assert detector.pattern_learning_engine == mock_pattern_learning_engine
        assert detector.config.agent_name == "PatternDetector"
        assert AgentCapability.PATTERN_DETECTION in detector.config.capabilities
        assert detector.user_baselines == {}
        assert detector.pattern_cache == {}
    
    def test_custom_configuration(self, mock_memory_manager, mock_pattern_learning_engine):
        """Test pattern detector with custom configuration."""
        custom_config = AgentConfiguration(
            agent_id="custom_pattern_detector",
            agent_name="CustomPatternDetector",
            version="2.0.0",
            capabilities=[AgentCapability.PATTERN_DETECTION],
            custom_parameters={"anomaly_threshold": 0.8}
        )
        
        detector = PatternDetector(
            mock_memory_manager, 
            mock_pattern_learning_engine, 
            custom_config
        )
        
        assert detector.config.agent_id == "custom_pattern_detector"
        assert detector.config.custom_parameters["anomaly_threshold"] == 0.8
    
    def test_extract_transaction_valid(self, pattern_detector, sample_request_data):
        """Test extracting valid transaction from request data."""
        transaction = pattern_detector._extract_transaction(sample_request_data)
        
        assert transaction is not None
        assert transaction.id == "tx_pattern_request_001"
        assert transaction.user_id == "user_pattern_request_123"
        assert transaction.amount == Decimal("350.00")
        assert transaction.merchant == "Electronics Store"
        assert transaction.location.city == "Boston"
        assert transaction.device_info.device_type == "desktop"
    
    def test_extract_transaction_invalid(self, pattern_detector):
        """Test extracting transaction from invalid request data."""
        invalid_data = {"invalid": "data"}
        
        transaction = pattern_detector._extract_transaction(invalid_data)
        
        # Should handle gracefully and return a transaction with default values
        assert transaction is not None
        assert transaction.id == ""
        assert transaction.amount == Decimal("0")
    
    def test_detect_amount_anomaly_high_amount(self, pattern_detector, sample_transaction):
        """Test detection of high amount anomaly."""
        # Create baseline with low average amount
        baseline = {
            "amount_stats": {
                "mean": 50.0,
                "std": 20.0,
                "median": 45.0,
                "min": 10.0,
                "max": 100.0
            }
        }
        
        # Test with high amount transaction
        sample_transaction.amount = Decimal("500.00")
        
        anomaly = pattern_detector._detect_amount_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "amount_anomaly"
        assert anomaly.score > 0.5
        assert anomaly.confidence > 0.5
        assert "standard deviations" in anomaly.description
    
    def test_detect_amount_anomaly_normal_amount(self, pattern_detector, sample_transaction):
        """Test no anomaly detection for normal amount."""
        # Create baseline with similar average amount
        baseline = {
            "amount_stats": {
                "mean": 180.0,
                "std": 50.0,
                "median": 175.0,
                "min": 50.0,
                "max": 300.0
            }
        }
        
        anomaly = pattern_detector._detect_amount_anomaly(sample_transaction, baseline)
        
        assert anomaly is None
    
    def test_detect_temporal_anomaly_late_night(self, pattern_detector, sample_transaction):
        """Test detection of late night temporal anomaly."""
        # Set transaction to late night
        sample_transaction.timestamp = sample_transaction.timestamp.replace(hour=3)
        
        anomaly = pattern_detector._detect_temporal_anomaly(sample_transaction, {})
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "temporal_anomaly"
        assert anomaly.score == 0.7
        assert "late night" in anomaly.description.lower()
    
    def test_detect_temporal_anomaly_normal_time(self, pattern_detector, sample_transaction):
        """Test no anomaly detection for normal time."""
        # Set transaction to normal business hours
        sample_transaction.timestamp = sample_transaction.timestamp.replace(hour=14)
        
        anomaly = pattern_detector._detect_temporal_anomaly(sample_transaction, {})
        
        assert anomaly is None
    
    def test_detect_merchant_anomaly_high_risk(self, pattern_detector, sample_transaction):
        """Test detection of high-risk merchant anomaly."""
        sample_transaction.merchant = "Bitcoin Casino"
        
        anomaly = pattern_detector._detect_merchant_anomaly(sample_transaction, {})
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "merchant_anomaly"
        assert anomaly.score == 0.8
        assert "high-risk merchant" in anomaly.description
    
    def test_detect_merchant_anomaly_normal_merchant(self, pattern_detector, sample_transaction):
        """Test no anomaly detection for normal merchant."""
        sample_transaction.merchant = "Starbucks"
        
        anomaly = pattern_detector._detect_merchant_anomaly(sample_transaction, {})
        
        assert anomaly is None
    
    def test_detect_location_anomaly_new_country(self, pattern_detector, sample_transaction):
        """Test detection of new country location anomaly."""
        baseline = {
            "location_stats": {
                "common_countries": ["US", "CA"],
                "common_cities": ["New York", "Boston"]
            }
        }
        
        sample_transaction.location.country = "FR"
        sample_transaction.location.city = "Paris"
        
        anomaly = pattern_detector._detect_location_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "location_anomaly"
        assert anomaly.score == 0.7
        assert "new country" in anomaly.description
    
    def test_detect_location_anomaly_known_country(self, pattern_detector, sample_transaction):
        """Test no anomaly detection for known country."""
        baseline = {
            "location_stats": {
                "common_countries": ["US", "CA"],
                "common_cities": ["New York", "Boston"]
            }
        }
        
        anomaly = pattern_detector._detect_location_anomaly(sample_transaction, baseline)
        
        assert anomaly is None
    
    def test_detect_spending_patterns_escalating(self, pattern_detector):
        """Test detection of escalating spending pattern."""
        # Create transactions with escalating amounts
        transactions = []
        base_time = datetime.now()
        amounts = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550]
        
        for i, amount in enumerate(amounts):
            tx = Transaction(
                id=f"tx_escalate_{i}",
                user_id="user_escalate_123",
                amount=Decimal(f"{amount}.00"),
                currency="USD",
                merchant="Test Store",
                category="retail",
                location=Location(country="US", city="New York"),
                timestamp=base_time + timedelta(hours=i),
                card_type="credit",
                device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            transactions.append(tx)
        
        patterns = pattern_detector._detect_spending_patterns(transactions)
        
        assert len(patterns) > 0
        escalating_patterns = [p for p in patterns if p.pattern_type == "escalating_spending"]
        assert len(escalating_patterns) > 0
        
        pattern = escalating_patterns[0]
        assert pattern.strength > 0.6  # Should be high strength
        assert pattern.trend_direction == "increasing"
        assert pattern.risk_level == "medium"
    
    def test_analyze_amount_trend_increasing(self, pattern_detector):
        """Test analysis of increasing amount trend."""
        # Create transactions with increasing trend
        transactions = []
        base_time = datetime.now()
        
        for i in range(10):
            amount = 100 + i * 20  # Increasing trend
            tx = Transaction(
                id=f"tx_trend_{i}",
                user_id="user_trend_123",
                amount=Decimal(f"{amount}.00"),
                currency="USD",
                merchant="Test Store",
                category="retail",
                location=Location(country="US", city="New York"),
                timestamp=base_time + timedelta(days=i),
                card_type="credit",
                device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            transactions.append(tx)
        
        trend = pattern_detector._analyze_amount_trend(transactions, 30)
        
        assert trend is not None
        assert trend.metric_name == "transaction_amount"
        assert trend.trend_direction == "increasing"
        assert trend.trend_strength > 0
        assert trend.prediction_confidence > 0
        assert trend.predicted_next_value > trend.current_value
    
    def test_calculate_pattern_similarity(self, pattern_detector, sample_transaction, mock_memory_manager):
        """Test pattern similarity calculation."""
        # Mock recent transactions for velocity check
        mock_memory_manager.get_user_transaction_history.return_value = [
            sample_transaction, sample_transaction, sample_transaction, sample_transaction
        ]
        
        # Create a mock fraud pattern
        mock_pattern = Mock()
        mock_pattern.pattern_type = "velocity_fraud"
        
        similarity = pattern_detector._calculate_pattern_similarity(sample_transaction, mock_pattern)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be high due to velocity characteristics
    
    def test_calculate_overall_anomaly_score(self, pattern_detector):
        """Test calculation of overall anomaly score."""
        result = PatternDetectionResult(transaction_id="tx_test")
        
        # Add some anomaly scores
        result.anomaly_scores = [
            AnomalyScore("amount_anomaly", 0.8, 0.9, "High amount"),
            AnomalyScore("temporal_anomaly", 0.6, 0.7, "Late night"),
            AnomalyScore("merchant_anomaly", 0.9, 0.95, "High risk merchant")
        ]
        
        overall_score = pattern_detector._calculate_overall_anomaly_score(result)
        
        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.5  # Should be high due to multiple anomalies
    
    def test_calculate_overall_confidence(self, pattern_detector):
        """Test calculation of overall confidence."""
        result = PatternDetectionResult(transaction_id="tx_test")
        
        # Add various analysis results
        result.anomaly_scores = [
            AnomalyScore("amount_anomaly", 0.8, 0.9, "High amount")
        ]
        
        result.behavioral_patterns = [
            BehavioralPattern(
                "pattern_001", "escalating_spending", "Escalating pattern",
                0.7, 5, datetime.now(), "increasing", "medium"
            )
        ]
        
        result.trend_analyses = [
            TrendAnalysis(
                "transaction_amount", "increasing", 0.6, 0.8,
                200.0, 220.0, 30, 25
            )
        ]
        
        confidence = pattern_detector._calculate_overall_confidence(result)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.6  # Should be reasonably high
    
    def test_generate_pattern_recommendations(self, pattern_detector):
        """Test generation of pattern recommendations."""
        result = PatternDetectionResult(transaction_id="tx_test")
        result.overall_anomaly_score = 0.9
        
        # Add high anomaly scores
        result.anomaly_scores = [
            AnomalyScore("amount_anomaly", 0.8, 0.9, "High amount"),
            AnomalyScore("merchant_anomaly", 0.9, 0.95, "High risk merchant")
        ]
        
        recommendations = pattern_detector._generate_pattern_recommendations(result)
        
        assert len(recommendations) > 0
        assert any("High anomaly detected" in rec for rec in recommendations)
        assert any("Decline transaction" in rec for rec in recommendations)
    
    def test_process_request_success(self, pattern_detector, mock_memory_manager, sample_request_data):
        """Test successful request processing."""
        # Mock memory manager responses
        mock_memory_manager.get_user_transaction_history.return_value = []
        mock_memory_manager.get_all_fraud_patterns.return_value = []
        
        result = pattern_detector.process_request(sample_request_data)
        
        assert result.success is True
        assert "pattern_detection" in result.result_data
        assert result.confidence_score >= 0
    
    def test_process_request_invalid_data(self, pattern_detector):
        """Test request processing with invalid data."""
        invalid_request = {"invalid": "data"}
        
        result = pattern_detector.process_request(invalid_request)
        
        assert result.success is False
        assert "Invalid transaction data" in result.error_message
    
    def test_get_user_baseline_cached(self, pattern_detector):
        """Test getting cached user baseline."""
        user_id = "user_cached_123"
        cached_baseline = {"amount_stats": {"mean": 100.0}}
        
        # Add to cache
        pattern_detector.user_baselines[user_id] = cached_baseline
        
        baseline = pattern_detector._get_user_baseline(user_id)
        
        assert baseline == cached_baseline
    
    def test_calculate_user_baseline(self, pattern_detector, mock_memory_manager):
        """Test calculation of user baseline statistics."""
        # Mock transaction history
        transactions = []
        for i in range(10):
            tx = Transaction(
                id=f"tx_baseline_{i}",
                user_id="user_baseline_123",
                amount=Decimal(f"{100 + i * 10}.00"),
                currency="USD",
                merchant="Test Store",
                category="retail",
                location=Location(country="US", city="New York"),
                timestamp=datetime.now() - timedelta(days=i),
                card_type="credit",
                device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            transactions.append(tx)
        
        mock_memory_manager.get_user_transaction_history.return_value = transactions
        
        baseline = pattern_detector._calculate_user_baseline("user_baseline_123")
        
        assert "amount_stats" in baseline
        assert "location_stats" in baseline
        assert baseline["amount_stats"]["mean"] > 0
        assert len(baseline["location_stats"]["common_countries"]) > 0
    
    def test_pattern_cache_operations(self, pattern_detector):
        """Test pattern cache operations."""
        # Add some data to cache
        pattern_detector.pattern_cache["test_pattern"] = {"data": "test"}
        pattern_detector.user_baselines["test_user"] = {"baseline": "test"}
        
        # Get cache stats
        stats = pattern_detector.get_pattern_cache_stats()
        
        assert stats["cached_patterns"] == 1
        assert stats["cached_baselines"] == 1
        assert stats["cache_size_estimate"] > 0
        
        # Clear cache
        pattern_detector.clear_pattern_cache()
        
        assert len(pattern_detector.pattern_cache) == 0
        assert len(pattern_detector.user_baselines) == 0
    
    def test_agent_status_and_health(self, pattern_detector):
        """Test agent status and health check functionality."""
        # Get status
        status = pattern_detector.get_status()
        
        assert status["agent_name"] == "PatternDetector"
        assert status["status"] == "ready"
        assert "pattern_detection" in [cap for cap in status["capabilities"]]
        
        # Get health check
        health = pattern_detector.get_health_check()
        
        assert health["health_status"] == "healthy"
        assert len(health["issues"]) == 0


if __name__ == "__main__":
    pytest.main([__file__])