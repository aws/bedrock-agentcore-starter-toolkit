"""Identity CLI commands for credential provider management and workload identity."""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import typer
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ...operations.identity.helpers import (
    IdentityCognitoManager,
    get_cognito_access_token,
    get_cognito_m2m_token,
    update_cognito_callback_urls,
)
from ...utils.aws import get_region
from ...utils.runtime.config import load_config, save_config
from ..common import _handle_error, _handle_warn, _print_success, console

# Identity CLI app
identity_app = typer.Typer(help="Manage Identity service resources")

logger = logging.getLogger(__name__)


@identity_app.command("create-credential-provider")
def create_credential_provider(
    name: str = typer.Option(..., "--name", "-n", help="Credential provider name"),
    provider_type: str = typer.Option(..., "--type", "-t", help="Provider type: cognito, github, google, salesforce"),
    client_id: str = typer.Option(..., "--client-id", help="OAuth client ID"),
    client_secret: str = typer.Option(..., "--client-secret", help="OAuth client secret"),
    discovery_url: Optional[str] = typer.Option(
        None, "--discovery-url", help="OAuth discovery URL (required for cognito)"
    ),
    cognito_pool_id: Optional[str] = typer.Option(
        None, "--cognito-pool-id", help="Cognito pool ID (for auto-updating callback URLs)"
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
):
    r"""Create an OAuth2 credential provider for outbound authentication (3LO support).

    This command:
    1. Creates credential provider in Identity service
    2. Returns AgentCore's callback URL that MUST be registered with your IdP
    3. Optionally auto-updates Cognito callback URLs (if --cognito-pool-id provided)
    4. Saves configuration to .bedrock_agentcore.yaml

    Examples:
        # Create Cognito provider (auto-updates callback URLs)
        agentcore identity create-credential-provider --name MyCognito --type cognito \
            --client-id abc123 --client-secret xyz789 \
            --discovery-url https://cognito-idp.us-west-2.amazonaws.com/\
us-west-2_xxx/.well-known/openid-configuration \
            --cognito-pool-id us-west-2_xxx

        # Create GitHub provider
        agentcore identity create-credential-provider --name MyGitHub --type github \
            --client-id abc123 --client-secret xyz789
    """
    try:
        from bedrock_agentcore.services.identity import IdentityClient

        region = region or get_region()
        console.print(f"[cyan]Creating {provider_type} credential provider '{name}' in {region}...[/cyan]")

        # Build provider config based on type
        provider_config = _build_provider_config(provider_type, name, client_id, client_secret, discovery_url)

        # Create provider using SDK
        identity_client = IdentityClient(region)
        response = identity_client.create_oauth2_credential_provider(provider_config)

        provider_arn = response.get("credentialProviderArn", "")
        agentcore_callback_url = response.get("callbackUrl", "")

        # ⭐ CRITICAL: Handle AgentCore's callback URL
        if agentcore_callback_url:
            console.print("\n[yellow]⚠️  Important: AgentCore Callback URL[/yellow]")
            console.print(f"[dim]{agentcore_callback_url}[/dim]\n")

            # If Cognito pool provided, auto-update callback URLs
            if cognito_pool_id and provider_type == "cognito":
                console.print(
                    f"[cyan]Auto-updating Cognito pool {cognito_pool_id} with AgentCore callback URL...[/cyan]"
                )
                try:
                    update_cognito_callback_urls(
                        pool_id=cognito_pool_id, client_id=client_id, callback_url=agentcore_callback_url, region=region
                    )
                    _print_success("Cognito pool updated with callback URL")
                except Exception as e:
                    _handle_warn(f"Failed to auto-update Cognito callback URLs: {e}")
                    console.print(
                        "\n[yellow]You must manually add this callback URL to your Cognito app client:[/yellow]"
                    )
                    console.print("[cyan]1. Go to Cognito Console → User Pool → App Client[/cyan]")
                    console.print(f"[cyan]2. Add callback URL: {agentcore_callback_url}[/cyan]\n")
            else:
                # Guide user to register callback URL manually
                console.print(
                    Panel(
                        f"[bold yellow]⚠️  ACTION REQUIRED[/bold yellow]\n\n"
                        f"You MUST register this callback URL with your Identity Provider:\n\n"
                        f"[cyan]{agentcore_callback_url}[/cyan]\n\n"
                        f"For Cognito:\n"
                        f"  • Go to AWS Console → Cognito → User Pool\n"
                        f"  • Select App Client → Edit Hosted UI settings\n"
                        f"  • Add the callback URL above to 'Allowed callback URLs'\n\n"
                        f"For other providers (GitHub, Google, etc.):\n"
                        f"  • Add this URL to your OAuth app's authorized redirect URIs",
                        title="⚠️ Callback URL Registration Required",
                        border_style="yellow",
                    )
                )

        # Store in .bedrock_agentcore.yaml
        _save_provider_config(name, provider_arn, provider_type, agentcore_callback_url)

        # Success message
        console.print(
            Panel(
                f"[bold]Credential Provider Created[/bold]\n\n"
                f"Name: [cyan]{name}[/cyan]\n"
                f"Type: [cyan]{provider_type}[/cyan]\n"
                f"ARN: [dim]{provider_arn}[/dim]\n"
                f"Callback URL: [dim]{agentcore_callback_url or 'N/A'}[/dim]\n\n"
                f"✅ Configuration saved to .bedrock_agentcore.yaml\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   1. Ensure callback URL is registered with your IdP\n"
                f"   2. Create/update workload identity with your app's callback URLs\n"
                f"   3. [cyan]agentcore launch[/cyan]  # Permissions auto-added",
                title="✅ Success",
                border_style="green",
            )
        )

    except Exception as e:
        _handle_error(f"Failed to create credential provider: {str(e)}", e)


@identity_app.command("create-workload-identity")
def create_workload_identity(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Workload identity name (auto-generated if empty)"),
    return_urls: Optional[str] = typer.Option(
        None,
        "--return-urls",
        help="Optional: OAuth return URLs for enhanced session binding security. Not required for basic OAuth flows.",
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
):
    """Create a workload identity for your agent.

    A workload identity represents your agent and must be created before the agent can
    obtain OAuth2 tokens. You must specify callback URLs where OAuth providers will
    redirect users after authorization.

    Examples:
        # Create with local callback URL
        agentcore identity create-workload --name MyAgent \
            --return-urls http://localhost:8081/oauth2/callback

        # Create with multiple callback URLs (local + production)
        agentcore identity create-workload --name MyAgent \
            --return-urls http://localhost:8081/oauth2/callback,https://prod.example.com/callback
    """
    try:
        from bedrock_agentcore.services.identity import IdentityClient

        region = region or get_region()

        # Parse return URLs
        return_url_list = []
        if return_urls:
            return_url_list = [url.strip() for url in return_urls.split(",")]

        # Auto-generate name if not provided
        if not name:
            # Try to get from config
            config_path = Path.cwd() / ".bedrock_agentcore.yaml"
            if config_path.exists():
                project_config = load_config(config_path)
                agent_config = project_config.get_agent_config()
                name = f"{agent_config.name}-workload"
            else:
                import uuid

                name = f"workload-{uuid.uuid4().hex[:8]}"

        console.print(f"[cyan]Creating workload identity '{name}' in {region}...[/cyan]")

        identity_client = IdentityClient(region)
        response = identity_client.create_workload_identity(
            name=name, allowed_resource_oauth_2_return_urls=return_url_list
        )

        workload_arn = response.get("workloadIdentityArn", "")

        # Store in config
        _save_workload_config(name, workload_arn, return_url_list)

        # Display result
        table = Table(title="Workload Identity Created")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Name", name)
        table.add_row("ARN", workload_arn)
        if return_url_list:
            table.add_row("Callback URLs", "\n".join(return_url_list))

        console.print(table)
        _print_success("Workload identity created and saved to .bedrock_agentcore.yaml")

    except Exception as e:
        _handle_error(f"Failed to create workload identity: {repr(e)}", e)


@identity_app.command("update-workload-identity")
def update_workload_identity(
    name: str = typer.Option(..., "--name", "-n", help="Workload identity name"),
    add_return_urls: Optional[str] = typer.Option(None, "--add-return-urls", help="Comma-separated return URLs to ADD"),
    set_return_urls: Optional[str] = typer.Option(
        None, "--set-return-urls", help="Comma-separated return URLs to SET (replaces existing)"
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
):
    r"""Update workload identity callback URLs.

    Use --add-return-urls to append new URLs to existing ones.
    Use --set-return-urls to replace all existing URLs.

    Examples:
        # Add a production return URL
        agentcore identity update-workload --name MyAgent-workload \
            --add-return-urls https://prod.example.com/callback

        # Replace all return URLs
        agentcore identity update-workload --name MyAgent-workload \
            --set-return-urls http://localhost:8081/callback,https://prod.example.com/callback
    """
    try:
        from bedrock_agentcore.services.identity import IdentityClient

        region = region or get_region()
        identity_client = IdentityClient(region)

        # Get current workload identity
        current_workload = identity_client.get_workload_identity(name)
        current_urls = current_workload.get("allowedResourceOauth2ReturnUrls", [])

        # Determine new callback URLs
        if set_return_urls:
            new_urls = [url.strip() for url in set_return_urls.split(",")]
        elif add_return_urls:
            additional_urls = [url.strip() for url in add_return_urls.split(",")]
            new_urls = list(set(current_urls + additional_urls))  # Remove duplicates
        else:
            _handle_error("Must provide either --add-return-urls or --set-return-urls")

        console.print(f"[cyan]Updating workload identity '{name}'...[/cyan]")

        # Update workload identity
        identity_client.update_workload_identity(name=name, allowed_resource_oauth_2_return_urls=new_urls)

        # Update config
        _save_workload_config(name, current_workload.get("workloadIdentityArn", ""), new_urls)

        # Display result
        table = Table(title="Workload Identity Updated")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Name", name)
        table.add_row("Previous URLs", "\n".join(current_urls) if current_urls else "[dim]None[/dim]")
        table.add_row("New URLs", "\n".join(new_urls))

        console.print(table)
        _print_success("Workload identity updated")

    except Exception as e:
        _handle_error(f"Failed to update workload identity: {str(e)}", e)


@identity_app.command("get-cognito-inbound-token")
def get_cognito_inbound_token(
    auth_flow: str = typer.Option(
        "user", "--auth-flow", help="OAuth flow type: 'user' (USER_FEDERATION) or 'm2m' (M2M)"
    ),
    pool_id: Optional[str] = typer.Option(
        None, "--pool-id", help="Cognito User Pool ID (auto-loads from RUNTIME_POOL_ID env var)"
    ),
    client_id: Optional[str] = typer.Option(
        None, "--client-id", help="Cognito App Client ID (auto-loads from RUNTIME_CLIENT_ID env var)"
    ),
    client_secret: Optional[str] = typer.Option(
        None, "--client-secret", help="Client secret (auto-loads from RUNTIME_CLIENT_SECRET env var, required for m2m)"
    ),
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Username (auto-loads from RUNTIME_USERNAME env var, required for user flow)"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password (auto-loads from RUNTIME_PASSWORD env var, required for user flow)"
    ),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
):
    """Get an access token from Cognito for Runtime inbound authentication.

    Supports USER_FEDERATION and M2M flows. Auto-loads credentials from environment.

    Examples:
        # Auto-load from environment (user flow)
        export $(grep -v '^#' .agentcore_identity_user.env | xargs)
        TOKEN=$(agentcore identity get-cognito-inbound-token)

        # Auto-load from environment (m2m flow)
        export $(grep -v '^#' .agentcore_identity_m2m.env | xargs)
        TOKEN=$(agentcore identity get-cognito-inbound-token --auth-flow m2m)

        # Explicit parameters (overrides env)
        TOKEN=$(agentcore identity get-cognito-inbound-token \
                 --pool-id us-west-2_xxx --client-id abc123 \
                 --username user --password pass)
    """
    try:
        import os

        region = region or get_region()

        # Validate flow type
        if auth_flow not in ["user", "m2m"]:
            _handle_error("--auth-flow must be 'user' or 'm2m'")

        # Auto-load from environment (explicit parameters override)
        pool_id = pool_id or os.getenv("RUNTIME_POOL_ID")
        client_id = client_id or os.getenv("RUNTIME_CLIENT_ID")
        client_secret = client_secret or os.getenv("RUNTIME_CLIENT_SECRET")
        username = username or os.getenv("RUNTIME_USERNAME")
        password = password or os.getenv("RUNTIME_PASSWORD")

        # Validate required parameters
        if not pool_id:
            _handle_error(
                "Cognito pool ID required. Either:\n"
                "  1. Set RUNTIME_POOL_ID environment variable, or\n"
                "  2. Provide --pool-id parameter"
            )

        if not client_id:
            _handle_error(
                "Cognito client ID required. Either:\n"
                "  1. Set RUNTIME_CLIENT_ID environment variable, or\n"
                "  2. Provide --client-id parameter"
            )

        # Flow-specific validation and token retrieval
        if auth_flow == "user":
            if not username:
                _handle_error(
                    "Username required for USER flow. Either:\n"
                    "  1. Set RUNTIME_USERNAME environment variable, or\n"
                    "  2. Provide --username parameter"
                )

            if not password:
                _handle_error(
                    "Password required for USER flow. Either:\n"
                    "  1. Set RUNTIME_PASSWORD environment variable, or\n"
                    "  2. Provide --password parameter"
                )

            # Get token using USER_PASSWORD_AUTH
            token = get_cognito_access_token(
                pool_id=pool_id,
                client_id=client_id,
                username=username,
                password=password,
                client_secret=client_secret,
                region=region,
            )

        else:  # m2m
            if not client_secret:
                _handle_error(
                    "Client secret required for M2M flow. Either:\n"
                    "  1. Set RUNTIME_CLIENT_SECRET environment variable, or\n"
                    "  2. Provide --client-secret parameter"
                )

            # Get token using CLIENT_CREDENTIALS
            token = get_cognito_m2m_token(
                pool_id=pool_id,
                client_id=client_id,
                client_secret=client_secret,
                region=region,
            )

        # Print only the token
        print(token)

    except Exception as e:
        _handle_error(f"Failed to get token: {repr(e)}", e)


@identity_app.command("list-credential-providers")
def list_credential_providers():
    """List configured credential providers from .bedrock_agentcore.yaml."""
    try:
        config_path = Path.cwd() / ".bedrock_agentcore.yaml"
        if not config_path.exists():
            console.print("[yellow]No .bedrock_agentcore.yaml found. Run 'agentcore configure' first.[/yellow]")
            raise typer.Exit(1)

        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config()

        if (
            not hasattr(agent_config, "identity")
            or not agent_config.identity
            or not agent_config.identity.credential_providers
        ):
            console.print("[yellow]No credential providers configured.[/yellow]")
            console.print("Run [cyan]agentcore identity create-credential-provider[/cyan] to add one.")
            raise typer.Exit(0)

        table = Table(title="Configured Credential Providers")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("ARN", style="dim")
        table.add_column("Callback URL", style="green")

        for provider in agent_config.identity.credential_providers:
            callback_url = getattr(provider, "callback_url", "N/A")
            callback_display = (
                callback_url[:50] + "..."
                if hasattr(provider, "callback_url") and len(provider.callback_url) > 50
                else callback_url
            )
            table.add_row(
                provider.name,
                provider.type,
                provider.arn[:50] + "..." if len(provider.arn) > 50 else provider.arn,
                callback_display,
            )

        console.print(table)

        # Show workload info if available
        if (
            hasattr(agent_config, "identity")
            and hasattr(agent_config.identity, "workload")
            and agent_config.identity.workload is not None
        ):
            workload = agent_config.identity.workload
            console.print(f"\n[cyan]Workload Identity:[/cyan] {workload.name}")
            if hasattr(workload, "return_urls") and workload.return_urls:
                console.print("[cyan]App Return URLs:[/cyan]")
                for url in workload.return_urls:
                    console.print(f"  • {url}")

    except Exception as e:
        _handle_error(f"Failed to list providers: {str(e)}", e)


def _build_provider_config(
    provider_type: str, name: str, client_id: str, client_secret: str, discovery_url: Optional[str]
) -> dict:
    """Build provider configuration based on type."""
    if provider_type == "cognito":
        if not discovery_url:
            _handle_error(f"--discovery-url required for {provider_type} provider type")

        return {
            "name": name,
            "credentialProviderVendor": "CustomOauth2",
            "oauth2ProviderConfigInput": {
                "customOauth2ProviderConfig": {
                    "oauthDiscovery": {"discoveryUrl": discovery_url},
                    "clientId": client_id,
                    "clientSecret": client_secret,
                }
            },
        }

    elif provider_type == "github":
        return {
            "name": name,
            "credentialProviderVendor": "GithubOauth2",
            "oauth2ProviderConfigInput": {
                "githubOauth2ProviderConfig": {"clientId": client_id, "clientSecret": client_secret}
            },
        }

    elif provider_type == "google":
        return {
            "name": name,
            "credentialProviderVendor": "GoogleOauth2",
            "oauth2ProviderConfigInput": {
                "googleOauth2ProviderConfig": {"clientId": client_id, "clientSecret": client_secret}
            },
        }

    elif provider_type == "salesforce":
        return {
            "name": name,
            "credentialProviderVendor": "SalesforceOauth2",
            "oauth2ProviderConfigInput": {
                "salesforceOauth2ProviderConfig": {"clientId": client_id, "clientSecret": client_secret}
            },
        }

    else:
        _handle_error(
            f"Unsupported provider type: {provider_type}.\n"
            f"Supported by this CLI: cognito, github, google, salesforce\n"
            f"Note: Identity supports additional providers (Atlassian, Slack, etc.) via custom-oauth2. "
            f"See AWS documentation for full list."
        )


def _save_provider_config(name: str, arn: str, provider_type: str, callback_url: str):
    """Save provider configuration to .bedrock_agentcore.yaml."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    if config_path.exists():
        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config()

        # Initialize identity config if not present
        if not hasattr(agent_config, "identity") or not agent_config.identity:
            from ...utils.runtime.schema import IdentityConfig

            agent_config.identity = IdentityConfig()

        # Add provider
        from ...utils.runtime.schema import CredentialProviderInfo

        agent_config.identity.credential_providers.append(
            CredentialProviderInfo(name=name, arn=arn, type=provider_type, callback_url=callback_url)
        )

        # Save config
        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)
    else:
        _handle_warn(".bedrock_agentcore.yaml not found. Provider created but not saved to config.")


def _save_workload_config(name: str, arn: str, return_urls: List[str]):
    """Save workload identity configuration to .bedrock_agentcore.yaml."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    if config_path.exists():
        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config()

        # Initialize identity config if not present
        if not hasattr(agent_config, "identity") or not agent_config.identity:
            from ...utils.runtime.schema import IdentityConfig

            agent_config.identity = IdentityConfig()

        # Set workload info
        from ...utils.runtime.schema import WorkloadIdentityInfo

        agent_config.identity.workload = WorkloadIdentityInfo(name=name, arn=arn, return_urls=return_urls)

        # Save config
        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)


@identity_app.command("setup-cognito")
def setup_cognito(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (defaults to configured region)"),
    auth_flow: str = typer.Option(
        "user", "--auth-flow", help="Identity pool OAuth flow type: user (USER_FEDERATION) or m2m (client_credentials)"
    ),
):
    """Create Cognito user pools for Identity authentication.

    Creates two user pools:
    - Runtime Pool: For agent inbound JWT authentication
    - Identity Pool: For agent outbound OAuth to external services

    Auth Flow Types:
    - user: USER_FEDERATION flow with user consent (default)
    - m2m: Machine-to-machine with client credentials

    Configuration is saved and automatically used by subsequent commands.
    """
    from pathlib import Path

    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    # Determine region
    if not region:
        if config_path.exists():
            project_config = load_config(config_path)
            # Get region from first agent or default
            if project_config.agents:
                first_agent = list(project_config.agents.values())[0]
                region = first_agent.aws.region

        if not region:
            # Fall back to AWS CLI default
            import boto3

            session = boto3.Session()
            region = session.region_name or "us-west-2"

    # Validate flow type
    if auth_flow not in ["user", "m2m"]:
        console.print("[red]Error: --auth-flow must be 'user' or 'm2m'[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Creating Cognito pools in region:[/bold] {region}\n")
    console.print(f"[bold]Identity auth flow type:[/bold] {auth_flow}\n")

    # Create the pools
    manager = IdentityCognitoManager(region)

    # Call appropriate method based on flow type
    if auth_flow == "user":
        result = manager.create_user_federation_pools()
    else:  # m2m
        result = manager.create_m2m_pools()

    # Save to a temporary config file for later use
    # Save to config file
    cognito_config_path = Path.cwd() / f".agentcore_identity_cognito_{auth_flow}.json"
    with open(cognito_config_path, "w") as f:
        json.dump(result, f, indent=2)

    # Also save as shell script for easy sourcing
    env_file_path = Path.cwd() / f".agentcore_identity_{auth_flow}.env"
    with open(env_file_path, "w") as f:
        f.write("# AgentCore Identity Environment Variables\n")
        f.write(f"# To load: export $(grep -v '^#' .agentcore_identity_{auth_flow}.env | xargs)\n\n")
        f.write("# Runtime Pool (Inbound Auth)\n")
        f.write(f"RUNTIME_POOL_ID={result['runtime']['pool_id']}\n")
        f.write(f"RUNTIME_CLIENT_ID={result['runtime']['client_id']}\n")
        f.write(f"RUNTIME_DISCOVERY_URL={result['runtime']['discovery_url']}\n")
        f.write(f"RUNTIME_USERNAME={result['runtime']['username']}\n")
        f.write(f"RUNTIME_PASSWORD={result['runtime']['password']}\n")
        f.write("\n# Identity Pool (Outbound Auth)\n")
        if auth_flow == "user":
            f.write(f"IDENTITY_POOL_ID={result['identity']['pool_id']}\n")
            f.write(f"IDENTITY_CLIENT_ID={result['identity']['client_id']}\n")
            f.write(f"IDENTITY_CLIENT_SECRET={result['identity']['client_secret']}\n")
            f.write(f"IDENTITY_DISCOVERY_URL={result['identity']['discovery_url']}\n")
            f.write(f"IDENTITY_USERNAME={result['identity']['username']}\n")
            f.write(f"IDENTITY_PASSWORD={result['identity']['password']}\n")

        elif auth_flow == "m2m":
            f.write(f"IDENTITY_POOL_ID={result['identity']['pool_id']}\n")
            f.write(f"IDENTITY_CLIENT_ID={result['identity']['client_id']}\n")
            f.write(f"IDENTITY_CLIENT_SECRET={result['identity']['client_secret']}\n")
            f.write(f"IDENTITY_TOKEN_ENDPOINT={result['identity']['token_endpoint']}\n")
            f.write(f"IDENTITY_RESOURCE_SERVER={result['identity']['resource_server_identifier']}\n")

    # Make script executable
    os.chmod(env_file_path, 0o600)  # Read/write for owner only (secure)

    console.print()
    console.print("[bold green]✅ Cognito pools created successfully![/bold green]\n")

    # Display non-sensitive summary
    runtime_panel = Panel(
        f"[bold]Pool ID:[/bold] {result['runtime']['pool_id']}\n"
        f"[bold]Client ID:[/bold] {result['runtime']['client_id']}\n"
        f"[bold]Discovery URL:[/bold] {result['runtime']['discovery_url']}\n"
        f"[bold]Test User:[/bold] {result['runtime']['username']}",
        title="[bold cyan]Runtime Pool (Inbound Auth)[/bold cyan]",
        border_style="cyan",
    )
    console.print(runtime_panel)
    console.print()

    # Display Identity User Pool if created
    identity_panel = Panel(
        f"[bold]Pool ID:[/bold] {result['identity']['pool_id']}\n"
        f"[bold]Client ID:[/bold] {result['identity']['client_id']}\n"
        f"[bold]Flow Type:[/bold] {auth_flow.upper()}\n"
        + (
            f"[bold]Discovery URL:[/bold] {result['identity']['discovery_url']}\n"
            f"[bold]Test User:[/bold] {result['identity']['username']}"
            if auth_flow == "user"
            else f"[bold]Token Endpoint:[/bold] {result['identity']['token_endpoint']}\n"
            f"[bold]Resource Server:[/bold] {result['identity']['resource_server_identifier']}"
        ),
        title=f"[bold green]Identity Pool - {('User Consent' if auth_flow == 'user' else 'M2M')}[/bold green]",
        border_style="green",
    )
    console.print(identity_panel)
    console.print()

    # Show where secrets are stored
    console.print("[bold yellow]🔐 Credentials saved securely to:[/bold yellow]")
    console.print(f"   • {cognito_config_path} (JSON format)")
    console.print(f"   • {env_file_path} (standard .env format)")
    console.print()

    # Show how to load variables
    console.print("[bold]To load environment variables:[/bold]")
    console.print()
    console.print("Bash/Zsh:")
    load_cmd = f"export $(grep -v '^#' .agentcore_identity_{auth_flow}.env | xargs)"
    syntax = Syntax(load_cmd, "bash", theme="monokai", line_numbers=False)
    console.print(syntax)
    console.print()


@identity_app.command("cleanup")
def cleanup_identity(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name to clean up Identity resources for"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean up Identity resources for an agent.

    Removes:
    - Credential providers
    - Workload identities
    - Cognito pools (if created by setup-cognito)
    - IAM inline policies
    """
    from pathlib import Path

    from bedrock_agentcore.services.identity import IdentityClient

    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    if not config_path.exists():
        console.print("[red]Error: No .bedrock_agentcore.yaml found[/red]")
        raise typer.Exit(1)

    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent)
    region = agent_config.aws.region

    # Check what exists for confirmation display
    cognito_files_found = []
    for flow in ["user", "m2m"]:
        config_file = Path.cwd() / f".agentcore_identity_cognito_{flow}.json"
        if config_file.exists():
            cognito_files_found.append(flow)

    # Confirm deletion
    if not force:
        console.print(f"\n[bold red]⚠️  This will delete Identity resources for agent:[/bold red] {agent_config.name}")
        console.print("\nResources to be deleted:")

        if agent_config.identity and agent_config.identity.credential_providers:
            console.print(f"  • {len(agent_config.identity.credential_providers)} credential provider(s)")

        if agent_config.identity and agent_config.identity.workload:
            console.print(f"  • Workload identity: {agent_config.identity.workload.name}")

        if cognito_files_found:
            console.print(f"  • Cognito user pools ({', '.join(cognito_files_found)} flow)")

        if not typer.confirm("\nProceed with deletion?", default=False):
            console.print("Cancelled")
            raise typer.Exit(0)

    console.print("\n[bold]Cleaning up Identity resources...[/bold]\n")

    identity_client = IdentityClient(region)

    # Delete credential providers
    if agent_config.identity and agent_config.identity.credential_providers:
        for provider in agent_config.identity.credential_providers:
            try:
                console.print(f"  • Deleting credential provider: {provider.name}")
                identity_client.cp_client.delete_oauth2_credential_provider(name=provider.name)
                console.print("    ✓ Deleted")
            except identity_client.cp_client.exceptions.ResourceNotFoundException:
                console.print("    ✓ Already deleted or never existed")
            except Exception as e:
                console.print(f"    :warning:  Error: {repr(e)}")

    # Delete workload identity
    if agent_config.identity and agent_config.identity.workload:
        try:
            console.print(f"  • Deleting workload identity: {agent_config.identity.workload.name}")
            identity_client.identity_client.delete_workload_identity(name=agent_config.identity.workload.name)
            console.print("    ✓ Deleted")
        except identity_client.identity_client.exceptions.ResourceNotFoundException:
            console.print("    ✓ Already deleted or never existed")
        except Exception as e:
            console.print(f"    ⚠️  Error: {repr(e)}")

    # Delete Cognito pools for each flow type found
    for flow in ["user", "m2m"]:
        cognito_config_path = Path.cwd() / f".agentcore_identity_cognito_{flow}.json"
        env_file_path = Path.cwd() / f".agentcore_identity_{flow}.env"

        if cognito_config_path.exists():
            try:
                with open(cognito_config_path) as f:
                    cognito_config = json.load(f)

                console.print(f"  • Deleting Cognito pools ({flow} flow)...")
                manager = IdentityCognitoManager(region)
                manager.cleanup_cognito_pools(
                    runtime_pool_id=cognito_config["runtime"]["pool_id"],
                    identity_pool_id=cognito_config["identity"]["pool_id"],
                )
                console.print("    ✓ Deleted Cognito pools")

                # Delete config files
                cognito_config_path.unlink()
                console.print(f"    ✓ Deleted {flow} config file")

                if env_file_path.exists():
                    env_file_path.unlink()
                    console.print(f"    ✓ Deleted {flow} environment file")

            except Exception as e:
                console.print(f"    ⚠️  Error cleaning up {flow} flow: {str(e)}")

    # Clear Identity config from agent
    if agent_config.identity:
        agent_config.identity.credential_providers = []
        agent_config.identity.workload = None

    project_config.agents[agent_config.name] = agent_config
    save_config(project_config, config_path)

    console.print("\n[bold green]✅ Identity cleanup complete[/bold green]")
