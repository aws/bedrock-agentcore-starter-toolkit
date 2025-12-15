"""User-friendly Evaluation client for Python scripts and notebooks."""

from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from ...operations.evaluation import evaluator_processor, online_processor
from ...operations.evaluation.control_plane_client import EvaluationControlPlaneClient
from ...operations.evaluation.data_plane_client import EvaluationDataPlaneClient
from ...operations.evaluation.formatters import (
    display_evaluator_details,
    display_evaluator_list,
    save_evaluation_results,
    save_json_output,
)
from ...operations.evaluation.models import EvaluationResults
from ...operations.evaluation.on_demand_processor import EvaluationProcessor


class Evaluation:
    """Notebook interface for agent evaluation - mirrors CLI commands.

    This interface provides Python API equivalents to CLI evaluation commands,
    reusing the same underlying operations for consistency.

    Example:
        >>> from bedrock_agentcore_starter_toolkit import Evaluation
        >>>
        >>> # For evaluator management (no agent_id needed)
        >>> eval_client = Evaluation(region="us-east-1")
        >>> evaluators = eval_client.list_evaluators()
        >>> details = eval_client.get_evaluator("Builtin.Helpfulness")
        >>>
        >>> # For running evaluations (provide agent_id)
        >>> results = eval_client.run(agent_id="my-agent", session_id="session-123")
        >>>
        >>> # Or set default agent_id in initialization
        >>> eval_client = Evaluation(region="us-east-1", agent_id="my-agent")
        >>> results = eval_client.run(session_id="session-123")
    """

    def __init__(
        self,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """Initialize Evaluation client.

        Args:
            region: AWS region (optional - uses boto3 default if not specified)
            endpoint_url: Optional custom evaluation API endpoint

        Note:
            agent_id is NOT stored at the client level - it must be provided as a parameter
            to methods that require it (like run()). This makes the API clearer and thread-safe.

        Example:
            # For evaluator management (no agent_id needed)
            >>> eval_client = Evaluation(region="us-east-1")
            >>> eval_client.list_evaluators()
            >>> eval_client.create_evaluator(name="my-eval", config={...})

            # For running evaluations (provide agent_id as parameter)
            >>> eval_client = Evaluation(region="us-east-1")
            >>> results = eval_client.run(agent_id="my-agent", session_id="session-123")
        """
        # Use provided region or fall back to boto3 default
        if region:
            self.region = region
        else:
            import boto3

            session = boto3.Session()
            self.region = session.region_name or "us-east-1"

        self.console = Console()

        # Initialize clients and processor (reuse operations layer)
        self._data_plane_client = EvaluationDataPlaneClient(region_name=self.region, endpoint_url=endpoint_url)
        self._control_plane_client = EvaluationControlPlaneClient(region_name=self.region)
        self._processor = EvaluationProcessor(self._data_plane_client, self._control_plane_client)

    @classmethod
    def from_config(
        cls, config_path: Optional[Path] = None, agent_name: Optional[str] = None
    ) -> tuple["Evaluation", str, Optional[str]]:
        """Create Evaluation client from config file.

        Args:
            config_path: Path to config file (default: .bedrock_agentcore.yaml in cwd)
            agent_name: Agent name from config (uses first agent if not specified)

        Returns:
            Tuple of (Evaluation instance, agent_id, session_id)

        Example:
            eval_client, agent_id, session_id = Evaluation.from_config()
            results = eval_client.run(agent_id=agent_id, session_id=session_id)

            # Or just use the agent_id
            eval_client, agent_id, _ = Evaluation.from_config()
            results = eval_client.run(agent_id=agent_id, session_id="my-session")
        """
        # Import here to avoid circular dependency
        from ...utils.runtime.config import load_config_if_exists

        if config_path is None:
            config_path = Path.cwd() / ".bedrock_agentcore.yaml"

        config = load_config_if_exists(config_path)
        if not config:
            raise ValueError(f"No config file found at {config_path}")

        agent_config = config.get_agent_config(agent_name)

        return (
            cls(region=agent_config.aws.region),
            agent_config.bedrock_agentcore.agent_id,
            agent_config.bedrock_agentcore.agent_session_id,
        )

    def get_latest_session(self, agent_id: str) -> Optional[str]:
        """Get the latest session ID for the specified agent.

        Args:
            agent_id: Agent ID to query for latest session

        Returns:
            Latest session ID or None if no sessions found

        Raises:
            ValueError: If agent_id or region not configured
        """
        if not agent_id or not self.region:
            raise ValueError("Agent ID and region required")

        # Initialize processor if needed
        if not self._processor:
            self._data_plane_client = EvaluationDataPlaneClient(region_name=self.region)
            self._control_plane_client = EvaluationControlPlaneClient(region_name=self.region)
            self._processor = EvaluationProcessor(self._data_plane_client, self._control_plane_client)

        try:
            # Use processor's get_latest_session
            latest = self._processor.get_latest_session(agent_id, self.region)

            if not latest:
                self.console.print(f"[yellow]Warning: No sessions found for agent {agent_id} (last 7 days)[/yellow]")

            return latest
        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to fetch latest session: {e}[/yellow]")
            return None

    def run(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        evaluators: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
        output: Optional[str] = None,
    ) -> EvaluationResults:
        """Run evaluation on a session (mirrors: agentcore eval run).

        Default: Evaluates all traces (most recent 1000 spans).
        With trace_id: Evaluates only that trace (includes spans from all previous traces for context).

        Args:
            agent_id: Agent ID to evaluate (required)
            session_id: Session ID to evaluate (auto-fetches latest if not provided)
            evaluators: List of evaluators to use (default: ["Builtin.GoalSuccessRate"])
            trace_id: Optional trace ID - evaluates only this trace, with previous traces for context
            output: Optional path to save results to JSON file

        Returns:
            EvaluationResults with scores and explanations

        Example:
            # Evaluate latest session automatically
            results = eval_client.run(agent_id="my-agent")

            # Evaluate specific session
            results = eval_client.run(agent_id="my-agent", session_id="session-123")

            # Evaluate with multiple evaluators
            results = eval_client.run(
                agent_id="my-agent",
                session_id="session-123",
                evaluators=["Builtin.Helpfulness", "Builtin.Accuracy"]
            )

            # Evaluate specific trace only (with previous traces for context)
            results = eval_client.run(agent_id="my-agent", session_id="session-123", trace_id="trace-456")

            # Save results to file
            results = eval_client.run(agent_id="my-agent", session_id="session-123", output="results.json")
        """
        if not agent_id:
            raise ValueError(
                "agent_id is required for run(). Provide it as a parameter.\n"
                "Example: eval_client.run(agent_id='my-agent', session_id='session-123')"
            )

        # If no session_id provided, try to fetch latest
        if not session_id:
            self.console.print("[cyan]No session_id provided, fetching latest session...[/cyan]")
            session_id = self.get_latest_session(agent_id)

            if not session_id:
                raise ValueError(
                    "No session_id provided and could not fetch latest session. "
                    "Please provide session_id explicitly or ensure agent has recent sessions."
                )

            self.console.print(f"[cyan]Using latest session:[/cyan] {session_id}\n")

        # Initialize clients if not done yet (deferred initialization)
        if not self._processor:
            self._data_plane_client = EvaluationDataPlaneClient(region_name=self.region)
            self._control_plane_client = EvaluationControlPlaneClient(region_name=self.region)
            self._processor = EvaluationProcessor(self._data_plane_client, self._control_plane_client)

        evaluators = evaluators or ["Builtin.GoalSuccessRate"]

        # Display what we're doing (similar to CLI)
        self.console.print(f"\n[cyan]Evaluating session:[/cyan] {session_id}")
        if trace_id:
            self.console.print(f"[cyan]Trace:[/cyan] {trace_id} (with previous traces for context)")
        else:
            self.console.print("[cyan]Mode:[/cyan] All traces (most recent 1000 spans)")
        self.console.print(f"[cyan]Evaluators:[/cyan] {', '.join(evaluators)}\n")

        # Run evaluation using processor
        with self.console.status("[cyan]Running evaluation...[/cyan]"):
            results = self._processor.evaluate_session(
                session_id=session_id,
                evaluators=evaluators,
                agent_id=agent_id,
                region=self.region,
                trace_id=trace_id,
            )

        # Save to file if requested
        if output:
            save_evaluation_results(results, output, self.console)

        return results

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
            response = self._control_plane_client.list_evaluators(max_results=max_results)

        evaluators = response.get("evaluators", [])
        display_evaluator_list(evaluators, self.console)
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
            response = self._control_plane_client.get_evaluator(evaluator_id=evaluator_id)

        # Save to file if requested
        if output:
            save_json_output(response, output, self.console)
            return response

        # Display details
        display_evaluator_details(response, self.console)
        return response

    def duplicate_evaluator(
        self,
        source_evaluator_id: str,
        new_name: str,
        description: Optional[str] = None,
    ) -> Dict:
        """Duplicate a custom evaluator (mirrors: agentcore eval evaluator create interactive).

        Args:
            source_evaluator_id: ID of custom evaluator to duplicate
            new_name: Name for the new evaluator
            description: Optional description for new evaluator (defaults to source description)

        Returns:
            Dict with evaluator creation response

        Example:
            # Duplicate an existing custom evaluator
            response = eval_client.duplicate_evaluator(
                "my-evaluator-abc123",
                "my-evaluator-v2",
                description="Version 2 of my evaluator"
            )
        """
        # Create new evaluator using operations module
        with self.console.status(f"[cyan]Creating evaluator '{new_name}'...[/cyan]"):
            response = evaluator_processor.duplicate_evaluator(
                self._control_plane_client, source_evaluator_id, new_name, description
            )

        evaluator_id = response.get("evaluatorId", "")
        evaluator_arn = response.get("evaluatorArn", "")

        self.console.print("\n[green]✓[/green] Evaluator duplicated successfully!")
        self.console.print(f"\n[bold]ID:[/bold] {evaluator_id}")
        self.console.print(f"[bold]ARN:[/bold] {evaluator_arn}")
        self.console.print(f"\n[dim]Use: eval_client.run(evaluators=['{evaluator_id}'])[/dim]")

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
            level: Evaluation level (TRACE, TOOL_CALL, SESSION)
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
        with self.console.status(f"[cyan]Creating evaluator '{name}'...[/cyan]"):
            response = evaluator_processor.create_evaluator(
                self._control_plane_client, name, config, level, description
            )

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
        with self.console.status(f"[cyan]Updating evaluator {evaluator_id}...[/cyan]"):
            response = evaluator_processor.update_evaluator(
                self._control_plane_client, evaluator_id, description, config
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
            evaluator_processor.delete_evaluator(self._control_plane_client, evaluator_id)

        self.console.print("\n[green]✓[/green] Evaluator deleted successfully")

    # ===========================
    # Online Evaluation Config Methods
    # ===========================

    def create_online_config(
        self,
        config_name: str,
        agent_id: Optional[str] = None,
        agent_endpoint: str = "DEFAULT",
        config_description: Optional[str] = None,
        sampling_rate: float = 1.0,
        evaluator_list: Optional[List[str]] = None,
        execution_role: Optional[str] = None,
        auto_create_execution_role: bool = True,
        enable_on_create: bool = True,
    ) -> Dict:
        """Create online evaluation configuration (mirrors: agentcore eval online create).

        Enables continuous automatic evaluation of agent interactions by monitoring
        CloudWatch logs and evaluating sampled interactions in real-time.

        Args:
            config_name: Name for the evaluation configuration
            agent_id: Agent ID to evaluate (required)
            agent_endpoint: Agent endpoint type (DEFAULT, DRAFT, or alias ARN)
            config_description: Optional description
            sampling_rate: Percentage of interactions to evaluate (0-100, default: 1.0)
            evaluator_list: List of evaluator IDs (default: ["Builtin.GoalSuccessRate"])
            execution_role: IAM role ARN for evaluation execution
            auto_create_execution_role: Auto-create role if not provided (default: True)
            enable_on_create: Enable config immediately after creation (default: True)

        Returns:
            Dict with config details from API response

        Example:
            # Create with defaults (1% sampling, Builtin.GoalSuccessRate)
            config = eval_client.create_online_config("my-config", agent_id="my-agent")

            # Create with custom settings
            config = eval_client.create_online_config(
                config_name="production-eval",
                agent_id="my-agent",
                sampling_rate=5.0,
                evaluator_list=["Builtin.Helpfulness", "Builtin.Accuracy"],
                config_description="Production evaluation config"
            )

            # Access output log group
            output_log = config['outputConfig']['cloudWatchConfig']['logGroupName']
        """
        if not agent_id:
            raise ValueError("agent_id is required. Provide it in create_online_config()")

        response = online_processor.create_online_evaluation_config(
            client=self._control_plane_client,
            config_name=config_name,
            agent_id=agent_id,
            agent_endpoint=agent_endpoint,
            config_description=config_description,
            sampling_rate=sampling_rate,
            evaluator_list=evaluator_list,
            execution_role=execution_role,
            auto_create_execution_role=auto_create_execution_role,
            enable_on_create=enable_on_create,
        )

        self.console.print("✅ Online evaluation configuration created!")

        return response

    def get_online_config(self, config_id: str) -> Dict:
        """Get online evaluation configuration details (mirrors: agentcore eval online get).

        Args:
            config_id: Online evaluation config ID

        Returns:
            Dict with config details from API response

        Example:
            config = eval_client.get_online_config("config-123")
            print(f"Status: {config['status']}")
            print(f"Sampling: {config['rule']['samplingConfig']['samplingPercentage']}%")
        """
        response = online_processor.get_online_evaluation_config(
            client=self._control_plane_client,
            config_id=config_id,
        )

        return response

    def list_online_configs(self, agent_id: Optional[str] = None, max_results: int = 50) -> Dict:
        """List online evaluation configurations (mirrors: agentcore eval online list).

        Args:
            agent_id: Optional filter by agent ID
            max_results: Maximum number of configs to return

        Returns:
            Dict with 'onlineEvaluationConfigs' key containing list of config dicts

        Example:
            # List all configs
            configs = eval_client.list_online_configs()

            # List configs for specific agent
            configs = eval_client.list_online_configs(agent_id="agent-123")

            # Print config details
            for config in configs['onlineEvaluationConfigs']:
                print(f"{config['onlineEvaluationConfigName']}: {config['status']}")
        """
        with self.console.status("[cyan]Fetching online evaluation configs...[/cyan]"):
            response = online_processor.list_online_evaluation_configs(
                client=self._control_plane_client,
                agent_id=agent_id,
                max_results=max_results,
            )

        return response

    def update_online_config(
        self,
        config_id: str,
        status: Optional[str] = None,
        sampling_rate: Optional[float] = None,
        evaluator_list: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict:
        """Update online evaluation configuration (mirrors: agentcore eval online update).

        Args:
            config_id: Online evaluation config ID to update
            status: New status (ENABLED/DISABLED)
            sampling_rate: New sampling rate (0-100)
            evaluator_list: New list of evaluator IDs
            description: New description

        Returns:
            Dict with updated config details

        Example:
            # Enable/disable config
            eval_client.update_online_config("config-123", status="DISABLED")

            # Change sampling rate
            eval_client.update_online_config("config-123", sampling_rate=75.0)

            # Update evaluators
            eval_client.update_online_config(
                "config-123",
                evaluator_list=["Builtin.Helpfulness", "Builtin.Accuracy"]
            )
        """
        response = online_processor.update_online_evaluation_config(
            client=self._control_plane_client,
            config_id=config_id,
            status=status,
            sampling_rate=sampling_rate,
            evaluator_list=evaluator_list,
            description=description,
        )

        self.console.print("✅ Configuration updated!")

        return response

    def delete_online_config(self, config_id: str, delete_execution_role: bool = False) -> None:
        """Delete online evaluation configuration (mirrors: agentcore eval online delete).

        Args:
            config_id: Online evaluation config ID to delete
            delete_execution_role: If True, also delete the IAM execution role (default: False)

        Example:
            # Delete config only
            eval_client.delete_online_config("config-123")

            # Delete config and its execution role
            eval_client.delete_online_config("config-123", delete_execution_role=True)
        """
        online_processor.delete_online_evaluation_config(
            client=self._control_plane_client,
            config_id=config_id,
            delete_execution_role=delete_execution_role,
        )

        self.console.print("✅ Configuration deleted!")
