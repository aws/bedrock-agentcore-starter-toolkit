"""
Scalable Event Processing Architecture

Provides auto-scaling, event buffering, batch processing, event replay,
and comprehensive audit logging for high-volume event processing.
"""

import logging
import asyncio
import json
import time
import gzip
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue, PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import uuid
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Event processing modes."""
    REAL_TIME = "real_time"
    BATCH = "batch"
    HYBRID = "hybrid"


class ScalingStrategy(Enum):
    """Auto-scaling strategies."""
    QUEUE_BASED = "queue_based"
    THROUGHPUT_BASED = "throughput_based"
    LATENCY_BASED = "latency_based"
    ADAPTIVE = "adaptive"


class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class EventBatch:
    """Batch of events for processing."""
    batch_id: str
    events: List[Dict[str, Any]]
    created_at: datetime
    priority: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority < other.priority


@dataclass
class ProcessingMetrics:
    """Metrics for event processing performance."""
    events_processed: int = 0
    events_per_second: float = 0.0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0
    queue_depth: int = 0
    active_workers: int = 0
    batch_size_avg: float = 0.0
    throughput_trend: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ScalingDecision:
    """Auto-scaling decision."""
    action: str  # "scale_up", "scale_down", "no_change"
    target_workers: int
    reason: str
    confidence: float
    timestamp: datetime


class ScalableEventProcessor:
    """
    Scalable event processing architecture with auto-scaling,
    buffering, batch processing, and event replay capabilities.
    """
    
    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 20,
        batch_size: int = 100,
        buffer_size: int = 10000,
        processing_mode: ProcessingMode = ProcessingMode.HYBRID
    ):
        """Initialize scalable event processor."""
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.buffer_size = buffer_size
        self.processing_mode = processing_mode
        
        # Event processing
        self.event_buffer = Queue(maxsize=buffer_size)
        self.batch_queue = PriorityQueue()
        self.processing_queue = Queue()
        
        # Worker management
        self.workers = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=4)
        
        # Auto-scaling
        self.scaling_strategy = ScalingStrategy.ADAPTIVE
        self.scale_up_threshold = 0.8
        self.scale_down_threshold = 0.3
        self.scaling_cooldown = 60  # seconds
        self.last_scaling_action = datetime.now()
        
        # Event replay and recovery
        self.enable_replay = True
        self.replay_storage_path = "event_replay"
        self.checkpoint_interval = 1000  # events
        self.last_checkpoint = 0
        
        # Audit logging
        self.enable_audit_logging = True
        self.audit_log_path = "audit_logs"
        self.log_rotation_size = 100 * 1024 * 1024  # 100MB
        self.log_compression = True
        
        # Metrics and monitoring
        self.metrics = ProcessingMetrics()
        self.performance_history = []
        
        # State management
        self.is_running = False
        self.processor_threads = []
        
        # Event handlers
        self.event_processors: List[Callable] = []
        self.batch_processors: List[Callable] = []
        
        # Initialize storage directories
        self._initialize_storage()
        
        logger.info("Scalable event processor initialized")    
 
    def _initialize_storage(self) -> None:
        """Initialize storage directories for replay and audit logs."""
        if self.enable_replay:
            Path(self.replay_storage_path).mkdir(parents=True, exist_ok=True)
        
        if self.enable_audit_logging:
            Path(self.audit_log_path).mkdir(parents=True, exist_ok=True)
    
    def add_event_processor(self, processor: Callable) -> None:
        """Add event processor for real-time processing."""
        self.event_processors.append(processor)
        logger.debug("Added event processor")
    
    def add_batch_processor(self, processor: Callable) -> None:
        """Add batch processor for batch processing."""
        self.batch_processors.append(processor)
        logger.debug("Added batch processor")
    
    def start(self) -> None:
        """Start the scalable event processor."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start core processing threads
        self.processor_threads = [
            threading.Thread(target=self._event_buffer_manager, daemon=True),
            threading.Thread(target=self._batch_processor, daemon=True),
            threading.Thread(target=self._metrics_monitor, daemon=True),
            threading.Thread(target=self._auto_scaler, daemon=True),
            threading.Thread(target=self._checkpoint_manager, daemon=True)
        ]
        
        for thread in self.processor_threads:
            thread.start()
        
        # Start initial workers
        self._scale_workers(self.min_workers)
        
        logger.info(f"Scalable event processor started with {self.min_workers} workers")
    
    def stop(self) -> None:
        """Stop the scalable event processor."""
        self.is_running = False
        
        # Wait for threads to finish
        for thread in self.processor_threads:
            thread.join(timeout=5)
        
        # Shutdown executors
        self.executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        # Final checkpoint
        if self.enable_replay:
            self._create_checkpoint()
        
        logger.info("Scalable event processor stopped")
    
    def submit_event(self, event: Dict[str, Any]) -> bool:
        """Submit event for processing."""
        try:
            # Add processing metadata
            event["_submitted_at"] = datetime.now().isoformat()
            event["_event_id"] = event.get("event_id", str(uuid.uuid4()))
            
            # Add to buffer
            self.event_buffer.put_nowait(event)
            
            # Audit log
            if self.enable_audit_logging:
                self._audit_log("event_submitted", event["_event_id"], event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit event: {str(e)}")
            return False
    
    def submit_events_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Submit batch of events for processing."""
        try:
            batch = EventBatch(
                batch_id=str(uuid.uuid4()),
                events=events,
                created_at=datetime.now()
            )
            
            self.batch_queue.put_nowait(batch)
            
            # Audit log
            if self.enable_audit_logging:
                self._audit_log("batch_submitted", batch.batch_id, {
                    "event_count": len(events),
                    "batch_id": batch.batch_id
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit event batch: {str(e)}")
            return False
    
    def get_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics."""
        self.metrics.queue_depth = self.event_buffer.qsize()
        self.metrics.active_workers = len(self.workers)
        self.metrics.last_updated = datetime.now()
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed processor status."""
        metrics = self.get_metrics()
        
        return {
            "is_running": self.is_running,
            "processing_mode": self.processing_mode.value,
            "scaling_strategy": self.scaling_strategy.value,
            "workers": {
                "active": metrics.active_workers,
                "min": self.min_workers,
                "max": self.max_workers
            },
            "queues": {
                "event_buffer": self.event_buffer.qsize(),
                "batch_queue": self.batch_queue.qsize(),
                "processing_queue": self.processing_queue.qsize()
            },
            "metrics": {
                "events_processed": metrics.events_processed,
                "events_per_second": metrics.events_per_second,
                "average_latency_ms": metrics.average_latency_ms,
                "error_rate": metrics.error_rate
            },
            "storage": {
                "replay_enabled": self.enable_replay,
                "audit_logging_enabled": self.enable_audit_logging,
                "last_checkpoint": self.last_checkpoint
            }
        }
    
    def replay_events(self, start_time: datetime, end_time: datetime = None) -> int:
        """Replay events from storage within time range."""
        if not self.enable_replay:
            logger.warning("Event replay is disabled")
            return 0
        
        end_time = end_time or datetime.now()
        replayed_count = 0
        
        try:
            # Find replay files in time range
            replay_files = self._find_replay_files(start_time, end_time)
            
            for file_path in replay_files:
                events = self._load_replay_file(file_path)
                
                for event in events:
                    event_time = datetime.fromisoformat(event.get("_submitted_at", ""))
                    
                    if start_time <= event_time <= end_time:
                        # Mark as replay event
                        event["_is_replay"] = True
                        event["_replayed_at"] = datetime.now().isoformat()
                        
                        self.submit_event(event)
                        replayed_count += 1
            
            logger.info(f"Replayed {replayed_count} events from {start_time} to {end_time}")
            return replayed_count
            
        except Exception as e:
            logger.error(f"Error during event replay: {str(e)}")
            return 0
    
    def _event_buffer_manager(self) -> None:
        """Manage event buffer and create batches."""
        batch_events = []
        last_batch_time = time.time()
        
        while self.is_running:
            try:
                # Get events from buffer
                try:
                    event = self.event_buffer.get(timeout=1.0)
                    batch_events.append(event)
                except Empty:
                    pass
                
                current_time = time.time()
                
                # Create batch if conditions are met
                should_create_batch = (
                    len(batch_events) >= self.batch_size or
                    (batch_events and (current_time - last_batch_time) > 5.0)  # 5 second timeout
                )
                
                if should_create_batch and batch_events:
                    self._create_event_batch(batch_events)
                    batch_events = []
                    last_batch_time = current_time
                
            except Exception as e:
                logger.error(f"Error in event buffer manager: {str(e)}")
                time.sleep(1)
    
    def _create_event_batch(self, events: List[Dict[str, Any]]) -> None:
        """Create and queue event batch."""
        batch = EventBatch(
            batch_id=str(uuid.uuid4()),
            events=events,
            created_at=datetime.now()
        )
        
        # Store for replay if enabled
        if self.enable_replay:
            self._store_replay_batch(batch)
        
        # Queue for processing
        if self.processing_mode in [ProcessingMode.BATCH, ProcessingMode.HYBRID]:
            self.batch_queue.put_nowait(batch)
        
        # Process individually for real-time mode
        if self.processing_mode in [ProcessingMode.REAL_TIME, ProcessingMode.HYBRID]:
            for event in events:
                self.processing_queue.put_nowait(event)
    
    def _batch_processor(self) -> None:
        """Process event batches."""
        while self.is_running:
            try:
                batch = self.batch_queue.get(timeout=1.0)
                self._process_batch(batch)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in batch processor: {str(e)}")
                time.sleep(1)
    
    def _process_batch(self, batch: EventBatch) -> None:
        """Process a single event batch."""
        start_time = time.time()
        
        try:
            # Process with registered batch processors
            for processor in self.batch_processors:
                try:
                    processor(batch.events)
                except Exception as e:
                    logger.error(f"Error in batch processor: {str(e)}")
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics.events_processed += len(batch.events)
            
            # Audit log
            if self.enable_audit_logging:
                self._audit_log("batch_processed", batch.batch_id, {
                    "event_count": len(batch.events),
                    "processing_time_ms": processing_time
                })
            
        except Exception as e:
            logger.error(f"Error processing batch {batch.batch_id}: {str(e)}")
    
    def _worker_loop(self, worker_id: str) -> None:
        """Individual worker processing loop."""
        while self.is_running:
            try:
                event = self.processing_queue.get(timeout=1.0)
                self._process_single_event(event, worker_id)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {str(e)}")
                time.sleep(1)
    
    def _process_single_event(self, event: Dict[str, Any], worker_id: str) -> None:
        """Process a single event."""
        start_time = time.time()
        
        try:
            # Process with registered event processors
            for processor in self.event_processors:
                try:
                    processor(event)
                except Exception as e:
                    logger.error(f"Error in event processor: {str(e)}")
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics.events_processed += 1
            
            # Audit log
            if self.enable_audit_logging:
                self._audit_log("event_processed", event.get("_event_id", "unknown"), {
                    "worker_id": worker_id,
                    "processing_time_ms": processing_time
                })
            
        except Exception as e:
            logger.error(f"Error processing event {event.get('_event_id', 'unknown')}: {str(e)}")
    
    def _metrics_monitor(self) -> None:
        """Monitor and update performance metrics."""
        last_count = 0
        last_time = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                current_count = self.metrics.events_processed
                
                # Calculate throughput
                time_diff = current_time - last_time
                if time_diff >= 10.0:  # Update every 10 seconds
                    count_diff = current_count - last_count
                    self.metrics.events_per_second = count_diff / time_diff
                    
                    # Update trend
                    self.metrics.throughput_trend.append(self.metrics.events_per_second)
                    if len(self.metrics.throughput_trend) > 60:  # Keep last 10 minutes
                        self.metrics.throughput_trend = self.metrics.throughput_trend[-60:]
                    
                    last_count = current_count
                    last_time = current_time
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in metrics monitor: {str(e)}")
                time.sleep(10)
    
    def _auto_scaler(self) -> None:
        """Auto-scaling based on load and performance."""
        while self.is_running:
            try:
                # Check if cooldown period has passed
                if (datetime.now() - self.last_scaling_action).total_seconds() < self.scaling_cooldown:
                    time.sleep(10)
                    continue
                
                decision = self._make_scaling_decision()
                
                if decision.action != "no_change":
                    self._execute_scaling_decision(decision)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in auto-scaler: {str(e)}")
                time.sleep(60)
    
    def _make_scaling_decision(self) -> ScalingDecision:
        """Make auto-scaling decision based on current metrics."""
        current_workers = len(self.workers)
        queue_utilization = self.event_buffer.qsize() / self.buffer_size
        
        # Queue-based scaling
        if queue_utilization > self.scale_up_threshold and current_workers < self.max_workers:
            return ScalingDecision(
                action="scale_up",
                target_workers=min(current_workers + 2, self.max_workers),
                reason=f"High queue utilization: {queue_utilization:.2f}",
                confidence=0.8,
                timestamp=datetime.now()
            )
        
        elif queue_utilization < self.scale_down_threshold and current_workers > self.min_workers:
            return ScalingDecision(
                action="scale_down",
                target_workers=max(current_workers - 1, self.min_workers),
                reason=f"Low queue utilization: {queue_utilization:.2f}",
                confidence=0.7,
                timestamp=datetime.now()
            )
        
        return ScalingDecision(
            action="no_change",
            target_workers=current_workers,
            reason="Metrics within acceptable range",
            confidence=0.9,
            timestamp=datetime.now()
        )
    
    def _execute_scaling_decision(self, decision: ScalingDecision) -> None:
        """Execute auto-scaling decision."""
        current_workers = len(self.workers)
        
        if decision.action == "scale_up":
            workers_to_add = decision.target_workers - current_workers
            self._scale_workers(decision.target_workers)
            logger.info(f"Scaled up: added {workers_to_add} workers ({decision.reason})")
        
        elif decision.action == "scale_down":
            workers_to_remove = current_workers - decision.target_workers
            self._scale_workers(decision.target_workers)
            logger.info(f"Scaled down: removed {workers_to_remove} workers ({decision.reason})")
        
        self.last_scaling_action = datetime.now()
    
    def _scale_workers(self, target_count: int) -> None:
        """Scale workers to target count."""
        current_count = len(self.workers)
        
        if target_count > current_count:
            # Add workers
            for i in range(target_count - current_count):
                worker_id = f"worker_{len(self.workers)}"
                future = self.executor.submit(self._worker_loop, worker_id)
                self.workers.append({"id": worker_id, "future": future})
        
        elif target_count < current_count:
            # Remove workers (they will finish current work and exit)
            workers_to_remove = current_count - target_count
            self.workers = self.workers[:-workers_to_remove]
    
    def _checkpoint_manager(self) -> None:
        """Manage checkpoints for event replay."""
        while self.is_running:
            try:
                if (self.metrics.events_processed - self.last_checkpoint) >= self.checkpoint_interval:
                    self._create_checkpoint()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in checkpoint manager: {str(e)}")
                time.sleep(60)
    
    def _create_checkpoint(self) -> None:
        """Create checkpoint for event replay."""
        if not self.enable_replay:
            return
        
        try:
            checkpoint_data = {
                "timestamp": datetime.now().isoformat(),
                "events_processed": self.metrics.events_processed,
                "last_event_id": getattr(self, '_last_event_id', None),
                "metrics": {
                    "events_per_second": self.metrics.events_per_second,
                    "average_latency_ms": self.metrics.average_latency_ms,
                    "error_rate": self.metrics.error_rate
                }
            }
            
            checkpoint_file = os.path.join(
                self.replay_storage_path,
                f"checkpoint_{int(time.time())}.json"
            )
            
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f)
            
            self.last_checkpoint = self.metrics.events_processed
            logger.debug(f"Created checkpoint: {checkpoint_file}")
            
        except Exception as e:
            logger.error(f"Error creating checkpoint: {str(e)}")
    
    def _store_replay_batch(self, batch: EventBatch) -> None:
        """Store event batch for replay capability."""
        if not self.enable_replay:
            return
        
        try:
            # Create timestamped filename
            timestamp = batch.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"events_{timestamp}_{batch.batch_id}.json"
            
            if self.log_compression:
                filename += ".gz"
            
            file_path = os.path.join(self.replay_storage_path, filename)
            
            # Prepare data
            replay_data = {
                "batch_id": batch.batch_id,
                "created_at": batch.created_at.isoformat(),
                "event_count": len(batch.events),
                "events": batch.events
            }
            
            # Write file
            if self.log_compression:
                with gzip.open(file_path, 'wt') as f:
                    json.dump(replay_data, f)
            else:
                with open(file_path, 'w') as f:
                    json.dump(replay_data, f)
            
        except Exception as e:
            logger.error(f"Error storing replay batch: {str(e)}")
    
    def _find_replay_files(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Find replay files within time range."""
        replay_files = []
        
        try:
            for filename in os.listdir(self.replay_storage_path):
                if filename.startswith("events_"):
                    file_path = os.path.join(self.replay_storage_path, filename)
                    
                    # Extract timestamp from filename
                    parts = filename.split("_")
                    if len(parts) >= 3:
                        timestamp_str = f"{parts[1]}_{parts[2]}"
                        try:
                            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            if start_time <= file_time <= end_time:
                                replay_files.append(file_path)
                        except ValueError:
                            continue
            
            return sorted(replay_files)
            
        except Exception as e:
            logger.error(f"Error finding replay files: {str(e)}")
            return []
    
    def _load_replay_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load events from replay file."""
        try:
            if file_path.endswith('.gz'):
                with gzip.open(file_path, 'rt') as f:
                    data = json.load(f)
            else:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            
            return data.get("events", [])
            
        except Exception as e:
            logger.error(f"Error loading replay file {file_path}: {str(e)}")
            return []
    
    def _audit_log(self, action: str, entity_id: str, details: Dict[str, Any]) -> None:
        """Write audit log entry."""
        if not self.enable_audit_logging:
            return
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "entity_id": entity_id,
                "details": details,
                "checksum": self._calculate_checksum(f"{action}:{entity_id}:{json.dumps(details, sort_keys=True)}")
            }
            
            # Determine log file
            log_filename = f"audit_{datetime.now().strftime('%Y%m%d')}.log"
            log_path = os.path.join(self.audit_log_path, log_filename)
            
            # Write log entry
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Check for log rotation
            self._check_log_rotation(log_path)
            
        except Exception as e:
            logger.error(f"Error writing audit log: {str(e)}")
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate checksum for audit trail integrity."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _check_log_rotation(self, log_path: str) -> None:
        """Check if log rotation is needed."""
        try:
            if os.path.getsize(log_path) > self.log_rotation_size:
                # Rotate log
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_path = f"{log_path}.{timestamp}"
                
                if self.log_compression:
                    rotated_path += ".gz"
                    
                    with open(log_path, 'rb') as f_in:
                        with gzip.open(rotated_path, 'wb') as f_out:
                            f_out.writelines(f_in)
                else:
                    os.rename(log_path, rotated_path)
                
                # Create new log file
                open(log_path, 'w').close()
                
                logger.info(f"Rotated audit log: {rotated_path}")
                
        except Exception as e:
            logger.error(f"Error rotating log: {str(e)}")


def create_scalable_processor(
    min_workers: int = 2,
    max_workers: int = 20,
    batch_size: int = 100,
    enable_replay: bool = True,
    enable_audit: bool = True
) -> ScalableEventProcessor:
    """
    Create a scalable event processor with common configuration.
    
    Args:
        min_workers: Minimum number of workers
        max_workers: Maximum number of workers
        batch_size: Events per batch
        enable_replay: Enable event replay capability
        enable_audit: Enable audit logging
        
    Returns:
        ScalableEventProcessor instance
    """
    processor = ScalableEventProcessor(
        min_workers=min_workers,
        max_workers=max_workers,
        batch_size=batch_size
    )
    
    processor.enable_replay = enable_replay
    processor.enable_audit_logging = enable_audit
    
    return processor