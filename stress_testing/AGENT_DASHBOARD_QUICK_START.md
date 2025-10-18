# Enhanced Agent Dashboard - Quick Start Guide

## Overview

The enhanced agent dashboard provides comprehensive real-time monitoring of AI agents under stress testing conditions. It includes health indicators, workload distribution, coordination efficiency metrics, and workflow visualization.

## Features

### 🔥 Stress Test Metrics Section
- **Healthy Agents Count**: Number of agents with health score ≥ 80%
- **Average Load**: Current load across all agents
- **Average Response Time**: Mean response time under stress
- **Coordination Efficiency**: Success rate of agent coordination
- **Total Requests**: Cumulative requests processed

### 💚 Agent Health Indicators
- **Color-Coded Status**: Green (healthy), Orange (warning), Red (critical)
- **Pulsing Health Dots**: Animated indicators showing real-time status
- **Load Meters**: Visual horizontal bars with gradient colors
- **Response Time Indicators**: Performance classification (Fast/OK/Slow/Critical)
- **Alert Badges**: Contextual warnings for issues

### 📊 Workload Distribution
- **Dual-Axis Bar Chart**: Shows requests processed and current load per agent
- **Balance Score**: Indicates how evenly work is distributed
- **Real-Time Updates**: Chart updates every 5 seconds

### 🔄 Coordination Workflow
- **Visual Node Diagram**: Shows transaction flow through agents
- **Animated Arrows**: Data flow visualization between agents
- **Bottleneck Detection**: Automatically identifies slow agents
- **Timing Information**: Average response time per agent
- **Event Counts**: Number of coordination events per agent

### ⚡ Coordination Efficiency
- **Efficiency Score**: Combined metric of success rate and speed
- **Event Type Breakdown**: Detailed metrics by event type
- **Success Rate**: Percentage of completed events
- **Average Coordination Time**: Mean time for coordination steps

## Getting Started

### 1. Start the Dashboard Server

```bash
# From project root
python web_interface/dashboard_server.py
```

The server will start on `http://localhost:5000`

### 2. Open the Dashboard

Navigate to: `http://localhost:5000/agent_dashboard.html`

### 3. Run a Stress Test Simulation

In a separate terminal:

```bash
# Run the demo script
python stress_testing/demo_agent_dashboard.py

# Follow the prompts to start a live simulation
```

## API Endpoints

### Get Stress Test Metrics
```python
from web_interface.agent_dashboard_api import AgentDashboardAPI

api = AgentDashboardAPI()
metrics = api.get_stress_test_metrics()

# Returns:
# {
#     'timestamp': '2025-10-18T...',
#     'agents': [...],
#     'workload_distribution': {...},
#     'coordination_efficiency': {...},
#     'summary': {...}
# }
```

### Get Agent Performance Under Load
```python
perf = api.get_agent_performance_under_load('agent_id')

# Returns:
# {
#     'success': True,
#     'agent_id': 'agent_id',
#     'agent_name': 'Agent Name',
#     'current_metrics': {...},
#     'trends': {...},
#     'history': [...]
# }
```

### Get Workload Distribution Details
```python
workload = api.get_workload_distribution_details()

# Returns:
# {
#     'timestamp': '2025-10-18T...',
#     'distribution': [...],
#     'balance_metrics': {...}
# }
```

### Get Coordination Efficiency Metrics
```python
coord = api.get_coordination_efficiency_metrics()

# Returns:
# {
#     'timestamp': '2025-10-18T...',
#     'total_events': 100,
#     'completed_events': 95,
#     'overall_success_rate': 0.95,
#     'avg_coordination_time_ms': 150.5,
#     'efficiency_score': 0.92,
#     'event_types': {...}
# }
```

## Understanding the Metrics

### Health Score (0-1)
Calculated from:
- **Success Rate** (40%): Percentage of successful requests
- **Response Time** (30%): Inverse of response time (faster = better)
- **Load** (20%): Inverse of current load (lower = better)
- **Error Rate** (10%): Inverse of error rate

**Thresholds:**
- ≥ 0.9: Healthy (Green)
- 0.7-0.9: Warning (Orange)
- < 0.7: Critical (Red)

### Load Percentage (0-100%)
Current workload as percentage of capacity.

**Thresholds:**
- < 50%: Low (Green)
- 50-70%: Medium (Blue)
- 70-85%: High (Orange)
- > 85%: Critical (Red)

### Response Time Classification
- **⚡ Fast**: < 100ms
- **✓ OK**: 100-300ms
- **⚠ Slow**: 300-500ms
- **🔴 Critical**: > 500ms

### Coordination Efficiency Score (0-1)
Calculated from:
- **Success Rate** (70%): Percentage of completed events
- **Speed Score** (30%): Inverse of average duration (baseline: 500ms)

**Interpretation:**
- ≥ 0.9: Excellent
- 0.7-0.9: Good
- 0.5-0.7: Fair
- < 0.5: Poor

### Balance Score (0-1)
Measures how evenly work is distributed across agents.
- 1.0: Perfect balance
- 0.8-1.0: Well balanced
- 0.6-0.8: Moderately balanced
- < 0.6: Imbalanced (may need rebalancing)

## Alert Indicators

The dashboard automatically shows alerts for:

### High Error Count
- **Trigger**: Error count > 50
- **Type**: Error (Red)
- **Action**: Investigate error logs

### Excessive Load
- **Trigger**: Load > 85%
- **Type**: Error (Red)
- **Action**: Scale up or rebalance

### Elevated Load
- **Trigger**: Load > 70%
- **Type**: Info (Blue)
- **Action**: Monitor closely

### Slow Response Times
- **Trigger**: Response time > 500ms
- **Type**: Error (Red)
- **Action**: Optimize or scale

### Elevated Response Times
- **Trigger**: Response time > 300ms
- **Type**: Info (Blue)
- **Action**: Monitor performance

### Low Health Score
- **Trigger**: Health score < 0.7
- **Type**: Error (Red)
- **Action**: Investigate and remediate

## Bottleneck Detection

The workflow visualization automatically identifies bottlenecks:

### Detection Criteria
- Agent response time > 80% of maximum across all agents
- AND response time > 200ms

### Visual Indicators
- **⚠️ Warning**: Response time 200-400ms
- **⚠️ Critical**: Response time > 400ms

### Remediation
1. Check agent logs for errors
2. Verify resource availability (CPU, memory)
3. Consider scaling the agent
4. Optimize agent logic if needed

## Auto-Refresh

The dashboard auto-refreshes every 5 seconds by default.

**To disable:**
- Uncheck "Auto-refresh (5s)" checkbox

**To manually refresh:**
- Click "🔄 Refresh Dashboard" button

## Customization

### Adjust Refresh Interval
Edit `agent_dashboard.html`:
```javascript
// Change 5000 to desired milliseconds
autoRefreshInterval = setInterval(refreshDashboard, 5000);
```

### Modify Health Thresholds
Edit `agent_dashboard_api.py`:
```python
def _calculate_health_score(self, metrics: AgentMetrics) -> float:
    # Adjust weights
    success_weight = 0.4  # Default
    response_time_weight = 0.3  # Default
    load_weight = 0.2  # Default
    error_weight = 0.1  # Default
```

### Change Color Scheme
Edit CSS in `agent_dashboard.html`:
```css
.health-dot.healthy {
    background: #4caf50;  /* Green */
}
.health-dot.warning {
    background: #ff9800;  /* Orange */
}
.health-dot.critical {
    background: #f44336;  /* Red */
}
```

## Troubleshooting

### Dashboard Not Loading
1. Verify server is running: `http://localhost:5000`
2. Check console for JavaScript errors (F12)
3. Ensure Chart.js CDN is accessible

### No Data Showing
1. Verify agents are initialized in API
2. Run demo script to generate activity
3. Check browser console for errors

### Charts Not Rendering
1. Verify Chart.js is loaded (check Network tab)
2. Clear browser cache
3. Try different browser

### Slow Performance
1. Reduce auto-refresh interval
2. Limit history data points
3. Close other browser tabs

## Integration with Stress Testing

The agent dashboard integrates seamlessly with stress testing:

```python
from stress_testing.orchestrator.stress_test_orchestrator import StressTestOrchestrator
from web_interface.agent_dashboard_api import AgentDashboardAPI

# Initialize
api = AgentDashboardAPI()
orchestrator = StressTestOrchestrator(config)

# During stress test, update agent metrics
for agent_id, metrics in orchestrator.get_agent_metrics().items():
    api.update_agent_metrics(
        agent_id=agent_id,
        requests_processed=metrics.requests_processed,
        response_time_ms=metrics.avg_response_time_ms,
        success=metrics.success_rate > 0.95,
        load=metrics.current_load
    )
```

## Best Practices

1. **Monitor During Stress Tests**: Keep dashboard open during tests
2. **Watch for Bottlenecks**: Address bottlenecks immediately
3. **Track Trends**: Use performance history to identify degradation
4. **Set Alerts**: Configure alerts for critical thresholds
5. **Document Issues**: Screenshot alerts for post-mortem analysis
6. **Regular Reviews**: Review metrics after each test run

## Next Steps

1. **Explore Admin Dashboard**: For infrastructure metrics
2. **View Analytics Dashboard**: For fraud detection metrics
3. **Run Stress Tests**: Use orchestrator to generate load
4. **Customize Thresholds**: Adjust for your specific needs
5. **Export Data**: Implement export functionality for reports

## Support

For issues or questions:
1. Check `TASK_7_COMPLETION_SUMMARY.md` for implementation details
2. Review `demo_agent_dashboard.py` for usage examples
3. Consult `agent_dashboard_api.py` for API documentation

---

**Last Updated**: 2025-10-18  
**Version**: 1.0.0  
**Status**: Production Ready
