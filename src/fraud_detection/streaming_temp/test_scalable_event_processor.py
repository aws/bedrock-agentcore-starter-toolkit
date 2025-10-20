"""
Unit tests for Scalable Event Processing Architecture.
"""

import pytest
import time
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

from src.scalable_event_processor import (
    ScalableEventProcessor, EventBatch, ProcessingMetrics, ScalingDecision,
    ProcessingMode, ScalingStrategy, create_scalable_processor
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def scalable_processor(temp_dir):
    """Create scalable event processor for testing."""
    processor = ScalableEventProcessor(
        min_workers=1,
        max_workers=4,
        batch_size=5,
        buffer_size=50
    )
    
    # Use temp directory for storage
    processor.replay_storage_path = f"{temp_dir}/replay"
    processor.audit_log_path = f"{temp_dir}/audit"
    processor._initialize_storage()
    
    return processor


@pytest.fixture
def sample_events():
    """Create sample events for testing."""
    return [
        {
            "event_id": f"event_{i}",
            "type": "fraud_detected",
            "user_id": f"user_{i % 3}",
            "amount": 100.0 * (i + 1),
            "timestamp": datetime.now().isoformat()
        }
        for i in range(10)
    ]


class TestScalableEventProcessor:
    """Test cases for ScalableEventProcessor."""
    
    def test_processor_initialization(self, scalable_processor):
        """Test processor initialization."""
        assert scalable_processor.min_workers == 1
        assert scalable_processor.max_workers == 4
        assert scalable_processor.batch_size == 5
        assert scalable_processor.buffer_size == 50
        assert scalable_processor.is_running is False
        assert scalable_processor.processing_mode == ProcessingMode.HYBRID
    
    def test_add_processors(self, scalable_processor):
        """Test adding event and batch processors."""
        def event_processor(event):
            pass
        
        def batch_processor(events):
            pass
        
        scalable_processor.add_event_processor(event_processor)
        scalable_processor.add_batch_processor(batch_processor)
        
        assert len(scalable_processor.event_processors) == 1
        assert len(scalable_processor.batch_processors) == 1
        assert event_processor in scalable_processor.event_processors
        assert batch_processor in scalable_processor.batch_processors
    
    def test_submit_event(self, scalable_processor):
        """Test submitting single events."""
        event = {
            "event_id": "test_event",
            "type": "test",
            "data": {"key": "value"}
        }
        
        success = scalable_processor.submit_event(event)
        
        assert success is True
        assert scalable_processor.event_buffer.qsize() == 1
        
        # Check that metadata was added
        buffered_event = scalable_processor.event_buffer.get()
        assert "_submitted_at" in buffered_event
        assert "_event_id" in buffered_event
    
    def test_submit_events_batch(self, scalable_processor, sample_events):
        """Test submitting event batches."""
        success = scalable_processor.submit_events_batch(sample_events)
        
        assert success is True
        assert scalable_processor.batch_queue.qsize() == 1
        
        # Check batch contents
        batch = scalable_processor.batch_queue.get()
        assert isinstance(batch, EventBatch)
        assert len(batch.events) == len(sample_events)
        assert batch.batch_id is not None
    
    def test_get_metrics(self, scalable_processor):
        """Test getting processing metrics."""
        metrics = scalable_processor.get_metrics()
        
        assert isinstance(metrics, ProcessingMetrics)
        assert hasattr(metrics, 'events_processed')
        assert hasattr(metrics, 'events_per_second')
        assert hasattr(metrics, 'queue_depth')
        assert hasattr(metrics, 'active_workers')
    
    def test_get_status(self, scalable_processor):
        """Test getting processor status."""
        status = scalable_processor.get_status()
        
        assert "is_running" in status
        assert "processing_mode" in status
        assert "scaling_strategy" in status
        assert "workers" in status
        assert "queues" in status
        assert "metrics" in status
        assert "storage" in status
        
        assert status["processing_mode"] == ProcessingMode.HYBRID.value
        assert status["workers"]["min"] == 1
        assert status["workers"]["max"] == 4
    
    def test_start_stop_processor(self, scalable_processor):
        """Test starting and stopping the processor."""
        # Start processor
        scalable_processor.start()
        assert scalable_processor.is_running is True
        assert len(scalable_processor.processor_threads) > 0
        
        # Stop processor
        scalable_processor.stop()
        assert scalable_processor.is_running is False
    
    def test_event_batch_creation(self, scalable_processor):
        """Test event batch creation."""
        events = [{"event_id": f"event_{i}"} for i in range(3)]
        
        scalable_processor._create_event_batch(events)
        
        # Should create batch for batch processing
        assert scalable_processor.batch_queue.qsize() == 1
        
        # Should also queue individual events for real-time processing
        assert scalable_processor.processing_queue.qsize() == 3
    
    def test_scaling_decision_making(self, scalable_processor):
        """Test auto-scaling decision making."""
        # Test scale up decision
        scalable_processor.event_buffer.put("dummy_event")  # Add load
        
        decision = scalable_processor._make_scaling_decision()
        
        assert isinstance(decision, ScalingDecision)
        assert decision.action in ["scale_up", "scale_down", "no_change"]
        assert decision.target_workers >= scalable_processor.min_workers
        assert decision.target_workers <= scalable_processor.max_workers
    
    def test_worker_scaling(self, scalable_processor):
        """Test worker scaling functionality."""
        initial_workers = len(scalable_processor.workers)
        
        # Scale up
        scalable_processor._scale_workers(3)
        assert len(scalable_processor.workers) == 3
        
        # Scale down
        scalable_processor._scale_workers(1)
        assert len(scalable_processor.workers) == 1
    
    def test_checkpoint_creation(self, scalable_processor):
        """Test checkpoint creation for replay."""
        scalable_processor.metrics.events_processed = 100
        scalable_processor._create_checkpoint()
        
        # Check that checkpoint file was created
        checkpoint_files = list(Path(scalable_processor.replay_storage_path).glob("checkpoint_*.json"))
        assert len(checkpoint_files) > 0
        
        # Verify checkpoint content
        with open(checkpoint_files[0], 'r') as f:
            checkpoint_data = json.load(f)
        
        assert "timestamp" in checkpoint_data
        assert "events_processed" in checkpoint_data
        assert checkpoint_data["events_processed"] == 100
    
    def test_replay_batch_storage(self, scalable_processor):
        """Test storing batches for replay."""
        events = [{"event_id": f"event_{i}"} for i in range(3)]
        batch = EventBatch(
            batch_id="test_batch",
            events=events,
            created_at=datetime.now()
        )
        
        scalable_processor._store_replay_batch(batch)
        
        # Check that replay file was created
        replay_files = list(Path(scalable_processor.replay_storage_path).glob("events_*.json*"))
        assert len(replay_files) > 0
    
    def test_event_replay(self, scalable_processor):
        """Test event replay functionality."""
        # Create some test events and store them
        events = [{"event_id": f"replay_event_{i}"} for i in range(5)]
        batch = EventBatch(
            batch_id="replay_batch",
            events=events,
            created_at=datetime.now()
        )
        
        scalable_processor._store_replay_batch(batch)
        
        # Test replay
        start_time = datetime.now() - timedelta(minutes=1)
        end_time = datetime.now() + timedelta(minutes=1)
        
        replayed_count = scalable_processor.replay_events(start_time, end_time)
        
        assert replayed_count > 0
        assert scalable_processor.event_buffer.qsize() > 0
    
    def test_audit_logging(self, scalable_processor):
        """Test audit logging functionality."""
        scalable_processor._audit_log("test_action", "test_entity", {"key": "value"})
        
        # Check that audit log file was created
        audit_files = list(Path(scalable_processor.audit_log_path).glob("audit_*.log"))
        assert len(audit_files) > 0
        
        # Verify audit log content
        with open(audit_files[0], 'r') as f:
            log_lines = f.readlines()
        
        assert len(log_lines) > 0
        
        log_entry = json.loads(log_lines[0])
        assert log_entry["action"] == "test_action"
        assert log_entry["entity_id"] == "test_entity"
        assert "checksum" in log_entry
    
    def test_processing_with_handlers(self, scalable_processor):
        """Test event processing with registered handlers."""
        processed_events = []
        processed_batches = []
        
        def event_handler(event):
            processed_events.append(event)
        
        def batch_handler(events):
            processed_batches.append(events)
        
        scalable_processor.add_event_processor(event_handler)
        scalable_processor.add_batch_processor(batch_handler)
        
        # Process single event
        test_event = {"event_id": "test_single", "data": "test"}
        scalable_processor._process_single_event(test_event, "test_worker")
        
        assert len(processed_events) == 1
        assert processed_events[0]["event_id"] == "test_single"
        
        # Process batch
        test_batch = EventBatch(
            batch_id="test_batch",
            events=[{"event_id": "batch_event_1"}, {"event_id": "batch_event_2"}],
            created_at=datetime.now()
        )
        
        scalable_processor._process_batch(test_batch)
        
        assert len(processed_batches) == 1
        assert len(processed_batches[0]) == 2
    
    def test_metrics_monitoring(self, scalable_processor):
        """Test metrics monitoring and updates."""
        initial_count = scalable_processor.metrics.events_processed
        
        # Simulate processing some events
        scalable_processor.metrics.events_processed += 10
        
        # Check metrics update
        metrics = scalable_processor.get_metrics()
        assert metrics.events_processed == initial_count + 10
    
    def test_error_handling(self, scalable_processor):
        """Test error handling in processing."""
        def failing_processor(event):
            raise ValueError("Test error")
        
        scalable_processor.add_event_processor(failing_processor)
        
        # Should not crash when processor fails
        test_event = {"event_id": "error_test"}
        scalable_processor._process_single_event(test_event, "test_worker")
        
        # Processor should continue working
        assert scalable_processor.is_running is False  # Not started yet


class TestEventBatch:
    """Test cases for EventBatch class."""
    
    def test_event_batch_creation(self):
        """Test event batch creation."""
        events = [{"event_id": f"event_{i}"} for i in range(3)]
        batch = EventBatch(
            batch_id="test_batch",
            events=events,
            created_at=datetime.now()
        )
        
        assert batch.batch_id == "test_batch"
        assert len(batch.events) == 3
        assert batch.priority == 100  # Default priority
        assert isinstance(batch.created_at, datetime)
    
    def test_batch_priority_ordering(self):
        """Test batch priority ordering for queue."""
        high_priority_batch = EventBatch(
            batch_id="high",
            events=[],
            created_at=datetime.now(),
            priority=10
        )
        
        low_priority_batch = EventBatch(
            batch_id="low",
            events=[],
            created_at=datetime.now(),
            priority=100
        )
        
        # High priority (lower number) should be "less than" low priority
        assert high_priority_batch < low_priority_batch


class TestProcessingMetrics:
    """Test cases for ProcessingMetrics class."""
    
    def test_metrics_creation(self):
        """Test processing metrics creation."""
        metrics = ProcessingMetrics()
        
        assert metrics.events_processed == 0
        assert metrics.events_per_second == 0.0
        assert metrics.average_latency_ms == 0.0
        assert metrics.error_rate == 0.0
        assert isinstance(metrics.throughput_trend, list)
        assert isinstance(metrics.last_updated, datetime)


class TestScalingDecision:
    """Test cases for ScalingDecision class."""
    
    def test_scaling_decision_creation(self):
        """Test scaling decision creation."""
        decision = ScalingDecision(
            action="scale_up",
            target_workers=5,
            reason="High load detected",
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        assert decision.action == "scale_up"
        assert decision.target_workers == 5
        assert decision.reason == "High load detected"
        assert decision.confidence == 0.8
        assert isinstance(decision.timestamp, datetime)


class TestCreateScalableProcessor:
    """Test cases for create_scalable_processor function."""
    
    def test_create_processor_with_defaults(self):
        """Test creating processor with default settings."""
        processor = create_scalable_processor()
        
        assert processor.min_workers == 2
        assert processor.max_workers == 20
        assert processor.batch_size == 100
        assert processor.enable_replay is True
        assert processor.enable_audit_logging is True
    
    def test_create_processor_with_custom_settings(self):
        """Test creating processor with custom settings."""
        processor = create_scalable_processor(
            min_workers=1,
            max_workers=10,
            batch_size=50,
            enable_replay=False,
            enable_audit=False
        )
        
        assert processor.min_workers == 1
        assert processor.max_workers == 10
        assert processor.batch_size == 50
        assert processor.enable_replay is False
        assert processor.enable_audit_logging is False


if __name__ == "__main__":
    pytest.main([__file__])