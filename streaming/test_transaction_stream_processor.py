"""
Unit tests for Real-Time Transaction Stream Processing.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from streaming.transaction_stream_processor import (
    TransactionStreamProcessor, StreamingFraudDetector, Transaction, 
    ProcessingResult, ProcessingPriority, StreamStatus
)


@pytest.fixture
def sample_transaction():
    """Create sample transaction for testing."""
    return Transaction(
        transaction_id="txn_123",
        user_id="user_456",
        amount=150.0,
        currency="USD",
        merchant="Test Store",
        category="retail",
        timestamp=datetime.now(),
        location={"country": "US", "city": "New York"},
        device_info={"type": "mobile", "id": "device_789"}
    )


@pytest.fixture
def fraud_detector():
    """Create fraud detector for testing."""
    return StreamingFraudDetector()


@pytest.fixture
def stream_processor():
    """Create stream processor for testing."""
    return TransactionStreamProcessor(
        max_workers=2,
        queue_size=100,
        batch_size=10
    )


class TestTransaction:
    """Test cases for Transaction class."""
    
    def test_transaction_creation(self, sample_transaction):
        """Test transaction creation and properties."""
        assert sample_transaction.transaction_id == "txn_123"
        assert sample_transaction.user_id == "user_456"
        assert sample_transaction.amount == 150.0
        assert sample_transaction.currency == "USD"
    
    def test_transaction_serialization(self, sample_transaction):
        """Test transaction serialization and deserialization."""
        # Serialize to dict
        transaction_dict = sample_transaction.to_dict()
        
        assert transaction_dict["transaction_id"] == "txn_123"
        assert transaction_dict["amount"] == 150.0
        assert isinstance(transaction_dict["timestamp"], str)
        
        # Deserialize from dict
        restored_transaction = Transaction.from_dict(transaction_dict)
        
        assert restored_transaction.transaction_id == sample_transaction.transaction_id
        assert restored_transaction.amount == sample_transaction.amount
        assert restored_transaction.currency == sample_transaction.currency


class TestStreamingFraudDetector:
    """Test cases for StreamingFraudDetector."""
    
    def test_fraud_detector_initialization(self, fraud_detector):
        """Test fraud detector initialization."""
        assert fraud_detector.processing_stats["total_processed"] == 0
        assert fraud_detector.processing_stats["fraud_detected"] == 0
    
    def test_detect_fraud_low_risk(self, fraud_detector):
        """Test fraud detection for low-risk transaction."""
        transaction = Transaction(
            transaction_id="low_risk_txn",
            user_id="user_123",
            amount=50.0,  # Low amount
            currency="USD",
            merchant="Grocery Store",
            category="grocery",  # Low-risk category
            timestamp=datetime.now().replace(hour=14),  # Normal time
            location={"country": "US", "city": "Boston"},
            device_info={"type": "card"}
        )
        
        result = fraud_detector.detect_fraud(transaction)
        
        assert result.transaction_id == "low_risk_txn"
        assert result.decision == "APPROVE"
        assert result.risk_score < 0.4
        assert result.confidence_score > 0.7
    
    def test_detect_fraud_high_risk(self, fraud_detector):
        """Test fraud detection for high-risk transaction."""
        transaction = Transaction(
            transaction_id="high_risk_txn",
            user_id="user_456",
            amount=8000.0,  # High amount
            currency="USD",
            merchant="Crypto Exchange",
            category="crypto",  # High-risk category
            timestamp=datetime.now().replace(hour=3),  # Unusual time
            location={"country": "RU", "city": "Moscow"},  # International
            device_info={"type": "web"}
        )
        
        result = fraud_detector.detect_fraud(transaction)
        
        assert result.transaction_id == "high_risk_txn"
        assert result.decision in ["DECLINE", "FLAG"]
        assert result.risk_score > 0.6
        assert len(result.fraud_indicators) > 0
        assert "high_amount" in result.fraud_indicators
        assert "high_risk_category" in result.fraud_indicators
    
    def test_fraud_detector_stats(self, fraud_detector, sample_transaction):
        """Test fraud detector statistics tracking."""
        # Process a transaction
        result = fraud_detector.detect_fraud(sample_transaction)
        
        stats = fraud_detector.get_stats()
        assert stats["total_processed"] == 1
        assert "average_processing_time_ms" in stats
        assert stats["average_processing_time_ms"] > 0


class TestTransactionStreamProcessor:
    """Test cases for TransactionStreamProcessor."""
    
    def test_processor_initialization(self, stream_processor):
        """Test stream processor initialization."""
        assert stream_processor.status == StreamStatus.STOPPED
        assert stream_processor.max_workers == 2
        assert stream_processor.queue_size == 100
        assert len(stream_processor.priority_queues) == 4
    
    def test_set_fraud_detector(self, stream_processor, fraud_detector):
        """Test setting fraud detector."""
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        assert stream_processor.fraud_detector is not None
    
    def test_priority_determination(self, stream_processor):
        """Test transaction priority determination."""
        # High-value transaction
        high_value_txn = Transaction(
            transaction_id="high_value",
            user_id="user_1",
            amount=15000.0,
            currency="USD",
            merchant="Luxury Store",
            category="retail",
            timestamp=datetime.now(),
            location={"country": "US"},
            device_info={}
        )
        
        priority = stream_processor._determine_priority(high_value_txn)
        assert priority == ProcessingPriority.CRITICAL
        
        # International transaction
        intl_txn = Transaction(
            transaction_id="intl",
            user_id="user_2",
            amount=500.0,
            currency="EUR",
            merchant="European Store",
            category="retail",
            timestamp=datetime.now(),
            location={"country": "DE"},
            device_info={}
        )
        
        priority = stream_processor._determine_priority(intl_txn)
        assert priority == ProcessingPriority.HIGH
        
        # Normal transaction
        normal_txn = Transaction(
            transaction_id="normal",
            user_id="user_3",
            amount=100.0,
            currency="USD",
            merchant="Coffee Shop",
            category="food",
            timestamp=datetime.now(),
            location={"country": "US"},
            device_info={}
        )
        
        priority = stream_processor._determine_priority(normal_txn)
        assert priority == ProcessingPriority.NORMAL
    
    def test_process_transaction_not_running(self, stream_processor, sample_transaction):
        """Test processing transaction when processor is not running."""
        success = stream_processor.process_transaction(sample_transaction)
        assert success is False
    
    def test_start_stop_processor(self, stream_processor, fraud_detector):
        """Test starting and stopping the processor."""
        # Set fraud detector
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        
        # Start processor
        stream_processor.start()
        assert stream_processor.status == StreamStatus.RUNNING
        assert len(stream_processor.workers) >= stream_processor.min_workers
        
        # Stop processor
        stream_processor.stop()
        assert stream_processor.status == StreamStatus.STOPPED
    
    def test_process_transaction_running(self, stream_processor, fraud_detector, sample_transaction):
        """Test processing transaction when processor is running."""
        # Set fraud detector and start
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        stream_processor.start()
        
        try:
            # Process transaction
            success = stream_processor.process_transaction(sample_transaction)
            assert success is True
            
            # Give some time for processing
            time.sleep(0.1)
            
            # Check metrics
            metrics = stream_processor.get_metrics()
            assert metrics.queue_depth >= 0
            assert metrics.active_workers > 0
            
        finally:
            stream_processor.stop()
    
    def test_process_batch(self, stream_processor, fraud_detector):
        """Test batch processing."""
        # Create batch of transactions
        transactions = []
        for i in range(5):
            txn = Transaction(
                transaction_id=f"batch_txn_{i}",
                user_id=f"user_{i}",
                amount=100.0 + i * 50,
                currency="USD",
                merchant="Test Store",
                category="retail",
                timestamp=datetime.now(),
                location={"country": "US"},
                device_info={}
            )
            transactions.append(txn)
        
        # Set fraud detector and start
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        stream_processor.start()
        
        try:
            # Process batch
            results = stream_processor.process_batch(transactions)
            assert len(results) == 5
            assert all(results)  # All should succeed
            
        finally:
            stream_processor.stop()
    
    def test_get_status(self, stream_processor, fraud_detector):
        """Test getting processor status."""
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        
        status = stream_processor.get_status()
        assert "status" in status
        assert "metrics" in status
        assert "configuration" in status
        assert "queue_status" in status
        
        assert status["status"] == "stopped"
        assert status["configuration"]["max_workers"] == 2
    
    def test_result_handler(self, stream_processor, fraud_detector, sample_transaction):
        """Test result handler functionality."""
        results_received = []
        
        def result_handler(result: ProcessingResult):
            results_received.append(result)
        
        # Add result handler
        stream_processor.add_result_handler(result_handler)
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        stream_processor.start()
        
        try:
            # Process transaction
            stream_processor.process_transaction(sample_transaction)
            
            # Wait for processing
            time.sleep(0.2)
            
            # Check that result was handled
            assert len(results_received) > 0
            assert results_received[0].transaction_id == sample_transaction.transaction_id
            
        finally:
            stream_processor.stop()
    
    def test_error_handler(self, stream_processor, sample_transaction):
        """Test error handler functionality."""
        errors_received = []
        
        def error_handler(error: Exception, transaction: Transaction):
            errors_received.append((error, transaction))
        
        def failing_detector(transaction: Transaction) -> ProcessingResult:
            raise ValueError("Test error")
        
        # Add error handler and failing detector
        stream_processor.add_error_handler(error_handler)
        stream_processor.set_fraud_detector(failing_detector)
        stream_processor.start()
        
        try:
            # Process transaction (should fail)
            stream_processor.process_transaction(sample_transaction)
            
            # Wait for processing
            time.sleep(0.2)
            
            # Check that error was handled
            assert len(errors_received) > 0
            assert errors_received[0][1].transaction_id == sample_transaction.transaction_id
            
        finally:
            stream_processor.stop()
    
    def test_metrics_update(self, stream_processor, fraud_detector, sample_transaction):
        """Test metrics updating."""
        stream_processor.set_fraud_detector(fraud_detector.detect_fraud)
        stream_processor.start()
        
        try:
            # Process some transactions
            for i in range(3):
                txn = Transaction(
                    transaction_id=f"metrics_txn_{i}",
                    user_id=f"user_{i}",
                    amount=100.0,
                    currency="USD",
                    merchant="Test Store",
                    category="retail",
                    timestamp=datetime.now(),
                    location={"country": "US"},
                    device_info={}
                )
                stream_processor.process_transaction(txn)
            
            # Wait for processing
            time.sleep(0.3)
            
            # Check metrics
            metrics = stream_processor.get_metrics()
            assert metrics.transactions_processed >= 0
            assert metrics.active_workers > 0
            
        finally:
            stream_processor.stop()


class TestProcessingResult:
    """Test cases for ProcessingResult."""
    
    def test_processing_result_creation(self):
        """Test processing result creation."""
        result = ProcessingResult(
            transaction_id="test_txn",
            decision="APPROVE",
            confidence_score=0.85,
            risk_score=0.25,
            processing_time_ms=150.0,
            fraud_indicators=["low_risk"],
            recommendations=["Standard processing"],
            timestamp=datetime.now()
        )
        
        assert result.transaction_id == "test_txn"
        assert result.decision == "APPROVE"
        assert result.confidence_score == 0.85
        assert result.risk_score == 0.25
        assert len(result.fraud_indicators) == 1
        assert len(result.recommendations) == 1


if __name__ == "__main__":
    pytest.main([__file__])