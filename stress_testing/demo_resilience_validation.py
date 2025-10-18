"""
Demo: Resilience Validation

This demo showcases the resilience validation capabilities including:
- Automatic recovery detection
- Circuit breaker validation
- Retry mechanism testing
- Dead letter queue processing
"""

import asyncio
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from stress_testing.resilience_validator import ResilienceValidator
from stress_testing.models import (
    FailureScenario,
    FailureType,
    SystemMetrics
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


def create_sample_metrics(
    throughput: float = 1000.0,
    error_rate: float = 0.001,
    latency: float = 500.0
) -> SystemMetrics:
    """Create sample system metrics."""
    total_requests = int(throughput * 10)
    failed_requests = int(total_requests * error_rate)
    successful_requests = total_requests - failed_requests
    
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=throughput,
        requests_total=total_requests,
        requests_successful=successful_requests,
        requests_failed=failed_requests,
        avg_response_time_ms=latency * 0.3,
        p50_response_time_ms=latency * 0.2,
        p95_response_time_ms=latency * 0.6,
        p99_response_time_ms=latency,
        max_response_time_ms=latency * 1.5,
        error_rate=error_rate,
        timeout_rate=error_rate * 0.5,
        cpu_utilization=0.60,
        memory_utilization=0.70,
        network_throughput_mbps=100.0
    )


async def demo_recovery_detection():
    """Demonstrate automatic recovery detection."""
    console.print("\n[bold cyan]═══ Automatic Recovery Detection Demo ═══[/bold cyan]\n")
    
    validator = ResilienceValidator(
        recovery_timeout_seconds=30.0,
        check_interval_seconds=2.0
    )
    
    # Create failure scenario
    failure = FailureScenario(
        failure_type=FailureType.LAMBDA_CRASH,
        start_time_seconds=0.0,
        duration_seconds=5.0,
        severity=0.8,
        parameters={}
    )
    
    # Simulate failure with degraded metrics
    console.print("[yellow]Simulating Lambda crash failure...[/yellow]")
    degraded_metrics = create_sample_metrics(
        throughput=500.0,
        error_rate=0.15,
        latency=2000.0
    )
    
    await validator.register_failure(failure, degraded_metrics)
    console.print(f"✓ Failure registered: {failure.failure_type.value}")
    console.print(f"  Active failures: {len(validator.active_failures)}")
    
    # Wait for failure duration
    console.print(f"\n[dim]Waiting {failure.duration_seconds}s for failure duration...[/dim]")
    await asyncio.sleep(failure.duration_seconds + 1)
    
    # Simulate recovery with normal metrics
    console.print("\n[green]System recovering...[/green]")
    normal_metrics = create_sample_metrics(
        throughput=1000.0,
        error_rate=0.001,
        latency=500.0
    )
    
    # Manually trigger recovery check
    await validator._check_for_recovery(normal_metrics)
    
    # Display results
    stats = validator.get_recovery_statistics()
    
    table = Table(title="Recovery Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Failures", str(stats['total_failures_detected']))
    table.add_row("Recoveries Detected", str(stats['total_recoveries_detected']))
    table.add_row("Recovery Failures", str(stats['total_recovery_failures']))
    table.add_row("Success Rate", f"{stats['recovery_success_rate']:.1%}")
    table.add_row("Avg Recovery Time", f"{stats['average_recovery_time_seconds']:.2f}s")
    
    console.print(table)
    
    if validator.recovery_events:
        event = validator.recovery_events[0]
        console.print(f"\n[bold green]✓ Recovery detected![/bold green]")
        console.print(f"  Recovery time: {event.recovery_time_seconds:.2f}s")
        console.print(f"  Error rate: {event.metrics_before['error_rate']:.2%} → {event.metrics_after['error_rate']:.2%}")
        console.print(f"  Throughput: {event.metrics_before['throughput_tps']:.0f} → {event.metrics_after['throughput_tps']:.0f} TPS")


async def demo_circuit_breaker():
    """Demonstrate circuit breaker validation."""
    console.print("\n[bold cyan]═══ Circuit Breaker Validation Demo ═══[/bold cyan]\n")
    
    validator = ResilienceValidator()
    
    services = ["payment_service", "fraud_detection_api", "user_service"]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for service in services:
            task = progress.add_task(f"Validating {service}...", total=None)
            
            result = await validator.validate_circuit_breaker(
                service_name=service,
                failure_threshold=5,
                timeout_seconds=3.0
            )
            
            progress.remove_task(task)
            
            status = "✓ PASSED" if result.validation_passed else "✗ FAILED"
            color = "green" if result.validation_passed else "red"
            console.print(f"[{color}]{status}[/{color}] {service}")
            console.print(f"  Triggered: {result.triggered}")
            console.print(f"  Time to open: {result.time_to_open_seconds:.3f}s")
            console.print(f"  Time to close: {result.time_to_close_seconds:.3f}s")
            console.print()
    
    # Display summary
    stats = validator.get_circuit_breaker_statistics()
    
    table = Table(title="Circuit Breaker Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Validations", str(stats['total_validations']))
    table.add_row("Passed", str(stats['passed_validations']))
    table.add_row("Failed", str(stats['failed_validations']))
    table.add_row("Success Rate", f"{stats['success_rate']:.1%}")
    
    console.print(table)


async def demo_retry_mechanism():
    """Demonstrate retry mechanism validation."""
    console.print("\n[bold cyan]═══ Retry Mechanism Validation Demo ═══[/bold cyan]\n")
    
    validator = ResilienceValidator()
    
    operations = [
        ("database_query", 3, 100.0),
        ("api_call", 5, 200.0),
        ("file_upload", 4, 150.0)
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for operation, max_retries, backoff in operations:
            task = progress.add_task(f"Testing {operation}...", total=None)
            
            result = await validator.validate_retry_mechanism(
                operation_type=operation,
                max_retries=max_retries,
                initial_backoff_ms=backoff
            )
            
            progress.remove_task(task)
            
            status = "✓ PASSED" if result.validation_passed else "✗ FAILED"
            color = "green" if result.validation_passed else "red"
            console.print(f"[{color}]{status}[/{color}] {operation}")
            console.print(f"  Retry attempts: {result.retry_attempts}")
            console.print(f"  Successful: {result.successful_retries}")
            console.print(f"  Exponential backoff: {result.exponential_backoff_detected}")
            console.print(f"  Max retries respected: {result.max_retries_respected}")
            
            if result.retry_timings:
                timings_str = ", ".join(f"{t:.0f}ms" for t in result.retry_timings)
                console.print(f"  Retry timings: {timings_str}")
            console.print()
    
    # Display summary
    stats = validator.get_retry_statistics()
    
    table = Table(title="Retry Mechanism Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Validations", str(stats['total_validations']))
    table.add_row("Passed", str(stats['passed_validations']))
    table.add_row("Failed", str(stats['failed_validations']))
    table.add_row("Success Rate", f"{stats['success_rate']:.1%}")
    
    console.print(table)


async def demo_dlq_processing():
    """Demonstrate DLQ processing validation."""
    console.print("\n[bold cyan]═══ Dead Letter Queue Validation Demo ═══[/bold cyan]\n")
    
    validator = ResilienceValidator()
    
    queues = [
        ("transaction_dlq", 20),
        ("notification_dlq", 15),
        ("audit_dlq", 10)
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for queue, message_count in queues:
            task = progress.add_task(f"Processing {queue}...", total=None)
            
            result = await validator.validate_dlq_processing(
                queue_name=queue,
                test_message_count=message_count
            )
            
            progress.remove_task(task)
            
            status = "✓ PASSED" if result.validation_passed else "✗ FAILED"
            color = "green" if result.validation_passed else "red"
            console.print(f"[{color}]{status}[/{color}] {queue}")
            console.print(f"  Messages sent: {result.messages_sent_to_dlq}")
            console.print(f"  Messages processed: {result.messages_processed_from_dlq}")
            console.print(f"  Success rate: {result.processing_success_rate:.1%}")
            console.print(f"  Avg processing time: {result.average_processing_time_ms:.1f}ms")
            console.print()
    
    # Display summary
    stats = validator.get_dlq_statistics()
    
    table = Table(title="DLQ Processing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Validations", str(stats['total_validations']))
    table.add_row("Passed", str(stats['passed_validations']))
    table.add_row("Failed", str(stats['failed_validations']))
    table.add_row("Success Rate", f"{stats['success_rate']:.1%}")
    table.add_row("Avg Processing Success", f"{stats['average_processing_success_rate']:.1%}")
    
    console.print(table)


async def demo_comprehensive_report():
    """Demonstrate comprehensive resilience report."""
    console.print("\n[bold cyan]═══ Comprehensive Resilience Report ═══[/bold cyan]\n")
    
    validator = ResilienceValidator()
    
    # Run all validations
    console.print("[dim]Running comprehensive resilience tests...[/dim]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running validations...", total=4)
        
        # Circuit breaker
        await validator.validate_circuit_breaker("test_service")
        progress.advance(task)
        
        # Retry mechanism
        await validator.validate_retry_mechanism("test_operation")
        progress.advance(task)
        
        # DLQ processing
        await validator.validate_dlq_processing("test_queue")
        progress.advance(task)
        
        # Recovery detection
        failure = FailureScenario(
            failure_type=FailureType.NETWORK_LATENCY,
            start_time_seconds=0.0,
            duration_seconds=2.0,
            severity=0.5,
            parameters={}
        )
        await validator.register_failure(failure, create_sample_metrics(error_rate=0.1))
        await asyncio.sleep(3)
        await validator._check_for_recovery(create_sample_metrics())
        progress.advance(task)
    
    # Get comprehensive report
    report = validator.get_comprehensive_report()
    
    # Display overall score
    score = report['overall_resilience_score']
    score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
    
    console.print(Panel(
        f"[bold {score_color}]Overall Resilience Score: {score:.1f}/100[/bold {score_color}]",
        title="Resilience Assessment",
        border_style=score_color
    ))
    
    # Display detailed metrics
    console.print("\n[bold]Detailed Metrics:[/bold]\n")
    
    # Recovery
    recovery = report['recovery']
    console.print("[cyan]Recovery:[/cyan]")
    console.print(f"  Success Rate: {recovery['recovery_success_rate']:.1%}")
    console.print(f"  Avg Recovery Time: {recovery['average_recovery_time_seconds']:.2f}s")
    
    # Circuit Breaker
    cb = report['circuit_breaker']
    console.print("\n[cyan]Circuit Breaker:[/cyan]")
    console.print(f"  Success Rate: {cb['success_rate']:.1%}")
    console.print(f"  Validations: {cb['passed_validations']}/{cb['total_validations']}")
    
    # Retry Mechanism
    retry = report['retry_mechanism']
    console.print("\n[cyan]Retry Mechanism:[/cyan]")
    console.print(f"  Success Rate: {retry['success_rate']:.1%}")
    console.print(f"  Validations: {retry['passed_validations']}/{retry['total_validations']}")
    
    # DLQ Processing
    dlq = report['dlq_processing']
    console.print("\n[cyan]DLQ Processing:[/cyan]")
    console.print(f"  Success Rate: {dlq['success_rate']:.1%}")
    console.print(f"  Avg Processing Success: {dlq['average_processing_success_rate']:.1%}")


async def main():
    """Run all demos."""
    console.print(Panel.fit(
        "[bold cyan]Resilience Validation Demo[/bold cyan]\n"
        "Demonstrating automatic recovery detection, circuit breakers,\n"
        "retry mechanisms, and DLQ processing",
        border_style="cyan"
    ))
    
    try:
        # Run demos
        await demo_recovery_detection()
        await demo_circuit_breaker()
        await demo_retry_mechanism()
        await demo_dlq_processing()
        await demo_comprehensive_report()
        
        console.print("\n[bold green]✓ All resilience validation demos completed successfully![/bold green]\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        logger.exception("Demo failed")


if __name__ == "__main__":
    asyncio.run(main())
