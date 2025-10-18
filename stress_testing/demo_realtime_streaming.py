"""
Demo: Real-Time Metrics Streaming

This demo showcases the real-time metrics streaming capabilities:
- WebSocket server for metric broadcasting
- Metric update batching for efficiency
- Client subscription management
- Metric filtering based on client preferences

Usage:
    python -m stress_testing.demo_realtime_streaming
"""

import asyncio
import logging
from datetime import datetime
import random

from stress_testing.models import SystemMetrics, AgentMetrics, BusinessMetrics
from stress_testing.metrics import RealTimeMetricsStreamer, MetricType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_mock_metrics(streamer: RealTimeMetricsStreamer, duration_seconds: int = 60):
    """
    Generate and broadcast mock metrics for demonstration.
    
    Args:
        streamer: RealTimeMetricsStreamer instance
        duration_seconds: How long to generate metrics
    """
    logger.info(f"Starting mock metrics generation for {duration_seconds} seconds")
    
    start_time = asyncio.get_event_loop().time()
    iteration = 0
    
    while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
        iteration += 1
        
        # Generate system metrics
        system_metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            throughput_tps=random.uniform(800, 1200),
            requests_total=iteration * 1000,
            requests_successful=int(iteration * 1000 * 0.99),
            requests_failed=int(iteration * 1000 * 0.01),
            avg_response_time_ms=random.uniform(100, 200),
            p50_response_time_ms=random.uniform(80, 120),
            p95_response_time_ms=random.uniform(200, 300),
            p99_response_time_ms=random.uniform(400, 600),
            max_response_time_ms=random.uniform(800, 1200),
            error_rate=random.uniform(0.005, 0.015),
            timeout_rate=random.uniform(0.001, 0.005),
            cpu_utilization=random.uniform(0.6, 0.8),
            memory_utilization=random.uniform(0.5, 0.7),
            network_throughput_mbps=random.uniform(80, 120)
        )
        
        await streamer.broadcast_system_metrics(system_metrics)
        
        # Generate agent metrics
        agent_metrics = []
        agent_names = ["Transaction Analyzer", "Pattern Detector", "Risk Assessor", "Decision Maker"]
        
        for i, name in enumerate(agent_names):
            agent_metric = AgentMetrics(
                agent_id=f"agent_{i+1}",
                agent_name=name,
                timestamp=datetime.utcnow(),
                requests_processed=random.randint(900, 1100),
                avg_response_time_ms=random.uniform(100, 200),
                p95_response_time_ms=random.uniform(250, 350),
                p99_response_time_ms=random.uniform(450, 550),
                success_rate=random.uniform(0.97, 0.99),
                error_count=random.randint(5, 15),
                timeout_count=random.randint(0, 5),
                current_load=random.uniform(0.6, 0.85),
                concurrent_requests=random.randint(15, 25),
                health_score=random.uniform(0.92, 0.98),
                status="healthy" if random.random() > 0.1 else "degraded",
                decision_accuracy=random.uniform(0.93, 0.97),
                false_positive_rate=random.uniform(0.01, 0.03),
                false_negative_rate=random.uniform(0.005, 0.015)
            )
            agent_metrics.append(agent_metric)
        
        await streamer.broadcast_agent_metrics(agent_metrics)
        
        # Generate business metrics
        business_metrics = BusinessMetrics(
            timestamp=datetime.utcnow(),
            transactions_processed=iteration * 1000,
            transactions_per_second=random.uniform(900, 1100),
            fraud_detected=int(iteration * 20),
            fraud_prevented_amount=iteration * 2500.0,
            fraud_detection_rate=0.02,
            fraud_detection_accuracy=random.uniform(0.93, 0.97),
            cost_per_transaction=random.uniform(0.018, 0.022),
            total_cost=iteration * 20.0,
            roi_percentage=random.uniform(140, 160),
            money_saved=iteration * 5000.0,
            payback_period_months=random.uniform(5.5, 6.5),
            customer_impact_score=random.uniform(0.92, 0.96),
            false_positive_impact=random.uniform(0.015, 0.025),
            performance_vs_baseline=random.uniform(1.4, 1.6),
            cost_vs_baseline=random.uniform(0.45, 0.55)
        )
        
        await streamer.broadcast_business_metrics(business_metrics)
        
        # Log progress
        if iteration % 10 == 0:
            stats = streamer.get_statistics()
            logger.info(
                f"Iteration {iteration}: "
                f"Clients={stats['connected_clients']}, "
                f"Messages={stats['total_messages_sent']}, "
                f"Queue={stats['metrics_queue_size']}"
            )
        
        # Wait before next iteration
        await asyncio.sleep(1)
    
    logger.info("Mock metrics generation completed")


async def print_connection_instructions():
    """Print instructions for connecting to the WebSocket server."""
    print("\n" + "="*80)
    print("🚀 Real-Time Metrics Streaming Server Started")
    print("="*80)
    print("\nWebSocket Server: ws://localhost:8765")
    print("\n📡 Connection Instructions:")
    print("\n1. Using JavaScript (Browser Console or Node.js):")
    print("   ```javascript")
    print("   const ws = new WebSocket('ws://localhost:8765');")
    print("   ")
    print("   ws.onopen = () => {")
    print("     console.log('Connected to metrics stream');")
    print("     ")
    print("     // Subscribe to specific metrics")
    print("     ws.send(JSON.stringify({")
    print("       type: 'subscribe',")
    print("       metric_types: ['system', 'agent', 'business']")
    print("     }));")
    print("     ")
    print("     // Set update interval (seconds)")
    print("     ws.send(JSON.stringify({")
    print("       type: 'set_update_interval',")
    print("       interval_seconds: 2")
    print("     }));")
    print("     ")
    print("     // Set filters")
    print("     ws.send(JSON.stringify({")
    print("       type: 'set_filters',")
    print("       filters: {")
    print("         agent_ids: ['agent_1', 'agent_2']")
    print("       }")
    print("     }));")
    print("   };")
    print("   ")
    print("   ws.onmessage = (event) => {")
    print("     const data = JSON.parse(event.data);")
    print("     console.log('Received:', data);")
    print("   };")
    print("   ```")
    print("\n2. Using Python (websockets library):")
    print("   ```python")
    print("   import asyncio")
    print("   import websockets")
    print("   import json")
    print("   ")
    print("   async def connect():")
    print("       async with websockets.connect('ws://localhost:8765') as ws:")
    print("           # Subscribe to metrics")
    print("           await ws.send(json.dumps({")
    print("               'type': 'subscribe',")
    print("               'metric_types': ['system', 'business']")
    print("           }))")
    print("           ")
    print("           # Receive messages")
    print("           async for message in ws:")
    print("               data = json.loads(message)")
    print("               print(f'Received: {data['type']}')")
    print("   ")
    print("   asyncio.run(connect())")
    print("   ```")
    print("\n3. Using curl (for testing):")
    print("   ```bash")
    print("   # Install websocat: https://github.com/vi/websocat")
    print("   websocat ws://localhost:8765")
    print("   ```")
    print("\n📊 Available Message Types:")
    print("   - welcome: Initial connection message")
    print("   - metric_update: Single metric update")
    print("   - metric_batch: Batched metric updates")
    print("   - subscription_confirmed: Subscription confirmation")
    print("   - filters_updated: Filter update confirmation")
    print("\n🎯 Available Metric Types:")
    print("   - system: System-level metrics (throughput, latency, errors)")
    print("   - agent: Agent-specific metrics (performance, health)")
    print("   - business: Business value metrics (ROI, fraud detection)")
    print("   - hero: Hero metrics for presentation")
    print("   - presentation: Full presentation data")
    print("   - all: Subscribe to all metric types")
    print("\n⚙️  Client Commands:")
    print("   - subscribe: Subscribe to metric types")
    print("   - unsubscribe: Unsubscribe from metric types")
    print("   - set_filters: Set data filters")
    print("   - set_update_interval: Set update frequency")
    print("   - ping: Ping server (responds with pong)")
    print("\n" + "="*80)
    print("Press Ctrl+C to stop the server")
    print("="*80 + "\n")


async def main():
    """Main demo function."""
    logger.info("Starting Real-Time Metrics Streaming Demo")
    
    # Create streamer
    streamer = RealTimeMetricsStreamer(
        host="0.0.0.0",
        port=8765,
        batch_size=5,
        batch_timeout_seconds=0.5
    )
    
    try:
        # Start WebSocket server
        await streamer.start()
        
        # Print connection instructions
        await print_connection_instructions()
        
        # Generate mock metrics
        await generate_mock_metrics(streamer, duration_seconds=300)  # 5 minutes
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
    finally:
        # Stop server
        logger.info("Stopping WebSocket server...")
        await streamer.stop()
        
        # Print final statistics
        stats = streamer.get_statistics()
        print("\n" + "="*80)
        print("📊 Final Statistics")
        print("="*80)
        print(f"Total Clients Connected: {stats['total_clients_connected']}")
        print(f"Total Messages Sent: {stats['total_messages_sent']}")
        print(f"Uptime: {stats['uptime_seconds']:.1f} seconds")
        print("="*80 + "\n")
        
        logger.info("Demo completed")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
