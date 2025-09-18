"""Configuration management for BedrockAgentCore runtime."""

import os
from pathlib import Path
from typing import Dict, Optional

from ..common import _handle_error, _print_success, _prompt_with_default, console


class ConfigurationManager:
    """Manages interactive configuration prompts with existing configuration defaults."""

    def __init__(self, config_path: Path, non_interactive: bool = False):
        """Initialize the ConfigPrompt with a configuration path.

        Args:
            config_path: Path to the configuration file
            non_interactive: If True, use defaults without prompting
        """
        from ...utils.runtime.config import load_config_if_exists

        project_config = load_config_if_exists(config_path)
        self.existing_config = project_config.get_agent_config() if project_config else None
        self.non_interactive = non_interactive

    def prompt_execution_role(self) -> Optional[str]:
        """Prompt for execution role. Returns role name/ARN or None for auto-creation."""
        if self.non_interactive:
            _print_success("Will auto-create execution role")
            return None

        console.print("\n🔐 [cyan]Execution Role[/cyan]")
        console.print(
            "[dim]Press Enter to auto-create execution role, or provide execution role ARN/name to use existing[/dim]"
        )

        # Show existing config info but don't use as default
        if self.existing_config and self.existing_config.aws.execution_role:
            console.print(f"[dim]Previously configured: {self.existing_config.aws.execution_role}[/dim]")

        role = _prompt_with_default("Execution role ARN/name (or press Enter to auto-create)", "")

        if role:
            _print_success(f"Using existing execution role: [dim]{role}[/dim]")
            return role
        else:
            _print_success("Will auto-create execution role")
            return None

    def prompt_ecr_repository(self) -> tuple[Optional[str], bool]:
        """Prompt for ECR repository. Returns (repository, auto_create_flag)."""
        if self.non_interactive:
            _print_success("Will auto-create ECR repository")
            return None, True

        console.print("\n🏗️  [cyan]ECR Repository[/cyan]")
        console.print(
            "[dim]Press Enter to auto-create ECR repository, or provide ECR Repository URI to use existing[/dim]"
        )

        # Show existing config info but don't use as default
        if self.existing_config and self.existing_config.aws.ecr_repository:
            console.print(f"[dim]Previously configured: {self.existing_config.aws.ecr_repository}[/dim]")

        response = _prompt_with_default("ECR Repository URI (or press Enter to auto-create)", "")

        if response:
            _print_success(f"Using existing ECR repository: [dim]{response}[/dim]")
            return response, False
        else:
            _print_success("Will auto-create ECR repository")
            return None, True

    def prompt_oauth_config(self) -> Optional[dict]:
        """Prompt for OAuth configuration. Returns OAuth config dict or None."""
        if self.non_interactive:
            _print_success("Using default IAM authorization")
            return None

        console.print("\n🔐 [cyan]Authorization Configuration[/cyan]")
        console.print("[dim]By default, Bedrock AgentCore uses IAM authorization.[/dim]")

        existing_oauth = self.existing_config and self.existing_config.authorizer_configuration
        oauth_default = "yes" if existing_oauth else "no"

        response = _prompt_with_default("Configure OAuth authorizer instead? (yes/no)", oauth_default)

        if response.lower() in ["yes", "y"]:
            return self._configure_oauth()
        else:
            _print_success("Using default IAM authorization")
            return None

    def _configure_oauth(self) -> dict:
        """Configure OAuth settings and return config dict."""
        console.print("\n📋 [cyan]OAuth Configuration[/cyan]")

        # Get existing OAuth values
        existing_discovery_url = ""
        existing_client_ids = ""
        existing_audience = ""

        if (
            self.existing_config
            and self.existing_config.authorizer_configuration
            and "customJWTAuthorizer" in self.existing_config.authorizer_configuration
        ):
            jwt_config = self.existing_config.authorizer_configuration["customJWTAuthorizer"]
            existing_discovery_url = jwt_config.get("discoveryUrl", "")
            existing_client_ids = ",".join(jwt_config.get("allowedClients", []))
            existing_audience = ",".join(jwt_config.get("allowedAudience", []))

        # Prompt for discovery URL
        default_discovery_url = existing_discovery_url or os.getenv("BEDROCK_AGENTCORE_DISCOVERY_URL", "")
        discovery_url = _prompt_with_default("Enter OAuth discovery URL", default_discovery_url)

        if not discovery_url:
            _handle_error("OAuth discovery URL is required")

        # Prompt for client IDs
        default_client_id = existing_client_ids or os.getenv("BEDROCK_AGENTCORE_CLIENT_ID", "")
        client_ids_input = _prompt_with_default("Enter allowed OAuth client IDs (comma-separated)", default_client_id)
        # Prompt for audience
        default_audience = existing_audience or os.getenv("BEDROCK_AGENTCORE_AUDIENCE", "")
        audience_input = _prompt_with_default("Enter allowed OAuth audience (comma-separated)", default_audience)

        if not client_ids_input and not audience_input:
            _handle_error("At least one client ID or one audience is required for OAuth configuration")

        # Parse and return config
        client_ids = [cid.strip() for cid in client_ids_input.split(",") if cid.strip()]
        audience = [aud.strip() for aud in audience_input.split(", ") if aud.strip()]

        config: Dict = {
            "customJWTAuthorizer": {
                "discoveryUrl": discovery_url,
            }
        }

        if client_ids:
            config["customJWTAuthorizer"]["allowedClients"] = client_ids

        if audience:
            config["customJWTAuthorizer"]["allowedAudience"] = audience

        _print_success("OAuth authorizer configuration created")
        return config
