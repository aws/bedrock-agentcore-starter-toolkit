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
        amount=Decimal("250.00"),
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
def sample_user_transactions():
    """Create sample user transaction history."""
    transactions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(20):
        tx = Transaction(
            id=f"tx_history_{i:03d}",
            user_id="user_pattern_123",
            amount=Decimal(f"{100 + i * 10}.00"),
            currency="USD",
            merchant=f"Store_{i % 5}",  # 5 different stores
            category="retail",
            location=Location(country="US", city="New York"),
            timestamp=base_time + timedelta(days=i),
            card_type="credit",
            device_info=DeviceInfo(
                device_id="device_pattern_001",
                device_type="mobile",
                os="iOS"
            ),
            ip_address="192.168.1.1",
            session_id=f"session_{i}"
        )
        transactions.append(tx)
    
    return transactions


@pytest.fixture
def sample_request_data():
    """Create sample request data for testing."""
    return {
        "transaction": {
            "id": "tx_request_pattern_001",
            "user_id": "user_request_pattern_123",
            "amount": "500.00",
            "currency": "USD",
            "merchant": "Unusual Store",
            "category": "electronics",
            "location": {
                "country": "US",
                "city": "Los Angeles"
            },
            "timestamp": datetime.now().isoformat(),
            "card_type": "credit",
            "device_info": {
                "device_id": "device_request_001",
                "device_type": "desktop",
                "os": "Windows"
            },
            "ip_address": "10.0.0.1",
            "session_id": "session_request_001"
        },
        "analysis_type": "full"
    }


class TestAnomalyScore:
    """Test cases for AnomalyScore class."""
    
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
        assert score.statistical_evidence["z_score"] == 3.2


class TestBehavioralPattern:
    """Test cases for BehavioralPattern class."""
    
    def test_behavioral_pattern_creation(self):
        """Test creating a behavioral pattern."""
        pattern = BehavioralPattern(
            pattern_id="pattern_001",
            pattern_type="escalating_spending",
            description="User shows escalating spending",
            strength=0.8,
            frequency=5,
            last_seen=datetime.now(),
            trend_direction="increasing",
            risk_level="medium"
        )
        
        assert pattern.pattern_type == "escalating_spending"
        assert pattern.strength == 0.8
        assert pattern.risk_level == "medium"


class TestTrendAnalysis:
    """Test cases for TrendAnalysis class."""
    
    def test_trend_analysis_creation(self):
        """Test creating a trend analysis."""
        trend = TrendAnalysis(
            metric_name="transaction_amount",
            trend_direction="increasing",
            trend_strength=0.7,
            prediction_confidence=0.8,
            current_value=250.0,
            predicted_next_value=275.0,
            time_window_days=30,
            data_points=20
        )
        
        assert trend.metric_name == "transaction_amount"
        assert trend.trend_direction == "increasing"
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
        assert detector.statistical_models is not None
        assert detector.user_baselines == {}
    
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
        assert transaction.id == "tx_request_pattern_001"
        assert transaction.user_id == "user_request_pattern_123"
        assert transaction.amount == Decimal("500.00")
        assert transaction.merchant == "Unusual Store"
    
    def test_extract_transaction_invalid(self, pattern_detector):
        """Test extracting transaction from invalid request data."""
        invalid_data = {"invalid": "data"}
        
        transaction = pattern_detector._extract_transaction(invalid_data)
        
        # Should handle gracefully and return a transaction with default values
        assert transaction is not None
        assert transaction.id == ""
        assert transaction.amount == Decimal("0")
    
    def test_detect_amount_anomaly_high(self, pattern_detector, sample_transaction):
        """Test detection of high amount anomaly."""
        # Create baseline with low amounts
        baseline = {
            "amount_stats": {
                "mean": 50.0,
                "std": 10.0,
                "median": 50.0,
                "min": 30.0,
                "max": 80.0
            }
        }
        
        # Test with high amount transaction
        sample_transaction.amount = Decimal("200.00")  # Much higher than baseline
        
        anomaly = pattern_detector._detect_amount_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "amount_anomaly"
        assert anomaly.score > 0.5
        assert anomaly.confidence > 0.5
        assert "standard deviations" in anomaly.description
    
    def test_detect_amount_anomaly_normal(self, pattern_detector, sample_transaction):
        """Test detection with normal amount (no anomaly)."""
        # Create baseline with similar amounts
        baseline = {
            "amount_stats": {
                "mean": 250.0,
                "std": 50.0,
                "median": 250.0,
                "min": 150.0,
                "max": 350.0
            }
        }
        
        anomaly = pattern_detector._detect_amount_anomaly(sample_transaction, baseline)
        
        assert anomaly is None  # Should not detect anomaly for normal amount
    
    def test_detect_frequency_anomaly_high(self, pattern_detector, mock_memory_manager, sample_transaction):
        """Test detection of high frequency anomaly."""
        # Mock high frequency of transactions today
        recent_transactions = []
        today = datetime.now().date()
        
        for i in range(15):  # 15 transactions today
            tx = Transaction(
                id=f"tx_freq_{i}",
                user_id=sample_transaction.user_id,
                amount=Decimal("100.00"),
                currency="USD",
                merchant="Store",
                category="retail",
                location=sample_transaction.location,
                timestamp=datetime.now().replace(hour=i % 12),
                card_type="credit",
                device_info=sample_transaction.device_info,
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            recent_transactions.append(tx)
        
        mock_memory_manager.get_user_transaction_history.return_value = recent_transactions
        
        baseline = {
            "frequency_stats": {
                "mean_daily": 3.0,
                "std_daily": 1.0,
                "max_daily": 5
            }
        }
        
        anomaly = pattern_detector._detect_frequency_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "frequency_anomaly"
        assert anomaly.score > 0.5
    
    def test_detect_temporal_anomaly_late_night(self, pattern_detector, sample_transaction):
        """Test detection of late night temporal anomaly."""
        # Set transaction to late night
        sample_transaction.timestamp = sample_transaction.timestamp.replace(hour=3)
        
        baseline = {}  # Empty baseline
        
        anomaly = pattern_detector._detect_temporal_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "temporal_anomaly"
        assert "late night" in anomaly.description.lower()
        assert anomaly.score > 0.5
    
    def test_detect_merchant_anomaly_high_risk(self, pattern_detector, sample_transaction):
        """Test detection of high-risk merchant anomaly."""
        # Set high-risk merchant
        sample_transaction.merchant = "Bitcoin Casino Exchange"
        
        baseline = {}  # Empty baseline
        
        anomaly = pattern_detector._detect_merchant_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "merchant_anomaly"
        assert "high-risk" in anomaly.description.lower()
        assert anomaly.score > 0.7
    
    def test_detect_location_anomaly_new_country(self, pattern_detector, sample_transaction):
        """Test detection of new country location anomaly."""
        # Set transaction in new country
        sample_transaction.location.country = "FR"
        sample_transaction.location.city = "Paris"
        
        baseline = {
            "location_stats": {
                "common_countries": ["US"],
                "common_cities": ["New York", "Boston"]
            }
        }
        
        anomaly = pattern_detector._detect_location_anomaly(sample_transaction, baseline)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == "location_anomaly"
        assert "new country" in anomaly.description.lower()
        assert anomaly.score > 0.5
    
    def test_recognize_behavioral_patterns_escalating(self, pattern_detector, mock_memory_manager):
        """Test recognition of escalating spending behavioral pattern."""
        # Create escalating transaction history
        escalating_transactions = []
        base_time = datetime.now() - timedelta(days=10)
        
        for i in range(5):
            tx = Transaction(
                id=f"tx_escalate_{i}",
                user_id="user_escalate_123",
                amount=Decimal(f"{100 + i * 50}.00"),  # Escalating amounts
                currency="USD",
                merchant="Store",
                category="retail",
                location=Location(country="US", city="New York"),
                timestamp=base_time + timedelta(days=i * 2),
                card_type="credit",
                device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
                ip_address="192.168.1.1",
                session_id=f"session_{i}"
            )
            escalating_transactions.append(tx)
        
        mock_memory_manager.get_user_transaction_history.return_value = escalating_transactions
        
        # Create test transaction
        test_transaction = Transaction(
            id="tx_test_escalate",
            user_id="user_escalate_123",
            amount=Decimal("350.00"),
            currency="USD",
            merchant="Store",
            category="retail",
            location=Location(country="US", city="New York"),
            timestamp=datetime.now(),
            card_type="credit",
            device_info=DeviceInfo(device_id="device_001", device_type="mobile", os="iOS"),
            ip_address="192.168.1.1",
            session_id="session_test"
        )
        
        patterns = pattern_detector._recognize_behavioral_patterns(test_transaction)
        
        # Should detect escalating spending pattern
        escalating_patterns = [p for p in patterns if p.pattern_type == "escalating_spending"]
        assert len(escalating_patterns) > 0
        
        escalating_pattern = escalating_patterns[0]
        assert escalating_pattern.trend_direction == "increasing"
        assert escalating_pattern.strength > 0.5
    
    def test_analyze_amount_trend_increasing(self, pattern_detector):
        """Test analysis of increasing amount trend."""
        # Create transactions with increasing amounts
        transactions = []
        base_time = datetime.now() - timedelta(days=20)
        
        for i in range(10):
            tx = Transaction(
                id=f"tx_trend_{i}",
                user_id="user_trend_123",
                amount=Decimal(f"{100 + i * 20}.00"),  # Increasing trend
                currency="USD",
                merchant="Store",
                category="retail",
                location=Location(country="US", city="New York"),
                timestamp=base_time + timedelta(days=i * 2),
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
        assert trend.predicted_next_value > trend.current_value
    
    def test_calculate_pattern_similarity(self, pattern_detector, sample_transaction):
        """Test pattern similarity calculation."""
        # Create a mock fraud pattern
        mock_pattern = Mock()
        mock_pattern.pattern_type = "velocity_fraud"
        mock_pattern.pattern_id = "velocity_001"
        mock_pattern.description = "Rapid transactions"
        
        # Mock memory manager to return some recent transactions
        mock_recent_transactions = [sample_transaction] * 5  # 5 recent transactions
        pattern_detector.memory_manager.get_user_transaction_history.return_value = mock_recent_transactions
        
        similarity = pattern_detector._calculate_pattern_similarity(sample_transaction, mock_pattern)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be high due to multiple recent transactions
    
    def test_process_request_success(self, pattern_detector, mock_memory_manager, sample_request_data):
        """Test successful pattern detection request processing."""
        # Mock memory manager responses
        mock_memory_manager.get_user_transaction_history.return_value = []
        mock_memory_manager.get_all_fraud_patterns.return_value = []
        
        result = pattern_detector.execute_with_metrics(sample_request_data)
        
        assert result.success is True
        assert "pattern_detection" in result.result_data
        assert result.confidence_score >= 0
    
    def test_process_request_invalid_data(self, pattern_detector):
        """Test pattern detection with invalid request data."""
        invalid_request = {"invalid": "data"}
        
        result = pattern_detector.execute_with_metrics(invalid_request)
        
        assert result.success is False
        assert "Invalid transaction data" in result.error_message
    
    def test_calculate_user_baseline(self, pattern_detector, sample_user_transactions):
        """Test calculation of user baseline statistics."""
        # Mock memory manager to return sample transactions
        pattern_detector.memory_manager.get_user_transaction_history.return_value = sample_user_transactions
        
        baseline = pattern_detector._calculate_user_baseline("user_pattern_123")
        
        assert "amount_stats" in baseline
        assert "frequency_stats" in baseline
        assert "temporal_stats" in baseline
        assert "merchant_stats" in baseline
        assert "location_stats" in baseline
        
        # Check amount stats
        amount_stats = baseline["amount_stats"]
        assert "mean" in amount_stats
        assert "std" in amount_stats
        assert "median" in amount_stats
        
        # Check merchant stats
        merchant_stats = baseline["merchant_stats"]
        assert "frequent_merchants" in merchant_stats
        assert len(merchant_stats["frequent_merchants"]) > 0
    
    def test_get_user_baseline_caching(self, pattern_detector, sample_user_transactions):
        """Test that user baselines are cached properly."""
        user_id = "user_cache_test"
        
        # Mock memory manager
        pattern_detector.memory_manager.get_user_transaction_history.return_value = sample_user_transactions
        
        # First call should calculate baseline
        baseline1 = pattern_detector._get_user_baseline(user_id)
        assert user_id in pattern_detector.user_baselines
        
        # Second call should use cached baseline
        baseline2 = pattern_detector._get_user_baseline(user_id)
        assert baseline1 is baseline2  # Should be the same object (cached)
    
    def test_pattern_cache_management(self, pattern_detector):
        """Test pattern cache management functionality."""
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
    
    def test_overall_anomaly_score_calculation(self, pattern_detector):
        """Test calculation of overall anomaly score."""
        # Create test result with multiple anomalies
        result = PatternDetectionResult(transaction_id="tx_test")
        
        result.anomaly_scores = [
            AnomalyScore("amount_anomaly", 0.8, 0.9, "High amount"),
            AnomalyScore("frequency_anomaly", 0.6, 0.7, "High frequency"),
            AnomalyScore("temporal_anomaly", 0.4, 0.8, "Unusual time")
        ]
        
        overall_score = pattern_detector._calculate_overall_anomaly_score(result)
        
        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.5  # Should be high due to multiple anomalies
    
    def test_generate_pattern_recommendations(self, pattern_detector):
        """Test generation of pattern-based recommendations."""
        # Create test result with high anomaly score
        result = PatternDetectionResult(transaction_id="tx_test")
        result.overall_anomaly_score = 0.9
        
        result.anomaly_scores = [
            AnomalyScore("amount_anomaly", 0.8, 0.9, "High amount anomaly")
        ]
        
        result.behavioral_patterns = [
            BehavioralPattern(
                pattern_id="high_risk_001",
                pattern_type="escalating_spending",
                description="Escalating spending detected",
                strength=0.8,
                frequency=5,
                last_seen=datetime.now(),
                trend_direction="increasing",
                risk_level="high"
            )
        ]
        
        recommendations = pattern_detector._generate_pattern_recommendations(result)
        
        assert len(recommendations) > 0
        assert any("Decline" in rec for rec in recommendations)  # Should recommend decline for high anomaly
        assert any("High anomaly detected" in rec for rec in recommendations)


if __name__ == "__main__":
    pytest.main([__file__])