"""Console print utils for create command."""

from rich import box  # <--- Added import for ASCII style box
from rich.panel import Panel

from ...cli.common import console
from ..constants import IACProvider
from ..types import ProjectContext


def emit_create_completed_message(ctx: ProjectContext):
    """Take in the project context and emit a helpful message to console."""
    # end of progress sandwhich
    console.print("[cyan]✓ Agent Initialized.[/cyan]")
    # create some space so its not cramped
    console.print()

    # Common "Next Steps" styling to match the screenshot
    next_steps_header = "[bold]Next Steps[/bold]"

    intro_text = "You're ready to go! Happy building 🚀\n"

    if not ctx.iac_provider:
        console.print(
            Panel(
                f"{intro_text}"
                f"Enter your project directory using [cyan]cd ./{ctx.name}[/cyan]\n"
                f"Run [cyan]agentcore dev[/cyan] to start the dev server\n"
                f"Add memory with [cyan]agentcore configure[/cyan]\n"
                f"Launch with [cyan]agentcore deploy[/cyan]\n",
                title="Create Success",
                title_align="center",
                border_style="#39F56B",
            )
        )
        return

    # Extract conditional expressions to avoid newlines in f-strings
    gateway_name = ctx.name + "-AgentCoreGateway"

    gateway_auth = "Cognito" if not ctx.custom_authorizer_enabled else "Custom Authorizer"

    next_steps_cmd = (
        "cd cdk && npm install && npm run cdk synth && npm run cdk:deploy"
        if ctx.iac_provider == IACProvider.CDK
        else "cd terraform && terraform init && terraform apply"
    )

    console.print(
        Panel(
            f"{intro_text}\n"
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
            f"Network Mode: [cyan]{'VPC' if ctx.vpc_enabled else 'Public'}[/cyan]\n"
            f"Gateway Name: [cyan]{gateway_name}[/cyan]\n"
            f"Gateway Authorization: [cyan]{gateway_auth}[/cyan]\n"
            f"Memory Name: [cyan]{ctx.memory_name if ctx.memory_enabled else 'Memory Disabled'}[/cyan]\n"
            f"📄 Config saved to: [dim]{str(ctx.output_dir) + '/.bedrock_agentcore.yaml'}[/dim]\n"
            f"\n"
            f"{next_steps_header}\n"
            f"[cyan]cd {ctx.name}[/cyan]\n"
            f"[cyan]agentcore dev[/cyan] - Start local development server\n"
            f'[cyan]agentcore invoke --dev "Hello"[/cyan] - Test your agent locally\n'
            f"[cyan]{next_steps_cmd}[/cyan]\n"
            f"[cyan]agentcore invoke[/cyan] - Test your deployed agent",
            title="Create Success :tada:",
            title_align="center",
            border_style="#39F56B",
            box=box.ASCII,
        )
    )
