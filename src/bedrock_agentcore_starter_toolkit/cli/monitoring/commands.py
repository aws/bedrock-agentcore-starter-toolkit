"""CLI commands for monitoring and performance analytics."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...monitoring import MetricsCollector, OperationalInsights, PerformanceDashboard
from ..common import _handle_error, _print_success

console = Console()
monitoring_app = typer.Typer(help="Monitor agent performance and analytics")


@monitoring_app.command("metrics")
def get_metrics(
    agent_id: str = typer.Argument(..., help="Agent ID to monitor"),
    hours: int = typer.Option(1, "--hours", "-h", help="Hours of data to collect"),
    region: str = typer.Option("us-east-1", "--region", "-r", help="AWS region"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Get performance metrics for an agent."""
    try:
        collector = MetricsCollector(region)
        metrics = collector.collect_agent_metrics(agent_id, hours)
        
        if json_output:
            console.print(json.dumps(metrics, indent=2))
            return
        
        # Display formatted metrics
        console.print(f"\n[bold cyan]Performance Metrics for Agent: {agent_id}[/bold cyan]")
        console.print(f"[dim]Time Range: {metrics['time_range']['start']} to {metrics['time_range']['end']}[/dim]\n")
        
        # Performance table
        perf_table = Table(title="Performance Metrics")
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Value", style="green")
        
        perf = metrics["performance"]
        perf_table.add_row("Average Latency", f"{perf['avg_latency']:.2f}ms")
        perf_table.add_row("Max Latency", f"{perf['max_latency']:.2f}ms")
        perf_table.add_row("Min Latency", f"{perf['min_latency']:.2f}ms")
        perf_table.add_row("Request Count", str(perf['request_count']))
        
        console.print(perf_table)
        
        # Error metrics
        error_table = Table(title="Error Metrics")
        error_table.add_column("Metric", style="cyan")
        error_table.add_column("Value", style="red")
        
        errors = metrics["errors"]
        error_table.add_row("Error Count", str(errors['error_count']))
        error_table.add_row("Total Requests", str(errors['total_requests']))
        error_table.add_row("Error Rate", f"{errors['error_rate']}%")
        
        console.print(error_table)
        
        # Usage metrics
        usage_table = Table(title="Resource Usage")
        usage_table.add_column("Metric", style="cyan")
        usage_table.add_column("Value", style="yellow")
        
        usage = metrics["usage"]
        usage_table.add_row("Avg Memory Usage", f"{usage['avg_memory_usage']}%")
        usage_table.add_row("Max Memory Usage", f"{usage['max_memory_usage']}%")
        usage_table.add_row("Memory Efficiency", f"{usage['memory_efficiency']}%")
        
        console.print(usage_table)
        
    except Exception as e:
        _handle_error(f"Failed to collect metrics: {e}", e)


@monitoring_app.command("dashboard")
def create_dashboard(
    agent_id: str = typer.Argument(..., help="Agent ID to create dashboard for"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Dashboard name"),
    region: str = typer.Option("us-east-1", "--region", "-r", help="AWS region")
):
    """Create CloudWatch dashboard for an agent."""
    try:
        dashboard = PerformanceDashboard(region)
        url = dashboard.create_agent_dashboard(agent_id, name)
        
        _print_success(f"Dashboard created successfully!")
        console.print(f"[cyan]Dashboard URL: {url}[/cyan]")
        
    except Exception as e:
        _handle_error(f"Failed to create dashboard: {e}", e)


@monitoring_app.command("report")
def generate_report(
    agent_id: str = typer.Argument(..., help="Agent ID to generate report for"),
    hours: int = typer.Option(24, "--hours", "-h", help="Hours of data to analyze"),
    region: str = typer.Option("us-east-1", "--region", "-r", help="AWS region"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Generate comprehensive performance report."""
    try:
        dashboard = PerformanceDashboard(region)
        report = dashboard.generate_performance_report(agent_id, hours)
        
        if json_output:
            console.print(json.dumps(report, indent=2))
            return
        
        # Display formatted report
        console.print(Panel(
            f"[green]Performance Report for Agent: {agent_id}[/green]\n\n"
            f"Performance Score: [bold]{report['performance_score']}/100[/bold]\n"
            f"Report Time: {report['report_time']}\n"
            f"Dashboard: [cyan]{report['dashboard_url']}[/cyan]",
            title="Agent Performance Report",
            border_style="green"
        ))
        
        # Recommendations
        if report['recommendations']:
            console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for i, rec in enumerate(report['recommendations'], 1):
                console.print(f"  {i}. {rec}")
        
    except Exception as e:
        _handle_error(f"Failed to generate report: {e}", e)


@monitoring_app.command("insights")
def analyze_insights(
    agent_id: str = typer.Argument(..., help="Agent ID to analyze"),
    hours: int = typer.Option(24, "--hours", "-h", help="Hours of data to analyze"),
    region: str = typer.Option("us-east-1", "--region", "-r", help="AWS region"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Analyze operational insights and conversation patterns."""
    try:
        insights = OperationalInsights(region)
        analysis = insights.analyze_conversation_patterns(agent_id, hours)
        
        if json_output:
            console.print(json.dumps(analysis, indent=2))
            return
        
        console.print(f"\n[bold cyan]Operational Insights for Agent: {agent_id}[/bold cyan]")
        console.print(f"[dim]Analysis Period: {hours} hours[/dim]\n")
        
        # Session analysis
        if 'session_analysis' in analysis:
            session_table = Table(title="Session Analysis")
            session_table.add_column("Metric", style="cyan")
            session_table.add_column("Value", style="green")
            
            sessions = analysis['session_analysis']
            session_table.add_row("Total Sessions", str(sessions.get('total_sessions', 0)))
            session_table.add_row("Avg Session Length", f"{sessions.get('avg_session_length', 0):.1f}")
            session_table.add_row("Max Session Length", str(sessions.get('max_session_length', 0)))
            
            console.print(session_table)
        
        # Topic analysis
        if 'topic_analysis' in analysis:
            topics = analysis['topic_analysis'].get('top_topics', {})
            if topics:
                console.print("\n[bold yellow]Top Conversation Topics:[/bold yellow]")
                for topic, count in list(topics.items())[:5]:
                    console.print(f"  • {topic}: {count} mentions")
        
    except Exception as e:
        _handle_error(f"Failed to analyze insights: {e}", e)


@monitoring_app.command("anomalies")
def detect_anomalies(
    agent_id: str = typer.Argument(..., help="Agent ID to check for anomalies"),
    days: int = typer.Option(7, "--days", "-d", help="Days of historical data to analyze"),
    region: str = typer.Option("us-east-1", "--region", "-r", help="AWS region"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Detect performance anomalies and unusual patterns."""
    try:
        insights = OperationalInsights(region)
        anomalies = insights.detect_performance_anomalies(agent_id, days)
        
        if json_output:
            console.print(json.dumps(anomalies, indent=2))
            return
        
        console.print(f"\n[bold cyan]Anomaly Detection for Agent: {agent_id}[/bold cyan]")
        console.print(f"[dim]Analysis Period: {days} days[/dim]\n")
        
        total_anomalies = anomalies.get('anomalies_detected', 0)
        
        if total_anomalies == 0:
            console.print("[green]✅ No anomalies detected - performance looks stable![/green]")
            return
        
        console.print(f"[yellow]⚠️  {total_anomalies} anomalies detected[/yellow]\n")
        
        # Display anomalies
        anomaly_data = anomalies.get('anomalies', {})
        
        if anomaly_data.get('latency_spikes'):
            console.print("[red]Latency Spikes:[/red]")
            for spike in anomaly_data['latency_spikes']:
                console.print(f"  • {spike['date']}: {spike['current']:.0f}ms (↑{spike['increase']})")
        
        if anomaly_data.get('error_bursts'):
            console.print("[red]Error Rate Increases:[/red]")
            for burst in anomaly_data['error_bursts']:
                console.print(f"  • {burst['date']}: {burst['current']:.1f}% errors")
        
    except Exception as e:
        _handle_error(f"Failed to detect anomalies: {e}", e)


@monitoring_app.command("optimize")
def get_optimization_recommendations(
    agent_id: str = typer.Argument(..., help="Agent ID to optimize"),
    region: str = typer.Option("us-east-1", "--region", "-r", help="AWS region"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Get optimization recommendations for an agent."""
    try:
        insights = OperationalInsights(region)
        recommendations = insights.generate_optimization_recommendations(agent_id)
        
        if json_output:
            console.print(json.dumps(recommendations, indent=2))
            return
        
        console.print(f"\n[bold cyan]Optimization Recommendations for Agent: {agent_id}[/bold cyan]")
        console.print(f"[dim]Generated: {recommendations['generated_at']}[/dim]\n")
        
        total_recs = recommendations.get('total_recommendations', 0)
        if total_recs == 0:
            console.print("[green]✅ No optimization recommendations - agent is performing well![/green]")
            return
        
        console.print(f"[yellow]{total_recs} recommendations found[/yellow]\n")
        
        # Display recommendations by category
        for category, recs in recommendations['recommendations'].items():
            if recs:
                console.print(f"[bold]{category.title()}:[/bold]")
                for rec in recs:
                    priority_color = "red" if rec['priority'] == "high" else "yellow"
                    console.print(f"  [{priority_color}]• {rec['issue']}[/{priority_color}]")
                    console.print(f"    💡 {rec['recommendation']}")
                    console.print(f"    📈 {rec['impact']}\n")
        
    except Exception as e:
        _handle_error(f"Failed to get recommendations: {e}", e)