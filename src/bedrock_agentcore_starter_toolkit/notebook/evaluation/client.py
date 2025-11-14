"""User-friendly Evaluation client for Python scripts and notebooks."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from ...operations.evaluation.client import EvaluationClient
from ...operations.evaluation.cp_client import EvaluationControlPlaneClient
from ...operations.evaluation.models.evaluation import EvaluationResults


class Evaluation:
    """Notebook interface for agent evaluation - mirrors CLI commands.

    This interface provides Python API equivalents to CLI evaluation commands,
    reusing the same underlying operations for consistency.

    Example:
        >>> from bedrock_agentcore_starter_toolkit import Evaluation
        >>>
        >>> # Initialize (similar to CLI --agent-id --region flags)
        >>> eval_client = Evaluation(agent_id="my-agent", region="us-east-1")
        >>>
        >>> # Run evaluation (mirrors: agentcore eval run)
        >>> results = eval_client.run(session_id="session-123")
        >>>
        >>> # List evaluators (mirrors: agentcore eval evaluator list)
        >>> evaluators = eval_client.list_evaluators()
        >>>
        >>> # Get evaluator details (mirrors: agentcore eval evaluator get)
        >>> details = eval_client.get_evaluator("Builtin.Helpfulness")
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        region: Optional[str] = None,
        session_id: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """Initialize Evaluation client.

        Args:
            agent_id: Agent ID to evaluate
            region: AWS region
            session_id: Optional default session ID for convenience
            endpoint_url: Optional custom evaluation API endpoint
        """
        self.agent_id = agent_id
        self.region = region
        self.session_id = session_id
        self.console = Console()

        # Initialize clients (reuse operations layer)
        self._eval_client = EvaluationClient(region=region, endpoint_url=endpoint_url)
        self._cp_client = EvaluationControlPlaneClient(region=region)

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None, agent_name: Optional[str] = None) -> "Evaluation":
        """Create Evaluation client from config file.

        Args:
            config_path: Path to config file (default: .bedrock_agentcore.yaml in cwd)
            agent_name: Agent name from config (uses first agent if not specified)

        Returns:
            Configured Evaluation instance

        Example:
            eval_client = Evaluation.from_config()
            results = eval_client.evaluate()
        """
        # Import here to avoid circular dependency
        from ...utils.runtime.config import load_config_if_exists

        if config_path is None:
            config_path = Path.cwd() / ".bedrock_agentcore.yaml"

        config = load_config_if_exists(config_path)
        if not config:
            raise ValueError(f"No config file found at {config_path}")

        agent_config = config.get_agent_config(agent_name)

        return cls(
            agent_id=agent_config.bedrock_agentcore.agent_id,
            region=agent_config.aws.region,
            session_id=agent_config.bedrock_agentcore.agent_session_id,
        )

    def run(
        self,
        session_id: Optional[str] = None,
        evaluators: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
        output: Optional[str] = None,
    ) -> EvaluationResults:
        """Run evaluation on a session (mirrors: agentcore eval run).

        Default: Evaluates all traces (most recent 1000 spans).
        With trace_id: Evaluates only that trace (includes spans from all previous traces for context).

        Args:
            session_id: Session ID to evaluate (uses default if not provided)
            evaluators: List of evaluators to use (default: ["Builtin.GoalSuccessRate"])
            trace_id: Optional trace ID - evaluates only this trace, with previous traces for context
            output: Optional path to save results to JSON file

        Returns:
            EvaluationResults with scores and explanations

        Example:
            # Evaluate all traces with default evaluator
            results = eval_client.run("session-123")

            # Evaluate with multiple evaluators
            results = eval_client.run(
                "session-123",
                evaluators=["Builtin.Helpfulness", "Builtin.Accuracy"]
            )

            # Evaluate specific trace only (with previous traces for context)
            results = eval_client.run("session-123", trace_id="trace-456")

            # Save results to file
            results = eval_client.run("session-123", output="results.json")
        """
        session_id = session_id or self.session_id
        if not session_id:
            raise ValueError("No session_id provided")

        if not self.agent_id or not self.region:
            raise ValueError("Agent ID and region required. Provide them in __init__ or use from_config()")

        evaluators = evaluators or ["Builtin.GoalSuccessRate"]

        # Display what we're doing (similar to CLI)
        self.console.print(f"\n[cyan]Evaluating session:[/cyan] {session_id}")
        if trace_id:
            self.console.print(f"[cyan]Trace:[/cyan] {trace_id} (with previous traces for context)")
        else:
            self.console.print("[cyan]Mode:[/cyan] All traces (most recent 1000 spans)")
        self.console.print(f"[cyan]Evaluators:[/cyan] {', '.join(evaluators)}\n")

        # Run evaluation using operations client
        with self.console.status("[cyan]Running evaluation...[/cyan]"):
            results = self._eval_client.evaluate_session(
                session_id=session_id,
                evaluators=evaluators,
                agent_id=self.agent_id,
                region=self.region,
                trace_id=trace_id,
            )

        # Save to file if requested
        if output:
            self._save_results(results, output)

        return results

    def _save_results(self, results: EvaluationResults, output_file: str) -> None:
        """Save evaluation results to a JSON file (internal helper)."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save results
        results_dict = results.to_dict()
        input_data = results_dict.pop("input_data", None)

        with open(output_path, "w") as f:
            json.dump(results_dict, f, indent=2, default=str)

        self.console.print(f"\n[green]✓[/green] Results saved to: {output_path}")

        # Save input data to separate file if present
        if input_data is not None:
            stem = output_path.stem
            suffix = output_path.suffix
            input_path = output_path.parent / f"{stem}_input{suffix}"

            with open(input_path, "w") as f:
                json.dump(input_data, f, indent=2, default=str)

            self.console.print(f"[green]✓[/green] Input data saved to: {input_path}")

    # ===========================
    # Evaluator Management Methods
    # ===========================

    def list_evaluators(self, max_results: int = 50) -> Dict:
        """List all evaluators (mirrors: agentcore eval evaluator list).

        Args:
            max_results: Maximum number of evaluators to return

        Returns:
            Dict with 'evaluators' key containing list of evaluator dicts

        Example:
            evaluators = eval_client.list_evaluators()
            for ev in evaluators['evaluators']:
                print(ev['evaluatorId'], ev['evaluatorName'])
        """
        with self.console.status("[cyan]Fetching evaluators...[/cyan]"):
            response = self._cp_client.list_evaluators(max_results=max_results)

        evaluators = response.get("evaluators", [])

        if not evaluators:
            self.console.print("[yellow]No evaluators found[/yellow]")
            return response

        # Separate builtin and custom
        builtin = [e for e in evaluators if e.get("evaluatorId", "").startswith("Builtin.")]
        custom = [e for e in evaluators if not e.get("evaluatorId", "").startswith("Builtin.")]

        # Display builtin evaluators
        if builtin:
            self.console.print(f"\n[bold cyan]Built-in Evaluators ({len(builtin)})[/bold cyan]\n")

            builtin_table = Table(show_header=True)
            builtin_table.add_column("ID", style="cyan", no_wrap=True, width=30)
            builtin_table.add_column("Name", style="white", width=30)
            builtin_table.add_column("Description", style="dim")

            for ev in sorted(builtin, key=lambda x: x.get("evaluatorId", "")):
                builtin_table.add_row(ev.get("evaluatorId", ""), ev.get("evaluatorName", ""), ev.get("description", ""))

            self.console.print(builtin_table)

        # Display custom evaluators
        if custom:
            self.console.print(f"\n[bold green]Custom Evaluators ({len(custom)})[/bold green]\n")

            custom_table = Table(show_header=True)
            custom_table.add_column("ID", style="green", no_wrap=True)
            custom_table.add_column("Name", style="white")
            custom_table.add_column("Created", style="dim")

            for ev in sorted(custom, key=lambda x: x.get("createdAt", ""), reverse=True):
                created = ev.get("createdAt", "")
                if created:
                    created = str(created).split("T")[0]  # Just the date

                custom_table.add_row(ev.get("evaluatorId", ""), ev.get("evaluatorName", ""), created)

            self.console.print(custom_table)

        self.console.print(f"\n[dim]Total: {len(evaluators)} ({len(builtin)} builtin, {len(custom)} custom)[/dim]")

        return response

    def get_evaluator(self, evaluator_id: str, output: Optional[str] = None) -> Dict:
        """Get detailed information about an evaluator (mirrors: agentcore eval evaluator get).

        Args:
            evaluator_id: Evaluator ID (e.g., Builtin.Helpfulness or custom-id)
            output: Optional path to save details to JSON file

        Returns:
            Dict with evaluator details

        Example:
            details = eval_client.get_evaluator("Builtin.Helpfulness")
            print(details['instructions'])
        """
        with self.console.status(f"[cyan]Fetching evaluator {evaluator_id}...[/cyan]"):
            response = self._cp_client.get_evaluator(evaluator_id=evaluator_id)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(response, f, indent=2, default=str)
            self.console.print(f"\n[green]✓[/green] Saved to: {output_path}")
            return response

        # Display summary
        self.console.print("\n[bold cyan]Evaluator Details[/bold cyan]\n")
        self.console.print(f"[bold]ID:[/bold] {response.get('evaluatorId', '')}")
        self.console.print(f"[bold]Name:[/bold] {response.get('evaluatorName', '')}")
        self.console.print(f"[bold]Level:[/bold] {response.get('level', '')}")

        if "description" in response:
            self.console.print(f"[bold]Description:[/bold] {response['description']}")

        # Show instructions preview
        if "evaluatorConfig" in response:
            config = response["evaluatorConfig"]
            if "llmAsAJudge" in config and "instructions" in config["llmAsAJudge"]:
                instructions = config["llmAsAJudge"]["instructions"]
                preview = instructions[:200] + "..." if len(instructions) > 200 else instructions
                self.console.print(f"\n[bold]Instructions:[/bold] {preview}")

        return response

    def create_evaluator(
        self,
        name: str,
        config: Dict,
        level: str = "TRACE",
        description: Optional[str] = None,
    ) -> Dict:
        """Create a custom evaluator (mirrors: agentcore eval evaluator create).

        Args:
            name: Evaluator name
            config: Evaluator configuration dict (must contain 'llmAsAJudge' key)
            level: Evaluation level (TRACE, SPAN, SESSION)
            description: Optional evaluator description

        Returns:
            Dict with evaluator creation response

        Example:
            config = {
                "llmAsAJudge": {
                    "modelConfig": {
                        "bedrockEvaluatorModelConfig": {
                            "modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0"
                        }
                    },
                    "instructions": "Evaluate the quality...",
                    "ratingScale": {
                        "numerical": [
                            {"value": 0, "label": "Poor", "definition": "..."},
                            {"value": 1, "label": "Good", "definition": "..."}
                        ]
                    }
                }
            }
            response = eval_client.create_evaluator("my-evaluator", config)
        """
        # Validate required structure
        if "llmAsAJudge" not in config:
            raise ValueError("Config must contain 'llmAsAJudge' key")

        with self.console.status(f"[cyan]Creating evaluator '{name}'...[/cyan]"):
            response = self._cp_client.create_evaluator(name=name, config=config, level=level, description=description)

        evaluator_id = response.get("evaluatorId", "")
        evaluator_arn = response.get("evaluatorArn", "")

        self.console.print("\n[green]✓[/green] Evaluator created successfully!")
        self.console.print(f"\n[bold]ID:[/bold] {evaluator_id}")
        self.console.print(f"[bold]ARN:[/bold] {evaluator_arn}")
        self.console.print(f"\n[dim]Use: eval_client.run(evaluators=['{evaluator_id}'])[/dim]")

        return response

    def update_evaluator(
        self,
        evaluator_id: str,
        description: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> Dict:
        """Update a custom evaluator (mirrors: agentcore eval evaluator update).

        Args:
            evaluator_id: Evaluator ID to update
            description: New description
            config: New configuration dict

        Returns:
            Dict with update response

        Example:
            response = eval_client.update_evaluator(
                "my-evaluator-abc123",
                description="Updated description"
            )
        """
        if not description and not config:
            self.console.print("[yellow]No updates specified[/yellow]")
            return {}

        with self.console.status(f"[cyan]Updating evaluator {evaluator_id}...[/cyan]"):
            response = self._cp_client.update_evaluator(
                evaluator_id=evaluator_id, description=description, config=config
            )

        self.console.print("\n[green]✓[/green] Evaluator updated successfully!")
        if "updatedAt" in response:
            self.console.print(f"[dim]Updated at: {response['updatedAt']}[/dim]")

        return response

    def delete_evaluator(self, evaluator_id: str) -> None:
        """Delete a custom evaluator (mirrors: agentcore eval evaluator delete).

        Args:
            evaluator_id: Evaluator ID to delete

        Example:
            eval_client.delete_evaluator("my-evaluator-abc123")
        """
        with self.console.status(f"[cyan]Deleting evaluator {evaluator_id}...[/cyan]"):
            self._cp_client.delete_evaluator(evaluator_id=evaluator_id)

        self.console.print("\n[green]✓[/green] Evaluator deleted successfully")
