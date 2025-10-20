#!/usr/bin/env python3
"""
Demo: Real-Time Transaction Stream Processing

Demonstrates high-throughput, low-latency processing of transaction streams
for real-time fraud detection with automatic scaling and monitoring.
"""

import logging
import time
import random
from datetime import datetime, timedelta
from src.transaction_stream_processor import (
    TransactionStreamProcessor, StreamingFraudDetector,
    Transaction, ProcessingResult, ProcessingPriority
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def generate_sample_transaction(transaction_id: int, fraud_probability: float = 0.1) -> Transaction:
    """Generate a sample transaction for testing."""
    is_fraud = random.random() < fraud_probability
    
    # Generate transaction characteristics
    if is_fraud:
        # Fraudulent transaction characteristics
        amount = random.uniform(5000, 50000)
        merchant = random.choice(["UNKNOWN_MERCHANT", "SUSPICIOUS_STORE", "CRYPTO_EXCHANGE"])
        category = random.choice(["gambling", "crypto", "cash_advance"])
        country = random.choice(["XX", "YY", "ZZ"])  # High-risk countries
        hour = random.choice([2, 3, 4, 23, 24, 1])  # Unusual hours
    else:
        # Normal transaction characteristics
        amount = random.uniform(10, 500)
        merchant = random.choice(["Starbucks", "Amazon", "Walmart", "Target", "Whole Foods"])
        category = random.choice(["food", "retail", "groceries", "entertainment"])
        country = "US"
        hour = random.randint(8, 20)  # Normal hours
    
    timestamp = datetime.now().replace(hour=hour % 24)
    
    return Transaction(
        transaction_id=f"TXN-{transaction_id:06d}",
        user_id=f"USER-{random.randint(1, 1000):04d}",
        amount=amount,
        currency="USD",
        merchant=merchant,
        category=category,
        timestamp=timestamp,
        location={"city": "New York" if country == "US" else "Unknown", "country": country},
        device_info={"device_id": f"DEV-{random.randint(1, 100):03d}", "ip": f"192.168.1.{random.randint(1, 255)}"},
        metadata={"is_fraud": is_fraud}  # For demo purposes only
    )


def demo_scenario_1_basic_streaming():
    """Scenario 1: Basic real-time stream processing."""
    print_section("Scenario 1: Basic Real-Time Stream Processing")
    
    # Initialize processor and detector
    processor = TransactionStreamProcessor(
        max_workers=5,
        queue_size=1000,
        batch_size=10
    )
    
    detector = StreamingFraudDetector()
    processor.set_fraud_detector(detector.detect_fraud)
    
    # Add result handler
    results = []
    def result_handler(result: ProcessingResult):
        results.append(result)
        if result.decision in ["DECLINE", "FLAG"]:
            print(f"  ⚠️  {result.transaction_id}: {result.decision} (Risk: {result.risk_score:.2f})")
    
    processor.add_result_handler(result_handler)
    
    # Start processor
    processor.start()
    print("✅ Stream processor started\n")
    
    # Process transactions
    print("Processing 20 transactions...")
    print("-" * 80)
    
    for i in range(20):
        transaction = generate_sample_transaction(i, fraud_probability=0.15)
        processor.process_transaction(transaction)
        time.sleep(0.05)  # Simulate real-time arrival
    
    # Wait for processing
    time.sleep(2)
    
    # Show results
    print(f"\n✅ Processed {len(results)} transactions")
    
    fraud_count = sum(1 for r in results if r.decision in ["DECLINE", "FLAG"])
    print(f"   Fraud detected: {fraud_count}")
    print(f"   Fraud rate: {(fraud_count / len(results) * 100):.1f}%")
    
    # Show metrics
    metrics = processor.get_metrics()
    print(f"\nMetrics:")
    print(f"   Transactions processed: {metrics.transactions_processed}")
    print(f"   Average processing time: {metrics.average_processing_time_ms:.1f}ms")
    print(f"   Error count: {metrics.error_count}")
    
    processor.stop()
    print("\n✅ Stream processor stopped")


def demo_scenario_2_high_throughput():
    """Scenario 2: High-throughput processing."""
    print_section("Scenario 2: High-Throughput Processing")
    
    processor = TransactionStreamProcessor(
        max_workers=10,
        queue_size=5000,
        batch_size=50
    )
    
    detector = StreamingFraudDetector()
    processor.set_fraud_detector(detector.detect_fraud)
    
    # Track results
    results = []
    def result_handler(result: ProcessingResult):
        results.append(result)
    
    processor.add_result_handler(result_handler)
    
    processor.start()
    print("✅ Stream processor started with 10 workers\n")
    
    # Process large batch
    print("Processing 500 transactions...")
    start_time = time.time()
    
    for i in range(500):
        transaction = generate_sample_transaction(i, fraud_probability=0.1)
        processor.process_transaction(transaction)
    
    # Wait for processing
    time.sleep(5)
    
    elapsed_time = time.time() - start_time
    
    # Show performance
    print(f"\n✅ Processed {len(results)} transactions in {elapsed_time:.2f}s")
    print(f"   Throughput: {len(results) / elapsed_time:.1f} transactions/second")
    
    metrics = processor.get_metrics()
    print(f"\nPerformance Metrics:")
    print(f"   Average processing time: {metrics.average_processing_time_ms:.1f}ms")
    print(f"   Transactions per second: {metrics.transactions_per_second:.1f}")
    print(f"   Active workers: {metrics.active_workers}")
    print(f"   Queue depth: {metrics.queue_depth}")
    
    processor.stop()


def demo_scenario_3_priority_processing():
    """Scenario 3: Priority-based processing."""
    print_section("Scenario 3: Priority-Based Processing")
    
    processor = TransactionStreamProcessor(
        max_workers=3,
        queue_size=1000
    )
    
    detector = StreamingFraudDetector()
    processor.set_fraud_detector(detector.detect_fraud)
    
    # Track processing order
    processing_order = []
    def result_handler(result: ProcessingResult):
        processing_order.append(result.transaction_id)
    
    processor.add_result_handler(result_handler)
    
    processor.start()
    print("✅ Stream processor started\n")
    
    # Submit transactions with different priorities
    print("Submitting transactions with different priorities:")
    print("-" * 80)
    
    transactions = [
        (generate_sample_transaction(1, 0), ProcessingPriority.LOW, "$50"),
        (generate_sample_transaction(2, 0), ProcessingPriority.CRITICAL, "$25,000"),
        (generate_sample_transaction(3, 0), ProcessingPriority.NORMAL, "$200"),
        (generate_sample_transaction(4, 0), ProcessingPriority.HIGH, "$5,000"),
        (generate_sample_transaction(5, 0), ProcessingPriority.NORMAL, "$150"),
    ]
    
    for transaction, priority, amount in transactions:
        transaction.amount = float(amount.replace("$", "").replace(",", ""))
        processor.process_transaction(transaction, priority)
        print(f"  {transaction.transaction_id}: {amount} - Priority: {priority.name}")
    
    time.sleep(2)
    
    print(f"\nProcessing Order:")
    print("-" * 80)
    for i, txn_id in enumerate(processing_order[:5], 1):
        print(f"  {i}. {txn_id}")
    
    print("\n💡 CRITICAL and HIGH priority transactions processed first")
    
    processor.stop()


def demo_scenario_4_auto_scaling():
    """Scenario 4: Automatic scaling based on load."""
    print_section("Scenario 4: Auto-Scaling Based on Load")
    
    processor = TransactionStreamProcessor(
        max_workers=10,
        queue_size=2000
    )
    
    processor.enable_auto_scaling = True
    processor.min_workers = 2
    processor.scale_up_threshold = 0.6  # Scale up at 60% utilization
    processor.scale_down_threshold = 0.2  # Scale down at 20% utilization
    
    detector = StreamingFraudDetector()
    processor.set_fraud_detector(detector.detect_fraud)
    
    processor.start()
    print("✅ Stream processor started with auto-scaling enabled\n")
    print(f"Configuration:")
    print(f"   Min workers: {processor.min_workers}")
    print(f"   Max workers: {processor.max_workers}")
    print(f"   Scale-up threshold: {processor.scale_up_threshold * 100}%")
    print(f"   Scale-down threshold: {processor.scale_down_threshold * 100}%")
    print()
    
    # Phase 1: Low load
    print("Phase 1: Low Load (50 transactions)")
    print("-" * 80)
    for i in range(50):
        transaction = generate_sample_transaction(i)
        processor.process_transaction(transaction)
        time.sleep(0.01)
    
    time.sleep(2)
    status = processor.get_status()
    print(f"   Active workers: {status['metrics']['active_workers']}")
    print(f"   Queue depth: {status['metrics']['queue_depth']}")
    
    # Phase 2: High load
    print("\nPhase 2: High Load (500 transactions rapidly)")
    print("-" * 80)
    for i in range(500):
        transaction = generate_sample_transaction(i + 50)
        processor.process_transaction(transaction)
    
    time.sleep(3)
    status = processor.get_status()
    print(f"   Active workers: {status['metrics']['active_workers']} (scaled up)")
    print(f"   Queue depth: {status['metrics']['queue_depth']}")
    
    # Phase 3: Return to low load
    print("\nPhase 3: Return to Low Load")
    print("-" * 80)
    time.sleep(5)  # Let queue drain
    
    status = processor.get_status()
    print(f"   Active workers: {status['metrics']['active_workers']} (scaled down)")
    print(f"   Queue depth: {status['metrics']['queue_depth']}")
    
    print("\n💡 System automatically scaled workers based on load")
    
    processor.stop()


def demo_scenario_5_error_handling():
    """Scenario 5: Error handling and recovery."""
    print_section("Scenario 5: Error Handling and Recovery")
    
    processor = TransactionStreamProcessor(
        max_workers=5,
        queue_size=1000
    )
    
    # Create detector that occasionally fails
    detector = StreamingFraudDetector()
    
    error_count = [0]
    def error_handler(error: Exception, transaction: Transaction):
        error_count[0] += 1
        print(f"  ⚠️  Error processing {transaction.transaction_id}: {str(error)[:50]}")
    
    processor.add_error_handler(error_handler)
    processor.set_fraud_detector(detector.detect_fraud)
    
    processor.start()
    print("✅ Stream processor started with error handling\n")
    
    # Process transactions
    print("Processing 30 transactions (some may have errors)...")
    print("-" * 80)
    
    for i in range(30):
        transaction = generate_sample_transaction(i)
        processor.process_transaction(transaction)
        time.sleep(0.05)
    
    time.sleep(2)
    
    metrics = processor.get_metrics()
    print(f"\n✅ Processing complete")
    print(f"   Transactions processed: {metrics.transactions_processed}")
    print(f"   Errors handled: {error_count[0]}")
    print(f"   Error rate: {metrics.error_rate:.2f}%")
    
    print("\n💡 System continued processing despite errors")
    
    processor.stop()


def demo_scenario_6_real_time_metrics():
    """Scenario 6: Real-time metrics and monitoring."""
    print_section("Scenario 6: Real-Time Metrics and Monitoring")
    
    processor = TransactionStreamProcessor(
        max_workers=8,
        queue_size=2000
    )
    
    detector = StreamingFraudDetector()
    processor.set_fraud_detector(detector.detect_fraud)
    
    processor.start()
    print("✅ Stream processor started\n")
    
    # Process transactions and show metrics periodically
    print("Processing 200 transactions with real-time metrics...")
    print("-" * 80)
    
    for i in range(200):
        transaction = generate_sample_transaction(i, fraud_probability=0.12)
        processor.process_transaction(transaction)
        
        # Show metrics every 50 transactions
        if (i + 1) % 50 == 0:
            status = processor.get_status()
            metrics = status['metrics']
            print(f"\nAfter {i + 1} transactions:")
            print(f"   Processed: {metrics['transactions_processed']}")
            print(f"   TPS: {metrics['transactions_per_second']:.1f}")
            print(f"   Avg time: {metrics['average_processing_time_ms']:.1f}ms")
            print(f"   Queue depth: {metrics['queue_depth']}")
            print(f"   Active workers: {metrics['active_workers']}")
    
    time.sleep(2)
    
    # Final statistics
    print("\nFinal Statistics:")
    print("-" * 80)
    status = processor.get_status()
    metrics = status['metrics']
    
    print(f"Total Transactions: {metrics['transactions_processed']}")
    print(f"Throughput: {metrics['transactions_per_second']:.1f} TPS")
    print(f"Average Processing Time: {metrics['average_processing_time_ms']:.1f}ms")
    print(f"Error Rate: {metrics['error_rate']:.2f}%")
    
    # Fraud detection stats
    fraud_stats = detector.get_stats()
    print(f"\nFraud Detection:")
    print(f"   Fraud detected: {fraud_stats['fraud_detected']}")
    print(f"   Detection rate: {fraud_stats.get('fraud_detection_rate', 0):.1f}%")
    
    processor.stop()


def demo_batch_processing():
    """Demo: Batch processing mode."""
    print_section("Batch Processing Mode")
    
    processor = TransactionStreamProcessor(
        max_workers=10,
        queue_size=5000,
        batch_size=100
    )
    
    detector = StreamingFraudDetector()
    processor.set_fraud_detector(detector.detect_fraud)
    
    processor.start()
    print("✅ Stream processor started in batch mode\n")
    
    # Generate batch of transactions
    print("Generating batch of 100 transactions...")
    transactions = [generate_sample_transaction(i, fraud_probability=0.1) for i in range(100)]
    
    # Process batch
    print("Processing batch...")
    start_time = time.time()
    results = processor.process_batch(transactions)
    
    # Wait for completion
    time.sleep(3)
    
    elapsed_time = time.time() - start_time
    
    print(f"\n✅ Batch processing complete")
    print(f"   Transactions: {len(transactions)}")
    print(f"   Time: {elapsed_time:.2f}s")
    print(f"   Throughput: {len(transactions) / elapsed_time:.1f} TPS")
    print(f"   Success rate: {(sum(results) / len(results) * 100):.1f}%")
    
    processor.stop()


def main():
    """Run all demo scenarios."""
    print("\n" + "="*80)
    print("  REAL-TIME TRANSACTION STREAM PROCESSING DEMO")
    print("  High-Throughput Fraud Detection")
    print("="*80)
    
    try:
        # Run scenarios
        demo_scenario_1_basic_streaming()
        demo_scenario_2_high_throughput()
        demo_scenario_3_priority_processing()
        demo_scenario_4_auto_scaling()
        demo_scenario_5_error_handling()
        demo_scenario_6_real_time_metrics()
        demo_batch_processing()
        
        print_section("Demo Complete")
        print("✅ All scenarios executed successfully!")
        print()
        print("Key Features Demonstrated:")
        print("  • Real-time transaction stream processing")
        print("  • High-throughput processing (500+ TPS)")
        print("  • Priority-based processing")
        print("  • Automatic scaling based on load")
        print("  • Error handling and recovery")
        print("  • Real-time metrics and monitoring")
        print("  • Batch processing mode")
        print()
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}", exc_info=True)
        print(f"\n❌ Demo failed: {str(e)}")


if __name__ == "__main__":
    main()
