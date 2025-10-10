"""
Real-Time Transaction Stream Processing

Provides high-throughput, low-latency processing of transaction streams
for real-time fraud detection with automatic scaling and monitoring.
"""

import logging
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import statistics

logger = logging.getLogger(__name__)


class StreamStatus(Enum):
    """Stream processing status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


class ProcessingPriority(Enum):
    """Transaction processing priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Transaction:
    """Transaction data structure for stream processing."""
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant: str
    category: str
    timestamp: datetime
    location: Dict[str, Any]
    device_info: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "merchant": self.merchant,
            "category": self.category,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "device_info": self.device_info,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create transaction from dictionary."""
        return cls(
            transaction_id=data["transaction_id"],
            user_id=data["user_id"],
            amount=float(data["amount"]),
            currency=data["currency"],
            merchant=data["merchant"],
            category=data["category"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            location=data.get("location", {}),
            device_info=data.get("device_info", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class ProcessingResult:
    """Result of transaction processing."""
    transaction_id: str
    decision: str
    confidence_score: float
    risk_score: float
    processing_time_ms: float
    fraud_indicators: List[str]
    recommendations: List[str]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamMetrics:
    """Stream processing metrics."""
    transactions_processed: int = 0
    transactions_per_second: float = 0.0
    average_processing_time_ms: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    queue_depth: int = 0
    active_workers: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_throughput(self, processed_count: int, time_window_seconds: float) -> None:
        """Update throughput metrics."""
        self.transactions_per_second = processed_count / time_window_seconds if time_window_seconds > 0 else 0.0
        self.last_update = datetime.now()
    
    def update_processing_time(self, processing_times: List[float]) -> None:
        """Update processing time metrics."""
        if processing_times:
            self.average_processing_time_ms = statistics.mean(processing_times)
    
    def update_error_rate(self) -> None:
        """Update error rate."""
        if self.transactions_processed > 0:
            self.error_rate = (self.error_count / self.transactions_processed) * 100


class TransactionStreamProcessor:
    """
    High-performance real-time transaction stream processor.
    
    Features:
    - Asynchronous processing with configurable concurrency
    - Automatic scaling based on load
    - Priority-based processing
    - Real-time metrics and monitoring
    - Error handling and recovery
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        queue_size: int = 10000,
        batch_size: int = 100,
        processing_timeout: float = 5.0
    ):
        """
        Initialize stream processor.
        
        Args:
            max_workers: Maximum number of worker threads
            queue_size: Maximum queue size for buffering
            batch_size: Batch size for processing optimization
            processing_timeout: Timeout for individual transaction processing
        """
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.batch_size = batch_size
        self.processing_timeout = processing_timeout
        
        # Processing queues by priority
        self.priority_queues = {
            ProcessingPriority.CRITICAL: Queue(maxsize=queue_size // 4),
            ProcessingPriority.HIGH: Queue(maxsize=queue_size // 4),
            ProcessingPriority.NORMAL: Queue(maxsize=queue_size // 2),
            ProcessingPriority.LOW: Queue(maxsize=queue_size // 4)
        }
        
        # Worker management
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.workers = []
        self.status = StreamStatus.STOPPED
        
        # Processing handlers
        self.fraud_detector: Optional[Callable[[Transaction], ProcessingResult]] = None
        self.result_handlers: List[Callable[[ProcessingResult], None]] = []
        self.error_handlers: List[Callable[[Exception, Transaction], None]] = []
        
        # Metrics and monitoring
        self.metrics = StreamMetrics()
        self.processing_times = []
        self.last_metrics_update = datetime.now()
        self.metrics_window = 60  # seconds
        
        # Auto-scaling configuration
        self.enable_auto_scaling = True
        self.min_workers = 2
        self.scale_up_threshold = 0.8  # Queue utilization
        self.scale_down_threshold = 0.3
        self.last_scale_check = datetime.now()
        self.scale_check_interval = 30  # seconds
        
        logger.info(f"Transaction stream processor initialized with {max_workers} max workers")
    
    def set_fraud_detector(self, detector: Callable[[Transaction], ProcessingResult]) -> None:
        """
        Set the fraud detection function.
        
        Args:
            detector: Function that takes a Transaction and returns ProcessingResult
        """
        self.fraud_detector = detector
        logger.info("Fraud detector registered")
    
    def add_result_handler(self, handler: Callable[[ProcessingResult], None]) -> None:
        """
        Add result handler for processing results.
        
        Args:
            handler: Function to handle processing results
        """
        self.result_handlers.append(handler)
        logger.debug("Result handler added")
    
    def add_error_handler(self, handler: Callable[[Exception, Transaction], None]) -> None:
        """
        Add error handler for processing errors.
        
        Args:
            handler: Function to handle processing errors
        """
        self.error_handlers.append(handler)
        logger.debug("Error handler added")
    
    def start(self) -> None:
        """Start the stream processor."""
        if self.status != StreamStatus.STOPPED:
            logger.warning("Stream processor is already running")
            return
        
        if not self.fraud_detector:
            raise ValueError("Fraud detector must be set before starting")
        
        self.status = StreamStatus.STARTING
        logger.info("Starting transaction stream processor")
        
        # Start worker threads
        for i in range(self.min_workers):
            self._start_worker(f"worker_{i}")
        
        # Start monitoring thread
        self.executor.submit(self._metrics_monitor)
        
        # Start auto-scaling thread if enabled
        if self.enable_auto_scaling:
            self.executor.submit(self._auto_scaler)
        
        self.status = StreamStatus.RUNNING
        logger.info(f"Stream processor started with {len(self.workers)} workers")
    
    def stop(self) -> None:
        """Stop the stream processor."""
        if self.status == StreamStatus.STOPPED:
            return
        
        self.status = StreamStatus.STOPPING
        logger.info("Stopping transaction stream processor")
        
        # Stop accepting new transactions
        # Workers will finish current transactions and exit
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.workers.clear()
        self.status = StreamStatus.STOPPED
        logger.info("Stream processor stopped")
    
    def process_transaction(
        self, 
        transaction: Transaction, 
        priority: ProcessingPriority = ProcessingPriority.NORMAL
    ) -> bool:
        """
        Submit transaction for processing.
        
        Args:
            transaction: Transaction to process
            priority: Processing priority
            
        Returns:
            True if transaction was queued successfully
        """
        if self.status != StreamStatus.RUNNING:
            logger.warning("Cannot process transaction - processor not running")
            return False
        
        try:
            # Add to appropriate priority queue
            queue = self.priority_queues[priority]
            queue.put_nowait((transaction, priority))
            
            logger.debug(f"Queued transaction {transaction.transaction_id} with priority {priority.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue transaction {transaction.transaction_id}: {str(e)}")
            return False
    
    def process_batch(self, transactions: List[Transaction]) -> List[bool]:
        """
        Process a batch of transactions.
        
        Args:
            transactions: List of transactions to process
            
        Returns:
            List of success flags for each transaction
        """
        results = []
        for transaction in transactions:
            # Determine priority based on transaction characteristics
            priority = self._determine_priority(transaction)
            success = self.process_transaction(transaction, priority)
            results.append(success)
        
        return results
    
    def get_metrics(self) -> StreamMetrics:
        """Get current processing metrics."""
        # Update queue depth
        total_queue_depth = sum(q.qsize() for q in self.priority_queues.values())
        self.metrics.queue_depth = total_queue_depth
        self.metrics.active_workers = len(self.workers)
        
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed processor status."""
        metrics = self.get_metrics()
        
        return {
            "status": self.status.value,
            "metrics": {
                "transactions_processed": metrics.transactions_processed,
                "transactions_per_second": metrics.transactions_per_second,
                "average_processing_time_ms": metrics.average_processing_time_ms,
                "error_count": metrics.error_count,
                "error_rate": metrics.error_rate,
                "queue_depth": metrics.queue_depth,
                "active_workers": metrics.active_workers
            },
            "configuration": {
                "max_workers": self.max_workers,
                "queue_size": self.queue_size,
                "batch_size": self.batch_size,
                "auto_scaling_enabled": self.enable_auto_scaling
            },
            "queue_status": {
                priority.name.lower(): queue.qsize() 
                for priority, queue in self.priority_queues.items()
            }
        }
    
    def _start_worker(self, worker_id: str) -> None:
        """Start a new worker thread."""
        worker_future = self.executor.submit(self._worker_loop, worker_id)
        self.workers.append({
            "id": worker_id,
            "future": worker_future,
            "start_time": datetime.now()
        })
        logger.debug(f"Started worker: {worker_id}")
    
    def _worker_loop(self, worker_id: str) -> None:
        """Main worker processing loop."""
        logger.debug(f"Worker {worker_id} started")
        
        while self.status == StreamStatus.RUNNING:
            try:
                # Get next transaction from priority queues
                transaction, priority = self._get_next_transaction()
                
                if transaction is None:
                    time.sleep(0.01)  # Brief pause if no transactions
                    continue
                
                # Process transaction
                start_time = time.time()
                try:
                    result = self.fraud_detector(transaction)
                    processing_time = (time.time() - start_time) * 1000
                    
                    # Update metrics
                    self.metrics.transactions_processed += 1
                    self.processing_times.append(processing_time)
                    
                    # Handle result
                    for handler in self.result_handlers:
                        try:
                            handler(result)
                        except Exception as e:
                            logger.error(f"Error in result handler: {str(e)}")
                    
                    logger.debug(f"Processed transaction {transaction.transaction_id} in {processing_time:.1f}ms")
                    
                except Exception as e:
                    self.metrics.error_count += 1
                    logger.error(f"Error processing transaction {transaction.transaction_id}: {str(e)}")
                    
                    # Handle error
                    for handler in self.error_handlers:
                        try:
                            handler(e, transaction)
                        except Exception as handler_error:
                            logger.error(f"Error in error handler: {str(handler_error)}")
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}")
                time.sleep(1)  # Pause on error
        
        logger.debug(f"Worker {worker_id} stopped")
    
    def _get_next_transaction(self) -> tuple[Optional[Transaction], Optional[ProcessingPriority]]:
        """Get next transaction from priority queues."""
        # Check queues in priority order
        for priority in [ProcessingPriority.CRITICAL, ProcessingPriority.HIGH, 
                        ProcessingPriority.NORMAL, ProcessingPriority.LOW]:
            queue = self.priority_queues[priority]
            try:
                transaction, trans_priority = queue.get(timeout=0.1)
                return transaction, trans_priority
            except Empty:
                continue
        
        return None, None
    
    def _determine_priority(self, transaction: Transaction) -> ProcessingPriority:
        """Determine processing priority for a transaction."""
        # High-value transactions get higher priority
        if transaction.amount > 10000:
            return ProcessingPriority.CRITICAL
        elif transaction.amount > 1000:
            return ProcessingPriority.HIGH
        
        # International transactions get higher priority
        if transaction.location.get("country") != "US":
            return ProcessingPriority.HIGH
        
        # Certain categories get higher priority
        high_risk_categories = ["gambling", "crypto", "cash_advance"]
        if transaction.category.lower() in high_risk_categories:
            return ProcessingPriority.HIGH
        
        return ProcessingPriority.NORMAL
    
    def _metrics_monitor(self) -> None:
        """Monitor and update metrics."""
        while self.status == StreamStatus.RUNNING:
            try:
                current_time = datetime.now()
                time_window = (current_time - self.last_metrics_update).total_seconds()
                
                if time_window >= self.metrics_window:
                    # Update throughput
                    processed_in_window = self.metrics.transactions_processed
                    self.metrics.update_throughput(processed_in_window, time_window)
                    
                    # Update processing times
                    if self.processing_times:
                        self.metrics.update_processing_time(self.processing_times[-1000:])  # Last 1000
                    
                    # Update error rate
                    self.metrics.update_error_rate()
                    
                    self.last_metrics_update = current_time
                    
                    logger.debug(f"Metrics updated: {self.metrics.transactions_per_second:.1f} TPS, "
                               f"{self.metrics.average_processing_time_ms:.1f}ms avg")
                
                time.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in metrics monitor: {str(e)}")
                time.sleep(10)
    
    def _auto_scaler(self) -> None:
        """Automatic scaling based on queue utilization."""
        while self.status == StreamStatus.RUNNING:
            try:
                current_time = datetime.now()
                
                if (current_time - self.last_scale_check).total_seconds() >= self.scale_check_interval:
                    self._check_scaling()
                    self.last_scale_check = current_time
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in auto-scaler: {str(e)}")
                time.sleep(30)
    
    def _check_scaling(self) -> None:
        """Check if scaling is needed."""
        total_queue_size = sum(q.maxsize for q in self.priority_queues.values())
        total_queue_depth = sum(q.qsize() for q in self.priority_queues.values())
        
        utilization = total_queue_depth / total_queue_size if total_queue_size > 0 else 0
        current_workers = len(self.workers)
        
        # Scale up if utilization is high and we have capacity
        if utilization > self.scale_up_threshold and current_workers < self.max_workers:
            new_worker_id = f"worker_{current_workers}"
            self._start_worker(new_worker_id)
            logger.info(f"Scaled up: added worker {new_worker_id} (utilization: {utilization:.2f})")
        
        # Scale down if utilization is low and we have more than minimum workers
        elif utilization < self.scale_down_threshold and current_workers > self.min_workers:
            # Remove a worker (it will finish current work and exit)
            if self.workers:
                removed_worker = self.workers.pop()
                logger.info(f"Scaled down: removed worker {removed_worker['id']} (utilization: {utilization:.2f})")


class StreamingFraudDetector:
    """
    Streaming fraud detector that integrates with the transaction stream processor.
    """
    
    def __init__(self):
        """Initialize streaming fraud detector."""
        self.risk_rules = []
        self.ml_models = {}
        self.processing_stats = {
            "total_processed": 0,
            "fraud_detected": 0,
            "false_positives": 0,
            "processing_times": []
        }
    
    def detect_fraud(self, transaction: Transaction) -> ProcessingResult:
        """
        Detect fraud in a transaction.
        
        Args:
            transaction: Transaction to analyze
            
        Returns:
            ProcessingResult with fraud detection results
        """
        start_time = time.time()
        
        try:
            # Initialize result
            fraud_indicators = []
            risk_score = 0.0
            
            # Apply risk rules
            risk_score += self._apply_risk_rules(transaction, fraud_indicators)
            
            # Apply ML models (placeholder)
            risk_score += self._apply_ml_models(transaction, fraud_indicators)
            
            # Determine decision based on risk score
            if risk_score >= 0.8:
                decision = "DECLINE"
                confidence = 0.9
            elif risk_score >= 0.6:
                decision = "FLAG"
                confidence = 0.7
            elif risk_score >= 0.4:
                decision = "REVIEW"
                confidence = 0.6
            else:
                decision = "APPROVE"
                confidence = 0.8
            
            # Generate recommendations
            recommendations = self._generate_recommendations(risk_score, fraud_indicators)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update stats
            self.processing_stats["total_processed"] += 1
            self.processing_stats["processing_times"].append(processing_time)
            
            if decision in ["DECLINE", "FLAG"]:
                self.processing_stats["fraud_detected"] += 1
            
            return ProcessingResult(
                transaction_id=transaction.transaction_id,
                decision=decision,
                confidence_score=confidence,
                risk_score=risk_score,
                processing_time_ms=processing_time,
                fraud_indicators=fraud_indicators,
                recommendations=recommendations,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in fraud detection for {transaction.transaction_id}: {str(e)}")
            
            # Return safe default
            return ProcessingResult(
                transaction_id=transaction.transaction_id,
                decision="REVIEW",
                confidence_score=0.5,
                risk_score=0.5,
                processing_time_ms=(time.time() - start_time) * 1000,
                fraud_indicators=["processing_error"],
                recommendations=["Manual review required due to processing error"],
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    def _apply_risk_rules(self, transaction: Transaction, fraud_indicators: List[str]) -> float:
        """Apply rule-based risk assessment."""
        risk_score = 0.0
        
        # High amount rule
        if transaction.amount > 5000:
            risk_score += 0.3
            fraud_indicators.append("high_amount")
        
        # Unusual time rule (simplified)
        hour = transaction.timestamp.hour
        if hour < 6 or hour > 22:
            risk_score += 0.2
            fraud_indicators.append("unusual_time")
        
        # International transaction rule
        if transaction.location.get("country") != "US":
            risk_score += 0.25
            fraud_indicators.append("international_transaction")
        
        # High-risk merchant categories
        high_risk_categories = ["gambling", "crypto", "cash_advance", "adult_entertainment"]
        if transaction.category.lower() in high_risk_categories:
            risk_score += 0.35
            fraud_indicators.append("high_risk_category")
        
        return min(risk_score, 1.0)
    
    def _apply_ml_models(self, transaction: Transaction, fraud_indicators: List[str]) -> float:
        """Apply ML models for fraud detection (placeholder)."""
        # Placeholder for ML model integration
        # In a real implementation, this would call trained models
        
        # Simple heuristic for demonstration
        risk_score = 0.0
        
        # Velocity check (simplified)
        if transaction.amount > 1000:
            risk_score += 0.1
            fraud_indicators.append("velocity_risk")
        
        return min(risk_score, 1.0)
    
    def _generate_recommendations(self, risk_score: float, fraud_indicators: List[str]) -> List[str]:
        """Generate recommendations based on risk assessment."""
        recommendations = []
        
        if risk_score >= 0.8:
            recommendations.append("Block transaction immediately")
            recommendations.append("Contact customer for verification")
        elif risk_score >= 0.6:
            recommendations.append("Flag for manual review")
            recommendations.append("Monitor customer activity")
        elif risk_score >= 0.4:
            recommendations.append("Enhanced monitoring")
        else:
            recommendations.append("Standard processing")
        
        # Specific recommendations based on indicators
        if "high_amount" in fraud_indicators:
            recommendations.append("Verify large transaction with customer")
        
        if "international_transaction" in fraud_indicators:
            recommendations.append("Check travel notifications")
        
        if "unusual_time" in fraud_indicators:
            recommendations.append("Verify transaction timing with customer")
        
        return recommendations
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fraud detection statistics."""
        stats = self.processing_stats.copy()
        
        if stats["processing_times"]:
            stats["average_processing_time_ms"] = statistics.mean(stats["processing_times"])
            stats["max_processing_time_ms"] = max(stats["processing_times"])
            stats["min_processing_time_ms"] = min(stats["processing_times"])
        
        if stats["total_processed"] > 0:
            stats["fraud_detection_rate"] = (stats["fraud_detected"] / stats["total_processed"]) * 100
        
        return stats