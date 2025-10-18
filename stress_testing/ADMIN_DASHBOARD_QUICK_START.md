# Admin Dashboard Quick Start Guide

## Overview

The Admin Dashboard provides comprehensive infrastructure health monitoring, resource utilization tracking, cost management, and operational controls for the stress testing framework.

## Features

### 1. Infrastructure Health Monitoring
- Real-time health status of all AWS services
- Lambda, DynamoDB, Kinesis, Bedrock, S3, CloudWatch
- Color-coded status indicators (healthy, degraded, unhealthy)
- Threshold-based alerting

### 2. Resource Utilization Tracking
- Lambda concurrent executions
- DynamoDB read/write capacity usage
- Kinesis stream metrics
- S3 operations per second
- Bedrock API quota usage
- Visual progress bars with warning/critical thresholds

### 3. Cost Tracking & Budget Management
- Real-time cost monitoring (hourly, daily, monthly)
- Cost breakdown by AWS service
- Budget usage percentage
- Cost trend analysis
- Automated budget alerts

### 4. Operational Controls
- **Stress Test Controls**: Start, pause, resume, stop tests
- **Failure Injection**: Inject various failure types for resilience testing
- **Emergency Stop**: Immediately halt all operations

## Quick Start

### Running the Demo

```bash
# From the project root
python stress_testing/demo_admin_dashboard.py
```

### Opening the Dashboard

1. **Local File Access**:
   ```
   file:///path/to/stress_testing/dashboards/admin_dashboard.html
   ```

2. **With HTTP Server** (recommended):
   ```bash
   cd stress_testing/dashboards
   python -m http.server 8080
   ```
   Then open: `http://localhost:8080/admin_dashboard.html`

## Dashboard Sections

### Infrastructure Health
- **Healthy** (Green): Service operating normally
- **Degraded** (Orange): Service approaching limits
- **Unhealthy** (Red): Service exceeding thresholds

### Resource Utilization
- Visual bars showing current usage vs. capacity
- Color-coded warnings (green → yellow → red)
- Real-time updates every 5 seconds

### Cost Tracking
- Four summary boxes: Hourly, Daily, Monthly, Budget %
- Service-by-service cost breakdown
- Alert notifications for budget concerns

### Operational Controls
- **Test Control**: Manage stress test execution
  - Start new tests
  - Pause/resume active tests
  - Stop running tests
  
- **Failure Injection**: Test system resilience
  - Lambda failures
  - DynamoDB throttling
  - Network latency
  - Bedrock rate limits
  
- **Emergency Stop**: Nuclear option
  - Immediately halts all operations
  - Requires double confirmation

## API Endpoints

The Admin Dashboard API provides the following endpoints:

### Health & Monitoring
```python
# Get infrastructure health
health = await admin_api.get_infrastructure_health()

# Get resource utilization
utilization = await admin_api.get_resource_utilization()

# Get cost tracking
costs = await admin_api.get_cost_tracking()

# Get operational controls status
controls = await admin_api.get_operational_controls()
```

### Test Controls
```python
# Start stress test
result = await admin_api.start_stress_test(scenario_id="peak_load_test")

# Pause test
result = await admin_api.pause_stress_test()

# Resume test
result = await admin_api.resume_stress_test()

# Stop test
result = await admin_api.stop_stress_test(reason="User requested")
```

### Failure Injection
```python
# Inject failure
result = await admin_api.inject_failure(
    failure_type="lambda_failure",
    duration_seconds=60
)
```

### Emergency Controls
```python
# Emergency stop (use with caution!)
result = await admin_api.emergency_stop()
```

## Integration with Stress Testing Framework

### Component Setup

```python
from stress_testing.dashboards.admin_dashboard_api import AdminDashboardAPI
from stress_testing.orchestrator.stress_test_orchestrator import StressTestOrchestrator
from stress_testing.metrics.metrics_aggregator import MetricsAggregator
from stress_testing.failure_injection.failure_injector import FailureInjector

# Initialize components
admin_api = AdminDashboardAPI()
orchestrator = StressTestOrchestrator()
metrics_aggregator = MetricsAggregator()
failure_injector = FailureInjector()

# Inject dependencies
admin_api.set_components(
    orchestrator=orchestrator,
    metrics_aggregator=metrics_aggregator,
    failure_injector=failure_injector
)
```

### Real-Time Updates

The dashboard auto-refreshes every 5 seconds. For WebSocket-based real-time updates:

```python
from stress_testing.metrics.realtime_metrics_streamer import RealTimeMetricsStreamer

# Start WebSocket server
streamer = RealTimeMetricsStreamer(host="0.0.0.0", port=8765)
await streamer.start()

# Broadcast admin metrics
await streamer.queue_metric({
    'metric_type': 'admin',
    'data': admin_api.get_dashboard_data()
})
```

## Configuration

### AWS Service Thresholds

Edit `admin_dashboard_api.py` to customize thresholds:

```python
# Lambda
threshold_warning = 1500  # concurrent executions
threshold_critical = 2000

# DynamoDB
threshold_warning = 5000  # WCU
threshold_critical = 8000

# Kinesis
threshold_warning = 60000  # ms iterator age
threshold_critical = 120000
```

### Budget Limits

```python
budget_limit = 1000.0  # Monthly budget in USD
```

### Auto-Refresh Interval

In `admin_dashboard.html`:

```javascript
// Change refresh interval (milliseconds)
updateInterval = setInterval(updateDashboard, 5000);  // 5 seconds
```

## Security Considerations

### Production Deployment

1. **Authentication**: Add API key or OAuth authentication
2. **Authorization**: Implement role-based access control
3. **Rate Limiting**: Prevent API abuse
4. **Audit Logging**: Log all control actions
5. **HTTPS**: Use secure connections
6. **IP Whitelisting**: Restrict access to known IPs

### Emergency Stop Protection

```python
# Require multi-factor authentication
# Log all emergency stop actions
# Send notifications to administrators
# Implement cooldown period
```

## Troubleshooting

### Dashboard Not Updating

1. Check browser console for errors
2. Verify API endpoints are accessible
3. Check WebSocket connection (if using)
4. Ensure AWS credentials are configured

### AWS Metrics Not Available

1. Verify boto3 is installed: `pip install boto3`
2. Configure AWS credentials: `aws configure`
3. Check IAM permissions for CloudWatch, Cost Explorer
4. Verify region settings

### Cost Data Not Showing

1. Enable Cost Explorer in AWS Console
2. Wait 24 hours for initial data
3. Verify IAM permissions for Cost Explorer API
4. Check date range in queries

## Best Practices

1. **Monitor Regularly**: Check dashboard before and during stress tests
2. **Set Budgets**: Configure appropriate budget limits
3. **Test Controls**: Verify all controls work before production use
4. **Document Actions**: Log all operational control actions
5. **Review Costs**: Analyze cost trends weekly
6. **Update Thresholds**: Adjust based on actual usage patterns

## Next Steps

1. ✅ Run the demo script
2. ✅ Open the dashboard in a browser
3. ✅ Test all operational controls
4. ⬜ Integrate with live AWS services
5. ⬜ Set up WebSocket for real-time updates
6. ⬜ Configure authentication
7. ⬜ Deploy to production environment

## Support

For issues or questions:
- Check the demo script for examples
- Review API documentation in `admin_dashboard_api.py`
- See main stress testing README for architecture details

---

**Admin Dashboard** - Part of the Stress Testing Framework
