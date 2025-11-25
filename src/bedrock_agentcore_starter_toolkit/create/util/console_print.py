"""Console print utils for create command."""

from ...cli.cli_ui import sandwich_text_ui
from ...cli.common import console
from ..constants import IACProvider
from ..types import ProjectContext


def emit_create_completed_message(ctx: ProjectContext):
    """Take in the project context and emit a helpful message to console."""
    # end of progress sandwhich
    console.print("✓ Agent Initialized.")
    # create some space so its not cramped
    console.print()

    # Common "Next Steps" styling to match the screenshot
    next_steps_header = "[bold]Next Steps[/bold]"

    intro_text = "You're ready to go! Happy building 🚀\n"

    if not ctx.iac_provider:
        # Add memory line only if memory is not enabled
        memory_config_line = "Add memory with [cyan]agentcore configure[/cyan]\n" if not ctx.memory_enabled else ""

        sandwich_text_ui(
            style="#39F56B",
            text=f"{intro_text}"
            f"Enter your project directory using [cyan]cd {ctx.name}[/cyan]\n"
            f"Run [cyan]agentcore dev[/cyan] to start the dev server\n"
            f"Log into AWS with [cyan]aws login[/cyan]\n"
            f"{memory_config_line}"
            f"Launch with [cyan]agentcore deploy[/cyan]",
        )
        return

    # Extract conditional expressions to avoid newlines in f-strings
    gateway_name = ctx.name + "-AgentCoreGateway"

    gateway_auth = "Cognito" if not ctx.custom_authorizer_enabled else "Custom Authorizer"

    memory_output_line = f"Memory Name: [cyan]{ctx.memory_name}[/cyan]\n" if ctx.memory_enabled else ""

    next_steps_cmd = (
        "cd cdk && npm install && npm run cdk synth && npm run cdk:deploy"
        if ctx.iac_provider == IACProvider.CDK
        else "cd terraform && terraform init && terraform apply"
    )

    sandwich_text_ui(
        style="#39F56B",
        text=f"{intro_text}"
        f"\n"
        f"[bold]Project Details[/bold]\n"
        f"SDK Provider: [cyan]{ctx.sdk_provider}[/cyan]\n"
        f"Runtime Entrypoint: [cyan]{ctx.name}/src/main.py[/cyan]\n"
        f"IAC Entrypoint: [cyan]{ctx.name}/{ctx.iac_provider}/[/cyan]\n"
        f"Deployment: [cyan]{ctx.deployment_type}[/cyan]\n"
        f"\n"
        f"[bold]Configuration[/bold]\n"
        f"Agent Name: [cyan]{ctx.agent_name}[/cyan]\n"
        f"Gateway Name: [cyan]{gateway_name}[/cyan]\n"
        f"Gateway Authorization: [cyan]{gateway_auth}[/cyan]\n"
        f"Network Mode: [cyan]{'VPC' if ctx.vpc_enabled else 'Public'}[/cyan]\n"
        f"{memory_output_line}"
        f"📄 Config saved to: [cyan]{ctx.name}/.bedrock_agentcore.yaml[/cyan]\n"
        f"\n"
        f"{next_steps_header}\n"
        f"[cyan]cd {ctx.name}[/cyan]\n"
        f"[cyan]agentcore dev[/cyan] - Start local development server\n"
        f"Log into AWS with [cyan]aws login[/cyan]\n"
        f'[cyan]agentcore invoke --dev "Hello"[/cyan] - Test your agent locally\n'
        f"[cyan]{next_steps_cmd}[/cyan] - Deploy your project\n"
        f"[cyan]agentcore invoke[/cyan] - Test your deployed agent",
    )
