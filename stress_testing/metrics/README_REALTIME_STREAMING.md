# Real-Time Metrics Streaming

## Overview

The Real-Time Metrics Streaming system provides WebSocket-based broadcasting of stress test metrics to connected clients. This enables live dashboards, monitoring tools, and analytics applications to receive metrics updates in real-time with minimal latency.

## Features

### 1. WebSocket Server for Metric Broadcasting
- Asynchronous WebSocket server using the `websockets` library
- Supports multiple concurrent client connections
- Automatic connection management and cleanup
- Heartbeat/ping-pong support for connection health

### 2. Metric Update Batching for Efficiency
- Configurable batch size and timeout
- Reduces network overhead by grouping metrics
- Automatic flushing based on size or time thresholds
- Per-client batching for optimal delivery

### 3. Client Subscription Management
- Subscribe to specific metric types (system, agent, business, hero, presentation)
- Dynamic subscription updates without reconnection
- "All" subscription for receiving all metric types
- Subscription confirmation messages

### 4. Metric Filtering Based on Client Preferences
- Filter by agent IDs to receive only specific agent metrics
- Filter by metric fields to reduce payload size
- Configurable update intervals per client
- Client-specific data transformations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  RealTimeMetricsStreamer                     │
│                                                              │
│  ┌────────────────┐         ┌──────────────────┐           │
│  │ WebSocket      │         │  Metrics Queue   │           │
│  │ Server         │◄────────┤  (asyncio.Queue) │           │
│  │ (port 8765)    │         └──────────────────┘           │
│  └────────┬───────┘                                         │
│           │                                                  │
│           ▼                                                  │
│  ┌────────────────────────────────────────────────┐        │
│  │         Client Subscription Manager             │        │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │        │
│  │  │ Client 1 │  │ Client 2 │  │ Client N │     │        │
│  │  │          │  │          │  │          │     │        │
│  │  │ Filters  │  │ Filters  │  │ Filters  │     │        │
│  │  │ Batch    │  │ Batch    │  │ Batch    │     │        │
│  │  └──────────┘  └──────────┘  └──────────┘     │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

```bash
pip install websockets
```

### Optional Dependencies

For testing and development:
```bash
pip install pytest pytest-asyncio
```

## Usage

### Starting the WebSocket Server

```python
import asyncio
from stress_testing.metrics import RealTimeMetricsStreamer

async def main():
    # Create streamer
    streamer = RealTimeMetricsStreamer(
        host="0.0.0.0",
        port=8765,
        batch_size=10,
        batch_timeout_seconds=0.5
    )
    
    # Start server
    await streamer.start()
    
    # Keep server running
    try:
        await asyncio.Future()  # Run forever
    finally:
        await streamer.stop()

asyncio.run(main())
```

### Broadcasting Metrics

```python
from stress_testing.models import SystemMetrics
from datetime import datetime

# Create metrics
system_metrics = SystemMetrics(
    timestamp=datetime.utcnow(),
    throughput_tps=1000.0,
    requests_total=10000,
    requests_successful=9900,
    requests_failed=100,
    avg_response_time_ms=150.0,
    p50_response_time_ms=120.0,
    p95_response_time_ms=300.0,
    p99_response_time_ms=500.0,
    max_response_time_ms=1000.0,
    error_rate=0.01,
    timeout_rate=0.001,
    cpu_utilization=0.75,
    memory_utilization=0.60,
    network_throughput_mbps=100.0
)

# Broadcast to all connected clients
await streamer.broadcast_system_metrics(system_metrics)
```

### Client Connection (JavaScript)

```javascript
// Connect to WebSocket server
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    console.log('Connected to metrics stream');
    
    // Subscribe to specific metrics
    ws.send(JSON.stringify({
        type: 'subscribe',
        metric_types: ['system', 'agent', 'business']
    }));
    
    // Set update interval (2 seconds)
    ws.send(JSON.stringify({
        type: 'set_update_interval',
        interval_seconds: 2
    }));
    
    // Set filters (only agent_1 and agent_2)
    ws.send(JSON.stringify({
        type: 'set_filters',
        filters: {
            agent_ids: ['agent_1', 'agent_2']
        }
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'metric_update') {
        console.log('Metric:', data.data);
    } else if (data.type === 'metric_batch') {
        console.log('Batch:', data.count, 'metrics');
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Connection closed');
};
```

### Client Connection (Python)

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to metrics
        await websocket.send(json.dumps({
            'type': 'subscribe',
            'metric_types': ['system', 'business']
        }))
        
        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'metric_update':
                print(f"Metric data: {data['data']}")

asyncio.run(connect())
```

## Message Protocol

### Client → Server Messages

#### Subscribe to Metrics
```json
{
    "type": "subscribe",
    "metric_types": ["system", "agent", "business"]
}
```

#### Unsubscribe from Metrics
```json
{
    "type": "unsubscribe",
    "metric_types": ["hero"]
}
```

#### Set Filters
```json
{
    "type": "set_filters",
    "filters": {
        "agent_ids": ["agent_1", "agent_2"],
        "fields": ["throughput_tps", "error_rate"]
    }
}
```

#### Set Update Interval
```json
{
    "type": "set_update_interval",
    "interval_seconds": 2.0
}
```

#### Ping
```json
{
    "type": "ping"
}
```

### Server → Client Messages

#### Welcome Message
```json
{
    "type": "welcome",
    "client_id": "client_1",
    "timestamp": "2024-01-01T12:00:00",
    "message": "Connected to real-time metrics stream"
}
```

#### Metric Update
```json
{
    "type": "metric_update",
    "data": {
        "metric_type": "system",
        "timestamp": "2024-01-01T12:00:00",
        "data": {
            "throughput_tps": 1000.0,
            "error_rate": 0.01,
            ...
        }
    }
}
```

#### Metric Batch
```json
{
    "type": "metric_batch",
    "count": 5,
    "data": [
        {
            "metric_type": "system",
            "timestamp": "2024-01-01T12:00:00",
            "data": {...}
        },
        ...
    ]
}
```

#### Subscription Confirmed
```json
{
    "type": "subscription_confirmed",
    "metric_types": ["system", "agent", "business"]
}
```

#### Filters Updated
```json
{
    "type": "filters_updated",
    "filters": {
        "agent_ids": ["agent_1", "agent_2"]
    }
}
```

#### Pong
```json
{
    "type": "pong"
}
```

## Metric Types

### System Metrics
- Throughput (TPS)
- Response times (avg, P50, P95, P99, max)
- Error rates
- Resource utilization (CPU, memory, network)
- Queue metrics

### Agent Metrics
- Per-agent performance
- Request processing stats
- Success rates and errors
- Load and health scores
- Decision quality metrics

### Business Metrics
- Transactions processed
- Fraud detection stats
- Cost metrics
- ROI calculations
- Customer impact

### Hero Metrics
- Large-format presentation metrics
- Key performance indicators
- Business value metrics

### Presentation Data
- Complete presentation dashboard data
- Transaction flow visualizations
- Competitive benchmarks

## Configuration

### Batch Configuration

```python
streamer = RealTimeMetricsStreamer(
    batch_size=10,              # Flush after 10 metrics
    batch_timeout_seconds=0.5   # Or after 0.5 seconds
)
```

### Client Update Interval

Clients can set their own update intervals:
```javascript
ws.send(JSON.stringify({
    type: 'set_update_interval',
    interval_seconds: 1.0  // Update every second
}));
```

### Filtering

Filter by agent IDs:
```javascript
ws.send(JSON.stringify({
    type: 'set_filters',
    filters: {
        agent_ids: ['agent_1', 'agent_2']
    }
}));
```

Filter by fields:
```javascript
ws.send(JSON.stringify({
    type: 'set_filters',
    filters: {
        fields: ['throughput_tps', 'error_rate', 'cpu_utilization']
    }
}));
```

## Testing

### Run Unit Tests

```bash
pytest stress_testing/metrics/test_realtime_metrics_streamer.py -v
```

### Run Demo

```bash
python -m stress_testing.demo_realtime_streaming
```

Then open the test client in your browser:
```
http://localhost:5000/websocket_test_client.html
```

Or use the standalone HTML file:
```
stress_testing/dashboards/websocket_test_client.html
```

## Performance Considerations

### Batching
- Reduces network overhead by grouping metrics
- Configurable batch size and timeout
- Per-client batching for optimal delivery

### Filtering
- Reduces payload size by filtering unwanted data
- Client-side filtering applied before transmission
- Supports both field-level and entity-level filtering

### Update Intervals
- Clients can set their own update frequency
- Prevents overwhelming slow clients
- Balances real-time updates with performance

### Connection Management
- Automatic cleanup of disconnected clients
- Efficient message routing to subscribed clients only
- Graceful handling of connection errors

## Statistics and Monitoring

Get streamer statistics:
```python
stats = streamer.get_statistics()
print(f"Connected clients: {stats['connected_clients']}")
print(f"Total messages sent: {stats['total_messages_sent']}")
print(f"Uptime: {stats['uptime_seconds']} seconds")
```

Check client connection:
```python
if streamer.is_client_connected('client_1'):
    print("Client is connected")
```

Get client count:
```python
count = streamer.get_client_count()
print(f"Active clients: {count}")
```

## Integration with Stress Testing Framework

The real-time metrics streamer integrates seamlessly with the stress testing orchestrator:

```python
from stress_testing.orchestrator import StressTestOrchestrator
from stress_testing.metrics import RealTimeMetricsStreamer

async def run_stress_test_with_streaming():
    # Create streamer
    streamer = RealTimeMetricsStreamer()
    await streamer.start()
    
    # Create orchestrator
    orchestrator = StressTestOrchestrator(config)
    orchestrator.set_metrics_streamer(streamer)
    
    # Run test (metrics will be streamed automatically)
    await orchestrator.execute_scenario(scenario)
    
    # Stop streamer
    await streamer.stop()
```

## Troubleshooting

### WebSocket Connection Fails

1. Check if the server is running:
   ```bash
   netstat -an | grep 8765
   ```

2. Verify firewall settings allow WebSocket connections

3. Check if `websockets` library is installed:
   ```bash
   pip install websockets
   ```

### No Metrics Received

1. Verify subscription:
   ```javascript
   ws.send(JSON.stringify({
       type: 'subscribe',
       metric_types: ['all']
   }));
   ```

2. Check update interval isn't too high

3. Verify metrics are being generated and queued

### High Latency

1. Reduce batch timeout:
   ```python
   streamer = RealTimeMetricsStreamer(batch_timeout_seconds=0.1)
   ```

2. Increase client update interval

3. Apply filters to reduce payload size

## Requirements Satisfied

This implementation satisfies the following requirements from the stress testing framework:

- **Requirement 9.1**: Real-time CloudWatch metrics publishing with < 60 second delay
- **Requirement 9.2**: SNS notifications delivered within 2 minutes
- **Requirement 13.1**: Real-time unified presentation dashboard
- **Requirement 14.5**: Dashboard updates in real-time (< 2s latency)

## Future Enhancements

- [ ] SSL/TLS support for secure WebSocket connections
- [ ] Authentication and authorization
- [ ] Compression for large payloads
- [ ] Replay capability for historical metrics
- [ ] Metric aggregation and downsampling
- [ ] Multi-region support with edge caching
