"""Bedrock Agent Translation Tool."""

import os
import subprocess  # nosec # needed to run the agent file
import uuid

import boto3
import questionary
import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bedrock_agentcore_starter_toolkit.services.runtime import generate_session_id

from ...services.import_agent.scripts.bedrock_to_langchain import BedrockLangchainTranslation
from ...services.import_agent.scripts.bedrock_to_strands import BedrockStrandsTranslation
from ..common import console
from .agent_info import auth_and_get_info, get_agent_aliases, get_agents, get_clients

app = typer.Typer(help="Import Agent")


def _verify_aws_credentials() -> bool:
    """Verify that AWS credentials are present and valid."""
    try:
        # Try to get the caller identity to verify credentials
        boto3.client("sts").get_caller_identity()
        return True
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]AWS credentials are invalid![/bold red]\n"
                f"Error: {str(e)}\n"
                f"Please reconfigure your AWS credentials by running:\n"
                f"[bold]aws configure[/bold]",
                title="Authentication Error",
                border_style="red",
            )
        )
        return False


def _run_agent(output_dir, output_path):
    """Run the generated agent."""
    try:
        console.print(
            Panel(
                "[bold green]Installing dependencies and launching the agent...[/bold green]\nYou can start using your translated agent below:",  # noqa: E501
                title="Agent Launch",
                border_style="green",
            )
        )

        # Create a virutal environment for the translated agent, install dependencies, and run CLI
        subprocess.check_call(["python", "-m", "venv", ".venv"], cwd=output_dir)  # nosec
        subprocess.check_call(
            [".venv/bin/python", "-m", "pip", "-q", "install", "--no-cache-dir", "-r", "requirements.txt"],
            cwd=output_dir,
        )  # nosec
        process = subprocess.Popen([".venv/bin/python", output_path, "--cli"], cwd=output_dir)  # nosec

        while True:
            try:
                process.wait()
                break
            except KeyboardInterrupt:
                pass

        console.print("\n[green]Agent execution completed.[/green]")

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]Failed to run the agent![/bold red]\nError: {str(e)}",
                title="Execution Error",
                border_style="red",
            )
        )


def _agentcore_invoke_cli(output_dir):
    """Run the generated agent."""
    session_id = generate_session_id()
    while True:
        query = input("\nEnter your query (or type 'exit' to quit): ")
        if query.lower() == "exit":
            console.print("\n[yellow]Exiting AgentCore CLI...[/yellow]")
            break

        try:
            subprocess.check_call(["agentcore", "invoke", str(query), "-s", session_id], cwd=output_dir)  # nosec
        except Exception as e:
            console.print(
                Panel(
                    f"[bold red]Error invoking agent![/bold red]\nError: {str(e)}",
                    title="Invocation Error",
                    border_style="red",
                )
            )
            continue


@app.command()
def import_agent(
    agent_id: str = typer.Option(None, "--agent-id", help="ID of the Bedrock Agent to import"),
    agent_alias_id: str = typer.Option(None, "--agent-alias-id", help="ID of the Agent Alias to use"),
    target_platform: str = typer.Option(None, "--target-platform", help="Target platform (langchain or strands)"),
    region: str = typer.Option(None, "--region", help="AWS region for Bedrock (e.g., us-west-2)"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose mode for the generated agent"),
    disable_gateway: bool = typer.Option(False, "--disable-gateway", help="Disable AgentCore Gateway primitive"),
    disable_memory: bool = typer.Option(False, "--disable-memory", help="Disable AgentCore Memory primitive"),
    disable_code_interpreter: bool = typer.Option(
        False, "--disable-code-interpreter", help="Disable AgentCore Code Interpreter primitive"
    ),
    disable_observability: bool = typer.Option(
        False, "--disable-observability", help="Disable AgentCore Observability primitive"
    ),
    deploy_runtime: bool = typer.Option(False, "--deploy-runtime", help="Deploy to AgentCore Runtime"),
    run_option: str = typer.Option(None, "--run-option", help="How to run the agent (locally, runtime, none)"),
    output_dir: str = typer.Option("./output/", "--output-dir", help="Output directory for generated code"),
):
    """Use a Bedrock Agent to generate a LangChain or Strands agent with AgentCore primitives."""
    try:
        run_agent_choice = ""
        output_path = ""

        os.makedirs(output_dir, exist_ok=True)

        # Display welcome banner
        console.print(
            Panel(
                Text("Bedrock Agent Translation Tool", style="bold cyan"),
                subtitle="Convert your Bedrock Agent to LangChain/Strands code with AgentCore Primitives",
                border_style="cyan",
            )
        )

        # Verify AWS credentials
        console.print("\n[bold]Verifying AWS credentials...[/bold]")
        if not _verify_aws_credentials():
            return

        console.print("[bold green]✓[/bold green] AWS credentials verified!")

        # Available AWS regions for Bedrock Agents
        aws_regions = [
            {"name": "US East (N. Virginia)", "code": "us-east-1"},
            {"name": "US West (Oregon)", "code": "us-west-2"},
            {"name": "AWS GovCloud (US-West)", "code": "us-gov-west-1"},
            {"name": "Asia Pacific (Tokyo)", "code": "ap-northeast-1"},
            {"name": "Asia Pacific (Mumbai)", "code": "ap-south-1"},
            {"name": "Asia Pacific (Singapore)", "code": "ap-southeast-1"},
            {"name": "Asia Pacific (Sydney)", "code": "ap-southeast-2"},
            {"name": "Canada (Central)", "code": "ca-central-1"},
            {"name": "Europe (Frankfurt)", "code": "eu-central-1"},
            {"name": "Europe (Zurich)", "code": "eu-central-2"},
            {"name": "Europe (Ireland)", "code": "eu-west-1"},
            {"name": "Europe (London)", "code": "eu-west-2"},
            {"name": "Europe (Paris)", "code": "eu-west-3"},
            {"name": "South America (São Paulo)", "code": "sa-east-1"},
        ]

        # Set region from command line or prompt user to select
        selected_region_code = None
        if region:
            # Validate the provided region
            valid_region_codes = [r["code"] for r in aws_regions]
            if region in valid_region_codes:
                selected_region_code = region
                region_name = next((r["name"] for r in aws_regions if r["code"] == region), "Unknown")
                console.print(f"[bold green]✓[/bold green] Using region: {region_name} ({region})")
            else:
                console.print(
                    Panel(
                        f"[bold yellow]Warning: '{region}' is not a recognized Bedrock region.[/bold yellow]\n"
                        f"Proceeding with region selection.",
                        title="Region Warning",
                        border_style="yellow",
                    )
                )

        # If region wasn't provided or was invalid, prompt for selection
        if not selected_region_code:
            console.print("\n[bold]Select an AWS region for Bedrock Agents:[/bold]")
            region_choices = [f"{region['name']} ({region['code']})" for region in aws_regions]
            selected_region = questionary.select(
                "Select a region:",
                choices=region_choices,
            ).ask()

            if selected_region is None:  # Handle case where user presses Esc
                console.print("\n[yellow]Region selection cancelled by user.[/yellow]")
                return

            # Extract region code from selection
            selected_region_code = selected_region.split("(")[-1].strip(")")
            console.print(f"[bold green]✓[/bold green] Selected region: {selected_region}")

        # Get AWS credentials and clients
        credentials = boto3.Session().get_credentials()
        bedrock_client, bedrock_agent_client = get_clients(credentials, selected_region_code)

        # Get all agents in the user's account
        console.print("\n[bold]Fetching available agents...[/bold]")
        agents = get_agents(bedrock_agent_client)

        if not agents:
            console.print(
                Panel("[bold red]No agents found in your account![/bold red]", title="Error", border_style="red")
            )
            return

        # Display agents in a table
        agents_table = Table(title="\nAvailable Agents")
        agents_table.add_column("ID", style="cyan")
        agents_table.add_column("Name", style="green")
        agents_table.add_column("Description", style="yellow")

        for agent in agents:
            agents_table.add_row(agent["id"], agent["name"] or "No name", agent["description"] or "No description")

        console.print(agents_table, "\n")

        # Let user select an agent if not provided
        if agent_id is None:
            agent_choices = [f"{agent['name']} ({agent['id']})" for agent in agents]
            selected_agent = questionary.select(
                "Select an agent:",
                choices=agent_choices,
            ).ask()

            if selected_agent is None:  # Handle case where user presses Esc
                console.print("\n[yellow]Agent selection cancelled by user.[/yellow]")
                return

            # Extract agent ID from selection
            agent_id = selected_agent.split("(")[-1].strip(")")
        else:
            # Verify the provided agent ID exists
            agent_exists = any(agent["id"] == agent_id for agent in agents)
            if not agent_exists:
                console.print(
                    Panel(
                        f"[bold red]Agent with ID '{agent_id}' not found![/bold red]",
                        title="Error",
                        border_style="red",
                    )
                )
                return

        # Get all aliases for the selected agent
        console.print(f"[bold]Fetching aliases for agent {agent_id}...[/bold]")
        aliases = get_agent_aliases(bedrock_agent_client, agent_id)

        if not aliases:
            console.print(
                Panel(
                    f"[bold red]No aliases found for agent {agent_id}![/bold red]",
                    title="Error",
                    border_style="red",
                )
            )
            return

        # Display aliases in a table
        aliases_table = Table(title=f"\nAvailable Aliases for Agent {agent_id}")
        aliases_table.add_column("ID", style="cyan")
        aliases_table.add_column("Name", style="green")
        aliases_table.add_column("Description", style="yellow")

        for alias in aliases:
            aliases_table.add_row(alias["id"], alias["name"] or "No name", alias["description"] or "No description")

        console.print(aliases_table, "\n")

        # Let user select an alias if not provided
        if agent_alias_id is None:
            alias_choices = [f"{alias['name']} ({alias['id']})" for alias in aliases]
            selected_alias = questionary.select(
                "Select an alias:",
                choices=alias_choices,
            ).ask()

            if selected_alias is None:  # Handle case where user presses Esc
                console.print("\n[yellow]Alias selection cancelled by user.[/yellow]")
                return

            # Extract alias ID from selection
            agent_alias_id = selected_alias.split("(")[-1].strip(")")
        else:
            # Verify the provided alias ID exists
            alias_exists = any(alias["id"] == agent_alias_id for alias in aliases)
            if not alias_exists:
                console.print(
                    Panel(
                        f"[bold red]Alias with ID '{agent_alias_id}' not found for agent '{agent_id}'![/bold red]",
                        title="Error",
                        border_style="red",
                    )
                )
                return

        # Select target platform if not provided
        if target_platform is None:
            target_platform = questionary.select(
                "Select your target platform:",
                choices=["langchain (0.3.x) + langgraph (0.5.x)", "strands (1.0.x)"],
            ).ask()

            if target_platform is None:  # Handle case where user presses Esc
                console.print("\n[yellow]Platform selection cancelled by user.[/yellow]")
                return

            target_platform = "langchain" if target_platform.startswith("langchain") else "strands"
        else:
            # Validate target platform
            if target_platform not in ["langchain", "strands"]:
                console.print(
                    Panel(
                        f"[bold red]Invalid target platform '{target_platform}'![/bold red]\n"
                        f"Valid options are: langchain, strands",
                        title="Error",
                        border_style="red",
                    )
                )
                return

        # Set verbose mode based on flags or ask user
        verbose_mode = verbose

        # Ask about verbose mode if not provided via flags
        if not verbose_mode:  # Only ask if neither verbose nor debug is True
            verbose_choice = questionary.confirm("Enable verbose output for the generated agent?", default=False).ask()

            if verbose_choice is None:  # Handle case where user presses Esc
                console.print("\n[yellow]Verbose mode selection cancelled by user.[/yellow]")
                return

            verbose_mode = verbose_choice

        # Set primitives based on flags, default to True unless explicitly disabled
        primitives_opt_in = {
            "gateway": not disable_gateway,
            "memory": not disable_memory,
            "code_interpreter": not disable_code_interpreter,
            "observability": not disable_observability,
        }

        selected_primitives = [k for k, v in primitives_opt_in.items() if v]
        console.print(f"[bold green]✓[/bold green] Selected AgentCore primitives: {selected_primitives}\n")

        # Show progress
        with console.status("[bold green]Fetching agent configuration...[/bold green]"):
            try:
                agent_config = auth_and_get_info(agent_id, agent_alias_id, output_dir, selected_region_code)
                console.print("[bold green]✓[/bold green] Agent configuration retrieved!\n")
            except Exception as e:
                console.print(
                    Panel(
                        f"[bold red]Failed to retrieve agent configuration![/bold red]\nError: {str(e)}",
                        title="Configuration Error",
                        border_style="red",
                    )
                )
                return

        # Translate the agent
        with console.status(f"[bold green]Translating agent to {target_platform}...[/bold green]"):
            try:
                if target_platform == "langchain":
                    output_path = os.path.join(output_dir, "langchain_agent.py")
                    translator = BedrockLangchainTranslation(
                        agent_config, debug=verbose_mode, output_dir=output_dir, enabled_primitives=primitives_opt_in
                    )
                    environment_variables = translator.translate_bedrock_to_langchain(output_path)
                else:  # strands
                    output_path = os.path.join(output_dir, "strands_agent.py")
                    translator = BedrockStrandsTranslation(
                        agent_config, debug=verbose_mode, output_dir=output_dir, enabled_primitives=primitives_opt_in
                    )
                    environment_variables = translator.translate_bedrock_to_strands(output_path)

                console.print(f"\n[bold green]✓[/bold green] Agent translated to {target_platform}!")
                console.print(f"[bold]  Output file:[/bold] {output_path}\n")
            except KeyboardInterrupt:
                console.print("\n[yellow]Translation process cancelled by user.[/yellow]")
                return
            except Exception as e:
                console.print(
                    Panel(
                        f"[bold red]Failed to translate agent![/bold red]\nError: {str(e)}",
                        title="Translation Error",
                        border_style="red",
                    )
                )
                return

        # AgentCore Runtime deployment options
        output_path = os.path.abspath(output_path)
        output_dir = os.path.abspath(output_dir)
        requirements_path = os.path.join(output_dir, "requirements.txt")

        # Ask about deployment if not provided via flag
        if not deploy_runtime:  # Only ask if deploy_runtime is False (default)
            deploy_runtime_choice = questionary.confirm(
                "Would you like to deploy the agent to AgentCore Runtime? (This will take a few minutes)", default=False
            ).ask()

            if deploy_runtime_choice is None:  # Handle case where user presses Esc
                console.print("\n[yellow]AgentCore Runtime deployment selection cancelled by user.[/yellow]")
                deploy_runtime = False
            else:
                deploy_runtime = deploy_runtime_choice

        if deploy_runtime:
            try:
                agent_name = f"agent_{uuid.uuid4().hex[:8].lower()}"
                console.print("[bold]  \nDeploying agent to AgentCore Runtime...\n[/bold]")
                env_injection_code = (
                    ""
                    if not environment_variables
                    else "--env " + " --env ".join(f"{k}={v}" for k, v in environment_variables.items())
                )

                configure_cmd = f"agentcore configure --entrypoint {output_path} --requirements-file {requirements_path} --ecr auto -n '{agent_name}'"  # noqa: E501
                set_default_cmd = f"agentcore configure set-default '{agent_name}'"
                launch_cmd = f"agentcore launch {env_injection_code}"

                os.system(f"cd {output_dir} && {configure_cmd} && {set_default_cmd} && {launch_cmd}")  # nosec

            except Exception as e:
                console.print(
                    Panel(
                        f"[bold red]Failed to deploy agent to AgentCore Runtime![/bold red]\nError: {str(e)}",
                        title="Deployment Error",
                        border_style="red",
                    )
                )
                return

        # Determine how to run the agent
        if run_option is None:
            run_options = ["Install dependencies and run locally", "Don't run now"]

            if deploy_runtime:
                run_options.insert(1, "Run on AgentCore Runtime")

            run_agent_choice = questionary.select(
                "How would you like to run the agent?",
                choices=run_options,
            ).ask()
            if run_agent_choice is None:  # Handle case where user presses Esc
                console.print("\n[yellow]Run selection cancelled by user.[/yellow]")
                return
        else:
            # Map run_option to the expected values
            if run_option.lower() == "locally":
                run_agent_choice = "Install dependencies and run locally"
            elif run_option.lower() == "runtime":
                if not deploy_runtime:
                    console.print(
                        Panel(
                            "[bold red]Cannot run on AgentCore Runtime because it was not deployed![/bold red]",
                            title="Error",
                            border_style="red",
                        )
                    )
                    run_agent_choice = "Don't run now"
                else:
                    run_agent_choice = "Run on AgentCore Runtime"
            elif run_option.lower() == "none":
                run_agent_choice = "Don't run now"
            else:
                console.print(
                    Panel(
                        f"[bold red]Invalid run option '{run_option}'![/bold red]\n"
                        f"Valid options are: locally, runtime, none",
                        title="Error",
                        border_style="red",
                    )
                )
                run_agent_choice = "Don't run now"

    except KeyboardInterrupt:
        console.print("\n[yellow]Migration process cancelled by user.[/yellow]")
    except SystemExit:
        console.print("\n[yellow]Migration process exited.[/yellow]")
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]An unexpected error occurred![/bold red]\nError: {str(e)}",
                title="Unexpected Error",
                border_style="red",
            )
        )

    if run_agent_choice == "Install dependencies and run locally":
        _run_agent(output_dir, output_path)
    elif run_agent_choice == "Run on AgentCore Runtime" and deploy_runtime:
        console.print(
            Panel(
                "[bold green]Starting AgentCore Runtime interactive CLI...[/bold green]",
                title="AgentCore Runtime",
                border_style="green",
            )
        )
        _agentcore_invoke_cli(output_dir)
    elif run_agent_choice == "Don't run now":
        console.print(
            Panel(
                f"[bold green]Migration completed successfully![/bold green]\n"
                f"Install the required dependencies and then run your agent with:\n"
                f"[bold]python {output_path} --cli[/bold]",
                title="Migration Complete",
                border_style="green",
            )
        )
