# Real-Time Metrics Streaming - Quick Start Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install websockets
```

### 2. Start the Demo Server

```bash
python -m stress_testing.demo_realtime_streaming
```

This will:
- Start WebSocket server on `ws://localhost:8765`
- Generate mock metrics for 5 minutes
- Display connection instructions

### 3. Connect a Client

#### Option A: Use the HTML Test Client

Open `stress_testing/dashboards/websocket_test_client.html` in your browser.

#### Option B: Use JavaScript Console

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    console.log('Connected!');
    
    // Subscribe to all metrics
    ws.send(JSON.stringify({
        type: 'subscribe',
        metric_types: ['all']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data.type);
    
    if (data.type === 'metric_update') {
        console.log('Metric:', data.data.metric_type);
    }
};
```

#### Option C: Use Python

```python
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect('ws://localhost:8765') as ws:
        # Subscribe
        await ws.send(json.dumps({
            'type': 'subscribe',
            'metric_types': ['system', 'business']
        }))
        
        # Receive
        async for message in ws:
            data = json.loads(message)
            print(f"Received: {data['type']}")

asyncio.run(connect())
```

## 📊 Available Metric Types

- `system` - System metrics (throughput, latency, errors)
- `agent` - Agent metrics (performance, health)
- `business` - Business metrics (ROI, fraud detection)
- `hero` - Hero metrics (presentation)
- `presentation` - Full presentation data
- `all` - All metric types

## ⚙️ Client Commands

### Subscribe to Metrics

```json
{
  "type": "subscribe",
  "metric_types": ["system", "agent", "business"]
}
```

### Set Update Interval

```json
{
  "type": "set_update_interval",
  "interval_seconds": 2.0
}
```

### Filter by Agent IDs

```json
{
  "type": "set_filters",
  "filters": {
    "agent_ids": ["agent_1", "agent_2"]
  }
}
```

### Filter by Fields

```json
{
  "type": "set_filters",
  "filters": {
    "fields": ["throughput_tps", "error_rate"]
  }
}
```

### Ping Server

```json
{
  "type": "ping"
}
```

## 🔧 Integration Example

```python
import asyncio
from stress_testing.metrics import RealTimeMetricsStreamer, MetricsCollector
from stress_testing.models import SystemMetrics
from datetime import datetime

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
    print("WebSocket server started on ws://localhost:8765")
    
    # Create metrics collector
    collector = MetricsCollector()
    
    # Collect and broadcast metrics
    while True:
        # Collect metrics
        metrics = await collector.collect_all_metrics()
        
        # Broadcast to all connected clients
        await streamer.broadcast_system_metrics(metrics['system'])
        await streamer.broadcast_agent_metrics(metrics['agents'])
        await streamer.broadcast_business_metrics(metrics['business'])
        
        # Wait before next collection
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
```

## 📈 Monitoring

### Get Server Statistics

```python
stats = streamer.get_statistics()
print(f"Connected clients: {stats['connected_clients']}")
print(f"Total messages sent: {stats['total_messages_sent']}")
print(f"Uptime: {stats['uptime_seconds']} seconds")
```

### Check Client Connection

```python
if streamer.is_client_connected('client_1'):
    print("Client is connected")
```

### Get Client Count

```python
count = streamer.get_client_count()
print(f"Active clients: {count}")
```

## 🎯 Common Use Cases

### Dashboard Integration

```javascript
// Real-time dashboard updates
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'subscribe',
        metric_types: ['system', 'business']
    }));
    
    ws.send(JSON.stringify({
        type: 'set_update_interval',
        interval_seconds: 1
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'metric_update') {
        updateDashboard(data.data);
    }
};

function updateDashboard(metrics) {
    // Update your dashboard UI
    document.getElementById('throughput').textContent = 
        metrics.data.throughput_tps + ' TPS';
}
```

### Monitoring Specific Agents

```javascript
// Monitor only specific agents
ws.send(JSON.stringify({
    type: 'subscribe',
    metric_types: ['agent']
}));

ws.send(JSON.stringify({
    type: 'set_filters',
    filters: {
        agent_ids: ['agent_1', 'agent_2']
    }
}));
```

### Low-Bandwidth Client

```javascript
// Reduce update frequency and payload size
ws.send(JSON.stringify({
    type: 'set_update_interval',
    interval_seconds: 5
}));

ws.send(JSON.stringify({
    type: 'set_filters',
    filters: {
        fields: ['throughput_tps', 'error_rate']
    }
}));
```

## 🐛 Troubleshooting

### Connection Refused

```bash
# Check if server is running
netstat -an | grep 8765

# Start the server
python -m stress_testing.demo_realtime_streaming
```

### No Metrics Received

```javascript
// Ensure you're subscribed
ws.send(JSON.stringify({
    type: 'subscribe',
    metric_types: ['all']
}));
```

### High Latency

```python
# Reduce batch timeout
streamer = RealTimeMetricsStreamer(
    batch_timeout_seconds=0.1  # Flush more frequently
)
```

## 📚 More Information

- Full documentation: `stress_testing/metrics/README_REALTIME_STREAMING.md`
- Test suite: `stress_testing/metrics/test_realtime_metrics_streamer.py`
- Demo script: `stress_testing/demo_realtime_streaming.py`
- HTML client: `stress_testing/dashboards/websocket_test_client.html`

## 🎉 That's It!

You now have real-time metrics streaming up and running. Connect your dashboards, monitoring tools, or analytics applications to receive live updates with minimal latency.

For more advanced usage and configuration options, see the full documentation.
