"""Configuration management for BedrockAgentCore runtime."""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..common import _handle_error, _print_success, _prompt_with_default, console


class ConfigurationManager:
    """Manages interactive configuration prompts with existing configuration defaults."""

    def __init__(self, config_path: Path, non_interactive: bool = False, region: Optional[str] = None):
        """Initialize the ConfigPrompt with a configuration path.

        Args:
            config_path: Path to the configuration file
            non_interactive: If True, use defaults without prompting
            region: AWS region for checking existing memories (optional, from configure operation)
        """
        from ...utils.runtime.config import load_config_if_exists

        project_config = load_config_if_exists(config_path)
        self.existing_config = project_config.get_agent_config() if project_config else None
        self.non_interactive = non_interactive
        self.region = region

    def prompt_agent_name(self, suggested_name: str) -> str:
        """Prompt for agent name with a suggested default.

        Args:
            suggested_name: The suggested agent name based on entrypoint path

        Returns:
            The selected or entered agent name
        """
        if self.non_interactive:
            _print_success(f"Agent name (inferred): {suggested_name}")
            return suggested_name

        console.print(f"\n🏷️  [cyan]Inferred agent name[/cyan]: {suggested_name}")
        console.print("[dim]Press Enter to use this name, or type a different one (alphanumeric without '-')[/dim]")
        agent_name = _prompt_with_default("Agent name", suggested_name)

        if not agent_name:
            agent_name = suggested_name

        _print_success(f"Using agent name: [cyan]{agent_name}[/cyan]")
        return agent_name

    def prompt_execution_role(self) -> Optional[str]:
        """Prompt for execution role. Returns role name/ARN or None for auto-creation."""
        if self.non_interactive:
            _print_success("Will auto-create execution role")
            return None

        console.print("\n🔐 [cyan]Execution Role[/cyan]")
        console.print(
            "[dim]Press Enter to auto-create execution role, or provide execution role ARN/name to use existing[/dim]"
        )

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

        response = _prompt_with_default("ECR Repository URI (or press Enter to auto-create)", "")

        if response:
            _print_success(f"Using existing ECR repository: [dim]{response}[/dim]")
            return response, False
        else:
            _print_success("Will auto-create ECR repository")
            return None, True

    def prompt_s3_bucket(self) -> tuple[Optional[str], bool]:
        """Prompt for S3 bucket. Returns (bucket_uri, auto_create_flag)."""
        if self.non_interactive:
            _print_success("Will auto-create S3 bucket")
            return None, True

        console.print("\n🏗️  [cyan]S3 Bucket[/cyan]")
        console.print("[dim]Press Enter to auto-create S3 bucket, or provide S3 URI/path to use existing[/dim]")

        response = _prompt_with_default("S3 URI/path (or press Enter to auto-create)", "")

        if response:
            # Validate the bucket exists
            if self._validate_s3_bucket(response):
                _print_success(f"Using existing S3 bucket: [dim]{response}[/dim]")
                return response, False
            else:
                console.print(f"[red]Error: S3 bucket/path '{response}' does not exist or is not accessible[/red]")
                return self.prompt_s3_bucket()  # Retry
        else:
            _print_success("Will auto-create S3 bucket")
            return None, True

    def _validate_s3_bucket(self, s3_input: str) -> bool:
        """Validate that S3 bucket exists and is accessible."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            # Parse bucket name from input
            if s3_input.startswith("s3://"):
                s3_path = s3_input[5:]
            else:
                s3_path = s3_input

            bucket_name = s3_path.split("/")[0]

            # Check if bucket exists and is accessible
            s3 = boto3.client("s3")

            # Get account_id from existing config or STS
            if self.existing_config and self.existing_config.aws.account:
                account_id = self.existing_config.aws.account
            else:
                sts = boto3.client("sts")
                account_id = sts.get_caller_identity()["Account"]

            s3.head_bucket(Bucket=bucket_name, ExpectedBucketOwner=account_id)
            return True

        except ClientError:
            return False
        except Exception:
            return False

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

        # Prompt for discovery URL
        default_discovery_url = os.getenv("BEDROCK_AGENTCORE_DISCOVERY_URL", "")
        discovery_url = _prompt_with_default("Enter OAuth discovery URL", default_discovery_url)

        if not discovery_url:
            _handle_error("OAuth discovery URL is required")

        # Prompt for client IDs
        default_client_id = os.getenv("BEDROCK_AGENTCORE_CLIENT_ID", "")
        client_ids_input = _prompt_with_default("Enter allowed OAuth client IDs (comma-separated)", default_client_id)
        # Prompt for audience
        default_audience = os.getenv("BEDROCK_AGENTCORE_AUDIENCE", "")
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

    def prompt_request_header_allowlist(self) -> Optional[dict]:
        """Prompt for request header allowlist configuration. Returns allowlist config dict or None."""
        if self.non_interactive:
            _print_success("Using default request header configuration")
            return None

        console.print("\n🔒 [cyan]Request Header Allowlist[/cyan]")
        console.print("[dim]Configure which request headers are allowed to pass through to your agent.[/dim]")
        console.print("[dim]Common headers: Authorization, X-Amzn-Bedrock-AgentCore-Runtime-Custom-*[/dim]")

        # Get existing allowlist values
        existing_headers = ""
        if (
            self.existing_config
            and self.existing_config.request_header_configuration
            and "requestHeaderAllowlist" in self.existing_config.request_header_configuration
        ):
            existing_headers = ",".join(self.existing_config.request_header_configuration["requestHeaderAllowlist"])

        allowlist_default = "yes" if existing_headers else "no"
        response = _prompt_with_default("Configure request header allowlist? (yes/no)", allowlist_default)

        if response.lower() in ["yes", "y"]:
            return self._configure_request_header_allowlist()
        else:
            _print_success("Using default request header configuration")
            return None

    def _configure_request_header_allowlist(self) -> dict:
        """Configure request header allowlist and return config dict."""
        console.print("\n📋 [cyan]Request Header Allowlist Configuration[/cyan]")

        # Prompt for headers
        default_headers = "Authorization,X-Amzn-Bedrock-AgentCore-Runtime-Custom-*"
        headers_input = _prompt_with_default("Enter allowed request headers (comma-separated)", default_headers)

        if not headers_input:
            _handle_error("At least one request header must be specified for allowlist configuration")

        # Parse and validate headers
        headers = [header.strip() for header in headers_input.split(",") if header.strip()]

        if not headers:
            _handle_error("Empty request header allowlist provided")

        _print_success(f"Request header allowlist configured with {len(headers)} headers")

        return {"requestHeaderAllowlist": headers}

    def prompt_memory_type(self) -> tuple[bool, bool]:
        """Prompt user for memory configuration preference.

        Returns:
            Tuple of (enable_memory, enable_ltm)
        """
        console.print("\n[cyan]Memory Configuration[/cyan]")
        console.print("Short-term memory stores conversation within sessions.")
        console.print("Long-term memory extracts preferences and facts across sessions.")
        console.print()

        # First ask if they want memory at all
        enable_memory_response = _prompt_with_default("Enable memory for your agent? (yes/no)", "yes").strip().lower()

        enable_memory = enable_memory_response in ["yes", "y"]

        if not enable_memory:
            _print_success("Memory disabled")
            return False, False

        # If memory is enabled, ask about long-term memory
        console.print("\n[dim]Long-term memory extracts:[/dim]")
        console.print("  • User preferences (e.g., 'I prefer Python')")
        console.print("  • Semantic facts (e.g., 'My birthday is in January')")
        console.print("  • Session summaries")
        console.print()

        enable_ltm_response = _prompt_with_default("Enable long-term memory extraction? (yes/no)", "no").strip().lower()

        enable_ltm = enable_ltm_response in ["yes", "y"]

        if enable_ltm:
            _print_success("Long-term memory will be configured")
        else:
            _print_success("Using short-term memory only")

        return enable_memory, enable_ltm

    def prompt_memory_selection(self) -> Tuple[str, str]:
        """Prompt user to select existing memory or create new (no skip option).

        Returns:
            Tuple of (action, value) where:
            - action is "USE_EXISTING", "CREATE_NEW", "SKIP"
            - value is memory_id for USE_EXISTING, mode for CREATE_NEW, None for SKIP
        """
        if self.non_interactive:
            # In non-interactive mode, default to creating new STM
            return ("CREATE_NEW", "STM_ONLY")

        console.print("\n[cyan]Memory Configuration[/cyan]")
        console.print("[dim]Tip: Use --disable-memory flag to skip memory entirely[/dim]\n")

        # Try to list existing memories
        try:
            from ...operations.memory.manager import MemoryManager

            # Get region from passed parameter OR existing config
            region = self.region or (self.existing_config.aws.region if self.existing_config else None)

            if not region:
                # No region available - offer skip option
                console.print("[dim]No region configured yet[/dim]")
                console.print("\n[dim]Options:[/dim]")
                console.print("[dim]  • Press Enter to create new memory[/dim]")
                console.print("[dim]  • Type 's' to skip memory setup[/dim]")  # <-- ADD
                console.print()

                response = _prompt_with_default("Your choice", "").strip().lower()

                if response == "s" or response == "skip":  # <-- ADD
                    _print_success("Skipping memory configuration")
                    return ("SKIP", None)

                return self._prompt_new_memory_config()

            memory_manager = MemoryManager(region_name=region)
            existing_memories = memory_manager.list_memories(max_results=10)

            if existing_memories:
                console.print("[cyan]Existing memory resources found:[/cyan]")
                for i, mem in enumerate(existing_memories, 1):
                    # Display memory summary
                    mem_id = mem.get("id", "unknown")
                    mem_name = mem.get("name", "")
                    if "memory-" in mem_id:
                        display_name = mem_id.split("memory-")[0] + "memory"
                    else:
                        display_name = mem_name or mem_id[:40]

                    console.print(f"  {i}. [bold]{display_name}[/bold]")
                    if mem.get("description"):
                        console.print(f"     [dim]{mem.get('description')}[/dim]")
                    console.print(f"     [dim]ID: {mem_id}[/dim]")

                console.print("\n[dim]Options:[/dim]")
                console.print("[dim]  • Enter a number to use existing memory[/dim]")
                console.print("[dim]  • Press Enter to create new memory[/dim]")
                console.print("[dim]  • Type 's' to skip memory setup[/dim]")

                response = _prompt_with_default("Your choice", "").strip().lower()

                if response == "s" or response == "skip":
                    _print_success("Skipping memory configuration")
                    return ("SKIP", None)
                elif response.isdigit():
                    idx = int(response) - 1
                    if 0 <= idx < len(existing_memories):
                        selected = existing_memories[idx]
                        _print_success(f"Using existing memory: {selected.get('name', selected.get('id'))}")
                        return ("USE_EXISTING", selected.get("id"))
            else:
                # No existing memories found
                console.print("[yellow]No existing memory resources found in your account[/yellow]")
                console.print("\n[dim]Options:[/dim]")
                console.print("[dim]  • Press Enter to create new memory[/dim]")
                console.print("[dim]  • Type 's' to skip memory setup[/dim]")
                console.print()

                response = _prompt_with_default("Your choice", "").strip().lower()

                if response == "s" or response == "skip":
                    _print_success("Skipping memory configuration")
                    return ("SKIP", None)

        except Exception as e:
            console.print(f"[dim]Could not list existing memories: {e}[/dim]")

        # Fall back to creating new memory
        return self._prompt_new_memory_config()

    def _prompt_new_memory_config(self) -> Tuple[str, str]:
        """Prompt for new memory configuration - LTM yes/no only."""
        console.print("[green]✓ Short-term memory will be enabled (default)[/green]")
        console.print("  • Stores conversations within sessions")
        console.print("  • Provides immediate context recall")
        console.print()
        console.print("[cyan]Optional: Long-term memory[/cyan]")
        console.print("  • Extracts user preferences across sessions")
        console.print("  • Remembers facts and patterns")
        console.print("  • Creates session summaries")
        console.print("  • [dim]Note: Takes 120-180 seconds to process[/dim]")
        console.print()

        response = _prompt_with_default("Enable long-term memory? (yes/no)", "no").strip().lower()

        if response in ["yes", "y"]:
            _print_success("Configuring short-term + long-term memory")
            return ("CREATE_NEW", "STM_AND_LTM")
        else:
            _print_success("Using short-term memory only")
            return ("CREATE_NEW", "STM_ONLY")
