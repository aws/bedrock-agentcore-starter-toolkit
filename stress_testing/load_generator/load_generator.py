"""
Load Generator - Generates transaction load with precise rate control.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from collections import deque

from .transaction_factory import TransactionFactory
from ..models import LoadProfile, LoadProfileType, SystemMetrics


logger = logging.getLogger(__name__)


class RateController:
    """Controls transaction generation rate with precision."""
    
    def __init__(self, target_tps: float):
        """
        Initialize rate controller.
        
        Args:
            target_tps: Target transactions per second
        """
        self.target_tps = target_tps
        self.interval = 1.0 / target_tps if target_tps > 0 else 0
        self.last_send_time = 0.0
        self.sent_count = 0
        self.start_time = time.time()
    
    async def wait_for_next_slot(self):
        """Wait until next transaction slot is available."""
        if self.target_tps <= 0:
            return
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        expected_count = int(elapsed * self.target_tps)
        
        if self.sent_count >= expected_count:
            # We're ahead, need to wait
            wait_time = (self.sent_count + 1) / self.target_tps - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.sent_count += 1
    
    def update_rate(self, new_tps: float):
        """Update target TPS."""
        self.target_tps = new_tps
        self.interval = 1.0 / new_tps if new_tps > 0 else 0
    
    def get_current_rate(self) -> float:
        """Get actual current rate."""
        elapsed = time.time() - self.start_time
        return self.sent_count / elapsed if elapsed > 0 else 0


class LoadGenerator:
    """Generates transaction load with configurable patterns."""
    
    def __init__(
        self,
        transaction_factory: Optional[TransactionFactory] = None,
        num_workers: int = 10,
        submission_callback: Optional[Callable] = None
    ):
        """
        Initialize load generator.
        
        Args:
            transaction_factory: Factory for generating transactions
            num_workers: Number of parallel workers
            submission_callback: Async callback for submitting transactions
        """
        self.transaction_factory = transaction_factory or TransactionFactory()
        self.num_workers = num_workers
        self.submission_callback = submission_callback
        
        # State
        self.is_running = False
        self.current_tps = 0.0
        self.load_profile: Optional[LoadProfile] = None
        
        # Workers
        self.workers: List[asyncio.Task] = []
        self.rate_controller: Optional[RateController] = None
        
        # Metrics
        self.total_sent = 0
        self.total_success = 0
        self.total_failed = 0
        self.start_time: Optional[datetime] = None
        self.response_times: deque = deque(maxlen=1000)
        
        # Queue for backpressure
        self.transaction_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        logger.info(f"LoadGenerator initialized with {num_workers} workers")
    
    async def start(self, load_profile: LoadProfile, duration_seconds: int):
        """
        Start load generation.
        
        Args:
            load_profile: Load profile to follow
            duration_seconds: Duration to run
        """
        if self.is_running:
            logger.warning("Load generator already running")
            return
        
        self.is_running = True
        self.load_profile = load_profile
        self.start_time = datetime.utcnow()
        self.total_sent = 0
        self.total_success = 0
        self.total_failed = 0
        
        logger.info(f"Starting load generation: {load_profile.profile_type.value}, duration={duration_seconds}s")
        
        # Start workers
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        
        # Start load pattern controller
        controller_task = asyncio.create_task(
            self._load_pattern_controller(load_profile, duration_seconds)
        )
        
        # Wait for completion
        await controller_task
        
        # Stop workers
        await self.stop()
    
    async def stop(self):
        """Stop load generation."""
        if not self.is_running:
            return
        
        logger.info("Stopping load generation")
        self.is_running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info(f"Load generation stopped. Total sent: {self.total_sent}")
    
    async def _load_pattern_controller(self, profile: LoadProfile, duration: int):
        """Control load pattern over time."""
        start = time.time()
        
        if profile.profile_type == LoadProfileType.RAMP_UP:
            await self._ramp_up_pattern(profile, duration, start)
        elif profile.profile_type == LoadProfileType.SUSTAINED:
            await self._sustained_pattern(profile, duration, start)
        elif profile.profile_type == LoadProfileType.BURST:
            await self._burst_pattern(profile, duration, start)
        elif profile.profile_type == LoadProfileType.WAVE:
            await self._wave_pattern(profile, duration, start)
        elif profile.profile_type == LoadProfileType.CHAOS:
            await self._chaos_pattern(profile, duration, start)
    
    async def _ramp_up_pattern(self, profile: LoadProfile, duration: int, start: float):
        """Ramp up from start_tps to peak_tps."""
        ramp_duration = min(60, duration // 3)  # 1 minute or 1/3 of duration
        sustained_duration = duration - ramp_duration
        
        # Ramp up phase
        for i in range(ramp_duration):
            if not self.is_running:
                break
            
            progress = i / ramp_duration
            current_tps = profile.start_tps + (profile.peak_tps - profile.start_tps) * progress
            self.current_tps = current_tps
            self.rate_controller = RateController(current_tps)
            
            await asyncio.sleep(1)
        
        # Sustained phase
        self.current_tps = profile.peak_tps
        self.rate_controller = RateController(profile.peak_tps)
        await asyncio.sleep(sustained_duration)
    
    async def _sustained_pattern(self, profile: LoadProfile, duration: int, start: float):
        """Maintain sustained TPS."""
        self.current_tps = profile.sustained_tps
        self.rate_controller = RateController(profile.sustained_tps)
        await asyncio.sleep(duration)
    
    async def _burst_pattern(self, profile: LoadProfile, duration: int, start: float):
        """Generate periodic bursts."""
        self.rate_controller = RateController(profile.sustained_tps)
        
        elapsed = 0
        while elapsed < duration and self.is_running:
            # Sustained load
            self.current_tps = profile.sustained_tps
            self.rate_controller.update_rate(profile.sustained_tps)
            await asyncio.sleep(profile.burst_interval_seconds)
            elapsed += profile.burst_interval_seconds
            
            if elapsed >= duration:
                break
            
            # Burst
            self.current_tps = profile.burst_tps
            self.rate_controller.update_rate(profile.burst_tps)
            await asyncio.sleep(profile.burst_duration_seconds)
            elapsed += profile.burst_duration_seconds
    
    async def _wave_pattern(self, profile: LoadProfile, duration: int, start: float):
        """Generate wave pattern."""
        import math
        
        self.rate_controller = RateController(profile.sustained_tps)
        
        elapsed = 0
        while elapsed < duration and self.is_running:
            # Calculate wave position
            wave_progress = (elapsed % profile.wave_period_seconds) / profile.wave_period_seconds
            wave_value = math.sin(wave_progress * 2 * math.pi)
            
            # Calculate TPS
            current_tps = profile.sustained_tps + (profile.wave_amplitude * wave_value)
            current_tps = max(0, current_tps)
            
            self.current_tps = current_tps
            self.rate_controller.update_rate(current_tps)
            
            await asyncio.sleep(1)
            elapsed += 1
    
    async def _chaos_pattern(self, profile: LoadProfile, duration: int, start: float):
        """Generate chaotic random load."""
        import random
        
        self.rate_controller = RateController(profile.sustained_tps)
        
        elapsed = 0
        while elapsed < duration and self.is_running:
            # Random TPS change
            current_tps = random.uniform(profile.chaos_min_tps, profile.chaos_max_tps)
            self.current_tps = current_tps
            self.rate_controller.update_rate(current_tps)
            
            await asyncio.sleep(profile.chaos_change_interval_seconds)
            elapsed += profile.chaos_change_interval_seconds
    
    async def _worker(self, worker_id: int):
        """Worker that generates and submits transactions."""
        logger.debug(f"Worker {worker_id} started")
        
        try:
            while self.is_running:
                # Wait for rate limit
                if self.rate_controller:
                    await self.rate_controller.wait_for_next_slot()
                
                # Generate transaction
                transaction = self.transaction_factory.generate_transaction()
                
                # Submit transaction
                success = await self._submit_transaction(transaction)
                
                # Update metrics
                self.total_sent += 1
                if success:
                    self.total_success += 1
                else:
                    self.total_failed += 1
                
        except asyncio.CancelledError:
            logger.debug(f"Worker {worker_id} cancelled")
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
    
    async def _submit_transaction(self, transaction: Dict[str, Any]) -> bool:
        """
        Submit a transaction.
        
        Args:
            transaction: Transaction to submit
            
        Returns:
            True if successful, False otherwise
        """
        if not self.submission_callback:
            # No callback, just simulate
            await asyncio.sleep(0.001)
            return True
        
        try:
            start_time = time.time()
            
            # Call submission callback
            if asyncio.iscoroutinefunction(self.submission_callback):
                result = await self.submission_callback(transaction)
            else:
                result = self.submission_callback(transaction)
            
            # Track response time
            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)
            
            return result is not False
            
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return False
    
    def get_metrics(self) -> SystemMetrics:
        """Get current load generator metrics."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 1
        
        # Calculate response time percentiles
        sorted_times = sorted(self.response_times) if self.response_times else [0]
        p50_idx = int(len(sorted_times) * 0.50)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            throughput_tps=self.total_sent / elapsed,
            requests_total=self.total_sent,
            requests_successful=self.total_success,
            requests_failed=self.total_failed,
            avg_response_time_ms=sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            p50_response_time_ms=sorted_times[p50_idx],
            p95_response_time_ms=sorted_times[p95_idx],
            p99_response_time_ms=sorted_times[p99_idx],
            max_response_time_ms=max(sorted_times),
            error_rate=self.total_failed / self.total_sent if self.total_sent > 0 else 0,
            timeout_rate=0.0,
            cpu_utilization=0.0,
            memory_utilization=0.0,
            network_throughput_mbps=0.0,
            queue_depth=self.transaction_queue.qsize()
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load generator statistics."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            "is_running": self.is_running,
            "current_tps": self.current_tps,
            "target_tps": self.rate_controller.target_tps if self.rate_controller else 0,
            "actual_tps": self.rate_controller.get_current_rate() if self.rate_controller else 0,
            "total_sent": self.total_sent,
            "total_success": self.total_success,
            "total_failed": self.total_failed,
            "success_rate": self.total_success / self.total_sent if self.total_sent > 0 else 0,
            "elapsed_seconds": elapsed,
            "num_workers": self.num_workers,
            "queue_depth": self.transaction_queue.qsize()
        }
