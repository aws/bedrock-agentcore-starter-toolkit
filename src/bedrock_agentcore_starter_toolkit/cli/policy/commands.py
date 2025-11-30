"""Bedrock AgentCore Policy CLI commands."""

import json
from typing import Optional

import typer

from ...operations.policy import PolicyClient
from ..common import console

# Create a Typer app for policy commands
policy_app = typer.Typer(help="Manage Bedrock AgentCore Policy Engines and Policies")


# ==================== Policy Engine Commands ====================


@policy_app.command("create-policy-engine")
def create_policy_engine(
    name: str = typer.Option(..., "--name", "-n", help="Name of the policy engine"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Policy engine description"),
) -> None:
    """Create a new policy engine."""
    client = PolicyClient(region_name=region)
    response = client.create_policy_engine(
        name=name,
        description=description,
    )
    console.print("[green]✓ Policy engine creation initiated![/green]")
    console.print(f"[bold]Engine ID:[/bold] {response.get('policyEngineId', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    console.print("[dim]Use 'get-policy-engine' to check when status becomes ACTIVE[/dim]")
    console.print(f"[bold]Name:[/bold] {response.get('name', 'N/A')}")
    if response.get("policyEngineArn"):
        console.print(f"[bold]ARN:[/bold] [dim]{response['policyEngineArn']}[/dim]")


@policy_app.command("get-policy-engine")
def get_policy_engine(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
) -> None:
    """Get policy engine details."""
    client = PolicyClient(region_name=region)
    response = client.get_policy_engine(policy_engine_id)
    console.print("\n[bold cyan]Policy Engine Details:[/bold cyan]")
    console.print(f"[bold]Engine ID:[/bold] {response.get('policyEngineId', 'N/A')}")
    console.print(f"[bold]Name:[/bold] {response.get('name', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    console.print(f"[bold]Description:[/bold] {response.get('description', 'N/A')}")
    if response.get("policyEngineArn"):
        console.print(f"[bold]ARN:[/bold] [dim]{response['policyEngineArn']}[/dim]")
    if response.get("createdAt"):
        console.print(f"[bold]Created:[/bold] {response['createdAt']}")
    if response.get("updatedAt"):
        console.print(f"[bold]Updated:[/bold] {response['updatedAt']}")


@policy_app.command("update-policy-engine")
def update_policy_engine(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Updated description"),
) -> None:
    """Update a policy engine."""
    client = PolicyClient(region_name=region)
    response = client.update_policy_engine(
        policy_engine_id=policy_engine_id,
        description=description,
    )
    console.print("[green]✓ Policy engine update initiated![/green]")
    console.print(f"[bold]Engine ID:[/bold] {response.get('policyEngineId', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    if response.get("updatedAt"):
        console.print(f"[bold]Updated:[/bold] {response['updatedAt']}")


@policy_app.command("list-policy-engines")
def list_policy_engines(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    max_results: Optional[int] = typer.Option(None, "--max-results", help="Maximum number of results"),
    next_token: Optional[str] = typer.Option(None, "--next-token", help="Token for pagination"),
) -> None:
    """List policy engines."""
    from rich.table import Table

    client = PolicyClient(region_name=region)
    response = client.list_policy_engines(max_results=max_results, next_token=next_token)

    engines = response.get("policyEngines", [])

    if not engines:
        console.print("[yellow]No policy engines found.[/yellow]")
        return

    table = Table(title=f"Policy Engines ({len(engines)})")
    table.add_column("Engine ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created At", style="blue")

    for engine in engines:
        table.add_row(
            engine.get("policyEngineId", "N/A"),
            engine.get("name", "N/A"),
            engine.get("status", "N/A"),
            str(engine.get("createdAt", "N/A")),
        )

    console.print(table)

    if response.get("nextToken"):
        console.print(f"\n[dim]Next token:[/dim] {response['nextToken']}")


@policy_app.command("delete-policy-engine")
def delete_policy_engine(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
) -> None:
    """Delete a policy engine."""
    client = PolicyClient(region_name=region)
    response = client.delete_policy_engine(policy_engine_id)
    console.print("[green]✓ Policy engine deletion initiated![/green]")
    console.print(f"[bold]Engine ID:[/bold] {policy_engine_id}")
    if response.get("status"):
        console.print(f"[bold]Status:[/bold] {response['status']}")


# ==================== Policy Commands ====================


@policy_app.command("create-policy")
def create_policy(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    name: str = typer.Option(..., "--name", "-n", help="Policy name"),
    definition: str = typer.Option(
        ...,
        "--definition",
        "-def",
        help='Policy definition JSON (e.g., \'{"cedar":{"statement":"permit(...);"}}\')',
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Policy description"),
    validation_mode: Optional[str] = typer.Option(
        None, "--validation-mode", help="Validation mode (FAIL_ON_ANY_FINDINGS, IGNORE_ALL_FINDINGS)"
    ),
) -> None:
    """Create a new policy."""
    client = PolicyClient(region_name=region)

    # Parse the definition JSON
    try:
        definition_dict = json.loads(definition)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing definition JSON: {e}[/red]")
        raise typer.Exit(1) from None

    response = client.create_policy(
        policy_engine_id=policy_engine_id,
        name=name,
        definition=definition_dict,
        description=description,
        validation_mode=validation_mode,
    )
    console.print("[green]✓ Policy creation initiated![/green]")
    console.print(f"[bold]Policy ID:[/bold] {response.get('policyId', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    console.print(f"[bold]Name:[/bold] {response.get('name', 'N/A')}")
    console.print("[dim]Use 'get-policy' to check when status becomes ACTIVE[/dim]")
    if response.get("policyArn"):
        console.print(f"[bold]ARN:[/bold] [dim]{response['policyArn']}[/dim]")


@policy_app.command("get-policy")
def get_policy(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    policy_id: str = typer.Option(..., "--policy-id", "-p", help="Policy ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
) -> None:
    """Get policy details."""
    client = PolicyClient(region_name=region)
    response = client.get_policy(policy_engine_id, policy_id)
    console.print("\n[bold cyan]Policy Details:[/bold cyan]")
    console.print(f"[bold]Policy ID:[/bold] {response.get('policyId', 'N/A')}")
    console.print(f"[bold]Name:[/bold] {response.get('name', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    console.print(f"[bold]Description:[/bold] {response.get('description', 'N/A')}")
    if response.get("policyArn"):
        console.print(f"[bold]ARN:[/bold] [dim]{response['policyArn']}[/dim]")
    if response.get("definition"):
        console.print("\n[bold]Definition:[/bold]")
        console.print(json.dumps(response["definition"], indent=2))
    if response.get("createdAt"):
        console.print(f"\n[bold]Created:[/bold] {response['createdAt']}")
    if response.get("updatedAt"):
        console.print(f"[bold]Updated:[/bold] {response['updatedAt']}")


@policy_app.command("update-policy")
def update_policy(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    policy_id: str = typer.Option(..., "--policy-id", "-p", help="Policy ID"),
    definition: str = typer.Option(..., "--definition", "-def", help="Updated policy definition JSON"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Updated description"),
    validation_mode: Optional[str] = typer.Option(
        None, "--validation-mode", help="Validation mode (FAIL_ON_ANY_FINDINGS, IGNORE_ALL_FINDINGS)"
    ),
) -> None:
    """Update a policy."""
    client = PolicyClient(region_name=region)

    # Parse the definition JSON
    try:
        definition_dict = json.loads(definition)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing definition JSON: {e}[/red]")
        raise typer.Exit(1) from None

    response = client.update_policy(
        policy_engine_id=policy_engine_id,
        policy_id=policy_id,
        definition=definition_dict,
        description=description,
        validation_mode=validation_mode,
    )
    console.print("[green]✓ Policy update initiated![/green]")
    console.print(f"[bold]Policy ID:[/bold] {response.get('policyId', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    if response.get("updatedAt"):
        console.print(f"[bold]Updated:[/bold] {response['updatedAt']}")


@policy_app.command("list-policies")
def list_policies(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    target_resource_scope: Optional[str] = typer.Option(None, "--target-resource-scope", help="Filter by resource ARN"),
    max_results: Optional[int] = typer.Option(None, "--max-results", help="Maximum number of results"),
    next_token: Optional[str] = typer.Option(None, "--next-token", help="Token for pagination"),
) -> None:
    """List policies."""
    from rich.table import Table

    client = PolicyClient(region_name=region)
    response = client.list_policies(
        policy_engine_id=policy_engine_id,
        target_resource_scope=target_resource_scope,
        max_results=max_results,
        next_token=next_token,
    )

    policies = response.get("policies", [])

    if not policies:
        console.print("[yellow]No policies found.[/yellow]")
        return

    table = Table(title=f"Policies ({len(policies)})")
    table.add_column("Policy ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created At", style="blue")

    for policy in policies:
        table.add_row(
            policy.get("policyId", "N/A"),
            policy.get("name", "N/A"),
            policy.get("status", "N/A"),
            str(policy.get("createdAt", "N/A")),
        )

    console.print(table)

    if response.get("nextToken"):
        console.print(f"\n[dim]Next token:[/dim] {response['nextToken']}")


@policy_app.command("delete-policy")
def delete_policy(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    policy_id: str = typer.Option(..., "--policy-id", "-p", help="Policy ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
) -> None:
    """Delete a policy."""
    client = PolicyClient(region_name=region)
    response = client.delete_policy(policy_engine_id, policy_id)
    console.print("[green]✓ Policy deletion initiated![/green]")
    console.print(f"[bold]Policy ID:[/bold] {policy_id}")
    if response.get("status"):
        console.print(f"[bold]Status:[/bold] {response['status']}")


# ==================== Policy Generation Commands ====================


@policy_app.command("start-policy-generation")
def start_policy_generation(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    name: str = typer.Option(..., "--name", "-n", help="Generation name"),
    resource_arn: str = typer.Option(..., "--resource-arn", help="Resource ARN for policy generation"),
    content: str = typer.Option(
        ...,
        "--content",
        "-c",
        help="Natural language policy description",
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
) -> None:
    r"""Start a policy generation workflow.

    Example:
        agentcore policy start-generation \\
            --engine-id "testPolicyEngine-abc123" \\
            --name "refund-policy-generation" \\
            --resource-arn "arn:aws:bedrock-agentcore:us-east-1:123456789:gateway/my-gateway" \\
            --content "Allow refunds under $1000"
    """
    client = PolicyClient(region_name=region)

    resource = {"arn": resource_arn}
    content_obj = {"rawText": content}

    response = client.start_policy_generation(
        policy_engine_id=policy_engine_id,
        name=name,
        resource=resource,
        content=content_obj,
    )
    console.print("[green]✓ Policy generation initiated![/green]")
    console.print(f"[bold]Generation ID:[/bold] {response.get('policyGenerationId', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    console.print(f"[bold]Name:[/bold] {response.get('name', 'N/A')}")
    console.print("[dim]Use 'get-policy-generation' to check progress[/dim]")
    if response.get("policyGenerationArn"):
        console.print(f"[bold]ARN:[/bold] [dim]{response['policyGenerationArn']}[/dim]")


@policy_app.command("get-policy-generation")
def get_policy_generation(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    generation_id: str = typer.Option(..., "--generation-id", "-g", help="Generation ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
) -> None:
    """Get policy generation details."""
    client = PolicyClient(region_name=region)
    response = client.get_policy_generation(policy_engine_id, generation_id)
    console.print("\n[bold cyan]Policy Generation Details:[/bold cyan]")
    console.print(f"[bold]Generation ID:[/bold] {response.get('policyGenerationId', 'N/A')}")
    console.print(f"[bold]Name:[/bold] {response.get('name', 'N/A')}")
    console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
    if response.get("policyGenerationArn"):
        console.print(f"[bold]ARN:[/bold] [dim]{response['policyGenerationArn']}[/dim]")
    if response.get("createdAt"):
        console.print(f"[bold]Created:[/bold] {response['createdAt']}")
    if response.get("updatedAt"):
        console.print(f"[bold]Updated:[/bold] {response['updatedAt']}")


@policy_app.command("list-policy-generation-assets")
def get_policy_generation_assets(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    generation_id: str = typer.Option(..., "--generation-id", "-g", help="Generation ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    max_results: Optional[int] = typer.Option(None, "--max-results", help="Maximum number of results"),
    next_token: Optional[str] = typer.Option(None, "--next-token", help="Token for pagination"),
) -> None:
    """Get policy generation assets (generated policies)."""
    client = PolicyClient(region_name=region)
    response = client.list_policy_generation_assets(policy_engine_id, generation_id, max_results, next_token)

    # Filter out ResponseMetadata to show only relevant data
    filtered_response = {"policyGenerationAssets": response.get("policyGenerationAssets", [])}
    if "nextToken" in response:
        filtered_response["nextToken"] = response["nextToken"]

    console.print(json.dumps(filtered_response, indent=2, default=str))


@policy_app.command("list-policy-generations")
def list_policy_generations(
    policy_engine_id: str = typer.Option(..., "--engine-id", "-e", help="Policy engine ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: us-east-1)"),
    max_results: Optional[int] = typer.Option(None, "--max-results", help="Maximum number of results"),
    next_token: Optional[str] = typer.Option(None, "--next-token", help="Token for pagination"),
) -> None:
    """List policy generations."""
    from rich.table import Table

    client = PolicyClient(region_name=region)
    response = client.list_policy_generations(
        policy_engine_id=policy_engine_id,
        max_results=max_results,
        next_token=next_token,
    )

    generations = response.get("policyGenerations", [])

    if not generations:
        console.print("[yellow]No policy generations found.[/yellow]")
        return

    table = Table(title=f"Policy Generations ({len(generations)})")
    table.add_column("Generation ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created At", style="blue")

    for gen in generations:
        table.add_row(
            gen.get("policyGenerationId", "N/A"),
            gen.get("name", "N/A"),
            gen.get("status", "N/A"),
            str(gen.get("createdAt", "N/A")),
        )

    console.print(table)

    if response.get("nextToken"):
        console.print(f"\n[dim]Next token:[/dim] {response['nextToken']}")


if __name__ == "__main__":
    policy_app()
