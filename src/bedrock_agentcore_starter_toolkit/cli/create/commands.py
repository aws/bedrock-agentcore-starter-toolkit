#!/usr/bin/env python3
import json
import os
import uuid

import boto3
import questionary
import typer
import yaml
from dotenv import load_dotenv
from rich.panel import Panel
from rich.text import Text

from ...services.create.strands_create import StrandsCreate
from ...services.create.utils import get_clients
from ..common import console

load_dotenv()

create_app = typer.Typer(help="Create Agent")


class AgentConfigureWorkflow:
    def __init__(self, console, app, output_dir, agent_name=None, region=None):
        self.agent_name = agent_name or f"agent-{uuid.uuid4().hex.lower()}"
        self.region = region or "us-west-2"  # Default region
        self.agent_config = {
            "agent": {
                "agentName": self.agent_name,
                "instruction": "",
                "foundationModel": "",
                "providerName": "",
                "memoryConfiguration": {},
                "guardrailConfiguration": {},
                "promptOverrideConfiguration": {"promptConfigurations": []},
            },
            "knowledge_bases": [],
        }
        self.target_platform = "strands"
        self.credentials = boto3.Session().get_credentials()
        self.bedrock_client, self.bedrock_agent_client = get_clients(self.credentials)
        self.debug_enabled = False
        self.tools_config = {
            "code_interpreter": False,
            "browser": False,
            "human_input": False,
        }
        self.observability_enabled = True
        self.tool_classes = []
        self.memory_config = {"enabled": False, "strategies": [], "max_days": 30}

        self.console = console
        self.app = app
        self.output_dir = output_dir

    def _create_env_file(self, api_key):
        """Create a .env file with the MODEL_API_KEY."""
        try:
            env_file_path = os.path.join(self.output_dir, ".env")
            os.makedirs(self.output_dir, exist_ok=True)

            with open(env_file_path, "w", encoding="utf-8") as f:
                f.write(f"MODEL_API_KEY={api_key}\n")

            self.console.print(f"[bold green]✓[/bold green] API key saved to .env file: {env_file_path}")
        except Exception as e:
            self.console.print(f"[bold red]Error creating .env file: {str(e)}[/bold red]")

    def verify_aws_credentials(self) -> bool:
        """Verify that AWS credentials are present and valid."""
        try:
            # Try to get the caller identity to verify credentials
            boto3.client("sts").get_caller_identity()
            return True
        except Exception as e:
            self.console.print(
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

    def collect_model_info(self):
        """Collect information about the model provider and model ID."""
        # Load supported models from JSON file
        try:
            models_file_path = os.path.join(os.path.dirname(__file__), "supported_models.json")
            with open(models_file_path, "r", encoding="utf-8") as f:
                supported_models = json.load(f)
        except Exception as e:
            self.console.print(f"[bold red]Error loading supported models: {str(e)}[/bold red]")
            return False

        # Create provider choices from the JSON file
        provider_choices = [provider_info["name"] for provider_info in supported_models["providers"].values()]

        selected_provider_display = questionary.select(
            "Select a model provider:",
            choices=provider_choices,
        ).ask()

        if selected_provider_display is None:
            self.console.print("\n[yellow]Model provider selection cancelled by user.[/yellow]")
            return False

        # Find the provider key from the display name
        selected_provider_key = None
        for key, info in supported_models["providers"].items():
            if info["name"] == selected_provider_display:
                selected_provider_key = key
                break

        if not selected_provider_key:
            self.console.print("[bold red]Invalid provider selection![/bold red]")
            return False

        provider_info = supported_models["providers"][selected_provider_key]

        # Handle different provider types
        if selected_provider_key == "bedrock":
            # For Bedrock, use empty models list (user will fill in later)
            if not provider_info["models"]:
                self.console.print(
                    "[bold yellow]No Bedrock models configured. Please add models to supported_models.json[/bold yellow]"
                )
                return False

            model_id = questionary.select(
                "Select a Bedrock model:",
                choices=provider_info["models"],
            ).ask()

            if model_id is None:
                self.console.print("\n[yellow]Model selection cancelled by user.[/yellow]")
                return False

            self.agent_config["agent"]["foundationModel"] = model_id
            self.agent_config["agent"]["providerName"] = selected_provider_key

        elif selected_provider_key == "litellm":
            # For LiteLLM, ask for API key and custom model ID
            api_key = questionary.password(f"Enter your {selected_provider_display} API key:").ask()
            if api_key is None:
                self.console.print("\n[yellow]API key input cancelled by user.[/yellow]")
                return False

            model_id = questionary.text("Enter the model ID string for LiteLLM:").ask()
            if model_id is None:
                self.console.print("\n[yellow]Model ID input cancelled by user.[/yellow]")
                return False

            self.agent_config["agent"]["foundationModel"] = model_id
            self.agent_config["agent"]["providerName"] = selected_provider_key

            # Create .env file with API key
            self._create_env_file(api_key)

        else:
            # For OpenAI and Anthropic, ask for API key first
            api_key = questionary.password(f"Enter your {selected_provider_display} API key:").ask()
            if api_key is None:
                self.console.print("\n[yellow]API key input cancelled by user.[/yellow]")
                return False

            # Then select model from predefined models
            if not provider_info["models"]:
                self.console.print(f"[bold red]No models configured for {selected_provider_display}![/bold red]")
                return False

            model_id = questionary.select(
                f"Select a model for {selected_provider_display}:",
                choices=provider_info["models"],
            ).ask()

            if model_id is None:
                self.console.print("\n[yellow]Model ID input cancelled by user.[/yellow]")
                return False

            self.agent_config["agent"]["foundationModel"] = model_id
            self.agent_config["agent"]["providerName"] = selected_provider_key

            # Create .env file with API key
            self._create_env_file(api_key)

        self.console.print(
            f"[bold green]✓[/bold green] Model selected: {self.agent_config['agent']['foundationModel']} ({selected_provider_key})"
        )
        return True

    def collect_agent_instructions(self):
        """Collect agent instructions and goals."""
        instructions = questionary.text(
            "Enter the agent instructions and goals (press Enter to open a multi-line editor):", multiline=True
        ).ask()

        if instructions is None:
            self.console.print("\n[yellow]Agent instructions input cancelled by user.[/yellow]")
            return False

        self.agent_config["agent"]["instruction"] = instructions

        self.console.print("[bold green]✓[/bold green] Agent instructions collected")
        return True

    def collect_knowledge_bases(self):
        """Collect knowledge bases for the agent."""
        try_kb = questionary.confirm("Do you want to add Knowledge Bases to your agent?", default=False).ask()

        if try_kb is None:
            self.console.print("\n[yellow]Knowledge Base selection cancelled by user.[/yellow]")
            return True  # This is optional, so return True

        if not try_kb:
            self.console.print("[yellow]Skipping Knowledge Bases.[/yellow]")
            return True

        try:
            # Get knowledge bases from the user's AWS account
            response = self.bedrock_agent_client.list_knowledge_bases()

            kb_choices = []
            kb_info = {}

            if not response.get("knowledgeBaseSummaries"):
                self.console.print(
                    "[bold yellow]No Knowledge Bases found in your account. Skipping this step.[/bold yellow]"
                )
                return True

            for kb in response.get("knowledgeBaseSummaries", []):
                kb = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb.get("knowledgeBaseId"))[
                    "knowledgeBase"
                ]
                kb_id = kb.get("knowledgeBaseId")
                kb_name = kb.get("name")
                kb_description = kb.get("description") or "No description"
                display_name = f"{kb_name} ({kb_id})"

                kb_choices.append(display_name)
                kb_info[display_name] = {
                    "id": kb_id,
                    "name": kb_name,
                    "description": kb_description,
                    "knowledgeBaseArn": kb.get("knowledgeBaseArn", ""),
                }

            selected_kbs = questionary.checkbox(
                "Select Knowledge Bases to add to your agent:", choices=kb_choices
            ).ask()

            if selected_kbs is None:
                self.console.print("\n[yellow]Knowledge Base selection cancelled by user.[/yellow]")
                return False

            for selected in selected_kbs:
                self.agent_config["knowledge_bases"].append(
                    {
                        "knowledgeBaseId": kb_info[selected]["id"],
                        "knowledgeBaseArn": kb_info[selected]["knowledgeBaseArn"],
                        "name": kb_info[selected]["name"],
                        "description": kb_info[selected]["description"],
                    }
                )

            self.console.print(f"[bold green]✓[/bold green] Selected {len(selected_kbs)} Knowledge Bases")

        except Exception as e:
            self.console.print(f"[bold red]Error fetching Knowledge Bases: {str(e)}[/bold red]")
            self.console.print("[yellow]Continuing without Knowledge Bases.[/yellow]")

        return True

    def collect_guardrails(self):
        """Collect guardrails for the agent (if using Bedrock)."""
        if self.agent_config["agent"]["providerName"].lower() != "bedrock":
            self.console.print(
                "[yellow]Guardrails are only available for Amazon Bedrock models. Skipping this step.[/yellow]"
            )
            return True

        try_guardrails = questionary.confirm("Do you want to add Guardrails to your agent?", default=False).ask()

        if try_guardrails is None:
            self.console.print("\n[yellow]Guardrail selection cancelled by user.[/yellow]")
            return True  # This is optional, so return True

        if not try_guardrails:
            self.console.print("[yellow]Skipping Guardrails.[/yellow]")
            return True

        try:
            # Get guardrails from the user's AWS account
            response = self.bedrock_client.list_guardrails()

            guardrail_choices = []
            guardrail_info = {}

            if not response.get("guardrails"):
                self.console.print(
                    "[bold yellow]No Guardrails found in your account. Skipping this step.[/bold yellow]"
                )
                return True

            for guardrail in response.get("guardrails", []):
                guardrail_id = guardrail.get("id")
                guardrail_name = guardrail.get("name")
                guardrail_version = guardrail.get("version")
                display_name = f"{guardrail_name} v{guardrail_version} ({guardrail_id})"

                guardrail_choices.append(display_name)
                guardrail_info[display_name] = {"id": guardrail_id, "version": guardrail_version}

            selected_guardrail = questionary.select(
                "Select a Guardrail for your agent:", choices=guardrail_choices
            ).ask()

            if selected_guardrail is None:
                self.console.print("\n[yellow]Guardrail selection cancelled by user.[/yellow]")
                return True  # Still optional, so return True

            self.agent_config["agent"]["guardrailConfiguration"] = {
                "guardrailId": guardrail_info[selected_guardrail]["id"],
                "version": guardrail_info[selected_guardrail]["version"],
            }

            self.console.print(f"[bold green]✓[/bold green] Selected Guardrail: {selected_guardrail}")

        except Exception as e:
            self.console.print(f"[bold red]Error fetching Guardrails: {str(e)}[/bold red]")
            self.console.print("[yellow]Continuing without Guardrails.[/yellow]")

        return True

    def collect_memory_config(self):
        """Collect memory configuration."""
        memory_enabled = questionary.confirm(
            "Do you want to enable Long Term Memory for your agent?", default=False
        ).ask()

        if memory_enabled is None:
            self.console.print("\n[yellow]Memory configuration cancelled by user.[/yellow]")
            return False

        if not memory_enabled:
            self.console.print("[yellow]Skipping Memory Configuration.[/yellow]")
            self.memory_config = {"enabled": False, "strategies": [], "max_days": 30}
            return True

        # Select memory strategies (multiple selection)
        memory_strategies = questionary.checkbox(
            "Select memory strategies:",
            choices=["semantic", "summarization", "user_preferences"],
        ).ask()

        if memory_strategies is None:
            self.console.print("\n[yellow]Memory strategy selection cancelled by user.[/yellow]")
            return False

        if not memory_strategies:
            self.console.print("\n[yellow]At least one memory strategy must be selected.[/yellow]")
            return False

        # Store memory configuration
        self.memory_config = {"enabled": True, "strategies": memory_strategies, "max_days": 30}

        self.console.print(
            f"[bold green]✓[/bold green] Memory configuration set with strategies: {', '.join(memory_strategies)}"
        )
        return True

    def collect_tools_config(self):
        """Collect configuration for built-in tools."""
        # Code Interpreter
        code_enabled = questionary.confirm("Do you want to enable the Code Interpreter tool?", default=False).ask()

        if code_enabled is None:
            self.console.print("\n[yellow]Code Interpreter configuration cancelled by user.[/yellow]")
            return False

        self.tools_config["code_interpreter"] = code_enabled

        # Browser Tool
        browser_enabled = questionary.confirm("Do you want to enable the Browser tool?", default=False).ask()

        if browser_enabled is None:
            self.console.print("\n[yellow]Browser tool configuration cancelled by user.[/yellow]")
            return False

        self.tools_config["browser"] = browser_enabled

        # Human Input Tool
        human_input = questionary.confirm("Do you want to enable the Human Input tool?", default=True).ask()

        if human_input is None:
            self.console.print("\n[yellow]Human Input tool configuration cancelled by user.[/yellow]")
            return False

        self.tools_config["human_input"] = human_input

        return True

    def collect_observability_config(self):
        """Collect observability configuration."""
        observability = questionary.confirm("Do you want to enable Observability/Tracing?", default=False).ask()

        if observability is None:
            self.console.print("\n[yellow]Observability configuration cancelled by user.[/yellow]")
            return False

        self.observability_enabled = observability

        if observability:
            self.console.print("[bold green]✓[/bold green] Observability enabled")
        else:
            self.console.print("[yellow]Observability disabled[/yellow]")

        return True

    def select_target_platform(self):
        """Select the target platform for code generation."""
        platform = questionary.select(
            "Select your target platform:",
            choices=["langchain", "strands"],
        ).ask()

        if platform is None:
            self.console.print("\n[yellow]Platform selection cancelled by user.[/yellow]")
            return False

        self.target_platform = platform
        self.console.print(f"[bold green]✓[/bold green] Target platform: {platform}")
        return True

    def collect_tool_classes(self):
        """Collect tool classes for the agent."""
        self.console.print("Connect your agent to AgentCore Gateway, custom MCP servers, and more.")

        defining_tools = True

        while defining_tools:
            # Display current tool classes if any exist
            # if self.tool_classes:
            #     self.console.print("\n[bold]Current Tool Classes:[/bold]")
            #     for idx, tool_class in enumerate(self.tool_classes, 1):
            #         table = Table(title=f"Tool Class {idx}")
            #         table.add_column("Property", style="cyan")
            #         table.add_column("Value", style="green")

            #         table.add_row("Type", tool_class["type"])

            #         if tool_class["type"] == "existing_gateway":
            #             table.add_row("Gateway ID", tool_class.get("gateway_id", "N/A"))
            #             table.add_row("Gateway Name", tool_class.get("gateway_name", "N/A"))
            #         elif tool_class["type"] == "new_gateway":
            #             targets_str = "\n".join(
            #                 [f"- {target['target_type']}" for target in tool_class.get("targets", [])]
            #             )
            #             table.add_row("Targets", targets_str if targets_str else "None")
            #         elif tool_class["type"] == "custom_mcp":
            #             table.add_row("MCP Server URL", tool_class.get("mcp_server_url", "N/A"))

            #         self.console.print(table)

            # Ask user to select tool class type
            tool_choice = questionary.select(
                "Select tool class type:",
                choices=[
                    "Select existing gateway",
                    "Define new gateway",
                    "Custom MCP server",
                    "Exit tool class definition",
                ],
            ).ask()

            if tool_choice is None:
                self.console.print("\n[yellow]Tool class selection cancelled by user.[/yellow]")
                return False

            if tool_choice == "Exit tool class definition":
                defining_tools = False
                break

            elif tool_choice == "Select existing gateway":
                if not self._handle_existing_gateway():
                    return False

            elif tool_choice == "Define new gateway":
                if not self._handle_new_gateway():
                    return False

            elif tool_choice == "Custom MCP server":
                if not self._handle_custom_mcp():
                    return False

        if self.tool_classes:
            self.console.print(f"[bold green]✓[/bold green] Defined {len(self.tool_classes)} tool classes")
        else:
            self.console.print("[yellow]No tool classes defined.[/yellow]")

        return True

    def _handle_existing_gateway(self):
        """Handle selection of existing gateway."""
        try:
            # Create bedrock-agentcore-control client
            agentcore_client = boto3.client("bedrock-agentcore-control")

            # List gateways
            response = agentcore_client.list_gateways(maxResults=50)

            if not response.get("items"):
                self.console.print("[bold yellow]No existing gateways found in your account.[/bold yellow]")
                return True

            # Create choices from gateways
            gateway_choices = []
            gateway_info = {}

            for gateway in response.get("items", []):
                gateway_id = gateway.get("gatewayId")
                gateway_name = gateway.get("name", "Unnamed Gateway")
                status = gateway.get("status", "Unknown")
                display_name = f"{gateway_name} ({gateway_id}) - {status}"

                gateway_choices.append(display_name)
                gateway_info[display_name] = {"gateway_id": gateway_id, "gateway_name": gateway_name, "status": status}

            # Let user select gateway
            selected_gateway = questionary.select("Select an existing gateway:", choices=gateway_choices).ask()

            if selected_gateway is None:
                self.console.print("\n[yellow]Gateway selection cancelled by user.[/yellow]")
                return False

            # Add to tool classes
            tool_class = {
                "type": "existing_gateway",
                "gateway_id": gateway_info[selected_gateway]["gateway_id"],
                "gateway_name": gateway_info[selected_gateway]["gateway_name"],
                "status": gateway_info[selected_gateway]["status"],
            }

            self.tool_classes.append(tool_class)
            self.console.print(
                f"[bold green]✓[/bold green] Added existing gateway: {gateway_info[selected_gateway]['gateway_name']}"
            )

        except Exception as e:
            self.console.print(f"[bold red]Error listing gateways: {str(e)}[/bold red]")
            self.console.print("[yellow]Continuing without adding gateway.[/yellow]")

        return True

    def _handle_new_gateway(self):
        """Handle creation of new gateway with targets."""
        tool_class = {"type": "new_gateway", "targets": []}

        defining_targets = True

        while defining_targets:
            # Display current targets if any exist
            # if tool_class["targets"]:
            #     self.console.print("\n[bold]Current Targets:[/bold]")
            #     for idx, target in enumerate(tool_class["targets"], 1):
            #         target_table = Table(title=f"Target {idx}: {target['target_type']}")
            #         target_table.add_column("Property", style="cyan")
            #         target_table.add_column("Value", style="green")

            #         target_table.add_row("Type", target["target_type"])

            #         if target["target_type"] == "lambda":
            #             target_table.add_row("Lambda ARN", target.get("lambda_arn", "N/A"))
            #             target_table.add_row("Tool Schema", "JSON provided" if target.get("tool_schema") else "N/A")
            #         elif target["target_type"] in ["smithy", "openapi"]:
            #             target_table.add_row("Spec", "JSON provided" if target.get("spec") else "N/A")
            #             target_table.add_row("Credentials", "JSON provided" if target.get("credentials") else "N/A")

            #         self.console.print(target_table)

            # Ask if user wants to add a target
            add_target = questionary.confirm("Do you want to add a target to this gateway?", default=True).ask()

            if add_target is None or not add_target:
                defining_targets = False
                break

            # Select target type
            target_type = questionary.select("Select target type:", choices=["lambda", "smithy", "openapi"]).ask()

            if target_type is None:
                self.console.print("\n[yellow]Target type selection cancelled by user.[/yellow]")
                return False

            target = {"target_type": target_type}

            if target_type == "lambda":
                # Get Lambda ARN
                lambda_arn = questionary.text("Enter the Lambda ARN:").ask()
                if lambda_arn is None:
                    self.console.print("\n[yellow]Lambda ARN input cancelled by user.[/yellow]")
                    return False

                # Get tool schema JSON
                tool_schema = questionary.text("Enter the tool schema as a JSON string:", multiline=True).ask()
                if tool_schema is None:
                    self.console.print("\n[yellow]Tool schema input cancelled by user.[/yellow]")
                    return False

                target["lambda_arn"] = lambda_arn
                target["tool_schema"] = tool_schema

            elif target_type in ["smithy", "openapi"]:
                # Get spec JSON
                spec = questionary.text(f"Enter the {target_type} spec as a JSON string:", multiline=True).ask()
                if spec is None:
                    self.console.print(f"\n[yellow]{target_type.title()} spec input cancelled by user.[/yellow]")
                    return False

                # Get credentials JSON
                credentials = questionary.text("Enter the credentials as a JSON string:", multiline=True).ask()
                if credentials is None:
                    self.console.print("\n[yellow]Credentials input cancelled by user.[/yellow]")
                    return False

                target["spec"] = spec
                target["credentials"] = credentials

            # Add target to gateway
            tool_class["targets"].append(target)
            self.console.print(f"[bold green]✓[/bold green] Added {target_type} target")

        # Add gateway to tool classes if it has targets
        if tool_class["targets"]:
            self.tool_classes.append(tool_class)
            self.console.print(
                f"[bold green]✓[/bold green] Added new gateway with {len(tool_class['targets'])} targets"
            )
        else:
            self.console.print("[yellow]No targets added to gateway. Gateway not saved.[/yellow]")

        return True

    def _handle_custom_mcp(self):
        """Handle custom MCP server configuration."""
        # Get MCP server URL
        mcp_server_url = questionary.text("Enter the MCP server URL:").ask()
        if mcp_server_url is None:
            self.console.print("\n[yellow]MCP server URL input cancelled by user.[/yellow]")
            return False

        tool_class = {"type": "custom_mcp", "mcp_server_url": mcp_server_url}

        self.tool_classes.append(tool_class)
        self.console.print(f"[bold green]✓[/bold green] Added custom MCP server: {mcp_server_url}")

        return True

    def run_workflow(self):
        """Run the complete agent creation workflow."""
        self.console.print(
            Panel(
                Text("Agent Configure Workflow", style="bold cyan"),
                subtitle="Define your agent configuration",
                border_style="cyan",
            )
        )

        # Define the workflow steps
        steps = [
            ("Agent Instructions", self.collect_agent_instructions),
            ("Model Information", self.collect_model_info),
            ("Tool Classes", self.collect_tool_classes),
            ("Knowledge Bases", self.collect_knowledge_bases),
            ("Guardrails", self.collect_guardrails),
            ("Memory Configuration", self.collect_memory_config),
            ("1P Tools Configuration", self.collect_tools_config),
            # ("Target Platform", self.select_target_platform),
        ]

        # Run each step
        for step_name, step_func in steps:
            self.console.print(f"\n[bold]Step: {step_name}[/bold]")
            if not step_func():
                self.console.print(f"\n[yellow]Workflow cancelled by user during '{step_name}' step.[/yellow]")
                return None

        # Map region names to AWS region codes
        region_mapping = {
            "us-east-1": "US East (N. Virginia)",
            "us-west-2": "US West (Oregon)",
            "eu-central-1": "Europe (Frankfurt)",
            "ap-southeast-2": "Asia Pacific (Sydney)",
        }

        # Get region display name, default to the region code if not found
        region_display = region_mapping.get(self.region, self.region)

        # Create modelConfig based on provider
        model_config = {}
        if self.agent_config["agent"]["providerName"].lower() == "bedrock":
            if self.agent_config["agent"]["guardrailConfiguration"]:
                model_config["guardrailConfiguration"] = self.agent_config["agent"]["guardrailConfiguration"]
        elif self.agent_config["agent"]["providerName"].lower() == "litellm":
            # For LiteLLM, include the API key in modelConfig
            if "modelConfig" in self.agent_config["agent"] and "api_key" in self.agent_config["agent"]["modelConfig"]:
                model_config["api_key"] = self.agent_config["agent"]["modelConfig"]["api_key"]

        # Prepare the final configuration in the required format
        final_config = {
            "agent": {
                "name": self.agent_name,
                "instruction": self.agent_config["agent"]["instruction"],
                "foundationModel": self.agent_config["agent"]["foundationModel"],
                "providerName": self.agent_config["agent"]["providerName"],
                "modelConfig": model_config,
                "debugEnabled": self.debug_enabled,
            },
            "knowledge_bases": self.agent_config["knowledge_bases"],
            "tools_1p": {
                "code_interpreter": self.tools_config["code_interpreter"],
                "browser": self.tools_config["browser"],
                "human_input": self.tools_config["human_input"],
            },
            "tool_classes": self.tool_classes,
            "memory": self.memory_config,
            "target_platform": self.target_platform,
            "observability_enabled": self.observability_enabled,
            "region": self.region,
        }

        # Save the configuration to a file for debugging
        output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)

        config_file = os.path.join(output_dir, "agent_config.yaml")
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(final_config, f, indent=2, default_flow_style=False, sort_keys=False)

        self.console.print(f"\n[bold green]✓[/bold green] Agent configuration saved to: {config_file}")

        return final_config

    def configure(self):
        """Create a new agent or import from Bedrock Agents."""
        # Verify AWS credentials
        self.console.print("[bold]Verifying AWS credentials...[/bold]")
        if not self.verify_aws_credentials():
            return

        self.console.print("[bold green]✓[/bold green] AWS credentials verified!")

        final_config = self.run_workflow()

        if not final_config:
            self.console.print("\n[yellow]Agent creation workflow cancelled by user.[/yellow]")
            return

        self.console.print(
            Panel(
                f"[bold green]Agent configuration complete![/bold green]\n\n"
                f"Agent Name: {final_config['agent']['name']}\n"
                f"Model: {final_config['agent']['foundationModel']} ({final_config['agent']['providerName']})\n"
                f"Target Platform: {final_config['target_platform']}\n"
                f"Region: {final_config['region']}",
                title="Agent Configured",
                border_style="green",
            )
        )

        return final_config


class AgentCreationWorkflow:
    def __init__(self, console, app, config):
        self.console = console
        self.app = app
        self.config = config

    def create(self, output_dir: str):
        """Create the agent based on the selected platform."""
        platform = self.config.get("target_platform", "strands")
        os.makedirs(output_dir, exist_ok=True)

        with self.console.status("[bold green]Generating Agent...[/bold green]"):
            if platform.startswith("strands"):
                strands_creator = StrandsCreate(self.config, output_dir)
                strands_creator.create_strands(name="strands_agent.py")

        self.console.print(
            Panel(
                f"[bold green]✓[/bold green] Agent '{self.config['agent']['name']}' created successfully!\n"
                "You can now deploy your agent to AgentCore Runtime or use it locally.",
                title="Agent Created",
                border_style="green",
            )
        )


@create_app.command()
def create(
    agent_name: str = typer.Option(None, "--agent-name", "-n", help="Name of the agent"),
    region: str = typer.Option(
        "us-east-1", "--region", "-r", help="AWS region (us-east-1, us-west-2, eu-central-1, ap-southeast-2)"
    ),
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the agent configuration file (YAML format, optional) to generate the agent from an existing configuration",
    ),
    output_dir: str = typer.Option(
        "./output", "--output-dir", "-o", help="Directory to save the generated agent configuration and code"
    ),
):
    """Create a new agent configuration interactively."""
    if not config:
        agent_config = AgentConfigureWorkflow(
            console=console, app=create_app, output_dir=output_dir, agent_name=agent_name, region=region
        ).configure()
    else:
        # Load YAML configuration file
        with open(config, "r", encoding="utf-8") as f:
            agent_config = yaml.safe_load(f)

    if agent_config:
        AgentCreationWorkflow(console=console, app=create_app, config=agent_config).create(output_dir=output_dir)


# ruff: noqa
