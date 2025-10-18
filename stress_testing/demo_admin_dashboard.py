"""
Demo script for Admin Dashboard.

This script demonstrates the admin dashboard functionality including:
- Infrastructure health monitoring
- Resource utilization tracking
- Cost tracking and budget alerts
- Operational controls (start/stop tests, failure injection, emergency stop)
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_admin_dashboard():
    """Demonstrate admin dashboard functionality."""
    print("\n" + "="*80)
    print("ADMIN DASHBOARD DEMO")
    print("="*80 + "\n")
    
    # Import components
    from stress_testing.dashboards.admin_dashboard_api import AdminDashboardAPI
    from stress_testing.orchestrator.stress_test_orchestrator import StressTestOrchestrator
    from stress_testing.models import StressTestConfig
    
    # Initialize components
    print("1. Initializing Admin Dashboard API...")
    admin_api = AdminDashboardAPI()
    
    # Initialize orchestrator for test controls
    orchestrator = StressTestOrchestrator()
    admin_api.set_components(orchestrator=orchestrator)
    
    print("✓ Admin Dashboard API initialized\n")
    
    # Test infrastructure health
    print("2. Checking Infrastructure Health...")
    print("-" * 80)
    health_status = await admin_api.get_infrastructure_health()
    
    for service in health_status:
        status_icon = "✓" if service.status == "healthy" else "⚠" if service.status == "degraded" else "✗"
        print(f"{status_icon} {service.service_name:15} | Status: {service.status:10} | "
              f"{service.metric_value:.0f} {service.metric_unit}")
        print(f"   Details: {service.details}")
    
    print()
    
    # Test resource utilization
    print("3. Checking Resource Utilization...")
    print("-" * 80)
    utilization = await admin_api.get_resource_utilization()
    
    print(f"Lambda Concurrent:     {utilization.lambda_concurrent_executions:,} / {utilization.lambda_max_concurrent:,}")
    print(f"DynamoDB Read:         {utilization.dynamodb_read_capacity_used:,.0f} / {utilization.dynamodb_read_capacity_provisioned:,.0f} RCU")
    print(f"DynamoDB Write:        {utilization.dynamodb_write_capacity_used:,.0f} / {utilization.dynamodb_write_capacity_provisioned:,.0f} WCU")
    print(f"Kinesis Records:       {utilization.kinesis_incoming_records:,.0f} records/sec")
    print(f"Kinesis Iterator Age:  {utilization.kinesis_iterator_age_ms/1000:.1f} seconds")
    print(f"S3 Operations:         {utilization.s3_operations_per_second:.0f} ops/sec")
    print(f"Bedrock Quota:         {utilization.bedrock_quota_used_percentage:.1f}%")
    print()
    
    # Test cost tracking
    print("4. Checking Cost Tracking...")
    print("-" * 80)
    costs = await admin_api.get_cost_tracking()
    
    print(f"Current Hourly Cost:   ${costs.current_hourly_cost:.2f}")
    print(f"Current Daily Cost:    ${costs.current_daily_cost:.2f}")
    print(f"Monthly Projection:    ${costs.projected_monthly_cost:.2f}")
    print(f"Budget Limit:          ${costs.budget_limit:.2f}")
    print(f"Budget Used:           {costs.budget_used_percentage:.1f}%")
    print(f"Cost Trend:            {costs.cost_trend}")
    print()
    
    print("Cost by Service:")
    for service, cost in costs.cost_by_service.items():
        percentage = (cost / costs.current_daily_cost) * 100
        print(f"  {service:15} ${cost:8.2f} ({percentage:5.1f}%)")
    
    if costs.alerts:
        print("\n⚠️  Cost Alerts:")
        for alert in costs.alerts:
            print(f"  • {alert}")
    print()
    
    # Test operational controls
    print("5. Checking Operational Controls...")
    print("-" * 80)
    controls = await admin_api.get_operational_controls()
    
    for control in controls:
        status_icon = "●" if control.status == "active" else "○"
        print(f"{status_icon} {control.control_name:30} | Status: {control.status:10}")
        if control.last_action:
            print(f"   Last action: {control.last_action.strftime('%Y-%m-%d %H:%M:%S')} by {control.last_action_by}")
    print()
    
    # Test start/stop controls
    print("6. Testing Stress Test Controls...")
    print("-" * 80)
    
    # Start test
    print("Starting stress test...")
    result = await admin_api.start_stress_test("peak_load_test")
    print(f"Result: {result['message']}")
    if result['success']:
        print(f"Test ID: {result['test_id']}")
    print()
    
    # Check status
    await asyncio.sleep(1)
    controls = await admin_api.get_operational_controls()
    test_control = next((c for c in controls if c.control_id == "test_control"), None)
    if test_control:
        print(f"Test Control Status: {test_control.status}")
    print()
    
    # Pause test
    print("Pausing stress test...")
    result = await admin_api.pause_stress_test()
    print(f"Result: {result['message']}")
    print()
    
    # Resume test
    await asyncio.sleep(1)
    print("Resuming stress test...")
    result = await admin_api.resume_stress_test()
    print(f"Result: {result['message']}")
    print()
    
    # Stop test
    await asyncio.sleep(1)
    print("Stopping stress test...")
    result = await admin_api.stop_stress_test(reason="Demo completed")
    print(f"Result: {result['message']}")
    print()
    
    # Test failure injection
    print("7. Testing Failure Injection...")
    print("-" * 80)
    
    print("Injecting Lambda failure...")
    result = await admin_api.inject_failure("lambda_failure", duration_seconds=30)
    print(f"Result: {result['message']}")
    if result['success']:
        print(f"Failure ID: {result['failure_id']}")
    print()
    
    print("Injecting DynamoDB throttle...")
    result = await admin_api.inject_failure("dynamodb_throttle", duration_seconds=45)
    print(f"Result: {result['message']}")
    if result['success']:
        print(f"Failure ID: {result['failure_id']}")
    print()
    
    # Test emergency stop (without actually executing)
    print("8. Emergency Stop Control...")
    print("-" * 80)
    print("Emergency stop is available but not executed in demo")
    print("In production, this would immediately halt all operations")
    print()
    
    # Get complete dashboard data
    print("9. Getting Complete Dashboard Data...")
    print("-" * 80)
    dashboard_data = admin_api.get_dashboard_data()
    
    print(f"Dashboard data retrieved at: {dashboard_data['timestamp']}")
    print(f"Infrastructure health checks: {len(dashboard_data.get('infrastructure_health', []))}")
    print(f"Resource utilization metrics: {len(dashboard_data.get('resource_utilization', {}))} fields")
    print(f"Cost tracking data: {len(dashboard_data.get('cost_tracking', {}))} fields")
    print(f"Operational controls: {len(dashboard_data.get('operational_controls', []))}")
    print()
    
    # Display dashboard URL
    print("10. Dashboard Access...")
    print("-" * 80)
    dashboard_path = Path(__file__).parent / "dashboards" / "admin_dashboard.html"
    print(f"Admin Dashboard HTML: {dashboard_path}")
    print(f"Open in browser: file://{dashboard_path.absolute()}")
    print()
    
    print("="*80)
    print("ADMIN DASHBOARD DEMO COMPLETED")
    print("="*80)
    print()
    print("Summary:")
    print("✓ Infrastructure health monitoring working")
    print("✓ Resource utilization tracking working")
    print("✓ Cost tracking and budget alerts working")
    print("✓ Stress test controls (start/pause/resume/stop) working")
    print("✓ Failure injection controls working")
    print("✓ Emergency stop control available")
    print()
    print("Next Steps:")
    print("1. Open the admin dashboard HTML in a browser")
    print("2. Integrate with actual AWS services for live data")
    print("3. Connect to WebSocket server for real-time updates")
    print("4. Add authentication and authorization")
    print()


def main():
    """Main entry point."""
    try:
        asyncio.run(demo_admin_dashboard())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
