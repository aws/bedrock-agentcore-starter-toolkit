from rich.panel import Panel
from ...cli.common import console
from ..types import ProjectContext
from ..constants import IACProvider

def emit_bootstrap_completed_message(ctx: ProjectContext):
    """
    Take in the project context and emit a helpful message to console.
    """
    console.print(
        Panel(
            f"[bold]Agent Details[/bold]\n"
            f"Agent Name: [cyan]{ctx.agent_name}[/cyan]\n"
            f"Deployment: [cyan]{ctx.deployment_type}[/cyan]\n"

            f"\n"
            f"[bold]Project Details[/bold]\n"
            f"SDK Provider: [cyan]{ctx.sdk_provider}[/cyan]\n"
            f"Runtime Entrypoint: [cyan]{ctx.entrypoint_path}[/cyan]\n"
            f"IAC Provider: [cyan]{ctx.iac_provider}[/cyan]\n"
            f"IAC Entrypoint: [cyan]{ctx.iac_dir}[/cyan]\n"

            f"\n"
            f"[bold]Configuration[/bold]\n"
            f"Network Mode: [cyan]{"VPC" if ctx.vpc_enabled else "Public"}[/cyan]\n"
            f"Gateway Name: [cyan]{ctx.name + "-AgentCoreGateway" if not ctx.src_implementation_provided else "Source code provided so, gateway was not created"}[/cyan]\n"
            f"Gateway Authorization: [cyan]{('Cognito' if not ctx.custom_authorizer_enabled else 'Custom Authorizer') if not ctx.src_implementation_provided else 'N/A'}[/cyan]\n"
            f"Memory Name: [cyan]{ctx.memory_name if ctx.memory_enabled else "Memory Disabled"}[/cyan]\n"

            f"📄 Config saved to: [dim]{str(ctx.output_dir) + "/.bedrock_agentcore.yaml"}[/dim]\n\n"
            f"[bold]Next Steps:[/bold]\n"
            f"[cyan]{"`cd cdk && npm install && npm run cdk synth && npm run cdk:deploy`" if ctx.iac_provider == IACProvider.CDK else "`cd terraform && terraform init && terraform apply`"}[/cyan]\n"
            f"[cyan](after deploying) `agentcore invoke`[/cyan]",
            title="Bootstrap Success",
            border_style="bright_blue",
        )
    )