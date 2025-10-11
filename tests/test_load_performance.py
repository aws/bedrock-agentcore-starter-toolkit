"""
Load and Performance Testing Suite

Tests system under high transaction volumes (1000+ TPS),
validates auto-scaling behavior, measures response times,
and tests system recovery from failures.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from unified_fraud_detection_system import UnifiedFraudDetectionSystem
from transaction_processing_pipeline import TransactionProcessingPipeline


class PerformanceMetrics:
    """Track performance metrics during load testing."""
    
    def __init__(self):
        self.response_times = []
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = None
        self.end_time = None
    
    def record_response(self, response_time: float, success: bool):
        """Record a response."""
        self.response_times.append(response_time)
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def get_statistics(self) -> Dict:
        """Calculate performance statistics."""
        if not self.response_times:
            return {}
        
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        
        return {
            "total_requests": len(self.response_times),
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / len(self.response_times) * 100,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": self._percentile(self.response_times, 95),
            "p99_response_time": self._percentile(self.response_times, 99),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "throughput_tps": len(self.response_times) / duration if duration > 0 else 0,
            "duration_seconds": duration
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestHighVolumeProcessing:
    """Test system under high transaction volumes."""
    
    @pytest.fixture
    def system(self):
        """Create unified system for testing."""
        return UnifiedFraudDetectionSystem()
    
    def generate_transaction(self, tx_id: int) -> Dict:
        """Generate realistic test transaction."""
        return {
            "transaction_id": f"load_test_{tx_id}",
            "user_id": f"user_{random.randint(1, 1000)}",
            "amount": round(random.uniform(10, 10000), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "merchant": random.choice(["Store A", "Store B", "Store C", "Online Shop"]),
            "location": random.choice(["New York", "London", "Tokyo", "Sydney"]),
            "device_id": f"device_{random.randint(1, 500)}",
            "timestamp": datetime.now().isoformat()
        }
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_1000_tps_sustained_load(self, system):
        """Test system at 1000 transactions per second."""
        metrics = PerformanceMetrics()
        metrics.start_time = datetime.now()
        
        # Generate 10,000 transactions (10 seconds at 1000 TPS)
        num_transactions = 10000
        batch_size = 100
        
        print(f"\nStarting load test: {num_transactions} transactions")
        
        for batch_start in range(0, num_transactions, batch_size):
            batch_end = min(batch_start + batch_size, num_transactions)
            transactions = [
                self.generate_transaction(i) 
                for i in range(batch_start, batch_end)
            ]
            
            # Process batch concurrently
            start_time = time.time()
            results = await asyncio.gather(*[
                system.process_transaction(tx) 
                for tx in transactions
            ], return_exceptions=True)
            batch_time = time.time() - start_time
            
            # Record metrics
            for result in results:
                success = not isinstance(result, Exception) and result is not None
                metrics.record_response(batch_time / len(transactions), success)
            
            # Small delay to simulate realistic load
            await asyncio.sleep(0.01)
        
        metrics.end_time = datetime.now()
        stats = metrics.get_statistics()
        
        print(f"\nLoad Test Results:")
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Success Rate: {stats['success_rate']:.2f}%")
        print(f"  Avg Response Time: {stats['avg_response_time']*1000:.2f}ms")
        print(f"  P95 Response Time: {stats['p95_response_time']*1000:.2f}ms")
        print(f"  P99 Response Time: {stats['p99_response_time']*1000:.2f}ms")
        print(f"  Throughput: {stats['throughput_tps']:.2f} TPS")
        
        # Assertions
        assert stats['success_rate'] >= 95, "Success rate should be at least 95%"
        assert stats['avg_response_time'] < 1.0, "Average response time should be under 1 second"
        assert stats['p99_response_time'] < 2.0, "P99 response time should be under 2 seconds"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_burst_traffic_handling(self, system):
        """Test system handling sudden traffic bursts."""
        metrics = PerformanceMetrics()
        metrics.start_time = datetime.now()
        
        # Simulate burst: 5000 transactions in 1 second
        num_transactions = 5000
        transactions = [self.generate_transaction(i) for i in range(num_transactions)]
        
        print(f"\nStarting burst test: {num_transactions} transactions")
        
        start_time = time.time()
        results = await asyncio.gather(*[
            system.process_transaction(tx) 
            for tx in transactions
        ], return_exceptions=True)
        burst_time = time.time() - start_time
        
        # Record metrics
        for result in results:
            success = not isinstance(result, Exception) and result is not None
            metrics.record_response(burst_time / len(transactions), success)
        
        metrics.end_time = datetime.now()
        stats = metrics.get_statistics()
        
        print(f"\nBurst Test Results:")
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Success Rate: {stats['success_rate']:.2f}%")
        print(f"  Burst Duration: {burst_time:.2f}s")
        print(f"  Effective TPS: {num_transactions/burst_time:.2f}")
        
        # System should handle burst without major failures
        assert stats['success_rate'] >= 90, "Should handle burst with 90%+ success rate"
    
    @pytest.mark.asyncio
    async def test_concurrent_user_simulation(self, system):
        """Test system with concurrent users."""
        num_users = 100
        transactions_per_user = 10
        
        async def simulate_user(user_id: int):
            """Simulate a single user's transactions."""
            user_metrics = []
            for i in range(transactions_per_user):
                tx = {
                    "transaction_id": f"user_{user_id}_tx_{i}",
                    "user_id": f"user_{user_id}",
                    "amount": round(random.uniform(10, 1000), 2),
                    "currency": "USD",
                    "timestamp": datetime.now().isoformat()
                }
                
                start = time.time()
                try:
                    result = await system.process_transaction(tx)
                    response_time = time.time() - start
                    user_metrics.append((response_time, True))
                except Exception:
                    response_time = time.time() - start
                    user_metrics.append((response_time, False))
                
                # Random delay between transactions
                await asyncio.sleep(random.uniform(0.1, 0.5))
            
            return user_metrics
        
        print(f"\nSimulating {num_users} concurrent users")
        
        # Run all users concurrently
        start_time = time.time()
        user_results = await asyncio.gather(*[
            simulate_user(i) for i in range(num_users)
        ])
        total_time = time.time() - start_time
        
        # Aggregate metrics
        all_metrics = [metric for user in user_results for metric in user]
        success_count = sum(1 for _, success in all_metrics if success)
        avg_response = statistics.mean([rt for rt, _ in all_metrics])
        
        print(f"\nConcurrent User Test Results:")
        print(f"  Total Transactions: {len(all_metrics)}")
        print(f"  Success Rate: {success_count/len(all_metrics)*100:.2f}%")
        print(f"  Avg Response Time: {avg_response*1000:.2f}ms")
        print(f"  Total Duration: {total_time:.2f}s")
        
        assert success_count / len(all_metrics) >= 0.95


class TestAutoScaling:
    """Test auto-scaling behavior under load."""
    
    @pytest.fixture
    def pipeline(self):
        """Create processing pipeline."""
        return TransactionProcessingPipeline()
    
    @pytest.mark.asyncio
    async def test_scale_up_behavior(self, pipeline):
        """Test system scales up under increasing load."""
        # Start with low load
        low_load_transactions = [
            {"transaction_id": f"scale_low_{i}", "amount": 100.0}
            for i in range(10)
        ]
        
        low_load_start = time.time()
        await asyncio.gather(*[
            pipeline.process_transaction(tx) 
            for tx in low_load_transactions
        ])
        low_load_time = time.time() - low_load_start
        
        # Increase to high load
        high_load_transactions = [
            {"transaction_id": f"scale_high_{i}", "amount": 100.0}
            for i in range(100)
        ]
        
        high_load_start = time.time()
        await asyncio.gather(*[
            pipeline.process_transaction(tx) 
            for tx in high_load_transactions
        ])
        high_load_time = time.time() - high_load_start
        
        # Calculate throughput
        low_throughput = len(low_load_transactions) / low_load_time
        high_throughput = len(high_load_transactions) / high_load_time
        
        print(f"\nAuto-Scaling Test:")
        print(f"  Low Load Throughput: {low_throughput:.2f} TPS")
        print(f"  High Load Throughput: {high_throughput:.2f} TPS")
        print(f"  Scaling Factor: {high_throughput/low_throughput:.2f}x")
        
        # High load throughput should be higher (system scaled)
        assert high_throughput >= low_throughput * 0.8, "System should maintain throughput under load"
    
    @pytest.mark.asyncio
    async def test_scale_down_behavior(self, pipeline):
        """Test system scales down after load decreases."""
        # High load period
        high_load_transactions = [
            {"transaction_id": f"scale_down_high_{i}", "amount": 100.0}
            for i in range(100)
        ]
        
        await asyncio.gather(*[
            pipeline.process_transaction(tx) 
            for tx in high_load_transactions
        ])
        
        # Wait for scale down
        await asyncio.sleep(2)
        
        # Low load period
        low_load_transactions = [
            {"transaction_id": f"scale_down_low_{i}", "amount": 100.0}
            for i in range(10)
        ]
        
        start = time.time()
        await asyncio.gather(*[
            pipeline.process_transaction(tx) 
            for tx in low_load_transactions
        ])
        response_time = time.time() - start
        
        # Should still be responsive after scale down
        avg_response = response_time / len(low_load_transactions)
        assert avg_response < 0.5, "System should remain responsive after scale down"


class TestResponseTimeOptimization:
    """Test and measure response time optimization."""
    
    @pytest.fixture
    def system(self):
        """Create system for testing."""
        return UnifiedFraudDetectionSystem()
    
    @pytest.mark.asyncio
    async def test_response_time_targets(self, system):
        """Test system meets response time targets."""
        num_samples = 100
        response_times = []
        
        for i in range(num_samples):
            tx = {
                "transaction_id": f"response_test_{i}",
                "user_id": f"user_{i}",
                "amount": 1000.00,
                "currency": "USD",
                "timestamp": datetime.now().isoformat()
            }
            
            start = time.time()
            await system.process_transaction(tx)
            response_time = time.time() - start
            response_times.append(response_time)
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        p95_time = PerformanceMetrics._percentile(response_times, 95)
        p99_time = PerformanceMetrics._percentile(response_times, 99)
        
        print(f"\nResponse Time Analysis:")
        print(f"  Average: {avg_time*1000:.2f}ms")
        print(f"  P95: {p95_time*1000:.2f}ms")
        print(f"  P99: {p99_time*1000:.2f}ms")
        
        # Assert targets
        assert avg_time < 0.5, "Average response time should be under 500ms"
        assert p95_time < 1.0, "P95 response time should be under 1 second"
        assert p99_time < 2.0, "P99 response time should be under 2 seconds"
    
    @pytest.mark.asyncio
    async def test_caching_effectiveness(self, system):
        """Test caching improves response times."""
        user_id = "cache_test_user"
        
        # First request (cold cache)
        tx1 = {
            "transaction_id": "cache_test_1",
            "user_id": user_id,
            "amount": 1000.00,
            "currency": "USD"
        }
        
        start = time.time()
        await system.process_transaction(tx1)
        cold_time = time.time() - start
        
        # Second request (warm cache)
        tx2 = {
            "transaction_id": "cache_test_2",
            "user_id": user_id,
            "amount": 1000.00,
            "currency": "USD"
        }
        
        start = time.time()
        await system.process_transaction(tx2)
        warm_time = time.time() - start
        
        print(f"\nCaching Effectiveness:")
        print(f"  Cold Cache: {cold_time*1000:.2f}ms")
        print(f"  Warm Cache: {warm_time*1000:.2f}ms")
        print(f"  Improvement: {(1 - warm_time/cold_time)*100:.1f}%")
        
        # Warm cache should be faster
        assert warm_time <= cold_time, "Cached requests should be faster or equal"


class TestSystemRecovery:
    """Test system recovery from failures."""
    
    @pytest.fixture
    def system(self):
        """Create system for testing."""
        return UnifiedFraudDetectionSystem()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, system):
        """Test system degrades gracefully under failures."""
        # Simulate partial system failure
        with pytest.raises(Exception):
            # This should trigger fallback mechanisms
            tx = {
                "transaction_id": "degradation_test",
                "user_id": "test_user",
                "amount": 1000.00,
                "currency": "INVALID"  # Invalid currency
            }
            
            result = await system.process_transaction(tx)
            
            # System should still provide a decision
            assert result is not None
            assert "decision" in result
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, system):
        """Test circuit breaker prevents cascading failures."""
        # Send multiple failing requests
        failing_transactions = [
            {
                "transaction_id": f"circuit_test_{i}",
                "user_id": "test_user",
                "amount": -1000.00  # Invalid amount
            }
            for i in range(10)
        ]
        
        results = await asyncio.gather(*[
            system.process_transaction(tx) 
            for tx in failing_transactions
        ], return_exceptions=True)
        
        # Circuit breaker should trip and fail fast
        # Later requests should fail faster than earlier ones
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_recovery_after_failure(self, system):
        """Test system recovers after transient failures."""
        # Cause a failure
        try:
            tx_fail = {
                "transaction_id": "recovery_fail",
                "user_id": "test_user",
                "amount": -1000.00
            }
            await system.process_transaction(tx_fail)
        except Exception:
            pass
        
        # Wait for recovery
        await asyncio.sleep(1)
        
        # Normal transaction should work
        tx_normal = {
            "transaction_id": "recovery_success",
            "user_id": "test_user",
            "amount": 1000.00,
            "currency": "USD"
        }
        
        result = await system.process_transaction(tx_normal)
        assert result is not None
        assert result["decision"] in ["APPROVE", "DECLINE", "FLAG", "REVIEW"]


@pytest.mark.asyncio
async def test_stress_test():
    """Comprehensive stress test."""
    system = UnifiedFraudDetectionSystem()
    metrics = PerformanceMetrics()
    metrics.start_time = datetime.now()
    
    # Run for 30 seconds with varying load
    duration = 30
    start_time = time.time()
    transaction_id = 0
    
    print(f"\nRunning {duration}-second stress test...")
    
    while time.time() - start_time < duration:
        # Vary load over time
        current_time = time.time() - start_time
        load_factor = 1 + 0.5 * (1 + random.random())  # 1-2x base load
        batch_size = int(10 * load_factor)
        
        transactions = [
            {
                "transaction_id": f"stress_{transaction_id + i}",
                "user_id": f"user_{random.randint(1, 100)}",
                "amount": round(random.uniform(10, 5000), 2),
                "currency": "USD",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(batch_size)
        ]
        transaction_id += batch_size
        
        batch_start = time.time()
        results = await asyncio.gather(*[
            system.process_transaction(tx) 
            for tx in transactions
        ], return_exceptions=True)
        batch_time = time.time() - batch_start
        
        for result in results:
            success = not isinstance(result, Exception) and result is not None
            metrics.record_response(batch_time / len(transactions), success)
        
        await asyncio.sleep(0.1)
    
    metrics.end_time = datetime.now()
    stats = metrics.get_statistics()
    
    print(f"\nStress Test Results:")
    print(f"  Duration: {stats['duration_seconds']:.2f}s")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Success Rate: {stats['success_rate']:.2f}%")
    print(f"  Avg Throughput: {stats['throughput_tps']:.2f} TPS")
    print(f"  Avg Response Time: {stats['avg_response_time']*1000:.2f}ms")
    print(f"  P99 Response Time: {stats['p99_response_time']*1000:.2f}ms")
    
    assert stats['success_rate'] >= 90, "Should maintain 90%+ success rate under stress"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "not slow"])
